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
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from opentelemetry import trace

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lỗi transport httpx coi là TẠM THỜI (thử lại được): timeout, mất kết nối, server đóng đột ngột.
_TRANSIENT_EXC = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
)


def _is_transient_status(code: int) -> bool:
    """429 (rate limit), 499 (client closed — proxy LlamaCloud), 5xx (lỗi server) → thử lại được."""
    return code == 429 or code == 499 or code >= 500


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
        rows = [
            [((cell or "").strip() or None) for cell in row] for row in item["rows"]
        ]
    if not md and not value and not rows:
        return None
    return ParsedBlock(
        type=typ,
        value=value or md,
        md=md or value,
        level=item.get("lvl"),
        rows=rows,
    )


def _request_with_retry(
    send: Callable[[], httpx.Response], what: str
) -> httpx.Response:
    """Gọi một request httpx, thử lại khi lỗi TẠM THỜI (429/499/5xx + lỗi transport).

    ``send`` PHẢI tự thực hiện request từ đầu mỗi lần gọi (vd upload mở lại file — upload không
    resume được). 4xx khác (400/401/413/415…) → raise NGAY (lỗi do file/khoá, retry vô ích).
    Backoff lũy thừa + jitter (LlamaParse không trả ``Retry-After``). KHÔNG log nội dung/PII."""
    last_exc: Exception | None = None
    for attempt in range(settings.llamaparse_max_retries + 1):
        try:
            r = send()
            r.raise_for_status()
            return r
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if not _is_transient_status(code):
                raise  # 4xx không-transient → hỏng thật, không thử lại
            last_exc = exc
            reason = f"HTTP {code}"
        except _TRANSIENT_EXC as exc:
            last_exc = exc
            reason = type(exc).__name__
        if attempt >= settings.llamaparse_max_retries:
            break
        delay = settings.llamaparse_retry_base_delay * (2**attempt) + random.uniform(
            0, 1
        )
        logger.warning(
            "parse %s: lỗi tạm thời (%s), thử lại %d/%d sau %.1fs.",
            what,
            reason,
            attempt + 1,
            settings.llamaparse_max_retries,
            delay,
        )
        time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _upload(client: httpx.Client, path: str) -> str:
    ext = Path(path).suffix.lower()
    mime = _MIME.get(ext, "application/octet-stream")
    name = Path(path).name
    url = f"{settings.llamaparse_base_url}/upload"
    # parse_mode: ép vision đọc trang (bỏ qua text-layer font lỗi → giữ dấu tiếng Việt). Xem config.
    data = {
        "language": settings.llamaparse_language,
        "parse_mode": settings.llamaparse_parse_mode,
    }

    def send() -> httpx.Response:
        # Mở lại file MỖI lần thử: upload không resume → phải gửi lại từ đầu con trỏ.
        with open(path, "rb") as f:
            return client.post(
                url, headers=_headers(), files={"file": (name, f, mime)}, data=data
            )

    r = _request_with_retry(send, "upload")
    return r.json()["id"]


def _wait(client: httpx.Client, job_id: str) -> str:
    """Poll trạng thái job tới khi xong/lỗi/hết giờ. Trả status cuối (SUCCESS/PARTIAL_SUCCESS)."""
    deadline = time.monotonic() + settings.llamaparse_max_wait_seconds
    url = f"{settings.llamaparse_base_url}/job/{job_id}"
    while True:
        r = _request_with_retry(lambda: client.get(url, headers=_headers()), "poll")
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
    url = f"{settings.llamaparse_base_url}/job/{job_id}/result/json"
    r = _request_with_retry(lambda: client.get(url, headers=_headers()), "result")
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
        # Pha WRITE (đẩy file) có ngân sách RIÊNG & rộng — tránh httpx tự ngắt khi upload file lớn
        # (→ LlamaCloud trả 499). connect/read/pool theo timeout chung.
        timeout = httpx.Timeout(
            connect=10.0,
            read=settings.llamaparse_http_timeout,
            write=settings.llamaparse_upload_write_timeout,
            pool=10.0,
        )
        with httpx.Client(timeout=timeout) as client:
            job_id = _upload(client, path)
            span.set_attribute("rag.ingest.parse.job_id", job_id)
            status = _wait(client, job_id)
            pages = _fetch_pages(client, job_id)

        if not pages or not any(p.md or p.blocks for p in pages):
            raise ValueError("LlamaParse trả kết quả rỗng (không trích được nội dung).")

        span.set_attribute("rag.ingest.parse.pages", len(pages))
        span.set_attribute("rag.ingest.parse.status", status)
        logger.info(
            "parse: job %s xong (%s trang, status=%s).", job_id, len(pages), status
        )
        return pages
