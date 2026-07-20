from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import AgentTask, AgentTrace


class TraceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_task(
        self,
        *,
        task_type: str,
        input_text: str,
        user_id: str = "default",
        paper_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentTask:
        task = AgentTask(
            task_type=task_type,
            input_text=input_text,
            user_id=user_id,
            paper_id=paper_id,
            metadata_json=metadata or {},
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def finish_task(self, task_id: str, output_text: str, status: str = "completed") -> AgentTask | None:
        task = self.db.get(AgentTask, task_id)
        if not task:
            return None
        task.output_text = output_text
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def record_step(
        self,
        *,
        task_id: str,
        user_id: str,
        agent_name: str,
        step_name: str,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        retrieved_chunks: list[dict[str, Any]] | None = None,
        latency_ms: int = 0,
        token_usage: dict[str, Any] | None = None,
        error: str | None = None,
        status: str = "success",
    ) -> AgentTrace:
        trace = AgentTrace(
            task_id=task_id,
            user_id=user_id,
            agent_name=agent_name,
            step_name=step_name,
            input_json=input_json or {},
            output_json=output_json or {},
            tool_calls=tool_calls or [],
            retrieved_chunks=retrieved_chunks or [],
            latency_ms=latency_ms,
            token_usage=token_usage or {},
            error=error,
            status=status,
        )
        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)
        return trace

    def get_task(self, task_id: str) -> AgentTask | None:
        return self.db.get(AgentTask, task_id)

    def list_tasks(self, limit: int = 20) -> list[AgentTask]:
        statement = select(AgentTask).order_by(AgentTask.updated_at.desc(), AgentTask.created_at.desc()).limit(limit)
        return list(self.db.scalars(statement))

    def list_trace(self, task_id: str) -> list[AgentTrace]:
        statement = select(AgentTrace).where(AgentTrace.task_id == task_id).order_by(AgentTrace.created_at)
        return list(self.db.scalars(statement))

    def summarize_skill_outcomes(self, user_id: str | None = None) -> list[dict[str, Any]]:
        statement = select(AgentTrace).where(
            AgentTrace.agent_name == "SkillManager",
            AgentTrace.step_name == "record_skill_outcomes",
        )
        if user_id is not None:
            statement = statement.where(AgentTrace.user_id == user_id)
        traces = self.db.scalars(statement)
        summary: dict[str, dict[str, Any]] = {}
        for trace in traces:
            output = (trace.output_json or {}).get("output", {})
            if not isinstance(output, dict):
                continue
            outcomes = output.get("skill_outcomes", [])
            if not isinstance(outcomes, list):
                continue
            for outcome in outcomes:
                if not isinstance(outcome, dict) or not outcome.get("skill_id"):
                    continue
                skill_id = str(outcome["skill_id"])
                item = summary.setdefault(skill_id, {
                    "skill_id": skill_id,
                    "uses": 0,
                    "helpful": 0,
                    "needs_review": 0,
                    "unknown": 0,
                    "confidence_total": 0.0,
                })
                item["uses"] += 1
                label = str(outcome.get("outcome") or "unknown")
                if label not in {"helpful", "needs_review"}:
                    label = "unknown"
                item[label] += 1
                item["confidence_total"] += float(outcome.get("reflection_confidence", 0) or 0)
        results = []
        for item in summary.values():
            uses = item["uses"] or 1
            results.append({
                "skill_id": item["skill_id"],
                "uses": item["uses"],
                "helpful": item["helpful"],
                "needs_review": item["needs_review"],
                "unknown": item["unknown"],
                "average_reflection_confidence": round(item["confidence_total"] / uses, 3),
            })
        return sorted(results, key=lambda item: item["skill_id"])

    def skill_review_signals(self, user_id: str | None = None) -> list[dict[str, Any]]:
        signals = []
        for item in self.summarize_skill_outcomes(user_id=user_id):
            if item["uses"] >= 3 and item["needs_review"] > item["helpful"]:
                signals.append({
                    "skill_id": item["skill_id"],
                    "signal": "review_recommended",
                    "reason": f"needs_review outcomes exceed helpful outcomes after {item['uses']} uses",
                    "uses": item["uses"],
                    "helpful": item["helpful"],
                    "needs_review": item["needs_review"],
                })
        return signals

    def summarize_memory_outcomes(self, user_id: str | None = None) -> list[dict[str, Any]]:
        statement = select(AgentTrace).where(
            AgentTrace.agent_name == "ReflectionAgent",
            AgentTrace.step_name == "evaluate_execution",
        )
        if user_id is not None:
            statement = statement.where(AgentTrace.user_id == user_id)
        summary: dict[str, dict[str, Any]] = {}
        for trace in self.db.scalars(statement):
            output = (trace.output_json or {}).get("output", {})
            if not isinstance(output, dict):
                continue
            feedback = output.get("memory_feedback", [])
            if not isinstance(feedback, list):
                continue
            for item in feedback:
                if not isinstance(item, dict) or not item.get("memory_id"):
                    continue
                memory_id = str(item["memory_id"])
                summary_item = summary.setdefault(memory_id, {
                    "memory_id": memory_id,
                    "uses": 0,
                    "used": 0,
                    "needs_review": 0,
                    "unknown": 0,
                })
                summary_item["uses"] += 1
                label = str(item.get("status") or "unknown")
                if label not in {"used", "needs_review"}:
                    label = "unknown"
                summary_item[label] += 1
        return sorted(summary.values(), key=lambda item: item["memory_id"])

    def memory_review_signals(self, user_id: str | None = None) -> list[dict[str, Any]]:
        signals = []
        for item in self.summarize_memory_outcomes(user_id=user_id):
            if item["uses"] >= 3 and item["needs_review"] > item["used"]:
                signals.append({
                    "memory_id": item["memory_id"],
                    "signal": "review_recommended",
                    "reason": f"needs_review outcomes exceed used outcomes after {item['uses']} uses",
                    "uses": item["uses"],
                    "used": item["used"],
                    "needs_review": item["needs_review"],
                })
        return signals

    def summarize_workflow_lesson_outcomes(self, user_id: str | None = None) -> list[dict[str, Any]]:
        statement = select(AgentTrace).where(
            AgentTrace.agent_name == "ReflectionAgent",
            AgentTrace.step_name == "evaluate_execution",
        )
        if user_id is not None:
            statement = statement.where(AgentTrace.user_id == user_id)
        summary: dict[str, dict[str, Any]] = {}
        for trace in self.db.scalars(statement):
            output = (trace.output_json or {}).get("output", {})
            if not isinstance(output, dict):
                continue
            feedback = output.get("workflow_lesson_feedback", [])
            if not isinstance(feedback, list):
                continue
            for item in feedback:
                if not isinstance(item, dict) or not item.get("lesson_id"):
                    continue
                lesson_id = str(item["lesson_id"])
                summary_item = summary.setdefault(lesson_id, {
                    "lesson_id": lesson_id,
                    "uses": 0,
                    "applied": 0,
                    "needs_review": 0,
                    "unknown": 0,
                })
                summary_item["uses"] += 1
                label = str(item.get("status") or "unknown")
                if label not in {"applied", "needs_review"}:
                    label = "unknown"
                summary_item[label] += 1
        return sorted(summary.values(), key=lambda item: item["lesson_id"])

    def workflow_lesson_review_signals(self, user_id: str | None = None) -> list[dict[str, Any]]:
        signals = []
        for item in self.summarize_workflow_lesson_outcomes(user_id=user_id):
            if item["uses"] >= 3 and item["needs_review"] > item["applied"]:
                signals.append({
                    "lesson_id": item["lesson_id"],
                    "signal": "review_recommended",
                    "reason": f"needs_review outcomes exceed applied outcomes after {item['uses']} uses",
                    "uses": item["uses"],
                    "applied": item["applied"],
                    "needs_review": item["needs_review"],
                })
        return signals

    def summarize_plan_outcomes(self, user_id: str | None = None) -> list[dict[str, Any]]:
        statement = select(AgentTrace).where(
            AgentTrace.agent_name == "ReflectionAgent",
            AgentTrace.step_name == "evaluate_execution",
        )
        if user_id is not None:
            statement = statement.where(AgentTrace.user_id == user_id)
        summary: dict[str, dict[str, Any]] = {}
        for trace in self.db.scalars(statement):
            output = (trace.output_json or {}).get("output", {})
            if not isinstance(output, dict):
                continue
            feedback = output.get("plan_feedback")
            if not isinstance(feedback, dict):
                continue
            task = self.get_task(trace.task_id)
            if not task:
                continue
            task_type = task.task_type
            item = summary.setdefault(task_type, {
                "task_type": task_type,
                "uses": 0,
                "completed": 0,
                "incomplete": 0,
                "unknown": 0,
                "evidence_total": 0.0,
            })
            item["uses"] += 1
            status = str(feedback.get("status") or "unknown")
            if status not in {"completed", "incomplete"}:
                status = "unknown"
            item[status] += 1
            item["evidence_total"] += float(feedback.get("evidence_count", 0) or 0)
        results = []
        for item in summary.values():
            uses = item["uses"] or 1
            results.append({
                "task_type": item["task_type"],
                "uses": item["uses"],
                "completed": item["completed"],
                "incomplete": item["incomplete"],
                "unknown": item["unknown"],
                "average_evidence_count": round(item["evidence_total"] / uses, 3),
            })
        return sorted(results, key=lambda item: item["task_type"])

    def plan_review_signals(self, user_id: str | None = None) -> list[dict[str, Any]]:
        signals = []
        for item in self.summarize_plan_outcomes(user_id=user_id):
            if item["uses"] >= 3 and item["incomplete"] > item["completed"]:
                signals.append({
                    "task_type": item["task_type"],
                    "signal": "review_recommended",
                    "reason": f"incomplete plan outcomes exceed completed outcomes after {item['uses']} uses",
                    "uses": item["uses"],
                    "completed": item["completed"],
                    "incomplete": item["incomplete"],
                })
        return signals
