"""Reusable PaperHermes tools."""
from __future__ import annotations

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from rag.models import RetrievedChunk


class _ChunkRetriever(BaseRetriever):
    """Thin retriever that returns pre-existing chunks."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stored_chunks: list[RetrievedChunk]

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
        **kwargs,
    ) -> list[Document]:
        return [
            Document(
                page_content=c.text,
                metadata={
                    "chunk_id": c.id,
                    "paper_id": c.paper_id,
                    "section_title": c.section_title,
                    "score": c.score,
                },
            )
            for c in self.stored_chunks
        ]


class _NoOpMemoryService:
    def search(self, user_id, query, limit=3):
        return []

    def create(self, payload):
        pass


class _NoOpTraceService:
    pass


def run_analysis(task_type: str, chunks: list[RetrievedChunk]) -> str:
    """Run a paper-analysis graph task with pre-retrieved chunks.

    This replaces the old ``PaperCoordinatorAgent().run(...)`` calls.
    Imports are deferred to avoid circular import with agent_core.llm.
    """
    from agent_core.graph import build_paper_graph  # noqa: E402
    from agent_core.llm import PaperHermesLLM  # noqa: E402

    llm = PaperHermesLLM(provider="stub")
    retriever = _ChunkRetriever(stored_chunks=chunks)
    graph = build_paper_graph(
        llm=llm,
        retriever=retriever,
        memory_service=_NoOpMemoryService(),
        trace_service=_NoOpTraceService(),
    )
    state = graph.invoke({
        "user_input": task_type,
        "paper_id": chunks[0].paper_id if chunks else "",
        "user_id": "tool",
        "task_type": task_type,
    })
    return state.get("final_answer", "")
