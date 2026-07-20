from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="DPO preference tuning after PaperHermes SFT")
    parser.add_argument("--model", type=Path, required=True, help="Merged SFT model directory")
    parser.add_argument("--train-file", type=Path, default=Path("artifacts/data/paperhermes-v1/dpo_train.jsonl"))
    parser.add_argument("--eval-file", type=Path, default=Path("artifacts/data/paperhermes-v1/dpo_validation.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/models/paperhermes-dpo"))
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--beta", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import DPOConfig, DPOTrainer

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(args.model), quantization_config=quantization, device_map="auto", torch_dtype="auto"
    )
    model.config.use_cache = False
    tokenizer = AutoTokenizer.from_pretrained(str(args.model), use_fast=True)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    dataset = load_dataset(
        "json", data_files={"train": str(args.train_file), "validation": str(args.eval_file)}
    )
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    train_config = DPOConfig(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        beta=args.beta,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=16,
        gradient_checkpointing=True,
        max_length=2048,
        max_prompt_length=1536,
        logging_steps=5,
        eval_strategy="steps",
        eval_steps=50,
        save_steps=50,
        save_total_limit=2,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        report_to=["tensorboard"],
        seed=args.seed,
    )
    trainer = DPOTrainer(
        model=model,
        ref_model=None,
        args=train_config,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    result = trainer.train()
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    (args.output_dir / "training_manifest.json").write_text(
        json.dumps(
            {
                "stage": "dpo",
                "sft_model": str(args.model),
                "train_file": str(args.train_file),
                "eval_file": str(args.eval_file),
                "beta": args.beta,
                "seed": args.seed,
                "metrics": result.metrics,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
