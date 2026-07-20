from __future__ import annotations

from backend.db.models import Memory
from backend.services.memory_service import MemoryService


def search_memory(service: MemoryService, user_id: str, query: str, limit: int = 10) -> list[Memory]:
    return service.search(user_id, query, limit)
