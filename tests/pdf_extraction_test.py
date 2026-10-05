"""Smoke test: designed / multi-column resume layouts must not silently drop text.

Regression guard for passing ``ignore_graphics=True`` to ``pymupdf_rag.to_markdown``
in ``pdf.PDFHandler.extract_text_from_pdf``.

Designed resume templates (Canva, Adobe Express, ...) paint sidebar/section content
on decorative vector panels. Without ``ignore_graphics`` those panels are treated as
significant images and every text line drawn over them is dropped -- so whole
sections (skills, education, contact) vanish before the LLM ever sees them.

The fixture recreates the ``resume/sample.pdf`` persona (Barack Obama) in a two-column
layout with a coloured sidebar, then asserts the sidebar text survives extraction.
No API key / LLM required -- this exercises only the PDF -> Markdown stage.
"""

import os
import sys
import tempfile

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pdf  # noqa: E402


def _build_canva_resume(path):
    """Two-column 'Canva-style' resume: a coloured sidebar panel (Contact / Skills /
    Education) beside a plain main column (name / work / awards)."""
    navy, teal, grey, white, dark = (
        (0.13, 0.19, 0.28),
        (0.09, 0.46, 0.49),
        (0.85, 0.87, 0.90),
        (1, 1, 1),
        (0.12, 0.12, 0.14),
    )
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    sb = 205
    # decorative vector graphics (varied shapes => flagged "significant")
    page.draw_rect(pymupdf.Rect(0, 0, sb, 840), color=None, fill=navy)
    page.draw_circle(pymupdf.Point(sb / 2, 92), 58, color=white, fill=grey, width=3)
    page.draw_rect(pymupdf.Rect(24, 300, 182, 304), color=None, fill=teal)
    page.draw_rect(pymupdf.Rect(24, 470, 182, 474), color=None, fill=teal)

    def txt(x, y, s, size=10, color=dark, bold=False):
        page.insert_text(
            pymupdf.Point(x, y),
            s,
            fontsize=size,
            fontname="hebo" if bold else "helv",
            color=color,
        )

    # main column (plain white) -- survives extraction either way
    txt(sb + 22, 62, "Barack Obama", size=26, color=navy, bold=True)
    txt(sb + 22, 90, "44th President of the United States", size=11)
    y = 175
    txt(sb + 22, y, "WORK EXPERIENCE", size=13, color=teal, bold=True)
    y += 26
    txt(sb + 22, y, "President of the United States", size=11, bold=True)
    y += 16
    txt(sb + 22, y, "The White House  |  January 2009 - January 2017", size=9)
    y += 20
    for b in (
        "Served as the 44th President of the United States.",
        "Represented the United States in international diplomacy.",
    ):
        txt(sb + 22, y, "- " + b, size=9)
        y += 16

    # sidebar (drawn over the decorative panel) -- this is what the bug drops
    y = 175
    txt(28, y, "CONTACT", size=12, color=white, bold=True)
    y += 22
    for line in ("Phone: (555) 123-4567", "barack.obama@example.com", "Washington, DC"):
        txt(28, y, line, size=9, color=white)
        y += 16
    y = 325
    txt(28, y, "SKILLS", size=12, color=white, bold=True)
    y += 22
    for line in (
        "Executive Leadership",
        "Public Speaking",
        "Strategic Planning",
        "International Relations",
    ):
        txt(28, y, "- " + line, size=9, color=white)
        y += 17
    y = 495
    txt(28, y, "EDUCATION", size=12, color=white, bold=True)
    y += 22
    for line in ("Juris Doctor (J.D.)", "Harvard Law School", "1991"):
        txt(28, y, line, size=9, color=white)
        y += 16

    doc.save(path)


def test_designed_layout_sidebar_is_not_dropped():
    # extract_text_from_pdf uses no model; stub the provider so PDFHandler() needs
    # no API key.
    pdf.initialize_llm_provider = lambda *a, **k: None
    handler = pdf.PDFHandler()
    with tempfile.TemporaryDirectory() as d:
        fixture = os.path.join(d, "canva_resume.pdf")
        _build_canva_resume(fixture)
        text = handler.extract_text_from_pdf(fixture) or ""

    for needed in (
        "Juris Doctor",
        "Harvard Law School",
        "Executive Leadership",
        "barack.obama@example.com",
    ):
        assert needed in text, (
            f"designed-layout extraction dropped {needed!r} "
            "(to_markdown(ignore_graphics=True) regression?)"
        )


if __name__ == "__main__":
    test_designed_layout_sidebar_is_not_dropped()
    print("OK: designed-layout sidebar preserved")
