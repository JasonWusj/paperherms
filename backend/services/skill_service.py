from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Skill
from backend.schemas import SkillCreate, SkillUpdate


REVIEW_STATUSES = {"draft", "active", "rejected", "archived"}


class SkillService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: SkillCreate) -> Skill:
        skill = Skill(
            name=payload.name,
            description=payload.description,
            prompt_template=payload.prompt_template,
            metadata_json=payload.metadata,
        )
        self.db.add(skill)
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def create_candidate(
        self,
        user_id: str,
        candidate: dict,
        source_task_id: str | None = None,
    ) -> Skill:
        metadata = dict(candidate.get("metadata") or {})
        metadata.update({
            "status": candidate.get("status", "draft"),
            "source": "learning",
            "source_task_id": source_task_id,
            "user_id": user_id,
            "confidence": candidate.get("confidence", 0.0),
            "trigger_patterns": candidate.get("trigger_patterns", []),
            "steps": candidate.get("steps", []),
        })
        skill = Skill(
            name=self._unique_candidate_name(str(candidate.get("name") or "learned_skill")),
            description=str(candidate.get("description") or ""),
            prompt_template=str(candidate.get("prompt_template") or "{input}"),
            metadata_json=metadata,
        )
        self.db.add(skill)
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def list(self, status: str | None = None, source_task_id: str | None = None) -> list[Skill]:
        skills = list(self.db.scalars(select(Skill).order_by(Skill.name.asc())))
        if status is not None:
            skills = [skill for skill in skills if self._status(skill) == status]
        if source_task_id is not None:
            skills = [
                skill
                for skill in skills
                if (skill.metadata_json or {}).get("source_task_id") == source_task_id
            ]
        return skills

    def get(self, skill_id: str) -> Skill | None:
        return self.db.get(Skill, skill_id)

    def search_for_task(
        self,
        user_id: str,
        task_type: str,
        query: str,
        limit: int = 3,
    ) -> list[Skill]:
        query_text = query.lower()
        task_text = task_type.lower()
        skills = list(self.db.scalars(select(Skill).order_by(Skill.usage_count.desc(), Skill.updated_at.desc())))
        matches: list[Skill] = []
        for skill in skills:
            metadata = skill.metadata_json or {}
            if metadata.get("status", "active") != "active":
                continue
            owner = metadata.get("user_id")
            if owner and owner != user_id:
                continue
            patterns = [str(item).lower() for item in metadata.get("trigger_patterns", [])]
            searchable = " ".join([skill.name.lower(), skill.description.lower(), *patterns])
            pattern_matches = any(
                pattern and (pattern in query_text or pattern == task_text)
                for pattern in patterns
            )
            task_matches = bool(task_text and task_text in searchable)
            if pattern_matches or task_matches:
                matches.append(skill)
            if len(matches) >= limit:
                break
        return matches

    def select_for_task(
        self,
        user_id: str,
        task_type: str,
        query: str,
        limit: int = 3,
    ) -> list[dict]:
        selections = []
        for skill in self.search_for_task(user_id, task_type, query, limit=limit):
            selections.append(self._selection_record(skill, task_type, query))
        return selections

    def update(self, skill_id: str, payload: SkillUpdate) -> Skill | None:
        skill = self.get(skill_id)
        if not skill:
            return None
        changed_fields = []
        original_metadata = dict(skill.metadata_json or {})
        if payload.description is not None:
            if payload.description != skill.description:
                changed_fields.append("description")
            skill.description = payload.description
        if payload.prompt_template is not None:
            if payload.prompt_template != skill.prompt_template:
                changed_fields.append("prompt_template")
            skill.prompt_template = payload.prompt_template
        if payload.metadata is not None:
            metadata = dict(payload.metadata)
            changed_fields.extend(self._metadata_changed_fields(original_metadata, metadata))
            if changed_fields:
                self._append_review_history(
                    metadata,
                    {
                        "action": "content_update",
                        "changed_fields": sorted(set(changed_fields)),
                        "reviewed_by": "default",
                    },
                )
            skill.metadata_json = metadata
        elif changed_fields:
            metadata = dict(skill.metadata_json or {})
            self._append_review_history(
                metadata,
                {
                    "action": "content_update",
                    "changed_fields": sorted(set(changed_fields)),
                    "reviewed_by": "default",
                },
            )
            skill.metadata_json = metadata
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def update_status(self, skill_id: str, status: str, reviewed_by: str = "default") -> Skill | None:
        if status not in REVIEW_STATUSES:
            raise ValueError(f"Unsupported review status: {status}")
        skill = self.get(skill_id)
        if not skill:
            return None
        metadata = dict(skill.metadata_json or {})
        previous_status = self._status(skill)
        self._append_review_history(
            metadata,
            {
                "action": "status_update",
                "from_status": previous_status,
                "to_status": status,
                "reviewed_by": reviewed_by,
            },
        )
        metadata.update({
            "status": status,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        })
        skill.metadata_json = metadata
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def run(self, skill_id: str, input_text: str) -> tuple[Skill | None, str]:
        skill = self.get(skill_id)
        if not skill:
            return None, ""
        skill.usage_count += 1
        output = skill.prompt_template.replace("{input}", input_text)
        self.db.commit()
        self.db.refresh(skill)
        return skill, output

    def record_usage(self, skill_id: str) -> Skill | None:
        skill = self.get(skill_id)
        if not skill:
            return None
        skill.usage_count += 1
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def _unique_candidate_name(self, base_name: str) -> str:
        normalized = "_".join(base_name.lower().strip().split()) or "learned_skill"
        existing = self.db.scalar(select(Skill).where(Skill.name == normalized))
        if not existing:
            return normalized
        suffix = 2
        while self.db.scalar(select(Skill).where(Skill.name == f"{normalized}_{suffix}")):
            suffix += 1
        return f"{normalized}_{suffix}"

    def _status(self, skill: Skill) -> str:
        return str((skill.metadata_json or {}).get("status", "active"))

    def _append_review_history(self, metadata: dict, entry: dict) -> None:
        history = list(metadata.get("review_history", []))
        timestamp = datetime.now(timezone.utc).isoformat()
        history.append({**entry, "reviewed_at": timestamp})
        metadata["review_history"] = history

    def _metadata_changed_fields(self, before: dict, after: dict) -> list[str]:
        fields = []
        for key in sorted(set(before) | set(after)):
            if key in {"review_history", "reviewed_at", "reviewed_by"}:
                continue
            if before.get(key) != after.get(key):
                fields.append(f"metadata.{key}")
        return fields

    def _selection_record(self, skill: Skill, task_type: str, query: str) -> dict:
        metadata = skill.metadata_json or {}
        query_text = query.lower()
        task_text = task_type.lower()
        patterns = [str(item).lower() for item in metadata.get("trigger_patterns", [])]
        matched_patterns = [
            pattern for pattern in patterns
            if pattern and (pattern in query_text or pattern == task_text)
        ]
        if matched_patterns:
            reason = f"matched trigger patterns: {', '.join(matched_patterns)}"
        else:
            reason = f"task type '{task_type}' matched skill name or description"
        return {
            "skill_id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "reason": reason,
            "matched_patterns": matched_patterns,
            "confidence": float(metadata.get("confidence", 0.5) or 0.5),
            "prompt_template": skill.prompt_template,
            "metadata_json": metadata,
        }
