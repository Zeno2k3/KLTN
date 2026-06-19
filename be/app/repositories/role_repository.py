"""Truy vấn dữ liệu vai trò (role)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role


async def get_by_name(db: AsyncSession, name: str) -> Role | None:
    return await db.scalar(select(Role).where(Role.name == name))
