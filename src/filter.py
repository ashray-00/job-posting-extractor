"""Programmatic rejection sampling for teacher candidate labels.

No model calls. Pure rules using src.normalize (+ rapidfuzz for skills).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError
from rapidfuzz import fuzz

from schema.posting import JobPosting
from src.normalize import normalize_skill, normalize_text, parse_money

_ROOT = Path(__file__).resolve().parent.parent

# Configurable remote / hybrid lexical triggers (lowercase matched against normalised text)
REMOTE_TRIGGERS: list[str] = [
    "remote",
    "remotely",
    "remote work",
    "home office",
    "homeoffice",
    "home-based",
    "home based",
    "from home",
    "work from home",
    "wfh",
    "hybrid",
    "ortsunabhängig",
    "ortsunabhangig",  # ascii fold after NFKC may still keep umlauts; keep both
    "telecommut",
    "telework",
    "mobiles arbeiten",
]

# Spelled-out years (English + German), mapped to integers
_SPELLED_YEARS: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "twenty": 20,
    "null": 0,
    "eins": 1,
    "ein": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "funf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "elf": 11,
    "zwölf": 12,
    "zwolf": 12,
    "dreizehn": 13,
    "vierzehn": 14,
    "fünfzehn": 15,
    "funfzehn": 15,
    "zwanzig": 20,
}

_MONEY_CANDIDATE = re.compile(
    r"(?:€|\$|£|EUR|USD|GBP)?\s*"
    r"\d{1,3}(?:[.\s,]\d{3})+|\d+"
    r"(?:\s*[kK])?"
    r"(?:\s*(?:€|\$|£|EUR|USD|GBP))?",
    re.IGNORECASE,
)

# "5 years", "5+ years", "5-year", "3-5 years", "3 – 5 years"
_DIGIT_YEARS = re.compile(
    r"\b(\d{1,2})\s*[+]?\s*(?:years?|jahre?n?|yrs?)\b",
    re.IGNORECASE,
)
_HYPHEN_YEAR = re.compile(
    r"\b(\d{1,2})\s*[-–—]\s*(?:year|jahr)\b",
    re.IGNORECASE,
)
_YEAR_RANGE = re.compile(
    r"\b(\d{1,2})\s*[-–—]\s*(\d{1,2})\s*[+]?\s*(?:years?|jahre?n?|yrs?)\b",
    re.IGNORECASE,
)


def _label(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("candidate_label") or doc.get("label") or {}


def _text(doc: dict[str, Any]) -> str:
    return doc.get("text") or ""


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def rule_schema(doc: dict[str, Any]) -> bool:
    """Structural/field validation against JobPosting.

    Cross-field salary order is handled by ``salary_order``; for schema we
    temporarily swap inverted ranges so that rule is not double-counted.
    """
    try:
        data = dict(_label(doc))
        smin, smax = data.get("salary_min"), data.get("salary_max")
        if smin is not None and smax is not None and smin > smax:
            data["salary_min"], data["salary_max"] = smax, smin
        JobPosting.model_validate(data)
        return True
    except ValidationError:
        return False


def rule_salary_order(doc: dict[str, Any]) -> bool:
    lab = _label(doc)
    lo, hi = lab.get("salary_min"), lab.get("salary_max")
    if lo is None or hi is None:
        return True
    return lo <= hi


def rule_salary_plausible(doc: dict[str, Any]) -> bool:
    lab = _label(doc)
    period = lab.get("salary_period")
    bounds = {
        "year": (10_000, 500_000),
        "month": (800, 40_000),
        "hour": (5, 500),
    }
    if period not in bounds:
        # No period: only check if values look wildly impossible as yearly
        for key in ("salary_min", "salary_max"):
            v = lab.get(key)
            if v is None:
                continue
            if v < 5 or v > 500_000:
                return False
        return True

    lo_b, hi_b = bounds[period]
    for key in ("salary_min", "salary_max"):
        v = lab.get(key)
        if v is None:
            continue
        if not (lo_b <= v <= hi_b):
            return False
    return True


def _money_values_in_text(text: str) -> list[int]:
    values: list[int] = []
    for m in _MONEY_CANDIDATE.finditer(text):
        parsed = parse_money(m.group(0))
        if parsed is not None:
            values.append(parsed)
    return values


def rule_salary_grounded(doc: dict[str, Any]) -> bool:
    lab = _label(doc)
    targets = [v for v in (lab.get("salary_min"), lab.get("salary_max")) if v is not None]
    if not targets:
        return True
    found = _money_values_in_text(_text(doc))
    if not found:
        return False
    for t in targets:
        if not any(abs(t - f) <= max(1, int(t * 0.01)) for f in found):
            return False
    return True


def _skill_grounded_in_text(skill: str, norm_src: str) -> bool:
    """True if skill is attested in source text.

    Accepts exact / punct-normalized substring, fuzzy partial ≥ 90, or every
    significant token appearing in the text (covers paraphrases like
    ``functional testing`` ↔ ``functional … tests``).
    """
    s = normalize_text(str(skill))
    if not s:
        return False
    if s in norm_src:
        return True
    if fuzz.partial_ratio(s, norm_src) >= 90:
        return True

    ns = normalize_skill(str(skill))
    hay = re.sub(r"[^\w\s]", " ", norm_src)
    hay = re.sub(r"\s+", " ", hay).strip()
    if ns and ns in hay:
        return True

    toks = [t for t in re.split(r"\W+", s) if len(t) >= 3]
    if not toks:
        return False

    def _tok_in(t: str) -> bool:
        if re.search(rf"\b{re.escape(t)}\b", hay):
            return True
        for suf in ("ing", "tion", "ments", "ment", "ers", "ies", "es", "s"):
            if t.endswith(suf) and len(t) > len(suf) + 2:
                stem = t[: -len(suf)]
                if re.search(rf"\b{re.escape(stem)}\b", hay):
                    return True
        return False

    return all(_tok_in(t) for t in toks)


def rule_skills_grounded(doc: dict[str, Any]) -> bool:
    lab = _label(doc)
    skills = list(lab.get("required_skills") or []) + list(lab.get("nice_to_have_skills") or [])
    if not skills:
        return True
    norm_src = normalize_text(_text(doc))
    ungrounded = sum(1 for skill in skills if not _skill_grounded_in_text(str(skill), norm_src))
    return (ungrounded / len(skills)) <= 0.10


def _experience_mentions(text: str) -> set[int]:
    found: set[int] = set()
    for m in _DIGIT_YEARS.finditer(text):
        found.add(int(m.group(1)))
    for m in _HYPHEN_YEAR.finditer(text):
        found.add(int(m.group(1)))
    for m in _YEAR_RANGE.finditer(text):
        found.add(int(m.group(1)))
        found.add(int(m.group(2)))
    # Spelled-out near "year(s)" / "Jahr"
    lower = normalize_text(text)
    for word, val in _SPELLED_YEARS.items():
        for m in re.finditer(rf"\b{re.escape(word)}\b", lower):
            start = max(0, m.start() - 30)
            end = min(len(lower), m.end() + 30)
            window = lower[start:end]
            if any(k in window for k in ("year", "jahr", "yrs", "erfahrung", "experience")):
                found.add(val)
            else:
                found.add(val)
    # Bare "5+" patterns
    for m in re.finditer(r"\b(\d{1,2})\s*\+", text):
        found.add(int(m.group(1)))
    return found


def rule_experience_grounded(doc: dict[str, Any]) -> bool:
    lab = _label(doc)
    years = lab.get("years_experience_min")
    if years is None:
        return True
    mentions = _experience_mentions(_text(doc))
    return int(years) in mentions


def rule_remote_trigger(doc: dict[str, Any]) -> bool:
    lab = _label(doc)
    policy = lab.get("remote_policy")
    if policy not in ("remote", "hybrid"):
        return True
    norm = normalize_text(_text(doc))
    return any(normalize_text(t) in norm for t in REMOTE_TRIGGERS)


def rule_language_plausible(doc: dict[str, Any]) -> bool:
    lab = _label(doc)
    langs = lab.get("languages") or []
    if not langs:
        return True
    norm = normalize_text(_text(doc))
    aliases = {
        "en": ["en", "english", "englisch"],
        "de": ["de", "german", "deutsch"],
        "fr": ["fr", "french", "französisch", "franzosisch"],
        "es": ["es", "spanish", "spanisch"],
        "it": ["it", "italian", "italienisch"],
        "nl": ["nl", "dutch", "niederländisch", "niederlandisch"],
        "pl": ["pl", "polish", "polnisch"],
        "pt": ["pt", "portuguese", "portugiesisch"],
        "ru": ["ru", "russian", "russisch"],
        "zh": ["zh", "chinese", "chinesisch"],
        "ja": ["ja", "japanese", "japanisch"],
    }
    for item in langs:
        code = normalize_text(str(item.get("lang", "")))
        if not code:
            return False
        names = aliases.get(code, [code])
        ok = False
        for n in names:
            nn = normalize_text(n)
            # Word-boundary for short codes; substring for full names (handles
            # glued OCR like "EnglishBasic").
            if len(nn) <= 2:
                if re.search(rf"\b{re.escape(nn)}\b", norm):
                    ok = True
                    break
            elif nn in norm:
                ok = True
                break
        if not ok:
            return False
    return True


def rule_city_grounded(doc: dict[str, Any]) -> bool:
    lab = _label(doc)
    city = lab.get("location_city")
    if city is None or city == "":
        return True
    return normalize_text(str(city)) in normalize_text(_text(doc))


RULES: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
    ("schema", rule_schema),
    ("salary_order", rule_salary_order),
    ("salary_plausible", rule_salary_plausible),
    ("salary_grounded", rule_salary_grounded),
    ("skills_grounded", rule_skills_grounded),
    ("experience_grounded", rule_experience_grounded),
    ("remote_trigger", rule_remote_trigger),
    ("language_plausible", rule_language_plausible),
    ("city_grounded", rule_city_grounded),
]


def check(doc: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (accepted, list of failed rule names)."""
    failed: list[str] = []
    for name, fn in RULES:
        try:
            ok = fn(doc)
        except Exception:
            ok = False
        if not ok:
            failed.append(name)
    return (len(failed) == 0, failed)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_table(
    n_total: int,
    n_rejected: int,
    rule_fails: Counter[str],
    source_stats: dict[str, dict[str, int]],
) -> None:
    print("\n=== Rejection summary ===")
    rate = n_rejected / n_total if n_total else 0.0
    print(f"total: {n_total}  accepted: {n_total - n_rejected}  "
          f"rejected: {n_rejected}  rejection_rate: {rate:.1%}")

    print("\nPer rule (share of all docs that failed this rule):")
    print(f"{'rule':<22} {'fails':>6} {'rate':>8}")
    print("-" * 38)
    for name, _ in RULES:
        c = rule_fails.get(name, 0)
        print(f"{name:<22} {c:>6} {c / n_total if n_total else 0:>8.1%}")

    print("\nPer source:")
    print(f"{'source':<16} {'n':>5} {'rej':>5} {'rate':>8}")
    print("-" * 36)
    for src in sorted(source_stats):
        s = source_stats[src]
        r = s["rejected"] / s["n"] if s["n"] else 0.0
        print(f"{src:<16} {s['n']:>5} {s['rejected']:>5} {r:>8.1%}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter candidate labels with pure rules")
    parser.add_argument("--input", type=str, default=str(_ROOT / "data" / "candidates.jsonl"))
    parser.add_argument(
        "--accepted", type=str, default=str(_ROOT / "data" / "train" / "train_raw.jsonl")
    )
    parser.add_argument(
        "--rejected", type=str, default=str(_ROOT / "data" / "rejected.jsonl")
    )
    args = parser.parse_args()

    inp = Path(args.input)
    accepted_path = Path(args.accepted)
    rejected_path = Path(args.rejected)
    for p in (accepted_path, rejected_path):
        p.parent.mkdir(parents=True, exist_ok=True)

    n_total = n_rejected = 0
    rule_fails: Counter[str] = Counter()
    source_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "rejected": 0})

    with open(inp, encoding="utf-8") as fin, \
         open(accepted_path, "w", encoding="utf-8") as facc, \
         open(rejected_path, "w", encoding="utf-8") as frej:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            n_total += 1
            src = str(doc.get("source") or "unknown")
            source_stats[src]["n"] += 1

            ok, failed = check(doc)
            if ok:
                facc.write(json.dumps(doc, ensure_ascii=False) + "\n")
            else:
                n_rejected += 1
                source_stats[src]["rejected"] += 1
                for r in failed:
                    rule_fails[r] += 1
                out = dict(doc)
                out["rejected_by"] = failed
                frej.write(json.dumps(out, ensure_ascii=False) + "\n")

    _print_table(n_total, n_rejected, rule_fails, source_stats)
    print(f"[filter] wrote accepted → {accepted_path}")
    print(f"[filter] wrote rejected → {rejected_path}")


if __name__ == "__main__":
    main()
