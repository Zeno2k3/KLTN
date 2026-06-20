"""Model tin nhắn — của người dùng hoặc của chatbot (assistant)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, MessageSender

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.evaluation import MessageEvaluation
    from app.models.feedback import MessageFeedback


class Message(CreatedAtMixin, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_type: Mapped[MessageSender] = mapped_column(
        Enum(
            MessageSender,
            name="message_sender",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Nguồn RAG trích dẫn: [{document_id, chunk_id, weaviate_uuid, snippet, score}].
    # JSONB trên Postgres; biến thể JSON cho SQLite (test) — DDL Postgres không đổi.
    context_sources: Mapped[list[dict] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite")
    )
    # Id trace để đối chiếu với Arize Phoenix (OpenTelemetry).
    trace_id: Mapped[str | None] = mapped_column(String(255))

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    feedback: Mapped[MessageFeedback | None] = relationship(
        back_populates="message", cascade="all, delete-orphan", passive_deletes=True
    )
    evaluations: Mapped[list[MessageEvaluation]] = relationship(
        back_populates="message", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index(
            "ix_messages_conversation_id_created_at",
            "conversation_id",
            "created_at",
        ),
    )
