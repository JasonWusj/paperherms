from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import AgentTask, AgentTrace, EvaluationRun
from backend.services.agent_service import PaperAgentService
from backend.services.integration_service import IntegrationNotificationService
from backend.services.trace_service import TraceService


class HermesEvaluationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trace_service = TraceService(db)

    def summarize(self, user_id: str | None = None, suite: str | None = None) -> dict[str, Any]:
        statement = select(AgentTask)
        if user_id is not None:
            statement = statement.where(AgentTask.user_id == user_id)
        if suite is not None:
            statement = statement.where(AgentTask.metadata_json["evaluation_suite"].as_string() == suite)
        tasks = list(self.db.scalars(statement))
        task_count = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.status == "completed")
        needs_review_tasks = sum(1 for task in tasks if task.status == "needs_review")
        task_type_summary = self._summarize_plan_outcomes(tasks) if suite is not None else self.trace_service.summarize_plan_outcomes(user_id=user_id)
        plan_uses = sum(item["uses"] for item in task_type_summary)
        plan_completed = sum(item["completed"] for item in task_type_summary)
        evidence_total = sum(item["average_evidence_count"] * item["uses"] for item in task_type_summary)
        payload = {
            "user_id": user_id,
            "task_count": task_count,
            "completed_tasks": completed_tasks,
            "needs_review_tasks": needs_review_tasks,
            "completion_rate": self._ratio(completed_tasks, task_count),
            "plan_completion_rate": self._ratio(plan_completed, plan_uses),
            "average_evidence_count": round(evidence_total / plan_uses, 3) if plan_uses else 0.0,
            "task_type_summary": task_type_summary,
            "review_signal_counts": {
                "skill": len(self.trace_service.skill_review_signals(user_id=user_id)),
                "memory": len(self.trace_service.memory_review_signals(user_id=user_id)),
                "workflow_lesson": len(self.trace_service.workflow_lesson_review_signals(user_id=user_id)),
                "plan": len(self.trace_service.plan_review_signals(user_id=user_id)),
            },
        }
        if suite is not None:
            payload["evaluation_suite"] = suite
            payload["case_summary"] = self._case_summary(tasks)
        return payload

    def create_run(self, user_id: str = "default", suite: str | None = None, trigger: str = "manual") -> dict[str, Any]:
        replay_summary = self._replay_suite_cases(user_id=user_id, suite=suite, trigger=trigger) if suite else None
        summary = self.summarize(user_id=user_id, suite=suite)
        if replay_summary is not None:
            summary["replay_summary"] = replay_summary
            self._apply_replay_aggregate(summary, replay_summary)
        run = EvaluationRun(
            user_id=user_id,
            evaluation_suite=suite,
            trigger=trigger,
            summary_json=summary,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        serialized = self._serialize_run(run)
        self._notify_evaluation_run_completed(serialized)
        return serialized

    def list_runs(self, user_id: str | None = None, suite: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        statement = select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(limit)
        if user_id is not None:
            statement = statement.where(EvaluationRun.user_id == user_id)
        if suite is not None:
            statement = statement.where(EvaluationRun.evaluation_suite == suite)
        return [self._serialize_run(run) for run in self.db.scalars(statement)]

    def compare_runs(self, baseline_run_id: str, candidate_run_id: str) -> dict[str, Any] | None:
        baseline = self.db.get(EvaluationRun, baseline_run_id)
        candidate = self.db.get(EvaluationRun, candidate_run_id)
        if not baseline or not candidate:
            return None
        baseline_summary = baseline.summary_json or {}
        candidate_summary = candidate.summary_json or {}
        return {
            "baseline_run_id": baseline.id,
            "candidate_run_id": candidate.id,
            "aggregate_delta": self._summary_delta(baseline_summary, candidate_summary),
            "case_deltas": self._case_deltas(baseline_summary, candidate_summary),
        }

    def extract_regression_cases(
        self,
        *,
        user_id: str = "default",
        suite: str = "paperhermes-regression",
        limit: int = 20,
    ) -> dict[str, Any]:
        statement = (
            select(AgentTask)
            .where(AgentTask.user_id == user_id)
            .order_by(AgentTask.updated_at.desc(), AgentTask.created_at.desc())
        )
        cases = []
        created_count = 0
        for task in self.db.scalars(statement):
            if len(cases) >= limit:
                break
            reason = self._regression_case_reason(task)
            if reason is None:
                continue
            metadata = dict(task.metadata_json or {})
            case_id = str(metadata.get("evaluation_case_id") or f"{task.task_type}-{task.id}")
            if metadata.get("evaluation_suite") == suite:
                cases.append({
                    "case_id": case_id,
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "source": metadata.get("evaluation_case_source") or "trace_failure",
                    "reason": "already in evaluation suite",
                })
                continue
            metadata.update({
                "evaluation_suite": suite,
                "evaluation_case_id": case_id,
                "evaluation_case_source": "trace_failure",
                "evaluation_case_reason": reason,
            })
            task.metadata_json = metadata
            created_count += 1
            cases.append({
                "case_id": case_id,
                "task_id": task.id,
                "task_type": task.task_type,
                "source": "trace_failure",
                "reason": reason,
            })
        if created_count:
            self.db.commit()
        return {
            "user_id": user_id,
            "evaluation_suite": suite,
            "created_count": created_count,
            "cases": cases,
        }

    def _serialize_run(self, run: EvaluationRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "user_id": run.user_id,
            "evaluation_suite": run.evaluation_suite,
            "trigger": run.trigger,
            "summary": run.summary_json,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        }

    def _notify_evaluation_run_completed(self, run: dict[str, Any]) -> None:
        try:
            IntegrationNotificationService().notify_evaluation_run_completed(run)
        except Exception:
            return

    def _summary_delta(self, baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        baseline_signals = baseline.get("review_signal_counts", {}) if isinstance(baseline.get("review_signal_counts"), dict) else {}
        candidate_signals = candidate.get("review_signal_counts", {}) if isinstance(candidate.get("review_signal_counts"), dict) else {}
        return {
            "completion_rate": round(float(candidate.get("completion_rate", 0) or 0) - float(baseline.get("completion_rate", 0) or 0), 3),
            "plan_completion_rate": round(float(candidate.get("plan_completion_rate", 0) or 0) - float(baseline.get("plan_completion_rate", 0) or 0), 3),
            "average_evidence_count": round(float(candidate.get("average_evidence_count", 0) or 0) - float(baseline.get("average_evidence_count", 0) or 0), 3),
            "review_signals": {
                "skill": int(candidate_signals.get("skill", 0) or 0) - int(baseline_signals.get("skill", 0) or 0),
                "memory": int(candidate_signals.get("memory", 0) or 0) - int(baseline_signals.get("memory", 0) or 0),
                "workflow_lesson": int(candidate_signals.get("workflow_lesson", 0) or 0) - int(baseline_signals.get("workflow_lesson", 0) or 0),
                "plan": int(candidate_signals.get("plan", 0) or 0) - int(baseline_signals.get("plan", 0) or 0),
            },
        }

    def _apply_replay_aggregate(self, summary: dict[str, Any], replay_summary: dict[str, Any]) -> None:
        tasks = self._tasks_for_replay_summary(replay_summary)
        task_count = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.status == "completed")
        needs_review_tasks = sum(1 for task in tasks if task.status == "needs_review")
        task_type_summary = self._summarize_plan_outcomes(tasks)
        plan_uses = sum(item["uses"] for item in task_type_summary)
        plan_completed = sum(item["completed"] for item in task_type_summary)
        evidence_total = sum(item["average_evidence_count"] * item["uses"] for item in task_type_summary)
        summary.update({
            "task_count": task_count,
            "completed_tasks": completed_tasks,
            "needs_review_tasks": needs_review_tasks,
            "completion_rate": self._ratio(completed_tasks, task_count),
            "plan_completion_rate": self._ratio(plan_completed, plan_uses),
            "average_evidence_count": round(evidence_total / plan_uses, 3) if plan_uses else 0.0,
            "task_type_summary": task_type_summary,
        })

    def _tasks_for_replay_summary(self, replay_summary: dict[str, Any]) -> list[AgentTask]:
        tasks = []
        for item in replay_summary.get("replayed_cases", []):
            if isinstance(item, dict) and item.get("replay_task_id"):
                task = self.db.get(AgentTask, str(item["replay_task_id"]))
                if task:
                    tasks.append(task)
        for item in replay_summary.get("skipped_cases", []):
            if isinstance(item, dict) and item.get("source_task_id"):
                task = self.db.get(AgentTask, str(item["source_task_id"]))
                if task:
                    tasks.append(task)
        return tasks

    def _case_deltas(self, baseline: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
        baseline_cases = self._cases_by_id(baseline)
        candidate_cases = self._cases_by_id(candidate)
        results = []
        for case_id in sorted(set(baseline_cases) | set(candidate_cases)):
            before = baseline_cases.get(case_id, {})
            after = candidate_cases.get(case_id, {})
            before_status = str(before.get("plan_status") or "missing")
            after_status = str(after.get("plan_status") or "missing")
            before_evidence = int(before.get("evidence_count", 0) or 0)
            after_evidence = int(after.get("evidence_count", 0) or 0)
            results.append({
                "case_id": case_id,
                "baseline_plan_status": before_status,
                "candidate_plan_status": after_status,
                "baseline_evidence_count": before_evidence,
                "candidate_evidence_count": after_evidence,
                "status": self._case_delta_status(before_status, after_status, before_evidence, after_evidence),
            })
        return results

    def _cases_by_id(self, summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        cases = summary.get("case_summary", [])
        if isinstance(cases, list):
            results.update({
                str(item.get("case_id")): item
                for item in cases
                if isinstance(item, dict) and item.get("case_id")
            })
        replay_summary = summary.get("replay_summary", {})
        replayed_cases = replay_summary.get("replayed_cases", []) if isinstance(replay_summary, dict) else []
        if not isinstance(replayed_cases, list):
            return results
        for item in replayed_cases:
            if not isinstance(item, dict) or not item.get("case_id") or not item.get("replay_task_id"):
                continue
            case_id = str(item["case_id"])
            replay_task = self.db.get(AgentTask, str(item["replay_task_id"]))
            if not replay_task:
                continue
            feedback = self._plan_feedback(replay_task.id) or {}
            results[case_id] = {
                **results.get(case_id, {}),
                "case_id": case_id,
                "task_id": replay_task.id,
                "task_type": replay_task.task_type,
                "plan_status": str(feedback.get("status") or "unknown"),
                "evidence_count": int(feedback.get("evidence_count", 0) or 0),
            }
        return results

    def _case_delta_status(self, before_status: str, after_status: str, before_evidence: int, after_evidence: int) -> str:
        if before_status != "completed" and after_status == "completed":
            return "improved"
        if before_status == "completed" and after_status != "completed":
            return "regressed"
        if after_evidence > before_evidence:
            return "improved"
        if after_evidence < before_evidence:
            return "regressed"
        return "unchanged"

    def _regression_case_reason(self, task: AgentTask) -> str | None:
        feedback = self._plan_feedback(task.id) or {}
        plan_status = str(feedback.get("status") or "")
        if plan_status == "incomplete":
            return "plan status incomplete"
        if task.status == "needs_review":
            return "task status needs_review"
        return None

    def _ratio(self, numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round(numerator / denominator, 3)

    def _summarize_plan_outcomes(self, tasks: list[AgentTask]) -> list[dict[str, Any]]:
        summary: dict[str, dict[str, Any]] = {}
        for task in tasks:
            feedback = self._plan_feedback(task.id)
            if feedback is None:
                continue
            item = summary.setdefault(task.task_type, {
                "task_type": task.task_type,
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

    def _case_summary(self, tasks: list[AgentTask]) -> list[dict[str, Any]]:
        cases = []
        for task in tasks:
            feedback = self._plan_feedback(task.id) or {}
            metadata = task.metadata_json or {}
            cases.append({
                "case_id": str(metadata.get("evaluation_case_id") or task.id),
                "task_id": task.id,
                "task_type": task.task_type,
                "input_text": task.input_text,
                "paper_id": task.paper_id,
                "source": str(metadata.get("evaluation_case_source") or "unknown"),
                "reason": str(metadata.get("evaluation_case_reason") or ""),
                "status": task.status,
                "plan_status": str(feedback.get("status") or "unknown"),
                "evidence_count": int(feedback.get("evidence_count", 0) or 0),
            })
        return sorted(cases, key=lambda item: item["case_id"])

    def _replay_suite_cases(self, *, user_id: str, suite: str, trigger: str) -> dict[str, Any]:
        statement = (
            select(AgentTask)
            .where(
                AgentTask.user_id == user_id,
                AgentTask.metadata_json["evaluation_suite"].as_string() == suite,
            )
            .order_by(AgentTask.created_at)
        )
        agent_service: PaperAgentService | None = None
        replayed_cases = []
        skipped_cases = []
        for task in self.db.scalars(statement):
            case_id = str((task.metadata_json or {}).get("evaluation_case_id") or task.id)
            skip_reason = self._case_replay_skip_reason(task)
            if skip_reason is not None:
                skipped_cases.append({
                    "case_id": case_id,
                    "source_task_id": task.id,
                    "task_type": task.task_type,
                    "replay_status": "skipped",
                    "reason": skip_reason,
                    **self._task_audit_fields(task),
                })
                continue

            if agent_service is None:
                agent_service = PaperAgentService(self.db)
            answer = self._replay_case(agent_service, task, user_id)
            replay_task = self.db.get(AgentTask, answer.task_id)
            if replay_task:
                replay_task.metadata_json = {
                    **(replay_task.metadata_json or {}),
                    "evaluation_replay_of_task_id": task.id,
                    "evaluation_replay_case_id": case_id,
                    "evaluation_replay_suite": suite,
                    "evaluation_replay_trigger": trigger,
                }
                self.db.commit()
            replayed_cases.append({
                "case_id": case_id,
                "source_task_id": task.id,
                "replay_task_id": answer.task_id,
                "task_type": task.task_type,
                "replay_status": "replayed",
                **self._task_audit_fields(replay_task),
            })
        return {
            "replayable_cases": len(replayed_cases),
            "replayed_cases": replayed_cases,
            "skipped_cases": skipped_cases,
        }

    def _case_replay_skip_reason(self, task: AgentTask) -> str | None:
        if not task.paper_id:
            return "missing paper_id"
        if not task.input_text:
            return "missing input_text"
        if task.task_type == "paper_question_answering":
            return None
        if task.task_type.startswith("paper_"):
            return None
        return "unsupported task_type"

    def _replay_case(self, agent_service: PaperAgentService, task: AgentTask, user_id: str):
        if task.task_type == "paper_question_answering":
            return agent_service.answer_question(task.paper_id or "", task.input_text, user_id=user_id)
        analysis_type = task.task_type.removeprefix("paper_")
        return agent_service.analyze(task.paper_id or "", analysis_type, user_id=user_id)

    def _task_audit_fields(self, task: AgentTask | None) -> dict[str, Any]:
        if not task:
            return {
                "task_status": "missing",
                "plan_status": "unknown",
                "evidence_count": 0,
            }
        feedback = self._plan_feedback(task.id) or {}
        return {
            "task_status": task.status,
            "plan_status": str(feedback.get("status") or "unknown"),
            "evidence_count": int(feedback.get("evidence_count", 0) or 0),
        }

    def _plan_feedback(self, task_id: str) -> dict[str, Any] | None:
        trace = self.db.scalar(
            select(AgentTrace)
            .where(
                AgentTrace.task_id == task_id,
                AgentTrace.agent_name == "ReflectionAgent",
                AgentTrace.step_name == "evaluate_execution",
            )
            .order_by(AgentTrace.created_at.desc())
        )
        if not trace:
            return None
        output = (trace.output_json or {}).get("output", {})
        if not isinstance(output, dict):
            return None
        feedback = output.get("plan_feedback", {})
        if not isinstance(feedback, dict):
            return None
        return feedback
