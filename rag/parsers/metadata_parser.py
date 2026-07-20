from __future__ import annotations

import re

from rag.models import PaperMetadata


class MetadataParser:
    def parse(self, text: str) -> PaperMetadata:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else "Untitled Paper"
        authors = self._parse_authors(lines)
        abstract = self._parse_abstract(text)
        return PaperMetadata(title=title, authors=authors, abstract=abstract)

    def _parse_authors(self, lines: list[str]) -> list[str]:
        if len(lines) < 2:
            return []
        candidate = lines[1]
        if self._looks_like_heading(candidate):
            return []
        return [part.strip() for part in re.split(r",|;|\band\b", candidate) if part.strip()]

    def _parse_abstract(self, text: str) -> str:
        match = re.search(
            r"(?is)\babstract\b\s*(.*?)(?=\n\s*(?:\d+\.?\s+)?(?:introduction|1\s+introduction)\b)",
            text,
        )
        if match:
            return self._clean(match.group(1))

        match = re.search(r"(?is)\babstract\b\s*(.*?)(?=\n\s*(?:\d+\.?\s+)?[A-Z][^\n]{2,80}\n)", text)
        return self._clean(match.group(1)) if match else ""

    def _looks_like_heading(self, value: str) -> bool:
        return bool(re.match(r"(?i)^(abstract|introduction|method|experiments|references)\b", value))

    def _clean(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
