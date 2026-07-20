from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PaperSectionRead(BaseModel):
    id: str
    title: str
    content: str
    level: int
    page_start: int | None = None
    page_end: int | None = None

    model_config = {"from_attributes": True}


class PaperChunkRead(BaseModel):
    id: str
    chunk_index: int
    text: str
    section_title: str
    page_start: int | None = None
    page_end: int | None = None

    model_config = {"from_attributes": True}


class PaperListRead(BaseModel):
    id: str
    title: str
    authors: list[str]
    abstract: str
    original_filename: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PaperRead(BaseModel):
    id: str
    title: str
    authors: list[str]
    abstract: str
    original_filename: str
    status: str
    created_at: datetime
    sections: list[PaperSectionRead] = []
    chunks: list[PaperChunkRead] = []

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class RetrievedChunkRead(BaseModel):
    id: str
    paper_id: str
    text: str
    section_title: str
    score: float
    page_start: int | None = None
    page_end: int | None = None


class PaperQuestionRequest(BaseModel):
    question: str
    user_id: str = "default"


class AgentAnswerRead(BaseModel):
    task_id: str
    answer: str
    citations: list[RetrievedChunkRead] = []
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    model_version: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class UserFeedbackCreate(BaseModel):
    """Create or replace explicit feedback for one completed task."""

    user_id: str = "default"
    rating: Literal[-1, 1]
    issue_tags: list[str] = Field(default_factory=list, max_length=10)
    comment: str = Field(default="", max_length=2000)


class UserFeedbackRead(BaseModel):
    id: str
    task_id: str
    user_id: str
    rating: int
    issue_tags: list[str]
    comment: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RewardEventRead(BaseModel):
    id: str
    task_id: str
    feedback_id: str | None
    user_id: str
    reward_type: str
    reward: float
    components: dict[str, Any]
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserFeedbackSubmissionRead(BaseModel):
    feedback: UserFeedbackRead
    reward: RewardEventRead


class MemoryCreate(BaseModel):
    user_id: str
    memory_type: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    content: str | None = None
    metadata: dict[str, Any] | None = None


class ReviewStatusUpdate(BaseModel):
    status: str
    reviewed_by: str = "default"


class MemoryRead(BaseModel):
    id: str
    user_id: str
    memory_type: str
    content: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemorySearchRequest(BaseModel):
    user_id: str
    query: str
    limit: int = Field(default=10, ge=1, le=50)


class SkillCreate(BaseModel):
    name: str
    description: str = ""
    prompt_template: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillUpdate(BaseModel):
    description: str | None = None
    prompt_template: str | None = None
    metadata: dict[str, Any] | None = None


class SkillRunRequest(BaseModel):
    input_text: str
    user_id: str = "default"
    paper_id: str | None = None


class SkillRead(BaseModel):
    id: str
    name: str
    description: str
    prompt_template: str
    usage_count: int
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentTaskCreate(BaseModel):
    task_type: str
    input_text: str
    user_id: str = "default"
    paper_id: str | None = None


class AgentTaskRead(BaseModel):
    id: str
    user_id: str
    paper_id: str | None
    task_type: str
    input_text: str
    output_text: str
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TraceRead(BaseModel):
    id: str
    task_id: str
    user_id: str
    agent_name: str
    step_name: str
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    retrieved_chunks: list[dict[str, Any]]
    latency_ms: int
    token_usage: dict[str, Any]
    error: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentTaskLearningRead(BaseModel):
    task_id: str
    learning_traces: list[TraceRead]
    memory_candidates: list[MemoryRead]
    skill_candidates: list[SkillRead]
    workflow_lesson_candidates: list[MemoryRead] = []
    workflow_lessons: list[dict[str, Any]] = []
    skill_outcome_summary: list[dict[str, Any]] = []
    skill_review_signals: list[dict[str, Any]] = []
    memory_outcome_summary: list[dict[str, Any]] = []
    memory_review_signals: list[dict[str, Any]] = []
    workflow_lesson_outcome_summary: list[dict[str, Any]] = []
    workflow_lesson_review_signals: list[dict[str, Any]] = []
    plan_outcome_summary: list[dict[str, Any]] = []
    plan_review_signals: list[dict[str, Any]] = []


class ImprovementSuggestionApply(BaseModel):
    user_id: str = "default"
    target_type: str
    target_id: str
    suggestion_type: str
    proposed_patch: dict[str, Any]
    reviewed_by: str = "default"


class ImprovementSuggestionReview(BaseModel):
    status: str
    reviewed_by: str = "default"


class ImprovementRevisionRollback(BaseModel):
    reviewed_by: str = "default"


class EvaluationRunCreate(BaseModel):
    user_id: str = "default"
    suite: str | None = None
    trigger: str = "manual"


class EvaluationCaseExtractRequest(BaseModel):
    user_id: str = "default"
    suite: str = "paperhermes-regression"
    limit: int = Field(default=20, ge=1, le=100)
