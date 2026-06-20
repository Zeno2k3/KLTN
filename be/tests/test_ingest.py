"""Test các hàm thuần của pipeline ingest (không gọi mạng): trích xuất PDF, chunk, đếm token."""

import io

from pypdf import PdfWriter

from app.rag import ingest


def _blank_pdf_bytes(pages: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_extract_pdf_text_returns_page_count(tmp_path):
    path = tmp_path / "blank.pdf"
    path.write_bytes(_blank_pdf_bytes(pages=3))
    text, page_count = ingest.extract_pdf_text(str(path))
    assert page_count == 3
    # Trang trắng → không có text; hàm vẫn trả chuỗi (rỗng), không lỗi.
    assert isinstance(text, str)


def test_count_tokens_positive():
    assert ingest.count_tokens("xin chào thế giới") >= 1
    assert ingest.count_tokens("") == 0


def test_chunk_to_nodes_splits_and_tags_document_id():
    # Văn bản đủ dài để chắc chắn vượt 1 chunk (chunk_size mặc định 512 token).
    text = " ".join(f"Đây là câu số {i} trong tài liệu tuyển sinh." for i in range(800))
    nodes = ingest.chunk_to_nodes(text, document_id=42)
    assert len(nodes) >= 2
    assert all(n.metadata.get("document_id") == 42 for n in nodes)
    assert all(n.text.strip() for n in nodes)
