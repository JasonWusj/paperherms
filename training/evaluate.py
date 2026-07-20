from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


CITATION_PATTERN = re.compile(r"\[chunk:([^\s\]]+)\s+section:.*?\s+page:.*?\]")


def score_prediction(record: dict[str, Any]) -> dict[str, float]:
    answer = str(record.get("answer") or "")
    evidence_ids = {str(item) for item in record.get("evidence_ids", [])}
    citations = CITATION_PATTERN.findall(answer)
    valid = sum(citation in evidence_ids for citation in citations)
    return {
        "answered": 1.0 if answer.strip() else 0.0,
        "citation_format": 1.0 if citations else 0.0,
        "citation_precision": valid / max(len(citations), 1),
        "citation_coverage": min(len(set(citations) & evidence_ids) / max(len(evidence_ids), 1), 1.0),
        "refusal_when_no_evidence": (
            1.0
            if evidence_ids or any(term in answer for term in ("证据不足", "无法判断", "insufficient evidence"))
            else 0.0
        ),
    }


def evaluate_file(path: Path) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, float]]] = defaultdict(list)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            grouped[str(record.get("model") or "unknown")].append(score_prediction(record))
    summary: dict[str, Any] = {}
    for model, scores in grouped.items():
        summary[model] = {
            "samples": len(scores),
            **{
                key: round(sum(item[key] for item in scores) / max(len(scores), 1), 4)
                for key in scores[0]
            },
        }
    return {"source": str(path), "models": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Base/SFT/DPO grounded-generation files")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_file(args.predictions)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
