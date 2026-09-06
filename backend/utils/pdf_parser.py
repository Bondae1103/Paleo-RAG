"""
PDF parsing with layout awareness, using PyMuPDF (fitz).

Detects section headers via font size/boldness heuristics (not just regex
matching on common header strings, since journal templates vary widely),
and separately flags table-like blocks and figure captions so chunking.py
can keep them atomic.

Heuristics used (documented for whoever tunes this later):
- A text span is a candidate SECTION HEADER if its font size is
  meaningfully larger than the page's median body-text font size, OR it is
  bold AND short (<= 8 words) AND does not end in a period.
- A block is a candidate CAPTION if it starts with one of the standard
  scientific figure/table prefixes ("Figure", "Fig.", "Table", "Supplementary
  Table") — this one substring heuristic is intentionally kept simple, since
  caption prefixes are far more standardized across journals than section
  header styling is.
- A block is a candidate TABLE if PyMuPDF's block bbox has a high ratio of
  short lines with consistent multi-column spacing (many tab/whitespace-
  separated tokens per line). This is a heuristic, not a true table
  detector — for higher accuracy, swap in `pymupdf`'s `find_tables()` API
  (available in recent PyMuPDF versions) as a follow-up improvement.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from backend.core.chunking import Block, ChunkType

CAPTION_PREFIXES = ("figure", "fig.", "table", "supplementary table", "supplementary figure")


@dataclass
class _Span:
    text: str
    size: float
    bold: bool
    page_number: int


def _extract_spans(doc) -> list[_Span]:
    spans: list[_Span] = []
    for page_index, page in enumerate(doc):
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    font_flags = span.get("flags", 0)
                    is_bold = bool(font_flags & 2**4)  # bit 4 = bold, per PyMuPDF docs
                    spans.append(
                        _Span(text=text, size=span.get("size", 0.0), bold=is_bold, page_number=page_index)
                    )
    return spans


def _body_font_size(values: list[float]) -> float:
    """Estimate the body-text font size as the most frequent size (mode),
    weighted by how many spans use it — this is far more robust than a
    median/mean when a document has only a couple of large-font headers
    among many body-text spans (or, as in small synthetic test fixtures,
    only a handful of spans total where a median gets skewed by headers)."""
    if not values:
        return 0.0
    rounded = [round(v, 1) for v in values]
    counts: dict[float, int] = {}
    for v in rounded:
        counts[v] = counts.get(v, 0) + 1
    # Prefer the most frequent size; on ties, prefer the smaller size (body
    # text is smaller than headers).
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _looks_like_table_line(line: str) -> bool:
    # Heuristic: 3+ whitespace-separated numeric/short tokens is a strong
    # table-row signal (e.g. "Locus  Frequency  N  p-value").
    tokens = re.split(r"\s{2,}|\t", line.strip())
    tokens = [t for t in tokens if t]
    return len(tokens) >= 3


def parse_jats_xml(path: str) -> list[Block]:
    """Parse JATS XML (from PMC OA) into Block objects."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(path)
    root = tree.getroot()
    blocks: list[Block] = []

    abstract = root.find(".//abstract")
    if abstract is not None:
        abs_text = " ".join("".join(p.itertext()).strip() for p in abstract.findall(".//p"))
        if not abs_text:
            abs_text = "".join(abstract.itertext()).strip()
        if abs_text:
            blocks.append(Block(text=abs_text, section="Abstract", block_type=ChunkType.TEXT, page_number=1))

    for sec in root.findall(".//body//sec"):
        sec_title_el = sec.find("title")
        sec_title = "".join(sec_title_el.itertext()).strip() if sec_title_el is not None else "Main"

        for child in sec:
            tag = child.tag.lower()
            if tag == "title":
                continue
            if tag in ("table-wrap", "table"):
                tbl_text = "".join(child.itertext()).strip()
                if tbl_text:
                    blocks.append(Block(text=tbl_text, section=sec_title, block_type=ChunkType.TABLE, page_number=1))
            elif tag in ("fig", "figure"):
                caption_el = child.find(".//caption")
                caption_text = "".join(caption_el.itertext()).strip() if caption_el is not None else "".join(child.itertext()).strip()
                if caption_text:
                    blocks.append(Block(text=caption_text, section=sec_title, block_type=ChunkType.CAPTION, page_number=1))
            elif tag == "p":
                p_text = "".join(child.itertext()).strip()
                if p_text:
                    blocks.append(Block(text=p_text, section=sec_title, block_type=ChunkType.TEXT, page_number=1))

    if not blocks:
        body = root.find(".//body")
        if body is not None:
            for child in body:
                tag = child.tag.lower()
                if tag in ("table-wrap", "table"):
                    tbl_text = "".join(child.itertext()).strip()
                    if tbl_text:
                        blocks.append(Block(text=tbl_text, section="Body", block_type=ChunkType.TABLE, page_number=1))
                elif tag in ("fig", "figure"):
                    cap_text = "".join(child.itertext()).strip()
                    if cap_text:
                        blocks.append(Block(text=cap_text, section="Body", block_type=ChunkType.CAPTION, page_number=1))
                elif tag == "p":
                    p_text = "".join(child.itertext()).strip()
                    if p_text:
                        blocks.append(Block(text=p_text, section="Body", block_type=ChunkType.TEXT, page_number=1))

    return blocks


def parse_pdf(path: str) -> list[Block]:
    """Parse a PDF or JATS XML file at `path` into a flat list of Block objects,
    tagged by section and block type, in document order."""
    if str(path).lower().endswith(".xml"):
        return parse_jats_xml(path)

    import fitz  # PyMuPDF; imported lazily so this module can be imported
    # in environments/tests that don't need real PDF I/O.

    doc = fitz.open(path)
    spans = _extract_spans(doc)
    body_font_size = _body_font_size([s.size for s in spans]) or 10.0

    blocks: list[Block] = []
    current_section = "Unclassified"
    buffer_lines: list[str] = []
    buffer_page = 0
    buffer_type = ChunkType.TEXT

    def flush_buffer():
        nonlocal buffer_lines, buffer_type
        if not buffer_lines:
            return
        text = "\n".join(buffer_lines).strip()
        if not text:
            buffer_lines = []
            return
        if buffer_type == ChunkType.CAPTION:
            blocks.append(Block(text=text, section=current_section, block_type=ChunkType.CAPTION, page_number=buffer_page))
        elif sum(_looks_like_table_line(l) for l in buffer_lines) >= max(2, len(buffer_lines) // 2):
            blocks.append(Block(text=text, section=current_section, block_type=ChunkType.TABLE, page_number=buffer_page))
        else:
            blocks.append(Block(text=text, section=current_section, block_type=ChunkType.TEXT, page_number=buffer_page))
        buffer_lines = []
        buffer_type = ChunkType.TEXT

    for span in spans:
        is_header = (span.size >= body_font_size * 1.25) or (
            span.bold and len(span.text.split()) <= 8 and not span.text.endswith(".")
        )
        if is_header and len(span.text) < 80:
            flush_buffer()
            current_section = span.text.strip()
            buffer_page = span.page_number
            continue

        is_caption_start = span.text.strip().lower().startswith(CAPTION_PREFIXES)
        if is_caption_start:
            # A new caption always starts its own block — flush whatever
            # (non-caption) text was being accumulated first.
            flush_buffer()
            buffer_type = ChunkType.CAPTION
            buffer_lines.append(span.text)
            buffer_page = span.page_number
            continue

        if buffer_type == ChunkType.CAPTION:
            # A caption block ends as soon as a non-caption-prefixed span
            # follows it (real captions are typically short, single-line).
            flush_buffer()

        buffer_lines.append(span.text)
        buffer_page = span.page_number

    flush_buffer()
    doc.close()
    return blocks
