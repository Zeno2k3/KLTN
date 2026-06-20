"""Endpoint hỏi-đáp RAG (người dùng đã đăng nhập): gửi câu hỏi → nhận câu trả lời + trích dẫn,
và đọc lại lịch sử hội thoại (sidebar).

Pipeline: hybrid retrieve (BM25+vector, RRF) → cross-encoder rerank → LLM tổng hợp. Câu hỏi và
câu trả lời được lưu vào hội thoại của người dùng; các endpoint đọc đều kiểm quyền sở hữu.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import (
    AskRequest,
    AskResponse,
    ConversationDetail,
    ConversationSummary,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AskResponse:
    outcome = await chat_service.ask(
        db,
        user_id=current_user.id,
        question=payload.question,
        conversation_id=payload.conversation_id,
    )
    return AskResponse(
        conversation_id=outcome.conversation_id,
        answer=outcome.answer,
        sources=outcome.sources,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationSummary]:
    """Danh sách hội thoại của người dùng hiện tại (mới nhất trước)."""
    return await chat_service.list_conversations(db, user_id=current_user.id)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationDetail,
)
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetail:
    """Toàn bộ tin nhắn của một hội thoại (404 nếu không thuộc người dùng)."""
    return await chat_service.get_conversation(
        db, user_id=current_user.id, conversation_id=conversation_id
    )
