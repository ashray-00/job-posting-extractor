# Job posting extractor — results report

**Eval set:** `data/eval/eval_v1.jsonl` (196 German synthetic jobs, frozen)  
**Primary metric:** macro-F1 over 16 fields  
**Goal:** beat baseline **B2** (Qwen3-8B few-shot + constrained decoding, macro-F1 **0.752**) with a smaller tuned model and a cheaper prompt.

---

## Headline

| Run | Model | Prompt | Constrained? | macro-F1 | Prompt tok/doc | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| **B2** (target) | Qwen3-8B | few-shot | yes | **0.752** | ~3377 | Strong few-shot baseline |
| **B1** | Qwen3-8B | few-shot | no | 0.685 | ~3377 | Same prompt, free JSON |
| **B3** | Claude Haiku | v1 | yes | 0.999 | ~2901 | Teacher-class; not the cost target |
| Base 1.7B | Qwen3-1.7B | tuned_v1 | yes | 0.149 | ~896 | Untuned small model fails |
| Tuned (constrained) | 1.7B + LoRA | tuned_v1 | yes | 0.194 | ~896 | Schema bug → sparse JSON |
| **Tuned (unconstrained)** | 1.7B + LoRA | tuned_v1 | **no** | **0.776** | **~896** | **Beats B2** |

**Verdict:** Best adapter (`r32_lr2e4`) with the short `tuned_v1` prompt and **unconstrained** decoding scores **0.776 macro-F1**, beating B2 by **+0.024**, while using about **3.8× fewer prompt tokens** (~896 vs ~3377) and a **~5× smaller** base model.

---

## What we trained

Three LoRA configs on Qwen3-1.7B (SFT from teacher-labeled Djinni/EMSCAD → filtered → deduped → 695 train / 100 val):

| Config | Final val loss | Train loss | Peak VRAM | Wall clock |
| --- | --- | --- | --- | --- |
| r16_lr1e4 | 0.110 | 0.104 | 5.8 GB | ~4.7 min |
| r32_lr1e4 | 0.101 | 0.089 | 6.1 GB | ~3.0 min |
| **r32_lr2e4** (picked) | **0.093** | **0.072** | 6.1 GB | ~3.0 min |

Adapters are under `results/adapters/`. Eval used the lowest-val-loss run.

---

## Forgetting / safety checks

On general chat + null-heavy salary docs (`results/forgetting.summary.json`):

- **JSON when not asked:** 0% (adapter never dumps schema on casual prompts)
- **Length:** adapter answers ~63% as long as base (shorter, still coherent)
- **Hallucination on null-heavy salary fields:** base 0.0 → adapter **0.012** (tiny; healthy)

Training did not turn the model into a “JSON-only” bot.

---

## Why constrained tuned eval looked terrible (0.19)

The constrained run (`tuned_r32_lr2e4`) reported **schema_valid = 1.0** but **omission_rate ≈ 0.82** and near-zero F1 on title/skills/location/etc. Completions were tiny (~36 tokens vs ~172 unconstrained).

**Cause:** the JSON schema sent to vLLM had **no `required` fields**, so the sampler was free to emit a sparse object (often only enums like `contract_type` / `currency` / `visa_sponsorship`). That is a **serving/schema bug**, not proof the adapter failed.

**Evidence:** same adapter + same prompt **without** constrained decoding → **0.776** and full field coverage.

A schema fix (`required` + `strict`) was added in `src/run_eval.py`; constrained re-eval was not re-run on the downloaded artifacts yet.

---

## Tuned unconstrained vs B2 (fair comparison)

| Metric | B2 | Tuned unconst | Winner |
| --- | --- | --- | --- |
| macro-F1 | 0.752 | **0.776** | Tuned |
| schema_valid | 0.903 | **1.000** | Tuned |
| hallucination_rate | 0.127 | **0.033** | Tuned |
| omission_rate | 0.126 | **0.037** | Tuned |
| prompt tokens / doc | ~3377 | **~896** | Tuned |
| model size | 8B | **1.7B + LoRA** | Tuned |

Head-to-head field flips (`baseline_b2__vs__tuned_r32_lr2e4_unconst.compare.md`):

- Tuned right / B2 wrong: **351**
- B2 right / Tuned wrong: **187**

### Where the small model wins

Large gains on structured / numeric / enum-ish fields:

| Field | B2 F1 | Tuned F1 | Δ |
| --- | --- | --- | --- |
| seniority | 0.600 | 0.723 | +0.123 |
| years_experience_min | 0.730 | 0.850 | +0.120 |
| location_city | 0.860 | 0.931 | +0.071 |
| salary_max | 0.925 | 0.988 | +0.064 |
| salary_min | 0.934 | 0.982 | +0.048 |
| currency / period | ~0.94 | ~1.00 | +0.06 |

### Where it still loses

| Field | B2 F1 | Tuned F1 | Δ | Typical error |
| --- | --- | --- | --- | --- |
| title | 0.804 | 0.643 | −0.161 | Drops gender suffix / slightly normalizes |
| contract_type | 0.906 | 0.847 | −0.059 | working_student ↔ internship |
| languages | 0.301 | 0.265 | −0.036 | Wrong CEFR level |
| required_skills | 0.182 | 0.163 | −0.019 | Set mismatch (both models weak) |

**Skills and languages are hard for everyone** on this eval (strict set / structure match). Both B2 and the tuned model sit in the 0.1–0.3 F1 band there; that dominates remaining headroom more than salary/location.

---

## Error profile (tuned unconstrained)

From `tuned_r32_lr2e4_unconst.errors.md`:

- Worst fields by error count: **required_skills**, **nice_to_have_skills**, **languages**, **title**, **seniority**
- Skills errors are mostly **wrong_value** (partial lists, extras, missing tools) — not schema failures
- Seniority: mix of wrong enum and **omission** (predicting null)
- Very few salary/currency mistakes

---

## Simple takeaway

1. **You met the project goal** on the frozen German eval: a fine-tuned **1.7B** model beats the **8B few-shot constrained** baseline.
2. **Cost/latency win:** ~**4× shorter prompts**, smaller model → cheaper serving if you keep unconstrained (or fix constrained schema and re-measure).
3. **Do not trust the 0.19 constrained tuned number** — that run was starved by a loose schema.
4. **Remaining work:** fix constrained decoding and re-eval; improve **title** / **contract_type** / **skills** (data or post-processing), not more LoRA sweeps on val loss alone.

---

## Artifact index

| Path | What it is |
| --- | --- |
| `results/baseline_b*.json` | B1/B2/B3 metrics |
| `results/tuned_r32_lr2e4_unconst.json` | Winning run |
| `results/tuned_r32_lr2e4.json` | Broken constrained run (schema) |
| `results/base_1p7_tuned_v1.json` | Untuned 1.7B control |
| `results/*compare.md` / `*.errors.md` | Error dumps |
| `results/forgetting.*` | Instruction-following / null-heavy checks |
| `results/adapters/r32_lr2e4/` | Best LoRA weights + `train_meta.json` |
