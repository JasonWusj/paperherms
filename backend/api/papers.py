from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas import (
    AgentAnswerRead,
    PaperListRead,
    PaperQuestionRequest,
    PaperRead,
    RetrievedChunkRead,
    SearchRequest,
)
from backend.services.agent_service import PaperAgentService
from backend.services.paper_service import PaperService, safe_filename

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("", response_model=list[PaperListRead])
def list_papers(db: Session = Depends(get_db)):
    return PaperService(db).list()


@router.post("", response_model=PaperRead, status_code=status.HTTP_201_CREATED)
def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        return PaperService(db).create_from_pdf(safe_filename(file.filename), file.file)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {exc}") from exc


@router.get("/{paper_id}", response_model=PaperRead)
def get_paper(paper_id: str, db: Session = Depends(get_db)):
    paper = PaperService(db).get(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.post("/{paper_id}/search", response_model=list[RetrievedChunkRead])
def search_paper(paper_id: str, payload: SearchRequest, db: Session = Depends(get_db)):
    if not PaperService(db).get(paper_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperService(db).search(paper_id, payload.query, payload.limit)


@router.post("/{paper_id}/chat", response_model=AgentAnswerRead)
def chat_with_paper(paper_id: str, payload: PaperQuestionRequest, db: Session = Depends(get_db)):
    if not PaperService(db).get(paper_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperAgentService(db).answer_question(paper_id, payload.question, payload.user_id)


@router.post("/{paper_id}/summary", response_model=AgentAnswerRead)
def summarize_paper(paper_id: str, db: Session = Depends(get_db)):
    if not PaperService(db).get(paper_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperAgentService(db).analyze(paper_id, "summary")


@router.post("/{paper_id}/method", response_model=AgentAnswerRead)
def analyze_method(paper_id: str, db: Session = Depends(get_db)):
    if not PaperService(db).get(paper_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperAgentService(db).analyze(paper_id, "method")


@router.post("/{paper_id}/experiments", response_model=AgentAnswerRead)
def analyze_experiments(paper_id: str, db: Session = Depends(get_db)):
    if not PaperService(db).get(paper_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperAgentService(db).analyze(paper_id, "experiments")


@router.post("/{paper_id}/novelty", response_model=AgentAnswerRead)
def analyze_novelty(paper_id: str, db: Session = Depends(get_db)):
    if not PaperService(db).get(paper_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperAgentService(db).analyze(paper_id, "novelty")


@router.post("/{paper_id}/limitations", response_model=AgentAnswerRead)
def analyze_limitations(paper_id: str, db: Session = Depends(get_db)):
    if not PaperService(db).get(paper_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperAgentService(db).analyze(paper_id, "limitations")
