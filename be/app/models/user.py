"""Model người dùng — đăng nhập bằng email, mật khẩu lưu dạng hash bcrypt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.document import Document
    from app.models.role import Role


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Hash bcrypt (~60 ký tự) — sinh qua app.core.security.hash_password, không hash trong model.
    # Nullable: tài khoản đăng nhập bằng Google không có mật khẩu.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Nguồn đăng nhập: "local" (email + mật khẩu) hoặc "google".
    auth_provider: Mapped[str] = mapped_column(
        String(20), server_default=text("'local'"), nullable=False
    )
    # Định danh ổn định của tài khoản Google (claim "sub" trong ID token).
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    # Ảnh đại diện (lấy từ Google khi đăng nhập bằng Google).
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )

    role: Mapped[Role] = relationship(back_populates="users")
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    # Tài liệu admin tải lên — giữ lại (uploaded_by SET NULL) nếu user bị xóa.
    documents: Mapped[list[Document]] = relationship(back_populates="uploader")
