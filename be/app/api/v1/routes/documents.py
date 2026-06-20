"""Endpoint quản trị kho tài liệu PDF (chỉ admin): upload, danh sách, xoá.

Upload lưu file + tạo bản ghi 'processing' rồi lên lịch ingest nền
(trích xuất → chunk → embed → Weaviate). Trạng thái cập nhật bất đồng bộ;
frontend poll danh sách để thấy 'processing' → 'ready'/'failed'.
"""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.user import User
from app.repositories import document_repository
from app.schemas.document import DocumentResponse
from app.services import document_service

router = APIRouter(prefix="/admin/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[DocumentResponse]:
    docs = await document_repository.list_all(db)
    return [DocumentResponse.model_validate(doc) for doc in docs]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DocumentResponse:
    file_path, file_size, filename = await document_service.save_upload(file)
    document = await document_service.create_document(
        db,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        uploaded_by=current_user.id,
    )
    # Chụp lại dữ liệu trước khi session đóng; ingest chạy SAU khi response đã gửi.
    response = DocumentResponse.model_validate(document)
    background_tasks.add_task(document_service.ingest_document, document.id)
    return response


@router.get("/{document_id}/file")
async def serve_document_file(
    document_id: int,
    download: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> FileResponse:
    """Phục vụ file PDF gốc để xem (inline) hoặc tải xuống (attachment khi ?download=1)."""
    path, filename = await document_service.get_document_file(db, document_id)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_all_documents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, int]:
    """Xoá tất cả tài liệu (vector + file + bản ghi). Trả số lượng đã xoá."""
    deleted = await document_service.delete_all_documents(db)
    return {"deleted": deleted}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    await document_service.delete_document(db, document_id)
