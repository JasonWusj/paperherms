from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas import (
    AgentTaskCreate,
    AgentTaskLearningRead,
    AgentTaskRead,
    EvaluationCaseExtractRequest,
    EvaluationRunCreate,
    ImprovementRevisionRollback,
    ImprovementSuggestionApply,
    ImprovementSuggestionReview,
    TraceRead,
)
from backend.services.memory_service import MemoryService
from backend.services.skill_service import SkillService
from backend.services.agent_service import PaperAgentService
from backend.services.evaluation_service import HermesEvaluationService
from backend.services.improvement_service import HermesImprovementService
from backend.services.trace_service import TraceService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/tasks", response_model=AgentTaskRead)
def create_agent_task(payload: AgentTaskCreate, db: Session = Depends(get_db)):
    if payload.paper_id:
        result = PaperAgentService(db).analyze(payload.paper_id, payload.task_type, payload.user_id)
        task = TraceService(db).get_task(result.task_id)
        if task:
            return task
    return TraceService(db).create_task(
        task_type=payload.task_type,
        input_text=payload.input_text,
        user_id=payload.user_id,
        paper_id=payload.paper_id,
    )


@router.get("/tasks", response_model=list[AgentTaskRead])
def list_agent_tasks(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    return TraceService(db).list_tasks(limit=limit)


@router.get("/evaluation")
def get_agent_evaluation(
    user_id: str | None = None,
    suite: str | None = None,
    db: Session = Depends(get_db),
):
    return HermesEvaluationService(db).summarize(user_id=user_id, suite=suite)


@router.post("/evaluation-runs")
def create_agent_evaluation_run(payload: EvaluationRunCreate, db: Session = Depends(get_db)):
    return HermesEvaluationService(db).create_run(
        user_id=payload.user_id,
        suite=payload.suite,
        trigger=payload.trigger,
    )


@router.get("/evaluation-runs")
def list_agent_evaluation_runs(
    user_id: str | None = None,
    suite: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return HermesEvaluationService(db).list_runs(user_id=user_id, suite=suite, limit=limit)


@router.get("/evaluation-runs/compare")
def compare_agent_evaluation_runs(
    baseline_run_id: str,
    candidate_run_id: str,
    db: Session = Depends(get_db),
):
    result = HermesEvaluationService(db).compare_runs(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return result


@router.post("/evaluation-cases/extract")
def extract_agent_evaluation_cases(payload: EvaluationCaseExtractRequest, db: Session = Depends(get_db)):
    return HermesEvaluationService(db).extract_regression_cases(
        user_id=payload.user_id,
        suite=payload.suite,
        limit=payload.limit,
    )


@router.get("/improvement-suggestions")
def get_agent_improvement_suggestions(user_id: str | None = None, db: Session = Depends(get_db)):
    return HermesImprovementService(db).suggestions(user_id=user_id)


@router.get("/improvement-revisions")
def get_agent_improvement_revisions(target_type: str, target_id: str, db: Session = Depends(get_db)):
    return HermesImprovementService(db).list_revisions(target_type=target_type, target_id=target_id)


@router.post("/improvement-revisions/{revision_id}/rollback")
def rollback_agent_improvement_revision(
    revision_id: str,
    payload: ImprovementRevisionRollback,
    db: Session = Depends(get_db),
):
    result = HermesImprovementService(db).rollback_revision(revision_id, reviewed_by=payload.reviewed_by)
    if result is None:
        raise HTTPException(status_code=404, detail="Revision not found or unsupported rollback target")
    return result


@router.post("/improvement-suggestions/apply")
def apply_agent_improvement_suggestion(payload: ImprovementSuggestionApply, db: Session = Depends(get_db)):
    result = HermesImprovementService(db).apply(payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Suggestion target not found")
    return result


@router.post("/improvement-suggestions/{suggestion_id}/review")
def review_agent_improvement_suggestion(
    suggestion_id: str,
    payload: ImprovementSuggestionReview,
    db: Session = Depends(get_db),
):
    result = HermesImprovementService(db).review(suggestion_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Suggestion not found or unsupported review status")
    return result


@router.get("/tasks/{task_id}", response_model=AgentTaskRead)
def get_agent_task(task_id: str, db: Session = Depends(get_db)):
    task = TraceService(db).get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks/{task_id}/trace", response_model=list[TraceRead])
def get_agent_trace(task_id: str, db: Session = Depends(get_db)):
    return TraceService(db).list_trace(task_id)


@router.get("/tasks/{task_id}/learning", response_model=AgentTaskLearningRead)
def get_agent_learning(task_id: str, db: Session = Depends(get_db)):
    trace_service = TraceService(db)
    task = trace_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    learning_traces = [
        trace
        for trace in trace_service.list_trace(task_id)
        if trace.agent_name == "LearningAgent"
    ]
    workflow_lessons = []
    for trace in learning_traces:
        output = trace.output_json.get("output", "") if trace.output_json else ""
        if isinstance(output, str):
            try:
                import json

                parsed = json.loads(output)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(parsed, dict):
                workflow_lessons.extend(parsed.get("workflow_lessons", []))

    memory_candidates = MemoryService(db).list(source_task_id=task_id)
    return {
        "task_id": task_id,
        "learning_traces": learning_traces,
        "memory_candidates": memory_candidates,
        "skill_candidates": SkillService(db).list(source_task_id=task_id),
        "workflow_lesson_candidates": [
            memory for memory in memory_candidates if memory.memory_type == "workflow_lesson"
        ],
        "workflow_lessons": workflow_lessons,
        "skill_outcome_summary": trace_service.summarize_skill_outcomes(user_id=task.user_id),
        "skill_review_signals": trace_service.skill_review_signals(user_id=task.user_id),
        "memory_outcome_summary": trace_service.summarize_memory_outcomes(user_id=task.user_id),
        "memory_review_signals": trace_service.memory_review_signals(user_id=task.user_id),
        "workflow_lesson_outcome_summary": trace_service.summarize_workflow_lesson_outcomes(user_id=task.user_id),
        "workflow_lesson_review_signals": trace_service.workflow_lesson_review_signals(user_id=task.user_id),
        "plan_outcome_summary": trace_service.summarize_plan_outcomes(user_id=task.user_id),
        "plan_review_signals": trace_service.plan_review_signals(user_id=task.user_id),
    }


@router.post("/tasks/{task_id}/reflect")
def reflect_agent_task(task_id: str, db: Session = Depends(get_db)):
    service = TraceService(db)
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    service.record_step(
        task_id=task_id,
        user_id=task.user_id,
        agent_name="ReflectionAgent",
        step_name="manual_reflection",
        input_json={"task_id": task_id},
        output_json={"status": "recorded"},
    )
    return {"task_id": task_id, "status": "reflection_recorded"}
