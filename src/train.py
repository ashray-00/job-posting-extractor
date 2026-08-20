"""LoRA SFT with TRL + PEFT.

Pinned against installed versions (do not invent field names):
  trl==1.10.0  → SFTConfig uses ``max_length`` (not max_seq_length),
                 ``completion_only_loss``, ``warmup_steps`` (no warmup_ratio),
                 ``eval_strategy`` / ``eval_steps``, ``report_to``.
  peft==0.20.0 → ``target_modules="all-linear"`` expands to every nn.Linear
                 except the LM head (includes MLP gate/up/down projections).

Usage:
  python -m src.train configs/r32_lr1e4.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import torch
import yaml
from datasets import Dataset
from peft import LoraConfig, TaskType
from peft.tuners.lora.layer import LoraLayer
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainerCallback
from trl import SFTConfig, SFTTrainer

_ROOT = Path(__file__).resolve().parent.parent

# Load .env for HF_HOME / HF_TOKEN before model download
_ENV_FILE = _ROOT / ".env"
if _ENV_FILE.exists():
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

logger = logging.getLogger("train")


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise SystemExit(f"Config must be a mapping: {path}")
    required = [
        "base_model",
        "train_file",
        "val_file",
        "output_dir",
        "lora_r",
        "lora_alpha",
        "lora_dropout",
        "target_modules",
        "learning_rate",
        "num_train_epochs",
        "per_device_train_batch_size",
        "gradient_accumulation_steps",
        "max_seq_length",
        "warmup_ratio",
        "seed",
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise SystemExit(f"Config missing keys {missing}: {path}")
    return cfg


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _ROOT / p
    return p


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=_ROOT,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _load_prompt_completion_jsonl(path: Path) -> Dataset:
    """Load TRL conversational prompt-completion rows; force thinking off."""
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "prompt" not in row or "completion" not in row:
                raise ValueError(f"{path} row missing prompt/completion: {row.get('doc_id')}")
            rows.append(
                {
                    "prompt": row["prompt"],
                    "completion": row["completion"],
                    # Forwarded by trl.data_utils.apply_chat_template → Qwen3
                    "chat_template_kwargs": {"enable_thinking": False},
                }
            )
    if not rows:
        raise SystemExit(f"No examples in {path}")
    return Dataset.from_list(rows)


def _setup_file_logging(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "train.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Avoid duplicate handlers on re-entry
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(fh)
    root.addHandler(sh)
    return log_path


def _print_lora_coverage(model: torch.nn.Module) -> None:
    """Print adapted module names + trainable param count; confirm MLPs."""
    adapted = sorted(n for n, m in model.named_modules() if isinstance(m, LoraLayer))
    print("\n=== LoRA adapted modules ===")
    for name in adapted:
        print(f"  {name}")
    mlp_hits = [n for n in adapted if any(k in n for k in ("mlp.", "gate_proj", "up_proj", "down_proj"))]
    print(f"\nMLP-related adapted modules: {len(mlp_hits)}")
    for name in mlp_hits[:12]:
        print(f"  {name}")
    if len(mlp_hits) > 12:
        print(f"  … +{len(mlp_hits) - 12} more")
    if not mlp_hits:
        raise RuntimeError(
            "No MLP projections in LoRA targets — `all-linear` did not reach "
            "gate_proj/up_proj/down_proj. Refusing to train."
        )

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    pct = 100.0 * trainable / total if total else 0.0
    print(f"\nTrainable params: {trainable:,} / {total:,} ({pct:.4f}%)")
    logger.info("trainable=%d total=%d pct=%.4f mlp_lora=%d", trainable, total, pct, len(mlp_hits))


def _verify_completion_only_labels(trainer: SFTTrainer) -> None:
    """Pull one batch and assert prompt tokens are masked with -100."""
    loader = trainer.get_train_dataloader()
    batch = next(iter(loader))
    labels = batch["labels"]
    if not isinstance(labels, torch.Tensor):
        labels = torch.tensor(labels)

    row = labels[0].tolist()
    print("\n=== completion-only label check (first batch, row 0) ===")
    print(f"labels[:64]: {row[:64]}")
    n_mask = sum(1 for x in row if x == -100)
    n_sup = sum(1 for x in row if x != -100)
    print(f"masked (-100): {n_mask}  supervised: {n_sup}  seq_len: {len(row)}")

    # Prompt region is the leading -100 run (after any left-flush, still a
    # contiguous masked prefix before the first supervised token).
    first_sup = next((i for i, x in enumerate(row) if x != -100), None)
    if first_sup is None:
        raise RuntimeError("All labels are -100 — nothing to train on.")
    if first_sup == 0:
        raise RuntimeError(
            "No leading -100 mask on labels — prompt tokens are NOT masked. "
            "Check completion_only_loss / prompt-completion formatting."
        )
    prefix = row[:first_sup]
    if any(x != -100 for x in prefix):
        raise RuntimeError(f"Non-masked tokens inside prompt region: {prefix[:32]}")
    print(
        f"OK: prompt region labels[:{first_sup}] are all -100; "
        f"completion supervision starts at index {first_sup}."
    )
    logger.info("completion_only_ok first_sup=%d masked=%d supervised=%d", first_sup, n_mask, n_sup)


class _LossTracker(TrainerCallback):
    def __init__(self) -> None:
        self.final_train_loss: float | None = None
        self.final_eval_loss: float | None = None

    def on_log(self, args, state, control, logs=None, **kwargs):  # noqa: ANN001
        if not logs:
            return
        if "loss" in logs:
            self.final_train_loss = float(logs["loss"])
        if "eval_loss" in logs:
            self.final_eval_loss = float(logs["eval_loss"])


def _warmup_steps_from_ratio(
    *,
    n_train: int,
    per_device_train_batch_size: int,
    gradient_accumulation_steps: int,
    num_train_epochs: float,
    warmup_ratio: float,
) -> int:
    """TRL 1.10 SFTConfig has warmup_steps only — convert YAML warmup_ratio."""
    world = int(os.environ.get("WORLD_SIZE", "1"))
    batch = per_device_train_batch_size * max(world, 1) * gradient_accumulation_steps
    steps_per_epoch = max(1, math.ceil(n_train / batch))
    total_steps = max(1, int(math.ceil(steps_per_epoch * num_train_epochs)))
    return max(0, int(total_steps * warmup_ratio))


def main() -> None:
    parser = argparse.ArgumentParser(description="LoRA SFT (TRL + PEFT)")
    parser.add_argument("config", type=str, help="Path to YAML under configs/")
    args = parser.parse_args()

    cfg_path = _resolve(args.config)
    cfg = _load_yaml(cfg_path)

    output_dir = _resolve(cfg["output_dir"])
    log_path = _setup_file_logging(output_dir)
    logger.info("config=%s output_dir=%s", cfg_path, output_dir)
    logger.info("trl/peft field mapping: max_seq_length→max_length, warmup_ratio→warmup_steps")

    train_path = _resolve(cfg["train_file"])
    val_path = _resolve(cfg["val_file"])
    train_ds = _load_prompt_completion_jsonl(train_path)
    val_ds = _load_prompt_completion_jsonl(val_path)
    logger.info("train=%d val=%d", len(train_ds), len(val_ds))

    warmup_steps = _warmup_steps_from_ratio(
        n_train=len(train_ds),
        per_device_train_batch_size=int(cfg["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(cfg["gradient_accumulation_steps"]),
        num_train_epochs=float(cfg["num_train_epochs"]),
        warmup_ratio=float(cfg["warmup_ratio"]),
    )
    print(f"[train] warmup_ratio={cfg['warmup_ratio']} → warmup_steps={warmup_steps}")

    use_cuda = torch.cuda.is_available()
    use_bf16 = use_cuda and torch.cuda.is_bf16_supported()
    use_fp16 = use_cuda and not use_bf16

    # SFTConfig fields verified against trl==1.10.0 (pip show / inspect).
    sft_args = SFTConfig(
        output_dir=str(output_dir),
        max_length=int(cfg["max_seq_length"]),
        completion_only_loss=True,
        packing=False,
        learning_rate=float(cfg["learning_rate"]),
        num_train_epochs=float(cfg["num_train_epochs"]),
        per_device_train_batch_size=int(cfg["per_device_train_batch_size"]),
        per_device_eval_batch_size=int(cfg["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(cfg["gradient_accumulation_steps"]),
        warmup_steps=warmup_steps,
        seed=int(cfg["seed"]),
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_strategy="steps",
        logging_steps=10,
        report_to="none",  # local file only — no W&B/HF/Trackio
        bf16=use_bf16,
        fp16=use_fp16,
        use_cpu=not use_cuda,
        remove_unused_columns=False,
    )

    target_modules = cfg["target_modules"]
    if isinstance(target_modules, list):
        pass
    elif isinstance(target_modules, str):
        target_modules = target_modules.strip()
    else:
        raise SystemExit(f"target_modules must be str or list, got {type(target_modules)}")

    peft_config = LoraConfig(
        r=int(cfg["lora_r"]),
        lora_alpha=int(cfg["lora_alpha"]),
        lora_dropout=float(cfg["lora_dropout"]),
        target_modules=target_modules,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    print(f"[train] loading tokenizer/model {cfg['base_model']} …")
    tokenizer = AutoTokenizer.from_pretrained(cfg["base_model"], trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        cfg["base_model"],
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if use_bf16 else (torch.float16 if use_fp16 else None),
        device_map="auto" if torch.cuda.is_available() else None,
    )

    loss_tracker = _LossTracker()
    trainer = SFTTrainer(
        model=model,
        args=sft_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
        peft_config=peft_config,
        callbacks=[loss_tracker],
    )

    _print_lora_coverage(trainer.model)
    _verify_completion_only_labels(trainer)

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()

    t0 = time.perf_counter()
    train_result = trainer.train()
    wall_s = time.perf_counter() - t0

    peak_vram_bytes: int | None = None
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        peak_vram_bytes = int(torch.cuda.max_memory_allocated())

    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Prefer tracked losses; fall back to train_result / last eval
    final_train_loss = loss_tracker.final_train_loss
    if final_train_loss is None and train_result is not None:
        final_train_loss = float(train_result.training_loss)

    final_eval_loss = loss_tracker.final_eval_loss
    if final_eval_loss is None:
        for entry in reversed(trainer.state.log_history):
            if "eval_loss" in entry:
                final_eval_loss = float(entry["eval_loss"])
                break

    meta = {
        "config_path": str(cfg_path),
        "config": cfg,
        "trl_sftconfig_mapping": {
            "max_seq_length": "max_length",
            "warmup_ratio": f"warmup_steps={warmup_steps}",
            "completion_only_loss": True,
        },
        "git_sha": _git_sha(),
        "wall_clock_s": round(wall_s, 3),
        "peak_vram_bytes": peak_vram_bytes,
        "peak_vram_gb": round(peak_vram_bytes / (1024**3), 3) if peak_vram_bytes else None,
        "final_train_loss": final_train_loss,
        "final_eval_loss": final_eval_loss,
        "log_file": str(log_path),
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
    }
    meta_path = output_dir / "train_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[train] saved adapter → {output_dir}")
    print(f"[train] wrote {meta_path}")
    logger.info("done meta=%s", meta)


if __name__ == "__main__":
    main()
