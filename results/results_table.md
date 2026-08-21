| run | model | adapter | constrained | macro-F1 | hallucination | exact-match | p95 latency | prompt tokens | $/1000 docs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_1p7_tuned_v1 | Qwen/Qwen3-1.7B | — | true | 0.149 | 0.506 | 0.000 | 1955.8 | 896 | — |
| baseline_b1 | Qwen/Qwen3-8B | — | false | 0.685 | 0.125 | 0.005 | 6040.7 | 3377 | — |
| baseline_b2 | Qwen/Qwen3-8B | — | true | 0.752 | 0.127 | 0.010 | 6026.4 | 3377 | — |
| baseline_b3 | claude-haiku-4-5 | — | true | 0.999 | 0.000 | 0.990 | 0.6 | 2901 | 3.1221 |
| tuned_r32_lr2e4 | Qwen/Qwen3-1.7B | tuned | true | 0.194 | 0.000 | 0.000 | 704.9 | 896 | 0.0076 |
| tuned_r32_lr2e4_unconst | Qwen/Qwen3-1.7B | tuned | false | 0.775 | 0.033 | 0.005 | 1681.7 | 896 | 0.0076 |
