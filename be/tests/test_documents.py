"""Test endpoint /admin/documents: upload (tạo bản ghi + lên lịch ingest), phân quyền,
danh sách, xoá. Ingest nền được MOCK để không gọi OpenAI/Weaviate thật."""

import pytest
from sqlalchemy import func, select

from app.models.base import DocumentStatus
from app.models.document import Document, DocumentChunk
from app.repositories import document_repository
from app.services import document_service


def _pdf_file(name="quy-che.pdf", content=b"%PDF-1.4 noi dung gia"):
    return {"file": (name, content, "application/pdf")}


@pytest.mark.asyncio
async def test_upload_creates_document_and_schedules_ingest(
    admin_client, monkeypatch, tmp_path
):
    calls: list[int] = []

    async def fake_ingest(document_id):
        calls.append(document_id)

    monkeypatch.setattr(document_service, "ingest_document", fake_ingest)
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    resp = await admin_client.post("/api/v1/admin/documents", files=_pdf_file())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["filename"] == "quy-che.pdf"
    assert body["status"] == "processing"
    assert body["chunk_count"] == 0

    # File đã lưu ra đĩa (thư mục tạm)
    saved = list(tmp_path.glob("*.pdf"))
    assert len(saved) == 1

    # Ingest nền được lên lịch đúng id
    assert calls == [body["id"]]


@pytest.mark.asyncio
async def test_upload_forbidden_for_non_admin(user_client, monkeypatch, tmp_path):
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))
    resp = await user_client.post("/api/v1/admin/documents", files=_pdf_file())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(admin_client, monkeypatch, tmp_path):
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))
    resp = await admin_client.post(
        "/api/v1/admin/documents",
        files={"file": ("ghi-chu.txt", b"khong phai pdf", "text/plain")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_list_documents(admin_client, monkeypatch, tmp_path):
    async def fake_ingest(document_id):
        return None

    monkeypatch.setattr(document_service, "ingest_document", fake_ingest)
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    empty = await admin_client.get("/api/v1/admin/documents")
    assert empty.status_code == 200
    assert empty.json() == []

    for name in ("a.pdf", "b.pdf"):
        await admin_client.post("/api/v1/admin/documents", files=_pdf_file(name))

    resp = await admin_client.get("/api/v1/admin/documents")
    assert resp.status_code == 200
    assert {d["filename"] for d in resp.json()} == {"a.pdf", "b.pdf"}


@pytest.mark.asyncio
async def test_delete_document_removes_file_and_row(
    admin_client, monkeypatch, tmp_path
):
    async def fake_ingest(document_id):
        return None

    monkeypatch.setattr(document_service, "ingest_document", fake_ingest)
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    up = await admin_client.post("/api/v1/admin/documents", files=_pdf_file("c.pdf"))
    doc_id = up.json()["id"]
    saved = list(tmp_path.glob("*.pdf"))
    assert len(saved) == 1

    # Không có chunk (ingest mock) → KHÔNG gọi Weaviate; chốt lại để chắc chắn không ra mạng.
    weaviate_calls: list = []
    monkeypatch.setattr(
        document_service.vector_store,
        "delete_objects",
        lambda uuids: weaviate_calls.append(uuids),
    )

    resp = await admin_client.delete(f"/api/v1/admin/documents/{doc_id}")
    assert resp.status_code == 204
    assert not saved[0].exists()
    assert weaviate_calls == []

    listing = await admin_client.get("/api/v1/admin/documents")
    assert listing.json() == []


@pytest.mark.asyncio
async def test_delete_missing_document_returns_404(admin_client):
    resp = await admin_client.delete("/api/v1/admin/documents/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_serve_document_file_inline_and_download(
    admin_client, monkeypatch, tmp_path
):
    async def fake_ingest(document_id):
        return None

    monkeypatch.setattr(document_service, "ingest_document", fake_ingest)
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    content = b"%PDF-1.4 noi dung de xem lai"
    up = await admin_client.post(
        "/api/v1/admin/documents", files=_pdf_file("xem.pdf", content)
    )
    doc_id = up.json()["id"]

    # Xem (inline)
    view = await admin_client.get(f"/api/v1/admin/documents/{doc_id}/file")
    assert view.status_code == 200
    assert view.headers["content-type"].startswith("application/pdf")
    assert "inline" in view.headers["content-disposition"]
    assert view.content == content

    # Tải (attachment)
    dl = await admin_client.get(
        f"/api/v1/admin/documents/{doc_id}/file", params={"download": "true"}
    )
    assert dl.status_code == 200
    assert "attachment" in dl.headers["content-disposition"]
    assert "xem.pdf" in dl.headers["content-disposition"]


@pytest.mark.asyncio
async def test_serve_file_missing_document_returns_404(admin_client):
    resp = await admin_client.get("/api/v1/admin/documents/99999/file")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_serve_file_forbidden_for_non_admin(user_client):
    resp = await user_client.get("/api/v1/admin/documents/1/file")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_all_documents(admin_client, monkeypatch, tmp_path):
    async def fake_ingest(document_id):
        return None

    monkeypatch.setattr(document_service, "ingest_document", fake_ingest)
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    # Mock drop collection Weaviate (không ra mạng); 2 doc → sẽ được gọi.
    drop_calls: list[int] = []
    monkeypatch.setattr(
        document_service.vector_store,
        "delete_collection",
        lambda: drop_calls.append(1),
    )

    for name in ("a.pdf", "b.pdf", "c.pdf"):
        await admin_client.post("/api/v1/admin/documents", files=_pdf_file(name))
    assert len(list(tmp_path.glob("*.pdf"))) == 3

    resp = await admin_client.delete("/api/v1/admin/documents")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 3}
    assert drop_calls == [1]
    assert list(tmp_path.glob("*.pdf")) == []  # mọi file đã xoá

    listing = await admin_client.get("/api/v1/admin/documents")
    assert listing.json() == []


@pytest.mark.asyncio
async def test_delete_all_empty_is_noop(admin_client, monkeypatch):
    # Không có tài liệu → KHÔNG đụng Weaviate, trả deleted=0.
    drop_calls: list[int] = []
    monkeypatch.setattr(
        document_service.vector_store,
        "delete_collection",
        lambda: drop_calls.append(1),
    )
    resp = await admin_client.delete("/api/v1/admin/documents")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 0}
    assert drop_calls == []


@pytest.mark.asyncio
async def test_delete_all_forbidden_for_non_admin(user_client):
    resp = await user_client.delete("/api/v1/admin/documents")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_document_also_deletes_chunks(doc_session):
    """Xoá 1 tài liệu phải xoá luôn chunk con (không để mồ côi, kể cả SQLite không cascade)."""
    doc = await document_repository.create(
        doc_session,
        Document(
            filename="x.pdf",
            file_path="/tmp/x.pdf",
            file_size=1,
            status=DocumentStatus.ready,
        ),
    )
    await document_repository.add_chunks(
        doc_session,
        [
            DocumentChunk(document_id=doc.id, chunk_index=0, content="a"),
            DocumentChunk(document_id=doc.id, chunk_index=1, content="b"),
        ],
    )
    await doc_session.commit()

    await document_repository.delete(doc_session, doc)
    await doc_session.commit()

    docs_left = await doc_session.scalar(select(func.count()).select_from(Document))
    chunks_left = await doc_session.scalar(
        select(func.count()).select_from(DocumentChunk)
    )
    assert docs_left == 0
    assert chunks_left == 0  # KHÔNG còn chunk mồ côi


@pytest.mark.asyncio
async def test_rename_document(admin_client, monkeypatch, tmp_path):
    async def fake_ingest(document_id):
        return None

    monkeypatch.setattr(document_service, "ingest_document", fake_ingest)
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    up = await admin_client.post("/api/v1/admin/documents", files=_pdf_file("cu.pdf"))
    doc_id = up.json()["id"]

    resp = await admin_client.patch(
        f"/api/v1/admin/documents/{doc_id}",
        json={"filename": "Quy chế tuyển sinh 2026.pdf"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["filename"] == "Quy chế tuyển sinh 2026.pdf"

    # Danh sách phản ánh tên mới
    listing = await admin_client.get("/api/v1/admin/documents")
    assert listing.json()[0]["filename"] == "Quy chế tuyển sinh 2026.pdf"


@pytest.mark.asyncio
async def test_rename_trims_whitespace(admin_client, monkeypatch, tmp_path):
    async def fake_ingest(document_id):
        return None

    monkeypatch.setattr(document_service, "ingest_document", fake_ingest)
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    up = await admin_client.post("/api/v1/admin/documents", files=_pdf_file())
    doc_id = up.json()["id"]
    resp = await admin_client.patch(
        f"/api/v1/admin/documents/{doc_id}", json={"filename": "  Tên gọn  "}
    )
    assert resp.status_code == 200
    assert resp.json()["filename"] == "Tên gọn"


@pytest.mark.asyncio
async def test_rename_missing_document_returns_404(admin_client):
    resp = await admin_client.patch(
        "/api/v1/admin/documents/99999", json={"filename": "x.pdf"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rename_empty_filename_rejected(admin_client):
    # min_length=1 ở schema → 422; chuỗi chỉ khoảng trắng → service trả 400.
    blank = await admin_client.patch("/api/v1/admin/documents/1", json={"filename": ""})
    assert blank.status_code == 422


@pytest.mark.asyncio
async def test_rename_forbidden_for_non_admin(user_client):
    resp = await user_client.patch(
        "/api/v1/admin/documents/1", json={"filename": "x.pdf"}
    )
    assert resp.status_code == 403
