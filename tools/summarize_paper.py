from __future__ import annotations

from rag.models import RetrievedChunk
from tools import run_analysis


def summarize_paper(chunks: list[RetrievedChunk]) -> str:
    return run_analysis("summary", chunks)
