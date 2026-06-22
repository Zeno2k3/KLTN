"""Truy vấn tổng hợp cho thống kê admin (đếm theo khoảng thời gian) — async, portable.

Chỉ dùng COUNT/aggregate cơ bản (không ``date_trunc``) để chạy được cả PostgreSQL
(thật) lẫn SQLite (test). Việc chia bucket biểu đồ làm ở tầng service bằng Python.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import MessageSender
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.role import Role
from app.models.user import User


async def count_active_parents(db: AsyncSession, start: datetime, end: datetime) -> int:
    """Số phụ huynh (role=``user``) có ÍT NHẤT một tin nhắn ``user`` trong [start, end)."""
    stmt = (
        select(func.count(distinct(Conversation.user_id)))
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(User, Conversation.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .where(
            Message.sender_type == MessageSender.user,
            Message.created_at >= start,
            Message.created_at < end,
            Role.name == "user",
        )
    )
    return int(await db.scalar(stmt) or 0)


async def count_conversations(db: AsyncSession, start: datetime, end: datetime) -> int:
    """Số hội thoại được tạo trong [start, end)."""
    stmt = (
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.created_at >= start, Conversation.created_at < end)
    )
    return int(await db.scalar(stmt) or 0)


async def count_answered(db: AsyncSession, start: datetime, end: datetime) -> int:
    """Số câu trả lời của trợ lý (message ``assistant``) trong [start, end)."""
    stmt = (
        select(func.count())
        .select_from(Message)
        .where(
            Message.sender_type == MessageSender.assistant,
            Message.created_at >= start,
            Message.created_at < end,
        )
    )
    return int(await db.scalar(stmt) or 0)


async def total_documents(db: AsyncSession) -> int:
    """Tổng số tài liệu trong kho tri thức (toàn thời gian)."""
    return int(await db.scalar(select(func.count()).select_from(Document)) or 0)


async def conversation_timestamps(
    db: AsyncSession, start: datetime, end: datetime
) -> list[datetime]:
    """Mốc ``created_at`` của các hội thoại trong [start, end) — để service chia bucket."""
    result = await db.scalars(
        select(Conversation.created_at).where(
            Conversation.created_at >= start, Conversation.created_at < end
        )
    )
    return list(result.all())
