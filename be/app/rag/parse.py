"""Parse PDF/DOCX → markdown sạch theo trang bằng LlamaParse (LlamaCloud) qua REST API.

Thay TOÀN BỘ tầng trích xuất cũ (pdfplumber + OCR Vision + python-docx + xử lý font lỗi):
LlamaParse (cloud) lo OCR trang scan, bảng, font/dấu tiếng Việt phía server, trả về cho mỗi trang
markdown đã loại header/footer chạy + danh sách ``items`` ĐÃ PHÂN LOẠI (heading | text | table, kèm
``rows`` lưới ô cho bảng) — dùng làm block nguyên tử cho bước chunk.

Gọi REST API trực tiếp bằng ``httpx`` — KHÔNG dùng SDK ``llama-cloud``/``llama-cloud-services`` vì các
gói này phụ thuộc ``pydantic.v1`` → vỡ import trên Python 3.14 (đã kiểm chứng trên máy dự án).

Quy ước dự án:
- Hàm chạy ĐỒNG BỘ (tầng service bọc ``asyncio.to_thread``); mọi request có timeout + trần chờ job.
- Bọc span Phoenix ``rag.ingest.parse``.
- KHÔNG log nội dung/PII — chỉ log SỐ TRANG + job id.
- Thiếu API key → ``RuntimeError``; kết quả rỗng → ``ValueError`` (ingest đánh failed thay vì báo
  ready mà thiếu nội dung).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from opentelemetry import trace

from app.core.config import settings

logger = logging.getLogger(__name__)

# Kiểu một bảng: danh sách hàng, mỗi hàng là danh sách ô (ô rỗng = None) — khớp DocumentChunk.table_data.
Table = list[list[str | None]]

_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_DONE = {"SUCCESS", "PARTIAL_SUCCESS"}
_FAIL = {"ERROR", "CANCELLED", "CANCELED"}


@dataclass
class ParsedBlock:
    """Một block nguyên tử do LlamaParse phân loại (``item``): heading | text | table."""

    type: str  # "heading" | "text" | "table"
    value: str  # nội dung thuần (heading: chữ KHÔNG kèm '#')
    md: str  # markdown của block (heading: '# ...'; bảng: GFM '| |')
    level: int | None = None  # cấp tiêu đề (chỉ type == "heading")
    rows: Table | None = None  # lưới ô (chỉ type == "table")


@dataclass
class ParsedPage:
    """Nội dung một trang sau khi LlamaParse parse."""

    page_number: int
    md: str  # markdown cả trang (đã loại header/footer chạy)
    blocks: list[ParsedBlock] = field(default_factory=list)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.llama_cloud_api_key}",
        "accept": "application/json",
    }


def _to_block(item: dict) -> ParsedBlock | None:
    """Chuẩn hóa một ``item`` LlamaParse → ParsedBlock; trả None nếu rỗng/không hỗ trợ."""
    typ = item.get("type")
    if typ not in ("heading", "text", "table"):
        return None
    md = (item.get("md") or "").strip()
    value = (item.get("value") or "").strip()
    rows: Table | None = None
    if typ == "table" and isinstance(item.get("rows"), list):
        # "" → None để khớp kiểu Table (ô rỗng); giữ nguyên thứ tự hàng/cột.
        rows = [[((cell or "").strip() or None) for cell in row] for row in item["rows"]]
    if not md and not value and not rows:
        return None
    return ParsedBlock(
        type=typ,
        value=value or md,
        md=md or value,
        level=item.get("lvl"),
        rows=rows,
    )


def _upload(client: httpx.Client, path: str) -> str:
    ext = Path(path).suffix.lower()
    mime = _MIME.get(ext, "application/octet-stream")
    with open(path, "rb") as f:
        files = {"file": (Path(path).name, f, mime)}
        data = {"language": settings.llamaparse_language}
        r = client.post(
            f"{settings.llamaparse_base_url}/upload",
            headers=_headers(),
            files=files,
            data=data,
        )
    r.raise_for_status()
    return r.json()["id"]


def _wait(client: httpx.Client, job_id: str) -> str:
    """Poll trạng thái job tới khi xong/lỗi/hết giờ. Trả status cuối (SUCCESS/PARTIAL_SUCCESS)."""
    deadline = time.monotonic() + settings.llamaparse_max_wait_seconds
    while True:
        r = client.get(f"{settings.llamaparse_base_url}/job/{job_id}", headers=_headers())
        r.raise_for_status()
        status = r.json().get("status")
        if status in _DONE:
            return status
        if status in _FAIL:
            raise ValueError(f"LlamaParse job lỗi (status={status}, job={job_id}).")
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"LlamaParse quá {settings.llamaparse_max_wait_seconds}s chưa xong (job {job_id})."
            )
        time.sleep(settings.llamaparse_poll_interval)


def _fetch_pages(client: httpx.Client, job_id: str) -> list[ParsedPage]:
    r = client.get(
        f"{settings.llamaparse_base_url}/job/{job_id}/result/json", headers=_headers()
    )
    r.raise_for_status()
    raw_pages = r.json().get("pages", []) or []
    pages: list[ParsedPage] = []
    for i, p in enumerate(raw_pages):
        blocks = [
            b for b in (_to_block(it) for it in (p.get("items") or [])) if b is not None
        ]
        pages.append(
            ParsedPage(
                page_number=int(p.get("page") or i + 1),
                md=(p.get("md") or "").strip(),
                blocks=blocks,
            )
        )
    return pages

# Kết quả trả về
# {
#   "pages": [
#     {
#       "page": 1,
#       "md":   "# KẾ HOẠCH\n\n# Huy động trẻ ra lớp...\n\n...",   // ← markdown CẢ TRANG
#       "text": "KẾ HOẠCH Huy động trẻ ra lớp...",                // text thuần (không markdown)
#       "items": [                                                 // ← từng block ĐÃ PHÂN LOẠI
#         { "type": "heading", "lvl": 1, "value": "KẾ HOẠCH", "md": "# KẾ HOẠCH" },
#         { "type": "text",    "value": "Thực hiện Quyết định...", "md": "Thực hiện Quyết định..." },
#         { "type": "table",   "rows": [["Ngày bắt đầu","Nội dung"],["22/4/2026","..."]],
#                              "md": "| Ngày bắt đầu | Nội dung |\n| --- | --- |\n| 22/4/2026 | ... |" }
#       ],
#       "pageHeaderMarkdown": "ỦY BAN NHÂN DÂN\nPHƯỜNG BÌNH THẠNH\n...",
#       "pageFooterMarkdown": ""
#     }
#   ],
#   "job_metadata": { ... }
# }


def parse_document(path: str) -> list[ParsedPage]:
    """Parse 1 file PDF/DOCX → ``list[ParsedPage]`` (markdown + blocks theo trang) qua LlamaParse.

    Raise ``RuntimeError`` nếu thiếu API key; ``ValueError`` nếu kết quả rỗng; ``TimeoutError`` nếu
    job quá lâu. Bọc span Phoenix ``rag.ingest.parse``. Không log nội dung (PII)."""
    if not settings.llama_cloud_api_key:
        raise RuntimeError(
            "Thiếu LLAMA_CLOUD_API_KEY — không thể parse tài liệu qua LlamaParse."
        )

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.ingest.parse") as span:
        with httpx.Client(timeout=settings.llamaparse_http_timeout) as client:
            job_id = _upload(client, path)
            span.set_attribute("rag.ingest.parse.job_id", job_id)
            status = _wait(client, job_id)
            pages = _fetch_pages(client, job_id)

        if not pages or not any(p.md or p.blocks for p in pages):
            raise ValueError("LlamaParse trả kết quả rỗng (không trích được nội dung).")

        span.set_attribute("rag.ingest.parse.pages", len(pages))
        span.set_attribute("rag.ingest.parse.status", status)
        logger.info("parse: job %s xong (%s trang, status=%s).", job_id, len(pages), status)
        return pages
