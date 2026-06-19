"""Mixin và kiểu enum dùng chung cho toàn bộ ORM model."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class CreatedAtMixin:
    """Thêm cột ``created_at`` (timestamptz) tự gán thời điểm tạo bản ghi."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TimestampMixin(CreatedAtMixin):
    """Thêm cả ``created_at`` và ``updated_at`` (tự cập nhật mỗi lần sửa)."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MessageSender(enum.StrEnum):
    """Vai trò người gửi của một tin nhắn."""

    user = "user"
    assistant = "assistant"


class DocumentStatus(enum.StrEnum):
    """Trạng thái xử lý của một tài liệu PDF."""

    processing = "processing"
    ready = "ready"
    failed = "failed"
