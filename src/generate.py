"""Run the teacher over raw documents to produce candidate labels.

python -m src.generate --input data/raw/ --output data/candidates.jsonl \\
  --prompt-version v1 --limit N
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from schema.posting import JOB_POSTING_JSON_SCHEMA
from src import teacher
from src.prompts import FEW_SHOT_DOC_IDS, _ensure_prompts

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_EVAL = _ROOT / "data" / "eval" / "eval_v1.jsonl"


def _load_jsonl_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.exists():
        return ids
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ids.add(json.loads(line)["doc_id"])
    return ids


def _load_raw_docs(input_dir: Path) -> list[dict[str, Any]]:
    """Load unique docs with doc_id + text from *.jsonl under input_dir."""
    seen: set[str] = set()
    docs: list[dict[str, Any]] = []
    paths = sorted(input_dir.glob("*.jsonl"))
    if not paths:
        raise SystemExit(f"No *.jsonl files in {input_dir}")

    for path in paths:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                doc_id = row.get("doc_id")
                text = row.get("text")
                if not doc_id or not text:
                    continue
                if doc_id in seen:
                    continue
                seen.add(doc_id)
                docs.append({
                    "doc_id": doc_id,
                    "text": text,
                    "source": row.get("source", path.stem),
                    "lang": row.get("lang", ""),
                    "complication": row.get("complication"),
                })
    return docs


def _available_prompt_versions() -> set[str]:
    versions = set(teacher.PROMPTS)
    try:
        versions |= set(_ensure_prompts())
    except FileNotFoundError:
        pass
    return versions


async def _label_one(
    doc: dict[str, Any],
    *,
    prompt_version: str,
    schema: dict,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Returns (candidate_label, usage, cache_hit)."""
    cached = teacher._get_cache(teacher.MODEL, prompt_version, doc["text"])
    if cached:
        return cached["parsed"], cached["usage"], True

    if prompt_version in teacher.PROMPTS:
        parsed, usage = await teacher.extract_async(
            doc["text"], schema, prompt_version=prompt_version
        )
        return parsed, usage, False

    from src.prompts import get_prompt

    prompt = get_prompt(prompt_version, doc["text"])
    api_schema = teacher._prepare_schema_for_anthropic(schema)
    client = teacher.anthropic.AsyncAnthropic()
    msg = await teacher._call_with_retry_async(
        client,
        model=teacher.MODEL,
        max_tokens=4096,
        prompt=prompt,
        schema=api_schema,
    )
    parsed = json.loads(msg.content[0].text)
    usage = {
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
        "cost_usd": teacher._estimate_cost(
            msg.usage.input_tokens, msg.usage.output_tokens
        ),
    }
    teacher._put_cache(
        teacher.MODEL,
        prompt_version,
        doc["text"],
        {
            "parsed": parsed,
            "usage": usage,
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
        },
    )
    return parsed, usage, False


async def _run(
    docs: list[dict[str, Any]],
    *,
    output_path: Path,
    prompt_version: str,
    concurrency: int,
    budget_usd: float | None,
) -> None:
    schema = JOB_POSTING_JSON_SCHEMA
    sem = asyncio.Semaphore(concurrency)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_cost = 0.0
    done = 0
    stop_budget = False

    async def _one(doc: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal total_cost, done, stop_budget
        if stop_budget:
            return None
        async with sem:
            if stop_budget:
                return None
            parsed, usage, cache_hit = await _label_one(
                doc, prompt_version=prompt_version, schema=schema
            )
            cost = 0.0 if cache_hit else float(usage.get("cost_usd") or 0.0)
            total_cost += cost
            done += 1

            if done % 100 == 0:
                print(
                    f"[generate] {done}/{len(docs)} labeled  "
                    f"running_cost=${total_cost:.4f}"
                )

            if budget_usd is not None and total_cost >= budget_usd:
                stop_budget = True
                print(
                    f"[generate] BUDGET CEILING HIT: "
                    f"${total_cost:.4f} >= --budget-usd ${budget_usd:.4f}. Stopping."
                )

            assert doc["doc_id"] not in _EVAL_IDS, (
                f"refusing to write eval doc_id {doc['doc_id']}"
            )
            return {
                "doc_id": doc["doc_id"],
                "text": doc["text"],
                "candidate_label": parsed,
                "source": doc.get("source"),
                "lang": doc.get("lang"),
                "complication": doc.get("complication"),
                "teacher_model": teacher.MODEL,
                "prompt_version": prompt_version,
            }

    # Process in order but with limited concurrency; append as each finishes
    # Use a lock for file writes
    write_lock = asyncio.Lock()

    async def _one_and_write(doc: dict[str, Any]) -> None:
        row = await _one(doc)
        if row is None:
            return
        async with write_lock:
            with open(output_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    await asyncio.gather(*[_one_and_write(d) for d in docs])

    print(
        f"[generate] Done. labeled={done}  total_cost=${total_cost:.4f}  "
        f"output={output_path}"
    )


# Filled in main after loading eval ids (used by assert in _one)
_EVAL_IDS: set[str] = set()


def main() -> None:
    global _EVAL_IDS

    parser = argparse.ArgumentParser(
        description="Generate teacher candidate labels from raw documents"
    )
    parser.add_argument("--input", type=str, required=True, help="Directory of raw *.jsonl")
    parser.add_argument("--output", type=str, required=True, help="Output candidates JSONL")
    parser.add_argument("--prompt-version", type=str, required=True)
    parser.add_argument("--limit", type=int, default=None, help="Max new docs to label")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=None,
        help="Stop when cumulative reported cost reaches this ceiling",
    )
    parser.add_argument(
        "--eval-set",
        type=str,
        default=str(_DEFAULT_EVAL),
        help="Eval JSONL whose doc_ids must never be labeled",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.is_absolute():
        input_dir = _ROOT / input_dir
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = _ROOT / output_path
    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = _ROOT / eval_path

    versions = _available_prompt_versions()
    if args.prompt_version not in versions:
        raise SystemExit(
            f"Unknown prompt version {args.prompt_version!r}. "
            f"Available: {sorted(versions)}"
        )

    eval_ids = _load_jsonl_ids(eval_path)
    _EVAL_IDS = eval_ids
    few_shot_ids = set(FEW_SHOT_DOC_IDS)
    already = _load_jsonl_ids(output_path)

    docs = _load_raw_docs(input_dir)
    print(f"[generate] loaded {len(docs)} unique docs from {input_dir}")

    # Skip eval — then ASSERT none remain (do not only filter silently)
    skipped_eval = [d for d in docs if d["doc_id"] in eval_ids]
    docs = [d for d in docs if d["doc_id"] not in eval_ids]
    assert all(d["doc_id"] not in eval_ids for d in docs), (
        "eval contamination after filter"
    )
    assert not ({d["doc_id"] for d in docs} & eval_ids), (
        "eval doc_ids present in work list"
    )
    print(f"[generate] skipped {len(skipped_eval)} eval_v1 doc_ids (asserted clean)")

    # Also skip few-shot exemplars (must not enter train pipeline)
    skipped_fs = [d for d in docs if d["doc_id"] in few_shot_ids]
    docs = [d for d in docs if d["doc_id"] not in few_shot_ids]
    if skipped_fs:
        print(f"[generate] skipped {len(skipped_fs)} few-shot exemplar doc_ids")

    # Resume: skip already written
    skipped_done = [d for d in docs if d["doc_id"] in already]
    docs = [d for d in docs if d["doc_id"] not in already]
    print(f"[generate] skipped {len(skipped_done)} already in {output_path}")

    if args.limit is not None:
        docs = docs[: args.limit]

    print(f"[generate] will label {len(docs)} docs  prompt={args.prompt_version}")
    if not docs:
        print("[generate] nothing to do.")
        return

    # Final hard assert before any API calls
    work_ids = {d["doc_id"] for d in docs}
    assert work_ids.isdisjoint(eval_ids), (
        f"eval leakage in work set: {sorted(work_ids & eval_ids)[:10]}"
    )

    asyncio.run(
        _run(
            docs,
            output_path=output_path,
            prompt_version=args.prompt_version,
            concurrency=args.concurrency,
            budget_usd=args.budget_usd,
        )
    )


if __name__ == "__main__":
    main()
