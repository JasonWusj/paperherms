from __future__ import annotations

from rag.models import PaperMetadata


def generate_related_work(metadata_items: list[PaperMetadata]) -> str:
    lines = [f"- {item.title}: {item.abstract[:240]}" for item in metadata_items]
    return "Related work draft inputs:\n" + "\n".join(lines)
