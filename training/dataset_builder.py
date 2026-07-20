from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SYSTEM_PROMPT = (
    "你是 PaperHermes 论文研究助手。只能依据给定证据回答；关键结论后必须给出 "
    "[chunk:<id> section:<title> page:<number>] 格式的引用。证据不足时明确说明。"
)


def stable_split(paper_id: str) -> str:
    """Split by paper, never by question, to prevent paper-level leakage."""
    bucket = int(hashlib.sha256(paper_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def format_evidence(evidence: list[dict[str, Any]]) -> str:
    lines = []
    for item in evidence:
        lines.append(
            "\n".join(
                [
                    f"chunk_id: {item['chunk_id']}",
                    f"section: {item.get('section_title') or 'Unknown'}",
                    f"page: {item.get('page_start') or 'Unknown'}",
                    f"text: {str(item.get('text') or '').strip()}",
                ]
            )
        )
    return "\n\n---\n\n".join(lines)


def build_examples(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sft: list[dict[str, Any]] = []
    dpo: list[dict[str, Any]] = []
    for row in rows:
        paper_id = str(row.get("paper_id") or "").strip()
        question = str(row.get("question") or "").strip()
        evidence = row.get("evidence") or []
        chosen = str(row.get("chosen") or "").strip()
        rejected = str(row.get("rejected") or "").strip()
        if not paper_id or not question or not evidence or not chosen:
            continue
        split = stable_split(paper_id)
        prompt = f"问题：{question}\n\n论文证据：\n{format_evidence(evidence)}"
        common = {
            "example_id": str(row.get("example_id") or _example_id(paper_id, question)),
            "paper_id": paper_id,
            "split": split,
            "evidence_ids": [str(item["chunk_id"]) for item in evidence],
            "source": str(row.get("source") or "paperhermes_export"),
        }
        sft.append(
            {
                **common,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": chosen},
                ],
            }
        )
        if rejected and rejected != chosen:
            dpo.append(
                {
                    **common,
                    "prompt": f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n",
                    "chosen": chosen,
                    "rejected": rejected,
                }
            )
    return sft, dpo


def write_dataset(source: Path, output_dir: Path) -> dict[str, Any]:
    with source.open("r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    sft, dpo = build_examples(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, Counter[str]] = {"sft": Counter(), "dpo": Counter()}
    for name, records in (("sft", sft), ("dpo", dpo)):
        for split in ("train", "validation", "test"):
            selected = [record for record in records if record["split"] == split]
            target = output_dir / f"{name}_{split}.jsonl"
            with target.open("w", encoding="utf-8") as handle:
                for record in selected:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            counts[name][split] = len(selected)
    paper_splits: dict[str, str] = {}
    for record in sft:
        existing = paper_splits.setdefault(record["paper_id"], record["split"])
        if existing != record["split"]:
            raise ValueError(f"paper leakage detected for {record['paper_id']}")
    manifest = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "split_policy": "sha256(paper_id), 70/15/15",
        "paper_count": len(paper_splits),
        "counts": {name: dict(value) for name, value in counts.items()},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def _example_id(paper_id: str, question: str) -> str:
    return hashlib.sha256(f"{paper_id}\0{question}".encode("utf-8")).hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build leak-free PaperHermes SFT/DPO JSONL files")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/data/paperhermes-v1"))
    args = parser.parse_args()
    print(json.dumps(write_dataset(args.source, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
