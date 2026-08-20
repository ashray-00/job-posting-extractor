"""Evaluate any model configuration against a frozen eval set.

Writes exactly one JSON file to results/{run_id}.json and a preds JSONL
for error analysis. No other side effects.

Prompt text comes from ``src.prompts`` (and teacher ``v1`` for the API teacher
baseline). Prompt tokens are logged per request — that is part of the cost story.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from tqdm import tqdm

from schema.posting import JOB_POSTING_JSON_SCHEMA
from src import teacher
from src.metrics import evaluate
from src.prompts import PROMPTS as BASELINE_PROMPTS
from src.prompts import _ensure_prompts

_ROOT = Path(__file__).resolve().parent.parent
_RESULTS = _ROOT / "results"

TEMPERATURE = 0.0
SEED = 42
MAX_TOKENS = 4096


def _available_prompt_versions() -> dict[str, str]:
    """Union of teacher prompts and baseline prompts."""
    versions = dict(teacher.PROMPTS)
    try:
        versions.update(_ensure_prompts())
    except FileNotFoundError:
        versions.update(BASELINE_PROMPTS)
    return versions


def _render_prompt(prompt_version: str, text: str) -> str:
    versions = _available_prompt_versions()
    if prompt_version not in versions:
        raise KeyError(prompt_version)
    # teacher v1 and baseline prompts all use {text}; few_shot has JSON braces
    return versions[prompt_version].replace("{text}", text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=_ROOT,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (k - f) * (s[c] - s[f])


def _load_eval(path: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def _parse_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort parse of a JSON object from model text. Never raises."""
    if not text or not text.strip():
        return None
    text = text.strip()
    # Strip Qwen3 think blocks if a server still emits them
    if "</think>" in text:
        text = text.split("</think>", 1)[-1].strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _bool_arg(value: str) -> bool:
    v = value.strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"expected true/false, got {value!r}")


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

async def _vllm_one(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    model_name: str,
    prompt: str,
    constrained: bool,
    schema: dict,
    enable_thinking: bool,
    api_key: str | None = None,
) -> tuple[dict[str, Any] | None, str, int, int, float]:
    """Returns (parsed, raw_text, prompt_tokens, completion_tokens, latency_ms)."""
    body: dict[str, Any] = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "seed": SEED,
        "max_tokens": MAX_TOKENS,
        # Qwen3: thinking ON by default. Must disable for extraction / fair latency.
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
    }
    if constrained:
        # Portable OpenAI-compatible shape (vLLM docs; not guided_json).
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "JobPosting",
                "schema": schema,
            },
        }

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=body,
            headers=headers or None,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        return None, f"<<error: {exc}>>", 0, 0, latency_ms
    latency_ms = (time.perf_counter() - t0) * 1000

    raw = ""
    try:
        raw = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raw = json.dumps(data)

    usage = data.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    parsed = _parse_json_object(raw)
    return parsed, raw, prompt_tokens, completion_tokens, latency_ms


async def _api_one(
    *,
    text: str,
    prompt_version: str,
    constrained: bool,
    schema: dict,
) -> tuple[dict[str, Any] | None, str, int, int, float]:
    """Teacher / Anthropic path. Returns (parsed, raw, prompt_tok, completion_tok, latency_ms)."""
    t0 = time.perf_counter()
    try:
        # Prefer teacher.extract for its ``v1`` registry + caching when version is there.
        if constrained and prompt_version in teacher.PROMPTS:
            parsed, usage = await teacher.extract_async(
                text, schema, prompt_version=prompt_version
            )
            raw = json.dumps(parsed, ensure_ascii=False)
            latency_ms = (time.perf_counter() - t0) * 1000
            return (
                parsed,
                raw,
                int(usage.get("input_tokens") or 0),
                int(usage.get("output_tokens") or 0),
                latency_ms,
            )

        prompt = _render_prompt(prompt_version, text)
        if constrained:
            # Structured extract with a baseline prompt (e.g. few_shot_v1 on teacher).
            api_schema = teacher._prepare_schema_for_anthropic(schema)
            client = teacher.anthropic.AsyncAnthropic()
            msg = await teacher._call_with_retry_async(
                client,
                model=teacher.MODEL,
                max_tokens=MAX_TOKENS,
                prompt=prompt,
                schema=api_schema,
            )
            parsed = json.loads(msg.content[0].text)
            latency_ms = (time.perf_counter() - t0) * 1000
            return (
                parsed,
                msg.content[0].text,
                int(msg.usage.input_tokens),
                int(msg.usage.output_tokens),
                latency_ms,
            )

        result = await teacher.call_async(
            prompt,
            model=teacher.MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        raw = result.get("text") or ""
        parsed = _parse_json_object(raw)
        return (
            parsed,
            raw,
            int(result.get("input_tokens") or 0),
            int(result.get("output_tokens") or 0),
            latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        return None, f"<<error: {exc}>>", 0, 0, latency_ms


# ---------------------------------------------------------------------------
# Main eval loop
# ---------------------------------------------------------------------------

async def _run_all(
    docs: list[dict[str, Any]],
    *,
    backend: str,
    model: str,
    adapter: str | None,
    base_url: str,
    constrained: bool,
    prompt_version: str,
    concurrency: int,
    enable_thinking: bool,
    api_key: str | None = None,
) -> tuple[list[dict | None], list[dict], list[float], int, int, float]:
    """Returns preds, pred_rows, latencies_ms, prompt_total, completion_total, cost_usd."""
    sem = asyncio.Semaphore(concurrency)
    preds: list[dict | None] = [None] * len(docs)
    pred_rows: list[dict] = [{} for _ in docs]
    latencies: list[float] = [0.0] * len(docs)
    totals = {"prompt": 0, "completion": 0, "cost": 0.0}

    model_name = adapter if adapter else model
    schema = JOB_POSTING_JSON_SCHEMA
    pbar = tqdm(total=len(docs), desc="eval", unit="doc")

    async def _store(
        idx: int,
        doc: dict,
        parsed: dict | None,
        raw: str,
        pt: int,
        ct: int,
        lat: float,
        cost: float,
    ) -> None:
        preds[idx] = parsed
        latencies[idx] = lat
        totals["prompt"] += pt
        totals["completion"] += ct
        totals["cost"] += cost
        pred_rows[idx] = {
            "doc_id": doc.get("doc_id"),
            "difficulty": doc.get("difficulty"),
            "parsed": parsed,
            "raw": raw,
            "latency_ms": round(lat, 2),
            "prompt_tokens": pt,
            "completion_tokens": ct,
        }
        pbar.update(1)

    if backend == "vllm":
        async with httpx.AsyncClient(timeout=300.0) as shared:

            async def _one_vllm(idx: int, doc: dict) -> None:
                prompt = _render_prompt(prompt_version, doc["text"])
                async with sem:
                    parsed, raw, pt, ct, lat = await _vllm_one(
                        shared,
                        base_url=base_url,
                        model_name=model_name,
                        prompt=prompt,
                        constrained=constrained,
                        schema=schema,
                        enable_thinking=enable_thinking,
                        api_key=api_key,
                    )
                await _store(idx, doc, parsed, raw, pt, ct, lat, 0.0)

            await asyncio.gather(*[_one_vllm(i, d) for i, d in enumerate(docs)])
    else:

        async def _one_api(idx: int, doc: dict) -> None:
            async with sem:
                parsed, raw, pt, ct, lat = await _api_one(
                    text=doc["text"],
                    prompt_version=prompt_version,
                    constrained=constrained,
                    schema=schema,
                )
            cost = teacher._estimate_cost(pt, ct)
            await _store(idx, doc, parsed, raw, pt, ct, lat, cost)

        await asyncio.gather(*[_one_api(i, d) for i, d in enumerate(docs)])

    pbar.close()
    return (
        preds,
        pred_rows,
        latencies,
        int(totals["prompt"]),
        int(totals["completion"]),
        float(totals["cost"]),
    )


def run_eval(
    *,
    eval_set: Path,
    backend: str,
    model: str,
    adapter: str | None,
    base_url: str,
    constrained: bool,
    prompt_version: str,
    run_id: str,
    concurrency: int = 8,
    notes: str = "",
    vocab: dict[str, str] | None = None,
    enable_thinking: bool = False,
    api_key: str | None = None,
) -> Path:
    versions = _available_prompt_versions()
    if prompt_version not in versions:
        raise SystemExit(
            f"Unknown prompt version {prompt_version!r}. "
            f"Available: {sorted(versions)}"
        )

    docs = _load_eval(eval_set)
    if not docs:
        raise SystemExit(f"No documents in {eval_set}")

    if api_key is None:
        api_key = os.environ.get("VLLM_API_KEY") or os.environ.get("OPENAI_API_KEY")

    wall_t0 = time.perf_counter()
    preds, pred_rows, latencies, prompt_total, completion_total, cost_usd = asyncio.run(
        _run_all(
            docs,
            backend=backend,
            model=model,
            adapter=adapter,
            base_url=base_url,
            constrained=constrained,
            prompt_version=prompt_version,
            concurrency=concurrency,
            enable_thinking=enable_thinking,
            api_key=api_key,
        )
    )
    wall_clock_s = time.perf_counter() - wall_t0

    vocab = vocab or {}
    overall = evaluate(preds, docs, vocab)
    by_difficulty = evaluate(preds, docs, vocab, slice_by="difficulty")
    metrics = {**overall, "by_difficulty": by_difficulty}

    n = len(docs)
    prompt_avg = prompt_total / n if n else 0.0
    completion_avg = completion_total / n if n else 0.0

    record = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "model": model,
        "adapter": adapter,
        "quantization": None,
        "decoding": {
            "constrained": constrained,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "seed": SEED,
            "backend": backend,
            "base_url": base_url if backend == "vllm" else None,
            "enable_thinking": enable_thinking if backend == "vllm" else None,
        },
        "prompt_version": prompt_version,
        "eval_set": eval_set.name.replace(".jsonl", ""),
        "metrics": metrics,
        "tokens": {
            "prompt_total": prompt_total,
            "completion_total": completion_total,
            "prompt_avg_per_doc": round(prompt_avg, 1),
            "completion_avg_per_doc": round(completion_avg, 1),
            "n_docs": n,
        },
        "timing": {
            "wall_clock_s": round(wall_clock_s, 3),
            "p50_latency_ms": round(_percentile(latencies, 50), 2),
            "p95_latency_ms": round(_percentile(latencies, 95), 2),
        },
        "cost": {
            "usd_total": round(cost_usd, 6),
            "usd_per_1000_docs": round(cost_usd / n * 1000, 6) if n else 0.0,
        },
        "notes": notes,
    }

    _RESULTS.mkdir(parents=True, exist_ok=True)
    out_path = _RESULTS / f"{run_id}.json"
    preds_path = _RESULTS / f"{run_id}.preds.jsonl"

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    with open(preds_path, "w", encoding="utf-8") as fh:
        for row in pred_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[run_eval] Wrote {out_path}")
    print(f"[run_eval] Wrote {preds_path}")
    print(
        f"[run_eval] schema_valid_rate={metrics['schema_valid_rate']:.3f}  "
        f"macro_f1={metrics['macro_f1']:.3f}  "
        f"prompt_avg={prompt_avg:.0f}  completion_avg={completion_avg:.0f}  "
        f"cost=${cost_usd:.4f}"
    )
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a model against a frozen eval set")
    parser.add_argument("--eval-set", type=str, required=True)
    parser.add_argument("--backend", choices=["vllm", "api"], required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--adapter", type=str, default=None)
    parser.add_argument("--base-url", type=str, default="http://localhost:8000/v1")
    parser.add_argument("--constrained", type=_bool_arg, required=True)
    parser.add_argument("--prompt-version", type=str, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--notes", type=str, default="")
    parser.add_argument(
        "--enable-thinking",
        type=_bool_arg,
        default=False,
        help="Qwen3 reasoning mode. Default false — required for fair extraction baselines.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Bearer token for vLLM (defaults to env VLLM_API_KEY or OPENAI_API_KEY).",
    )
    args = parser.parse_args()

    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = _ROOT / eval_path

    run_eval(
        eval_set=eval_path,
        backend=args.backend,
        model=args.model,
        adapter=args.adapter,
        base_url=args.base_url,
        constrained=args.constrained,
        prompt_version=args.prompt_version,
        run_id=args.run_id,
        concurrency=args.concurrency,
        notes=args.notes,
        enable_thinking=args.enable_thinking,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    main()
