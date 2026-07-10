# Dynamic Role-Based Scoring Algorithm

## Overview
The Hiring Agent evaluates resumes on a standardized **120-point scale** (100 base points + 20 bonus points). Previously, the maximum points a candidate could earn in any given category (e.g., Open Source, Production) were hardcoded. 

This created a major discrepancy: A Senior Engineer lacking open source contributions would lose up to 35 points, even if they had immense production impact. Conversely, an Intern with incredible side projects was capped at 30 points and penalized for lacking professional experience.

To solve this, the agent now employs a **Dynamic Scoring Algorithm**. The 100 base points dynamically shift and re-allocate their maximum limits based on the candidate's target role.

## Category Weight Distribution

The following table dictates the maximum possible score for each category depending on the `--experience` level passed to the CLI. These weights are configured in `roles.py`.

| Role | Open Source | Self Projects | Production | Tech Skills | Total |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Intern** | 30 | 45 | 10 | 15 | 100 |
| **Entry** | 25 | 35 | 20 | 20 | 100 |
| **Junior** | 20 | 25 | 35 | 20 | 100 |
| **Mid** | 15 | 20 | 45 | 20 | 100 |
| **Senior** | 15 | 15 | 45 | 25 | 100 |
| **Staff/Principal** | 15 | 15 | 45 | 25 | 100 |

*Note: `open_source` and `self_projects` never drop below 15 maximum points. This ensures that startup founders, entrepreneurs, and active open-source maintainers always receive credit for their external work, even at the Principal engineering level.*

## How It Works Under the Hood

1. **Role Identification**: When `score.py` is executed, the `--experience` argument maps to a specific dictionary in `roles.py` called `ROLE_MAX_SCORES`.
2. **Context Injection**: The `evaluator.py` module fetches these `max_weights` and passes them directly into the Jinja2 template rendering context.
3. **Dynamic Prompt Math**: Instead of using static text bounds (e.g., `HIGH SCORES (25-35 points)`), the prompt templates use Jinja math to calculate the qualitative score bounds as a percentage of the dynamic maximum. 

For example, if evaluating a Senior Engineer, the Jinja template dynamically renders the prompt to cap Self Projects at 15 points, and shifts the definition of a "High Score" to be roughly 9-15 points. Because all math is computed prior to sending the prompt to the LLM (Gemini or Ollama), the system remains perfectly declarative and provider-agnostic.
