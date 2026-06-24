"""Test app/rag/doc_metadata.py trên markdown LlamaParse (offline, KHÔNG gọi LLM)."""

from app.rag import doc_metadata
from app.rag.parse import ParsedPage


def _page(md):
    return ParsedPage(page_number=1, md=md, blocks=[])


def test_extract_regex_on_markdown(monkeypatch):
    monkeypatch.setattr(doc_metadata.settings, "chunk_llm_enabled", False)
    md = (
        "# CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
        "ỦY BAN NHÂN DÂN PHƯỜNG BÌNH THẠNH\n"
        "# QUYẾT ĐỊNH\n"
        "Số: 123/QĐ-UBND\n"
        "ngày 5 tháng 6 năm 2026\n"
    )
    meta = doc_metadata.extract_doc_metadata([_page(md)], "qd.pdf")
    assert meta["doc_type"] == "quyet_dinh"
    assert meta["issued_date"] == "05/06/2026"
    assert "ỦY BAN NHÂN DÂN" in (meta["issuing_body"] or "")
    assert meta["doc_name"] == "Số 123/QĐ-UBND"


def test_extract_falls_back_doc_name_to_filename(monkeypatch):
    monkeypatch.setattr(doc_metadata.settings, "chunk_llm_enabled", False)
    meta = doc_metadata.extract_doc_metadata([_page("nội dung không có số")], "kh.pdf")
    assert meta["doc_type"] == "khac"
    assert meta["doc_name"] == "kh.pdf"


def test_strip_md_markers():
    assert doc_metadata._strip_md_markers("# Tiêu đề") == "Tiêu đề"
    assert doc_metadata._strip_md_markers("### Mục 3") == "Mục 3"
    assert doc_metadata._strip_md_markers("**đậm**") == "đậm"
