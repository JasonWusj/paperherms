from __future__ import annotations

from rag.models import RetrievedChunk
from tools import run_analysis


def analyze_limitations(chunks: list[RetrievedChunk]) -> str:
    return run_analysis("limitations", chunks)
