"""Truy vấn dữ liệu tài liệu PDF + chunk (data access) — không chứa business logic."""

from __future__ import annotations

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk


async def list_all(db: AsyncSession) -> list[Document]:
    """Danh sách tài liệu, mới nhất trước."""
    stmt = select(Document).order_by(Document.created_at.desc())
    result = await db.scalars(stmt)
    return list(result.all())


async def get_by_id(db: AsyncSession, document_id: int) -> Document | None:
    return await db.get(Document, document_id)


async def create(db: AsyncSession, document: Document) -> Document:
    """Thêm tài liệu và flush để lấy id (chưa commit — do tầng trên quản lý)."""
    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


async def add_chunks(db: AsyncSession, chunks: list[DocumentChunk]) -> None:
    db.add_all(chunks)
    await db.flush()


async def get_chunk_uuids(db: AsyncSession, document_id: int) -> list[str]:
    """UUID Weaviate của các chunk thuộc tài liệu — để xoá vector tương ứng."""
    stmt = select(DocumentChunk.weaviate_uuid).where(
        DocumentChunk.document_id == document_id,
        DocumentChunk.weaviate_uuid.is_not(None),
    )
    result = await db.scalars(stmt)
    return [str(u) for u in result.all()]


async def delete(db: AsyncSession, document: Document) -> None:
    """Xoá tài liệu + chunk con. Xoá chunk TƯỜNG MINH (không phụ thuộc FK cascade —
    SQLite trong test không bật foreign_keys, sẽ để lại chunk mồ côi nếu chỉ dựa cascade)."""
    await db.execute(
        sa_delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )
    await db.delete(document)
    await db.flush()


async def list_file_paths(db: AsyncSession) -> list[str]:
    """Đường dẫn file của mọi tài liệu — để xoá file đĩa khi 'xoá tất cả'."""
    result = await db.scalars(select(Document.file_path))
    return list(result.all())


async def delete_all(db: AsyncSession) -> int:
    """Xoá mọi tài liệu + chunk. Xoá chunk trước (không phụ thuộc FK cascade của SQLite
    trong test). Trả về số tài liệu đã xoá."""
    await db.execute(sa_delete(DocumentChunk))
    result = await db.execute(sa_delete(Document))
    await db.flush()
    return result.rowcount or 0
