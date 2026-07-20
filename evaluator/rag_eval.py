from __future__ import annotations

from rag.models import RetrievedChunk


def citation_coverage(answer: str, chunks: list[RetrievedChunk]) -> float:
    if not answer.strip():
        return 0.0
    cited = sum(1 for chunk in chunks if chunk.section_title.lower() in answer.lower())
    return cited / max(len(chunks), 1)
