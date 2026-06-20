"""Trích xuất & chia chunk PDF (hàm thuần, chạy local — không gọi mạng).

Tách khỏi ``vector_store`` để dễ unit-test phần chunking/đếm token mà không cần
OpenAI/Weaviate. Tầng service ráp các hàm này lại trong tiến trình nền.
"""

from __future__ import annotations

import logging

import tiktoken
from llama_index.core import Document as LIDocument
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from pypdf import PdfReader

from app.core.config import settings

logger = logging.getLogger(__name__)

# Bộ mã hoá của các model embedding OpenAI hiện tại (text-embedding-3-*).
_TOKEN_ENCODING = "cl100k_base"


def extract_pdf_text(path: str) -> tuple[str, int]:
    """Đọc PDF → (toàn văn nối theo trang, số trang). Không log nội dung (có thể chứa PII)."""
    reader = PdfReader(path)
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(pages).strip()
    return text, len(reader.pages)


def count_tokens(text: str) -> int:
    """Đếm token theo bộ mã hoá embedding; fallback đếm từ nếu tiktoken lỗi."""
    try:
        encoding = tiktoken.get_encoding(_TOKEN_ENCODING)
    except Exception:  # noqa: BLE001 — chỉ là số liệu phụ trợ
        return len(text.split())
    return len(encoding.encode(text))


def chunk_to_nodes(text: str, document_id: int) -> list[TextNode]:
    """Chia văn bản thành node theo câu (chunk_size/overlap từ config).

    Gắn metadata ``document_id`` vào mỗi node để truy vết/lọc khi truy hồi."""
    splitter = SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    doc = LIDocument(text=text, metadata={"document_id": document_id})
    return splitter.get_nodes_from_documents([doc])
