"""Truy vấn dữ liệu người dùng (data access) — không chứa business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email).options(selectinload(User.role))
    return await db.scalar(stmt)


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id).options(selectinload(User.role))
    return await db.scalar(stmt)


async def get_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    stmt = (
        select(User)
        .where(User.google_sub == google_sub)
        .options(selectinload(User.role))
    )
    return await db.scalar(stmt)


async def create(db: AsyncSession, user: User) -> User:
    """Thêm user mới và flush để lấy id (chưa commit — do get_db quản lý commit)."""
    db.add(user)
    await db.flush()
    await db.refresh(user, attribute_names=["role"])
    return user
