# Job posting extractor

A 1.7B model fine-tuned on **695** filtered teacher-labeled examples reaches **0.776 macro-F1** on a held-out set of **196** German synthetic postings (`eval_v1`), versus **0.752** for an 8B model with few-shot prompting and constrained decoding (B2), at roughly **~8× lower estimated serving cost per thousand documents** (~$0.008/1k from a closed-loop GPU bench vs ~$0.065/1k inferred from B2’s eval wall-clock on the same GPU rate — B2 was not re-benched with `src.bench`). Prompt tokens drop from ~3.4k/doc (few-shot) to ~0.9k/doc (~**3.8×**). Project one-time spend (Anthropic labelling + two days of RunPod) was about **$18.50**.

---

## Schema and design decisions

Single source of truth: [`schema/posting.py`](schema/posting.py) (Pydantic → JSON Schema for constrained decoding, filtering, and metrics).

| Field | Type | Design note |
|-------|------|-------------|
| `title` | `str \| null` | Free text; null if unstated |
| `seniority` | enum \| null | Closed set: intern…head |
| `contract_type` | enum \| null | Includes DE-relevant `working_student` |
| `workload` | enum \| null | `full_time` / `part_time` |
| `salary_min` / `salary_max` | `int \| null` | Integers only after normalisation |
| `salary_period` | enum \| null | year / month / hour |
| `currency` | ISO 4217 \| null | Exactly 3 uppercase letters |
| `remote_policy` | enum \| null | onsite / hybrid / remote |
| `location_city` | `str \| null` | |
| `location_country` | ISO 3166-1 alpha-2 \| null | |
| `required_skills` / `nice_to_have_skills` | `list[str]` | **Empty list = none stated; `null` forbidden on lists** |
| `years_experience_min` | `int \| null` | |
| `languages` | `{lang, level}[]` | ISO 639-1 + CEFR / native |
| `visa_sponsorship` | `bool \| null` | |

**Why this shape**

- **Null vs `[]`:** On scalars, `null` means “not in the document” and is a correct answer. On lists, `[]` means the same — forbidding list-nulls stops models from mixing “missing” with “empty.”
- **Closed enums** where HR language is messy but the downstream product needs a small set of values.
- **Strict currency/country codes** so metrics can score without fuzzy geopolitics.
- **Skills as unordered sets** after normalisation (see `src/normalize.py`) — order in the posting must not matter; exact string match would be worthless.

Frozen after day one: `data/eval/` and `src/metrics.py`. Prompt versions live in `src/prompts.py` / teacher prompts; the tuned path uses a short `tuned_v1` instruction (no few-shot blob).

---

## Data provenance and licences

| Source | Licence / access | Role |
|--------|------------------|------|
| **Djinni** (`lang-uk/recruitment-dataset-job-descriptions-english`) | MIT | Real EN/RU IT postings → teacher labels → train |
| **EMSCAD** (Kaggle `shivamb/real-or-fake-fake-jobposting-prediction`) | Kaggle ToS | Real postings with partial structured fields (salary, contract, remote) → teacher labels + **weak-label calibration** |
| **Synthetic German** (`synth_de`) | Generated | **Entire frozen eval set** (`eval_v1`) |
| **ESCO** | EU open data | Skill / occupation vocabulary for normalisation (not used as posting text) |
| **`lukebarousse/data_jobs`** | — | **Distribution reference only** (no description text; never extraction input) |

### Why German is synthetic

There was no clean, redistributable German job-description corpus with hand-structured gold at the field grain this schema needs. Building a real DE eval set means hiring annotators under local labour-posting licences. Instead, German postings were **generated** (teacher + `src/synth_de.py`) with salary/location/seniority marginals inspired by public DE job-market tables (`data_jobs` as distributional prior only). That buys a reproducible eval quickly; it does **not** buy “German real-world difficulty.” See [Where this is wrong](#where-this-is-wrong).

Training text is overwhelmingly **English** (Djinni/EMSCAD). Eval is **100% `synth_de`**. Cross-lingual transfer is part of the claim — and part of the risk.

Pipeline sketch: sample corpus → teacher extract (`claude-haiku-4-5`) → reject on schema/grounding (~19% reject on the v2 pass) → MinHash near-dedup + eval contamination check → 695 train / 100 val SFT rows → LoRA on Qwen3-1.7B.

---

## Evaluation methodology

### Eval set

- File: `data/eval/eval_v1.jsonl` (**frozen**, n=**196**, all `source=synth_de`).
- Labels produced with the teacher stack, then treated as gold for scoring. PROJECT notes aimed at ~180 hand-verified; the shipped file is 196 lines — treat “hand-verified” as aspirational process, not an independent third-party audit.
- Difficulty tags: `clean` (192) vs `adversarial` (4). The adversarial slice is too small to interpret.

### Metrics (frozen in `src/metrics.py`)

- **macro-F1:** unweighted mean of per-field F1 after normalisation.
- Null–null on scalars counts as a true negative, not a miss.
- **hallucination_rate / omission_rate** over (example, field) pairs.
- **schema_valid_rate**, **exact_record_match**, skill-set F1 after ESCO-ish normalisation.

### Baselines

| ID | Model | Prompt | Constrained | macro-F1 |
|----|-------|--------|-------------|----------|
| B1 | Qwen3-8B | few-shot | no | 0.685 |
| **B2** | Qwen3-8B | few-shot | **yes** | **0.752** |
| B3 | Claude Haiku 4.5 | teacher v1 | yes | 0.999 |
| Untuned 1.7B | Qwen3-1.7B | tuned_v1 | yes | 0.149 |
| **Tuned (this work)** | 1.7B + LoRA | tuned_v1 | **no\*** | **0.776** |

\*Constrained decoding on the adapter initially collapsed to sparse JSON because the raw Pydantic schema omitted top-level `required` (valid empty-ish objects). Unconstrained eval is the fair quality number; schema-fix lives in `src/run_eval.py` for a re-run.

### Teacher calibration

Before trusting labels, teacher extracts were checked against **EMSCAD weak fields** (contract, remote) and Djinni-side sanity (`src/calibrate_teacher.py`). Prompt **v2** tightened literal grounding after early over-extraction. Rejection sampling (`src/filter.py`) drops schema-invalid and poorly grounded rows.

### Contamination

`src/dedup.py` (MinHash LSH) removes near-duplicates within train and against the frozen eval texts so we are not fine-tuning on paraphrases of the test set.

### Forgetting smoke check

On 50 non-extraction prompts, the adapter emitted JSON **0%** of the time when not asked. On null-heavy salary docs, hallucination rate rose only to ~0.012 vs 0.0 for base (`results/forgetting.summary.json`).

---

## Results

### Headline runs

| run | model | adapter | constr. | macro-F1 | hallu. | exact | p95 lat (ms) | prompt tok/doc | $/1000 docs |
|-----|-------|---------|---------|----------|--------|-------|--------------|----------------|-------------|
| baseline_b1 | Qwen3-8B | — | false | 0.685 | 0.125 | 0.005 | 6041 | 3377 | — |
| **baseline_b2** | Qwen3-8B | — | true | **0.752** | 0.127 | 0.010 | 6026 | 3377 | ~0.065† |
| baseline_b3 | Haiku 4.5 | — | true | 0.999 | 0.000 | 0.990 | — | 2901 | 3.12 (API) |
| base_1p7_tuned_v1 | 1.7B | — | true | 0.149 | 0.506 | 0.000 | 1956 | 896 | — |
| tuned_r32_lr2e4 | 1.7B | LoRA | true | 0.194 | 0.000 | 0.000 | 705 | 896 | 0.0076‡ |
| **tuned_r32_lr2e4_unconst** | 1.7B | LoRA | **false** | **0.776** | **0.033** | 0.005 | 1682 | **896** | **0.0076‡** |

† B2 $/1000 inferred from eval wall-clock + `$0.40`/GPU-hour — **not** a `src.bench` sweep.  
‡ From `results/bench_tuned_r32_lr2e4.json` (best concurrency mean docs/hour).

Source table also: `results/results_table.md`.

### Per-field F1 (B2 vs tuned unconstrained)

| field | B2 | Tuned | Δ |
|-------|-----|-------|---|
| title | 0.804 | 0.643 | −0.161 |
| seniority | 0.600 | 0.723 | +0.123 |
| years_experience_min | 0.730 | 0.850 | +0.120 |
| location_city | 0.860 | 0.931 | +0.071 |
| salary_max | 0.925 | 0.988 | +0.064 |
| salary_min | 0.934 | 0.982 | +0.048 |
| currency | 0.938 | 0.997 | +0.059 |
| salary_period | 0.940 | 1.000 | +0.060 |
| workload | 0.938 | 0.974 | +0.036 |
| location_country | 0.938 | 0.966 | +0.028 |
| remote_policy | 0.927 | 0.943 | +0.016 |
| nice_to_have_skills | 0.108 | 0.135 | +0.027 |
| visa_sponsorship | 1.000 | 1.000 | 0 |
| required_skills | 0.182 | 0.163 | −0.019 |
| languages | 0.301 | 0.265 | −0.036 |
| contract_type | 0.906 | 0.847 | −0.059 |

Tuned wins on structured / numeric / enum-ish fields; loses on **title**, **contract_type**, and stays weak on **skills / languages** (as does B2).

### Per-slice (tuned unconstrained)

| slice | n | macro-F1 |
|-------|---|----------|
| clean | 192 | 0.775 |
| adversarial | 4 | 0.792 |
| source = synth_de | 196 | 0.776 |

Head-to-head field flips vs B2: tuned right / B2 wrong **351**; B2 right / tuned wrong **187** (`results/baseline_b2__vs__tuned_r32_lr2e4_unconst.compare.md`).

---

## Cost and payback

### One-time project cost (`configs/costs.yaml`)

| Line | USD |
|------|-----|
| Anthropic (19–20 Aug UTC, Haiku re-runs + Sonnet on the 19th) | 11.09 |
| RunPod GPU cloud (20–21 Aug) | 6.89 |
| RunPod storage (20–21 Aug) | 0.55 |
| Human labelling (booked) | 0.00 |
| **Total** | **18.53** |

### Serving

- Tuned 1.7B + LoRA: **`src.bench`** on a 4090-class pod → best mean **~52k docs/hour** (conc 64, fixed 256-token `ignore_eos` load) → **~$0.0076 / 1000 docs** at `$0.40`/GPU-hour.
- B2 8B: **no full bench** (cost). Rough eval-throughput estimate ~$0.065 / 1000 docs at the same GPU rate.
- Haiku API baseline (B3): **~$3.12 / 1000 docs** from token billing on the eval run.

### Payback chart

`results/payback.png` was **not** generated: fair payback needs a B2 `src.bench` file we skipped to save GPU. With the rough B2 estimate above, training cost (~$18.50) divides by per-doc savings on the order of **a few thousand documents** before the fine-tune is “paid back” versus renting 8B few-shot on the same GPU — treat that as directional only until B2 is benched the same way.

Regenerate table anytime:

```bash
python -m src.report --skip-payback
```

---

## Where this is wrong

This section is the part that matters.

### Fields the model is unreliable on

- **`required_skills` / `nice_to_have_skills` (F1 ~0.13–0.18):** Both B2 and the tuned model fail hard. Gold sets are long and brittle; predictions miss tools, add neighbors (Power BI vs DAX), or merge required/nice-to-have. Set-F1 after normalisation is kinder than exact field F1 but still not product-ready without a human or a skills ontology in the loop.
- **`languages` (~0.27):** CEFR levels are frequently off (B1 vs C1); omissions are common. Enum-looking but easy to get subtly wrong.
- **`title` (0.64 vs B2 0.80):** Tuned drops gender markers `(m/w/d)`, normalises casing, or truncates. Strict string F1 punishes harmless edits; users may not care — metrics do.
- **`contract_type`:** Systematic confusion **working_student ↔ internship** on DE-style ads.
- **`seniority`:** Better than B2 overall, but still mixes null vs junior/senior and over-predicts “senior.”

If your product needs skills/languages/title fidelity, **do not ship this adapter as-is**; use it for salary/location/remote/enums and keep a second stage (or human) for skills.

### Teacher bias

Eval gold and training labels both come from **the same teacher family** (Haiku). B3 scoring ~0.999 on this eval is not an independent ceiling — it is close to “teacher agrees with teacher.” Calibration against EMSCAD weak labels reduces some failure modes; it does not create an independent German gold standard. Gains over B2 may partly be “match the teacher’s style” rather than “recover ground truth.”

### Synthetic German ≠ real German

The whole eval is **`synth_de`**. Difficulty is whatever the generator made (formatting tricks, English requirement blocks inside DE text, European number formats). It is **not** the long-tail of real Bewerbungs-German, agency boilerplate, PDF-converted garbage, or multi-column portals. High DE macro-F1 here can evaporate on real postings. Conversely, failures on synth may be generator artifacts.

### n = 196 is small

Macro-F1 differences **under ~3 points** are not meaningful. Tuned **0.776** vs B2 **0.752** is a **+2.4** gap — inside that fog. Prefer the **cost** story (tokens, model size, measured docs/hour) and the **per-field** pattern (structured fields up, skills still broken) over the headline delta. The adversarial slice (n=4) should be ignored for decisions.

### Constrained decoding footgun

A “schema_valid = 1.0, macro-F1 = 0.19” run looked like a failed train; it was a **serving schema** with no `required` fields. Always read omission rate and completion length, not validity alone.

### Cost claims

Serving $/1k for the tuned model is from a real bench; for B2 it is **inferred**. Do not quote “8× cheaper than 8B” in a paper without an identical bench protocol. API Haiku $/1k is real but compares a different billing regime.

### Train scale

This is **hundreds** of SFT rows, not multi-thousand. The opening myth of “2,600 filtered examples” would overstate the data; the honest number is **695** train + **100** val after filter and dedup.

---

## Repo map

See [`PROJECT.md`](PROJECT.md) for contributor rules (frozen eval/metrics, results record shape). Key entry points:

```bash
python -m src.run_eval …      # quality
python -m src.bench …         # docs/hour (needs live vLLM)
python -m src.report …        # table (+ payback if both benches exist)
```

Artifacts live under `results/`. Adapters under `results/adapters/r32_lr2e4/`.
