from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from backend.db.models import Paper, PaperChunk
from backend.db.session import SessionLocal


TASK_TEMPLATES = {
    "method": "请概括这篇论文在该章节描述的核心方法。",
    "experiments": "请总结该章节中的实验设置、数据集或主要结果。",
    "limitations": "根据给定证据，说明方法可能存在的限制；不要补充证据外事实。",
}


def export_source(output: Path, max_chunks_per_paper: int = 12) -> int:
    """Export weakly supervised pairs locally; generated output is git-ignored."""
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with SessionLocal() as db, output.open("w", encoding="utf-8") as handle:
        for paper in db.scalars(select(Paper).order_by(Paper.created_at)):
            chunks = list(
                db.scalars(
                    select(PaperChunk)
                    .where(PaperChunk.paper_id == paper.id)
                    .order_by(PaperChunk.chunk_index)
                    .limit(max_chunks_per_paper)
                )
            )
            for index, chunk in enumerate(chunks):
                task = list(TASK_TEMPLATES)[index % len(TASK_TEMPLATES)]
                page = chunk.page_start or "Unknown"
                citation = f"[chunk:{chunk.id} section:{chunk.section_title} page:{page}]"
                chosen = f"{chunk.text[:700].strip()} {citation}"
                rejected = "该论文提出了一种有效方法，并在多个实验中取得了优秀结果。"
                row = {
                    "paper_id": paper.id,
                    "example_id": f"{paper.id}-{chunk.chunk_index}-{task}",
                    "question": TASK_TEMPLATES[task],
                    "evidence": [
                        {
                            "chunk_id": chunk.id,
                            "section_title": chunk.section_title,
                            "page_start": chunk.page_start,
                            "text": chunk.text,
                        }
                    ],
                    "chosen": chosen,
                    "rejected": rejected,
                    "source": "weak_extract_then_review",
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/data/training_source.jsonl"))
    parser.add_argument("--max-chunks-per-paper", type=int, default=12)
    args = parser.parse_args()
    count = export_source(args.output, args.max_chunks_per_paper)
    print(json.dumps({"output": str(args.output), "examples": count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
