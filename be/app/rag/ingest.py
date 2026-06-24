"""Đếm token cho pipeline RAG (hàm thuần — tách để unit-test không cần OpenAI/Weaviate)."""

from __future__ import annotations

import tiktoken

# Bộ mã hoá của các model embedding OpenAI hiện tại (text-embedding-3-*).
_TOKEN_ENCODING = "cl100k_base"


def count_tokens(text: str) -> int:
    """Đếm token theo bộ mã hoá embedding; fallback đếm từ nếu tiktoken lỗi."""
    try:
        encoding = tiktoken.get_encoding(_TOKEN_ENCODING)
    except Exception:  # noqa: BLE001 — chỉ là số liệu phụ trợ
        return len(text.split())
    return len(encoding.encode(text))
