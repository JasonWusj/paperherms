from __future__ import annotations

import hashlib
import random
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.db.models import AgentTask, BanditState, PolicyDecision, RewardEvent


class BanditService:
    """Small, interpretable LinUCB controller for RAG/Agent policy arms."""

    ACTIONS = ("economy", "balanced", "deep")
    STATE_KEY = "rag_policy"
    POLICY_VERSION = "linucb-v1"
    CONTEXT_DIM = 8

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def context(self, task: AgentTask) -> list[float]:
        text = task.input_text or ""
        digest = hashlib.sha256((task.task_type or "chat").encode("utf-8")).digest()
        task_hash = [digest[index] / 255.0 for index in (0, 1, 2)]
        chinese_ratio = sum("\u4e00" <= char <= "\u9fff" for char in text) / max(len(text), 1)
        return [
            1.0,
            min(len(text) / 500.0, 1.0),
            1.0 if task.paper_id else 0.0,
            chinese_ratio,
            *task_hash,
            1.0 if any(word in text.lower() for word in ("compare", "对比", "比较")) else 0.0,
        ]

    def choose(self, task: AgentTask) -> dict[str, Any]:
        configured = (self.settings.policy_name or "fixed").lower()
        context = self.context(task)
        if configured != "linucb":
            return {
                "policy_name": "fixed",
                "policy_version": "fixed-v1",
                "action": "balanced",
                "context": context,
                "action_scores": {action: 1.0 if action == "balanced" else 0.0 for action in self.ACTIONS},
                "propensity": 1.0,
                "exploration": False,
                "reason": "fixed baseline policy",
            }

        state = self._state()
        scores = {action: self._score(state, action, context) for action in self.ACTIONS}
        min_samples = max(int(self.settings.policy_min_samples), 0)
        warmup = state.total_updates < min_samples * len(self.ACTIONS)
        rng = random.Random(task.id)
        exploration = warmup or rng.random() < float(self.settings.policy_epsilon)
        if warmup:
            action = self.ACTIONS[state.total_updates % len(self.ACTIONS)]
            reason = "round-robin cold-start exploration"
        elif exploration:
            action = rng.choice(list(self.ACTIONS))
            reason = "epsilon exploration"
        else:
            action = max(self.ACTIONS, key=lambda item: scores[item])
            reason = "highest LinUCB upper confidence bound"
        epsilon = min(max(float(self.settings.policy_epsilon), 0.0), 1.0)
        propensity = (1.0 / len(self.ACTIONS)) if warmup else (
            epsilon / len(self.ACTIONS) + (1.0 - epsilon if not exploration else 0.0)
        )
        return {
            "policy_name": "linucb",
            "policy_version": state.policy_version,
            "action": action,
            "context": context,
            "action_scores": {key: round(value, 6) for key, value in scores.items()},
            "propensity": round(propensity, 6),
            "exploration": exploration,
            "reason": reason,
        }

    def record_decision(self, task: AgentTask, decision: dict[str, Any]) -> PolicyDecision:
        record = PolicyDecision(
            task_id=task.id,
            user_id=task.user_id,
            policy_name=str(decision.get("policy_name") or "fixed"),
            policy_version=str(decision.get("policy_version") or "fixed-v1"),
            action=str(decision.get("action") or "balanced"),
            context={"features": list(decision.get("context") or [])},
            action_scores=dict(decision.get("action_scores") or {}),
            propensity=float(decision.get("propensity", 1.0) or 1.0),
            exploration=bool(decision.get("exploration", False)),
            reason=str(decision.get("reason") or ""),
        )
        self.db.add(record)
        task.metadata_json = {
            **(task.metadata_json or {}),
            "policy": {
                **decision,
                "decision_id": record.id,
            },
        }
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_from_reward(self, task_id: str, event: RewardEvent) -> bool:
        decision = self.db.scalar(
            select(PolicyDecision).where(PolicyDecision.task_id == task_id).order_by(PolicyDecision.created_at.desc())
        )
        if not decision or decision.policy_name != "linucb":
            return False
        state = self._state()
        raw_context = (decision.context or {}).get("features", [])
        context = np.asarray(raw_context, dtype=float)
        if context.shape != (self.CONTEXT_DIM,):
            return False
        arm = state.parameters.setdefault(decision.action, self._empty_arm())
        matrix = np.asarray(arm["a"], dtype=float)
        vector = np.asarray(arm["b"], dtype=float)
        matrix += np.outer(context, context)
        vector += float(event.reward) * context
        arm["a"] = matrix.tolist()
        arm["b"] = vector.tolist()
        state.parameters = dict(state.parameters)
        state.counts = {**(state.counts or {}), decision.action: int((state.counts or {}).get(decision.action, 0)) + 1}
        state.total_updates = int(state.total_updates or 0) + 1
        self.db.commit()
        return True

    def summary(self) -> dict[str, Any]:
        state = self._state()
        events = list(self.db.scalars(select(RewardEvent).order_by(RewardEvent.created_at.desc()).limit(1000)))
        rewards_by_action = {action: [] for action in self.ACTIONS}
        decisions = list(self.db.scalars(select(PolicyDecision).order_by(PolicyDecision.created_at.desc()).limit(1000)))
        action_by_task = {decision.task_id: decision.action for decision in decisions}
        for event in events:
            action = action_by_task.get(event.task_id)
            if action in rewards_by_action:
                rewards_by_action[action].append(event.reward)
        return {
            "policy_name": self.settings.policy_name,
            "policy_version": state.policy_version,
            "actions": list(self.ACTIONS),
            "counts": state.counts or {},
            "total_updates": state.total_updates,
            "average_reward_by_action": {
                action: round(sum(values) / max(len(values), 1), 4)
                for action, values in rewards_by_action.items()
            },
        }

    def offline_replay(self, limit: int = 1000) -> dict[str, Any]:
        """Counterfactual comparison using capped inverse propensity scoring."""
        decisions = list(
            self.db.scalars(select(PolicyDecision).order_by(PolicyDecision.created_at.desc()).limit(limit))
        )
        events = list(
            self.db.scalars(select(RewardEvent).order_by(RewardEvent.created_at.desc()).limit(limit * 2))
        )
        reward_by_task: dict[str, RewardEvent] = {}
        for event in events:
            current = reward_by_task.get(event.task_id)
            if current is None or (current.reward_type == "weak" and event.reward_type == "final"):
                reward_by_task[event.task_id] = event
        samples = [
            (decision, reward_by_task[decision.task_id])
            for decision in decisions
            if decision.task_id in reward_by_task and decision.propensity > 0
        ]

        def estimate(target_action: str | None) -> dict[str, float | int]:
            weighted = 0.0
            effective = 0
            for decision, event in samples:
                target_probability = (1.0 / len(self.ACTIONS)) if target_action is None else (
                    1.0 if decision.action == target_action else 0.0
                )
                if target_probability == 0.0:
                    continue
                weight = min(target_probability / max(decision.propensity, 1e-6), 10.0)
                weighted += weight * event.reward
                effective += 1
            return {
                "estimated_reward": round(weighted / max(len(samples), 1), 6),
                "matched_samples": effective,
            }

        arm_rewards = {
            action: [event.reward for decision, event in samples if decision.action == action]
            for action in self.ACTIONS
        }
        arm_means = {
            action: sum(values) / len(values) if values else 0.0
            for action, values in arm_rewards.items()
        }
        best_mean = max(arm_means.values(), default=0.0)
        cumulative_regret = sum(best_mean - event.reward for _, event in reversed(samples))
        return {
            "method": "capped_inverse_propensity_scoring",
            "sample_count": len(samples),
            "policies": {
                "fixed_economy": estimate("economy"),
                "fixed_balanced": estimate("balanced"),
                "fixed_deep": estimate("deep"),
                "random": estimate(None),
                "logged_policy": {
                    "estimated_reward": round(
                        sum(event.reward for _, event in samples) / max(len(samples), 1), 6
                    ),
                    "matched_samples": len(samples),
                },
            },
            "observed_arm_means": {key: round(value, 6) for key, value in arm_means.items()},
            "cumulative_regret": round(cumulative_regret, 6),
            "warning": "IPS estimates are exploratory until every action has sufficient logged support.",
        }

    def retrieval_limit(self, action: str) -> int:
        return {"economy": 3, "balanced": 5, "deep": 8}.get(action, 5)

    def _state(self) -> BanditState:
        state = self.db.get(BanditState, self.STATE_KEY)
        if state:
            return state
        state = BanditState(
            state_key=self.STATE_KEY,
            policy_version=self.POLICY_VERSION,
            dimension=self.CONTEXT_DIM,
            alpha=float(self.settings.policy_alpha),
            epsilon=float(self.settings.policy_epsilon),
            actions=list(self.ACTIONS),
            parameters={action: self._empty_arm() for action in self.ACTIONS},
            counts={action: 0 for action in self.ACTIONS},
        )
        self.db.add(state)
        self.db.commit()
        self.db.refresh(state)
        return state

    def _score(self, state: BanditState, action: str, context: list[float]) -> float:
        arm = (state.parameters or {}).get(action) or self._empty_arm()
        matrix = np.asarray(arm["a"], dtype=float)
        vector = np.asarray(arm["b"], dtype=float)
        x = np.asarray(context, dtype=float)
        try:
            inverse_x = np.linalg.solve(matrix, x)
        except np.linalg.LinAlgError:
            inverse_x = np.linalg.pinv(matrix) @ x
        theta = np.linalg.solve(matrix, vector) if np.linalg.det(matrix) else np.linalg.pinv(matrix) @ vector
        uncertainty = float(np.sqrt(max(x @ inverse_x, 0.0)))
        return float(theta @ x + state.alpha * uncertainty)

    def _empty_arm(self) -> dict[str, Any]:
        return {
            "a": np.eye(self.CONTEXT_DIM, dtype=float).tolist(),
            "b": np.zeros(self.CONTEXT_DIM, dtype=float).tolist(),
        }
