"""Pydantic schema cho thống kê admin — response của GET /admin/stats."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# Mốc thời gian tổng hợp số liệu (mặc định 30 ngày).
StatRange = Literal["24h", "7d", "30d"]


class Metric(BaseModel):
    """Chỉ số đếm trong kỳ + % thay đổi so với kỳ liền trước (None nếu kỳ trước = 0)."""

    value: int
    delta_pct: float | None = None


class ChartBucket(BaseModel):
    """Một cột biểu đồ: nhãn mốc thời gian + số lượt trò chuyện trong khoảng."""

    label: str
    count: int


class TopicStat(BaseModel):
    """Khối chủ đề tư vấn (hệ thống chỉ có 1 chủ đề: tuyển sinh tiểu học)."""

    label: str
    count: int


class StatsResponse(BaseModel):
    """Tổng hợp số liệu cho tab Thống kê admin."""

    range: StatRange
    active_parents: Metric
    conversations: Metric
    answered_questions: Metric
    total_documents: int
    chart: list[ChartBucket]
    topic: TopicStat
