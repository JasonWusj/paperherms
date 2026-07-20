# backend/services/agent_service.py
from __future__ import annotations

from sqlalchemy.orm.session import Session

from agent_core.graph import build_paper_graph
from agent_core.llm import PaperHermesLLM
from backend.config import get_settings
from backend.schemas import AgentAnswerRead, RetrievedChunkRead
from backend.services.memory_service import MemoryService
from backend.services.paper_service import PaperService
from backend.services.reward_service import RewardService
from backend.services.skill_service import SkillService
from backend.services.trace_service import TraceService
from rag.retrievers.langchain_retriever import PaperHermesRetriever


class PaperAgentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.paper_service = PaperService(db)
        self.trace_service = TraceService(db)
        self.memory_service = MemoryService(db)
        self.skill_service = SkillService(db)
        self.reward_service = RewardService(db)
        self.llm = PaperHermesLLM(
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            api_style=self.settings.llm_api_style,
        )

    def answer_question(self, paper_id: str, question: str, user_id: str = "default") -> AgentAnswerRead:
        task = self.trace_service.create_task(
            task_type="paper_question_answering",
            input_text=question,
            user_id=user_id,
            paper_id=paper_id,
        )
        self.paper_service.search(paper_id, question, limit=1)
        retriever = PaperHermesRetriever(
            paper_retriever=self.paper_service.retriever, paper_id=paper_id
        )
        graph = build_paper_graph(
            llm=self.llm,
            retriever=retriever,
            memory_service=self.memory_service,
            skill_service=self.skill_service,
            trace_service=self.trace_service,
        )
        state = graph.invoke({
            "user_input": question,
            "paper_id": paper_id,
            "user_id": user_id,
            "task_id": task.id,
            "task_type": "chat",
        })
        # Record trace steps from graph state
        for step in state.get("trace_steps", []):
            self.trace_service.record_step(
                task_id=task.id,
                user_id=user_id,
                agent_name=step.get("agent_name", "Unknown"),
                step_name=step.get("step_name", "unknown"),
                output_json={"output": step.get("output", "")},
                retrieved_chunks=step.get("retrieved_chunks", []),
            )
        self.trace_service.finish_task(task.id, state.get("final_answer", ""))
        self.reward_service.record_weak_reward(self.trace_service.get_task(task.id) or task)
        citations_raw = state.get("citations", state.get("chunks", []))
        return AgentAnswerRead(
            task_id=task.id,
            answer=state.get("final_answer", ""),
            citations=[RetrievedChunkRead(**c) for c in citations_raw if isinstance(c, dict)],
        )

    def analyze(self, paper_id: str, analysis_type: str, user_id: str = "default") -> AgentAnswerRead:
        task = self.trace_service.create_task(
            task_type=f"paper_{analysis_type}",
            input_text=analysis_type,
            user_id=user_id,
            paper_id=paper_id,
        )
        self.paper_service.search(paper_id, analysis_type, limit=1)
        retriever = PaperHermesRetriever(
            paper_retriever=self.paper_service.retriever, paper_id=paper_id
        )
        graph = build_paper_graph(
            llm=self.llm,
            retriever=retriever,
            memory_service=self.memory_service,
            skill_service=self.skill_service,
            trace_service=self.trace_service,
        )
        state = graph.invoke({
            "user_input": analysis_type,
            "paper_id": paper_id,
            "user_id": user_id,
            "task_id": task.id,
            "task_type": analysis_type,
        })
        for step in state.get("trace_steps", []):
            self.trace_service.record_step(
                task_id=task.id,
                user_id=user_id,
                agent_name=step.get("agent_name", "Unknown"),
                step_name=step.get("step_name", "unknown"),
                output_json={"output": step.get("output", "")},
                retrieved_chunks=step.get("retrieved_chunks", []),
            )
        self.trace_service.finish_task(task.id, state.get("final_answer", ""))
        self.reward_service.record_weak_reward(self.trace_service.get_task(task.id) or task)
        citations_raw = state.get("citations", state.get("chunks", []))
        return AgentAnswerRead(
            task_id=task.id,
            answer=state.get("final_answer", ""),
            citations=[RetrievedChunkRead(**c) for c in citations_raw if isinstance(c, dict)],
        )
