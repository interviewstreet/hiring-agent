# Contributing Guidelines

Thanks for your interest in improving this project. Contributions are welcome, including documentation updates, bug reports, feature requests, and code changes.

## Reporting Bugs

1. Check that the bug has not already been reported: https://github.com/interviewstreet/hiring-agent/issues
2. Open a new bug report: https://github.com/interviewstreet/hiring-agent/issues/new
3. Please include:
   - Clear description of the issue and expected behavior
   - Environment info: OS, Python version, hiring-agent commit or version
   - Steps to reproduce
   - Relevant logs or stack traces

> [!TIP]
> If the bug involves PDF parsing or model output, attach a minimal PDF and the exact model you used.

## Feature Requests

1. Check for existing requests: https://github.com/interviewstreet/hiring-agent/issues
2. Open a new feature request: https://github.com/interviewstreet/hiring-agent/issues/new
3. Describe the problem, the proposed solution, and any alternatives you considered.

## Contributing Code

1. Pick an issue from https://github.com/interviewstreet/hiring-agent/issues or open one first.
2. Comment that you are working on it to avoid duplicate efforts.
3. Fork the repo, then create a feature branch for your change.

### Development

1. Fork and clone your fork.
2. Create a fresh branch per change. Avoid pushing changes to the default branch of your fork.
3. Set up the environment and run the pipeline locally to validate changes
4. Run the CLI on a small sample to verify behavior:

### Coding Style

* Use [Black](https://black.readthedocs.io/en/stable/) for formatting.
* Keep functions short and focused. Prefer pure helpers for prompt assembly and transformations.

### Prompts and Providers

* Keep prompts declarative and provider agnostic.
* Avoid model specific tokens or formatting that only one provider supports.
* Changes to prompts should include short before and after examples in the pull request description.

### Tests and Smoke Checks

* Validate changes with a couple of real resumes under different providers when possible:

  * One run with Ollama using the default local model.
  * One run with Gemini if you have an API key.
* Add or adjust small smoke tests that exercise each stage with minimal inputs:

  * PDF to Markdown
  * Section extraction to JSON Resume
  * GitHub enrichment on a known username
  * Evaluation to JSON with the required fields


### Commit Messages

* Use clear, imperative subjects, for example: `fix: handle en dash date ranges in work parser`.
* Reference the issue number when applicable.

## Code of Conduct

Be respectful and collaborative. If you see unacceptable behavior, report it through an issue or contact the maintainers.
