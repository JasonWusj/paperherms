from __future__ import annotations

import re

from rag.models import RetrievedChunk


class PaperReranker:
    def rerank(self, query: str, chunks: list[RetrievedChunk], *, limit: int) -> list[RetrievedChunk]:
        query_terms = self._terms(query)
        if not query_terms:
            return chunks[:limit]

        scored = [(self._score(query_terms, chunk), index, chunk) for index, chunk in enumerate(chunks)]
        scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        return [chunk for _, _, chunk in scored[:limit]]

    def _score(self, query_terms: set[str], chunk: RetrievedChunk) -> float:
        chunk_terms = self._terms(f"{chunk.section_title} {chunk.text}")
        overlap = len(query_terms & chunk_terms) / max(len(query_terms), 1)
        section_bonus = self._section_bonus(query_terms, chunk.section_title)
        return (chunk.score * 0.65) + (overlap * 0.25) + section_bonus

    def _section_bonus(self, query_terms: set[str], section_title: str) -> float:
        section = section_title.lower()
        groups = [
            ({"method", "approach", "algorithm", "architecture", "model"}, {"method", "approach"}),
            (
                {"experiment", "experiments", "dataset", "metric", "baseline", "ablation", "setup"},
                {"experiment", "evaluation", "result"},
            ),
            ({"novel", "novelty", "contribution", "innovation"}, {"contribution", "introduction"}),
            ({"limitation", "limitations", "weakness", "future"}, {"limitation", "discussion"}),
        ]
        for query_group, section_markers in groups:
            if query_terms & query_group and any(marker in section for marker in section_markers):
                return 0.35
        return 0.0

    def _terms(self, text: str) -> set[str]:
        english = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        cjk = [char for char in text if "\u4e00" <= char <= "\u9fff"]
        return set(english + cjk)
