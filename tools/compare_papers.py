from __future__ import annotations

from rag.models import PaperMetadata


def compare_papers(metadata_items: list[PaperMetadata]) -> list[dict[str, str]]:
    return [
        {"title": item.title, "authors": ", ".join(item.authors), "abstract": item.abstract}
        for item in metadata_items
    ]
