"""Dựng ``MetadataFilters`` (school_year + ward) TỪ CÂU HỎI người dùng để lọc truy xuất.

Chạy trong span ``rag.answer`` (``query_engine.answer_question``), SAU bước rewrite (dùng câu đã
condense). CHỈ thêm điều kiện EQ cho slot trích được; không slot nào → trả ``None`` (không lọc → giữ
recall). Lỗi parse → ``None`` (không bao giờ làm vỡ pipeline). Có fallback-on-empty ở query_engine
nếu filter ra 0 kết quả (tránh "biến mất" tài liệu do over-filter / object Weaviate cũ thiếu property).

Nguồn slot: ``school_year`` qua ``title_metadata.parse_year``; ``ward`` qua
``wards_data.find_ward_in_text`` (whitelist substring, tránh false-positive 'xã hội').
"""

from __future__ import annotations

import logging

from llama_index.core.vector_stores.types import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)

from app.rag.title_metadata import parse_year
from app.rag.wards_data import find_ward_in_text

logger = logging.getLogger(__name__)


def extract_filters(query_text: str | None) -> MetadataFilters | None:
    """Trả ``MetadataFilters`` (AND) cho slot trích được từ câu hỏi, hoặc ``None`` nếu không có slot."""
    try:
        year = parse_year(query_text)
        ward = find_ward_in_text(query_text)
    except Exception:  # noqa: BLE001 — trích filter KHÔNG được phép làm vỡ pipeline
        logger.warning("extract_filters lỗi — bỏ lọc cho câu hỏi này.")
        return None

    filters: list[MetadataFilter] = []
    if year:
        filters.append(
            MetadataFilter(key="school_year", value=year, operator=FilterOperator.EQ)
        )
    if ward:
        filters.append(
            MetadataFilter(key="ward", value=ward, operator=FilterOperator.EQ)
        )
    if not filters:
        return None
    return MetadataFilters(filters=filters, condition=FilterCondition.AND)
