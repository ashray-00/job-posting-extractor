"""Few-shot example docs must never leak into eval or train."""
from __future__ import annotations

import json
from pathlib import Path

from src.prompts import FEW_SHOT_DOC_IDS

_ROOT = Path(__file__).resolve().parent.parent


def _ids_in_jsonl(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ids.add(json.loads(line)["doc_id"])
    return ids


def test_few_shot_docs_excluded_from_eval_and_train():
    few = set(FEW_SHOT_DOC_IDS)
    assert len(few) == 3

    eval_ids = _ids_in_jsonl(_ROOT / "data" / "eval" / "eval_v1.jsonl")
    train_ids = _ids_in_jsonl(_ROOT / "data" / "train" / "train.jsonl")

    leaked_eval = few & eval_ids
    leaked_train = few & train_ids
    assert not leaked_eval, f"few-shot docs found in eval: {sorted(leaked_eval)}"
    assert not leaked_train, f"few-shot docs found in train: {sorted(leaked_train)}"


def test_few_shot_examples_file_matches_registry():
    path = _ROOT / "data" / "raw" / "few_shot_examples.jsonl"
    assert path.exists()
    file_ids = _ids_in_jsonl(path)
    assert file_ids == set(FEW_SHOT_DOC_IDS)
