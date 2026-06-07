"""测试 pdf_extractor 模块"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_extract_text_fallback_empty(tmp_path):
    """pdf_extractor 对不存在的 PDF 抛出 FileNotFoundError"""
    from data_pipeline.pdf_extractor import extract_text
    nonexistent = tmp_path / "nonexistent.pdf"
    try:
        extract_text(nonexistent)
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        pass


def test_extract_text_pymupdf_fallback(tmp_path):
    """pdf_extractor 在无 PDF-Extract-Kit 时用 PyMuPDF 降级"""
    from data_pipeline.pdf_extractor import extract_text, FITZ_AVAILABLE
    if not FITZ_AVAILABLE:
        return
    import fitz
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World MDA Section", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()
    text = extract_text(pdf_path, use_cache=False)
    assert "Hello World" in text


def test_cache_roundtrip(tmp_path):
    """pdf_extractor 缓存写入和读取正常"""
    from data_pipeline.pdf_extractor import _save_cache, _load_cache
    pdf_path = tmp_path / "test_cache.pdf"
    _save_cache(pdf_path, "test content")
    cached = _load_cache(pdf_path)
    assert cached == "test content"
