"""Final artifacts from everything in ``results/``.

Public API
----------
- ``cost_per_1000_docs(bench_result, gpu_usd_per_hour)`` — self-hosted $/1k docs
- ``api_cost_per_1000_docs(run, pricing)`` — API $/1k from token totals + pricing.yaml
- ``training_cost_usd(costs_path)`` — sum from costs.yaml; prints the breakdown
- ``results_table(...)`` — markdown table over eval result JSONs
- ``payback_curve(...)`` — fine-tuned vs best baseline cost-vs-volume plot

CLI::

  python -m src.report
  python -m src.report --finetuned-run tuned_r32_lr2e4_unconst --baseline-run baseline_b2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import yaml

_ROOT = Path(__file__).resolve().parent.parent
_RESULTS = _ROOT / "results"
_PRICING_PATH = _ROOT / "configs" / "pricing.yaml"
_COSTS_PATH = _ROOT / "configs" / "costs.yaml"

# Eval result files only (skip benches, forgetting, adapter junk).
_SKIP_NAME_PREFIXES = ("bench_",)
_SKIP_NAME_SUFFIXES = (".summary.json",)
_SKIP_EXACT = frozenset(
    {
        "forgetting.summary.json",
    }
)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping in {path}")
    return data


def _is_eval_result(path: Path, data: dict[str, Any]) -> bool:
    name = path.name
    if name in _SKIP_EXACT:
        return False
    if any(name.startswith(p) for p in _SKIP_NAME_PREFIXES):
        return False
    if any(name.endswith(s) for s in _SKIP_NAME_SUFFIXES):
        return False
    metrics = data.get("metrics")
    return isinstance(metrics, dict) and "macro_f1" in metrics


def iter_eval_results(results_dir: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    root = results_dir or _RESULTS
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = _load_json(path)
        except (json.JSONDecodeError, OSError):
            continue
        if _is_eval_result(path, data):
            out.append((path, data))
    return out


# ---------------------------------------------------------------------------
# Costs
# ---------------------------------------------------------------------------

def docs_per_hour_from_bench(
    bench_result: dict[str, Any],
    *,
    concurrency: int | str | None = "best",
) -> float:
    """Pick mean documents/hour from a ``bench_*.json`` record."""
    configs = bench_result.get("configurations") or []
    if not configs:
        raise ValueError("bench_result has no configurations")

    def mean_dph(cfg: dict[str, Any]) -> float:
        dph = cfg.get("documents_per_hour") or {}
        if isinstance(dph, dict) and "mean" in dph:
            return float(dph["mean"])
        if isinstance(dph, (int, float)):
            return float(dph)
        raise ValueError(f"bad documents_per_hour in config: {dph!r}")

    if concurrency == "best" or concurrency is None:
        return max(mean_dph(c) for c in configs)

    target = int(concurrency)
    for cfg in configs:
        if int(cfg.get("concurrency", -1)) == target:
            return mean_dph(cfg)
    raise KeyError(f"concurrency={target} not in bench configurations")


def cost_per_1000_docs(
    bench_result: dict[str, Any],
    gpu_usd_per_hour: float,
    *,
    concurrency: int | str | None = "best",
) -> float:
    """Self-hosted: ``(gpu_usd_per_hour / docs_per_hour) * 1000``."""
    dph = docs_per_hour_from_bench(bench_result, concurrency=concurrency)
    if dph <= 0:
        raise ValueError(f"docs_per_hour must be positive, got {dph}")
    if gpu_usd_per_hour < 0:
        raise ValueError(f"gpu_usd_per_hour must be >= 0, got {gpu_usd_per_hour}")
    return (float(gpu_usd_per_hour) / dph) * 1000.0


def api_cost_per_1000_docs(
    run: dict[str, Any],
    pricing: dict[str, Any],
) -> float:
    """API: bill prompt and completion tokens separately from ``configs/pricing.yaml``."""
    model = run.get("model")
    api = (pricing.get("api") or {})
    if model not in api:
        raise KeyError(
            f"model {model!r} not in pricing.yaml api section; "
            f"known={sorted(api)}"
        )
    rates = api[model]
    in_rate = float(rates["input_per_mtok"])
    out_rate = float(rates["output_per_mtok"])

    tokens = run.get("tokens") or {}
    prompt_total = float(tokens.get("prompt_total") or 0)
    completion_total = float(tokens.get("completion_total") or 0)
    n_docs = tokens.get("n_docs")
    if not n_docs:
        # Fall back from averages if present.
        avg_p = tokens.get("prompt_avg_per_doc")
        if avg_p and prompt_total:
            n_docs = int(round(prompt_total / float(avg_p)))
        else:
            n_docs = 0
    n_docs = int(n_docs)
    if n_docs <= 0:
        raise ValueError(f"run {run.get('run_id')!r} missing tokens.n_docs")

    usd_total = (prompt_total / 1_000_000.0) * in_rate + (
        completion_total / 1_000_000.0
    ) * out_rate
    return (usd_total / n_docs) * 1000.0


def training_cost_usd(
    costs_path: Path | None = None,
    *,
    print_breakdown: bool = True,
) -> float:
    """Sum one-time costs from ``configs/costs.yaml``. Always prints the breakdown."""
    path = costs_path or _COSTS_PATH
    data = _load_yaml(path)

    teacher = float(data.get("teacher_api_usd") or 0.0)
    gpu_rows = data.get("gpu_hours") or []
    gpu_total = 0.0
    gpu_lines: list[tuple[str, float, float, float]] = []
    for row in gpu_rows:
        hours = float(row["hours"])
        rate = float(row["usd_per_hour"])
        sub = hours * rate
        gpu_total += sub
        gpu_lines.append((str(row.get("label", "gpu")), hours, rate, sub))

    lab = data.get("labelling") or {}
    lab_hours = float(lab.get("hours") or 0.0)
    lab_rate = float(lab.get("usd_per_hour") or 0.0)
    lab_total = lab_hours * lab_rate
    lab_notes = str(lab.get("notes") or "")

    total = teacher + gpu_total + lab_total

    if print_breakdown:
        print("Training cost breakdown")
        print(f"  source: {path}")
        print(f"  teacher API:              ${teacher:,.4f}")
        print("  GPU hours:")
        if not gpu_lines:
            print("    (none)")
        for label, hours, rate, sub in gpu_lines:
            print(
                f"    - {label}: {hours:.3f} h × ${rate:.4f}/h = ${sub:,.4f}"
            )
        print(f"  GPU subtotal:             ${gpu_total:,.4f}")
        note = f"  ({lab_notes})" if lab_notes else ""
        print(
            f"  labelling: {lab_hours:.2f} h × ${lab_rate:.2f}/h "
            f"= ${lab_total:,.4f}{note}"
        )
        print(f"  TOTAL:                    ${total:,.4f}")

    return total


def _usd_per_1000_for_run(
    run: dict[str, Any],
    pricing: dict[str, Any],
    *,
    results_dir: Path,
) -> float | None:
    """Resolve $/1000 docs: API token pricing, else bench×GPU, else stored cost."""
    backend = (run.get("decoding") or {}).get("backend")
    model = run.get("model") or ""
    api_models = set((pricing.get("api") or {}).keys())

    is_api = backend == "api" or model in api_models
    if is_api and model in api_models:
        try:
            return api_cost_per_1000_docs(run, pricing)
        except (KeyError, ValueError):
            pass

    run_id = run.get("run_id") or ""
    benches = pricing.get("serving_benches") or {}
    gpu_rate = float(pricing.get("gpu_usd_per_hour") or 0.0)
    if run_id in benches and gpu_rate > 0:
        spec = benches[run_id]
        bench_id = spec.get("bench_run_id") or run_id
        conc = spec.get("concurrency", "best")
        bench_path = results_dir / f"bench_{bench_id}.json"
        if bench_path.is_file():
            try:
                return cost_per_1000_docs(
                    _load_json(bench_path),
                    gpu_rate,
                    concurrency=conc,
                )
            except (KeyError, ValueError):
                pass

    stored = (run.get("cost") or {}).get("usd_per_1000_docs")
    if stored is not None and float(stored) > 0:
        return float(stored)
    return None


# ---------------------------------------------------------------------------
# Results table
# ---------------------------------------------------------------------------

def results_table(
    results_dir: Path | None = None,
    *,
    pricing_path: Path | None = None,
) -> str:
    """Markdown table for every eval result JSON under ``results/``."""
    root = results_dir or _RESULTS
    pricing = _load_yaml(pricing_path or _PRICING_PATH)
    rows_data: list[dict[str, Any]] = []

    for path, run in iter_eval_results(root):
        metrics = run.get("metrics") or {}
        tokens = run.get("tokens") or {}
        timing = run.get("timing") or {}
        decoding = run.get("decoding") or {}
        usd = _usd_per_1000_for_run(run, pricing, results_dir=root)
        rows_data.append(
            {
                "run": run.get("run_id") or path.stem,
                "model": run.get("model") or "",
                "adapter": run.get("adapter") if run.get("adapter") is not None else "—",
                "constrained": decoding.get("constrained"),
                "macro_f1": metrics.get("macro_f1"),
                "hallucination": metrics.get("hallucination_rate"),
                "exact_match": metrics.get("exact_record_match"),
                "p95_latency_ms": timing.get("p95_latency_ms"),
                "prompt_tokens": tokens.get("prompt_avg_per_doc", tokens.get("prompt_total")),
                "usd_per_1000": usd,
            }
        )

    headers = [
        "run",
        "model",
        "adapter",
        "constrained",
        "macro-F1",
        "hallucination",
        "exact-match",
        "p95 latency",
        "prompt tokens",
        "$/1000 docs",
    ]

    def fmt(val: Any, kind: str) -> str:
        if val is None or val == "":
            return "—"
        if kind == "bool":
            return "true" if val else "false"
        if kind == "f3":
            return f"{float(val):.3f}"
        if kind == "f1":
            return f"{float(val):.1f}"
        if kind == "f2":
            return f"{float(val):.2f}"
        if kind == "f4":
            return f"{float(val):.4f}"
        if kind == "i0":
            return f"{float(val):.0f}"
        return str(val)

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for r in rows_data:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(r["run"]),
                    str(r["model"]),
                    str(r["adapter"]),
                    fmt(r["constrained"], "bool"),
                    fmt(r["macro_f1"], "f3"),
                    fmt(r["hallucination"], "f3"),
                    fmt(r["exact_match"], "f3"),
                    fmt(r["p95_latency_ms"], "f1"),
                    fmt(r["prompt_tokens"], "i0"),
                    fmt(r["usd_per_1000"], "f4"),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Payback curve
# ---------------------------------------------------------------------------

def payback_curve(
    training_cost_usd: float,
    configs: list[dict[str, Any]],
    *,
    out_path: Path | None = None,
    n_max: int | None = None,
) -> Path:
    """Plot ``total_cost(n) = training_cost + n * per_doc_cost`` for FT vs baseline.

    ``configs`` must contain exactly two entries with keys:
    ``name``, ``per_doc_cost_usd``, ``upfront_usd`` (0 for baseline).
    The fine-tuned entry should carry the training cost as ``upfront_usd``.
    """
    if len(configs) != 2:
        raise ValueError("payback_curve expects exactly two configs (FT + baseline)")
    for cfg in configs:
        if "name" not in cfg or "per_doc_cost_usd" not in cfg:
            raise ValueError(f"config missing name/per_doc_cost_usd: {cfg!r}")

    # Identify which is fine-tuned (non-zero upfront) vs baseline.
    ft = max(configs, key=lambda c: float(c.get("upfront_usd") or 0.0))
    base = min(configs, key=lambda c: float(c.get("upfront_usd") or 0.0))
    if ft is base:
        # Equal upfront — treat first as FT using passed training_cost_usd.
        ft, base = configs[0], configs[1]
        ft = {**ft, "upfront_usd": training_cost_usd}

    c_ft = float(ft["per_doc_cost_usd"])
    c_base = float(base["per_doc_cost_usd"])
    upfront = float(ft.get("upfront_usd") or training_cost_usd)

    if c_base <= c_ft:
        # No crossover — FT never cheaper per doc; still plot a useful range.
        crossover: float | None = None
        n_max = n_max or 200_000
    else:
        crossover = upfront / (c_base - c_ft)
        n_max = n_max or int(max(crossover * 2.0, 10_000))

    xs = list(range(0, n_max + 1, max(1, n_max // 400)))
    if xs[-1] != n_max:
        xs.append(n_max)
    y_ft = [upfront + n * c_ft for n in xs]
    y_base = [float(base.get("upfront_usd") or 0.0) + n * c_base for n in xs]

    out = out_path or (_RESULTS / "payback.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(xs, y_ft, label=str(ft["name"]), color="C0", linewidth=2)
    ax.plot(xs, y_base, label=str(base["name"]), color="C1", linewidth=2)

    if crossover is not None and 0 < crossover <= n_max:
        y_cross = upfront + crossover * c_ft
        ax.axvline(crossover, color="0.4", linestyle="--", linewidth=1)
        ax.plot([crossover], [y_cross], "o", color="0.2", markersize=6)
        ax.annotate(
            f"crossover @ {crossover:,.0f} docs\n(${y_cross:,.2f})",
            xy=(crossover, y_cross),
            xytext=(10, 20),
            textcoords="offset points",
            fontsize=9,
            arrowprops={"arrowstyle": "->", "color": "0.3"},
        )
    else:
        ax.annotate(
            "no crossover (FT $/doc ≥ baseline)",
            xy=(0.05, 0.95),
            xycoords="axes fraction",
            fontsize=9,
            va="top",
        )

    ax.set_xlabel("Documents processed (n)")
    ax.set_ylabel("Total cost (USD)")
    ax.set_title("Payback: fine-tuned vs best baseline")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _per_doc_cost(usd_per_1000: float | None) -> float | None:
    if usd_per_1000 is None:
        return None
    return float(usd_per_1000) / 1000.0


def build_payback_configs(
    *,
    finetuned_run: dict[str, Any],
    baseline_run: dict[str, Any],
    training_cost: float,
    pricing: dict[str, Any],
    results_dir: Path,
) -> list[dict[str, Any]]:
    ft_usd1k = _usd_per_1000_for_run(finetuned_run, pricing, results_dir=results_dir)
    base_usd1k = _usd_per_1000_for_run(baseline_run, pricing, results_dir=results_dir)
    if ft_usd1k is None:
        raise ValueError(
            f"cannot resolve $/1000 for fine-tuned run "
            f"{finetuned_run.get('run_id')!r} — need bench JSON or API pricing"
        )
    if base_usd1k is None:
        raise ValueError(
            f"cannot resolve $/1000 for baseline run "
            f"{baseline_run.get('run_id')!r} — need bench JSON or API pricing"
        )
    return [
        {
            "name": f"fine-tuned ({finetuned_run.get('run_id')})",
            "per_doc_cost_usd": _per_doc_cost(ft_usd1k),
            "upfront_usd": training_cost,
            "usd_per_1000": ft_usd1k,
        },
        {
            "name": f"baseline ({baseline_run.get('run_id')})",
            "per_doc_cost_usd": _per_doc_cost(base_usd1k),
            "upfront_usd": 0.0,
            "usd_per_1000": base_usd1k,
        },
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit results markdown table + payback.png from results/"
    )
    parser.add_argument("--results-dir", type=str, default=str(_RESULTS))
    parser.add_argument("--pricing", type=str, default=str(_PRICING_PATH))
    parser.add_argument("--costs", type=str, default=str(_COSTS_PATH))
    parser.add_argument(
        "--finetuned-run",
        type=str,
        default="tuned_r32_lr2e4_unconst",
        help="run_id of the fine-tuned eval result for the payback curve",
    )
    parser.add_argument(
        "--baseline-run",
        type=str,
        default="baseline_b2",
        help="run_id of the competing baseline for the payback curve",
    )
    parser.add_argument(
        "--table-out",
        type=str,
        default=str(_RESULTS / "results_table.md"),
        help="Where to write the markdown table",
    )
    parser.add_argument(
        "--payback-out",
        type=str,
        default=str(_RESULTS / "payback.png"),
    )
    parser.add_argument(
        "--skip-payback",
        action="store_true",
        help="Only emit the table (e.g. before benches exist)",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    pricing_path = Path(args.pricing)
    costs_path = Path(args.costs)

    table = results_table(results_dir, pricing_path=pricing_path)
    table_path = Path(args.table_out)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.write_text(table, encoding="utf-8")
    print(table)
    print(f"[report] wrote {table_path}")

    training = training_cost_usd(costs_path, print_breakdown=True)

    if args.skip_payback:
        print("[report] skip-payback set; not writing payback.png")
        return

    by_id = {
        (run.get("run_id") or path.stem): run
        for path, run in iter_eval_results(results_dir)
    }
    if args.finetuned_run not in by_id:
        raise SystemExit(f"fine-tuned run not found: {args.finetuned_run}")
    if args.baseline_run not in by_id:
        raise SystemExit(f"baseline run not found: {args.baseline_run}")

    pricing = _load_yaml(pricing_path)
    try:
        configs = build_payback_configs(
            finetuned_run=by_id[args.finetuned_run],
            baseline_run=by_id[args.baseline_run],
            training_cost=training,
            pricing=pricing,
            results_dir=results_dir,
        )
    except ValueError as exc:
        raise SystemExit(
            f"{exc}\n"
            "Fill configs/pricing.yaml serving_benches + run src.bench, "
            "or pass --skip-payback."
        ) from exc

    print(
        f"[report] payback per-doc: "
        f"FT=${configs[0]['per_doc_cost_usd']:.6f}  "
        f"baseline=${configs[1]['per_doc_cost_usd']:.6f}"
    )
    out = payback_curve(
        training,
        configs,
        out_path=Path(args.payback_out),
    )
    print(f"[report] wrote {out}")


if __name__ == "__main__":
    main()
