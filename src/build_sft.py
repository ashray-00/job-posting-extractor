"""Convert accepted teacher labels into TRL prompt-completion SFT files.

Emits conversational prompt-completion rows as specified by current TRL docs
(https://huggingface.co/docs/trl/en/dataset_formats):

    {
      "prompt": [{"role": "system"|"user", "content": "..."}, ...],
      "completion": [{"role": "assistant", "content": "..."}]
    }

so SFTTrainer can apply completion-only loss.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer, PreTrainedTokenizerBase

from schema.posting import JobPosting
from src.prompts import get_prompt

_ROOT = Path(__file__).resolve().parent.parent

# Load .env for HF_HOME / HF_TOKEN before tokenizer download
_ENV_FILE = _ROOT / ".env"
if _ENV_FILE.exists():
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

_DEFAULT_INPUT = _ROOT / "data" / "train" / "train_deduped.jsonl"
_DEFAULT_TRAIN_OUT = _ROOT / "data" / "train" / "train.jsonl"
_DEFAULT_VAL_OUT = _ROOT / "data" / "val" / "val.jsonl"
_DEFAULT_TOKENIZER = "Qwen/Qwen3-0.6B"
_FIELD_NAMES = list(JobPosting.model_fields.keys())


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _label_of(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("candidate_label") or doc.get("label") or {}


def _difficulty(doc: dict[str, Any]) -> str:
    return str(doc.get("difficulty") or doc.get("complication") or "clean")


def _stratum(doc: dict[str, Any]) -> tuple[str, str]:
    return (str(doc.get("source") or "unknown"), _difficulty(doc))


def build_example(doc: dict[str, Any]) -> dict[str, Any]:
    """TRL conversational prompt-completion row (+ light metadata).

    Must match ``src.run_eval`` serving shape: a single user message whose
    content is ``get_prompt("tuned_v1", text)`` (instruction + document),
    with ``enable_thinking=False``. Do not put the instruction in ``system`` —
    that silently diverges from inference.
    """
    label = _label_of(doc)
    completion_text = json.dumps(label, ensure_ascii=False, sort_keys=True)
    return {
        "prompt": [
            {"role": "user", "content": get_prompt("tuned_v1", doc["text"])},
        ],
        "completion": [
            {"role": "assistant", "content": completion_text},
        ],
        # metadata (ignored by TRL loss; useful for slicing / debugging)
        "doc_id": doc.get("doc_id"),
        "source": doc.get("source"),
        "lang": doc.get("lang"),
        "difficulty": _difficulty(doc),
    }


def _full_messages(example: dict[str, Any]) -> list[dict[str, str]]:
    return list(example["prompt"]) + list(example["completion"])


def render_chat(
    example: dict[str, Any],
    tokenizer: PreTrainedTokenizerBase,
) -> str:
    return tokenizer.apply_chat_template(
        _full_messages(example),
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=False,
    )


def render_serving_prefix(
    example: dict[str, Any],
    tokenizer: PreTrainedTokenizerBase,
) -> str:
    """What vLLM/run_eval feed the model before generation (thinking off)."""
    return tokenizer.apply_chat_template(
        example["prompt"],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


def assert_train_matches_serve(
    example: dict[str, Any],
    tokenizer: PreTrainedTokenizerBase,
) -> None:
    """Fail loud if the training render diverges from the inference prefix."""
    serving = render_serving_prefix(example, tokenizer)
    full = render_chat(example, tokenizer)
    if not full.startswith(serving):
        raise AssertionError(
            "TRAIN/SERVE TEMPLATE MISMATCH: full training render does not "
            "start with the inference generation prefix.\n"
            f"serving_prefix={serving!r}\n"
            f"training_full={full!r}"
        )


def token_length(
    example: dict[str, Any],
    tokenizer: PreTrainedTokenizerBase,
) -> int:
    rendered = render_chat(example, tokenizer)
    return len(tokenizer.encode(rendered))


def _percentile(values: list[int], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (k - f) * (s[c] - s[f])


def stratified_split(
    docs: list[dict[str, Any]],
    n_val: int,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split into (train, val) stratified by (source, difficulty)."""
    if n_val <= 0:
        return docs, []
    if n_val >= len(docs):
        return [], list(docs)

    rng = random.Random(seed)
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for d in docs:
        buckets[_stratum(d)].append(d)
    for key in buckets:
        rng.shuffle(buckets[key])

    total = len(docs)
    # Largest-remainder proportional allocation
    raw = {k: len(v) * n_val / total for k, v in buckets.items()}
    floors = {k: int(x) for k, x in raw.items()}
    # Ensure we don't ask for more than bucket size
    floors = {k: min(floors[k], len(buckets[k])) for k in floors}
    assigned = sum(floors.values())
    remainders = sorted(
        ((raw[k] - floors[k], k) for k in buckets),
        reverse=True,
    )
    while assigned < n_val:
        progressed = False
        for _, k in remainders:
            if floors[k] < len(buckets[k]):
                floors[k] += 1
                assigned += 1
                progressed = True
                if assigned >= n_val:
                    break
        if not progressed:
            break

    val: list[dict[str, Any]] = []
    train: list[dict[str, Any]] = []
    for k, pool in buckets.items():
        n = floors.get(k, 0)
        val.extend(pool[:n])
        train.extend(pool[n:])

    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def _is_null_field(label: dict[str, Any], field: str) -> bool:
    v = label.get(field)
    if field in ("required_skills", "nice_to_have_skills", "languages"):
        return v is None or v == []
    return v is None


def print_stats(examples: list[dict[str, Any]], token_lens: list[int]) -> None:
    print("\n=== SFT dataset stats ===")
    print(f"examples: {len(examples)}")
    if token_lens:
        print(
            "token length percentiles: "
            f"p50={_percentile(token_lens, 50):.0f}  "
            f"p90={_percentile(token_lens, 90):.0f}  "
            f"p95={_percentile(token_lens, 95):.0f}  "
            f"p99={_percentile(token_lens, 99):.0f}"
        )

    # Null / empty rates from assistant JSON
    null_counts = Counter()
    for ex in examples:
        label = json.loads(ex["completion"][0]["content"])
        for field in _FIELD_NAMES:
            if _is_null_field(label, field):
                null_counts[field] += 1
    n = max(len(examples), 1)
    print("\nnull/empty fraction by field:")
    for field in _FIELD_NAMES:
        print(f"  {field:<24} {null_counts[field] / n:6.1%}")

    langs = Counter(ex.get("lang") or "unknown" for ex in examples)
    print("\nlanguage distribution:")
    for lang, c in langs.most_common():
        print(f"  {lang:<12} {c:5d}  ({c / n:5.1%})")

    sources = Counter(ex.get("source") or "unknown" for ex in examples)
    print("\nsource distribution:")
    for src, c in sources.most_common():
        print(f"  {src:<12} {c:5d}  ({c / n:5.1%})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build TRL prompt-completion SFT files from accepted labels"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(_DEFAULT_INPUT if _DEFAULT_INPUT.exists() else _ROOT / "data" / "train" / "train_raw.jsonl"),
        help="Accepted (optionally deduped) JSONL",
    )
    parser.add_argument("--train-out", type=str, default=str(_DEFAULT_TRAIN_OUT))
    parser.add_argument("--val-out", type=str, default=str(_DEFAULT_VAL_OUT))
    parser.add_argument("--max-len", type=int, default=4096)
    parser.add_argument("--val-size", type=int, default=100)
    parser.add_argument("--tokenizer", type=str, default=_DEFAULT_TOKENIZER)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = _ROOT / input_path
    train_out = Path(args.train_out)
    if not train_out.is_absolute():
        train_out = _ROOT / train_out
    val_out = Path(args.val_out)
    if not val_out.is_absolute():
        val_out = _ROOT / val_out

    docs = _load_jsonl(input_path)
    print(f"[build_sft] loaded {len(docs)} docs from {input_path}")

    print(f"[build_sft] loading tokenizer {args.tokenizer} …")
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=True)

    examples: list[dict[str, Any]] = []
    token_lens: list[int] = []
    dropped_max_len = 0
    skipped_no_text = 0
    for doc in docs:
        if not doc.get("text"):
            skipped_no_text += 1
            continue
        ex = build_example(doc)
        n_tok = token_length(ex, tokenizer)
        if n_tok > args.max_len:
            dropped_max_len += 1
            continue
        examples.append(ex)
        token_lens.append(n_tok)

    print(
        f"[build_sft] dropped {dropped_max_len} examples exceeding --max-len "
        f"{args.max_len}; kept {len(examples)}"
        + (f"; skipped {skipped_no_text} with no text" if skipped_no_text else "")
    )

    # Attach token length onto parallel list aligned with examples for split
    paired = list(zip(examples, token_lens))
    # Stratify on metadata already on examples
    train_docs, val_docs = stratified_split(examples, n_val=args.val_size, seed=args.seed)

    # Rebuild token lens for train+val reporting
    def _lens_for(subset: list[dict[str, Any]]) -> list[int]:
        # map by id of dict object
        id_to_len = {id(ex): n for ex, n in paired}
        return [id_to_len[id(ex)] for ex in subset]

    train_lens = _lens_for(train_docs)
    val_lens = _lens_for(val_docs)

    _write_jsonl(train_out, train_docs)
    _write_jsonl(val_out, val_docs)
    print(f"[build_sft] wrote train={len(train_docs)} → {train_out}")
    print(f"[build_sft] wrote val={len(val_docs)} → {val_out}")

    print("\n--- train ---")
    print_stats(train_docs, train_lens)
    print("\n--- val ---")
    print_stats(val_docs, val_lens)

    # One fully-rendered training example with special tokens visible,
    # cross-checked against the inference generation prefix.
    sample = train_docs[0] if train_docs else (val_docs[0] if val_docs else None)
    if sample is not None:
        assert_train_matches_serve(sample, tokenizer)
        rendered = render_chat(sample, tokenizer)
        serving = render_serving_prefix(sample, tokenizer)
        print("\n=== inference generation prefix (repr) ===")
        print(repr(serving))
        print("\n=== fully-rendered training example (repr) ===")
        print(repr(rendered))
        print(
            "\n[build_sft] train/serve check: OK "
            "(training render starts with inference prefix; thinking disabled)"
        )


if __name__ == "__main__":
    main()
