"""Generate realistic synthetic German job postings using teacher API."""
from __future__ import annotations

import ast
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from src import teacher

_DATA_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

_COST_PER_1M_INPUT = 0.80   # Haiku 4.5
_COST_PER_1M_OUTPUT = 4.00  # Haiku 4.5

COMPLICATIONS = [
    ("no_salary", "Do NOT mention any salary, compensation, or pay anywhere in the posting."),
    ("vague_salary", 'Instead of a concrete salary, write only "Gehalt je nach Erfahrung" or "Vergütung nach Vereinbarung". Do not include any numbers for compensation.'),
    ("dual_role", "This posting advertises TWO different but related roles in a single text (e.g. Senior and Junior, or Developer and DevOps). Use a shared intro then separate requirement sections."),
    ("broken_whitespace", "Simulate broken PDF extraction: randomly split some words across lines, add spurious line breaks mid-sentence, and occasionally merge two words without a space."),
    ("no_location", "Do NOT mention any city, region, or country. Do not say 'remote' either — just omit location entirely."),
    ("no_experience", "Do NOT mention any years of experience or seniority requirement anywhere."),
]

# --- Diversity pools ---

_INDUSTRIES = [
    "Automobilindustrie", "Fintech", "E-Commerce", "Versicherung", "Pharma",
    "Logistik", "Energieversorgung", "Medizintechnik", "Telekommunikation",
    "Beratung", "Maschinenbau", "Lebensmittelindustrie", "Immobilien",
    "Bildungstechnologie", "Reise & Tourismus", "Gaming", "Cybersecurity",
    "Halbleitertechnik", "Landwirtschaftstechnik", "Luft- und Raumfahrt",
    "Öffentlicher Dienst", "Verlagswesen", "Modeindustrie", "Sporttech",
]

_COMPANY_STYLES = [
    "a 15-person startup founded last year",
    "a mid-sized Mittelstand company with ~300 employees, family-owned for 3 generations",
    "a large DAX-listed corporation with 20,000+ employees",
    "a fast-growing scale-up (Series B, ~80 people)",
    "a traditional German engineering firm modernizing its tech stack",
    "a public-sector IT service provider",
    "a fully remote company with no physical office",
    "an international company with German headquarters",
    "a university spin-off / research-adjacent company",
    "a non-profit / NGO that needs tech talent",
]

_TONES = [
    "formal and corporate (Sie-form throughout)",
    "casual startup (Du-form, informal, emoji allowed)",
    "dry and factual — just bullet points, minimal prose",
    "enthusiastic and marketing-heavy with lots of superlatives",
    "plain and no-nonsense, like a Bundesagentur für Arbeit listing",
    "warm and people-focused, emphasizing team culture",
]

_FORMATS = [
    "Use markdown headers (##) and bullet lists.",
    "Use a plain-text format with no markdown — just paragraphs and line breaks, as if pasted from an email.",
    "Use a structured format with labeled sections like 'Aufgaben:', 'Anforderungen:', 'Wir bieten:'.",
    "Use a compact format — everything in one dense paragraph per section, no bullets.",
    "Use a two-column style: short key-value pairs at the top (Standort: X, Beginn: sofort, etc.) followed by prose.",
    "Format it like it was copy-pasted from a PDF — section headers in ALL CAPS.",
]

_SENIORITY_LABELS = [
    None, "Junior", "Senior", "Lead", "Principal", "Head of",
    "Werkstudent", "Praktikant", "(Berufseinsteiger)",
]

# Real German company name fragments for variety
_COMPANY_PREFIXES = [
    "Nord", "Süd", "Rhein", "Alpen", "Hanse", "Elb", "Spree", "Isar",
    "Bayern", "Sachsen", "Schwaben", "Franken", "Westfalen", "Pflanz",
    "Grün", "Blau", "Neu", "Alt", "Schnell", "Klar", "Fein", "Stark",
]
_COMPANY_CORES = [
    "tech", "logik", "data", "werk", "kraft", "sys", "net", "lab",
    "code", "soft", "flow", "hub", "media", "cloud", "link", "bit",
    "grid", "kern", "plan", "vision", "ware", "mind", "punkt", "basis",
]
_COMPANY_SUFFIXES = ["GmbH", "AG", "SE", "GmbH & Co. KG", "e.V.", "UG"]


def _random_company(rng: random.Random) -> str:
    return (
        rng.choice(_COMPANY_PREFIXES)
        + rng.choice(_COMPANY_CORES)
        + " "
        + rng.choice(_COMPANY_SUFFIXES)
    )


SYSTEM_PROMPT = """\
You are a German HR copywriter who produces highly varied, authentic job postings \
for the German market. Every posting you write must feel distinct — different company \
personality, sentence structure, vocabulary, and layout. NEVER reuse phrases like \
"führendes Unternehmen" or "innovative Lösungen" across postings. Vary your openings, \
section order, and level of detail. Use natural German HR vocabulary where appropriate: \
Vollzeit, Teilzeit, unbefristet, befristet, Homeoffice, Werkstudent, Gehalt, Vergütung, \
Jahresbrutto. Format salaries in German style (e.g. 65.000 €). \
Output ONLY the job posting text, no JSON, no meta-commentary."""


# ---------------------------------------------------------------------------
# Distribution extraction from data_jobs
# ---------------------------------------------------------------------------

def build_de_profile(seed: int = 42) -> dict[str, Any]:
    from datasets import load_dataset

    ds = load_dataset("lukebarousse/data_jobs", split="train", streaming=True)
    rows = [r for i, r in zip(range(800_000), ds) if r.get("job_country") == "Germany"]
    print(f"[synth_de] {len(rows)} Germany rows loaded from data_jobs")

    titles = Counter(r["job_title_short"] for r in rows if r.get("job_title_short"))
    cities = Counter(
        r["job_location"].split(",")[0].strip()
        for r in rows
        if r.get("job_location") and "Germany" not in r["job_location"].split(",")[0]
    )
    schedules = Counter(r["job_schedule_type"] for r in rows if r.get("job_schedule_type"))

    salaries = [r["salary_year_avg"] for r in rows if r.get("salary_year_avg")]
    salaries.sort()
    salary_quartiles = []
    if salaries:
        for q in (0.25, 0.5, 0.75):
            idx = int(len(salaries) * q)
            salary_quartiles.append(int(salaries[idx]))

    all_skills: list[str] = []
    for r in rows:
        raw = r.get("job_skills")
        if raw:
            try:
                skills = ast.literal_eval(raw) if isinstance(raw, str) else raw
                if isinstance(skills, list):
                    all_skills.extend(skills)
            except (ValueError, SyntaxError):
                pass
    top_skills = [s for s, _ in Counter(all_skills).most_common(60)]

    return {
        "titles": dict(titles.most_common(40)),
        "cities": dict(cities.most_common(30)),
        "schedules": dict(schedules),
        "salary_quartiles": salary_quartiles,
        "top_skills": top_skills,
    }


# ---------------------------------------------------------------------------
# Profile sampling
# ---------------------------------------------------------------------------

def _weighted_choice(rng: random.Random, freq: dict[str, int]) -> str:
    items = list(freq.keys())
    weights = list(freq.values())
    return rng.choices(items, weights=weights, k=1)[0]


def _sample_profile(profile: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    title = _weighted_choice(rng, profile["titles"])
    city = _weighted_choice(rng, profile["cities"])
    schedule = _weighted_choice(rng, profile["schedules"])

    sq = profile["salary_quartiles"]
    if sq:
        base = rng.choice(sq)
        salary_min = int(base * rng.uniform(0.85, 1.0))
        salary_max = int(base * rng.uniform(1.0, 1.25))
    else:
        salary_min, salary_max = 45_000, 75_000

    n_skills = rng.randint(3, 8)
    skills = rng.sample(profile["top_skills"], min(n_skills, len(profile["top_skills"])))
    mixed_lang = rng.random() < 0.3

    return {
        "title": title,
        "city": city,
        "schedule": schedule,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "skills": skills,
        "mixed_lang": mixed_lang,
        "company_name": _random_company(rng),
        "industry": rng.choice(_INDUSTRIES),
        "company_style": rng.choice(_COMPANY_STYLES),
        "tone": rng.choice(_TONES),
        "format": rng.choice(_FORMATS),
        "seniority": rng.choice(_SENIORITY_LABELS),
        "include_mwd": rng.random() < 0.8,
    }


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def _build_prompt(sampled: dict[str, Any], complication: tuple[str, str] | None, idx: int) -> str:
    title = sampled["title"]
    if sampled["seniority"]:
        title = f"{sampled['seniority']} {title}"
    if sampled["include_mwd"]:
        title += " (m/w/d)"

    lines = [
        f"Write a complete, realistic German job posting. Make it feel unique — posting #{idx}.\n",
        f"PROFILE:",
        f"- Job title: {title}",
        f"- Company: {sampled['company_name']} (a {sampled['company_style']} in the {sampled['industry']} sector)",
        f"- City: {sampled['city']}",
        f"- Schedule: {sampled['schedule']}",
        f"- Salary range: {sampled['salary_min']:,} – {sampled['salary_max']:,} € Jahresbrutto".replace(",", "."),
        f"- Required skills: {', '.join(sampled['skills'])}",
        f"\nSTYLE CONSTRAINTS:",
        f"- Tone: {sampled['tone']}",
        f"- Format: {sampled['format']}",
        f"- Invent specific, realistic details: team size, tech stack versions, project examples, perks.",
        f"- Do NOT use generic filler like 'führendes Unternehmen', 'innovative Lösungen', 'dynamisches Team'.",
        f"  Instead describe what the company actually does in concrete terms.",
    ]

    if sampled["mixed_lang"]:
        lines.append(
            "\nThe technical requirements section should be in English "
            "(as if from an international engineering team), rest in German."
        )

    if complication:
        lines.append(f"\nSPECIAL INSTRUCTION: {complication[1]}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generation loop
# ---------------------------------------------------------------------------

def generate(
    n: int = 200,
    hard_case_ratio: float = 0.35,
    seed: int = 42,
    model: str = "claude-haiku-4-5",
    concurrency: int = 15,
) -> list[dict[str, Any]]:
    import asyncio

    rng = random.Random(seed)
    profile = build_de_profile(seed=seed)

    n_hard = int(n * hard_case_ratio)
    assignments: list[tuple[str, str] | None] = [
        COMPLICATIONS[rng.randint(0, len(COMPLICATIONS) - 1)] for _ in range(n_hard)
    ] + [None] * (n - n_hard)
    rng.shuffle(assignments)

    # Pre-build all prompts and profiles
    sampled_profiles = []
    call_kwargs = []
    for i, complication in enumerate(assignments):
        sampled = _sample_profile(profile, rng)
        sampled_profiles.append((sampled, complication))
        prompt = _build_prompt(sampled, complication, idx=i)
        call_kwargs.append({
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "model": model,
            "temperature": 1.0,
            "max_tokens": 4096,
        })

    print(f"[synth_de] Sending {n} requests with concurrency={concurrency} …")
    responses = asyncio.run(teacher.call_many_async(call_kwargs, concurrency=concurrency))

    docs: list[dict[str, Any]] = []
    total_in = 0
    total_out = 0

    for i, (resp, (sampled, complication)) in enumerate(zip(responses, sampled_profiles)):
        total_in += resp["input_tokens"]
        total_out += resp["output_tokens"]
        docs.append({
            "doc_id": f"synth_de_{i:04d}",
            "text": resp["text"],
            "source": "synth_de",
            "lang": "de",
            "weak_labels": {
                "title": sampled["title"],
                "city": sampled["city"],
                "schedule": sampled["schedule"],
                "salary_min": sampled["salary_min"],
                "salary_max": sampled["salary_max"],
                "skills": sampled["skills"],
                "mixed_lang": sampled["mixed_lang"],
                "company_name": sampled["company_name"],
                "industry": sampled["industry"],
                "seniority": sampled["seniority"],
            },
            "complication": complication[0] if complication else None,
        })

    cost_in = total_in / 1_000_000 * _COST_PER_1M_INPUT
    cost_out = total_out / 1_000_000 * _COST_PER_1M_OUTPUT
    cost_total = cost_in + cost_out

    print(f"\n[synth_de] Done. {len(docs)} postings generated.")
    print(f"  Input tokens:  {total_in:>10,}")
    print(f"  Output tokens: {total_out:>10,}")
    print(f"  Estimated cost: ${cost_total:.2f} (in: ${cost_in:.2f}, out: ${cost_out:.2f})")

    return docs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic German job postings")
    parser.add_argument("-n", type=int, default=200)
    parser.add_argument("--hard-case-ratio", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", type=str, default="claude-haiku-4-5")
    parser.add_argument("--concurrency", type=int, default=15)
    parser.add_argument("--out", type=str, default=str(_DATA_RAW / "synth_de.jsonl"))
    args = parser.parse_args()

    docs = generate(n=args.n, hard_case_ratio=args.hard_case_ratio, seed=args.seed, model=args.model, concurrency=args.concurrency)

    from src.data_prep import save_jsonl
    save_jsonl(docs, args.out)


if __name__ == "__main__":
    main()
