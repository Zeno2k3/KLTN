"""Model tài liệu PDF (kho tri thức RAG) và bản đồ chunk → Weaviate Cloud."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, DocumentStatus, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)  # bytes
    mime_type: Mapped[str | None] = mapped_column(
        String(128), server_default=text("'application/pdf'")
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        server_default=text("'processing'"),
        index=True,
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    # Metadata cấp văn bản (auto-extract từ header — xem app/rag/doc_metadata.py).
    doc_type: Mapped[str | None] = mapped_column(
        String(50)
    )  # ke_hoach|quyet_dinh|thong_tu|khac
    issued_date: Mapped[str | None] = mapped_column(
        String(50)
    )  # giữ dạng chuỗi (định dạng đa dạng)
    issuing_body: Mapped[str | None] = mapped_column(String(255))
    # Lọc truy xuất — parse từ TÊN FILE (xem app/rag/title_metadata.py). Địa bàn cấp phường/xã,
    # giữ nguyên (không quy về quận/huyện). Cũng đẩy vào node.metadata để Weaviate lọc.
    school_year: Mapped[str | None] = mapped_column(String(20))  # "2026-2027"
    ward: Mapped[str | None] = mapped_column(String(120))  # phường/xã/đặc khu

    uploader: Mapped[User | None] = relationship(back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentChunk.chunk_index",
    )


class DocumentChunk(CreatedAtMixin, Base):
    """Một đoạn (chunk) của tài liệu. Vector embedding nằm ở Weaviate Cloud;
    bảng này chỉ giữ text + ``weaviate_uuid`` để đồng bộ/xóa và truy vết trích dẫn."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # nội dung GỐC (không kèm context)
    weaviate_uuid: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), unique=True
    )
    token_count: Mapped[int | None] = mapped_column(Integer)
    # Metadata cấu trúc (structure-aware chunking). ``heading_path`` lưu JSON list breadcrumb;
    # ``context`` là đoạn Contextual Retrieval đã prepend vào vector (lưu riêng để trích dẫn sạch).
    heading_path: Mapped[str | None] = mapped_column(
        Text
    )  # JSON: ["A...", "Mục III", "Điều 1"]
    context: Mapped[str | None] = mapped_column(Text)
    chunk_type: Mapped[str | None] = mapped_column(String(20))  # text|table|list|mixed
    has_table: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    page_number: Mapped[int | None] = mapped_column(Integer)
    # Lưới bảng thô {"grid": [[ô...]]} cho chunk has_table — phục vụ render/QA/đối chiếu. Chỉ ở
    # Postgres, KHÔNG đẩy lên Weaviate. ``sa.JSON`` portable (Postgres JSON + SQLite TEXT cho test).
    table_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_doc_idx"
        ),
    )
