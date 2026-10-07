from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

CHUNK_SIZE = 500

_BLANK_LINE = re.compile(r"\n\s*\n")


@dataclass
class Chunk:
    """A slice of one page's text, small enough to pass to an LLM or index."""

    page: int
    start: int
    end: int
    text: str


def extract_pages(pdf_path: str | Path) -> list[str]:
    """Return each page's text, in order. Page 1 is index 0."""
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Find paragraph-sized units in page text, as (start, end) offsets.

    Prefers blank-line-separated paragraphs. Some PDFs (including our synthetic
    samples) hard-wrap every visual line with a single newline and never use a
    blank line, so when none is found we fall back to one unit per line. Either
    way a unit is never split internally, so a chunk built from these spans
    never breaks a line or paragraph in half.
    """
    if _BLANK_LINE.search(text):
        spans = []
        pos = 0
        for part in _BLANK_LINE.split(text):
            start = text.index(part, pos)
            end = start + len(part)
            spans.append((start, end))
            pos = end
        return spans

    spans = []
    pos = 0
    for line in text.split("\n"):
        end = pos + len(line)
        spans.append((pos, end))
        pos = end + 1  # skip the newline between lines
    return spans


def chunk_pages(pages: list[str], chunk_size: int = CHUNK_SIZE) -> list[Chunk]:
    """Group each page's text into ~chunk_size character chunks on paragraph boundaries."""
    chunks: list[Chunk] = []
    for page_number, text in enumerate(pages, start=1):
        current_start: int | None = None
        current_end: int | None = None
        for start, end in _paragraph_spans(text):
            if start == end:
                continue  # empty paragraph/line, e.g. a blank line or trailing newline
            if current_start is None:
                current_start, current_end = start, end
            elif end - current_start <= chunk_size:
                current_end = end
            else:
                chunks.append(Chunk(page_number, current_start, current_end, text[current_start:current_end]))
                current_start, current_end = start, end
        if current_start is not None:
            chunks.append(Chunk(page_number, current_start, current_end, text[current_start:current_end]))
    return chunks
