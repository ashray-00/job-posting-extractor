"""Versioned extraction prompts.

PROMPTS maps version string → prompt template. Templates that include a document
use the ``{text}`` placeholder. Few-shot examples are loaded from
``data/raw/few_shot_examples.jsonl`` and must never appear in eval or train.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_FEW_SHOT_PATH = _ROOT / "data" / "raw" / "few_shot_examples.jsonl"

# Document IDs used in few_shot_v1. Keep in sync with few_shot_examples.jsonl.
FEW_SHOT_DOC_IDS: tuple[str, ...] = (
    "synth_de_0005",  # salary absent → nulls
    "synth_de_0014",  # German posting + English requirements block
    "synth_de_0001",  # European salary range (77.935 – 89.148 €)
)


@lru_cache(maxsize=1)
def _load_few_shot_examples() -> list[dict]:
    if not _FEW_SHOT_PATH.exists():
        raise FileNotFoundError(
            f"Few-shot examples not found at {_FEW_SHOT_PATH}. "
            "Expected data/raw/few_shot_examples.jsonl."
        )
    rows: list[dict] = []
    with open(_FEW_SHOT_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    by_id = {r["doc_id"]: r for r in rows}
    missing = [d for d in FEW_SHOT_DOC_IDS if d not in by_id]
    if missing:
        raise ValueError(f"few_shot_examples.jsonl missing doc_ids: {missing}")
    return [by_id[d] for d in FEW_SHOT_DOC_IDS]


def _format_few_shot_block() -> str:
    parts: list[str] = []
    for i, ex in enumerate(_load_few_shot_examples(), start=1):
        label_json = json.dumps(ex["label"], ensure_ascii=False, indent=2)
        parts.append(
            f"### Example {i}\n"
            f"Document:\n{ex['text']}\n\n"
            f"Output:\n{label_json}"
        )
    return "\n\n".join(parts)


_ZERO_SHOT_V1 = (
    "Extract the job posting fields into JSON matching the JobPosting schema. "
    "Output nothing else. Use null for any field not stated in the document, "
    "and [] for list fields when nothing is stated.\n\n"
    "Document:\n{text}"
)

_FEW_SHOT_INSTRUCTION = (
    "Extract the job posting fields into JSON matching the JobPosting schema. "
    "Output nothing else. Use null for any field not stated in the document, "
    "and [] for list fields when nothing is stated.\n\n"
    "Study these examples carefully:\n"
    "- If no salary appears in the text, salary_min, salary_max, salary_period, "
    "and currency must be null.\n"
    "- German postings may contain an English requirements block; still extract "
    "skills from that block.\n"
    "- Parse European number formatting (e.g. 77.935 € means 77935).\n\n"
)

_TUNED_V1 = (
    "Extract JobPosting JSON from the document. "
    "null if unstated; [] if no list items. JSON only.\n\n"
    "{text}"
)


def _build_prompts() -> dict[str, str]:
    return {
        "zero_shot_v1": _ZERO_SHOT_V1,
        "few_shot_v1": _FEW_SHOT_INSTRUCTION + _format_few_shot_block() + "\n\n### Document to extract\n{text}",
        "tuned_v1": _TUNED_V1,
    }


# Built on first access so importing the module without data/ still works for
# tooling that only needs FEW_SHOT_DOC_IDS / count_tokens after data exists.
PROMPTS: dict[str, str] = {}


def _ensure_prompts() -> dict[str, str]:
    if not PROMPTS:
        PROMPTS.update(_build_prompts())
    return PROMPTS


def get_prompt(version: str, text: str) -> str:
    prompts = _ensure_prompts()
    if version not in prompts:
        raise KeyError(f"Unknown prompt version {version!r}. Available: {sorted(prompts)}")
    # Avoid str.format on few-shot JSON braces — only substitute the document slot.
    return prompts[version].replace("{text}", text)


def count_tokens(prompt_version: str, sample_text: str = "") -> int:
    """Token count of a prompt version (with optional sample document text)."""
    from transformers import AutoTokenizer

    prompts = _ensure_prompts()
    if prompt_version not in prompts:
        raise KeyError(f"Unknown prompt version {prompt_version!r}")
    rendered = prompts[prompt_version].replace("{text}", sample_text or "[DOCUMENT]")
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B", trust_remote_code=True)
    return len(tok.encode(rendered))


def print_token_table(sample_text: str = "") -> None:
    prompts = _ensure_prompts()
    rows = [(v, count_tokens(v, sample_text=sample_text)) for v in sorted(prompts)]
    print(f"{'version':<16} {'tokens':>8}")
    print("-" * 26)
    for name, n in rows:
        print(f"{name:<16} {n:>8}")


# Populate registry at import when examples are available.
try:
    _ensure_prompts()
except FileNotFoundError:
    pass


if __name__ == "__main__":
    print_token_table()
