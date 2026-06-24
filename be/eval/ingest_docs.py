"""Ingest tài liệu PDF thật vào kho RAG QUA PIPELINE THẬT (document_service) — cho eval / nạp corpus.

    PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/ingest_docs.py "C:\\path\\a.pdf" "C:\\path\\b.pdf"

Mỗi file: nếu đã có Document trùng ``filename`` → xóa sạch (vector Weaviate + row + file) rồi nạp lại.
Chạy đủ chuỗi: extract → OCR → metadata → clean (Nhóm A) → title_metadata (Nhóm B) → chunk → embed →
Weaviate. TỐN token OpenAI/Cohere + GHI Weaviate cloud. In ward/year/chunk sau khi xong.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid as uuid_lib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.observability import init_tracing
from app.models.document import Document
from app.repositories import document_repository
from app.services import document_service


async def _delete_same_name(name: str) -> int:
    n = 0
    async with AsyncSessionLocal() as db:
        existing = (
            await db.scalars(select(Document).where(Document.filename == name))
        ).all()
        ids = [d.id for d in existing]
    for doc_id in ids:
        async with AsyncSessionLocal() as db:
            await document_service.delete_document(db, doc_id)
        n += 1
    return n


async def ingest_one(src: Path) -> None:
    name = src.name
    removed = await _delete_same_name(name)
    if removed:
        print(f"  (đã xóa {removed} bản cũ cùng tên)")

    root = document_service._upload_root()
    dest = (
        root / f"{uuid_lib.uuid4().hex}{src.suffix.lower()}"
    )  # giữ đuôi gốc (.pdf/.docx)
    dest.write_bytes(src.read_bytes())
    async with AsyncSessionLocal() as db:
        doc = await document_service.create_document(
            db,
            filename=name,
            file_path=str(dest),
            file_size=dest.stat().st_size,
            uploaded_by=None,
        )
        doc_id = doc.id

    print(f"  ingest id={doc_id} ...")
    await document_service.ingest_document(doc_id)

    async with AsyncSessionLocal() as db:
        doc = await document_repository.get_by_id(db, doc_id)
        print(
            f"  -> status={doc.status} ward={doc.ward!r} year={doc.school_year!r} "
            f"type={doc.doc_type!r} chunks={doc.chunk_count}"
        )
        if str(doc.status) != "DocumentStatus.ready" and doc.status.value != "ready":
            print("  !! LỖI:", doc.error_message)


async def main(paths: list[str]) -> None:
    init_tracing()  # OTEL → Phoenix (script standalone không có lifespan app → phải tự bật)
    for p in paths:
        src = Path(p)
        print(f"\n=== {src.name} ===")
        if not src.exists():
            print("  [MISSING]", src)
            continue
        await ingest_one(src)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="đường dẫn các PDF cần ingest")
    args = ap.parse_args()
    asyncio.run(main(args.paths))
