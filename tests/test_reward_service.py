from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.db.models import AgentTask, AgentTrace, Base, RewardEvent, UserFeedback
from backend.schemas import UserFeedbackCreate
from backend.services.reward_service import RewardService


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def make_completed_task(db: Session) -> AgentTask:
    task = AgentTask(
        user_id="demo",
        task_type="paper_question_answering",
        input_text="What is the method?",
        output_text="The method uses attention with evidence from the Method section.",
        status="completed",
    )
    db.add(task)
    db.flush()
    db.add(
        AgentTrace(
            task_id=task.id,
            user_id="demo",
            agent_name="ReflectionAgent",
            step_name="check_answer_grounding",
            output_json={"output": {"status": "checked", "confidence": 0.8, "evidence_count": 3}},
            retrieved_chunks=[{"id": "a"}, {"id": "b"}, {"id": "c"}],
            latency_ms=500,
            token_usage={"total_tokens": 600},
        )
    )
    db.commit()
    db.refresh(task)
    return task


def test_human_feedback_replaces_current_feedback_and_creates_final_rewards() -> None:
    db = make_session()
    task = make_completed_task(db)
    service = RewardService(db)

    weak = service.record_weak_reward(task)
    positive, positive_reward = service.upsert_feedback(
        task,
        UserFeedbackCreate(user_id="demo", rating=1),
    )
    negative, negative_reward = service.upsert_feedback(
        task,
        UserFeedbackCreate(user_id="demo", rating=-1, issue_tags=["citation_error"]),
    )

    assert positive.id == negative.id
    assert negative.rating == -1
    assert positive_reward.reward > weak.reward
    assert negative_reward.reward < positive_reward.reward
    assert negative_reward.components["weak_reward"] is False
    assert db.scalar(select(func.count()).select_from(UserFeedback)) == 1
    assert db.scalar(select(func.count()).select_from(RewardEvent)) == 3


def test_weak_reward_is_idempotent() -> None:
    db = make_session()
    task = make_completed_task(db)
    service = RewardService(db)

    first = service.record_weak_reward(task)
    second = service.record_weak_reward(task)

    assert first.id == second.id
    assert db.scalar(select(func.count()).select_from(RewardEvent)) == 1
