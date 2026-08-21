"""Throughput bench: documents/hour under realistic load via ``vllm bench serve``.

Why wrap instead of a custom load generator
------------------------------------------
Current ``vllm bench serve`` (see https://docs.vllm.ai/en/stable/cli/bench/serve/)
already provides:

- ``--dataset-name custom`` + ``--dataset-path`` for real prompts
- ``--custom-output-len`` + ``--ignore-eos`` for fixed output length
- ``--num-warmups`` (discarded before measurement)
- ``--max-concurrency`` closed-loop load
- ``--percentile-metrics`` / ``--metric-percentiles`` for TTFT and E2EL
- ``--save-result`` JSON with output token throughput and request throughput

This module only adds what the CLI does not: sample prompts from the frozen
eval set (real input-length distribution), sweep concurrency with repeats,
aggregate mean/std, attach GPU / vLLM version / server flags, and write
``results/bench_{run_id}.json``.

Flag names are verified against ``vllm bench serve --help`` at runtime
(PROJECT.md rule 2 — never hard-code remembered CLI names blindly).

Example::

  python -m src.bench \\
    --run-id tuned_r32_lr2e4 \\
    --model Qwen/Qwen3-1.7B \\
    --base-url http://localhost:8000 \\
    --eval-set data/eval/eval_v1.jsonl \\
    --prompt-version tuned_v1 \\
    --server-flags 'vllm serve Qwen/Qwen3-1.7B --max-model-len 4096 ...'
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.prompts import get_prompt

_ROOT = Path(__file__).resolve().parent.parent
_RESULTS = _ROOT / "results"

# Measurement plan (not CLI flag names — those come from --help).
DEFAULT_CONCURRENCIES = (1, 4, 16, 64)
DEFAULT_REPEATS = 3
DEFAULT_NUM_WARMUPS = 20
DEFAULT_MAX_TOKENS = 256
DEFAULT_NUM_PROMPTS = 100

# Flags we require from the live bench --help before running.
_REQUIRED_HELP_FLAGS = (
    "--ignore-eos",
    "--num-warmups",
    "--max-concurrency",
    "--custom-output-len",
    "--dataset-name",
    "--dataset-path",
    "--save-result",
    "--percentile-metrics",
    "--metric-percentiles",
    "--result-dir",
    "--result-filename",
    "--num-prompts",
)

# Try these in order; some images ship a stub ``vllm bench`` without serve flags.
_BENCH_PREFIX_CANDIDATES: tuple[tuple[str, ...], ...] = (
    ("vllm", "bench", "serve"),
    (sys.executable, "-m", "vllm.entrypoints.cli.main", "bench", "serve"),
    (sys.executable, "-m", "vllm.benchmarks.serve"),
)


# ---------------------------------------------------------------------------
# Small helpers
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


def _mean_std(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0}
    if len(values) == 1:
        return {"mean": float(values[0]), "std": 0.0}
    return {
        "mean": float(statistics.mean(values)),
        "std": float(statistics.stdev(values)),
    }


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return float(s[f] + (k - f) * (s[c] - s[f]))


def _load_eval(path: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    if not docs:
        raise ValueError(f"empty eval set: {path}")
    return docs


def _doc_text(doc: dict[str, Any]) -> str:
    for key in ("text", "document", "content", "description"):
        val = doc.get(key)
        if isinstance(val, str) and val.strip():
            return val
    raise KeyError(
        f"eval doc {doc.get('doc_id', '?')!r} has no text/document/content field"
    )


# ---------------------------------------------------------------------------
# Environment metadata
# ---------------------------------------------------------------------------

def _gpu_name() -> str:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name",
                "--format=csv,noheader",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    names = [line.strip() for line in out.splitlines() if line.strip()]
    if not names:
        return "unknown"
    # Deduplicate while preserving order (multi-GPU same SKU → one label).
    uniq: list[str] = []
    for n in names:
        if n not in uniq:
            uniq.append(n)
    return " + ".join(uniq) if len(uniq) > 1 else uniq[0]


def _vllm_version() -> str:
    try:
        out = subprocess.check_output(
            [sys.executable, "-c", "import vllm; print(vllm.__version__)"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out:
            return out
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        out = subprocess.check_output(
            ["vllm", "--version"],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
        if out:
            # Often "vllm 0.x.y" or similar.
            m = re.search(r"(\d+\.\d+(?:\.\d+)?)", out)
            return m.group(1) if m else out.splitlines()[-1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return "unknown"


def _detect_server_flags_from_process() -> str | None:
    """Best-effort: find a local ``vllm serve`` cmdline via ``ps``."""
    try:
        out = subprocess.check_output(
            ["ps", "-ax", "-o", "command="],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    candidates: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if "vllm" in low and "serve" in low and "bench" not in low:
            candidates.append(line)
    if not candidates:
        return None
    # Prefer the longest match (usually the full launch line).
    return max(candidates, key=len)


# ---------------------------------------------------------------------------
# Dataset from eval (real input-length distribution)
# ---------------------------------------------------------------------------

def build_custom_dataset(
    eval_docs: list[dict[str, Any]],
    *,
    prompt_version: str,
    num_prompts: int,
    seed: int,
    out_path: Path,
) -> dict[str, Any]:
    """Write JSONL ``{"prompt": ...}`` rows for ``vllm bench serve --dataset-name custom``.

    Documents are sampled (with replacement if needed) from the eval set so
    input lengths follow the real distribution rather than a uniform synthetic
    length.
    """
    import random

    rng = random.Random(seed)
    n = len(eval_docs)
    if num_prompts <= n:
        chosen = rng.sample(eval_docs, k=num_prompts)
    else:
        chosen = [eval_docs[rng.randrange(n)] for _ in range(num_prompts)]

    char_lens: list[float] = []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for doc in chosen:
            prompt = get_prompt(prompt_version, _doc_text(doc))
            char_lens.append(float(len(prompt)))
            fh.write(json.dumps({"prompt": prompt}, ensure_ascii=False) + "\n")

    return {
        "n_prompts": len(chosen),
        "n_eval_docs": n,
        "sampling": "without_replacement" if num_prompts <= n else "with_replacement",
        "char_length": {
            "mean": float(statistics.mean(char_lens)),
            "std": float(statistics.stdev(char_lens)) if len(char_lens) > 1 else 0.0,
            "p50": _percentile(char_lens, 50),
            "p95": _percentile(char_lens, 95),
            "min": float(min(char_lens)),
            "max": float(max(char_lens)),
        },
    }


# ---------------------------------------------------------------------------
# vllm bench serve invocation
# ---------------------------------------------------------------------------

def _run_help(prefix: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            [*prefix, "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return 127, f"executable not found: {prefix[0]}"
    text = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, text


def _missing_flags(help_text: str) -> list[str]:
    return [f for f in _REQUIRED_HELP_FLAGS if f not in help_text]


def _resolve_bench_prefix() -> tuple[list[str], str]:
    """Return (argv prefix, help text) for a working ``… serve`` bench CLI."""
    attempts: list[str] = []
    for cand in _BENCH_PREFIX_CANDIDATES:
        prefix = list(cand)
        # Expand sys.executable placeholder already concrete in the tuple.
        code, text = _run_help(prefix)
        missing = _missing_flags(text)
        preview = text.strip().replace("\n", " | ")[:240] or "(empty)"
        attempts.append(
            f"  {' '.join(prefix)} --help → exit={code}, "
            f"missing={len(missing)}/{len(_REQUIRED_HELP_FLAGS)}, "
            f"preview={preview!r}"
        )
        if code == 0 and not missing:
            print(f"[bench] using load generator: {' '.join(prefix)}", flush=True)
            return prefix, text

    raise RuntimeError(
        "Could not find a working vLLM serve benchmark CLI with the required "
        "flags (--ignore-eos, --num-warmups, --custom-output-len, …).\n"
        "Tried:\n"
        + "\n".join(attempts)
        + "\n\nOn the pod, run:\n"
        "  vllm --version\n"
        "  vllm bench serve --help | head -80\n"
        "  python -m vllm.entrypoints.cli.main bench serve --help | head -80\n"
        "If those look wrong, upgrade vLLM in this env "
        "(pip/uv install -U vllm) — the server process can stay up."
    )


def _assert_required_flags(help_text: str) -> None:
    missing = _missing_flags(help_text)
    if missing:
        raise RuntimeError(
            "Bench CLI --help is missing required flags "
            f"{missing}. Upgrade vLLM or update src/bench.py. "
            "Checked against live --help (PROJECT.md rule 2).\n"
            f"Help preview:\n{help_text[:1500]}"
        )


def _parse_host_port(base_url: str) -> tuple[str, int, str | None]:
    """Return (host, port, base_url_or_none).

    Prefer ``--host`` / ``--port`` when the URL is a plain http(s) origin;
    otherwise pass ``--base-url`` through if the CLI supports it.
    """
    raw = base_url.strip().rstrip("/")
    # Allow both http://host:8000 and http://host:8000/v1
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = (parsed.path or "").rstrip("/")
    if path in ("", "/v1"):
        return host, port, None
    return host, port, raw


def _percentile_from_bench_json(result: dict[str, Any], metric: str, p: float) -> float:
    """Extract percentile ``p`` for ``ttft`` or ``e2el`` from a bench result dict."""
    key = f"percentiles_{metric}_ms"
    items = result.get(key) or []
    target = float(p)
    for item in items:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            if float(item[0]) == target:
                return float(item[1])
        elif isinstance(item, dict):
            pp = item.get("percentile", item.get("p"))
            if pp is not None and float(pp) == target:
                return float(item.get("value", item.get("ms", 0.0)))
    if math.isclose(target, 50.0):
        median_key = f"median_{metric}_ms"
        if median_key in result and result[median_key] is not None:
            return float(result[median_key])
    raise KeyError(
        f"percentile {p} for {metric} not found in bench result "
        f"(looked at {key!r}; keys={sorted(result)[:40]}…)"
    )


def _extract_trial_metrics(result: dict[str, Any]) -> dict[str, float]:
    out_tps = result.get("output_throughput")
    if out_tps is None:
        out_tps = result.get("output_token_throughput")
    if out_tps is None:
        raise KeyError(
            "bench result missing output_throughput / output_token_throughput"
        )
    req_tps = result.get("request_throughput")
    if req_tps is None:
        raise KeyError("bench result missing request_throughput")
    req_tps_f = float(req_tps)
    return {
        "output_tokens_per_s": float(out_tps),
        "request_throughput_per_s": req_tps_f,
        "documents_per_hour": req_tps_f * 3600.0,
        "e2e_latency_p50_ms": _percentile_from_bench_json(result, "e2el", 50),
        "e2e_latency_p95_ms": _percentile_from_bench_json(result, "e2el", 95),
        "ttft_p50_ms": _percentile_from_bench_json(result, "ttft", 50),
        "ttft_p95_ms": _percentile_from_bench_json(result, "ttft", 95),
        "benchmark_duration_s": float(result.get("duration", result.get("benchmark_duration_s", 0.0)) or 0.0),
        "completed_requests": float(result.get("completed", result.get("successful_requests", 0)) or 0),
    }


def _build_bench_cmd(
    *,
    bench_prefix: list[str],
    help_text: str,
    model: str,
    base_url: str,
    dataset_path: Path,
    result_dir: Path,
    result_filename: str,
    max_concurrency: int,
    num_prompts: int,
    num_warmups: int,
    max_tokens: int,
    enable_thinking: bool,
    seed: int,
) -> list[str]:
    host, port, full_base = _parse_host_port(base_url)
    cmd: list[str] = [
        *bench_prefix,
        "--backend",
        "openai-chat",
        "--endpoint",
        "/v1/chat/completions",
        "--model",
        model,
        "--dataset-name",
        "custom",
        "--dataset-path",
        str(dataset_path),
        "--custom-output-len",
        str(max_tokens),
        "--ignore-eos",
        "--num-warmups",
        str(num_warmups),
        "--num-prompts",
        str(num_prompts),
        "--max-concurrency",
        str(max_concurrency),
        "--request-rate",
        "inf",
        "--percentile-metrics",
        "ttft,e2el",
        "--metric-percentiles",
        "50,95",
        "--save-result",
        "--result-dir",
        str(result_dir),
        "--result-filename",
        result_filename,
        "--seed",
        str(seed),
    ]
    if full_base is not None and "--base-url" in help_text:
        cmd.extend(["--base-url", full_base])
    else:
        cmd.extend(["--host", host, "--port", str(port)])

    # Qwen3: thinking ON by default; disable for fair throughput unless asked.
    if "--extra-body" in help_text:
        extra = {
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
            "ignore_eos": True,
        }
        cmd.extend(["--extra-body", json.dumps(extra)])
    if "--temperature" in help_text:
        cmd.extend(["--temperature", "0.0"])
    if "--disable-tqdm" in help_text:
        cmd.append("--disable-tqdm")
    return cmd


def _run_vllm_bench(cmd: list[str], result_path: Path) -> dict[str, Any]:
    if result_path.exists():
        result_path.unlink()
    print(f"[bench] $ {' '.join(shlex.quote(c) for c in cmd)}", flush=True)
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=_ROOT, capture_output=True, text=True)
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(
            f"vllm bench serve failed (exit {proc.returncode}) in {wall:.1f}s\n"
            f"stdout:\n{proc.stdout[-4000:]}\n"
            f"stderr:\n{proc.stderr[-4000:]}"
        )
    if not result_path.is_file():
        raise RuntimeError(
            f"expected result file missing: {result_path}\n"
            f"stdout:\n{proc.stdout[-2000:]}\n"
            f"stderr:\n{proc.stderr[-2000:]}"
        )
    with open(result_path, encoding="utf-8") as fh:
        return json.load(fh)


def _aggregate_config(concurrency: int, trials: list[dict[str, float]]) -> dict[str, Any]:
    def col(key: str) -> list[float]:
        return [float(t[key]) for t in trials]

    return {
        "concurrency": concurrency,
        "output_tokens_per_s": _mean_std(col("output_tokens_per_s")),
        "documents_per_hour": _mean_std(col("documents_per_hour")),
        "e2e_latency_ms": {
            "p50": _mean_std(col("e2e_latency_p50_ms")),
            "p95": _mean_std(col("e2e_latency_p95_ms")),
        },
        "ttft_ms": {
            "p50": _mean_std(col("ttft_p50_ms")),
            "p95": _mean_std(col("ttft_p95_ms")),
        },
        "trials": trials,
    }


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def run_bench(
    *,
    run_id: str,
    model: str,
    base_url: str,
    eval_set: Path,
    prompt_version: str,
    server_flags: str | None,
    concurrencies: list[int] | None = None,
    repeats: int = DEFAULT_REPEATS,
    num_warmups: int = DEFAULT_NUM_WARMUPS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    num_prompts: int = DEFAULT_NUM_PROMPTS,
    enable_thinking: bool = False,
    seed: int = 42,
    notes: str = "",
) -> Path:
    if not run_id or "/" in run_id or "\\" in run_id:
        raise ValueError(f"invalid run_id: {run_id!r}")

    help_text = ""  # set below
    bench_prefix, help_text = _resolve_bench_prefix()
    _assert_required_flags(help_text)

    conc = list(concurrencies or DEFAULT_CONCURRENCIES)
    if repeats < 1:
        raise ValueError("repeats must be >= 1")

    flags = (server_flags or "").strip()
    if not flags:
        detected = _detect_server_flags_from_process()
        if detected:
            flags = detected
            print(f"[bench] auto-detected server cmdline:\n  {flags}", flush=True)
        else:
            raise ValueError(
                "Pass --server-flags with the exact ``vllm serve ...`` launch "
                "command (required for the results record). Auto-detect found "
                "no local vllm serve process."
            )

    eval_docs = _load_eval(eval_set)
    _RESULTS.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"bench_{run_id}_", dir=_RESULTS) as tmp:
        tmp_path = Path(tmp)
        dataset_path = tmp_path / "custom_prompts.jsonl"
        length_meta = build_custom_dataset(
            eval_docs,
            prompt_version=prompt_version,
            num_prompts=num_prompts,
            seed=seed,
            out_path=dataset_path,
        )

        configurations: list[dict[str, Any]] = []
        for concurrency in conc:
            trial_metrics: list[dict[str, float]] = []
            for rep in range(repeats):
                fname = f"c{concurrency}_r{rep}.json"
                result_path = tmp_path / fname
                cmd = _build_bench_cmd(
                    bench_prefix=bench_prefix,
                    help_text=help_text,
                    model=model,
                    base_url=base_url,
                    dataset_path=dataset_path,
                    result_dir=tmp_path,
                    result_filename=fname,
                    max_concurrency=concurrency,
                    num_prompts=num_prompts,
                    num_warmups=num_warmups,
                    max_tokens=max_tokens,
                    enable_thinking=enable_thinking,
                    seed=seed + concurrency * 100 + rep,
                )
                print(
                    f"[bench] concurrency={concurrency} repeat={rep + 1}/{repeats}",
                    flush=True,
                )
                raw = _run_vllm_bench(cmd, result_path)
                metrics = _extract_trial_metrics(raw)
                metrics["repeat"] = float(rep)
                trial_metrics.append(metrics)
                print(
                    f"[bench]   output_tok/s={metrics['output_tokens_per_s']:.2f}  "
                    f"docs/h={metrics['documents_per_hour']:.1f}  "
                    f"e2e_p50={metrics['e2e_latency_p50_ms']:.1f}ms  "
                    f"ttft_p50={metrics['ttft_p50_ms']:.1f}ms",
                    flush=True,
                )
            configurations.append(_aggregate_config(concurrency, trial_metrics))

    record = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "model": model,
        "base_url": base_url,
        "prompt_version": prompt_version,
        "eval_set": str(eval_set),
        "decoding": {
            "max_tokens": max_tokens,
            "ignore_eos": True,
            "ignore_eos_cli_flag": "--ignore-eos",
            "temperature": 0.0,
            "enable_thinking": enable_thinking,
        },
        "workload": {
            "num_prompts": num_prompts,
            "num_warmups": num_warmups,
            "repeats": repeats,
            "concurrencies": conc,
            "request_rate": "inf",
            "input_source": "eval_set_sampled",
            "input_length_chars": length_meta["char_length"],
            "sampling": length_meta["sampling"],
        },
        "environment": {
            "gpu_name": _gpu_name(),
            "vllm_version": _vllm_version(),
            "server_flags": flags,
        },
        "load_generator": {
            "tool": " ".join(bench_prefix),
            "backend": "openai-chat",
            "endpoint": "/v1/chat/completions",
            "rationale": (
                "Upstream bench covers fixed output via --custom-output-len + "
                "--ignore-eos, --num-warmups, --max-concurrency, and TTFT/E2EL "
                "percentiles. This wrapper supplies eval-sampled prompts, "
                "concurrency×repeat aggregation, and environment metadata."
            ),
        },
        "configurations": configurations,
        "notes": notes,
    }

    out_path = _RESULTS / f"bench_{run_id}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"[bench] wrote {out_path}", flush=True)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Measure documents/hour via vllm bench serve, with eval-set input "
            "lengths and a concurrency sweep."
        )
    )
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="OpenAI-compatible server origin (with or without /v1).",
    )
    parser.add_argument(
        "--eval-set",
        type=str,
        default="data/eval/eval_v1.jsonl",
        help="JSONL used to sample realistic input lengths / prompts.",
    )
    parser.add_argument("--prompt-version", type=str, default="tuned_v1")
    parser.add_argument(
        "--server-flags",
        type=str,
        default=None,
        help=(
            "Exact ``vllm serve ...`` command (or flag string) used on the "
            "server. Required for the results record; if omitted, attempts "
            "local process auto-detect."
        ),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        nargs="+",
        default=list(DEFAULT_CONCURRENCIES),
        help=f"Concurrency sweep (default: {' '.join(map(str, DEFAULT_CONCURRENCIES))}).",
    )
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--num-warmups", type=int, default=DEFAULT_NUM_WARMUPS)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Fixed output length (passed as --custom-output-len with --ignore-eos).",
    )
    parser.add_argument("--num-prompts", type=int, default=DEFAULT_NUM_PROMPTS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--enable-thinking",
        type=lambda v: str(v).strip().lower() in ("true", "1", "yes"),
        default=False,
    )
    parser.add_argument("--notes", type=str, default="")
    args = parser.parse_args()

    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = _ROOT / eval_path

    # Optional .env load (API keys etc.) — same pattern as other tools.
    env_file = _ROOT / ".env"
    if env_file.exists():
        with open(env_file) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    run_bench(
        run_id=args.run_id,
        model=args.model,
        base_url=args.base_url,
        eval_set=eval_path,
        prompt_version=args.prompt_version,
        server_flags=args.server_flags,
        concurrencies=list(args.concurrency),
        repeats=args.repeats,
        num_warmups=args.num_warmups,
        max_tokens=args.max_tokens,
        num_prompts=args.num_prompts,
        enable_thinking=args.enable_thinking,
        seed=args.seed,
        notes=args.notes,
    )


if __name__ == "__main__":
    main()
