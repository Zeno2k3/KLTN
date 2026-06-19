"""Kết nối Redis (async) — dùng để blacklist token khi đăng xuất.

Khi đăng xuất hoặc xoay vòng refresh token, ta lưu ``jti`` của token vào Redis
với TTL bằng thời gian còn lại tới khi token hết hạn; key tự biến mất sau đó.

Suy giảm mượt: nếu Redis không sẵn sàng, app vẫn chạy được — blacklist tạm vô
hiệu (token vẫn hết hạn theo TTL), chỉ ghi cảnh báo. Khi có Redis, blacklist
hoạt động đầy đủ.
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

_BLACKLIST_PREFIX = "bl:"

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    """Khởi tạo client Redis — gọi trong lifespan lúc startup."""
    global _redis
    if _redis is not None:
        return
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
    except RedisError as exc:
        await client.aclose()
        _redis = None
        logger.warning(
            "Không kết nối được Redis (%s) — blacklist token tạm vô hiệu.", exc
        )
        return
    _redis = client
    logger.info("Đã kết nối Redis: %s", settings.redis_url)


async def close_redis() -> None:
    """Đóng kết nối Redis — gọi trong lifespan lúc shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def blacklist_jti(jti: str, ttl_seconds: int) -> None:
    """Đưa ``jti`` vào blacklist trong ``ttl_seconds`` giây (no-op nếu Redis tắt)."""
    if not jti or ttl_seconds <= 0 or _redis is None:
        return
    try:
        await _redis.set(f"{_BLACKLIST_PREFIX}{jti}", "1", ex=ttl_seconds)
    except RedisError as exc:
        logger.warning("Lỗi ghi blacklist token: %s", exc)


async def is_blacklisted(jti: str) -> bool:
    """Kiểm tra ``jti`` có bị blacklist hay không (False nếu Redis tắt)."""
    if not jti or _redis is None:
        return False
    try:
        return bool(await _redis.exists(f"{_BLACKLIST_PREFIX}{jti}"))
    except RedisError:
        return False
