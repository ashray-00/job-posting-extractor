"""Near-duplicate removal (MinHash LSH) and train/eval contamination checks."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from datasketch import MinHash, MinHashLSH

from src.normalize import normalize_text
from src.prompts import FEW_SHOT_DOC_IDS, _load_few_shot_examples

logger = logging.getLogger(__name__)

_NUM_PERM = 128
_SHINGLE_N = 5


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    docs: list[dict[str, Any]] = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def _text_of(doc: dict[str, Any]) -> str:
    return doc.get("text") or ""


def _doc_id(doc: dict[str, Any]) -> str:
    return str(doc.get("doc_id", ""))


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def _char_shingles(text: str, n: int = _SHINGLE_N) -> set[str]:
    t = normalize_text(text)
    if len(t) < n:
        return {t} if t else set()
    return {t[i : i + n] for i in range(len(t) - n + 1)}


def _minhash(text: str, num_perm: int = _NUM_PERM) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for sh in _char_shingles(text):
        m.update(sh.encode("utf-8"))
    return m


def _union_find_clusters(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in edges:
        union(a, b)

    buckets: dict[int, list[int]] = {}
    for i in range(n):
        buckets.setdefault(find(i), []).append(i)
    return list(buckets.values())


def near_duplicates(
    docs: list[dict[str, Any]],
    threshold: float = 0.85,
) -> list[list[dict[str, Any]]]:
    """Cluster docs by MinHash LSH over character 5-shingles of normalised text.

    Returns every cluster (including singletons). Documents within a multi-doc
    cluster are near-duplicates at approximately ``threshold`` Jaccard.
    """
    if not docs:
        return []

    minhashes = [_minhash(_text_of(d)) for d in docs]
    lsh = MinHashLSH(threshold=threshold, num_perm=_NUM_PERM)
    for i, mh in enumerate(minhashes):
        lsh.insert(str(i), mh)

    edges: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for i, mh in enumerate(minhashes):
        for key in lsh.query(mh):
            j = int(key)
            if i == j:
                continue
            # Confirm estimated Jaccard meets threshold (LSH can false-positive)
            if minhashes[i].jaccard(minhashes[j]) < threshold:
                continue
            a, b = (i, j) if i < j else (j, i)
            if (a, b) not in seen:
                seen.add((a, b))
                edges.append((a, b))

    index_clusters = _union_find_clusters(len(docs), edges)
    return [[docs[i] for i in cluster] for cluster in index_clusters]


def dedupe(docs: list[dict[str, Any]], threshold: float = 0.85) -> list[dict[str, Any]]:
    """Keep one representative per near-duplicate cluster (longest text)."""
    clusters = near_duplicates(docs, threshold=threshold)
    kept: list[dict[str, Any]] = []
    removed = 0
    for cluster in clusters:
        if len(cluster) == 1:
            kept.append(cluster[0])
            continue
        best = max(cluster, key=lambda d: len(_text_of(d)))
        kept.append(best)
        removed += len(cluster) - 1
        dropped = [_doc_id(d) for d in cluster if d is not best]
        logger.info(
            "dedupe: cluster size=%d kept=%s dropped=%s",
            len(cluster),
            _doc_id(best),
            dropped,
        )
    logger.info("dedupe: removed %d near-duplicate(s); kept %d / %d", removed, len(kept), len(docs))
    print(f"[dedup] removed {removed} near-duplicate(s); kept {len(kept)} / {len(docs)}")
    return kept


def _near_dup_pairs(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    threshold: float = 0.85,
) -> list[tuple[str, str]]:
    """Return (left_id, right_id) pairs that are near-duplicates across sets."""
    if not left or not right:
        return []

    right_mh = [_minhash(_text_of(d)) for d in right]
    lsh = MinHashLSH(threshold=threshold, num_perm=_NUM_PERM)
    for i, mh in enumerate(right_mh):
        lsh.insert(str(i), mh)

    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for doc in left:
        mh = _minhash(_text_of(doc))
        for key in lsh.query(mh):
            j = int(key)
            if mh.jaccard(right_mh[j]) < threshold:
                continue
            pair = (_doc_id(doc), _doc_id(right[j]))
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs


def assert_no_contamination(
    train_path: str | Path,
    eval_path: str | Path,
    *,
    threshold: float = 0.85,
) -> None:
    """Raise if train and eval (or few-shot exemplars) contaminate each other.

    Checks:
      (a) exact doc_id overlap
      (b) exact normalised-text hash overlap
      (c) near-duplicate overlap at ``threshold``

    Few-shot examples from ``src.prompts`` are checked against both sets.
    """
    train = _load_jsonl(train_path)
    eval_docs = _load_jsonl(eval_path)
    few = list(_load_few_shot_examples())

    train_ids = {_doc_id(d) for d in train}
    eval_ids = {_doc_id(d) for d in eval_docs}
    few_ids = set(FEW_SHOT_DOC_IDS)

    # (a) exact doc_id overlap
    id_overlap = sorted(train_ids & eval_ids)
    if id_overlap:
        raise AssertionError(
            f"contamination (a) exact doc_id overlap train∩eval: {id_overlap}"
        )

    few_in_train = sorted(few_ids & train_ids)
    if few_in_train:
        raise AssertionError(
            f"contamination (a) few-shot doc_ids present in train: {few_in_train}"
        )
    few_in_eval = sorted(few_ids & eval_ids)
    if few_in_eval:
        raise AssertionError(
            f"contamination (a) few-shot doc_ids present in eval: {few_in_eval}"
        )

    # (b) exact normalised-text hash overlap
    def _hash_map(docs: list[dict[str, Any]]) -> dict[str, list[str]]:
        m: dict[str, list[str]] = {}
        for d in docs:
            h = text_hash(_text_of(d))
            m.setdefault(h, []).append(_doc_id(d))
        return m

    train_hashes = _hash_map(train)
    eval_hashes = _hash_map(eval_docs)
    few_hashes = _hash_map(few)

    hash_hits = []
    for h, eids in eval_hashes.items():
        if h in train_hashes:
            hash_hits.append(
                f"hash={h[:12]}… train={train_hashes[h]} eval={eids}"
            )
    if hash_hits:
        raise AssertionError(
            "contamination (b) exact normalised-text hash overlap train∩eval:\n  "
            + "\n  ".join(hash_hits)
        )

    for h, fids in few_hashes.items():
        if h in train_hashes:
            raise AssertionError(
                f"contamination (b) few-shot text hash in train: "
                f"few={fids} train={train_hashes[h]}"
            )
        if h in eval_hashes:
            raise AssertionError(
                f"contamination (b) few-shot text hash in eval: "
                f"few={fids} eval={eval_hashes[h]}"
            )

    # (c) near-duplicate overlap
    te_pairs = _near_dup_pairs(train, eval_docs, threshold=threshold)
    if te_pairs:
        raise AssertionError(
            f"contamination (c) near-duplicate overlap (threshold={threshold}) "
            f"train↔eval: {te_pairs}"
        )

    ft_pairs = _near_dup_pairs(few, train, threshold=threshold)
    if ft_pairs:
        raise AssertionError(
            f"contamination (c) near-duplicate overlap (threshold={threshold}) "
            f"few-shot↔train: {ft_pairs}"
        )

    fe_pairs = _near_dup_pairs(few, eval_docs, threshold=threshold)
    if fe_pairs:
        raise AssertionError(
            f"contamination (c) near-duplicate overlap (threshold={threshold}) "
            f"few-shot↔eval: {fe_pairs}"
        )
