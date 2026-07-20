from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas import MemoryCreate, MemoryRead, MemorySearchRequest, MemoryUpdate, ReviewStatusUpdate
from backend.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=list[MemoryRead])
def list_memories(
    user_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    return MemoryService(db).list(user_id=user_id, status=status)


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db)):
    return MemoryService(db).create(payload)


@router.post("/search", response_model=list[MemoryRead])
def search_memories(payload: MemorySearchRequest, db: Session = Depends(get_db)):
    return MemoryService(db).search(payload.user_id, payload.query, payload.limit)


@router.patch("/{memory_id}", response_model=MemoryRead)
def update_memory(memory_id: str, payload: MemoryUpdate, db: Session = Depends(get_db)):
    memory = MemoryService(db).update(memory_id, payload)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.patch("/{memory_id}/status", response_model=MemoryRead)
def update_memory_status(memory_id: str, payload: ReviewStatusUpdate, db: Session = Depends(get_db)):
    try:
        memory = MemoryService(db).update_status(
            memory_id,
            payload.status,
            reviewed_by=payload.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    deleted = MemoryService(db).delete(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
