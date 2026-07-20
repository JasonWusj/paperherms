from __future__ import annotations

from rag.models import PaperMetadata
from rag.parsers.metadata_parser import MetadataParser


def extract_metadata(text: str) -> PaperMetadata:
    return MetadataParser().parse(text)
