"""Pydantic schema cho tài liệu PDF — response của các endpoint /admin/documents."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import DocumentStatus


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
    created_at: datetime
