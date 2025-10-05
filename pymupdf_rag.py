"""
This script accepts a PDF document filename and converts it to a text file
in Markdown format, compatible with the GitHub standard.

It must be invoked with the filename like this:

python pymupdf_rag.py input.pdf [-pages PAGES]

The "PAGES" parameter is a string (containing no spaces) of comma-separated
page numbers to consider. Each item is either a single page number or a
number range "m-n". Use "N" to address the document's last page number.
Example: "-pages 2-15,40,43-N"

It will produce a markdown text file called "input.md".

Text will be sorted in Western reading order. Any table will be included in
the text in markdwn format as well.

Dependencies
-------------
PyMuPDF v1.25.5 or later

Copyright and License
----------------------
Copyright (C) 2024-2025 Artifex Software, Inc.

PyMuPDF4LLM is free software: you can redistribute it and/or modify it under the
terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option)
any later version.

Alternative licensing terms are available from the licensor.
For commercial licensing, see <https://www.artifex.com/> or contact
Artifex Software, Inc., 39 Mesa Street, Suite 108A, San Francisco,
CA 94129, USA, for further information.
"""

import os
import string
from binascii import b2a_base64
import pymupdf
from pymupdf import mupdf
from pymupdf4llm.helpers.get_text_lines import get_raw_lines, is_white
from pymupdf4llm.helpers.multi_column import column_boxes
from dataclasses import dataclass
from collections import defaultdict

pymupdf.TOOLS.unset_quad_corrections(True)

# Characters recognized as bullets when starting a line.
bullet = tuple(
    [
        "- ",
        "* ",
        "> ",
        chr(0xB6),
        chr(0xB7),
        chr(8224),
        chr(8225),
        chr(8226),
        chr(0xF0A7),
        chr(0xF0B7),
    ]
    + list(map(chr, range(9632, 9680)))
)

GRAPHICS_TEXT = "\n![](%s)\n"


class IdentifyHeaders:
    """Compute data for identifying header text.

    All non-white text from all selected pages is extracted and its font size
    noted as a rounded value.
    The most frequent font size (and all smaller ones) is taken as body text
    font size.
    Larger font sizes are mapped to strings of multiples of '#', the header
    tag in Markdown, which in turn is Markdown's representation of HTML's
    header tags <h1> to <h6>.
    Larger font sizes than body text but smaller than the <h6> font size are
    represented as <h6>.
    """

    def __init__(
        self,
        doc: str,
        pages: list = None,
        body_limit: float = 12,  # force this to be body text
        max_levels: int = 6,  # accept this many header levels
    ):
        """Read all text and make a dictionary of fontsizes.

        Args:
            doc: PDF document or filename
            pages: consider these page numbers only
            body_limit: treat text with larger font size as a header
        """
        if not isinstance(max_levels, int) or max_levels not in range(1, 7):
            raise ValueError("max_levels must be an integer between 1 and 6")
        if isinstance(doc, pymupdf.Document):
            mydoc = doc
        else:
            mydoc = pymupdf.open(doc)

        if pages is None:  # use all pages if omitted
            pages = range(mydoc.page_count)

        fontsizes = defaultdict(int)
        for pno in pages:
            page = mydoc.load_page(pno)
            blocks = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)["blocks"]
            for span in [  # look at all non-empty horizontal spans
                s
                for b in blocks
                for l in b["lines"]
                for s in l["spans"]
                if not is_white(s["text"])
            ]:
                fontsz = round(span["size"])  # # compute rounded fontsize
                fontsizes[fontsz] += len(span["text"].strip())  # add character count

        if mydoc != doc:
            # if opened here, close it now
            mydoc.close()

        # maps a fontsize to a string of multiple # header tag characters
        self.header_id = {}

        # If not provided, choose the most frequent font size as body text.
        # If no text at all on all pages, just use body_limit.
        # In any case all fonts not exceeding
        temp = sorted(
            [(k, v) for k, v in fontsizes.items()], key=lambda i: (i[1], i[0])
        )
        if temp:
            # most frequent font size
            self.body_limit = max(body_limit, temp[-1][0])
        else:
            self.body_limit = body_limit

        # identify up to 6 font sizes as header candidates
        sizes = sorted(
            [f for f in fontsizes.keys() if f > self.body_limit],
            reverse=True,
        )[:max_levels]

        # make the header tag dictionary
        for i, size in enumerate(sizes, start=1):
            self.header_id[size] = "#" * i + " "
        if self.header_id.keys():
            self.body_limit = min(self.header_id.keys()) - 1

    def get_header_id(self, span: dict, page=None) -> str:
        """Return appropriate markdown header prefix.

        Given a text span from a "dict"/"rawdict" extraction, determine the
        markdown header prefix string of 0 to n concatenated '#' characters.
        """
        fontsize = round(span["size"])  # compute fontsize
        if fontsize <= self.body_limit:
            return ""
        hdr_id = self.header_id.get(fontsize, "")
        return hdr_id


class TocHeaders:
    """Compute data for identifying header text.

    This is an alternative to IdentifyHeaders. Instead of running through the
    full document to identify font sizes, it uses the document's Table Of
    Contents (TOC) to identify headers on pages.
    Like IdentifyHeaders, this also is no guarantee to find headers, but it
    represents a good chance for appropriately built documents. In such cases,
    this method can be very much faster and more accurate, because we can
    directly use the hierarchy level of TOC items to ientify the header level.
    Examples where this works very well are the Adobe PDF documents.
    """

    def __init__(self, doc: str):
        """Read and store the TOC of the document."""
        if isinstance(doc, pymupdf.Document):
            mydoc = doc
        else:
            mydoc = pymupdf.open(doc)

        self.TOC = doc.get_toc()
        if mydoc != doc:
            # if opened here, close it now
            mydoc.close()

    def get_header_id(self, span: dict, page=None) -> str:
        """Return appropriate markdown header prefix.

        Given a text span from a "dict"/"rawdict" extraction, determine the
        markdown header prefix string of 0 to n concatenated '#' characters.
        """
        if not page:
            return ""
        # check if this page has TOC entries with an actual title
        my_toc = [t for t in self.TOC if t[1] and t[-1] == page.number + 1]
        if not my_toc:  # no TOC items present on this page
            return ""
        # Check if the span matches a TOC entry. This must be done in the
        # most forgiving way: exact matches are rare animals.
        text = span["text"].strip()  # remove leading and trailing whitespace
        for t in my_toc:
            title = t[1].strip()  # title of TOC entry
            lvl = t[0]  # level of TOC entry
            if text.startswith(title) or title.startswith(text):
                # found a match: return the header tag
                return "#" * lvl + " "
        return ""


# store relevant parameters here
@dataclass
class Parameters:
    pass


def refine_boxes(boxes, enlarge=0):
    """Join any rectangles with a pairwise non-empty overlap.

    Accepts and returns a list of Rect items.
    Note that rectangles that only "touch" each other (common point or edge)
    are not considered as overlapping.
    Use a positive "enlarge" parameter to enlarge rectangle by these many
    points in every direction.

    TODO: Consider using a sweeping line algorithm for this.
    """
    delta = (-enlarge, -enlarge, enlarge, enlarge)
    new_rects = []
    # list of all vector graphic rectangles
    prects = boxes[:]

    while prects:  # the algorithm will empty this list
        r = +prects[0] + delta  # copy of first rectangle
        repeat = True  # initialize condition
        while repeat:
            repeat = False  # set false as default
            for i in range(len(prects) - 1, 0, -1):  # from back to front
                if r.intersects(prects[i].irect):  # enlarge first rect with this
                    r |= prects[i]
                    del prects[i]  # delete this rect
                    repeat = True  # indicate must try again

        # first rect now includes all overlaps
        new_rects.append(r)
        del prects[0]

    new_rects = sorted(set(new_rects), key=lambda r: (r.x0, r.y0))
    return new_rects


def is_significant(box, paths):
    """Check whether the rectangle "box" contains 'signifiant' drawings.

    This means that some path is contained in the "interior" of box.
    To this end, we build a sub-box of 90% of the original box and check
    whether this still contains drawing paths.
    """
    if box.width > box.height:
        d = box.width * 0.025
    else:
        d = box.height * 0.025
    nbox = box + (d, d, -d, -d)  # nbox covers 90% of box interior
    # paths contained in, but not equal to box:
    my_paths = [p for p in paths if p["rect"] in box and p["rect"] != box]
    widths = set(round(p["rect"].width) for p in my_paths) | {round(box.width)}
    heights = set(round(p["rect"].height) for p in my_paths) | {round(box.height)}
    if len(widths) == 1 or len(heights) == 1:
        return False  # all paths are horizontal or vertical lines / rectangles
    for p in my_paths:
        rect = p["rect"]
        if (
            not (rect & nbox).is_empty and not p["rect"].is_empty
        ):  # intersects interior: significant!
            return True
        # Remaining case: a horizontal or vertical line
        # horizontal line:
        if (
            1
            and rect.y0 == rect.y1
            and nbox.y0 <= rect.y0 <= nbox.y1
            and rect.x0 < nbox.x1
            and rect.x1 > nbox.x0
        ):
            pass  # return True
        # vertical line
        if (
            1
            and rect.x0 == rect.x1
            and nbox.x0 <= rect.x0 <= nbox.x1
            and rect.y0 < nbox.y1
            and rect.y1 > nbox.y0
        ):
            pass  # return True
    return False


def to_markdown(
    doc,
    *,
    pages=None,
    hdr_info=None,
    write_images=False,
    embed_images=False,
    ignore_images=False,
    ignore_graphics=False,
    detect_bg_color=True,
    image_path="",
    image_format="png",
    image_size_limit=0.05,
    filename=None,
    force_text=True,
    page_chunks=False,
    page_separators=False,
    margins=0,
    dpi=150,
    page_width=612,
    page_height=None,
    table_strategy="lines_strict",
    graphics_limit=None,
    fontsize_limit=3,
    ignore_code=False,
    extract_words=False,
    show_progress=False,
    use_glyphs=False,
    ignore_alpha=False,
) -> str:
    """Process the document and return the text of the selected pages.

    Args:
        doc: pymupdf.Document or string.
        pages: list of page numbers to consider (0-based).
        hdr_info: callable or object having method 'get_hdr_info'.
        write_images: (bool) save images / graphics as files.
        embed_images: (bool) embed images in markdown text (base64 encoded)
        image_path: (str) store images in this folder.
        image_format: (str) use this image format. Choose a supported one.
        force_text: (bool) output text despite of image background.
        page_chunks: (bool) whether to segment output by page.
        page_separators: (bool) whether to include page separators in output.
        margins: omit content overlapping margin areas.
        dpi: (int) desired resolution for generated images.
        page_width: (float) assumption if page layout is variable.
        page_height: (float) assumption if page layout is variable.
        table_strategy: choose table detection strategy
        graphics_limit: (int) if vector graphics count exceeds this, ignore all.
        ignore_code: (bool) suppress code-like formatting (mono-space fonts)
        extract_words: (bool, False) include "words"-like output in page chunks
        show_progress: (bool, False) print progress as each page is processed.
        use_glyphs: (bool, False) replace the Invalid Unicode by glyph numbers.
        ignore_alpha: (bool, True) ignore text with alpha = 0 (transparent).

    """
    if write_images is False and embed_images is False and force_text is False:
        raise ValueError("Image and text on images cannot both be suppressed.")
    if embed_images is True:
        write_images = False
        image_path = ""
    if not 0 <= image_size_limit < 1:
        raise ValueError("'image_size_limit' must be non-negative and less than 1.")
    DPI = dpi
    IGNORE_CODE = ignore_code
    IMG_EXTENSION = image_format
    EXTRACT_WORDS = extract_words
    if EXTRACT_WORDS is True:
        page_chunks = True
        ignore_code = True
    IMG_PATH = image_path
    if IMG_PATH and write_images is True and not os.path.exists(IMG_PATH):
        os.mkdir(IMG_PATH)

    if not isinstance(doc, pymupdf.Document):
        doc = pymupdf.open(doc)

    FILENAME = doc.name if filename is None else filename
    GRAPHICS_LIMIT = graphics_limit
    FONTSIZE_LIMIT = fontsize_limit
    IGNORE_IMAGES = ignore_images
    IGNORE_GRAPHICS = ignore_graphics
    DETECT_BG_COLOR = detect_bg_color
    if doc.is_form_pdf or (doc.is_pdf and doc.has_annots()):
        doc.bake()

    # for reflowable documents allow making 1 page for the whole document
    if doc.is_reflowable:
        if hasattr(page_height, "__float__"):
            # accept user page dimensions
            doc.layout(width=page_width, height=page_height)
        else:
            # no page height limit given: make 1 page for whole document
            doc.layout(width=page_width, height=792)
            page_count = doc.page_count
            height = 792 * page_count  # height that covers full document
            doc.layout(width=page_width, height=height)

    if pages is None:  # use all pages if no selection given
        pages = list(range(doc.page_count))

    if hasattr(margins, "__float__"):
        margins = [margins] * 4
    if len(margins) == 2:
        margins = (0, margins[0], 0, margins[1])
    if len(margins) != 4:
        raise ValueError("margins must be one, two or four floats")
    elif not all(hasattr(m, "__float__") for m in margins):
        raise ValueError("margin values must be floats")

    # If "hdr_info" is not an object with a method "get_header_id", scan the
    # document and use font sizes as header level indicators.
    if callable(hdr_info):
        get_header_id = hdr_info
    elif hasattr(hdr_info, "get_header_id") and callable(hdr_info.get_header_id):
        get_header_id = hdr_info.get_header_id
    elif hdr_info is False:
        get_header_id = lambda s, page=None: ""
    else:
        hdr_info = IdentifyHeaders(doc)
        get_header_id = hdr_info.get_header_id

    def max_header_id(spans, page):
        hdr_ids = sorted(
            [l for l in set([len(get_header_id(s, page=page)) for s in spans]) if l > 0]
        )
        if not hdr_ids:
            return ""
        return "#" * (hdr_ids[0] - 1) + " "

    def resolve_links(links, span):
        """Accept a span and return a markdown link string.

        Args:
            links: a list as returned by page.get_links()
            span: a span dictionary as returned by page.get_text("dict")

        Returns:
            None or a string representing the link in MD format.
        """
        bbox = pymupdf.Rect(span["bbox"])  # span bbox
        span_text = span["text"].strip()

        # Find all links that overlap with this span
        overlapping_links = []
        for link in links:
            hot = link["from"]  # the hot area of the link
            # Check if the link area intersects with the span bbox
            if bbox.intersects(hot):
                overlapping_links.append(link)

        if not overlapping_links:
            return None

        # If only one link, return simple format
        if len(overlapping_links) == 1:
            link = overlapping_links[0]
            # Check if this looks like a partial URL (starts with http or contains domain parts)
            if span_text.startswith("http"):
                # Use the full link URL as the display text
                return f'[{link["uri"]}]({link["uri"]})'
            else:
                return f'[{span_text}]({link["uri"]})'

        # Multiple links found - need to split the text
        return _resolve_multiple_links(span_text, overlapping_links, bbox)

    def _resolve_multiple_links(span_text, links, span_bbox):
        """Resolve multiple links within a single span text.

        Args:
            span_text: The text content of the span
            links: List of overlapping links
            span_bbox: The bounding box of the span

        Returns:
            str: Markdown formatted text with multiple links
        """
        # Common patterns for multiple links
        if "|" in span_text:
            # Split by pipe separator
            parts = [part.strip() for part in span_text.split("|")]
            if len(parts) == len(links):
                # Perfect match - each part corresponds to a link
                result_parts = []
                for i, (part, link) in enumerate(zip(parts, links)):
                    result_parts.append(f'[{part}]({link["uri"]})')
                return " | ".join(result_parts)
            elif len(parts) >= len(links):
                # More parts than links - try to match intelligently
                return _match_parts_to_links(parts, links, span_bbox)

        # Try to identify individual words that should be linked
        words = span_text.split()
        if len(words) >= len(links):
            return _match_words_to_links(words, links, span_bbox)

        # Fallback: return the first link with the full text
        return f'[{span_text}]({links[0]["uri"]})'

    def _match_parts_to_links(parts, links, span_bbox):
        """Match parts of text to specific links based on content and position."""
        # Common platform names to match
        platform_keywords = {
            "github": ["github", "git"],
            "linkedin": ["linkedin", "linked"],
            "hackerrank": ["hackerrank", "hacker"],
            "twitter": ["twitter", "tweet"],
            "portfolio": ["portfolio", "site", "website"],
            "behance": ["behance"],
            "dribbble": ["dribbble"],
            "leetcode": ["leetcode", "leet"],
            "stackoverflow": ["stackoverflow", "stack"],
        }

        result_parts = []
        used_links = set()

        for part in parts:
            part_lower = part.lower()
            matched_link = None

            # Try to match by platform keywords
            for platform, keywords in platform_keywords.items():
                if any(keyword in part_lower for keyword in keywords):
                    # Find corresponding link
                    for i, link in enumerate(links):
                        if i not in used_links:
                            uri = link.get("uri", "").lower()
                            if platform in uri:
                                matched_link = link
                                used_links.add(i)
                                break
                    if matched_link:
                        break

            # If no keyword match, try to find the best remaining link
            if not matched_link and links:
                for i, link in enumerate(links):
                    if i not in used_links:
                        matched_link = link
                        used_links.add(i)
                        break

            if matched_link:
                result_parts.append(f'[{part}]({matched_link["uri"]})')
            else:
                result_parts.append(part)

        return " | ".join(result_parts)

    def _match_words_to_links(words, links, span_bbox):
        """Match individual words to links based on position and content."""
        # Simple heuristic: distribute links evenly among words
        if len(words) == len(links):
            result_parts = []
            for word, link in zip(words, links):
                result_parts.append(f'[{word}]({link["uri"]})')
            return " ".join(result_parts)

        # If more words than links, try to match by content
        return _match_parts_to_links(words, links, span_bbox)

    def save_image(parms, rect, i):
        """Optionally render the rect part of a page.

        We will ignore images that are empty or that have an edge smaller
        than x% of the corresponding page edge."""
        page = parms.page
        if (
            rect.width < page.rect.width * image_size_limit
            or rect.height < page.rect.height * image_size_limit
        ):
            return ""
        if write_images is True or embed_images is True:
            pix = page.get_pixmap(clip=rect, dpi=DPI)
        else:
            return ""
        if pix.height <= 0 or pix.width <= 0:
            return ""

        if write_images is True:
            filename = os.path.basename(parms.filename).replace(" ", "-")
            image_filename = os.path.join(
                IMG_PATH, f"{filename}-{page.number}-{i}.{IMG_EXTENSION}"
            )
            pix.save(image_filename)
            return image_filename.replace("\\", "/")
        elif embed_images is True:
            # make a base64 encoded string of the image
            data = b2a_base64(pix.tobytes(IMG_EXTENSION)).decode()
            data = f"data:image/{IMG_EXTENSION};base64," + data
            return data
        return ""

    def write_text(
        parms,
        clip: pymupdf.Rect,
        tables=True,
        images=True,
        force_text=force_text,
    ):
        """Output the text found inside the given clip.

        This is an alternative for plain text in that it outputs
        text enriched with markdown styling.
        The logic is capable of recognizing headers, body text, code blocks,
        inline code, bold, italic and bold-italic styling.
        There is also some effort for list supported (ordered / unordered) in
        that typical characters are replaced by respective markdown characters.

        'tables'/'images' indicate whether this execution should output these
        objects.
        """

        if clip is None:
            clip = parms.clip
        out_string = ""

        # This is a list of tuples (linerect, spanlist)
        nlines = get_raw_lines(
            parms.textpage,
            clip=clip,
            tolerance=3,
            ignore_invisible=not parms.accept_invisible,
        )
        nlines = [
            l for l in nlines if not intersects_rects(l[0], parms.tab_rects.values())
        ]

        parms.line_rects.extend([l[0] for l in nlines])  # store line rectangles

        prev_lrect = None  # previous line rectangle
        prev_bno = -1  # previous block number of line
        code = False  # mode indicator: outputting code
        prev_hdr_string = None

        for lrect, spans in nlines:
            # there may be tables or images inside the text block: skip them
            if intersects_rects(lrect, parms.img_rects):
                continue

            # ------------------------------------------------------------
            # Pick up tables ABOVE this text block
            # ------------------------------------------------------------
            if tables:
                tab_candidates = [
                    (i, tab_rect)
                    for i, tab_rect in parms.tab_rects.items()
                    if tab_rect.y1 <= lrect.y0
                    and i not in parms.written_tables
                    and (
                        0
                        or lrect.x0 <= tab_rect.x0 < lrect.x1
                        or lrect.x0 < tab_rect.x1 <= lrect.x1
                        or tab_rect.x0 <= lrect.x0 < lrect.x1 <= tab_rect.x1
                    )
                ]
                for i, _ in tab_candidates:
                    out_string += "\n" + parms.tabs[i].to_markdown(clean=False) + "\n"
                    if EXTRACT_WORDS:
                        # for "words" extraction, add table cells as line rects
                        cells = sorted(
                            set(
                                [
                                    pymupdf.Rect(c)
                                    for c in parms.tabs[i].header.cells
                                    + parms.tabs[i].cells
                                    if c is not None
                                ]
                            ),
                            key=lambda c: (c.y1, c.x0),
                        )
                        parms.line_rects.extend(cells)
                    parms.written_tables.append(i)
                    prev_hdr_string = None

            # ------------------------------------------------------------
            # Pick up images / graphics ABOVE this text block
            # ------------------------------------------------------------
            if images:
                for i in range(len(parms.img_rects)):
                    if i in parms.written_images:
                        continue
                    r = parms.img_rects[i]
                    if r.y1 <= lrect.y0 and (
                        0
                        or lrect.x0 <= r.x0 < lrect.x1
                        or lrect.x0 < r.x1 <= lrect.x1
                        or r.x0 <= lrect.x0 < lrect.x1 <= r.x1
                    ):
                        pathname = save_image(parms, r, i)
                        if pathname:
                            out_string += GRAPHICS_TEXT % pathname

                        # recursive invocation
                        if force_text is True:
                            img_txt = write_text(
                                parms,
                                r,
                                tables=False,
                                images=False,
                                force_text=True,
                            )

                            if not is_white(img_txt):
                                out_string += img_txt
                        parms.written_images.append(i)
                        prev_hdr_string = None

            parms.line_rects.append(lrect)
            # if line rect is far away from the previous one, add a line break
            if (
                len(parms.line_rects) > 1
                and lrect.y1 - parms.line_rects[-2].y1 > lrect.height * 1.5
            ):
                out_string += "\n"
            # make text string for the full line
            text = " ".join([s["text"] for s in spans]).strip()

            # full line strikeout?
            all_strikeout = all([s["char_flags"] & 1 for s in spans])
            # full line italic?
            all_italic = all([s["flags"] & 2 for s in spans])
            # full line bold?
            all_bold = all([(s["flags"] & 16) or (s["char_flags"] & 8) for s in spans])
            # full line mono-spaced?
            all_mono = all([s["flags"] & 8 for s in spans])

            # if line is a header, this will return multiple "#" characters,
            # otherwise an empty string
            hdr_string = max_header_id(spans, page=parms.page)  # a header?

            if hdr_string:  # if a header line, process it specially
                # Check if any spans in this heading have links
                has_links = False
                for s in spans:
                    if resolve_links(parms.links, s):
                        has_links = True
                        break

                if has_links:
                    # Process heading with links span-by-span
                    header_text = ""
                    for s in spans:
                        # Apply heading formatting to each span
                        span_text = s["text"].strip()

                        # Apply font formatting
                        if all_mono:
                            span_text = "`" + span_text + "`"
                        if all_italic:
                            span_text = "_" + span_text + "_"
                        if all_bold:
                            span_text = "**" + span_text + "**"
                        if all_strikeout:
                            span_text = "~~" + span_text + "~~"

                        # Resolve links for this span
                        ltext = resolve_links(parms.links, s)
                        if ltext:
                            header_text += ltext + " "
                        else:
                            header_text += span_text + " "

                    # Add the heading prefix and output
                    if hdr_string != prev_hdr_string:
                        out_string += hdr_string + header_text.strip() + "\n"
                    else:
                        # intercept if header text has been broken in multiple lines
                        while out_string.endswith("\n"):
                            out_string = out_string[:-1]
                        out_string += " " + header_text.strip() + "\n"
                    prev_hdr_string = hdr_string
                    continue
                else:
                    # No links in heading, process as before
                    if all_mono:
                        text = "`" + text + "`"
                    if all_italic:
                        text = "_" + text + "_"
                    if all_bold:
                        text = "**" + text + "**"
                    if all_strikeout:
                        text = "~~" + text + "~~"
                    if hdr_string != prev_hdr_string:
                        out_string += hdr_string + text + "\n"
                    else:
                        # intercept if header text has been broken in multiple lines
                        while out_string.endswith("\n"):
                            out_string = out_string[:-1]
                        out_string += " " + text + "\n"
                    prev_hdr_string = hdr_string
                    continue

            prev_hdr_string = hdr_string

            # start or extend a code block
            if all_mono and not IGNORE_CODE:
                if not code:  # if not already in code output mode:
                    out_string += "```\n"  # switch on "code" mode
                    code = True
                # compute approx. distance from left - assuming a width
                # of 0.5*fontsize.
                delta = int((lrect.x0 - clip.x0) / (spans[0]["size"] * 0.5))
                indent = " " * delta

                out_string += indent + text + "\n"
                continue  # done with this line

            if code and not all_mono:
                out_string += "```\n"  # switch off code mode
                code = False

            span0 = spans[0]
            bno = span0["block"]  # block number of line
            if bno != prev_bno:
                out_string += "\n"
                prev_bno = bno

            if (  # check if we need another line break
                prev_lrect
                and lrect.y1 - prev_lrect.y1 > lrect.height * 1.5
                or span0["text"].startswith("[")
                or span0["text"].startswith(bullet)
                or span0["flags"] & 1  # superscript?
            ):
                out_string += "\n"
            prev_lrect = lrect

            # this line is not all-mono, so switch off "code" mode
            if code:  # in code output mode?
                out_string += "```\n"  # switch of code mode
                code = False

            for i, s in enumerate(spans):  # iterate spans of the line
                # decode font properties
                mono = s["flags"] & 8
                bold = s["flags"] & 16 or s["char_flags"] & 8
                italic = s["flags"] & 2
                strikeout = s["char_flags"] & 1

                prefix = ""
                suffix = ""
                if mono:
                    prefix = "`" + prefix
                    suffix += "`"
                if bold:
                    prefix = "**" + prefix
                    suffix += "**"
                if italic:
                    prefix = "_" + prefix
                    suffix += "_"
                if strikeout:
                    prefix = "~~" + prefix
                    suffix += "~~"

                # convert intersecting link to markdown syntax
                ltext = resolve_links(parms.links, s)
                if ltext:
                    text = f"{hdr_string}{prefix}{ltext}{suffix} "
                else:
                    text = f"{hdr_string}{prefix}{s['text'].strip()}{suffix} "
                if text.startswith(bullet):
                    text = "- " + text[1:]
                    text = text.replace("  ", " ")
                    dist = span0["bbox"][0] - clip.x0
                    cwidth = (span0["bbox"][2] - span0["bbox"][0]) / len(span0["text"])
                    if cwidth == 0.0:
                        cwidth = span0["size"] * 0.5
                    text = " " * int(round(dist / cwidth)) + text

                out_string += text
            if not code:
                out_string += "\n"
        out_string += "\n"
        if code:
            out_string += "```\n"  # switch of code mode
            code = False
        out_string += "\n\n"
        return (
            out_string.replace(" \n", "\n").replace("  ", " ").replace("\n\n\n", "\n\n")
        )

    def is_in_rects(rect, rect_list):
        """Check if rect is contained in a rect of the list."""
        for i, r in enumerate(rect_list, start=1):
            if rect in r:
                return i
        return 0

    def intersects_rects(rect, rect_list):
        """Check if middle of rect is contained in a rect of the list."""
        delta = (-1, -1, 1, 1)  # enlarge rect_list members somewhat by this
        enlarged = rect + delta
        abs_enlarged = abs(enlarged) * 0.5
        for i, r in enumerate(rect_list, start=1):
            if abs(enlarged & r) > abs_enlarged:
                return i
        return 0

    def output_tables(parms, text_rect):
        """Output tables above given text rectangle."""
        this_md = ""  # markdown string for table(s) content
        if text_rect is not None:  # select tables above the text block
            for i, trect in sorted(
                [j for j in parms.tab_rects.items() if j[1].y1 <= text_rect.y0],
                key=lambda j: (j[1].y1, j[1].x0),
            ):
                if i in parms.written_tables:
                    continue
                this_md += parms.tabs[i].to_markdown(clean=False) + "\n"
                if EXTRACT_WORDS:
                    # for "words" extraction, add table cells as line rects
                    cells = sorted(
                        set(
                            [
                                pymupdf.Rect(c)
                                for c in parms.tabs[i].header.cells
                                + parms.tabs[i].cells
                                if c is not None
                            ]
                        ),
                        key=lambda c: (c.y1, c.x0),
                    )
                    parms.line_rects.extend(cells)
                parms.written_tables.append(i)  # do not touch this table twice

        else:  # output all remaining tables
            for i, trect in parms.tab_rects.items():
                if i in parms.written_tables:
                    continue
                this_md += parms.tabs[i].to_markdown(clean=False) + "\n"
                if EXTRACT_WORDS:
                    # for "words" extraction, add table cells as line rects
                    cells = sorted(
                        set(
                            [
                                pymupdf.Rect(c)
                                for c in parms.tabs[i].header.cells
                                + parms.tabs[i].cells
                                if c is not None
                            ]
                        ),
                        key=lambda c: (c.y1, c.x0),
                    )
                    parms.line_rects.extend(cells)
                parms.written_tables.append(i)  # do not touch this table twice
        return this_md

    def output_images(parms, text_rect, force_text):
        """Output images and graphics above text rectangle."""
        if not parms.img_rects:
            return ""
        this_md = ""  # markdown string
        if text_rect is not None:  # select images above the text block
            for i, img_rect in enumerate(parms.img_rects):
                if img_rect.y0 > text_rect.y0:
                    continue
                if img_rect.x0 >= text_rect.x1 or img_rect.x1 <= text_rect.x0:
                    continue
                if i in parms.written_images:
                    continue
                pathname = save_image(parms, img_rect, i)
                parms.written_images.append(i)  # do not touch this image twice
                if pathname:
                    this_md += GRAPHICS_TEXT % pathname
                if force_text:
                    img_txt = write_text(
                        parms,
                        img_rect,
                        tables=False,  # we have no tables here
                        images=False,  # we have no other images here
                        force_text=True,
                    )
                    if not is_white(img_txt):  # was there text at all?
                        this_md += img_txt
        else:  # output all remaining images
            for i, img_rect in enumerate(parms.img_rects):
                if i in parms.written_images:
                    continue
                pathname = save_image(parms, img_rect, i)
                parms.written_images.append(i)  # do not touch this image twice
                if pathname:
                    this_md += GRAPHICS_TEXT % pathname
                if force_text:
                    img_txt = write_text(
                        parms,
                        img_rect,
                        tables=False,  # we have no tables here
                        images=False,  # we have no other images here
                        force_text=True,
                    )
                    if not is_white(img_txt):
                        this_md += img_txt

        return this_md

    def page_is_ocr(page):
        """Check if page exclusivley contains OCR text.

        For this to be true, all text must be written as "ignore-text".
        """
        try:
            text_types = set([b[0] for b in page.get_bboxlog() if "text" in b[0]])
            if text_types == {"ignore-text"}:
                return True
        except:
            pass
        return False

    def get_bg_color(page):
        """Determine the background color of the page.

        The function returns a PDF RGB color triple or None.
        We check the color of 10 x 10 pixel areas in the four corners of the
        page. If they are unicolor and of the same color, we assume this to
        be the background color.
        """
        pix = page.get_pixmap(
            clip=(page.rect.x0, page.rect.y0, page.rect.x0 + 10, page.rect.y0 + 10)
        )
        if not pix.samples or not pix.is_unicolor:
            return None
        pixel_ul = pix.pixel(0, 0)  # upper left color
        pix = page.get_pixmap(
            clip=(page.rect.x1 - 10, page.rect.y0, page.rect.x1, page.rect.y0 + 10)
        )
        if not pix.samples or not pix.is_unicolor:
            return None
        pixel_ur = pix.pixel(0, 0)  # upper right color
        if not pixel_ul == pixel_ur:
            return None
        pix = page.get_pixmap(
            clip=(page.rect.x0, page.rect.y1 - 10, page.rect.x0 + 10, page.rect.y1)
        )
        if not pix.samples or not pix.is_unicolor:
            return None
        pixel_ll = pix.pixel(0, 0)  # lower left color
        if not pixel_ul == pixel_ll:
            return None
        pix = page.get_pixmap(
            clip=(page.rect.x1 - 10, page.rect.y1 - 10, page.rect.x1, page.rect.y1)
        )
        if not pix.samples or not pix.is_unicolor:
            return None
        pixel_lr = pix.pixel(0, 0)  # lower right color
        if not pixel_ul == pixel_lr:
            return None
        return (pixel_ul[0] / 255, pixel_ul[1] / 255, pixel_ul[2] / 255)

    def get_metadata(doc, pno):
        meta = doc.metadata.copy()
        meta["file_path"] = FILENAME
        meta["page_count"] = doc.page_count
        meta["page"] = pno + 1
        return meta

    def sort_words(words: list) -> list:
        """Reorder words in lines.

        The argument list must be presorted by bottom, then left coordinates.

        Words with similar top / bottom coordinates are assumed to belong to
        the same line and will be sorted left to right within that line.
        """
        if not words:
            return []
        nwords = []
        line = [words[0]]
        lrect = pymupdf.Rect(words[0][:4])
        for w in words[1:]:
            if abs(w[1] - lrect.y0) <= 3 or abs(w[3] - lrect.y1) <= 3:
                line.append(w)
                lrect |= w[:4]
            else:
                line.sort(key=lambda w: w[0])
                nwords.extend(line)
                line = [w]
                lrect = pymupdf.Rect(w[:4])
        line.sort(key=lambda w: w[0])
        nwords.extend(line)
        return nwords

    def get_page_output(
        doc, pno, margins, textflags, FILENAME, IGNORE_IMAGES, IGNORE_GRAPHICS
    ):
        """Process one page.

        Args:
            doc: pymupdf.Document
            pno: 0-based page number
            textflags: text extraction flag bits

        Returns:
            Markdown string of page content and image, table and vector
            graphics information.
        """
        page = doc[pno]
        page.remove_rotation()  # make sure we work on rotation=0
        parms = Parameters()  # all page information
        parms.page = page
        parms.filename = FILENAME
        parms.md_string = ""
        parms.images = []
        parms.tables = []
        parms.graphics = []
        parms.words = []
        parms.line_rects = []
        parms.accept_invisible = (
            page_is_ocr(page) or ignore_alpha
        )  # accept invisible text

        # determine background color
        parms.bg_color = None if not DETECT_BG_COLOR else get_bg_color(page)

        left, top, right, bottom = margins
        parms.clip = page.rect + (left, top, -right, -bottom)

        # extract external links on page
        parms.links = [l for l in page.get_links() if l["kind"] == pymupdf.LINK_URI]

        # extract annotation rectangles on page
        parms.annot_rects = [a.rect for a in page.annots()]

        # make a TextPage for all later extractions
        parms.textpage = page.get_textpage(flags=textflags, clip=parms.clip)

        # extract images on page
        if not IGNORE_IMAGES:
            img_info = page.get_image_info()
        else:
            img_info = []
        for i in range(len(img_info)):
            img_info[i]["bbox"] = pymupdf.Rect(img_info[i]["bbox"])

        # filter out images that are too small or outside the clip
        img_info = [
            i
            for i in img_info
            if i["bbox"].width >= image_size_limit * parms.clip.width
            and i["bbox"].height >= image_size_limit * parms.clip.height
            and i["bbox"].intersects(parms.clip)
            and i["bbox"].width > 3
            and i["bbox"].height > 3
        ]

        # sort descending by image area size
        img_info.sort(key=lambda i: abs(i["bbox"]), reverse=True)

        # subset of images truly inside the clip
        if img_info:
            img_max_size = abs(parms.clip) * 0.9
            sane = [i for i in img_info if abs(i["bbox"] & parms.clip) < img_max_size]
            if len(sane) < len(img_info):  # found some
                img_info = sane  # use those images instead
                # output full page image
                name = save_image(parms, parms.clip, "full")
                if name:
                    parms.md_string += GRAPHICS_TEXT % name

        img_info = img_info[:30]  # only accept the largest up to 30 images
        # run from back to front (= small to large)
        for i in range(len(img_info) - 1, 0, -1):
            r = img_info[i]["bbox"]
            if r.is_empty:
                del img_info[i]
                continue
            for j in range(i):  # image areas larger than r
                if r in img_info[j]["bbox"]:
                    del img_info[i]  # contained in some larger image
                    break
        parms.images = img_info

        parms.img_rects = [i["bbox"] for i in parms.images]

        # catch too-many-graphics situation
        graphics_count = len([b for b in page.get_bboxlog() if "path" in b[0]])
        if GRAPHICS_LIMIT and graphics_count > GRAPHICS_LIMIT:
            IGNORE_GRAPHICS = True

        # Locate all tables on page
        parms.written_tables = []  # stores already written tables
        omitted_table_rects = []
        parms.tabs = []
        if IGNORE_GRAPHICS or not table_strategy:
            # do not try to extract tables
            pass
        else:
            tabs = page.find_tables(clip=parms.clip, strategy=table_strategy)
            for t in tabs.tables:
                # remove tables with too few rows or columns
                if t.row_count < 2 or t.col_count < 2:
                    omitted_table_rects.append(pymupdf.Rect(t.bbox))
                    continue
                parms.tabs.append(t)
            parms.tabs.sort(key=lambda t: (t.bbox[0], t.bbox[1]))

        # Make a list of table boundary boxes.
        # Must include the header bbox (which may exist outside tab.bbox)
        tab_rects = {}
        for i, t in enumerate(parms.tabs):
            tab_rects[i] = pymupdf.Rect(t.bbox) | pymupdf.Rect(t.header.bbox)
            tab_dict = {
                "bbox": tuple(tab_rects[i]),
                "rows": t.row_count,
                "columns": t.col_count,
            }
            parms.tables.append(tab_dict)
        parms.tab_rects = tab_rects
        # list of table rectangles
        parms.tab_rects0 = list(tab_rects.values())

        # Select paths not intersecting any table.
        # Ignore full page graphics.
        # Ignore fill paths having the background color.
        if not IGNORE_GRAPHICS:
            paths = [
                p
                for p in page.get_drawings()
                if p["rect"] in parms.clip
                and p["rect"].width < parms.clip.width
                and p["rect"].height < parms.clip.height
                and (p["rect"].width > 3 or p["rect"].height > 3)
                and not (p["type"] == "f" and p["fill"] == parms.bg_color)
                and not intersects_rects(p["rect"], parms.tab_rects0)
                and not intersects_rects(p["rect"], parms.annot_rects)
            ]
        else:
            paths = []
        # catch too-many-graphics situation
        if GRAPHICS_LIMIT and len(paths) > GRAPHICS_LIMIT:
            paths = []

        # We also ignore vector graphics that only represent
        # "text emphasizing sugar".
        vg_clusters0 = []  # worthwhile vector graphics go here

        # walk through all vector graphics outside any table
        clusters = page.cluster_drawings(drawings=paths)
        for bbox in clusters:
            if is_significant(bbox, paths):
                vg_clusters0.append(bbox)

        # remove paths that are not in some relevant graphic
        parms.actual_paths = [p for p in paths if is_in_rects(p["rect"], vg_clusters0)]

        # also add image rectangles to the list and vice versa
        vg_clusters0.extend(parms.img_rects)
        parms.img_rects.extend(vg_clusters0)
        parms.img_rects = sorted(set(parms.img_rects), key=lambda r: (r.y1, r.x0))
        parms.written_images = []
        # these may no longer be pairwise disjoint:
        # remove area overlaps by joining into larger rects
        parms.vg_clusters0 = refine_boxes(vg_clusters0)

        parms.vg_clusters = dict((i, r) for i, r in enumerate(parms.vg_clusters0))
        # identify text bboxes on page, avoiding tables, images and graphics
        text_rects = column_boxes(
            parms.page,
            paths=parms.actual_paths,
            no_image_text=not force_text,
            textpage=parms.textpage,
            avoid=parms.tab_rects0 + parms.vg_clusters0,
            footer_margin=margins[3],
            header_margin=margins[1],
            ignore_images=IGNORE_IMAGES,
        )

        """
        ------------------------------------------------------------------
        Extract markdown text iterating over text rectangles.
        We also output any tables. They may live above, below or inside
        the text rectangles.
        ------------------------------------------------------------------
        """
        for text_rect in text_rects:
            # output tables above this rectangle
            parms.md_string += output_tables(parms, text_rect)
            parms.md_string += output_images(parms, text_rect, force_text)

            # output text inside this rectangle
            parms.md_string += write_text(
                parms,
                text_rect,
                force_text=force_text,
                images=True,
                tables=True,
            )

        parms.md_string = parms.md_string.replace(" ,", ",").replace("-\n", "")

        # write any remaining tables and images
        parms.md_string += output_tables(parms, None)
        parms.md_string += output_images(parms, None, force_text)

        while parms.md_string.startswith("\n"):
            parms.md_string = parms.md_string[1:]
        parms.md_string = parms.md_string.replace(chr(0), chr(0xFFFD))

        if EXTRACT_WORDS is True:
            # output words in sequence compliant with Markdown text
            rawwords = parms.textpage.extractWORDS()
            rawwords.sort(key=lambda w: (w[3], w[0]))

            words = []
            for lrect in parms.line_rects:
                lwords = []
                for w in rawwords:
                    wrect = pymupdf.Rect(w[:4])
                    if wrect in lrect:
                        lwords.append(w)
                words.extend(sort_words(lwords))

            # remove word duplicates without spoiling the sequence
            # duplicates may occur for multiple reasons
            nwords = []  # words w/o duplicates
            for w in words:
                if w not in nwords:
                    nwords.append(w)
            words = nwords

        else:
            words = []
        parms.words = words
        if page_separators:
            # add page separators to output
            parms.md_string += f"\n\n--- end of page={parms.page.number} ---\n\n"
        return parms

    if page_chunks is False:
        document_output = ""
    else:
        document_output = []

    # read the Table of Contents
    toc = doc.get_toc()

    # Text extraction flags:
    # omit clipped text, collect styles, use accurate bounding boxes
    textflags = (
        0
        | mupdf.FZ_STEXT_CLIP
        | mupdf.FZ_STEXT_ACCURATE_BBOXES
        # | mupdf.FZ_STEXT_IGNORE_ACTUALTEXT
        | 32768  # mupdf.FZ_STEXT_COLLECT_STYLES
    )
    # optionally replace 0xFFFD by glyph number
    if use_glyphs:
        textflags |= mupdf.FZ_STEXT_USE_GID_FOR_UNKNOWN_UNICODE

    for pno in pages:
        parms = get_page_output(
            doc, pno, margins, textflags, FILENAME, IGNORE_IMAGES, IGNORE_GRAPHICS
        )
        if page_chunks is False:
            document_output += parms.md_string
        else:
            # build subet of TOC for this page
            page_tocs = [t for t in toc if t[-1] == pno + 1]

            metadata = get_metadata(doc, pno)
            document_output.append(
                {
                    "metadata": metadata,
                    "toc_items": page_tocs,
                    "tables": parms.tables,
                    "images": parms.images,
                    "graphics": parms.graphics,
                    "text": parms.md_string,
                    "words": parms.words,
                }
            )
        del parms

    return document_output


def _parse_pages_arg(pages_arg: str, page_count: int) -> list:
    """Parse a pages string like '2-5,8,N' into 0-based page numbers.

    "N" may be used to reference the last page.
    """
    if not pages_arg:
        return None
    out = set()
    parts = pages_arg.split(",")
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if "-" in p:
            a, b = p.split("-", 1)
            a = a.strip()
            b = b.strip()
            if a.upper() == "N":
                start = page_count
            else:
                start = int(a)
            if b.upper() == "N":
                end = page_count
            else:
                end = int(b)
            # pages are specified 1-based, convert to 0-based
            for i in range(min(start, end) - 1, max(start, end)):
                if 0 <= i < page_count:
                    out.add(i)
        else:
            if p.upper() == "N":
                idx = page_count - 1
            else:
                idx = int(p) - 1
            if 0 <= idx < page_count:
                out.add(idx)
    return sorted(out)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Convert PDF to GitHub-friendly Markdown")
    parser.add_argument("input", help="input PDF filename")
    parser.add_argument("-o", "--output", help="output markdown filename (defaults to input.md)")
    parser.add_argument("-p", "--pages", help="pages to include, e.g. '1-3,5,N' where N is last page")
    parser.add_argument("--no-images", dest="images", action="store_false", help="do not write or embed images")
    parser.add_argument("--embed-images", dest="embed_images", action="store_true", help="embed images as base64 data URIs")
    parser.add_argument("--dpi", type=int, default=150, help="dpi for rendering images (default: 150)")
    args = parser.parse_args()

    doc = pymupdf.open(args.input)
    try:
        page_count = doc.page_count
    except Exception:
        page_count = None

    pages = None
    if args.pages:
        if page_count is None:
            # open to get page count
            with pymupdf.open(args.input) as tmpdoc:
                page_count = tmpdoc.page_count
        pages = _parse_pages_arg(args.pages, page_count)

    output = args.output if args.output else os.path.splitext(args.input)[0] + ".md"

    md = to_markdown(
        args.input,
        pages=pages,
        write_images=args.images and not args.embed_images,
        embed_images=args.embed_images,
        dpi=args.dpi,
    )

    # md may be list (page_chunks=True) or string; ensure string
    if isinstance(md, list):
        text = "\n\n".join([p.get("text", "") for p in md])
    else:
        text = md

    with open(output, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Wrote: {output}")


if __name__ == "__main__":
    main()
