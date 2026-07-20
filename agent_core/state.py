from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


class PaperAgentState(TypedDict, total=False):
    # Inputs
    user_input: str
    paper_id: str
    user_id: str
    task_id: str
    task_type: str  # summary / method / experiments / novelty / limitations / chat / compare / related_work
    strategy: str
    retrieval_limit: int

    # Intermediate state. Annotated lists support LangGraph fan-in merging.
    memories: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    selected_skills: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    planned_steps: list[str]
    agent_outputs: Annotated[list[dict[str, Any]], add]
    reflection: dict[str, Any]
    execution_feedback: dict[str, Any]
    learning: dict[str, Any]
    memory_candidates: list[dict[str, Any]]
    skill_candidates: list[dict[str, Any]]
    active_workflow_lessons: list[dict[str, Any]]
    workflow_lessons: list[dict[str, Any]]
    skill_outcomes: list[dict[str, Any]]
    trace_steps: Annotated[list[dict[str, Any]], add]

    # Outputs
    final_answer: str
    citations: list[dict[str, Any]]
