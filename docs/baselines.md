# Baseline runs (B0–B3) — do NOT start RunPod until B3 smoke-test works locally.

## What each baseline is

| ID | run_id | Model | Prompt | Constrained | Backend |
|----|--------|-------|--------|-------------|---------|
| B0 | `baseline_b0` | Qwen3-1.7B | `zero_shot_v1` | false | vllm |
| B1 | `baseline_b1` | Qwen3-8B | `few_shot_v1` | false | vllm |
| B2 | `baseline_b2` | Qwen3-8B | `few_shot_v1` | true | vllm |
| B3 | `baseline_b3` | claude-haiku-4-5 | `v1` | true | api |

## Gotchas (baked into `run_eval`)

- Thinking **off** by default (`chat_template_kwargs.enable_thinking=false`). Keep it off for fine-tuned runs too.
- Constrained uses `response_format.json_schema`, **not** `guided_json`.
- Every result logs `tokens.prompt_avg_per_doc` — few-shot will be ~1.5–3k; tuned later ~40.

## 1) Run B3 first (no GPU, ~$1–2)

```bash
source .venv/bin/activate
python -m src.run_eval \
  --eval-set data/eval/eval_v1.jsonl \
  --backend api \
  --model claude-haiku-4-5 \
  --constrained true \
  --prompt-version v1 \
  --run-id baseline_b3 \
  --concurrency 8 \
  --notes "B3 teacher ceiling"
```

## 2) Serve on RunPod (thinking disabled server-wide too)

```bash
# Prefer BOTH server default and client flag (client already sends enable_thinking=false)
vllm serve Qwen/Qwen3-8B \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --default-chat-template-kwargs '{"enable_thinking": false}'
```

Then B1 + B2 against that server:

```bash
python -m src.run_eval \
  --eval-set data/eval/eval_v1.jsonl \
  --backend vllm --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen3-8B \
  --prompt-version few_shot_v1 \
  --constrained false \
  --enable-thinking false \
  --run-id baseline_b1 \
  --notes "B1 8B few-shot unconstrained"

python -m src.run_eval \
  --eval-set data/eval/eval_v1.jsonl \
  --backend vllm --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen3-8B \
  --prompt-version few_shot_v1 \
  --constrained true \
  --enable-thinking false \
  --run-id baseline_b2 \
  --notes "B2 8B few-shot constrained — number to beat"
```

## 3) Swap to 1.7B for B0

```bash
vllm serve Qwen/Qwen3-1.7B \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --default-chat-template-kwargs '{"enable_thinking": false}'

python -m src.run_eval \
  --eval-set data/eval/eval_v1.jsonl \
  --backend vllm --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen3-1.7B \
  --prompt-version zero_shot_v1 \
  --constrained false \
  --enable-thinking false \
  --run-id baseline_b0 \
  --notes "B0 1.7B zero-shot unconstrained"
```

## 4) Comparison table

```bash
python -m src.report_baselines
```

Deliverable: `results/baseline_b{0,1,2,3}.json` (+ `.preds.jsonl`) and the printed table.
B2 `macro_f1` is the number the fine-tune must beat; B2 vs later tuned `prompt_avg_per_doc` is the cost story.
