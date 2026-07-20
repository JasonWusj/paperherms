from __future__ import annotations

from typing import Any

from rag.embeddings.embedding_client import EmbeddingClient
from rag.models import PaperChunk, RetrievedChunk
from rag.retrievers.reranker import PaperReranker
from rag.vector_store.qdrant_client import VectorStoreClient


class PaperRetriever:
    def __init__(
        self,
        embeddings: EmbeddingClient,
        vector_store: VectorStoreClient,
        reranker: PaperReranker | None = None,
    ) -> None:
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.reranker = reranker or PaperReranker()

    def index_chunks(self, chunks: list[PaperChunk | dict[str, Any]]) -> None:
        payloads = [self._to_payload(chunk) for chunk in chunks]
        vectors = self.embeddings.embed_texts([payload["text"] for payload in payloads])
        self.vector_store.upsert_chunks(payloads, vectors)

    def search(self, query: str, *, paper_id: str | None = None, limit: int = 5) -> list[RetrievedChunk]:
        vector = self.embeddings.embed_text(query)
        candidate_limit = max(limit * 4, limit)
        candidates = self.vector_store.search(vector, paper_id=paper_id, limit=candidate_limit)
        return self.reranker.rerank(query, candidates, limit=limit)

    def _to_payload(self, chunk: PaperChunk | dict[str, Any]) -> dict[str, Any]:
        if isinstance(chunk, PaperChunk):
            return {
                "id": chunk.id,
                "paper_id": chunk.paper_id,
                "text": chunk.text,
                "section_title": chunk.section_title,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "metadata": chunk.metadata,
            }
        return dict(chunk)
