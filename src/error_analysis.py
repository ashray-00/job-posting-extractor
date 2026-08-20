"""Error analysis over a run's preds JSONL + frozen eval set.

  python -m src.error_analysis --run-id baseline_b2
  python -m src.error_analysis --compare baseline_b1 baseline_b2

Writes ``results/{run_id}.errors.md`` (or a compare markdown for two runs).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.metrics import (
    FIELDS,
    _ALL_NULL,
    _is_null,
    _label_dict,
    _values_equal,
    evaluate,
)
from src.normalize import normalize_text

_ROOT = Path(__file__).resolve().parent.parent
_RESULTS = _ROOT / "results"
_DEFAULT_EVAL = _ROOT / "data" / "eval" / "eval_v1.jsonl"

ErrorKind = str  # "hallucination" | "omission" | "wrong_value"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _fmt_val(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _classify_field(
    field: str,
    pred_v: Any,
    gold_v: Any,
    vocab: dict[str, str],
) -> ErrorKind | None:
    """Return error kind, or None if the field is correct."""
    p_null = _is_null(field, pred_v)
    g_null = _is_null(field, gold_v)
    if p_null and g_null:
        return None
    if g_null and not p_null:
        return "hallucination"
    if not g_null and p_null:
        return "omission"
    if _values_equal(field, pred_v, gold_v, vocab):
        return None
    return "wrong_value"


def _join_preds_eval(
    preds: list[dict[str, Any]],
    eval_docs: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]]:
    """Align by doc_id → (eval_doc, parsed_pred_or_None, pred_row)."""
    by_id = {r["doc_id"]: r for r in preds}
    missing = [d["doc_id"] for d in eval_docs if d["doc_id"] not in by_id]
    if missing:
        raise SystemExit(
            f"preds missing {len(missing)} eval doc_ids (e.g. {missing[:5]})"
        )
    out = []
    for doc in eval_docs:
        row = by_id[doc["doc_id"]]
        parsed = row.get("parsed")
        if parsed is not None and not isinstance(parsed, dict):
            parsed = None
        out.append((doc, parsed, row))
    return out


def field_error_counts(
    joined: list[tuple[dict, dict | None, dict]],
    vocab: dict[str, str],
) -> dict[str, dict[str, int]]:
    counts = {
        f: {"hallucination": 0, "omission": 0, "wrong_value": 0, "total": 0}
        for f in FIELDS
    }
    for doc, pred, _ in joined:
        p_lab = dict(_ALL_NULL) if pred is None else _label_dict(pred)
        g_lab = _label_dict(doc)
        for field in FIELDS:
            kind = _classify_field(
                field, p_lab.get(field), g_lab.get(field), vocab
            )
            if kind is None:
                continue
            counts[field][kind] += 1
            counts[field]["total"] += 1
    return counts


def _macro_f1_table(
    preds: list[dict | None],
    golds: list[dict],
    vocab: dict[str, str],
    slice_by: str,
) -> list[tuple[str, float, int]]:
    sliced = evaluate(preds, golds, vocab, slice_by=slice_by)
    rows: list[tuple[str, float, int]] = []
    for tag, metrics in sliced.items():
        n = sum(1 for g in golds if str(g.get(slice_by, "unknown")) == tag)
        rows.append((tag, float(metrics["macro_f1"]), n))
    rows.sort(key=lambda r: r[0])
    return rows


def _search_span(text: str, needles: list[str], window: int = 80) -> str:
    """Excerpt around the first needle found in text (case-insensitive)."""
    if not text:
        return "(empty document)"
    lower = text.lower()
    best: tuple[int, str] | None = None
    for raw in needles:
        if raw is None:
            continue
        s = str(raw).strip()
        if len(s) < 2:
            continue
        # Try a few surface forms
        variants = {s, s.lower(), normalize_text(s)}
        if s.replace(".", "").isdigit() or s.isdigit():
            # European money / plain int
            variants.add(f"{int(float(s)):,}".replace(",", "."))
            variants.add(str(int(float(s))))
        for v in variants:
            if not v:
                continue
            idx = lower.find(v.lower())
            if idx < 0:
                continue
            if best is None or idx < best[0]:
                best = (idx, v)
    if best is None:
        # Fallback: head of document
        excerpt = text[: 2 * window].replace("\n", " ")
        return excerpt + ("…" if len(text) > 2 * window else "")

    idx, _ = best
    start = max(0, idx - window)
    end = min(len(text), idx + window)
    chunk = text[start:end].replace("\n", " ")
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + chunk + suffix


def _needles_for_field(field: str, pred_v: Any, gold_v: Any) -> list[str]:
    needles: list[str] = []
    for v in (gold_v, pred_v):
        if _is_null(field, v):
            continue
        if field in ("required_skills", "nice_to_have_skills"):
            needles.extend(str(x) for x in (v or []))
        elif field == "languages":
            for item in v or []:
                if isinstance(item, dict):
                    needles.append(str(item.get("lang", "")))
                    # common names
                    lang = str(item.get("lang", "")).lower()
                    needles.extend(
                        {
                            "en": ["english", "englisch"],
                            "de": ["german", "deutsch"],
                            "fr": ["french", "französisch"],
                        }.get(lang, [])
                    )
        else:
            needles.append(str(v))
    return needles


def _error_examples_for_field(
    field: str,
    joined: list[tuple[dict, dict | None, dict]],
    vocab: dict[str, str],
    k: int = 10,
) -> list[dict[str, Any]]:
    """Collect error examples; prefer wrong_value, then hallucination, then omission."""
    rank = {"wrong_value": 0, "hallucination": 1, "omission": 2}
    examples: list[dict[str, Any]] = []
    for doc, pred, _ in joined:
        p_lab = dict(_ALL_NULL) if pred is None else _label_dict(pred)
        g_lab = _label_dict(doc)
        pv, gv = p_lab.get(field), g_lab.get(field)
        kind = _classify_field(field, pv, gv, vocab)
        if kind is None:
            continue
        excerpt = _search_span(doc.get("text") or "", _needles_for_field(field, pv, gv))
        examples.append(
            {
                "doc_id": doc["doc_id"],
                "kind": kind,
                "pred": pv,
                "gold": gv,
                "excerpt": excerpt,
                "source": doc.get("source"),
                "difficulty": doc.get("difficulty"),
            }
        )
    examples.sort(key=lambda e: (rank.get(e["kind"], 9), e["doc_id"]))
    return examples[:k]


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def build_errors_report(
    run_id: str,
    *,
    eval_path: Path,
    vocab: dict[str, str] | None = None,
) -> Path:
    vocab = vocab or {}
    preds_path = _RESULTS / f"{run_id}.preds.jsonl"
    if not preds_path.exists():
        raise SystemExit(f"Missing preds: {preds_path}")

    preds_rows = _load_jsonl(preds_path)
    eval_docs = _load_jsonl(eval_path)
    joined = _join_preds_eval(preds_rows, eval_docs)

    pred_list = [p for _, p, _ in joined]
    counts = field_error_counts(joined, vocab)
    overall = evaluate(pred_list, eval_docs, vocab)
    by_diff = _macro_f1_table(pred_list, eval_docs, vocab, "difficulty")
    by_src = _macro_f1_table(pred_list, eval_docs, vocab, "source")

    # Five worst fields by total errors (tie-break: lower F1)
    field_f1 = {
        f: float(overall["field_f1"][f]["f1"]) for f in FIELDS  # type: ignore[index]
    }
    worst_fields = sorted(
        FIELDS,
        key=lambda f: (-counts[f]["total"], field_f1[f]),
    )[:5]

    lines: list[str] = [
        f"# Error analysis — `{run_id}`",
        "",
        f"Eval: `{eval_path}`  ·  preds: `{preds_path.name}`  ·  n={len(eval_docs)}",
        "",
        f"Overall macro-F1: **{overall['macro_f1']:.4f}**  ·  "
        f"schema_valid_rate: **{overall['schema_valid_rate']:.3f}**  ·  "
        f"hallucination_rate: **{overall['hallucination_rate']:.4f}**  ·  "
        f"omission_rate: **{overall['omission_rate']:.4f}**",
        "",
        "## Errors per field",
        "",
        _md_table(
            ["field", "hallucination", "omission", "wrong_value", "total", "field_f1"],
            [
                [
                    f,
                    counts[f]["hallucination"],
                    counts[f]["omission"],
                    counts[f]["wrong_value"],
                    counts[f]["total"],
                    f"{field_f1[f]:.3f}",
                ]
                for f in FIELDS
            ],
        ),
        "",
        "## Macro-F1 by difficulty",
        "",
        _md_table(
            ["difficulty", "macro_f1", "n"],
            [[tag, f"{m:.4f}", n] for tag, m, n in by_diff],
        ),
        "",
        "## Macro-F1 by source",
        "",
        _md_table(
            ["source", "macro_f1", "n"],
            [[tag, f"{m:.4f}", n] for tag, m, n in by_src],
        ),
        "",
        "## Worst fields — example dumps",
        "",
        f"Five fields with the most errors: {', '.join(f'`{f}`' for f in worst_fields)}.",
        "",
    ]

    for field in worst_fields:
        lines.append(f"### `{field}` ({counts[field]['total']} errors)")
        lines.append("")
        examples = _error_examples_for_field(field, joined, vocab, k=10)
        if not examples:
            lines.append("_No errors on this field._")
            lines.append("")
            continue
        for i, ex in enumerate(examples, start=1):
            lines.append(
                f"#### {i}. `{ex['doc_id']}` — {ex['kind']} "
                f"(source={ex.get('source')}, difficulty={ex.get('difficulty')})"
            )
            lines.append("")
            lines.append(f"- **gold:** `{_fmt_val(ex['gold'])}`")
            lines.append(f"- **pred:** `{_fmt_val(ex['pred'])}`")
            lines.append("- **excerpt:**")
            lines.append("")
            lines.append("```")
            lines.append(ex["excerpt"])
            lines.append("```")
            lines.append("")

    out = _RESULTS / f"{run_id}.errors.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _field_correct(
    field: str,
    pred: dict | None,
    gold_doc: dict,
    vocab: dict[str, str],
) -> bool:
    p_lab = dict(_ALL_NULL) if pred is None else _label_dict(pred)
    g_lab = _label_dict(gold_doc)
    return _classify_field(field, p_lab.get(field), g_lab.get(field), vocab) is None


def build_compare_report(
    run_a: str,
    run_b: str,
    *,
    eval_path: Path,
    vocab: dict[str, str] | None = None,
) -> Path:
    vocab = vocab or {}
    eval_docs = _load_jsonl(eval_path)
    preds_a = _load_jsonl(_RESULTS / f"{run_a}.preds.jsonl")
    preds_b = _load_jsonl(_RESULTS / f"{run_b}.preds.jsonl")
    join_a = {d["doc_id"]: p for d, p, _ in _join_preds_eval(preds_a, eval_docs)}
    join_b = {d["doc_id"]: p for d, p, _ in _join_preds_eval(preds_b, eval_docs)}

    # Examples where one model is fully-record-correct? User asked: where one is
    # right and the other wrong — interpret per-field, list notable flips.
    a_only: list[dict[str, Any]] = []  # A right, B wrong
    b_only: list[dict[str, Any]] = []  # B right, A wrong

    for doc in eval_docs:
        did = doc["doc_id"]
        pa, pb = join_a[did], join_b[did]
        for field in FIELDS:
            a_ok = _field_correct(field, pa, doc, vocab)
            b_ok = _field_correct(field, pb, doc, vocab)
            if a_ok == b_ok:
                continue
            g_lab = _label_dict(doc)
            p_a = dict(_ALL_NULL) if pa is None else _label_dict(pa)
            p_b = dict(_ALL_NULL) if pb is None else _label_dict(pb)
            entry = {
                "doc_id": did,
                "field": field,
                "gold": g_lab.get(field),
                "pred_a": p_a.get(field),
                "pred_b": p_b.get(field),
                "source": doc.get("source"),
                "difficulty": doc.get("difficulty"),
            }
            if a_ok and not b_ok:
                a_only.append(entry)
            else:
                b_only.append(entry)

    lines: list[str] = [
        f"# Cross-model comparison — `{run_a}` vs `{run_b}`",
        "",
        f"Eval: `{eval_path}`",
        "",
        f"- Fields where **{run_a} right / {run_b} wrong**: **{len(a_only)}**",
        f"- Fields where **{run_b} right / {run_a} wrong**: **{len(b_only)}**",
        "",
    ]

    def _section(title: str, rows: list[dict[str, Any]], limit: int = 40) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not rows:
            lines.append("_None._")
            lines.append("")
            return
        # Aggregate by field
        by_f: dict[str, int] = defaultdict(int)
        for r in rows:
            by_f[r["field"]] += 1
        lines.append(_md_table(
            ["field", "count"],
            [[f, by_f[f]] for f in sorted(by_f, key=lambda x: -by_f[x])],
        ))
        lines.append("")
        lines.append(f"Showing up to {limit} examples:")
        lines.append("")
        for i, r in enumerate(rows[:limit], start=1):
            lines.append(
                f"{i}. `{r['doc_id']}` · `{r['field']}` · "
                f"gold=`{_fmt_val(r['gold'])}` · "
                f"{run_a}=`{_fmt_val(r['pred_a'])}` · "
                f"{run_b}=`{_fmt_val(r['pred_b'])}`"
            )
        if len(rows) > limit:
            lines.append(f"\n_… +{len(rows) - limit} more_")
        lines.append("")

    _section(f"{run_a} right, {run_b} wrong", a_only)
    _section(f"{run_b} right, {run_a} wrong", b_only)

    out = _RESULTS / f"{run_a}__vs__{run_b}.compare.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-run error analysis markdown")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("RUN_A", "RUN_B"),
        default=None,
        help="Cross-model mode: list fields where one run is right and the other wrong",
    )
    parser.add_argument(
        "--eval-set",
        type=str,
        default=str(_DEFAULT_EVAL),
    )
    parser.add_argument(
        "--esco-vocab",
        type=str,
        default=None,
        help="Optional alias→canonical TSV for skill normalisation",
    )
    args = parser.parse_args()

    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = _ROOT / eval_path

    vocab: dict[str, str] = {}
    if args.esco_vocab:
        from src.normalize import load_esco_vocab

        vocab = load_esco_vocab(args.esco_vocab)

    if args.compare:
        out = build_compare_report(args.compare[0], args.compare[1], eval_path=eval_path, vocab=vocab)
        print(f"[error_analysis] wrote {out}")
        return

    if not args.run_id:
        raise SystemExit("Provide --run-id or --compare RUN_A RUN_B")

    out = build_errors_report(args.run_id, eval_path=eval_path, vocab=vocab)
    print(f"[error_analysis] wrote {out}")


if __name__ == "__main__":
    main()
