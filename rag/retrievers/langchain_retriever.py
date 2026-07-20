from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


class PaperHermesRetriever(BaseRetriever):
    """LangChain-compatible retriever wrapping the existing PaperRetriever."""

    paper_retriever: Any
    paper_id: str
    limit: int = 5

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        chunks = self.paper_retriever.search(query, paper_id=self.paper_id, limit=self.limit)
        return [
            Document(
                page_content=chunk.text,
                metadata={
                    "chunk_id": chunk.id,
                    "paper_id": chunk.paper_id,
                    "section_title": chunk.section_title,
                    "score": chunk.score,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                },
            )
            for chunk in chunks
        ]
