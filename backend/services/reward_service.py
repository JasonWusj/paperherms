from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import AgentTask, AgentTrace, RewardEvent, UserFeedback
from backend.schemas import UserFeedbackCreate


class RewardService:
    """Calculate auditable rewards from automatic signals and human feedback.

    The service intentionally keeps the reward calculation deterministic.  This
    makes it usable both online after a feedback request and offline during
    policy replay.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_feedback(self, task_id: str, user_id: str = "default") -> UserFeedback | None:
        return self.db.scalar(
            select(UserFeedback).where(
                UserFeedback.task_id == task_id,
                UserFeedback.user_id == user_id,
            )
        )

    def upsert_feedback(
        self, task: AgentTask, payload: UserFeedbackCreate
    ) -> tuple[UserFeedback, RewardEvent]:
        feedback = self.get_feedback(task.id, payload.user_id)
        if feedback is None:
            feedback = UserFeedback(
                task_id=task.id,
                user_id=payload.user_id,
                rating=payload.rating,
                issue_tags=payload.issue_tags,
                comment=payload.comment,
            )
            self.db.add(feedback)
            self.db.flush()
        else:
            feedback.rating = payload.rating
            feedback.issue_tags = payload.issue_tags
            feedback.comment = payload.comment

        event = self._record_reward(task, feedback=feedback, reward_type="final")
        self.db.commit()
        self.db.refresh(feedback)
        self.db.refresh(event)
        return feedback, event

    def record_weak_reward(self, task: AgentTask) -> RewardEvent:
        """Record an automatic reward before a user has responded."""
        event = self.db.scalar(
            select(RewardEvent)
            .where(RewardEvent.task_id == task.id, RewardEvent.reward_type == "weak")
            .order_by(RewardEvent.created_at.desc())
        )
        if event is None:
            event = self._record_reward(task, feedback=None, reward_type="weak")
        else:
            self._update_reward(event, task, feedback=None, reward_type="weak")
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_events(
        self, *, task_id: str | None = None, user_id: str | None = None, limit: int = 50
    ) -> list[RewardEvent]:
        statement = select(RewardEvent).order_by(RewardEvent.created_at.desc()).limit(limit)
        if task_id:
            statement = statement.where(RewardEvent.task_id == task_id)
        if user_id:
            statement = statement.where(RewardEvent.user_id == user_id)
        return list(self.db.scalars(statement))

    def summarize(self, user_id: str | None = None) -> dict[str, Any]:
        events = self.list_events(user_id=user_id, limit=1000)
        final = [event for event in events if event.reward_type == "final"]
        by_type: dict[str, dict[str, float]] = {}
        for event in events:
            item = by_type.setdefault(event.reward_type, {"count": 0, "reward_total": 0.0})
            item["count"] += 1
            item["reward_total"] += event.reward
        return {
            "user_id": user_id,
            "event_count": len(events),
            "feedback_count": len(final),
            "average_reward": round(sum(event.reward for event in events) / max(len(events), 1), 4),
            "average_final_reward": round(sum(event.reward for event in final) / max(len(final), 1), 4),
            "by_type": by_type,
        }

    def _record_reward(
        self, task: AgentTask, *, feedback: UserFeedback | None, reward_type: str
    ) -> RewardEvent:
        event = RewardEvent(
            task_id=task.id,
            feedback_id=feedback.id if feedback else None,
            user_id=feedback.user_id if feedback else task.user_id,
            reward_type=reward_type,
            reward=0.0,
            components={},
            source="human+automatic" if feedback else "automatic",
        )
        self.db.add(event)
        self.db.flush()
        self._update_reward(event, task, feedback=feedback, reward_type=reward_type)
        return event

    def _update_reward(
        self,
        event: RewardEvent,
        task: AgentTask,
        *,
        feedback: UserFeedback | None,
        reward_type: str,
    ) -> None:
        metrics = self._automatic_metrics(task)
        user_feedback = 0.5 if feedback is None else (1.0 if feedback.rating > 0 else 0.0)
        components = {
            "user_feedback": round(user_feedback, 4),
            "faithfulness": metrics["faithfulness"],
            "relevance": metrics["relevance"],
            "completeness": metrics["completeness"],
            "latency_penalty": metrics["latency_penalty"],
            "cost_penalty": metrics["cost_penalty"],
            "weak_reward": feedback is None,
            "feedback_rating": feedback.rating if feedback else None,
        }
        reward = (
            0.40 * components["user_feedback"]
            + 0.20 * components["faithfulness"]
            + 0.15 * components["relevance"]
            + 0.10 * components["completeness"]
            - 0.10 * components["latency_penalty"]
            - 0.05 * components["cost_penalty"]
        )
        event.reward_type = reward_type
        event.feedback_id = feedback.id if feedback else None
        event.user_id = feedback.user_id if feedback else task.user_id
        event.reward = round(reward, 6)
        event.components = components
        event.source = "human+automatic" if feedback else "automatic"

    def _automatic_metrics(self, task: AgentTask) -> dict[str, float]:
        traces = list(
            self.db.scalars(select(AgentTrace).where(AgentTrace.task_id == task.id))
        )
        answer = task.output_text or ""
        evidence_count = 0
        latency_ms = 0
        token_count = 0
        faithfulness = 0.0
        for trace in traces:
            latency_ms += int(trace.latency_ms or 0)
            usage = trace.token_usage or {}
            token_count += int(
                usage.get("total_tokens")
                or usage.get("total")
                or usage.get("input_tokens", 0)
                + usage.get("output_tokens", 0)
                or 0
            )
            evidence_count = max(evidence_count, len(trace.retrieved_chunks or []))
            if trace.agent_name == "ReflectionAgent":
                payload = (trace.output_json or {}).get("output", {})
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        payload = {}
                if isinstance(payload, dict):
                    confidence = float(payload.get("confidence", 0) or 0)
                    if payload.get("status") in {"checked", "completed"}:
                        faithfulness = max(faithfulness, min(max(confidence, 0.0), 1.0))
                    evidence_count = max(evidence_count, int(payload.get("evidence_count", 0) or 0))

        completed = 1.0 if task.status == "completed" and bool(answer.strip()) else 0.0
        relevance = completed
        completeness = min(evidence_count / 3.0, 1.0) if completed else 0.0
        if faithfulness == 0.0 and evidence_count:
            faithfulness = 0.5
        return {
            "faithfulness": round(faithfulness, 4),
            "relevance": round(relevance, 4),
            "completeness": round(completeness, 4),
            "latency_penalty": round(min(latency_ms / 5000.0, 1.0), 4),
            "cost_penalty": round(min(token_count / 6000.0, 1.0), 4),
        }
