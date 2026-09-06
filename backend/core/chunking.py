"""
Structure-aware chunking for scientific PDFs.

Per the implementation plan: chunk by detected section first, then split
further only within a section if it exceeds the token target. Tables and
figure captions are kept atomic (never split mid-row / mid-caption) up to a
hard cap, beyond which they're truncated with a marker.

This module has NO external dependencies (no network, no DB, no model calls)
so it is fully unit-testable in any environment.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    CAPTION = "caption"


@dataclass
class Block:
    """A parsed unit of document content, produced by pdf_parser.py, prior to
    chunking. Kept intentionally simple/serializable so pdf_parser.py can be
    swapped or mocked without touching chunking logic."""

    text: str
    section: str
    block_type: ChunkType = ChunkType.TEXT
    page_number: int = 0


@dataclass
class Chunk:
    doc_id: str
    chunk_index: int
    section: str
    chunk_type: ChunkType
    page_number: int
    text: str
    truncated: bool = False
    content_hash: str = field(default="")

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hash_chunk_text(self.text)


def hash_chunk_text(text: str) -> str:
    """Normalize (lowercase, whitespace-collapsed) and hash for dedup."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _approx_token_count(text: str) -> int:
    """Cheap token approximation (whitespace split) to avoid a hard tokenizer
    dependency in this module. The real pipeline may swap in a tiktoken/
    HF tokenizer count without changing the chunking algorithm's shape."""
    return max(1, len(text.split()))


def _split_text_with_overlap(text: str, target_tokens: int, overlap_tokens: int) -> list[str]:
    words = text.split()
    if len(words) <= target_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    step = max(1, target_tokens - overlap_tokens)
    while start < len(words):
        end = min(start + target_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks


def chunk_document(
    doc_id: str,
    blocks: list[Block],
    target_tokens: int = 512,
    overlap_tokens: int = 50,
    hard_cap_tokens: int = 1024,
    excluded_sections: tuple[str, ...] = ("references", "bibliography"),
) -> list[Chunk]:
    """
    Build the final chunk list for a document from its parsed blocks.

    Rules (per spec):
    - Tables and captions are never split mid-block, even if they exceed the
      token target — but they ARE truncated at hard_cap_tokens with a marker.
    - Plain text blocks are split by section, then recursively within a
      section if the section exceeds target_tokens, with overlap.
    - Reference/bibliography sections are excluded entirely.
    """
    chunks: list[Chunk] = []
    chunk_index = 0

    current_section = None
    current_text_blocks: list[Block] = []

    def flush_text_blocks():
        nonlocal chunk_index
        if not current_text_blocks:
            return
        full_text = "\n".join(b.text for b in current_text_blocks)
        page_number = current_text_blocks[0].page_number
        sec = current_text_blocks[0].section
        pieces = _split_text_with_overlap(full_text, target_tokens, overlap_tokens)
        for piece in pieces:
            token_count = _approx_token_count(piece)
            truncated = False
            text = piece
            if token_count > hard_cap_tokens:
                words = text.split()
                text = " ".join(words[:hard_cap_tokens]) + " [TRUNCATED]"
                truncated = True
            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    section=sec,
                    chunk_type=ChunkType.TEXT,
                    page_number=page_number,
                    text=text,
                    truncated=truncated,
                )
            )
            chunk_index += 1
        current_text_blocks.clear()

    for block in blocks:
        if block.section.strip().lower() in excluded_sections:
            continue

        if current_section != block.section:
            flush_text_blocks()
            current_section = block.section

        if block.block_type in (ChunkType.TABLE, ChunkType.CAPTION):
            flush_text_blocks()
            token_count = _approx_token_count(block.text)
            truncated = False
            text = block.text
            if token_count > hard_cap_tokens:
                words = text.split()
                text = " ".join(words[:hard_cap_tokens]) + " [TRUNCATED]"
                truncated = True
            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    section=block.section,
                    chunk_type=block.block_type,
                    page_number=block.page_number,
                    text=text,
                    truncated=truncated,
                )
            )
            chunk_index += 1
        else:
            current_text_blocks.append(block)

    flush_text_blocks()
    return chunks
