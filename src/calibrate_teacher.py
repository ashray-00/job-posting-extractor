"""Calibrate the teacher prompt against weak labels from Djinni and EMSCAD."""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from typing import Any

from schema.posting import JOB_POSTING_JSON_SCHEMA
from src import teacher
from src.data_prep import load_djinni, load_emscad


# ---------------------------------------------------------------------------
# Djinni: exp_years mapping
# ---------------------------------------------------------------------------

_DJINNI_EXP_MAP: dict[str, int | None] = {
    "no_exp": 0,
    "1y": 1,
    "2y": 2,
    "3y": 3,
    "5y": 5,
    "10y": 10,
}


def _djinni_exp_to_int(val: str | None) -> int | None:
    if val is None:
        return None
    return _DJINNI_EXP_MAP.get(val.strip().lower())


# ---------------------------------------------------------------------------
# EMSCAD: employment_type mapping → our contract_type
# ---------------------------------------------------------------------------

_EMSCAD_EMPLOYMENT_MAP: dict[str, str] = {
    "full-time": "permanent",
    "part-time": "permanent",
    "contract": "contract",
    "temporary": "fixed_term",
    "other": "contract",
}


def _emscad_contract(val: str | None) -> str | None:
    if not val:
        return None
    return _EMSCAD_EMPLOYMENT_MAP.get(val.strip().lower())


# ---------------------------------------------------------------------------
# Run extraction on a batch
# ---------------------------------------------------------------------------

def _extract_batch(
    docs: list[dict[str, Any]],
    prompt_version: str = "v1",
    concurrency: int = 8,
) -> list[dict]:
    texts = [d["text"] for d in docs]
    results = asyncio.run(
        teacher.extract_many_async(
            texts,
            JOB_POSTING_JSON_SCHEMA,
            prompt_version,
            concurrency=concurrency,
        )
    )
    return [parsed for parsed, _usage in results]


# ---------------------------------------------------------------------------
# Djinni calibration
# ---------------------------------------------------------------------------

def _calibrate_djinni(docs: list[dict[str, Any]], extractions: list[dict]) -> dict:
    exact = 0
    errors: list[int] = []
    total = 0

    for doc, ext in zip(docs, extractions):
        gold = _djinni_exp_to_int(doc["weak_labels"].get("exp_years"))
        pred = ext.get("years_experience_min")
        if gold is None:
            continue
        total += 1
        if pred == gold:
            exact += 1
        if pred is not None:
            errors.append(abs(pred - gold))

    exact_rate = exact / total if total else 0
    mae = sum(errors) / len(errors) if errors else float("nan")
    return {
        "total": total,
        "exact_match_rate": round(exact_rate, 3),
        "mean_absolute_error": round(mae, 2),
        "matched_count": len(errors),
    }


# ---------------------------------------------------------------------------
# EMSCAD calibration
# ---------------------------------------------------------------------------

def _calibrate_emscad_contract(docs: list[dict[str, Any]], extractions: list[dict]) -> dict:
    agree = 0
    total = 0
    matrix: dict[str, Counter] = {}

    for doc, ext in zip(docs, extractions):
        gold = _emscad_contract(doc["weak_labels"].get("employment_type"))
        pred = ext.get("contract_type")
        if gold is None:
            continue
        total += 1
        if gold not in matrix:
            matrix[gold] = Counter()
        pred_label = pred if pred else "null"
        matrix[gold][pred_label] += 1
        if gold == pred:
            agree += 1

    return {
        "total": total,
        "agreement_rate": round(agree / total, 3) if total else 0,
        "confusion_matrix": {k: dict(v) for k, v in sorted(matrix.items())},
    }


def _calibrate_emscad_remote(docs: list[dict[str, Any]], extractions: list[dict]) -> dict:
    agree = 0
    total = 0
    matrix: dict[str, Counter] = {}

    for doc, ext in zip(docs, extractions):
        tele_raw = doc["weak_labels"].get("telecommuting")
        if tele_raw is None or tele_raw == "":
            continue
        gold_remote = tele_raw == "1"
        pred_remote = ext.get("remote_policy") is not None and ext["remote_policy"] != "onsite"

        total += 1
        gold_label = "remote" if gold_remote else "onsite"
        pred_label = "remote" if pred_remote else "onsite"
        if gold_label not in matrix:
            matrix[gold_label] = Counter()
        matrix[gold_label][pred_label] += 1
        if gold_label == pred_label:
            agree += 1

    return {
        "total": total,
        "agreement_rate": round(agree / total, 3) if total else 0,
        "confusion_matrix": {k: dict(v) for k, v in sorted(matrix.items())},
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _print_confusion(label: str, cm: dict[str, dict[str, int]]) -> None:
    all_preds = sorted({p for row in cm.values() for p in row})
    header = f"  {'gold↓ / pred→':<18}" + "".join(f"{p:>12}" for p in all_preds)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for gold in sorted(cm):
        row = "".join(f"{cm[gold].get(p, 0):>12}" for p in all_preds)
        print(f"  {gold:<18}{row}")
    print()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Calibrate teacher prompt against weak labels")
    parser.add_argument("-n", type=int, default=200, help="Docs per source")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--prompt-version", type=str, default="v1")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    print(f"[calibrate] Loading {args.n} Djinni docs …")
    djinni_docs = load_djinni(n=args.n, seed=args.seed)
    print(f"[calibrate] Loading {args.n} EMSCAD docs …")
    emscad_docs = load_emscad(n=args.n, seed=args.seed)

    print(f"[calibrate] Extracting {len(djinni_docs)} Djinni docs …")
    djinni_ext = _extract_batch(djinni_docs, args.prompt_version, args.concurrency)

    print(f"[calibrate] Extracting {len(emscad_docs)} EMSCAD docs …")
    emscad_ext = _extract_batch(emscad_docs, args.prompt_version, args.concurrency)

    # --- Djinni report ---
    djinni_res = _calibrate_djinni(djinni_docs, djinni_ext)
    print("\n" + "=" * 60)
    print("DJINNI: years_experience_min vs Exp Years")
    print("=" * 60)
    print(f"  Evaluated:         {djinni_res['total']}")
    print(f"  Exact match rate:  {djinni_res['exact_match_rate']:.1%}")
    print(f"  MAE (when both present): {djinni_res['mean_absolute_error']:.2f} years")
    print(f"  Predictions present:     {djinni_res['matched_count']}")

    # --- EMSCAD contract report ---
    emscad_contract = _calibrate_emscad_contract(emscad_docs, emscad_ext)
    print("\n" + "=" * 60)
    print("EMSCAD: contract_type vs employment_type")
    print("=" * 60)
    print(f"  Evaluated:       {emscad_contract['total']}")
    print(f"  Agreement rate:  {emscad_contract['agreement_rate']:.1%}")
    print("\n  Confusion matrix:")
    _print_confusion("contract_type", emscad_contract["confusion_matrix"])

    # --- EMSCAD remote report ---
    emscad_remote = _calibrate_emscad_remote(emscad_docs, emscad_ext)
    print("=" * 60)
    print("EMSCAD: remote_policy vs telecommuting")
    print("=" * 60)
    print(f"  Evaluated:       {emscad_remote['total']}")
    print(f"  Agreement rate:  {emscad_remote['agreement_rate']:.1%}")
    print("\n  Confusion matrix:")
    _print_confusion("remote", emscad_remote["confusion_matrix"])

    # --- Cost summary from log ---
    from pathlib import Path
    log_path = Path(__file__).resolve().parent.parent / "logs" / "teacher_calls.jsonl"
    total_cost = 0.0
    if log_path.exists():
        for line in open(log_path):
            entry = json.loads(line)
            if not entry.get("cache_hit", False):
                total_cost += entry.get("cost_usd", 0)
    print(f"\n{'=' * 60}")
    print(f"Total API cost (non-cached calls in log): ${total_cost:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
