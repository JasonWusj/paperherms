from __future__ import annotations

from backend.db.models import Memory


def memory_precision(memories: list[Memory], min_chars: int = 20) -> float:
    if not memories:
        return 0.0
    useful = sum(1 for memory in memories if len(memory.content.strip()) >= min_chars)
    return useful / len(memories)
