"""Tổng hợp số liệu thống kê admin: tính cửa sổ thời gian, % thay đổi, chia bucket biểu đồ.

Mọi truy vấn đếm nằm ở ``statistics_repository``; service chỉ lo logic thời gian/định dạng.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import statistics_repository as repo
from app.schemas.statistics import (
    ChartBucket,
    Metric,
    StatRange,
    StatsResponse,
    TopicStat,
)

# Độ dài mỗi kỳ theo lựa chọn mốc thời gian.
_RANGE_DELTA: dict[StatRange, timedelta] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}
_BUCKETS = 6
_TOPIC_LABEL = "Tư vấn tuyển sinh tiểu học"


def _delta_pct(current: int, previous: int) -> float | None:
    """% thay đổi so với kỳ trước; None nếu kỳ trước = 0 (không có mốc để so)."""
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _as_utc(ts: datetime) -> datetime:
    """Chuẩn hoá về aware-UTC (DB SQLite trong test có thể trả naive)."""
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def _bucketize(
    timestamps: list[datetime], start: datetime, span: timedelta, intraday: bool
) -> list[ChartBucket]:
    """Chia [start, start+span) thành ``_BUCKETS`` khoảng đều, đếm timestamps vào từng khoảng."""
    step = span / _BUCKETS
    counts = [0] * _BUCKETS
    for raw in timestamps:
        idx = int((_as_utc(raw) - start) / step)
        idx = min(
            max(idx, 0), _BUCKETS - 1
        )  # kẹp về [0, _BUCKETS-1] kể cả đúng biên phải
        counts[idx] += 1
    fmt = "%H:%M" if intraday else "%d/%m"
    return [
        ChartBucket(label=(start + step * i).strftime(fmt), count=counts[i])
        for i in range(_BUCKETS)
    ]


async def build_stats(db: AsyncSession, range_: StatRange) -> StatsResponse:
    """Dựng toàn bộ số liệu cho tab Thống kê theo mốc thời gian ``range_``."""
    span = _RANGE_DELTA[range_]
    now = datetime.now(UTC)
    cur_start = now - span
    prev_start = now - 2 * span

    # Kỳ hiện tại
    parents_cur = await repo.count_active_parents(db, cur_start, now)
    convs_cur = await repo.count_conversations(db, cur_start, now)
    answered_cur = await repo.count_answered(db, cur_start, now)
    # Kỳ liền trước (cùng độ dài) — để tính % thay đổi
    parents_prev = await repo.count_active_parents(db, prev_start, cur_start)
    convs_prev = await repo.count_conversations(db, prev_start, cur_start)
    answered_prev = await repo.count_answered(db, prev_start, cur_start)

    total_docs = await repo.total_documents(db)
    timestamps = await repo.conversation_timestamps(db, cur_start, now)

    return StatsResponse(
        range=range_,
        active_parents=Metric(
            value=parents_cur, delta_pct=_delta_pct(parents_cur, parents_prev)
        ),
        conversations=Metric(
            value=convs_cur, delta_pct=_delta_pct(convs_cur, convs_prev)
        ),
        answered_questions=Metric(
            value=answered_cur, delta_pct=_delta_pct(answered_cur, answered_prev)
        ),
        total_documents=total_docs,
        chart=_bucketize(timestamps, cur_start, span, intraday=range_ == "24h"),
        topic=TopicStat(label=_TOPIC_LABEL, count=convs_cur),
    )
