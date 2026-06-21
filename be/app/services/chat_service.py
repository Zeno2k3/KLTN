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

from app.core.config import settings
from app.models.base import MessageSender
from app.rag import query_engine
from app.repositories import conversation_repository, document_repository
from app.schemas.chat import (
    ConversationDetail,
    ConversationSummary,
    DocumentChunkOut,
    DocumentDetailOut,
    MessageOut,
)

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

    # Lấy lịch sử hội thoại (sliding window) TRƯỚC khi lưu câu hỏi mới — để câu hiện tại KHÔNG
    # lọt vào ngữ cảnh router/rewriter. Hội thoại vừa tạo chưa có message → rỗng.
    prior = await conversation_repository.list_messages(db, conversation.id)
    history = [
        {"role": message.sender_type.value, "content": message.content}
        for message in prior
    ][-settings.chat_history_window :]

    # Lưu câu hỏi của người dùng trước.
    await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        sender_type=MessageSender.user,
        content=question,
    )

    # Chạy pipeline RAG (chặn → thread) kèm timeout: vượt ngưỡng → 503 thân thiện thay vì
    # treo vô hạn. Lưu ý: wait_for hủy phần CHỜ, thread nền vẫn chạy nốt (không hủy được
    # thread) — chấp nhận được vì chỉ là không trả về cho client.
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(query_engine.answer_question, question, history=history),
            timeout=settings.rag_timeout_seconds,
        )
    except TimeoutError:
        logger.warning(
            "RAG timeout sau %.0fs (user_id=%s) — trả 503.",
            settings.rag_timeout_seconds,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hệ thống đang xử lý lâu hơn dự kiến, vui lòng thử lại sau giây lát.",
        ) from None

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


async def get_document_detail(db: AsyncSession, document_id: int) -> DocumentDetailOut:
    """Tài liệu + toàn bộ đoạn text (cho bảng trích dẫn khi bấm chip nguồn).

    Chỉ đọc dữ liệu đã lưu (không truy vấn vector). 404 nếu tài liệu không tồn tại. Tài liệu
    chưa có chunk (đang xử lý / đã xoá vector) trả ``chunks: []`` để UI hiện trạng thái rỗng."""
    document = await document_repository.get_with_chunks(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu."
        )
    return DocumentDetailOut(
        id=document.id,
        filename=document.filename,
        page_count=document.page_count,
        chunk_count=len(document.chunks),
        chunks=[
            DocumentChunkOut(
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                weaviate_uuid=str(chunk.weaviate_uuid) if chunk.weaviate_uuid else None,
            )
            for chunk in document.chunks
        ],
    )


async def _owned_or_404(db: AsyncSession, *, user_id: int, conversation_id: int):
    """Lấy hội thoại nếu thuộc về ``user_id``, ngược lại raise 404."""
    conversation = await conversation_repository.get_by_id(db, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hội thoại."
        )
    return conversation


async def rename_conversation(
    db: AsyncSession, *, user_id: int, conversation_id: int, title: str
) -> ConversationSummary:
    """Đổi tên một hội thoại của người dùng; 404 nếu không thuộc về họ."""
    title = (title or "").strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tên không được rỗng."
        )
    conversation = await _owned_or_404(
        db, user_id=user_id, conversation_id=conversation_id
    )
    await conversation_repository.update_title(db, conversation, title[:_TITLE_MAX])
    await db.commit()

    latest = await conversation_repository.latest_message_map(db, [conversation.id])
    last = latest.get(conversation.id)
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        updated_at=conversation.updated_at,
        last_message=last.content[:_SNIPPET_MAX] if last else None,
    )


async def delete_conversation(
    db: AsyncSession, *, user_id: int, conversation_id: int
) -> None:
    """Xóa một hội thoại của người dùng; 404 nếu không thuộc về họ."""
    conversation = await _owned_or_404(
        db, user_id=user_id, conversation_id=conversation_id
    )
    await conversation_repository.delete(db, conversation)
    await db.commit()
