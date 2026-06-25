"""
Filter hidden or low-visibility PDF text before LLM resume extraction.

Mitigates white-on-white and tiny-font injection (see issue #273).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Union

import pymupdf

logger = logging.getLogger(__name__)

# Spans below this size are treated as hidden metadata (PoC footer uses 6pt).
MIN_VISIBLE_FONT_SIZE = 7.0

# RGB components all above this are treated as background-matching (near-white).
WHITE_COLOR_THRESHOLD = 0.90

# Resume PDFs must not embed GitHub enrichment blocks; only github.py adds those.
FORGED_GITHUB_BLOCK_RE = re.compile(
    r"===\s*GITHUB\s*DATA\s*===.*", re.DOTALL | re.IGNORECASE
)


def _span_rgb(color: int) -> tuple[float, float, float]:
    value = color & 0xFFFFFF
    r = ((value >> 16) & 0xFF) / 255.0
    g = ((value >> 8) & 0xFF) / 255.0
    b = (value & 0xFF) / 255.0
    return r, g, b


def is_hidden_span(
    span: dict,
    *,
    min_font_size: float = MIN_VISIBLE_FONT_SIZE,
    white_threshold: float = WHITE_COLOR_THRESHOLD,
) -> bool:
    """Return True if span is likely invisible or evasion text."""
    size = float(span.get("size", 12))
    if size < min_font_size:
        return True

    color = span.get("color", 0)
    if isinstance(color, int):
        r, g, b = _span_rgb(color)
        if r >= white_threshold and g >= white_threshold and b >= white_threshold:
            return True

    return False


def extract_visible_text_from_pdf(pdf_source: Union[str, Path, pymupdf.Document]) -> str:
    """
    Extract printable resume text, skipping hidden spans (near-white ink, tiny font).
    """
    owns_doc = False
    if isinstance(pdf_source, pymupdf.Document):
        doc = pdf_source
    else:
        doc = pymupdf.open(pdf_source)
        owns_doc = True

    try:
        lines: list[str] = []
        skipped_spans = 0
        kept_spans = 0

        for page in doc:
            page_dict = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    parts: list[str] = []
                    for span in line.get("spans", []):
                        if is_hidden_span(span):
                            skipped_spans += 1
                            continue
                        kept_spans += 1
                        parts.append(span.get("text", ""))
                    if parts:
                        lines.append("".join(parts).rstrip())

        text = "\n".join(lines).strip()
        logger.debug(
            "PDF visible extraction: %d kept spans, %d hidden spans, %d chars",
            kept_spans,
            skipped_spans,
            len(text),
        )
        return text
    finally:
        if owns_doc:
            doc.close()


def strip_forged_github_blocks(text: str) -> str:
    """Remove embedded === GITHUB DATA === blocks from untrusted resume text."""
    if not text:
        return text
    cleaned = FORGED_GITHUB_BLOCK_RE.sub("", text).strip()
    if cleaned != text:
        logger.warning("Removed forged === GITHUB DATA === block from resume text")
    return cleaned


def sanitize_resume_text_for_pipeline(text: str) -> str:
    """Defense-in-depth cleanup before LLM extraction or evaluation."""
    return strip_forged_github_blocks(text)
