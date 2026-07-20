import json
from pathlib import Path

from training.dataset_builder import build_examples, stable_split, write_dataset
from training.evaluate import score_prediction


def test_paper_split_is_stable_and_shared_by_all_examples() -> None:
    rows = [
        {
            "paper_id": "paper-1",
            "question": f"question-{index}",
            "evidence": [{"chunk_id": f"c-{index}", "text": "evidence"}],
            "chosen": f"answer [chunk:c-{index} section:Method page:1]",
            "rejected": "unsupported answer",
        }
        for index in range(4)
    ]
    sft, dpo = build_examples(rows)

    assert {item["split"] for item in sft} == {stable_split("paper-1")}
    assert {item["split"] for item in dpo} == {stable_split("paper-1")}


def test_dataset_manifest_and_citation_metrics(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text(
        json.dumps(
            {
                "paper_id": "paper-2",
                "question": "method?",
                "evidence": [{"chunk_id": "c-1", "text": "evidence"}],
                "chosen": "answer [chunk:c-1 section:Method page:1]",
                "rejected": "unsupported",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = write_dataset(source, tmp_path / "out")
    scores = score_prediction(
        {"answer": "answer [chunk:c-1 section:Method page:1]", "evidence_ids": ["c-1"]}
    )

    assert manifest["paper_count"] == 1
    assert scores["citation_precision"] == 1.0
    assert scores["citation_coverage"] == 1.0
