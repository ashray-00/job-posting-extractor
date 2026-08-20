"""Thin Anthropic client with disk caching, structured output, and async concurrency."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

_ROOT = Path(__file__).resolve().parent.parent
_CACHE_DIR = _ROOT / "data" / "raw" / ".teacher_cache"
_LOG_DIR = _ROOT / "logs"

MODEL = "claude-haiku-4-5"

# Haiku 4.5 pricing per 1M tokens
COST_PER_1M_INPUT = 0.80
COST_PER_1M_OUTPUT = 4.00

# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def _load_env() -> None:
    env_file = _ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()

# ---------------------------------------------------------------------------
# Versioned prompts
# ---------------------------------------------------------------------------

PROMPTS: dict[str, str] = {
    "v1": (
        "You are a structured-data extraction engine. Given a job posting, "
        "extract all fields into the JSON schema provided. Rules:\n"
        "- Output ONLY valid JSON matching the schema.\n"
        "- Use null for any field not stated or clearly implied in the text.\n"
        "- Use [] (empty list) for list fields when nothing is stated.\n"
        "- For salary, convert to integers. Parse German formats (65.000) and "
        "abbreviations (65k). If only one number is given, set both min and max.\n"
        "- currency must be a 3-letter uppercase ISO 4217 code (EUR, USD, GBP).\n"
        "- location_country must be a 2-letter uppercase ISO 3166-1 alpha-2 code.\n"
        "- required_skills: list the technologies/tools explicitly required.\n"
        "- nice_to_have_skills: list skills described as optional, preferred, or a plus.\n"
        "- languages: extract language requirements with ISO 639-1 codes and CEFR levels "
        "(A1-C2) or 'native'.\n"
        "- Do NOT hallucinate information not present in the text.\n\n"
        "Job posting:\n{text}"
    ),
}

# ---------------------------------------------------------------------------
# Schema preparation for Anthropic structured output
# ---------------------------------------------------------------------------

def _prepare_schema_for_anthropic(schema: dict) -> dict:
    """Add additionalProperties: false and required to all objects for Anthropic."""
    schema = copy.deepcopy(schema)

    def _fix_object(obj: dict) -> None:
        if obj.get("type") == "object":
            obj["additionalProperties"] = False
            if "properties" in obj and "required" not in obj:
                obj["required"] = list(obj["properties"].keys())
        for key in ("properties", "$defs"):
            if key in obj:
                for v in obj[key].values():
                    if isinstance(v, dict):
                        _fix_object(v)
        if "items" in obj and isinstance(obj["items"], dict):
            _fix_object(obj["items"])
        for variant_key in ("anyOf", "oneOf", "allOf"):
            if variant_key in obj:
                for item in obj[variant_key]:
                    if isinstance(item, dict):
                        _fix_object(item)

    _fix_object(schema)
    return schema

# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def _cache_key(model: str, prompt_version: str, text: str) -> str:
    blob = f"{model}|{prompt_version}|{text}"
    return hashlib.sha256(blob.encode()).hexdigest()


def _get_cache(model: str, prompt_version: str, text: str) -> dict[str, Any] | None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(model, prompt_version, text)
    path = _CACHE_DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text("utf-8"))
    return None


def _put_cache(model: str, prompt_version: str, text: str, result: dict[str, Any]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(model, prompt_version, text)
    path = _CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(result, ensure_ascii=False), "utf-8")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log_call(
    prompt_version: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    cache_hit: bool,
    model: str,
) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_version": prompt_version,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 6),
        "cache_hit": cache_hit,
    }
    with open(_LOG_DIR / "teacher_calls.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000 * COST_PER_1M_INPUT
            + output_tokens / 1_000_000 * COST_PER_1M_OUTPUT)

# ---------------------------------------------------------------------------
# Core extraction (sync)
# ---------------------------------------------------------------------------

def extract(
    text: str,
    schema: dict,
    prompt_version: str = "v1",
    *,
    model: str = MODEL,
    max_tokens: int = 4096,
) -> tuple[dict, dict]:
    """Extract structured data from text.

    Returns (parsed_json, usage_metadata).
    """
    cached = _get_cache(model, prompt_version, text)
    if cached:
        cost = _estimate_cost(cached["input_tokens"], cached["output_tokens"])
        _log_call(prompt_version, cached["input_tokens"], cached["output_tokens"], cost, True, model)
        return cached["parsed"], cached["usage"]

    prompt_template = PROMPTS[prompt_version]
    prompt = prompt_template.format(text=text)
    api_schema = _prepare_schema_for_anthropic(schema)

    client = anthropic.Anthropic()
    msg = _call_with_retry(
        client, model=model, max_tokens=max_tokens, prompt=prompt, schema=api_schema
    )

    parsed = json.loads(msg.content[0].text)
    input_tokens = msg.usage.input_tokens
    output_tokens = msg.usage.output_tokens
    cost = _estimate_cost(input_tokens, output_tokens)

    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    }
    _put_cache(model, prompt_version, text, {
        "parsed": parsed, "usage": usage,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
    })
    _log_call(prompt_version, input_tokens, output_tokens, cost, False, model)
    return parsed, usage

# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

_RETRY_STATUSES = {429, 500, 502, 503, 529}
_MAX_RETRIES = 5


def _call_with_retry(
    client: anthropic.Anthropic,
    *,
    model: str,
    max_tokens: int,
    prompt: str,
    schema: dict,
) -> Any:
    for attempt in range(_MAX_RETRIES):
        try:
            return client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.RateLimitError:
            if attempt == _MAX_RETRIES - 1:
                raise
            _backoff(attempt)
        except anthropic.APIStatusError as e:
            if e.status_code in _RETRY_STATUSES:
                if attempt == _MAX_RETRIES - 1:
                    raise
                _backoff(attempt)
            else:
                raise


async def _call_with_retry_async(
    client: anthropic.AsyncAnthropic,
    *,
    model: str,
    max_tokens: int,
    prompt: str,
    schema: dict,
) -> Any:
    for attempt in range(_MAX_RETRIES):
        try:
            return await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.RateLimitError:
            if attempt == _MAX_RETRIES - 1:
                raise
            await asyncio.sleep(_backoff_delay(attempt))
        except anthropic.APIStatusError as e:
            if e.status_code in _RETRY_STATUSES:
                if attempt == _MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(_backoff_delay(attempt))
            else:
                raise


def _backoff_delay(attempt: int) -> float:
    return min(2 ** attempt + 0.5, 60)


def _backoff(attempt: int) -> None:
    time.sleep(_backoff_delay(attempt))

# ---------------------------------------------------------------------------
# Async extraction
# ---------------------------------------------------------------------------

async def extract_async(
    text: str,
    schema: dict,
    prompt_version: str = "v1",
    *,
    model: str = MODEL,
    max_tokens: int = 4096,
    client: anthropic.AsyncAnthropic | None = None,
) -> tuple[dict, dict]:
    """Async version of extract()."""
    cached = _get_cache(model, prompt_version, text)
    if cached:
        cost = _estimate_cost(cached["input_tokens"], cached["output_tokens"])
        _log_call(prompt_version, cached["input_tokens"], cached["output_tokens"], cost, True, model)
        return cached["parsed"], cached["usage"]

    prompt_template = PROMPTS[prompt_version]
    prompt = prompt_template.format(text=text)
    api_schema = _prepare_schema_for_anthropic(schema)

    _client = client or anthropic.AsyncAnthropic()
    msg = await _call_with_retry_async(
        _client, model=model, max_tokens=max_tokens, prompt=prompt, schema=api_schema
    )

    parsed = json.loads(msg.content[0].text)
    input_tokens = msg.usage.input_tokens
    output_tokens = msg.usage.output_tokens
    cost = _estimate_cost(input_tokens, output_tokens)

    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    }
    _put_cache(model, prompt_version, text, {
        "parsed": parsed, "usage": usage,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
    })
    _log_call(prompt_version, input_tokens, output_tokens, cost, False, model)
    return parsed, usage


async def extract_many_async(
    texts: list[str],
    schema: dict,
    prompt_version: str = "v1",
    *,
    model: str = MODEL,
    concurrency: int = 8,
) -> list[tuple[dict, dict]]:
    """Run many extractions concurrently."""
    sem = asyncio.Semaphore(concurrency)
    client = anthropic.AsyncAnthropic()
    results: list[tuple[dict, dict] | None] = [None] * len(texts)

    async def _run(idx: int, text: str) -> None:
        async with sem:
            results[idx] = await extract_async(
                text, schema, prompt_version, model=model, client=client
            )

    await asyncio.gather(*[_run(i, t) for i, t in enumerate(texts)])
    return results  # type: ignore[return-value]

# ---------------------------------------------------------------------------
# Low-level call/call_async for synth_de (generation, not extraction)
# ---------------------------------------------------------------------------

def _gen_cache_key(model: str, prompt: str, system: str, temperature: float) -> str:
    blob = json.dumps({"model": model, "system": system, "prompt": prompt, "temperature": temperature}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def call(
    prompt: str,
    *,
    system: str = "",
    model: str = MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Low-level synchronous call (no structured output). Used by synth_de."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _gen_cache_key(model, prompt, system, temperature)
    cache_path = _CACHE_DIR / f"{key}.json"

    if cache_path.exists():
        return json.loads(cache_path.read_text("utf-8"))

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system if system else anthropic.NOT_GIVEN,
        messages=[{"role": "user", "content": prompt}],
    )

    result = {
        "text": msg.content[0].text,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    cache_path.write_text(json.dumps(result, ensure_ascii=False), "utf-8")
    return result


async def call_async(
    prompt: str,
    *,
    system: str = "",
    model: str = MODEL,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    client: anthropic.AsyncAnthropic | None = None,
) -> dict[str, Any]:
    """Low-level async call (no structured output). Used by synth_de."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _gen_cache_key(model, prompt, system, temperature)
    cache_path = _CACHE_DIR / f"{key}.json"

    if cache_path.exists():
        return json.loads(cache_path.read_text("utf-8"))

    _client = client or anthropic.AsyncAnthropic()
    msg = await _client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system if system else anthropic.NOT_GIVEN,
        messages=[{"role": "user", "content": prompt}],
    )

    result = {
        "text": msg.content[0].text,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    cache_path.write_text(json.dumps(result, ensure_ascii=False), "utf-8")
    return result


async def call_many_async(
    prompts: list[dict[str, Any]],
    *,
    concurrency: int = 15,
) -> list[dict[str, Any]]:
    """Run many low-level calls concurrently. Used by synth_de."""
    sem = asyncio.Semaphore(concurrency)
    client = anthropic.AsyncAnthropic()
    results: list[dict[str, Any] | None] = [None] * len(prompts)

    async def _run(idx: int, kwargs: dict) -> None:
        async with sem:
            results[idx] = await call_async(**kwargs, client=client)

    await asyncio.gather(*[_run(i, p) for i, p in enumerate(prompts)])
    return results  # type: ignore[return-value]
