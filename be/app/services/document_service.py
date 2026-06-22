"""Business logic tài liệu PDF: lưu upload, nạp (ingest) RAG nền, xoá.

Ingest là tác vụ nền (BackgroundTask) → dùng session ĐỘC LẬP từ ``AsyncSessionLocal``
(session của request đã đóng sau khi trả response). Mọi gọi LlamaIndex/Weaviate (đồng bộ,
có thể nặng/chặn) được bọc ``asyncio.to_thread`` để không chặn event loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid as uuid_lib
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.base import DocumentStatus
from app.models.document import Document, DocumentChunk
from app.rag import chunker, doc_metadata, extract, ocr, vector_store
from app.repositories import document_repository

logger = logging.getLogger(__name__)

# Gốc be/ (…/be/app/services/document_service.py → parents[2] = be/)
_BE_ROOT = Path(__file__).resolve().parents[2]
_PDF_MIME = "application/pdf"
_MAX_ERROR_LEN = 1000


def _upload_root() -> Path:
    root = Path(settings.upload_dir)
    if not root.is_absolute():
        root = _BE_ROOT / root
    root.mkdir(parents=True, exist_ok=True)
    return root


async def save_upload(upload: UploadFile) -> tuple[str, int, str]:
    """Validate (PDF + dung lượng) rồi lưu ra đĩa. Trả (đường_dẫn, kích_thước_byte, tên_gốc)."""
    filename = upload.filename or "tai-lieu.pdf"
    is_pdf = filename.lower().endswith(".pdf") or upload.content_type == _PDF_MIME
    if not is_pdf:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Chỉ chấp nhận tệp PDF.",
        )

    content = await upload.read()
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tệp rỗng.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Tệp vượt quá {settings.max_upload_mb} MB.",
        )

    dest = _upload_root() / f"{uuid_lib.uuid4().hex}.pdf"
    dest.write_bytes(content)
    return str(dest), size, filename


async def create_document(
    db,
    *,
    filename: str,
    file_path: str,
    file_size: int,
    uploaded_by: int | None,
) -> Document:
    """Tạo bản ghi tài liệu trạng thái 'processing' (ingest chạy nền sau đó)."""
    document = Document(
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=_PDF_MIME,
        uploaded_by=uploaded_by,
        status=DocumentStatus.processing,
    )
    document = await document_repository.create(db, document)
    # Commit NGAY: tác vụ ingest nền chạy ở session riêng, chỉ thấy dữ liệu đã commit
    # (nếu để get_db commit lúc teardown thì có thể chạy sau khi ingest đã query → không thấy row).
    await db.commit()
    return document


async def ingest_document(document_id: int) -> None:
    """Tác vụ nền: trích xuất (pdfplumber) → auto-extract metadata → structure-aware + LLM chunk →
    embed → ghi Weaviate → lưu chunk → status=ready.

    Lỗi bất kỳ → status=failed kèm lý do; cố gắng gỡ vector đã ghi để tránh rác."""
    async with AsyncSessionLocal() as db:
        document = await document_repository.get_by_id(db, document_id)
        if document is None:
            logger.warning("ingest: tài liệu %s không tồn tại, bỏ qua.", document_id)
            return
        file_path = document.file_path
        filename = document.filename

    try:
        # 1) Trích xuất text + bảng theo trang (CPU-bound → thread). Đánh dấu trang scan cần OCR.
        ocr_min = settings.ocr_min_chars if settings.ocr_enabled else 0
        pages = await asyncio.to_thread(
            extract.extract_with_tables, file_path, ocr_min
        )

        # 1b) OCR fallback cho trang scan (render + vision-LLM → ghi đè page.text). Có mạng → thread.
        if settings.ocr_enabled and any(p.needs_ocr for p in pages):
            pages = await asyncio.to_thread(ocr.ocr_pages, file_path, pages)

        has_content = any(p.text.strip() for p in pages) or any(p.tables for p in pages)
        if not has_content:
            raise ValueError(
                "Không trích xuất được văn bản từ PDF (kể cả sau khi OCR)."
            )
        page_count = len(pages)

        # 2) Auto-extract metadata cấp văn bản (regex + LLM xác nhận; có mạng → thread).
        doc_meta = await asyncio.to_thread(
            doc_metadata.extract_doc_metadata, pages, filename
        )

        # 3) Structure-aware + LLM chunking (gọi LLM → thread; bọc span Phoenix bên trong).
        chunk_nodes = await asyncio.to_thread(
            chunker.build_nodes, pages, document_id, filename, doc_meta
        )
        if not chunk_nodes:
            raise ValueError("PDF không tạo được chunk nào.")

        # 4) Embed + ghi Weaviate (mạng → thread).
        await asyncio.to_thread(
            vector_store.add_nodes, [cn.node for cn in chunk_nodes]
        )

        # 5) Lưu chunk + metadata + cập nhật trạng thái.
        async with AsyncSessionLocal() as db:
            document = await document_repository.get_by_id(db, document_id)
            if document is None:
                return
            chunks = [
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=cn.content,
                    weaviate_uuid=uuid_lib.UUID(cn.node.node_id),
                    token_count=cn.token_count,
                    heading_path=(
                        json.dumps(cn.heading_path, ensure_ascii=False)
                        if cn.heading_path
                        else None
                    ),
                    context=cn.context or None,
                    chunk_type=cn.chunk_type,
                    has_table=cn.has_table,
                    page_number=cn.page_number,
                )
                for i, cn in enumerate(chunk_nodes)
            ]
            await document_repository.add_chunks(db, chunks)
            document.status = DocumentStatus.ready
            document.page_count = page_count
            document.chunk_count = len(chunks)
            document.doc_type = doc_meta.get("doc_type")
            document.issued_date = doc_meta.get("issued_date")
            document.issuing_body = doc_meta.get("issuing_body")
            document.error_message = None
            await db.commit()
        logger.info(
            "ingest: tài liệu %s xong (%s chunk, %s trang).",
            document_id,
            len(chunk_nodes),
            page_count,
        )
    except Exception as exc:  # noqa: BLE001 — phải bắt mọi lỗi để đánh dấu failed
        logger.exception("ingest: tài liệu %s thất bại.", document_id)
        await _mark_failed(document_id, str(exc))


async def _mark_failed(document_id: int, message: str) -> None:
    async with AsyncSessionLocal() as db:
        document = await document_repository.get_by_id(db, document_id)
        if document is None:
            return
        document.status = DocumentStatus.failed
        document.error_message = message[:_MAX_ERROR_LEN]
        await db.commit()


async def delete_document(db, document_id: int) -> None:
    """Xoá tài liệu: COMMIT bản ghi trước, RỒI gỡ vector Weaviate + xoá file.

    Commit DB trước để nếu commit lỗi thì file/vector còn nguyên (khôi phục được);
    dọn dẹp ngoài là best-effort & idempotent nên chạy sau khi row chắc chắn đã xoá."""
    document = await document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu."
        )

    # Lấy thông tin cần cho dọn dẹp TRƯỚC khi xoá row.
    uuids = await document_repository.get_chunk_uuids(db, document_id)
    file_path = document.file_path

    await document_repository.delete(db, document)
    await db.commit()

    if uuids:
        try:
            await asyncio.to_thread(vector_store.delete_objects, uuids)
        except Exception:  # noqa: BLE001 — Weaviate lỗi không cản; row đã xoá
            logger.exception(
                "Xoá vector Weaviate cho tài liệu %s lỗi — bỏ qua.", document_id
            )
    with contextlib.suppress(FileNotFoundError, OSError):
        Path(file_path).unlink()


async def rename_document(db, document_id: int, filename: str) -> Document:
    """Đổi tên hiển thị tài liệu trong DB (admin list + bảng trích dẫn + tên file tải về).

    KHÔNG đụng vector Weaviate: metadata ``filename`` của chunk đã ingest nằm trong blob
    ``_node_content`` (định dạng nội bộ LlamaIndex) → muốn đổi phải re-ingest. Vì vậy chip
    nguồn ở câu trả lời chat MỚI vẫn hiện tên cũ tới khi re-ingest (hạn chế đã biết)."""
    filename = (filename or "").strip()
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tên không được rỗng."
        )
    document = await document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu."
        )
    document = await document_repository.update_filename(db, document, filename[:512])
    await db.commit()
    return document


async def get_document_file(db, document_id: int) -> tuple[str, str]:
    """Trả (đường_dẫn_tuyệt_đối, tên_file_gốc) để xem/tải; 404 nếu thiếu bản ghi hoặc file."""
    document = await document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu."
        )
    path = Path(document.file_path)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tệp tài liệu không còn trên máy chủ.",
        )
    return str(path), document.filename


async def delete_all_documents(db) -> int:
    """Xoá TẤT CẢ tài liệu: drop collection Weaviate + xoá mọi file + xoá mọi bản ghi.
    Trả về số tài liệu đã xoá."""
    paths = await document_repository.list_file_paths(db)
    if not paths:
        return 0

    # Xoá row + COMMIT trước, rồi dọn Weaviate/file (best-effort).
    deleted = await document_repository.delete_all(db)
    await db.commit()

    try:
        await asyncio.to_thread(vector_store.delete_collection)
    except Exception:  # noqa: BLE001 — Weaviate lỗi không cản; row đã xoá
        logger.exception("Xoá collection Weaviate lỗi — bỏ qua.")
    for file_path in paths:
        with contextlib.suppress(FileNotFoundError, OSError):
            Path(file_path).unlink()

    return deleted
