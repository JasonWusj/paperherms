from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas import ReviewStatusUpdate, SkillCreate, SkillRead, SkillRunRequest, SkillUpdate
from backend.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillRead])
def list_skills(status: str | None = None, db: Session = Depends(get_db)):
    return SkillService(db).list(status=status)


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)):
    return SkillService(db).create(payload)


@router.get("/{skill_id}", response_model=SkillRead)
def get_skill(skill_id: str, db: Session = Depends(get_db)):
    skill = SkillService(db).get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.patch("/{skill_id}", response_model=SkillRead)
def update_skill(skill_id: str, payload: SkillUpdate, db: Session = Depends(get_db)):
    skill = SkillService(db).update(skill_id, payload)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.patch("/{skill_id}/status", response_model=SkillRead)
def update_skill_status(skill_id: str, payload: ReviewStatusUpdate, db: Session = Depends(get_db)):
    try:
        skill = SkillService(db).update_status(
            skill_id,
            payload.status,
            reviewed_by=payload.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.post("/{skill_id}/run")
def run_skill(skill_id: str, payload: SkillRunRequest, db: Session = Depends(get_db)):
    skill, output = SkillService(db).run(skill_id, payload.input_text)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"skill_id": skill.id, "output": output, "usage_count": skill.usage_count}
