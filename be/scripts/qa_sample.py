"""QA mẫu chunk sau tiền xử lý — lấy ngẫu nhiên N chunk để RÀ TAY + cờ toàn vẹn tự động.

READ-ONLY: chỉ SELECT, không ghi DB/Weaviate. Chạy sau khi đã ingest tài liệu:

    python scripts/qa_sample.py --n 20            # 20 chunk ngẫu nhiên toàn kho
    python scripts/qa_sample.py --n 10 --doc-id 3 # chỉ tài liệu id=3
    python scripts/qa_sample.py --seed 42         # cố định mẫu để tái lập

Exit code != 0 nếu có cờ NẶNG (TABLE_NO_DATA / CONTEXT_IN_CONTENT) → dùng như cổng CI nhẹ.
Không in PII ra log hệ thống; chỉ in nội dung chunk ra stdout cho người rà (cắt 300 ký tự).
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.document import Document, DocumentChunk  # noqa: E402

# Cờ "nặng": gần như chắc chắn là lỗi pipeline → làm fail cổng CI.
HEAVY_FLAGS = frozenset({"TABLE_NO_DATA", "CONTEXT_IN_CONTENT"})


def compute_flags(chunk: object, *, chunk_size: int) -> list[str]:
    """Tính các cờ toàn vẹn cho MỘT chunk (hàm thuần — nhận object có các thuộc tính chunk).

    Đọc thuộc tính bằng ``getattr`` để chạy được trên cả ORM ``DocumentChunk`` lẫn ``SimpleNamespace``
    trong test. KHÔNG sửa đổi ``chunk``."""
    content = getattr(chunk, "content", "") or ""
    has_table = bool(getattr(chunk, "has_table", False))
    table_data = getattr(chunk, "table_data", None)
    context = getattr(chunk, "context", None) or ""
    token_count = getattr(chunk, "token_count", None) or 0
    weaviate_uuid = getattr(chunk, "weaviate_uuid", None)
    heading_path = getattr(chunk, "heading_path", None)

    flags: list[str] = []
    if not content.strip():
        flags.append("EMPTY_CONTENT")
    if has_table:
        grid = table_data.get("grid") if isinstance(table_data, dict) else table_data
        if not grid:
            flags.append("TABLE_NO_DATA")  # bảng nhưng mất lưới thô
        elif "|" not in content:
            flags.append(
                "TABLE_MD_MISMATCH"
            )  # có lưới nhưng markdown content không thấy bảng
    # content phải NGUYÊN VĂN — context chỉ prepend vào node.text, không được lẫn vào content.
    if context.strip() and context.strip() in content:
        flags.append("CONTEXT_IN_CONTENT")
    if token_count > 3 * chunk_size:
        flags.append("TOKEN_OUTLIER")  # Khoản nguyên tử quá lớn — cần soi
    if weaviate_uuid is None:
        flags.append("WEAVIATE_UUID_NULL")  # chunk không vào vector store
    if not has_table and not heading_path:
        flags.append("HEADING_EMPTY")  # cảnh báo mềm
    return flags


def select_sample(rows: list, n: int, seed: int | None) -> list:
    """Chọn ngẫu nhiên tối đa ``n`` phần tử (hàm thuần, không sửa ``rows``). ``seed`` cố định để tái lập."""
    if n <= 0 or len(rows) <= n:
        return list(rows)
    rng = random.Random(seed)
    return rng.sample(list(rows), n)


async def _load_rows(
    doc_id: int | None, session_maker=AsyncSessionLocal
) -> list[SimpleNamespace]:
    """Đọc chunk (+ tên tài liệu) thành ``SimpleNamespace`` để tách khỏi session (READ-ONLY)."""
    async with session_maker() as db:
        stmt = select(DocumentChunk, Document.filename).join(
            Document, Document.id == DocumentChunk.document_id
        )
        if doc_id is not None:
            stmt = stmt.where(DocumentChunk.document_id == doc_id)
        result = await db.execute(stmt)
        rows: list[SimpleNamespace] = []
        for chunk, filename in result.all():
            rows.append(
                SimpleNamespace(
                    document_id=chunk.document_id,
                    filename=filename,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    context=chunk.context,
                    chunk_type=chunk.chunk_type,
                    has_table=chunk.has_table,
                    table_data=chunk.table_data,
                    token_count=chunk.token_count,
                    page_number=chunk.page_number,
                    heading_path=chunk.heading_path,
                    weaviate_uuid=chunk.weaviate_uuid,
                )
            )
        return rows


def _print_chunk(row: SimpleNamespace, flags: list[str]) -> None:
    badge = ("⚠ " + ", ".join(flags)) if flags else "OK"
    print("─" * 80)
    print(
        f"[{row.filename} #{row.chunk_index}] trang {row.page_number} · {row.chunk_type} · "
        f"{row.token_count} tok · {badge}"
    )
    if row.heading_path:
        print(f"  ▸ {row.heading_path}")
    snippet = (row.content or "").strip().replace("\n", " ")
    print(f"  {snippet[:300]}{'…' if len(snippet) > 300 else ''}")
    if row.has_table and isinstance(row.table_data, dict):
        grid = row.table_data.get("grid") or []
        print(f"  table_data: {len(grid)} hàng × {len(grid[0]) if grid else 0} cột")


async def run(n: int, seed: int | None, doc_id: int | None) -> int:
    """Lấy mẫu + in + tổng kết cờ. Trả exit code (0 ok, 1 có cờ nặng)."""
    rows = await _load_rows(doc_id)
    if not rows:
        print("Không có chunk nào (kho rỗng hoặc doc-id không tồn tại).")
        return 0

    sample = select_sample(rows, n, seed)
    counts: dict[str, int] = {}
    heavy_hits = 0
    for row in sample:
        flags = compute_flags(row, chunk_size=settings.chunk_size)
        _print_chunk(row, flags)
        for f in flags:
            counts[f] = counts.get(f, 0) + 1
        if HEAVY_FLAGS & set(flags):
            heavy_hits += 1

    print("═" * 80)
    print(f"Đã rà {len(sample)}/{len(rows)} chunk.")
    if counts:
        for flag, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            mark = " (NẶNG)" if flag in HEAVY_FLAGS else ""
            print(f"  {flag}: {c} ({c * 100 // len(sample)}%){mark}")
    else:
        print("  Không có cờ nào — mẫu sạch.")
    return 1 if heavy_hits else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QA mẫu chunk sau tiền xử lý (read-only)."
    )
    parser.add_argument(
        "--n", type=int, default=20, help="số chunk lấy mẫu (mặc định 20)"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="seed ngẫu nhiên để tái lập"
    )
    parser.add_argument("--doc-id", type=int, default=None, help="chỉ lấy 1 tài liệu")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.n, args.seed, args.doc_id)))


if __name__ == "__main__":
    main()
