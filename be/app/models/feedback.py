"""Model đánh giá: theo từng tin nhắn và theo cả cuộc hội thoại (1:1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.message import Message


class MessageFeedback(CreatedAtMixin, Base):
    """Like/dislike + nhận xét cho một tin nhắn (mỗi tin nhắn tối đa 1 feedback)."""

    __tablename__ = "message_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 = like, -1 = dislike
    comment: Mapped[str | None] = mapped_column(Text)

    message: Mapped[Message] = relationship(back_populates="feedback")

    __table_args__ = (
        CheckConstraint("rating IN (-1, 1)", name="ck_message_feedbacks_rating"),
    )


class ConversationFeedback(CreatedAtMixin, Base):
    """Đánh giá sao (1..5) + nhận xét cho cả cuộc hội thoại."""

    __tablename__ = "conversation_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1..5 sao
    comment: Mapped[str | None] = mapped_column(Text)

    conversation: Mapped[Conversation] = relationship(back_populates="feedback")

    __table_args__ = (
        CheckConstraint(
            "rating BETWEEN 1 AND 5", name="ck_conversation_feedbacks_rating"
        ),
    )
