from pathlib import Path

from pipeline.ingest import chunk_pages, extract_pages

SAMPLE_PDF = Path(__file__).resolve().parents[2] / "packs" / "mortgage" / "samples" / "m-001.pdf"


def test_extract_pages_returns_text_per_page():
    pages = extract_pages(SAMPLE_PDF)
    assert len(pages) >= 2
    assert "Fernmoor Building Society" in pages[0]
    assert "Mortgage Offer and Illustration" in pages[0]


def test_chunk_pages_respects_blank_line_paragraph_boundaries():
    page = "First paragraph, one sentence.\n\nSecond paragraph here.\n\nThird paragraph."

    chunks = chunk_pages([page], chunk_size=1000)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.page == 1
    assert page[chunk.start : chunk.end] == chunk.text


def test_chunk_pages_splits_at_chunk_size_without_breaking_a_paragraph():
    paragraphs = [f"Paragraph number {i} with some filler words to pad it out a bit." for i in range(10)]
    page = "\n\n".join(paragraphs)

    chunks = chunk_pages([page], chunk_size=200)

    assert len(chunks) > 1
    for chunk in chunks:
        assert page[chunk.start : chunk.end] == chunk.text  # exact, contiguous slice of the page

    # concatenating the chunks' paragraphs in order recovers every paragraph exactly once
    reconstructed = [p for chunk in chunks for p in chunk.text.split("\n\n") if p]
    assert reconstructed == paragraphs


def test_chunk_pages_falls_back_to_line_boundaries_without_blank_lines():
    pages = extract_pages(SAMPLE_PDF)  # real PDFs hard-wrap with single newlines, no blank lines

    chunks = chunk_pages(pages, chunk_size=500)

    assert len(chunks) > 1
    assert any(chunk.page == 2 for chunk in chunks)
    for chunk in chunks:
        page_text = pages[chunk.page - 1]
        assert page_text[chunk.start : chunk.end] == chunk.text
        assert not chunk.text.startswith("\n")  # never starts mid-line


def test_chunk_pages_tracks_page_number_per_chunk():
    chunks = chunk_pages(["Page one text.", "Page two text."], chunk_size=500)

    assert [chunk.page for chunk in chunks] == [1, 2]
