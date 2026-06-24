"""Pydantic schema cho tài liệu PDF — response của các endpoint /admin/documents."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import DocumentStatus


class DocumentRenameRequest(BaseModel):
    """Đổi tên hiển thị của tài liệu (không đổi file trên đĩa)."""

    filename: str = Field(min_length=1, max_length=512)


class DocumentResponse(BaseModel):
    """Thông tin tài liệu trả về cho admin (map trực tiếp từ ORM ``Document``)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_size: int | None = None
    status: DocumentStatus
    page_count: int | None = None
    chunk_count: int
    error_message: str | None = None
    # Metadata lọc (parse từ tên file) — hiển thị cho admin.
    school_year: str | None = None
    ward: str | None = None
    created_at: datetime
