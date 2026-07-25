"""Detect suspicious PDF content before LLM evaluation."""

from __future__ import annotations

import logging
from typing import List

import pymupdf

from models import PdfIntegrityIssue, PdfIntegrityReport

logger = logging.getLogger(__name__)

OFF_PAGE_MARGIN = 50
MIN_SUSPICIOUS_FONT_SIZE = 2.0
WHITE_COLOR_THRESHOLD = 0.95
DUPLICATE_RATIO_THRESHOLD = 2.5


def _is_near_white(color: int) -> bool:
    if color is None:
        return False
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return r / 255 >= WHITE_COLOR_THRESHOLD and g / 255 >= WHITE_COLOR_THRESHOLD and b / 255 >= WHITE_COLOR_THRESHOLD


def scan_pdf_integrity(pdf_path: str) -> PdfIntegrityReport:
    issues: List[PdfIntegrityIssue] = []
    raw_char_count = 0
    visible_char_count = 0

    try:
        with pymupdf.open(pdf_path) as doc:
            for page_index, page in enumerate(doc):
                page_rect = page.rect
                text_dict = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)

                for block in text_dict.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            if not text.strip():
                                continue

                            raw_char_count += len(text)
                            size = span.get("size", 12)
                            color = span.get("color", 0)
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            x0, y0, x1, y1 = bbox

                            off_page = (
                                x1 < -OFF_PAGE_MARGIN
                                or y1 < -OFF_PAGE_MARGIN
                                or x0 > page_rect.width + OFF_PAGE_MARGIN
                                or y0 > page_rect.height + OFF_PAGE_MARGIN
                            )
                            tiny = size <= MIN_SUSPICIOUS_FONT_SIZE
                            invisible = _is_near_white(color)

                            if off_page:
                                issues.append(
                                    PdfIntegrityIssue(
                                        page=page_index + 1,
                                        issue_type="off_page_text",
                                        snippet=text[:80],
                                        severity="critical",
                                    )
                                )
                            elif invisible:
                                issues.append(
                                    PdfIntegrityIssue(
                                        page=page_index + 1,
                                        issue_type="invisible_text",
                                        snippet=text[:80],
                                        severity="critical",
                                    )
                                )
                            elif tiny:
                                issues.append(
                                    PdfIntegrityIssue(
                                        page=page_index + 1,
                                        issue_type="size_anomaly",
                                        snippet=text[:80],
                                        severity="warning",
                                    )
                                )
                            else:
                                visible_char_count += len(text)

                visible_markdown = page.get_text("text")
                visible_char_count = max(visible_char_count, len(visible_markdown.strip()))

    except Exception as exc:
        logger.error("PDF integrity scan failed: %s", exc)
        return PdfIntegrityReport(
            issues=[
                PdfIntegrityIssue(
                    page=0,
                    issue_type="scan_error",
                    snippet=str(exc)[:120],
                    severity="warning",
                )
            ],
            raw_char_count=0,
            visible_char_count=0,
            passed=True,
        )

    critical_count = sum(1 for issue in issues if issue.severity == "critical")
    ratio = raw_char_count / max(visible_char_count, 1)
    if ratio >= DUPLICATE_RATIO_THRESHOLD and critical_count == 0:
        issues.append(
            PdfIntegrityIssue(
                page=0,
                issue_type="duplicate_content",
                snippet=f"raw/visible char ratio {ratio:.1f}",
                severity="warning",
            )
        )

    passed = critical_count == 0
    return PdfIntegrityReport(
        issues=issues,
        raw_char_count=raw_char_count,
        visible_char_count=visible_char_count,
        passed=passed,
    )
