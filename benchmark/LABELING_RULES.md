# Bonus-claim labeling rules

Each case is one bonus the LLM awarded plus the resume text. The label answers:
"Would a careful human reviewer accept this bonus from this resume alone?"

- **supported**: the text states the candidate did the qualifying thing.
- **unsupported**: it is absent, only related, planned, failed, or belongs to someone else.

| Bonus | Supported | Unsupported |
|---|---|---|
| gsoc (+5) | Selected, participated, or contributed in Google Summer of Code, as student/contributor or mentor | Applied, rejected, preparing, attended a talk, helped others apply, wrote about it, a different program |
| girl_script (+3) | Participated as contributor, mentor, or project admin in Girl Script Summer of Code | Same exclusions; Google Summer of Code does not count |
| orchestrate (+1 to +4) | HackerRank Orchestrate result with an explicit rank equal to the claimed rank, within 500 | Participation with no rank, different stated rank, rank above 500, rank from another contest |
| founder (+3 to +5) | Founder or co-founder of a startup or company | Intern or staff at a startup, founder's office, student club founder, personal project, intern to a founder |
| early_engineer (+2 to +3) | Stated as a founding engineer or among the first 10-20 engineers/employees at a startup | Intern at a startup, "fast-growing startup" alone, first engineering hire of a large unit unstated, team size only |

Ambiguous wording stays out of the benchmark, so labels stay defensible. Hidden text is out of scope (see issue #273).
