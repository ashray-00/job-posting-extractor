"""Load, normalise, and sample source documents from Djinni and EMSCAD."""
from __future__ import annotations

import csv
import json
import os
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Load .env so HF_HOME is set before any HuggingFace import
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _has_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC.search(text))


def _tokenizer():
    """Lazy-load the Qwen3 tokenizer (imported only when summary is printed)."""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B", trust_remote_code=True)


# ---------------------------------------------------------------------------
# Djinni  (HuggingFace: lang-uk/recruitment-dataset-job-descriptions-english)
# ---------------------------------------------------------------------------

def load_djinni(n: int = 2000, seed: int = 42) -> list[dict[str, Any]]:
    from datasets import load_dataset

    ds = load_dataset(
        "lang-uk/recruitment-dataset-job-descriptions-english",
        split="train",
    )
    rows = [r for r in ds if len(r.get("Long Description") or "") >= 300]

    rng = random.Random(seed)
    rng.shuffle(rows)
    rows = rows[:n]

    docs: list[dict[str, Any]] = []
    for r in rows:
        text = r["Long Description"]
        docs.append({
            "doc_id": str(r.get("id", r.get("ID", ""))),
            "text": text,
            "source": "djinni",
            "lang": "mixed" if _has_cyrillic(text) else "en",
            "weak_labels": {
                "exp_years": r.get("Exp Years"),
                "english_level": r.get("English Level"),
                "primary_keyword": r.get("Primary Keyword"),
            },
        })
    return docs


# ---------------------------------------------------------------------------
# EMSCAD  (local CSV)
# ---------------------------------------------------------------------------

_EMSCAD_DEFAULT = _DATA_RAW / "emscad.csv"


def load_emscad(
    path: str | None = None,
    n: int = 2000,
    seed: int = 42,
) -> list[dict[str, Any]]:
    csv_path = Path(path) if path else _EMSCAD_DEFAULT
    if not csv_path.exists():
        print(
            f"[data_prep] EMSCAD CSV not found at {csv_path}\n"
            f"  → Download from Kaggle (shivamb/real-or-fake-fake-jobposting-prediction)\n"
            f"  → Place the CSV at: {_EMSCAD_DEFAULT}",
            file=sys.stderr,
        )
        return []

    with open(csv_path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        raw = list(reader)

    docs: list[dict[str, Any]] = []
    for i, r in enumerate(raw):
        parts = [
            r.get("description", "").strip(),
            r.get("requirements", "").strip(),
            r.get("benefits", "").strip(),
        ]
        text = "\n\n".join(p for p in parts if p)
        if len(text) < 300:
            continue
        docs.append({
            "doc_id": f"emscad_{i}",
            "text": text,
            "source": "emscad",
            "lang": "en",
            "weak_labels": {
                "employment_type": r.get("employment_type"),
                "required_experience": r.get("required_experience"),
                "required_education": r.get("required_education"),
                "telecommuting": r.get("telecommuting"),
                "location": r.get("location"),
                "salary_range": r.get("salary_range"),
            },
        })

    rng = random.Random(seed)
    rng.shuffle(docs)
    return docs[:n]


# ---------------------------------------------------------------------------
# Stratified sampling
# ---------------------------------------------------------------------------

def sample_stratified(
    docs: list[dict[str, Any]],
    n: int,
    by: str = "source",
    seed: int = 42,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict]] = {}
    for d in docs:
        buckets.setdefault(d[by], []).append(d)

    rng = random.Random(seed)
    per_bucket = max(1, n // len(buckets)) if buckets else 0
    sampled: list[dict[str, Any]] = []
    for key in sorted(buckets):
        pool = buckets[key]
        rng.shuffle(pool)
        sampled.extend(pool[:per_bucket])

    rng.shuffle(sampled)
    return sampled[:n]


# ---------------------------------------------------------------------------
# JSONL I/O  (writes only under data/raw/)
# ---------------------------------------------------------------------------

def save_jsonl(docs: list[dict[str, Any]], path: str | Path) -> Path:
    p = Path(path)
    if not str(p.resolve()).startswith(str(_DATA_RAW)):
        raise ValueError(f"save_jsonl only writes under {_DATA_RAW}, got {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"[data_prep] Wrote {len(docs)} docs → {p}")
    return p


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    docs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def _percentile(values: list[int | float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(s):
        return float(s[f])
    return s[f] + (k - f) * (s[c] - s[f])


def print_summary(docs: list[dict[str, Any]]) -> None:
    if not docs:
        print("[data_prep] No documents to summarise.")
        return

    tokenizer = _tokenizer()

    by_source: dict[str, list[dict]] = {}
    for d in docs:
        by_source.setdefault(d["source"], []).append(d)

    header = f"{'source':<10} {'count':>6} {'med_chars':>10} {'p95_chars':>10} {'med_toks':>9} {'p95_toks':>9} {'cyrillic%':>10}"
    print("\n" + header)
    print("-" * len(header))

    for src in sorted(by_source):
        group = by_source[src]
        char_lens = [len(d["text"]) for d in group]
        tok_lens = [len(tokenizer.encode(d["text"])) for d in group]
        cyr_frac = sum(1 for d in group if d["lang"] == "mixed") / len(group)

        med_c = int(statistics.median(char_lens))
        p95_c = int(_percentile(char_lens, 95))
        med_t = int(statistics.median(tok_lens))
        p95_t = int(_percentile(tok_lens, 95))

        print(f"{src:<10} {len(group):>6} {med_c:>10} {p95_c:>10} {med_t:>9} {p95_t:>9} {cyr_frac:>10.1%}")

    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Load and prepare training data")
    parser.add_argument("--djinni-n", type=int, default=2000)
    parser.add_argument("--emscad-n", type=int, default=2000)
    parser.add_argument("--emscad-path", type=str, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=str(_DATA_RAW / "corpus.jsonl"))
    args = parser.parse_args()

    print("[data_prep] Loading Djinni …")
    djinni = load_djinni(n=args.djinni_n, seed=args.seed)
    print(f"  → {len(djinni)} docs")

    print("[data_prep] Loading EMSCAD …")
    emscad = load_emscad(path=args.emscad_path, n=args.emscad_n, seed=args.seed)
    print(f"  → {len(emscad)} docs")

    all_docs = djinni + emscad
    print_summary(all_docs)

    save_jsonl(all_docs, args.out)


if __name__ == "__main__":
    main()
