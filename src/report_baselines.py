"""Compare baseline_*.json result files and print the first comparison table.

Usage:
  python -m src.report_baselines
  python -m src.report_baselines --glob 'results/baseline_*.json'
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Canonical baseline order
_BASELINE_ORDER = ("baseline_b0", "baseline_b1", "baseline_b2", "baseline_b3")

_LABELS = {
    "baseline_b0": "B0 1.7B zero-shot unconst",
    "baseline_b1": "B1 8B few-shot unconst",
    "baseline_b2": "B2 8B few-shot constr",
    "baseline_b3": "B3 teacher constrained",
}


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _row(run: dict) -> dict:
    m = run.get("metrics") or {}
    t = run.get("tokens") or {}
    timing = run.get("timing") or {}
    cost = run.get("cost") or {}
    return {
        "run_id": run.get("run_id", ""),
        "model": run.get("model", ""),
        "prompt": run.get("prompt_version", ""),
        "constrained": (run.get("decoding") or {}).get("constrained"),
        "macro_f1": m.get("macro_f1"),
        "schema_valid": m.get("schema_valid_rate"),
        "halluc": m.get("hallucination_rate"),
        "omit": m.get("omission_rate"),
        "exact": m.get("exact_record_match"),
        "prompt_avg": t.get("prompt_avg_per_doc"),
        "completion_avg": t.get("completion_avg_per_doc"),
        "p50_ms": timing.get("p50_latency_ms"),
        "p95_ms": timing.get("p95_latency_ms"),
        "usd_per_1000": cost.get("usd_per_1000_docs"),
    }


def print_table(rows: list[dict]) -> None:
    headers = [
        ("run", 28),
        ("macro_f1", 9),
        ("valid", 7),
        ("promptΔ", 9),
        ("cmplΔ", 8),
        ("p50ms", 8),
        ("$/1k", 8),
    ]
    print(" ".join(f"{name:<{width}}" for name, width in headers))
    print("-" * (sum(w for _, w in headers) + len(headers) - 1))

    for r in rows:
        label = _LABELS.get(r["run_id"], r["run_id"])[:28]

        def fmt(x, nd=3):
            if x is None:
                return "—"
            if isinstance(x, float):
                return f"{x:.{nd}f}"
            return str(x)

        cells = [
            f"{label:<28}",
            f"{fmt(r['macro_f1']):>9}",
            f"{fmt(r['schema_valid']):>7}",
            f"{fmt(r['prompt_avg'], 0):>9}",
            f"{fmt(r['completion_avg'], 0):>8}",
            f"{fmt(r['p50_ms'], 0):>8}",
            f"{fmt(r['usd_per_1000'], 2):>8}",
        ]
        print(" ".join(cells))

    prompt_avgs = [r["prompt_avg"] for r in rows if r.get("prompt_avg") is not None]
    if len(prompt_avgs) >= 2:
        hi = max(prompt_avgs)
        lo = min(prompt_avgs)
        if hi > 0 and lo > 0:
            print()
            print(
                f"Prompt tokens/doc: high={hi:.0f}  low={lo:.0f}  "
                f"ratio={hi / lo:.1f}×  ← this collapse is the fine-tune cost win"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare baseline result JSON files")
    parser.add_argument(
        "--dir",
        type=str,
        default=str(_ROOT / "results"),
        help="Directory containing baseline_*.json",
    )
    args = parser.parse_args()
    results_dir = Path(args.dir)

    paths = sorted(results_dir.glob("baseline_*.json"))
    if not paths:
        print(f"No baseline_*.json files in {results_dir}")
        print("Expected run_ids: baseline_b0 … baseline_b3")
        return

    by_id = {}
    for p in paths:
        run = _load(p)
        by_id[run.get("run_id") or p.stem] = run

    ordered = []
    for rid in _BASELINE_ORDER:
        if rid in by_id:
            ordered.append(_row(by_id[rid]))
    for rid, run in sorted(by_id.items()):
        if rid not in _BASELINE_ORDER:
            ordered.append(_row(run))

    print_table(ordered)
    print()
    print(f"Loaded {len(ordered)} runs from {results_dir}")
    missing = [r for r in _BASELINE_ORDER if r not in by_id]
    if missing:
        print(f"Still missing: {', '.join(missing)}")


if __name__ == "__main__":
    main()
