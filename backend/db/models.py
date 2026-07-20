from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


JsonType = JSON().with_variant(JSONB, "postgresql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Paper(Base, TimestampMixin):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(500))
    authors: Mapped[list[str]] = mapped_column(JsonType, default=list)
    abstract: Mapped[str] = mapped_column(Text, default="")
    original_filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    raw_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="parsed")

    sections: Mapped[list["PaperSection"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["PaperChunk"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )


class PaperSection(Base, TimestampMixin):
    __tablename__ = "paper_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    level: Mapped[int] = mapped_column(Integer, default=1)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    paper: Mapped[Paper] = relationship(back_populates="sections")


class PaperChunk(Base, TimestampMixin):
    __tablename__ = "paper_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    section_title: Mapped[str] = mapped_column(String(255))
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    paper: Mapped[Paper] = relationship(back_populates="chunks")


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    memory_type: Mapped[str] = mapped_column(String(100), index=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    prompt_template: Mapped[str] = mapped_column(Text)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class AgentTask(Base, TimestampMixin):
    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(255), default="default")
    paper_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String(100))
    input_text: Mapped[str] = mapped_column(Text)
    output_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    traces: Mapped[list["AgentTrace"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(255), default="default")
    agent_name: Mapped[str] = mapped_column(String(255))
    step_name: Mapped[str] = mapped_column(String(255))
    input_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list)
    retrieved_chunks: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[AgentTask] = relationship(back_populates="traces")


class UserFeedback(Base, TimestampMixin):
    """Explicit human feedback attached to one agent execution.

    A user can revise their feedback, but there is only one current feedback
    record per task/user pair.  Keeping this separate from the task makes the
    reward pipeline auditable and prevents feedback from overwriting traces.
    """

    __tablename__ = "user_feedback"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_user_feedback_task_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(255), default="default", index=True)
    rating: Mapped[int] = mapped_column(Integer)
    issue_tags: Mapped[list[str]] = mapped_column(JsonType, default=list)
    comment: Mapped[str] = mapped_column(Text, default="")


class RewardEvent(Base):
    """A reproducible reward calculation, including its individual signals."""

    __tablename__ = "reward_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    feedback_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_feedback.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), default="default", index=True)
    reward_type: Mapped[str] = mapped_column(String(50), default="weak")
    reward: Mapped[float] = mapped_column(Float, default=0.0)
    components: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    source: Mapped[str] = mapped_column(String(100), default="automatic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PolicyDecision(Base):
    """The policy action selected for a task, persisted for offline replay."""

    __tablename__ = "policy_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(255), default="default", index=True)
    policy_name: Mapped[str] = mapped_column(String(100), default="fixed")
    policy_version: Mapped[str] = mapped_column(String(100), default="v1")
    action: Mapped[str] = mapped_column(String(100))
    context: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    action_scores: Mapped[dict[str, float]] = mapped_column(JsonType, default=dict)
    propensity: Mapped[float] = mapped_column(Float, default=1.0)
    exploration: Mapped[bool] = mapped_column(default=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelVersion(Base, TimestampMixin):
    """Metadata only; model weights stay outside the source repository."""

    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), index=True)
    base_model: Mapped[str] = mapped_column(String(500))
    adapter_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    stage: Mapped[str] = mapped_column(String(50), default="candidate")
    metrics: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    training_config: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class ImprovementSuggestion(Base, TimestampMixin):
    __tablename__ = "improvement_suggestions"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", "suggestion_type", name="uq_improvement_suggestion_target"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(255), default="default", index=True)
    target_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[str] = mapped_column(String(255), index=True)
    suggestion_type: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    proposed_patch: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    evaluation_before: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    evaluation_after: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    evaluation_delta: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    baseline_evaluation_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    candidate_evaluation_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    evaluation_comparison: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    policy_decision: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(255), default="default", index=True)
    evaluation_suite: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    trigger: Mapped[str] = mapped_column(String(100), default="manual", index=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class HermesRevision(Base, TimestampMixin):
    __tablename__ = "hermes_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(255), default="default", index=True)
    target_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[str] = mapped_column(String(255), index=True)
    suggestion_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    action: Mapped[str] = mapped_column(String(100), index=True)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    policy_decision: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
