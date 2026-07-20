from __future__ import annotations

from rag.models import PaperSection
from rag.parsers.section_parser import SectionParser


def extract_sections(text: str) -> list[PaperSection]:
    return SectionParser().parse(text)
