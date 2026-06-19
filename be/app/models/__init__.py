"""Tập hợp toàn bộ ORM model.

Import mọi model tại đây để ``Base.metadata`` thấy đủ bảng khi Alembic autogenerate
(alembic/env.py chỉ cần ``import app.models``).
"""

from app.core.database import Base
from app.models.base import (
    CreatedAtMixin,
    DocumentStatus,
    MessageSender,
    TimestampMixin,
)
from app.models.conversation import Conversation
from app.models.document import Document, DocumentChunk
from app.models.evaluation import MessageEvaluation
from app.models.feedback import ConversationFeedback, MessageFeedback
from app.models.message import Message
from app.models.role import Role
from app.models.user import User

__all__ = [
    "Base",
    "CreatedAtMixin",
    "TimestampMixin",
    "MessageSender",
    "DocumentStatus",
    "Role",
    "User",
    "Conversation",
    "Message",
    "MessageFeedback",
    "ConversationFeedback",
    "Document",
    "DocumentChunk",
    "MessageEvaluation",
]
