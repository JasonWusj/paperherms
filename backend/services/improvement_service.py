from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from sqlalchemy.orm import Session

from backend.db.models import HermesRevision, ImprovementSuggestion, Memory, Skill
from backend.schemas import MemoryCreate, MemoryUpdate, SkillUpdate
from backend.services.evaluation_service import HermesEvaluationService
from backend.services.integration_service import IntegrationNotificationService
from backend.services.memory_service import MemoryService
from backend.services.skill_service import SkillService
from backend.services.trace_service import TraceService


class HermesImprovementService:
    REGRESSION_SUITE = "paperhermes-regression"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.trace_service = TraceService(db)
        self.memory_service = MemoryService(db)
        self.skill_service = SkillService(db)
        self.evaluation_service = HermesEvaluationService(db)

    def suggestions(self, user_id: str | None = None) -> dict[str, Any]:
        for item in self._computed_suggestions(user_id=user_id):
            self._ensure_suggestion(user_id=user_id, item=item)
        return {
            "user_id": user_id,
            "suggestions": [self._serialize_suggestion(item) for item in self._list_suggestions(user_id=user_id)],
        }

    def _computed_suggestions(self, user_id: str | None = None) -> list[dict[str, Any]]:
        items = []
        for signal in self.trace_service.memory_review_signals(user_id=user_id):
            memory_id = signal["memory_id"]
            items.append({
                "target_type": "memory",
                "target_id": memory_id,
                "suggestion_type": "review_patch",
                "status": "draft",
                "reason": signal["reason"],
                "proposed_patch": {
                    "action": "review_memory",
                    "memory_id": memory_id,
                    "recommendation": "revise or archive this memory before future recall",
                },
            })
        for signal in self.trace_service.workflow_lesson_review_signals(user_id=user_id):
            lesson_id = signal["lesson_id"]
            items.append({
                "target_type": "memory",
                "target_id": lesson_id,
                "suggestion_type": "review_patch",
                "status": "draft",
                "reason": signal["reason"],
                "proposed_patch": {
                    "action": "review_workflow_lesson",
                    "lesson_id": lesson_id,
                    "recommendation": "revise or archive this workflow lesson before future planning",
                },
            })
        for signal in self.trace_service.skill_review_signals(user_id=user_id):
            skill_id = signal["skill_id"]
            items.append({
                "target_type": "skill",
                "target_id": skill_id,
                "suggestion_type": "review_patch",
                "status": "draft",
                "reason": signal["reason"],
                "proposed_patch": {
                    "action": "review_skill",
                    "skill_id": skill_id,
                    "recommendation": "tighten trigger patterns or revise execution steps",
                },
            })
        for signal in self.trace_service.plan_review_signals(user_id=user_id):
            task_type = signal["task_type"]
            items.append({
                "target_type": "workflow",
                "target_id": task_type,
                "suggestion_type": "workflow_lesson_patch",
                "status": "draft",
                "reason": signal["reason"],
                "proposed_patch": {
                    "action": "draft_workflow_lesson",
                    "task_type": task_type,
                    "lesson": f"Review {task_type} workflow: incomplete plans exceeded completed plans after {signal['uses']} uses.",
                },
            })
        return sorted(items, key=lambda item: (item["target_type"], item["target_id"]))

    def apply(self, payload) -> dict[str, Any] | None:
        suite = self._evaluation_suite_for_apply(payload.user_id)
        baseline_run = self.evaluation_service.create_run(
            user_id=payload.user_id,
            suite=suite,
            trigger="suggestion_apply_baseline",
        )
        evaluation_before = baseline_run["summary"]
        target_snapshot = self._target_snapshot(payload)
        suggestion = self._find_suggestion(
            user_id=payload.user_id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            suggestion_type=payload.suggestion_type,
        )
        if target_snapshot:
            self._record_revision(payload, "before_apply", target_snapshot, suggestion=suggestion)
        if payload.target_type == "workflow":
            result = self._apply_workflow(payload)
        if payload.target_type == "memory":
            result = self._apply_memory(payload)
        if payload.target_type == "skill":
            result = self._apply_skill(payload)
        if payload.target_type not in {"workflow", "memory", "skill"}:
            return None
        if result is not None:
            candidate_run = self.evaluation_service.create_run(
                user_id=payload.user_id,
                suite=suite,
                trigger="suggestion_apply_candidate",
            )
            evaluation_after = candidate_run["summary"]
            comparison = self.evaluation_service.compare_runs(
                baseline_run_id=baseline_run["id"],
                candidate_run_id=candidate_run["id"],
            ) or {}
            policy_decision = self.policy_decision(comparison)
            applied_snapshot = self._result_snapshot(payload, result)
            if applied_snapshot:
                self._record_revision(payload, "after_apply", applied_snapshot, suggestion=suggestion, policy_decision=policy_decision)
            if policy_decision.get("status") == "blocked":
                rollback_snapshot = self._rollback_target(payload, target_snapshot, result)
                result["status"] = "blocked"
                result["rolled_back"] = True
                if rollback_snapshot:
                    self._record_revision(payload, "rolled_back", rollback_snapshot, suggestion=suggestion, policy_decision=policy_decision)
            result["policy_decision"] = policy_decision
            self._mark_applied(payload, evaluation_before, evaluation_after, baseline_run["id"], candidate_run["id"], comparison, policy_decision)
        return result

    def _evaluation_suite_for_apply(self, user_id: str) -> str | None:
        extraction = self.evaluation_service.extract_regression_cases(
            user_id=user_id,
            suite=self.REGRESSION_SUITE,
        )
        return self.REGRESSION_SUITE if extraction.get("cases") else None

    def review(self, suggestion_id: str, payload) -> dict[str, Any] | None:
        if payload.status not in {"rejected", "archived"}:
            return None
        suggestion = self.db.get(ImprovementSuggestion, suggestion_id)
        if not suggestion:
            return None
        suggestion.status = payload.status
        suggestion.reviewed_by = payload.reviewed_by
        suggestion.reviewed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(suggestion)
        return self._serialize_suggestion(suggestion)

    def _ensure_suggestion(self, user_id: str | None, item: dict[str, Any]) -> ImprovementSuggestion:
        suggestion = self._find_suggestion(
            user_id=user_id,
            target_type=item["target_type"],
            target_id=item["target_id"],
            suggestion_type=item["suggestion_type"],
        )
        if suggestion:
            if suggestion.status == "draft":
                suggestion.reason = item["reason"]
                suggestion.proposed_patch = item["proposed_patch"]
                self.db.commit()
                self.db.refresh(suggestion)
            return suggestion
        suggestion = ImprovementSuggestion(
            user_id=user_id or "default",
            target_type=item["target_type"],
            target_id=item["target_id"],
            suggestion_type=item["suggestion_type"],
            status="draft",
            reason=item["reason"],
            proposed_patch=item["proposed_patch"],
        )
        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)
        self._notify_improvement_suggestion_created(suggestion)
        return suggestion

    def _find_suggestion(
        self,
        *,
        user_id: str | None,
        target_type: str,
        target_id: str,
        suggestion_type: str,
    ) -> ImprovementSuggestion | None:
        return self.db.scalar(
            select(ImprovementSuggestion).where(
                ImprovementSuggestion.user_id == (user_id or "default"),
                ImprovementSuggestion.target_type == target_type,
                ImprovementSuggestion.target_id == target_id,
                ImprovementSuggestion.suggestion_type == suggestion_type,
            )
        )

    def _list_suggestions(self, user_id: str | None) -> list[ImprovementSuggestion]:
        statement = select(ImprovementSuggestion)
        if user_id is not None:
            statement = statement.where(ImprovementSuggestion.user_id == user_id)
        statement = statement.order_by(
            ImprovementSuggestion.target_type,
            ImprovementSuggestion.target_id,
            ImprovementSuggestion.created_at,
        )
        return list(self.db.scalars(statement))

    def list_revisions(self, target_type: str, target_id: str) -> list[dict[str, Any]]:
        statement = (
            select(HermesRevision)
            .where(HermesRevision.target_type == target_type, HermesRevision.target_id == target_id)
            .order_by(HermesRevision.sequence, HermesRevision.created_at, HermesRevision.id)
        )
        return [self._serialize_revision(item) for item in self.db.scalars(statement)]

    def rollback_revision(self, revision_id: str, reviewed_by: str = "default") -> dict[str, Any] | None:
        revision = self.db.get(HermesRevision, revision_id)
        if not revision:
            return None
        snapshot = dict(revision.snapshot_json or {})
        target = self._restore_revision_target(revision, snapshot)
        if target is None:
            return None
        policy_decision = {
            "status": "manual",
            "reason": f"rolled back by {reviewed_by}",
        }
        self._record_revision_record(
            user_id=revision.user_id,
            target_type=revision.target_type,
            target_id=revision.target_id,
            suggestion_id=revision.suggestion_id,
            action="manual_rollback",
            snapshot=self._restored_target_snapshot(revision.target_type, target),
            policy_decision=policy_decision,
        )
        return {
            "status": "rolled_back",
            "revision": self._serialize_revision(revision),
            "target": self._restored_target_snapshot(revision.target_type, target),
            "policy_decision": policy_decision,
        }

    def _serialize_suggestion(self, suggestion: ImprovementSuggestion) -> dict[str, Any]:
        return {
            "id": suggestion.id,
            "target_type": suggestion.target_type,
            "target_id": suggestion.target_id,
            "suggestion_type": suggestion.suggestion_type,
            "status": suggestion.status,
            "reason": suggestion.reason,
            "proposed_patch": suggestion.proposed_patch,
            "evaluation_before": suggestion.evaluation_before,
            "evaluation_after": suggestion.evaluation_after,
            "evaluation_delta": suggestion.evaluation_delta,
            "baseline_evaluation_run_id": suggestion.baseline_evaluation_run_id,
            "candidate_evaluation_run_id": suggestion.candidate_evaluation_run_id,
            "evaluation_comparison": suggestion.evaluation_comparison,
            "policy_decision": suggestion.policy_decision,
            "reviewed_by": suggestion.reviewed_by,
            "reviewed_at": suggestion.reviewed_at.isoformat() if suggestion.reviewed_at else None,
            "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
            "updated_at": suggestion.updated_at.isoformat() if suggestion.updated_at else None,
        }

    def _notify_improvement_suggestion_created(self, suggestion: ImprovementSuggestion) -> None:
        try:
            IntegrationNotificationService().notify_improvement_suggestion_created(
                self._serialize_suggestion(suggestion)
            )
        except Exception:
            return

    def _serialize_memory(self, memory: Memory) -> dict[str, Any]:
        return {
            "id": memory.id,
            "user_id": memory.user_id,
            "memory_type": memory.memory_type,
            "content": memory.content,
            "metadata_json": memory.metadata_json,
            "created_at": memory.created_at.isoformat() if memory.created_at else None,
            "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
        }

    def _serialize_skill(self, skill: Skill) -> dict[str, Any]:
        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "prompt_template": skill.prompt_template,
            "usage_count": skill.usage_count,
            "metadata_json": skill.metadata_json,
            "created_at": skill.created_at.isoformat() if skill.created_at else None,
            "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
        }

    def _serialize_revision(self, revision: HermesRevision) -> dict[str, Any]:
        return {
            "id": revision.id,
            "user_id": revision.user_id,
            "target_type": revision.target_type,
            "target_id": revision.target_id,
            "suggestion_id": revision.suggestion_id,
            "sequence": revision.sequence,
            "action": revision.action,
            "snapshot": revision.snapshot_json,
            "policy_decision": revision.policy_decision,
            "created_at": revision.created_at.isoformat() if revision.created_at else None,
            "updated_at": revision.updated_at.isoformat() if revision.updated_at else None,
        }

    def _record_revision(
        self,
        payload,
        action: str,
        snapshot: dict[str, Any],
        *,
        suggestion: ImprovementSuggestion | None,
        policy_decision: dict[str, Any] | None = None,
    ) -> HermesRevision:
        return self._record_revision_record(
            user_id=payload.user_id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            suggestion_id=suggestion.id if suggestion else None,
            action=action,
            snapshot=snapshot,
            policy_decision=policy_decision or {},
        )

    def _record_revision_record(
        self,
        *,
        user_id: str,
        target_type: str,
        target_id: str,
        suggestion_id: str | None,
        action: str,
        snapshot: dict[str, Any],
        policy_decision: dict[str, Any],
    ) -> HermesRevision:
        revision = HermesRevision(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            suggestion_id=suggestion_id,
            sequence=self._next_revision_sequence(target_type, target_id),
            action=action,
            snapshot_json=snapshot,
            policy_decision=policy_decision,
        )
        self.db.add(revision)
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def _restore_revision_target(self, revision: HermesRevision, snapshot: dict[str, Any]):
        if revision.target_type == "memory":
            memory = self.db.get(Memory, revision.target_id)
            if not memory:
                return None
            memory.content = str(snapshot.get("content") or "")
            memory.metadata_json = dict(snapshot.get("metadata_json") or {})
            self.db.commit()
            self.db.refresh(memory)
            return memory
        if revision.target_type == "skill":
            skill = self.db.get(Skill, revision.target_id)
            if not skill:
                return None
            skill.description = str(snapshot.get("description") or "")
            skill.prompt_template = str(snapshot.get("prompt_template") or "{input}")
            skill.usage_count = int(snapshot.get("usage_count", skill.usage_count) or 0)
            skill.metadata_json = dict(snapshot.get("metadata_json") or {})
            self.db.commit()
            self.db.refresh(skill)
            return skill
        return None

    def _restored_target_snapshot(self, target_type: str, target) -> dict[str, Any]:
        if target_type == "memory":
            return self._serialize_memory(target)
        if target_type == "skill":
            return self._serialize_skill(target)
        return {}

    def _next_revision_sequence(self, target_type: str, target_id: str) -> int:
        revisions = self.db.scalars(
            select(HermesRevision).where(
                HermesRevision.target_type == target_type,
                HermesRevision.target_id == target_id,
            )
        )
        return max((revision.sequence for revision in revisions), default=0) + 1

    def _target_snapshot(self, payload) -> dict[str, Any]:
        if payload.target_type == "memory":
            memory = self.db.get(Memory, payload.target_id)
            if not memory:
                return {}
            return {"content": memory.content, "metadata_json": dict(memory.metadata_json or {})}
        if payload.target_type == "skill":
            skill = self.db.get(Skill, payload.target_id)
            if not skill:
                return {}
            return {
                "description": skill.description,
                "prompt_template": skill.prompt_template,
                "usage_count": skill.usage_count,
                "metadata_json": dict(skill.metadata_json or {}),
            }
        return {}

    def _result_snapshot(self, payload, result: dict[str, Any]) -> dict[str, Any]:
        if payload.target_type == "workflow":
            created_memory = result.get("created_memory")
            return dict(created_memory) if isinstance(created_memory, dict) else {}
        if payload.target_type == "memory":
            updated_memory = result.get("updated_memory")
            return dict(updated_memory) if isinstance(updated_memory, dict) else {}
        if payload.target_type == "skill":
            updated_skill = result.get("updated_skill")
            return dict(updated_skill) if isinstance(updated_skill, dict) else {}
        return {}

    def _rollback_target(self, payload, snapshot: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        if payload.target_type == "workflow":
            created_memory = result.get("created_memory")
            memory_id = created_memory.get("id") if isinstance(created_memory, dict) else None
            if memory_id:
                memory = self.db.get(Memory, memory_id)
                if memory:
                    self.db.delete(memory)
                    self.db.commit()
            return {"rolled_back_id": memory_id} if memory_id else {}
        if payload.target_type == "memory" and snapshot:
            memory = self.db.get(Memory, payload.target_id)
            if memory:
                memory.content = snapshot["content"]
                memory.metadata_json = snapshot["metadata_json"]
                self.db.commit()
                self.db.refresh(memory)
                return self._serialize_memory(memory)
            return {}
        if payload.target_type == "skill" and snapshot:
            skill = self.db.get(Skill, payload.target_id)
            if skill:
                skill.description = snapshot["description"]
                skill.prompt_template = snapshot["prompt_template"]
                skill.usage_count = snapshot["usage_count"]
                skill.metadata_json = snapshot["metadata_json"]
                self.db.commit()
                self.db.refresh(skill)
                return self._serialize_skill(skill)
        return {}

    def _mark_applied(
        self,
        payload,
        evaluation_before: dict[str, Any],
        evaluation_after: dict[str, Any],
        baseline_run_id: str,
        candidate_run_id: str,
        comparison: dict[str, Any],
        policy_decision: dict[str, Any],
    ) -> None:
        suggestion = self._find_suggestion(
            user_id=payload.user_id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            suggestion_type=payload.suggestion_type,
        )
        if not suggestion:
            return
        suggestion.status = "blocked" if policy_decision.get("status") == "blocked" else "applied"
        suggestion.evaluation_before = evaluation_before
        suggestion.evaluation_after = evaluation_after
        suggestion.evaluation_delta = self._evaluation_delta(evaluation_before, evaluation_after)
        suggestion.baseline_evaluation_run_id = baseline_run_id
        suggestion.candidate_evaluation_run_id = candidate_run_id
        suggestion.evaluation_comparison = comparison
        suggestion.policy_decision = policy_decision
        suggestion.reviewed_by = payload.reviewed_by
        suggestion.reviewed_at = datetime.now(timezone.utc)
        self.db.commit()

    def policy_decision(self, comparison: dict[str, Any]) -> dict[str, Any]:
        aggregate_delta = comparison.get("aggregate_delta", {}) if isinstance(comparison, dict) else {}
        if not isinstance(aggregate_delta, dict):
            aggregate_delta = {}
        for key in ["completion_rate", "plan_completion_rate", "average_evidence_count"]:
            if float(aggregate_delta.get(key, 0) or 0) < 0:
                return {
                    "status": "blocked",
                    "reason": f"candidate evaluation regressed {key}",
                }
        review_signal_delta = aggregate_delta.get("review_signals", {})
        if isinstance(review_signal_delta, dict) and int(review_signal_delta.get("workflow_lesson", 0) or 0) > 0:
            return {
                "status": "blocked",
                "reason": "candidate evaluation increased workflow_lesson review signals",
            }
        case_deltas = comparison.get("case_deltas", []) if isinstance(comparison, dict) else []
        if isinstance(case_deltas, list):
            for item in case_deltas:
                if isinstance(item, dict) and item.get("status") == "regressed":
                    return {
                        "status": "blocked",
                        "reason": f"candidate evaluation regressed case {item.get('case_id') or 'unknown'}",
                    }
        return {
            "status": "allowed",
            "reason": "candidate evaluation did not regress",
        }

    def _evaluation_delta(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        before_signals = before.get("review_signal_counts", {}) if isinstance(before.get("review_signal_counts"), dict) else {}
        after_signals = after.get("review_signal_counts", {}) if isinstance(after.get("review_signal_counts"), dict) else {}
        return {
            "completion_rate": round(float(after.get("completion_rate", 0) or 0) - float(before.get("completion_rate", 0) or 0), 3),
            "plan_completion_rate": round(float(after.get("plan_completion_rate", 0) or 0) - float(before.get("plan_completion_rate", 0) or 0), 3),
            "average_evidence_count": round(float(after.get("average_evidence_count", 0) or 0) - float(before.get("average_evidence_count", 0) or 0), 3),
            "review_signals": {
                "skill": int(after_signals.get("skill", 0) or 0) - int(before_signals.get("skill", 0) or 0),
                "memory": int(after_signals.get("memory", 0) or 0) - int(before_signals.get("memory", 0) or 0),
                "workflow_lesson": int(after_signals.get("workflow_lesson", 0) or 0) - int(before_signals.get("workflow_lesson", 0) or 0),
                "plan": int(after_signals.get("plan", 0) or 0) - int(before_signals.get("plan", 0) or 0),
            },
        }

    def _apply_workflow(self, payload) -> dict[str, Any]:
        patch = dict(payload.proposed_patch or {})
        task_type = str(patch.get("task_type") or payload.target_id)
        lesson = str(patch.get("lesson") or f"Review {task_type} workflow before future runs.")
        memory = self.memory_service.create(MemoryCreate(
            user_id=payload.user_id,
            memory_type="workflow_lesson",
            content=lesson,
            metadata={
                "status": "draft",
                "source": "improvement_suggestion",
                "task_type": task_type,
                "suggestion_type": payload.suggestion_type,
                "target_id": payload.target_id,
                "reviewed_by": payload.reviewed_by,
                "suggestion_applied": True,
            },
        ))
        return {"status": "applied", "created_memory": self._serialize_memory(memory)}

    def _apply_memory(self, payload) -> dict[str, Any] | None:
        memory = self.memory_service.db.get(Memory, payload.target_id)
        if not memory:
            return None
        metadata = dict(memory.metadata_json or {})
        metadata.update({
            "suggestion_applied": True,
            "last_suggestion_type": payload.suggestion_type,
            "last_suggestion_patch": payload.proposed_patch,
            "reviewed_by": payload.reviewed_by,
        })
        updated = self.memory_service.update(memory.id, MemoryUpdate(content=memory.content, metadata=metadata))
        return {"status": "applied", "updated_memory": self._serialize_memory(updated)}

    def _apply_skill(self, payload) -> dict[str, Any] | None:
        skill = self.skill_service.get(payload.target_id)
        if not skill:
            return None
        metadata = dict(skill.metadata_json or {})
        metadata.update({
            "suggestion_applied": True,
            "last_suggestion_type": payload.suggestion_type,
            "last_suggestion_patch": payload.proposed_patch,
            "reviewed_by": payload.reviewed_by,
        })
        updated = self.skill_service.update(skill.id, SkillUpdate(
            description=skill.description,
            prompt_template=skill.prompt_template,
            metadata=metadata,
        ))
        return {"status": "applied", "updated_skill": self._serialize_skill(updated)}
