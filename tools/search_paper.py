from __future__ import annotations

from rag.models import RetrievedChunk
from rag.retrievers.paper_retriever import PaperRetriever


def search_paper(retriever: PaperRetriever, query: str, paper_id: str | None = None, limit: int = 5) -> list[RetrievedChunk]:
    return retriever.search(query, paper_id=paper_id, limit=limit)
