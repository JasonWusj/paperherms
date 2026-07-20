# PaperHermes QLoRA-SFT + DPO

This directory contains code only. Source corpora, generated JSONL files, checkpoints, adapters, and merged weights are written below `artifacts/` and are excluded from Git.

## Environment

Use Linux, CUDA, and a 12–24 GB GPU. The default 1.5B model is selected so the complete pipeline can run on a single card.

```bash
python -m venv .venv-training
source .venv-training/bin/activate
pip install -e '.[training]'
```

## 1. Build the data

Export weak examples from the local PaperHermes database, then review or replace generated answers before training:

```bash
python -m training.export_training_source --output artifacts/data/training_source.jsonl
python -m training.dataset_builder \
  --source artifacts/data/training_source.jsonl \
  --output-dir artifacts/data/paperhermes-v1
```

The split is a stable SHA-256 hash of `paper_id`: 70% train, 15% validation, 15% test. Every question from the same paper remains in one split. The manifest stores the source hash and counts.

Weak extractive `chosen/rejected` pairs are scaffolding, not final research data. For resume-quality results, manually inspect at least 100 pairs and use human feedback or a calibrated teacher judge to replace low-quality pairs.

## 2. SFT and DPO

```bash
python -m training.train_sft \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --output-dir artifacts/models/paperhermes-sft

python -m training.merge_adapter \
  --base-model Qwen/Qwen2.5-1.5B-Instruct \
  --adapter artifacts/models/paperhermes-sft \
  --output-dir artifacts/models/paperhermes-sft-merged

python -m training.train_dpo \
  --model artifacts/models/paperhermes-sft-merged \
  --output-dir artifacts/models/paperhermes-dpo
```

Both trainers use NF4 QLoRA, gradient checkpointing, fixed seeds, validation steps, TensorBoard logging, and a training manifest. DPO uses `beta=0.1` by default.

## 3. Evaluate

Generate answers from Base, SFT, and DPO into one JSONL file with `model`, `answer`, and `evidence_ids`, then run:

```bash
python -m training.evaluate \
  --predictions artifacts/evaluation/model_predictions.jsonl \
  --output artifacts/evaluation/model_comparison.json
```

Report citation format rate, precision, coverage, refusal behavior, human pairwise win rate, P50/P95 latency, and token usage. Automatic metrics must be accompanied by a manually reviewed test subset.
