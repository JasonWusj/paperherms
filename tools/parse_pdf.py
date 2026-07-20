from __future__ import annotations

from pathlib import Path

from rag.loaders.pdf_loader import PDFLoader


def parse_pdf(path: str | Path) -> str:
    return PDFLoader().load_text(path)
