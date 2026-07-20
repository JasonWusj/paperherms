from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.db.models import Memory
from backend.schemas import MemoryCreate, MemoryUpdate
from rag.embeddings.embedding_client import build_embedding_client
from rag.vector_store.qdrant_client import (
    InMemoryVectorStoreClient,
    QdrantVectorStoreClient,
    VectorStoreClient,
)


_memory_vector_store = InMemoryVectorStoreClient()
REVIEW_STATUSES = {"draft", "active", "rejected", "archived"}


class MemoryService:
    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        embeddings=None,
        vector_store: VectorStoreClient | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.embeddings = embeddings
        self.vector_store = vector_store

    def create(self, payload: MemoryCreate) -> Memory:
        memory = Memory(
            user_id=payload.user_id,
            memory_type=payload.memory_type,
            content=payload.content,
            metadata_json=payload.metadata,
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def list(
        self,
        user_id: str | None = None,
        status: str | None = None,
        source_task_id: str | None = None,
    ) -> list[Memory]:
        statement = select(Memory).order_by(Memory.created_at.desc())
        if user_id:
            statement = statement.where(Memory.user_id == user_id)
        memories = list(self.db.scalars(statement))
        if status is not None:
            memories = [memory for memory in memories if self._status(memory) == status]
        if source_task_id is not None:
            memories = [
                memory
                for memory in memories
                if (memory.metadata_json or {}).get("source_task_id") == source_task_id
            ]
        return memories

    def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]:
        vector_results = self._search_by_vector(user_id, query, limit)
        if vector_results:
            return [memory for memory in vector_results if self._is_active(memory)]
        return self._search_by_keyword(user_id, query, limit)

    def _search_by_keyword(self, user_id: str, query: str, limit: int) -> list[Memory]:
        statement = (
            select(Memory)
            .where(Memory.user_id == user_id, Memory.content.ilike(f"%{query}%"))
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        return [memory for memory in self.db.scalars(statement) if self._is_active(memory)]

    def _search_by_vector(self, user_id: str, query: str, limit: int) -> list[Memory]:
        memories = [
            memory
            for memory in self.db.scalars(select(Memory).where(Memory.user_id == user_id))
            if self._is_active(memory)
        ]
        if not memories:
            return []
        try:
            payloads = [self._to_vector_payload(memory) for memory in memories]
            embeddings = self._get_embeddings()
            vector_store = self._get_vector_store()
            vectors = embeddings.embed_texts([payload["text"] for payload in payloads])
            vector_store.upsert_chunks(payloads, vectors)
            query_vector = embeddings.embed_text(query)
            retrieved = vector_store.search(
                query_vector,
                paper_id=self._memory_paper_id(user_id),
                limit=max(limit * 3, limit),
            )
        except Exception:
            return []
        by_id = {memory.id: memory for memory in memories}
        ordered = [by_id[chunk.id] for chunk in retrieved if chunk.id in by_id]
        return ordered[:limit]

    def _is_active(self, memory: Memory) -> bool:
        return self._status(memory) == "active"

    def _status(self, memory: Memory) -> str:
        return str((memory.metadata_json or {}).get("status", "active"))

    def update(self, memory_id: str, payload: MemoryUpdate) -> Memory | None:
        memory = self.db.get(Memory, memory_id)
        if not memory:
            return None
        changed_fields = []
        original_metadata = dict(memory.metadata_json or {})
        if payload.content is not None:
            if payload.content != memory.content:
                changed_fields.append("content")
            memory.content = payload.content
        if payload.metadata is not None:
            metadata = dict(payload.metadata)
            changed_fields.extend(self._metadata_changed_fields(original_metadata, metadata))
            if changed_fields:
                self._append_review_history(
                    metadata,
                    {
                        "action": "content_update",
                        "changed_fields": sorted(set(changed_fields)),
                        "reviewed_by": "default",
                    },
                )
            memory.metadata_json = metadata
        elif changed_fields:
            metadata = dict(memory.metadata_json or {})
            self._append_review_history(
                metadata,
                {
                    "action": "content_update",
                    "changed_fields": sorted(set(changed_fields)),
                    "reviewed_by": "default",
                },
            )
            memory.metadata_json = metadata
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def update_status(self, memory_id: str, status: str, reviewed_by: str = "default") -> Memory | None:
        if status not in REVIEW_STATUSES:
            raise ValueError(f"Unsupported review status: {status}")
        memory = self.db.get(Memory, memory_id)
        if not memory:
            return None
        metadata = dict(memory.metadata_json or {})
        previous_status = self._status(memory)
        self._append_review_history(
            metadata,
            {
                "action": "status_update",
                "from_status": previous_status,
                "to_status": status,
                "reviewed_by": reviewed_by,
            },
        )
        metadata.update({
            "status": status,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        })
        memory.metadata_json = metadata
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def delete(self, memory_id: str) -> bool:
        memory = self.db.get(Memory, memory_id)
        if not memory:
            return False
        self.db.delete(memory)
        self.db.commit()
        return True

    def _to_vector_payload(self, memory: Memory) -> dict:
        return {
            "id": memory.id,
            "paper_id": self._memory_paper_id(memory.user_id),
            "text": memory.content,
            "section_title": memory.memory_type,
            "metadata": {
                "user_id": memory.user_id,
                "memory_type": memory.memory_type,
                **(memory.metadata_json or {}),
            },
        }

    def _memory_paper_id(self, user_id: str) -> str:
        return f"memory:{user_id}"

    def _append_review_history(self, metadata: dict, entry: dict) -> None:
        history = list(metadata.get("review_history", []))
        timestamp = datetime.now(timezone.utc).isoformat()
        history.append({**entry, "reviewed_at": timestamp})
        metadata["review_history"] = history

    def _metadata_changed_fields(self, before: dict, after: dict) -> list[str]:
        fields = []
        for key in sorted(set(before) | set(after)):
            if key in {"review_history", "reviewed_at", "reviewed_by"}:
                continue
            if before.get(key) != after.get(key):
                fields.append(f"metadata.{key}")
        return fields

    def _get_embeddings(self):
        if self.embeddings is None:
            self.embeddings = build_embedding_client(
                provider=self.settings.embedding_provider,
                dimension=self.settings.embedding_dim,
                model_name=self.settings.embedding_model,
                device=self.settings.embedding_device,
                batch_size=self.settings.embedding_batch_size,
                max_length=self.settings.embedding_max_length,
            )
        return self.embeddings

    def _get_vector_store(self) -> VectorStoreClient:
        if self.vector_store is None:
            self.vector_store = self._build_vector_store()
        return self.vector_store

    def _build_vector_store(self) -> VectorStoreClient:
        if self.settings.app_env == "test":
            return _memory_vector_store
        try:
            return QdrantVectorStoreClient(
                url=self.settings.qdrant_url,
                collection_name=f"{self.settings.qdrant_collection}_memories",
                dimension=self.settings.embedding_dim,
            )
        except Exception:
            return _memory_vector_store
