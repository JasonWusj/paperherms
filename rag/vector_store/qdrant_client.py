from __future__ import annotations

import math
from typing import Any, Protocol

from rag.models import RetrievedChunk


class VectorStoreClient(Protocol):
    def upsert_chunks(self, chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
        ...

    def search(
        self,
        vector: list[float],
        *,
        paper_id: str | None = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        ...


class InMemoryVectorStoreClient:
    def __init__(self) -> None:
        self._points: list[tuple[dict[str, Any], list[float]]] = []

    def upsert_chunks(self, chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
        by_id = {point[0]["id"]: point for point in self._points}
        for chunk, vector in zip(chunks, vectors, strict=True):
            by_id[chunk["id"]] = (chunk, vector)
        self._points = list(by_id.values())

    def search(
        self,
        vector: list[float],
        *,
        paper_id: str | None = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        scored: list[tuple[float, dict[str, Any]]] = []
        for payload, stored_vector in self._points:
            if paper_id and payload.get("paper_id") != paper_id:
                continue
            scored.append((self._cosine(vector, stored_vector), payload))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedChunk(
                id=payload["id"],
                paper_id=payload["paper_id"],
                text=payload["text"],
                section_title=payload.get("section_title", "Unknown"),
                page_start=payload.get("page_start"),
                page_end=payload.get("page_end"),
                score=score,
                metadata=payload.get("metadata", {}),
            )
            for score, payload in scored[:limit]
        ]

    def _cosine(self, left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)


class QdrantVectorStoreClient:
    def __init__(self, url: str, collection_name: str, dimension: int) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import Distance, VectorParams

        self.collection_name = collection_name
        self.client = QdrantClient(url=url)
        existing = {collection.name for collection in self.client.get_collections().collections}
        if collection_name not in existing:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )

    def upsert_chunks(self, chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
        from qdrant_client.http.models import PointStruct

        points = [
            PointStruct(id=chunk["id"], vector=vector, payload=chunk)
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(
        self,
        vector: list[float],
        *,
        paper_id: str | None = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        query_filter = None
        if paper_id:
            query_filter = Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            )
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=query_filter,
                limit=limit,
            )
            points = response.points
        else:
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
            )
        results: list[RetrievedChunk] = []
        for point in points:
            payload = point.payload or {}
            results.append(
                RetrievedChunk(
                    id=str(payload["id"]),
                    paper_id=str(payload["paper_id"]),
                    text=str(payload["text"]),
                    section_title=str(payload.get("section_title", "Unknown")),
                    page_start=payload.get("page_start"),
                    page_end=payload.get("page_end"),
                    score=float(point.score),
                    metadata=dict(payload.get("metadata", {})),
                )
            )
        return results
