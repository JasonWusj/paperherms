from __future__ import annotations

from rag.models import RetrievedChunk
from tools import run_analysis


def analyze_method(chunks: list[RetrievedChunk]) -> str:
    return run_analysis("method", chunks)
