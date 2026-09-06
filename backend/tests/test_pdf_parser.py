import fitz
import pytest

from backend.core.chunking import ChunkType
from backend.utils.pdf_parser import parse_pdf


@pytest.fixture
def synthetic_pdf(tmp_path):
    path = tmp_path / "synthetic.pdf"
    doc = fitz.open()
    page = doc.new_page()

    y = 72
    page.insert_text((72, y), "Introduction", fontsize=16, fontname="helv")
    y += 20
    page.insert_text((72, y), "This paper investigates ancient DNA recovered from permafrost.", fontsize=10)
    y += 16
    page.insert_text((72, y), "Samples were collected across multiple Siberian excavation sites.", fontsize=10)
    y += 16
    page.insert_text((72, y), "Extraction protocols followed established ancient DNA lab standards.", fontsize=10)
    y += 40
    page.insert_text((72, y), "Results", fontsize=16, fontname="helv")
    y += 20
    page.insert_text((72, y), "Sequencing yielded high coverage across the mitochondrial genome.", fontsize=10)
    y += 16
    page.insert_text((72, y), "Figure 1. Sample locations across the Siberian permafrost sites.", fontsize=9)

    doc.save(str(path))
    doc.close()
    return str(path)


def test_parse_pdf_detects_sections_and_caption(synthetic_pdf):
    blocks = parse_pdf(synthetic_pdf)

    sections = {b.section for b in blocks}
    assert "Introduction" in sections
    assert "Results" in sections

    caption_blocks = [b for b in blocks if b.block_type == ChunkType.CAPTION]
    assert len(caption_blocks) == 1
    assert "Figure 1" in caption_blocks[0].text
