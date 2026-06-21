"""Pydantic schema cho endpoint hỏi-đáp RAG ``/chat``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Yêu cầu hỏi: câu hỏi + (tuỳ chọn) id hội thoại để nối tiếp."""

    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None


class RenameConversationRequest(BaseModel):
    """Yêu cầu đổi tên hội thoại."""

    title: str = Field(min_length=1, max_length=255)


class SourceOut(BaseModel):
    """Một nguồn trích dẫn (chunk tài liệu) đã dùng để trả lời."""

    index: int | None = None
    document_id: int | None = None
    filename: str | None = None
    weaviate_uuid: str | None = None
    snippet: str | None = None
    score: float | None = None


class AskResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: list[SourceOut] = []


class ConversationSummary(BaseModel):
    """Mục hội thoại ở sidebar (nhẹ — KHÔNG kèm toàn bộ tin nhắn)."""

    id: int
    title: str
    updated_at: datetime
    last_message: str | None = None


class MessageOut(BaseModel):
    """Một tin nhắn khi đọc lại lịch sử (cột ``context_sources`` → ``sources``)."""

    id: int
    sender_type: str
    content: str
    sources: list[SourceOut] = []
    created_at: datetime


class ConversationDetail(BaseModel):
    """Một hội thoại + toàn bộ tin nhắn (khi mở từ sidebar)."""

    id: int
    title: str
    messages: list[MessageOut] = []


class DocumentChunkOut(BaseModel):
    """Một đoạn (chunk) text của tài liệu — để hiển thị trong bảng trích dẫn."""

    chunk_index: int
    content: str
    weaviate_uuid: str | None = None


class DocumentDetailOut(BaseModel):
    """Tài liệu + toàn bộ đoạn text (mở khi bấm chip nguồn). Chỉ đọc, không kèm vector."""

    id: int
    filename: str
    page_count: int | None = None
    chunk_count: int
    chunks: list[DocumentChunkOut] = []
