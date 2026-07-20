from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.config import Settings, get_settings
from backend.db.models import Paper, PaperChunk, PaperSection
from rag.chunkers.paper_chunker import PaperChunker
from rag.embeddings.embedding_client import build_embedding_client
from rag.loaders.pdf_loader import PDFLoader
from rag.models import PaperChunk as RagPaperChunk
from rag.models import PaperMetadata as RagPaperMetadata
from rag.models import PaperSection as RagPaperSection
from rag.parsers.metadata_parser import MetadataParser
from rag.parsers.section_parser import SectionParser
from rag.retrievers.paper_retriever import PaperRetriever
from rag.vector_store.qdrant_client import InMemoryVectorStoreClient, QdrantVectorStoreClient, VectorStoreClient
from backend.services.trace_service import TraceService


_memory_vector_store = InMemoryVectorStoreClient()


def sanitize_postgres_text(value: str | None) -> str:
    """Remove characters that PostgreSQL text fields cannot store.

    PyMuPDF can occasionally extract embedded NUL bytes from PDFs. Psycopg
    rejects those strings for text/varchar columns, so clean them before any
    metadata parsing, section persistence, chunk persistence, or tracing.
    """
    if not value:
        return ""
    return value.replace("\x00", "")


def sanitize_metadata(metadata: RagPaperMetadata) -> RagPaperMetadata:
    return RagPaperMetadata(
        title=sanitize_postgres_text(metadata.title),
        authors=[sanitize_postgres_text(author) for author in metadata.authors],
        abstract=sanitize_postgres_text(metadata.abstract),
    )


def sanitize_sections(sections: list[RagPaperSection]) -> list[RagPaperSection]:
    return [
        RagPaperSection(
            title=sanitize_postgres_text(section.title),
            content=sanitize_postgres_text(section.content),
            level=section.level,
            page_start=section.page_start,
            page_end=section.page_end,
        )
        for section in sections
    ]


def sanitize_chunks(chunks: list[RagPaperChunk]) -> list[RagPaperChunk]:
    return [
        RagPaperChunk(
            id=chunk.id,
            paper_id=chunk.paper_id,
            chunk_index=chunk.chunk_index,
            text=sanitize_postgres_text(chunk.text),
            section_title=sanitize_postgres_text(chunk.section_title),
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]


class PaperService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        vector_store: VectorStoreClient | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.loader = PDFLoader()
        self.metadata_parser = MetadataParser()
        self.section_parser = SectionParser()
        self.chunker = PaperChunker()
        self._embeddings = None
        self._vector_store = vector_store
        self._retriever = None

    def create_from_pdf(self, filename: str, file_obj: BinaryIO) -> Paper:
        trace_service = TraceService(self.db)
        task = trace_service.create_task(
            task_type="paper_ingestion",
            input_text=filename,
            user_id="default",
            metadata={"filename": filename},
        )
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        destination = self.settings.upload_dir / filename
        with destination.open("wb") as output:
            shutil.copyfileobj(file_obj, output)

        raw_text = sanitize_postgres_text(self.loader.load_text(destination))
        trace_service.record_step(
            task_id=task.id,
            user_id="default",
            agent_name="PDFLoader",
            step_name="parse_pdf_text",
            input_json={"filename": filename},
            output_json={"text_chars": len(raw_text)},
            tool_calls=[{"tool": "PyMuPDF", "path": str(destination)}],
        )
        metadata = sanitize_metadata(self.metadata_parser.parse(raw_text))
        sections = sanitize_sections(self.section_parser.parse(raw_text))
        trace_service.record_step(
            task_id=task.id,
            user_id="default",
            agent_name="PaperParser",
            step_name="extract_metadata_and_sections",
            input_json={"text_chars": len(raw_text)},
            output_json={
                "title": metadata.title,
                "author_count": len(metadata.authors),
                "section_count": len(sections),
            },
        )

        paper = Paper(
            title=metadata.title,
            authors=metadata.authors,
            abstract=metadata.abstract,
            original_filename=filename,
            file_path=str(destination),
            raw_text=raw_text,
            status="parsed",
        )
        self.db.add(paper)
        self.db.flush()

        for section in sections:
            self.db.add(
                PaperSection(
                    paper_id=paper.id,
                    title=section.title,
                    content=section.content,
                    level=section.level,
                    page_start=section.page_start,
                    page_end=section.page_end,
                )
            )

        rag_chunks = sanitize_chunks(self.chunker.chunk(paper.id, sections))
        self._persist_chunks(rag_chunks)
        self.db.commit()
        self.db.refresh(paper)
        self.retriever.index_chunks(rag_chunks)
        trace_service.record_step(
            task_id=task.id,
            user_id="default",
            agent_name="PaperIndexer",
            step_name="chunk_and_index_paper",
            input_json={"paper_id": paper.id},
            output_json={"chunk_count": len(rag_chunks)},
            tool_calls=[{"tool": "EmbeddingClient"}, {"tool": "VectorStoreClient"}],
        )
        trace_service.finish_task(task.id, f"Parsed and indexed paper {paper.id}")
        return self.get(paper.id) or paper

    def list(self) -> list[Paper]:
        statement = select(Paper).order_by(Paper.created_at.desc())
        return list(self.db.scalars(statement))

    def get(self, paper_id: str) -> Paper | None:
        statement = (
            select(Paper)
            .where(Paper.id == paper_id)
            .options(selectinload(Paper.sections), selectinload(Paper.chunks))
        )
        return self.db.scalar(statement)

    def search(self, paper_id: str, query: str, limit: int = 5):
        self._ensure_indexed(paper_id)
        return self.retriever.search(query, paper_id=paper_id, limit=limit)

    def _persist_chunks(self, chunks: list[RagPaperChunk]) -> None:
        for chunk in chunks:
            self.db.add(
                PaperChunk(
                    id=chunk.id,
                    paper_id=chunk.paper_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    section_title=chunk.section_title,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    chunk_metadata=chunk.metadata,
                )
            )

    def _ensure_indexed(self, paper_id: str) -> None:
        chunks = list(self.db.scalars(select(PaperChunk).where(PaperChunk.paper_id == paper_id)))
        payloads = [
            {
                "id": chunk.id,
                "paper_id": chunk.paper_id,
                "text": chunk.text,
                "section_title": chunk.section_title,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "metadata": chunk.chunk_metadata,
            }
            for chunk in chunks
        ]
        self.retriever.index_chunks(payloads)

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = build_embedding_client(
                provider=self.settings.embedding_provider,
                dimension=self.settings.embedding_dim,
                model_name=self.settings.embedding_model,
                device=self.settings.embedding_device,
                batch_size=self.settings.embedding_batch_size,
                max_length=self.settings.embedding_max_length,
            )
        return self._embeddings

    @property
    def vector_store(self) -> VectorStoreClient:
        if self._vector_store is None:
            self._vector_store = self._build_vector_store()
        return self._vector_store

    @property
    def retriever(self) -> PaperRetriever:
        if self._retriever is None:
            self._retriever = PaperRetriever(self.embeddings, self.vector_store)
        return self._retriever

    def _build_vector_store(self) -> VectorStoreClient:
        if self.settings.app_env == "test":
            return _memory_vector_store
        try:
            return QdrantVectorStoreClient(
                url=self.settings.qdrant_url,
                collection_name=self.settings.qdrant_collection,
                dimension=self.settings.embedding_dim,
            )
        except Exception:
            return _memory_vector_store


def safe_filename(filename: str) -> str:
    return Path(filename).name.replace("/", "_").replace("\\", "_")
