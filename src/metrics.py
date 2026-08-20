"""Pure evaluation metrics for job-posting extraction.

Imports limited to stdlib, pydantic, and src.normalize.
No file I/O, no network, no CLI, no logging.
"""
from __future__ import annotations

from typing import Any

from src.normalize import normalize_text, skills_equal

# All JobPosting fields (16). Order is stable for tests / reporting.
FIELDS: tuple[str, ...] = (
    "title",
    "seniority",
    "contract_type",
    "workload",
    "salary_min",
    "salary_max",
    "salary_period",
    "currency",
    "remote_policy",
    "location_city",
    "location_country",
    "required_skills",
    "nice_to_have_skills",
    "years_experience_min",
    "languages",
    "visa_sponsorship",
)

_STRING_FIELDS = frozenset({"title", "currency", "location_city", "location_country"})
_LIST_STR_FIELDS = frozenset({"required_skills", "nice_to_have_skills"})
_LIST_LANG_FIELD = "languages"

_ALL_NULL: dict[str, Any] = {
    "title": None,
    "seniority": None,
    "contract_type": None,
    "workload": None,
    "salary_min": None,
    "salary_max": None,
    "salary_period": None,
    "currency": None,
    "remote_policy": None,
    "location_city": None,
    "location_country": None,
    "required_skills": [],
    "nice_to_have_skills": [],
    "years_experience_min": None,
    "languages": [],
    "visa_sponsorship": None,
}


def _label_dict(record: dict[str, Any]) -> dict[str, Any]:
    """Extract field values from a gold/pred record."""
    if "label" in record and isinstance(record["label"], dict):
        src = record["label"]
    else:
        src = record
    out = dict(_ALL_NULL)
    for f in FIELDS:
        if f in src:
            out[f] = src[f]
    return out


def _is_null(field: str, value: Any) -> bool:
    if value is None:
        return True
    if field in _LIST_STR_FIELDS or field == _LIST_LANG_FIELD:
        return value == [] or value is None
    return False


def _norm_lang_set(langs: list | None) -> set[tuple[str, Any]]:
    result: set[tuple[str, Any]] = set()
    for item in langs or []:
        if isinstance(item, dict):
            lang = normalize_text(str(item.get("lang", "")))
            level = item.get("level")
            result.add((lang, level))
    return result


def _values_equal(field: str, pred: Any, gold: Any, vocab: dict[str, str]) -> bool:
    if _is_null(field, pred) and _is_null(field, gold):
        return True
    if _is_null(field, pred) or _is_null(field, gold):
        return False

    if field in _STRING_FIELDS:
        return normalize_text(str(pred)) == normalize_text(str(gold))

    if field in _LIST_STR_FIELDS:
        tp, fp, fn = skills_equal(list(gold), list(pred), vocab)
        return not fp and not fn

    if field == _LIST_LANG_FIELD:
        return _norm_lang_set(pred) == _norm_lang_set(gold)

    # ints, enums, bools — direct comparison
    return pred == gold


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def _prf(correct: int, pred_nn: int, gold_nn: int) -> dict[str, float | int]:
    """Precision / recall / F1 for one field, with vacuous both-null → 1.0."""
    if pred_nn == 0 and gold_nn == 0:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "support": 0}
    precision = (correct / pred_nn) if pred_nn > 0 else 0.0
    recall = (correct / gold_nn) if gold_nn > 0 else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "support": gold_nn,
    }


def _skill_set_f1(
    preds: list[dict[str, Any] | None],
    golds: list[dict[str, Any]],
    vocab: dict[str, str],
) -> dict[str, float]:
    total_tp = total_fp = total_fn = 0
    for pred, gold in zip(preds, golds):
        p_label = _ALL_NULL if pred is None else _label_dict(pred)
        g_label = _label_dict(gold)
        tp, fp, fn = skills_equal(
            list(g_label.get("required_skills") or []),
            list(p_label.get("required_skills") or []),
            vocab,
        )
        total_tp += len(tp)
        total_fp += len(fp)
        total_fn += len(fn)

    if total_tp + total_fp + total_fn == 0:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    return {"precision": precision, "recall": recall, "f1": _f1(precision, recall)}


def _evaluate_slice(
    preds: list[dict[str, Any] | None],
    golds: list[dict[str, Any]],
    vocab: dict[str, str],
) -> dict[str, Any]:
    n = len(preds)
    if n != len(golds):
        raise ValueError(f"preds ({n}) and golds ({len(golds)}) length mismatch")

    schema_valid = sum(1 for p in preds if p is not None)

    # Per-field counters
    correct_nn: dict[str, int] = {f: 0 for f in FIELDS}
    pred_nn: dict[str, int] = {f: 0 for f in FIELDS}
    gold_nn: dict[str, int] = {f: 0 for f in FIELDS}

    hall_num = hall_den = 0
    omit_num = omit_den = 0
    exact_matches = 0

    for pred, gold in zip(preds, golds):
        p_label = dict(_ALL_NULL) if pred is None else _label_dict(pred)
        g_label = _label_dict(gold)

        all_correct = True
        for field in FIELDS:
            pv = p_label.get(field, _ALL_NULL[field])
            gv = g_label.get(field, _ALL_NULL[field])
            p_null = _is_null(field, pv)
            g_null = _is_null(field, gv)

            if not p_null:
                pred_nn[field] += 1
            if not g_null:
                gold_nn[field] += 1

            equal = _values_equal(field, pv, gv, vocab)
            if not equal:
                all_correct = False

            # Both-null → TN: skip P/R numerators/denominators (already handled by nn counters)
            if not p_null and not g_null and equal:
                correct_nn[field] += 1

            if g_null:
                hall_den += 1
                if not p_null:
                    hall_num += 1
            else:
                omit_den += 1
                if p_null:
                    omit_num += 1

        if all_correct:
            exact_matches += 1

    field_f1: dict[str, dict[str, float | int]] = {}
    f1_scores: list[float] = []
    for field in FIELDS:
        stats = _prf(correct_nn[field], pred_nn[field], gold_nn[field])
        field_f1[field] = stats
        f1_scores.append(float(stats["f1"]))

    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    return {
        "schema_valid_rate": schema_valid / n if n else 0.0,
        "field_f1": field_f1,
        "macro_f1": macro_f1,
        "hallucination_rate": hall_num / hall_den if hall_den else 0.0,
        "omission_rate": omit_num / omit_den if omit_den else 0.0,
        "exact_record_match": exact_matches / n if n else 0.0,
        "skill_set_f1": _skill_set_f1(preds, golds, vocab),
    }


def evaluate(
    preds: list[dict[str, Any] | None],
    golds: list[dict[str, Any]],
    vocab: dict[str, str],
    slice_by: str | None = None,
) -> dict[str, Any]:
    """Compute extraction metrics.

    ``preds[i]`` is ``None`` if the model output failed to parse (treated as all-null).

    If ``slice_by`` is set (e.g. ``\"difficulty\"``), returns
    ``{tag: <metrics dict>, ...}`` for each tag found on gold records.
    """
    if slice_by is None:
        return _evaluate_slice(preds, golds, vocab)

    buckets: dict[str, tuple[list, list]] = {}
    for pred, gold in zip(preds, golds):
        tag = str(gold.get(slice_by, "unknown"))
        if tag not in buckets:
            buckets[tag] = ([], [])
        buckets[tag][0].append(pred)
        buckets[tag][1].append(gold)

    return {
        tag: _evaluate_slice(p_list, g_list, vocab)
        for tag, (p_list, g_list) in sorted(buckets.items())
    }
