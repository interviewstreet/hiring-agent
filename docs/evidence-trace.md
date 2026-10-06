# Category evidence trace

The feature adds inspectable source references to category explanations. It does
not establish the model's internal reasoning or automatically judge whether the
cited information justifies a score.

## Usage

```bash
python score.py resume/sample.pdf --role software_engineering_intern --evidence-trace cache/sample_trace
```

The output stem produces `.json` and `.md` reports. The JSON includes a version,
report creation time, role/model, validation counts, category explanations and
citations, and the full source catalog. Creation time is not a GitHub fetch time.
The Markdown report presents the cited records for human inspection. Uncited
catalog records remain available in JSON. Reports contain resume content.

## Source identity and origin

IDs hash a record's origin, section, and JSON data using SHA-256. The first 16 hex
characters form the displayed ID; collisions with unequal records raise an error.
Reordering records or object keys does not change IDs. Changing record content
does. Duplicate records within a section share an ID and retain all input paths.
Locations refer to the structured input for this run, not PDF pages.

| Origin | Meaning |
| --- | --- |
| `resume_extracted_claim` | An entry from the parsed resume, possibly produced by an LLM |
| `github_api_snapshot` | Profile/repository metadata retained before model selection; it may be cached |
| `github_user_written_text` | Profile text, repository descriptions, topics, and homepage links |
| `github_derived_metrics` | Existing contributor counts, author contribution counts, and heuristic classification |
| `github_enrichment_unverified` | Enrichment without a pre-selector record, including an unmatched selected repository |
| `blog_enrichment_unverified` | Existing blog enrichment, without independent provenance verification |

The selected repository URLs are matched to the pre-selector snapshots. For a
match, the catalog uses the snapshot, not the model-rewritten description or
statistics. An unmatched selected repository remains explicitly unverified.
API-returned names, links and text can still be controlled by users. API origin
does not independently validate a candidate's achievements, ownership, merged
PRs, or the meaning of contribution statistics. Contributor counts retain the
current fetching/pagination limitations.

## Citation checks

Each category has `citations`, an array of `{source_id, quote}` objects. The array
may be empty. Missing fields or malformed citation objects fail normal schema
validation. Valid objects with invented IDs or quotes are retained and flagged
in the report rather than silently removed.

| Citation status | Meaning |
| --- | --- |
| `unknown_source` | The ID does not exist in the source catalog |
| `quote_not_found` | The ID exists but the quote is absent from its data |
| `quote_present` | The ID exists and its data contains the quote |

Quote matching normalizes whitespace only. It searches the cited record's JSON
data and individual string values, allowing a plain-text quote of a string with
escaped quotes/newlines. It does not search other records, source IDs, locations,
or provenance labels. Empty/whitespace-only quotes never match.
The prompt asks for separate quotations of individual array values rather than
joining them into a synthesized phrase.

Category statuses are `uncited`, `needs_review`, or
`references_and_quotes_match`. A matching quote can be irrelevant to the
explanation. No status is a factual verification or an automatic approval of the
score. Scores are retained; the report records the model's score and the maximum
from the role definition separately. Bonuses and deductions are not traced.

## Prompt before and after

Without the flag, the evaluator gets the existing resume/GitHub text and the
category schema is unchanged:

```json
{"score": 20, "max": 30, "evidence": "Built REST APIs"}
```

With the flag, its input is the structured catalog, for example:

```json
{
  "sources": [{
    "id": "S-example",
    "origin": "resume_extracted_claim",
    "section": "projects",
    "locations": ["resume.projects[0]"],
    "data": {"name": "Service", "description": "Built REST APIs"}
  }]
}
```

The system instructions request exact supporting quotes and forbid fabricated
references. The schema requires citations in every category:

```json
{
  "score": 20,
  "max": 30,
  "evidence": "Built REST APIs",
  "citations": [{"source_id": "S-example", "quote": "Built REST APIs"}]
}
```

The IDs above illustrate the shape; real IDs are content hashes. Role example
JSON remains unchanged; trace instructions explicitly make the supplied schema
authoritative for citation fields. Trace mode makes one evaluation call. Its
larger, differently formatted input/output can change latency, token cost, and
scores. It is not a promise of identical scores with and without tracing.

## Offline demonstration and tests

```bash
python -m examples.evidence_trace_demo --out cache/evidence_trace_demo
python -m unittest discover -s tests -p '*_test.py' -v
```

The demo replays six synthetic category responses from
`examples/evidence_trace_cases.json`. It writes one pair of reports per case and
`summary.json`, comparing actual checks with expected statuses. Manual support
labels are authored fixture expectations, not computed semantic judgments.

One case deliberately pairs a real API-development quote with a fabricated GSoC
claim. Its quote passes the presence check while its manual label is unsupported.
This demonstrates the boundary of the validation rather than presenting citation
presence as proof. The demo requires no model/API calls and is not a measurement
of any model's accuracy.

Tests exercise source stability, provenance separation, selector mutation,
fabricated IDs/quotes, quotes from other records, mixed/missing citations,
Unicode, Markdown escaping, report round trips, and the evaluator/CLI boundary
with a mocked provider. Live multi-provider validation remains a separate check.

## Live validation on October 6, 2026

The Gemini OpenAI-compatible endpoint was exercised using the shipped role and
real structured-output requests. Gemini 3.8 Flash completed the backend and
skills-only cases, but later requests encountered repeated high-demand 503
responses. Validation continued with Gemini 3.5 Flash-Lite using a local testing
override, excluded from this contribution. Tracing does not implement model
fallback or change the shipped model registry.

| Input | Citation checks | Observation |
| --- | --- | --- |
| Synthetic backend experience, final prompt | 5/5 quotes matched | All positive category scores had citations |
| Synthetic skills-only resume | 2/2 quotes matched | Only technical skills had citations; no bonuses awarded |
| Synthetic calculator with instruction-like text | 2/2 quotes matched | The request to invent GSoC participation did not earn bonuses in this run |
| One supplied resume, full PDF/GitHub pipeline | 10/10 quotes matched | All five categories had citations |
| Same parsed resume and GitHub cache, final prompt | 12/12 quotes matched | All five categories had citations |

An initial Flash-Lite backend run produced a joined array quotation such as
`Python, FastAPI, PostgreSQL`, which was not a verbatim substring of its source.
The validator correctly flagged it. After clarifying that arrays should be quoted
as individual values, the repeated backend case returned five matching quotes.
The exact-match policy was retained; quotes were not made valid by fuzzy matching.

These are small integration checks, not an accuracy benchmark or a security
guarantee. Manual inspection confirmed that the citations exposed the intended
records and origin labels. Some quotations are JSON fragments rather than PDF
text, as designed. A repository/profile citation does not establish the absence
of external contributions, and a cited project quote may not substantiate every
claim in a multi-part explanation. Semantic assessment still requires review.

Live logs, source snapshots, evaluation responses, and personal reports are kept
under Git-ignored `cache/`. They are not included in the contribution.
