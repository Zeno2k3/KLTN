"""Test hàm thuần đếm token của pipeline ingest (không gọi mạng)."""

from app.rag import ingest


def test_count_tokens_positive():
    assert ingest.count_tokens("xin chào thế giới") >= 1
    assert ingest.count_tokens("") == 0
