"""Contamination check must catch a lightly paraphrased eval leak in train."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dedup import assert_no_contamination, dedupe, near_duplicates, text_hash


_EVAL_TEXT = (
    "Senior Backend Engineer (m/w/d) in Berlin. "
    "Full-time permanent role. Hybrid / Home Office possible. "
    "Salary 80.000 – 100.000 € Jahresbrutto. "
    "Required: Python, SQL, Docker. Nice to have: Kubernetes. "
    "At least 5 years of experience. "
    "Languages: English C1, German B2. "
    "Visa sponsorship not available. "
    "You will design APIs, own services end to end, and mentor juniors. "
    "Our stack also includes PostgreSQL, Redis, and Kafka for event streaming. "
    "Apply with a CV and a short note about a system you shipped."
)

# Light paraphrase: a few wording swaps; char 5-shingle Jaccard stays high.
_TRAIN_PARAPHRASE = (
    "Senior Backend Engineer (m/w/d) in Berlin. "
    "Full-time permanent role. Hybrid / Home Office possible. "
    "Salary 80.000 – 100.000 € Jahresbrutto. "
    "Required: Python, SQL, Docker. Nice to have: Kubernetes. "
    "At least 5 years of experience. "
    "Languages: English C1, German B2. "
    "Visa sponsorship is not available. "
    "You will design APIs, own services end-to-end, and mentor junior engineers. "
    "Our stack also includes PostgreSQL, Redis, and Kafka for event streaming. "
    "Apply with a CV and a brief note about a system you shipped."
)


def _write_jsonl(path: Path, docs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")


def test_near_duplicates_clusters_paraphrases():
    docs = [
        {"doc_id": "a", "text": _EVAL_TEXT},
        {"doc_id": "b", "text": _TRAIN_PARAPHRASE},
        {"doc_id": "c", "text": "Completely unrelated short posting about nursing in Lisbon."},
    ]
    clusters = near_duplicates(docs, threshold=0.85)
    # a and b should share a cluster; c alone
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2]
    pair = next(c for c in clusters if len(c) == 2)
    assert {d["doc_id"] for d in pair} == {"a", "b"}


def test_dedupe_keeps_longest():
    short = {"doc_id": "short", "text": _EVAL_TEXT}
    long = {"doc_id": "long", "text": _EVAL_TEXT + " Extra closing paragraph with more detail."}
    other = {"doc_id": "other", "text": "Unrelated role for a barista in Porto with flexible hours."}
    kept = dedupe([short, long, other], threshold=0.85)
    ids = {d["doc_id"] for d in kept}
    assert "long" in ids
    assert "short" not in ids
    assert "other" in ids
    assert len(kept) == 2


def test_assert_no_contamination_catches_paraphrased_eval_leak(tmp_path: Path):
    eval_path = tmp_path / "eval.jsonl"
    train_path = tmp_path / "train.jsonl"
    _write_jsonl(
        eval_path,
        [{"doc_id": "eval_001", "text": _EVAL_TEXT}],
    )
    _write_jsonl(
        train_path,
        [
            {
                "doc_id": "train_leak",
                "text": _TRAIN_PARAPHRASE,
            },
            {
                "doc_id": "train_clean",
                "text": (
                    "Junior gardener needed in Reykjavik. "
                    "Must enjoy cold weather and greenhouses. No software skills required."
                ),
            },
        ],
    )

    with pytest.raises(AssertionError, match=r"contamination \(c\) near-duplicate") as ei:
        assert_no_contamination(train_path, eval_path)

    msg = str(ei.value)
    assert "train_leak" in msg
    assert "eval_001" in msg


def test_assert_no_contamination_clean_passes(tmp_path: Path):
    eval_path = tmp_path / "eval.jsonl"
    train_path = tmp_path / "train.jsonl"
    _write_jsonl(
        eval_path,
        [{"doc_id": "eval_clean", "text": _EVAL_TEXT}],
    )
    _write_jsonl(
        train_path,
        [
            {
                "doc_id": "train_clean",
                "text": (
                    "Warehouse picker overnight shift in Anchorage. "
                    "Forklift certificate preferred. No programming."
                ),
            }
        ],
    )
    assert_no_contamination(train_path, eval_path)  # must not raise


def test_assert_no_contamination_doc_id_overlap(tmp_path: Path):
    eval_path = tmp_path / "eval.jsonl"
    train_path = tmp_path / "train.jsonl"
    shared_id = "shared_001"
    _write_jsonl(eval_path, [{"doc_id": shared_id, "text": "Eval unique body alpha beta gamma."}])
    _write_jsonl(train_path, [{"doc_id": shared_id, "text": "Train unique body delta epsilon zeta."}])
    with pytest.raises(AssertionError, match=r"contamination \(a\) exact doc_id"):
        assert_no_contamination(train_path, eval_path)


def test_text_hash_stable_under_whitespace_case():
    assert text_hash("Hello   World") == text_hash("hello world")
