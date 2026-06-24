"""Test dựng MetadataFilters từ CÂU HỎI (app/rag/query_filters.py)."""

from __future__ import annotations

from llama_index.core.vector_stores.types import FilterCondition, FilterOperator

from app.rag.query_filters import extract_filters


def _as_dict(filters) -> dict:
    return {f.key: f.value for f in filters.filters}


def test_extract_both_slots():
    f = extract_filters("hồ sơ tuyển sinh phường Bình Thạnh năm học 2026-2027 cần gì?")
    assert f is not None
    assert _as_dict(f) == {"ward": "Bình Thạnh", "school_year": "2026-2027"}
    assert f.condition == FilterCondition.AND
    assert all(mf.operator == FilterOperator.EQ for mf in f.filters)


def test_extract_ward_only():
    f = extract_filters("tuyển sinh ở phường Tân Bình thế nào?")
    assert _as_dict(f) == {"ward": "Tân Bình"}


def test_extract_year_only():
    f = extract_filters("kế hoạch tuyển sinh năm học 2026 2027 ra sao?")
    assert _as_dict(f) == {"school_year": "2026-2027"}


def test_extract_none_when_no_slot():
    assert extract_filters("hồ sơ lớp 1 cần những gì?") is None
    assert extract_filters(None) is None
