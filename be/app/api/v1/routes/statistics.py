"""Endpoint thống kê tổng quan cho admin (chỉ admin).

Trả số liệu hoạt động theo mốc thời gian chọn (24h / 7 ngày / 30 ngày): phụ huynh
hoạt động, lượt trò chuyện, câu hỏi đã giải đáp, tổng tài liệu, biểu đồ cột + chủ đề.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.statistics import StatRange, StatsResponse
from app.services import statistics_service

router = APIRouter(prefix="/admin/stats", tags=["statistics"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    range: StatRange = "30d",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> StatsResponse:
    return await statistics_service.build_stats(db, range)
