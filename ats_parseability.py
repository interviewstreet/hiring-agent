"""
Standalone PDF structural scan estimating how well a resume would survive a
real ATS text extractor (tables, multi-column layouts, and images are common
causes of silently dropped content). Independent of pdf.py's markdown
extraction pipeline -- opens the PDF directly with pymupdf.
"""

import logging
from typing import List, Optional, Tuple

import pymupdf
from pymupdf4llm.helpers.multi_column import column_boxes

from models import ParseabilityResult

logger = logging.getLogger(__name__)

TABLE_STRATEGY = "lines_strict"
TABLE_PENALTY = 15
MAX_TABLE_PENALTY = 45
MULTI_COLUMN_PENALTY = 20
EXTRA_COLUMN_PENALTY = 10
IMAGE_PENALTY = 5
MAX_IMAGE_PENALTY = 15
IMAGE_AREA_THRESHOLD = 0.05
COLUMN_OVERLAP_RATIO = 0.3


def _column_count(rects: List["pymupdf.Rect"]) -> int:
    best = 1
    for rect in rects:
        side_by_side = 1
        for other in rects:
            if other is rect:
                continue
            overlap_top = max(rect.y0, other.y0)
            overlap_bottom = min(rect.y1, other.y1)
            vertical_overlap = overlap_bottom - overlap_top
            min_height = min(rect.height, other.height)
            horizontally_disjoint = other.x0 >= rect.x1 or other.x1 <= rect.x0
            if min_height > 0 and vertical_overlap > COLUMN_OVERLAP_RATIO * min_height and horizontally_disjoint:
                side_by_side += 1
        best = max(best, side_by_side)
    return best


def _scan_page(page: "pymupdf.Page") -> Tuple[int, int, int]:
    tabs = page.find_tables(strategy=TABLE_STRATEGY)
    significant_tables = [t for t in tabs.tables if t.row_count >= 2 and t.col_count >= 2]
    table_rects = [pymupdf.Rect(t.bbox) for t in significant_tables]

    page_area = abs(page.rect)
    img_info = page.get_image_info()
    significant_images = [
        image for image in img_info if abs(pymupdf.Rect(image["bbox"])) >= IMAGE_AREA_THRESHOLD * page_area
    ]

    rects = column_boxes(page, avoid=table_rects)
    columns = _column_count(rects)

    return len(significant_tables), len(significant_images), columns


def _compute_score(table_count: int, image_count: int, max_columns: int) -> float:
    score = 100.0
    score -= TABLE_PENALTY * min(table_count, MAX_TABLE_PENALTY // TABLE_PENALTY)
    if max_columns >= 2:
        score -= MULTI_COLUMN_PENALTY
    if max_columns >= 3:
        score -= EXTRA_COLUMN_PENALTY
    score -= IMAGE_PENALTY * min(image_count, MAX_IMAGE_PENALTY // IMAGE_PENALTY)
    return max(0.0, score)


def _build_warnings(table_count: int, image_count: int, max_columns: int) -> List[str]:
    warnings = []
    if table_count > 0:
        warnings.append(
            f"{table_count} table(s) detected — many ATS parsers drop or scramble table content "
            "(skills grids, side-by-side contact blocks)."
        )
    if max_columns >= 2:
        warnings.append(
            f"Multi-column layout detected (up to {max_columns} columns) — many ATS parsers read "
            "left-to-right across columns, scrambling reading order."
        )
    if image_count > 0:
        warnings.append(
            f"{image_count} image(s)/graphic(s) detected — text inside images is invisible to most ATS parsers."
        )
    return warnings


def scan_pdf_parseability(pdf_path: str) -> Optional[ParseabilityResult]:
    try:
        with pymupdf.open(pdf_path) as doc:
            total_tables = 0
            total_images = 0
            max_columns = 1
            for page in doc:
                tables, images, columns = _scan_page(page)
                total_tables += tables
                total_images += images
                max_columns = max(max_columns, columns)

        return ParseabilityResult(
            table_count=total_tables,
            image_count=total_images,
            max_columns_detected=max_columns,
            warnings=_build_warnings(total_tables, total_images, max_columns),
            parseability_score=_compute_score(total_tables, total_images, max_columns),
        )
    except Exception as e:
        logger.warning(f"Failed to scan PDF parseability for {pdf_path}: {e}")
        return None
