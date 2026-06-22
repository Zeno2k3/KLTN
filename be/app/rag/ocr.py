"""Tầng OCR fallback cho PDF scan ảnh (không có lớp text) — OpenAI Vision qua LlamaIndex.

Tầng 2 của pipeline trích xuất (sau ``extract.extract_with_tables``): CHỈ chạy cho trang bị đánh
dấu ``needs_ocr``. Mỗi trang: render → PNG (pypdfium2, chỉ ở RAM, KHÔNG ghi đĩa) → gửi ``ImageBlock``
lên OpenAI vision-LLM lấy lại text tiếng Việt (bảng → markdown inline) → ghi đè ``page.text``.

Quy ước dự án:
- LLM RIÊNG cho bước OCR (singleton module, không dùng chung với synthesize/chunker/rewriter).
- Mọi call qua LlamaIndex ``OpenAI().chat()`` → Phoenix auto-trace (cấm gọi OpenAI "mù"); cả lượt
  bọc trong span ``rag.ingest.ocr``.
- Không log nội dung/ảnh (PII) — chỉ log SỐ TRANG.
- ``timeout`` + ``max_retries`` để 1 trang API treo không kẹt cả lượt.
- Vượt ``ocr_max_pages`` → raise (ingest → status=failed) thay vì ingest thiếu nội dung mà báo ready.

Hạn chế đã biết: bảng trong trang scan được giữ dạng **markdown inline trong ``page.text``** (chunk
như text, ``has_table=False``) — vision-LLM không trả lưới ô đáng tin để đưa vào ``page.tables``.
"""

from __future__ import annotations

import io
import logging
import re

import pypdfium2 as pdfium
from llama_index.core.llms import ChatMessage, ImageBlock, MessageRole, TextBlock
from llama_index.llms.openai import OpenAI
from opentelemetry import trace

from app.core.config import settings
from app.rag.extract import PageBlock

logger = logging.getLogger(__name__)

_llm: OpenAI | None = None

_OCR_SYSTEM_PROMPT = (
    "Bạn là công cụ OCR. Trích xuất CHÍNH XÁC toàn bộ văn bản trong ảnh trang tài liệu. "
    "Giữ nguyên thứ tự dòng và ngắt dòng theo bố cục gốc. KHÔNG tóm tắt, KHÔNG thêm chú thích, "
    "KHÔNG dịch, KHÔNG bịa. Nếu có bảng, trình bày lại dạng bảng Markdown. "
    "Nếu ảnh không chứa chữ nào, trả về chuỗi rỗng. CHỈ in nội dung trích được."
)


def _get_llm() -> OpenAI:
    """LLM riêng cho OCR (model ``ocr_model`` → fallback chat model). Có timeout + retries."""
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.ocr_model or settings.openai_chat_model,
            api_key=settings.openai_api_key,
            temperature=0.0,
            timeout=settings.ocr_timeout_seconds,
            max_retries=2,
        )
    return _llm


def render_page_png(pdf: pdfium.PdfDocument, page_index: int, dpi: int) -> bytes:
    """Render một trang PDF → PNG bytes (chỉ ở RAM). ``pdf`` mở sẵn (tái dùng cho cả tài liệu)."""
    page = pdf[page_index]
    bitmap = page.render(scale=dpi / 72.0)
    pil = bitmap.to_pil()
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()


def _strip_code_fence(s: str) -> str:
    """Bỏ rào ```...``` mà vision-LLM đôi khi bọc quanh toàn bộ output (lọt vào nội dung chunk)."""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s.strip()


def ocr_page_image(png: bytes) -> str:
    """Gửi ảnh trang lên OpenAI vision → text. Lỗi/timeout → trả "" (KHÔNG làm sập cả lượt)."""
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=_OCR_SYSTEM_PROMPT),
        ChatMessage(
            role=MessageRole.USER,
            blocks=[
                TextBlock(text="Trích xuất toàn bộ văn bản trong ảnh trang này."),
                ImageBlock(image=png, image_mimetype="image/png", detail="high"),
            ],
        ),
    ]
    try:
        resp = _get_llm().chat(messages)
        return _strip_code_fence(resp.message.content or "")
    except Exception:  # noqa: BLE001 — 1 trang lỗi không được làm hỏng cả tài liệu
        logger.exception("OCR một trang lỗi — bỏ qua trang đó.")
        return ""


def ocr_pages(path: str, pages: list[PageBlock]) -> list[PageBlock]:
    """OCR các trang ``needs_ocr`` (ghi đè ``page.text``). Trả lại cùng list ``pages``.

    Vượt ``ocr_max_pages`` → raise ValueError (ingest đánh failed). Mở ``PdfDocument`` MỘT lần cho
    cả tài liệu (tránh parse lại file mỗi trang). Bọc span ``rag.ingest.ocr``."""
    targets = [p for p in pages if p.needs_ocr]
    if not targets:
        return pages
    if len(targets) > settings.ocr_max_pages:
        raise ValueError(
            f"Tài liệu có {len(targets)} trang scan cần OCR, vượt trần "
            f"OCR_MAX_PAGES={settings.ocr_max_pages}. Hãy tách nhỏ tài liệu hoặc tăng ngưỡng."
        )

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.ingest.ocr") as span:
        span.set_attribute("rag.ingest.ocr_pages", len(targets))
        ocr_ok = 0
        pdf = pdfium.PdfDocument(path)
        try:
            for p in targets:
                png = render_page_png(pdf, p.page_number - 1, settings.ocr_dpi)
                text = ocr_page_image(png)
                if text:
                    p.text = text
                    ocr_ok += 1
        finally:
            pdf.close()
        span.set_attribute("rag.ingest.ocr_ok", ocr_ok)
        logger.info("OCR: %s/%s trang scan có kết quả.", ocr_ok, len(targets))
    return pages
