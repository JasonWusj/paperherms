from __future__ import annotations

import uuid

from rag.models import PaperChunk, PaperSection


class PaperChunker:
    def __init__(self, max_chars: int = 1200, overlap_chars: int = 160) -> None:
        if overlap_chars >= max_chars:
            raise ValueError("overlap_chars must be smaller than max_chars")
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, paper_id: str, sections: list[PaperSection]) -> list[PaperChunk]:
        chunks: list[PaperChunk] = []
        for section in sections:
            text = self._normalize(section.content)
            start = 0
            while start < len(text):
                end = min(start + self.max_chars, len(text))
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunk_index = len(chunks)
                    chunk_id = self._chunk_id(paper_id, chunk_index, section.title, chunk_text)
                    chunks.append(
                        PaperChunk(
                            id=chunk_id,
                            paper_id=paper_id,
                            chunk_index=chunk_index,
                            text=chunk_text,
                            section_title=section.title,
                            page_start=section.page_start,
                            page_end=section.page_end,
                            metadata={"char_start": start, "char_end": end},
                        )
                    )
                if end == len(text):
                    break
                start = max(end - self.overlap_chars, start + 1)
        return chunks

    def _normalize(self, text: str) -> str:
        return " ".join(text.split())

    def _chunk_id(self, paper_id: str, chunk_index: int, section_title: str, text: str) -> str:
        value = f"{paper_id}:{chunk_index}:{section_title}:{text}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, value))
