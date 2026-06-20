"""Truy vấn dữ liệu hội thoại + tin nhắn (data access) — không chứa business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import MessageSender
from app.models.conversation import Conversation
from app.models.message import Message


async def get_by_id(db: AsyncSession, conversation_id: int) -> Conversation | None:
    return await db.get(Conversation, conversation_id)


async def create(
    db: AsyncSession, *, user_id: int, title: str | None = None
) -> Conversation:
    """Tạo hội thoại mới (chưa commit — tầng trên quản lý). Flush để lấy id."""
    conversation = Conversation(user_id=user_id)
    if title:
        conversation.title = title
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


async def add_message(
    db: AsyncSession,
    *,
    conversation_id: int,
    sender_type: MessageSender,
    content: str,
    context_sources: list[dict] | None = None,
    trace_id: str | None = None,
) -> Message:
    """Thêm 1 tin nhắn (user hoặc assistant) vào hội thoại. Flush, KHÔNG commit."""
    message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        content=content,
        context_sources=context_sources,
        trace_id=trace_id,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def list_messages(db: AsyncSession, conversation_id: int) -> list[Message]:
    """Các tin nhắn của hội thoại, cũ → mới."""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    result = await db.scalars(stmt)
    return list(result.all())


async def list_by_user(db: AsyncSession, user_id: int) -> list[Conversation]:
    """Hội thoại của một người dùng, mới cập nhật nhất trước (cho sidebar)."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.scalars(stmt)
    return list(result.all())


async def latest_message_map(
    db: AsyncSession, conversation_ids: list[int]
) -> dict[int, Message]:
    """Tin nhắn MỚI NHẤT của mỗi hội thoại (để hiện snippet ở sidebar, tránh N+1)."""
    if not conversation_ids:
        return {}
    stmt = (
        select(Message)
        .where(Message.conversation_id.in_(conversation_ids))
        .order_by(Message.conversation_id, Message.created_at, Message.id)
    )
    result = await db.scalars(stmt)
    latest: dict[int, Message] = {}
    for message in result.all():
        # Đã sort created_at tăng dần → gán sau cùng = tin mới nhất của hội thoại.
        latest[message.conversation_id] = message
    return latest
