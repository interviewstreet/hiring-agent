# Golden Dataset & Evaluation Framework

A golden dataset of labeled résumés plus a runner that measures how well the
hiring agent's scores agree with human judgment. Use it to compare models
(e.g. `gemma3:4b` vs. `gemini-2.0-flash`) or to catch regressions after changing
prompts.

Addresses [issue #308](https://github.com/interviewstreet/hiring-agent/issues/308).

## What it measures

The dataset feeds the agent at the **evaluator boundary**: each case supplies a
structured résumé (`JSONResume` shape) and optional GitHub data, and the runner
compares the evaluator's output against human-assigned **bands** and
**per-category tolerance ranges**. This isolates *scoring quality* — the part
that changes when you swap models — without the noise of PDF parsing, extraction,
or live GitHub calls.

All committed résumés are **synthetic** (no PII, no real GitHub accounts).

## Layout

```
evals/
├── golden/            # one JSON file per résumé case
├── metrics.py         # pure metric functions (offline, no deps)
├── run_eval.py        # loads golden/, runs the agent, reports metrics
└── tests/             # offline unit + smoke + dataset-integrity tests
```

## Running

From the repo root, with an LLM backend configured (see the main README):

```bash
# Run the whole dataset with the default backend
python -m evals.run_eval

# Average 3 runs per case to smooth LLM non-determinism, and save a report
python -m evals.run_eval --repeat 3 --out report.json

# Run a single case
python -m evals.run_eval --filter strong_oss_gsoc

# Compare a different model — just change the environment
LLM_PROVIDER=gemini DEFAULT_MODEL=gemini-2.0-flash python -m evals.run_eval

# Use as a regression gate (non-zero exit if band accuracy drops below 0.7)
python -m evals.run_eval --min-band-accuracy 0.7
```

The JSON report is stamped with the provider, model, case count, repeat count,
and timestamp, so reports from different models are directly comparable.

## Case format

One JSON file per résumé in `golden/`:

```jsonc
{
  "id": "strong_oss_gsoc",
  "description": "Short human-readable summary of the case.",
  "resume": { /* a JSONResume object — same shape models.JSONResume expects */ },
  "github": null,                      // or a synthetic github_data dict
  "labels": {
    "overall_band": "strong",          // "strong" | "medium" | "weak"
    "categories": {
      "open_source":      { "min": 26, "max": 35 },
      "self_projects":    { "min": 18, "max": 30 },
      "production":       { "min": 14, "max": 25 },
      "technical_skills": { "min": 7,  "max": 10 }
    },
    "rationale": "Why a human assigned these ranges — kept for auditability."
  }
}
```

- Category ranges are inclusive `[min, max]` and must sit within the category
  caps (open_source ≤ 35, self_projects ≤ 30, production ≤ 25, technical_skills ≤ 10).
- The **band** is bucketed from the agent's total score using the default
  thresholds **strong ≥ 70, medium ≥ 40, weak < 40** (on the 0–120 total scale).

## Adding a case

1. Copy an existing file in `golden/` and give it a unique `id`.
2. Write a synthetic résumé and assign category ranges + an overall band, with a
   `rationale`. Keep ranges wide enough to tolerate LLM noise but tight enough to
   be meaningful.
3. Run the integrity tests — they check the schema, that ranges are within caps,
   and that your ranges are internally consistent with the declared band:

   ```bash
   python -m pytest evals/tests/test_golden_dataset.py
   ```

## Metrics reported

- **Band exact accuracy** — fraction of cases whose predicted band matches the gold band.
- **Band within-one rate** — treats bands as ordinal (weak→strong is worse than weak→medium).
- **Overall / per-category within-range rate** — fraction of category scores landing inside the tolerance range.
- **Per-category bias** (mean signed error to the range midpoint) — reveals systematic over/under-scoring.
- **Per-category mean-miss** — average distance outside the range when a score misses.
- **Spearman rank correlation** — does the agent order candidates the way humans do?
- **Stability** (with `--repeat > 1`) — standard deviation of the total across repeats.

## Limitations / next steps

- Measures the evaluator only, not PDF extraction or GitHub enrichment. A
  full-pipeline (PDF-in) mode is a natural follow-up.
- The seed set is small (9 cases) and intended to be grown by contributors.
- Requires a running LLM backend; the tests, however, run fully offline via a
  stubbed evaluator.
