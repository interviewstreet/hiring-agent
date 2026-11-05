# Benchmark results

Model: `gemma3:4b` through Ollama, 140 runs on synthetic resumes, scored by the real `ResumeEvaluator`.
Raw output: `results/gemma3_140_runs.jsonl`. Reproduce with `run_real_scoring.py --per-group 10 --controls 40`.

| Measure | Result |
|---|---|
| Runs scored | 137 of 140 (3 cut-off model responses) |
| Clean resumes given a false bonus | 11 of 39, 35 points |
| False awards | 75: 65 removed, 10 sent to review, 0 kept |
| Valid awards | 42: 40 kept, 2 sent to review, 0 removed |
| Valid claims missed by the model | 8, of which 7 recovered, 0 false recoveries |
| Orchestrate rank/points corrections | 33, with 0 validation crashes |

## Limits

- One model and synthetic resumes. This is not a production accuracy measure.
- The cases and checker share an author, and earlier versions of the checker were tuned on some of them.
- Gemini was not tested. `qwen3:4b` timed out on this hardware, and `mistral:7b` was not run.
- 3 of 140 runs still fail on truncated model JSON, which this change does not address.
