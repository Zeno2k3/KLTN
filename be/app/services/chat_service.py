"""Business logic hỏi-đáp RAG: điều phối retrieve→rerank→LLM rồi lưu hội thoại + tin nhắn.

Pipeline RAG (``query_engine.answer_question``) đồng bộ & chặn (LlamaIndex + model rerank local)
→ gọi qua ``asyncio.to_thread`` để không kẹt event loop. Lưu CẢ tin người dùng lẫn tin assistant
(kèm ``context_sources`` + ``trace_id``) rồi commit. Đọc lịch sử qua ``list_conversations`` /
``get_conversation`` (đều kiểm quyền sở hữu).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import MessageSender
from app.rag import query_engine
from app.repositories import conversation_repository
from app.schemas.chat import ConversationDetail, ConversationSummary, MessageOut

logger = logging.getLogger(__name__)

_TITLE_MAX = 60
_SNIPPET_MAX = 120


@dataclass
class AskOutcome:
    conversation_id: int
    answer: str
    sources: list[dict] = field(default_factory=list)


async def ask(
    db: AsyncSession,
    *,
    user_id: int,
    question: str,
    conversation_id: int | None = None,
) -> AskOutcome:
    """Trả lời câu hỏi của ``user_id`` và lưu vào hội thoại (tạo mới nếu chưa có)."""
    question = (question or "").strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Câu hỏi không được rỗng."
        )

    # Lấy/tạo hội thoại; nếu truyền id thì PHẢI thuộc về chính người dùng.
    if conversation_id is None:
        conversation = await conversation_repository.create(
            db, user_id=user_id, title=question[:_TITLE_MAX]
        )
    else:
        conversation = await conversation_repository.get_by_id(db, conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy hội thoại.",
            )

    # Lưu câu hỏi của người dùng trước.
    await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        sender_type=MessageSender.user,
        content=question,
    )

    # Chạy pipeline RAG (chặn → thread).
    result = await asyncio.to_thread(query_engine.answer_question, question)

    # Lưu câu trả lời assistant + nguồn trích dẫn + trace id.
    await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        sender_type=MessageSender.assistant,
        content=result.answer,
        context_sources=result.sources or None,
        trace_id=result.trace_id,
    )
    await db.commit()

    return AskOutcome(
        conversation_id=conversation.id,
        answer=result.answer,
        sources=result.sources,
    )


async def list_conversations(
    db: AsyncSession, *, user_id: int
) -> list[ConversationSummary]:
    """Danh sách hội thoại của người dùng + snippet tin nhắn cuối (cho sidebar)."""
    conversations = await conversation_repository.list_by_user(db, user_id)
    latest = await conversation_repository.latest_message_map(
        db, [c.id for c in conversations]
    )
    summaries: list[ConversationSummary] = []
    for conversation in conversations:
        last = latest.get(conversation.id)
        summaries.append(
            ConversationSummary(
                id=conversation.id,
                title=conversation.title,
                updated_at=conversation.updated_at,
                last_message=last.content[:_SNIPPET_MAX] if last else None,
            )
        )
    return summaries


async def get_conversation(
    db: AsyncSession, *, user_id: int, conversation_id: int
) -> ConversationDetail:
    """Một hội thoại + tin nhắn; 404 nếu không tồn tại hoặc không thuộc người dùng."""
    conversation = await conversation_repository.get_by_id(db, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hội thoại."
        )
    messages = await conversation_repository.list_messages(db, conversation_id)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        messages=[
            MessageOut(
                id=message.id,
                sender_type=message.sender_type,
                content=message.content,
                sources=message.context_sources or [],
                created_at=message.created_at,
            )
            for message in messages
        ],
    )
