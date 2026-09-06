from backend.core.chunking import Block, ChunkType, chunk_document, hash_chunk_text


def test_table_is_never_split_across_chunks():
    table_text = (
        "Locus  Frequency  N  p-value\n"
        "COL1A1  0.42  120  0.001\n"
        "MC1R  0.18  95  0.03\n"
        "TYR  0.09  110  0.21\n"
    )
    blocks = [
        Block(text="Some intro text about the study.", section="Introduction", block_type=ChunkType.TEXT, page_number=1),
        Block(text=table_text, section="Results", block_type=ChunkType.TABLE, page_number=2),
        Block(text="Figure 1. Allele frequency distribution across sampled loci.", section="Results", block_type=ChunkType.CAPTION, page_number=2),
        Block(text="Further discussion of the results follows in this section.", section="Discussion", block_type=ChunkType.TEXT, page_number=3),
    ]

    chunks = chunk_document(doc_id="doc1", blocks=blocks, target_tokens=50, overlap_tokens=5, hard_cap_tokens=1024)

    table_chunks = [c for c in chunks if c.chunk_type == ChunkType.TABLE]
    assert len(table_chunks) == 1
    assert table_chunks[0].text.count("\n") == table_text.count("\n")  # all rows present, untouched
    for row in ["COL1A1", "MC1R", "TYR"]:
        assert row in table_chunks[0].text


def test_caption_kept_atomic():
    blocks = [
        Block(text="Figure 1. Allele frequency distribution across sampled loci.", section="Results", block_type=ChunkType.CAPTION, page_number=2),
    ]
    chunks = chunk_document(doc_id="doc1", blocks=blocks, target_tokens=50, overlap_tokens=5, hard_cap_tokens=1024)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == ChunkType.CAPTION


def test_references_section_excluded():
    blocks = [
        Block(text="Body text here.", section="Introduction", block_type=ChunkType.TEXT, page_number=1),
        Block(text="Smith et al. 2020. Some Journal.", section="References", block_type=ChunkType.TEXT, page_number=5),
    ]
    chunks = chunk_document(doc_id="doc1", blocks=blocks)
    assert all(c.section.lower() != "references" for c in chunks)
    assert len(chunks) == 1


def test_long_text_section_split_with_overlap():
    long_text = " ".join([f"word{i}" for i in range(1000)])
    blocks = [Block(text=long_text, section="Methods", block_type=ChunkType.TEXT, page_number=1)]
    chunks = chunk_document(doc_id="doc1", blocks=blocks, target_tokens=200, overlap_tokens=20, hard_cap_tokens=1024)

    text_chunks = [c for c in chunks if c.chunk_type == ChunkType.TEXT]
    assert len(text_chunks) > 1
    # Overlap: the tail of chunk N should share words with the head of chunk N+1.
    tail_words = set(text_chunks[0].text.split()[-10:])
    head_words = set(text_chunks[1].text.split()[:30])
    assert tail_words & head_words


def test_hard_cap_truncates_oversized_table():
    huge_table = "\n".join(f"row{i}  val{i}  val{i}  val{i}" for i in range(2000))
    blocks = [Block(text=huge_table, section="Results", block_type=ChunkType.TABLE, page_number=1)]
    chunks = chunk_document(doc_id="doc1", blocks=blocks, hard_cap_tokens=100)
    assert chunks[0].truncated is True
    assert "[TRUNCATED]" in chunks[0].text


def test_content_hash_stable_for_identical_normalized_text():
    h1 = hash_chunk_text("Hello   World")
    h2 = hash_chunk_text("hello world")
    assert h1 == h2

    h3 = hash_chunk_text("A different chunk entirely")
    assert h1 != h3


def test_document_reading_order_preserved():
    blocks = [
        Block(text="Intro paragraph 1.", section="Introduction", block_type=ChunkType.TEXT, page_number=1),
        Block(text="Table 1. Fossil occurrences.", section="Introduction", block_type=ChunkType.TABLE, page_number=1),
        Block(text="Intro paragraph 2.", section="Introduction", block_type=ChunkType.TEXT, page_number=1),
        Block(text="Figure 1. Stratigraphic column.", section="Methods", block_type=ChunkType.CAPTION, page_number=2),
        Block(text="Methods paragraph 1.", section="Methods", block_type=ChunkType.TEXT, page_number=2),
    ]
    chunks = chunk_document(doc_id="doc_order", blocks=blocks)
    assert len(chunks) == 5
    assert chunks[0].text == "Intro paragraph 1."
    assert chunks[0].chunk_type == ChunkType.TEXT
    assert chunks[1].text == "Table 1. Fossil occurrences."
    assert chunks[1].chunk_type == ChunkType.TABLE
    assert chunks[2].text == "Intro paragraph 2."
    assert chunks[2].chunk_type == ChunkType.TEXT
    assert chunks[3].text == "Figure 1. Stratigraphic column."
    assert chunks[3].chunk_type == ChunkType.CAPTION
    assert chunks[4].text == "Methods paragraph 1."
    assert chunks[4].chunk_type == ChunkType.TEXT
