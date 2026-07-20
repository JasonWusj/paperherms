from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.db.models import AgentTask, Base, RewardEvent
from backend.services.bandit_service import BanditService


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_linucb_cold_start_rotates_actions_and_persists_updates() -> None:
    db = make_session()
    settings = Settings(policy_name="linucb", policy_min_samples=1, policy_epsilon=0.0)
    service = BanditService(db, settings)
    actions = []

    for index in range(3):
        task = AgentTask(
            user_id="demo",
            task_type="chat",
            input_text=f"question {index}",
            status="completed",
            output_text="answer",
        )
        db.add(task)
        db.commit()
        decision = service.choose(task)
        actions.append(decision["action"])
        service.record_decision(task, decision)
        event = RewardEvent(task_id=task.id, user_id="demo", reward_type="weak", reward=0.8, components={})
        db.add(event)
        db.commit()
        assert service.update_from_reward(task.id, event) is True

    assert actions == ["economy", "balanced", "deep"]
    summary = service.summary()
    assert summary["total_updates"] == 3
    assert sum(summary["counts"].values()) == 3
    replay = service.offline_replay()
    assert replay["sample_count"] == 3
    assert set(replay["policies"]) == {
        "fixed_economy",
        "fixed_balanced",
        "fixed_deep",
        "random",
        "logged_policy",
    }


def test_fixed_policy_is_backward_compatible() -> None:
    db = make_session()
    service = BanditService(db, Settings(policy_name="fixed"))
    task = AgentTask(user_id="demo", task_type="chat", input_text="hello")
    db.add(task)
    db.commit()

    decision = service.choose(task)

    assert decision["action"] == "balanced"
    assert decision["policy_name"] == "fixed"
    assert service.retrieval_limit("economy") == 3
    assert service.retrieval_limit("balanced") == 5
    assert service.retrieval_limit("deep") == 8
