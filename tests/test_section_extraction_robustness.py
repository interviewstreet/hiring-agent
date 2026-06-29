"""#4 robustness: one section failing to parse must not discard the entire
resume. We keep every section that parsed and only give up when nothing
usable was extracted. The LLM is stubbed out via _extract_section_data, so no
model is involved.
"""

from pdf import PDFHandler


def _make_handler():
    return PDFHandler()


def test_partial_section_failure_keeps_good_sections(monkeypatch):
    handler = _make_handler()

    # education and projects "fail" (None); the rest parse fine.
    section_results = {
        "basics": {"basics": {"name": "X"}},
        "work": {"work": [{"name": "Acme", "position": "SWE Intern"}]},
        "education": None,
        "skills": {"skills": [{"name": "Python"}]},
        "projects": None,
        "awards": {"awards": []},
    }

    def fake_extract(text_content, section_name, return_model=None):
        return section_results[section_name]

    monkeypatch.setattr(handler, "_extract_section_data", fake_extract)

    result = handler._extract_all_sections_separately("resume text")

    assert result is not None
    assert result.basics is not None and result.basics.name == "X"
    assert result.work and result.work[0].name == "Acme"
    assert result.skills and result.skills[0].name == "Python"
    # Failed sections are simply absent, not fatal.
    assert result.education is None
    assert result.projects is None


def test_all_sections_failing_returns_none(monkeypatch):
    handler = _make_handler()
    monkeypatch.setattr(handler, "_extract_section_data", lambda *a, **k: None)

    assert handler._extract_all_sections_separately("resume text") is None
