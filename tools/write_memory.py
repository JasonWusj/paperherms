from __future__ import annotations

from backend.db.models import Memory
from backend.schemas import MemoryCreate
from backend.services.memory_service import MemoryService


def write_memory(service: MemoryService, user_id: str, memory_type: str, content: str) -> Memory:
    return service.create(MemoryCreate(user_id=user_id, memory_type=memory_type, content=content))
