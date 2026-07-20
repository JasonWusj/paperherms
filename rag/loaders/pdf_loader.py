from __future__ import annotations

from pathlib import Path


class PDFLoader:
    def load_text(self, path: str | Path) -> str:
        import fitz

        document = fitz.open(str(path))
        try:
            pages = [page.get_text("text") for page in document]
        finally:
            document.close()
        return "\n\n".join(pages).strip()
