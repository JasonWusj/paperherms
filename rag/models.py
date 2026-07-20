from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PaperMetadata:
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""


@dataclass(frozen=True)
class PaperSection:
    title: str
    content: str
    level: int = 1
    page_start: int | None = None
    page_end: int | None = None


@dataclass(frozen=True)
class PaperChunk:
    id: str
    paper_id: str
    chunk_index: int
    text: str
    section_title: str
    page_start: int | None = None
    page_end: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    paper_id: str
    text: str
    section_title: str
    score: float
    page_start: int | None = None
    page_end: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
