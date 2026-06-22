"""Trích xuất PDF bằng ``pdfplumber`` (đọc được CẢ bảng) — hàm thuần, chạy local.

Thay ``pypdf`` (không đọc được bảng → text hỗn độn). Với mỗi trang trả về:
- ``text``: văn bản KHÔNG bao gồm chữ trong ô bảng (đã crop vùng bảng để tránh đếm 2 lần / nhiễu
  BM25). Nội dung bảng chỉ nằm ở ``tables`` và được dựng thành node độc lập ở tầng chunker.
- ``tables``: danh sách bảng, mỗi bảng là lưới ô (list[list[str|None]]).
- ``page_number``: số trang (1-based).

Không log nội dung PDF (có thể chứa PII). pdfplumber thuần Python (pdfminer.six) → 0 model, an toàn
trên máy RAM thấp.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pdfplumber

logger = logging.getLogger(__name__)

# Kiểu một bảng: danh sách hàng, mỗi hàng là danh sách ô (ô rỗng = None).
Table = list[list[str | None]]


@dataclass
class PageBlock:
    """Nội dung một trang PDF sau khi tách text khỏi bảng."""

    page_number: int
    text: str
    tables: list[Table] = field(default_factory=list)
    # True nếu trang gần như không có text-layer (scan ảnh) → cần OCR ở tầng 2 (xem rag/ocr.py).
    needs_ocr: bool = False


def _has_real_table(tables: list[Table]) -> bool:
    """Có ít nhất một bảng chứa ô KHÔNG rỗng (pdfplumber hay bắt nhầm 'bảng' rỗng trên trang scan)."""
    return any(
        any((cell or "").strip() for row in table for cell in row) for table in tables
    )


def _image_coverage(page: pdfplumber.page.Page) -> float:
    """Tỉ lệ diện tích trang bị ảnh che (0–1). Trang scan thường có 1 ảnh phủ gần kín trang."""
    try:
        page_area = float(page.width) * float(page.height)
        if page_area <= 0:
            return 0.0
        img_area = sum(
            max(0.0, (im["x1"] - im["x0"])) * max(0.0, (im["bottom"] - im["top"]))
            for im in page.images
        )
        return min(img_area / page_area, 1.0)
    except Exception:  # noqa: BLE001 — chỉ là tín hiệu phụ trợ
        return 0.0


def _needs_ocr(text: str, tables: list[Table], img_ratio: float, min_chars: int) -> bool:
    """Quyết định trang có cần OCR không.

    Cần OCR khi: bật ngưỡng (min_chars>0) VÀ không có bảng-thật VÀ
    (text quá ít  HOẶC  ảnh phủ phần lớn trang trong khi text-layer mỏng — bắt cả trang scan có
    watermark/header dạng text). ``not _has_real_table`` để trang scan bị pdfplumber gán 'bảng rỗng'
    KHÔNG thoát OCR (lỗ hổng mất nội dung)."""
    if min_chars <= 0:
        return False
    if _has_real_table(tables):
        return False
    text_len = len(text.strip())
    return text_len < min_chars or (img_ratio >= 0.5 and text_len < min_chars * 5)


def _text_outside_tables(page: pdfplumber.page.Page, table_bboxes: list[tuple]) -> str:
    """Trích text của trang nhưng LOẠI các ký tự nằm trong vùng bảng (theo bbox).

    pdfplumber gộp cả chữ trong ô bảng vào ``extract_text``; nếu không loại, nội dung bảng bị đếm
    hai lần (một lần ở text, một lần ở node bảng). Dùng ``page.filter`` bỏ object có TÂM nằm trong
    bbox bất kỳ của bảng."""
    if not table_bboxes:
        return page.extract_text() or ""

    def _keep(obj: dict) -> bool:
        cx = (obj["x0"] + obj["x1"]) / 2
        cy = (obj["top"] + obj["bottom"]) / 2
        for x0, top, x1, bottom in table_bboxes:
            if x0 <= cx <= x1 and top <= cy <= bottom:
                return False
        return True

    try:
        return page.filter(_keep).extract_text() or ""
    except Exception:  # noqa: BLE001 — filter lỗi hiếm gặp → lùi về text đầy đủ
        logger.warning("pdfplumber: filter bảng lỗi ở trang %s, dùng text đầy đủ.", page.page_number)
        return page.extract_text() or ""


def extract_with_tables(path: str, ocr_min_chars: int = 0) -> list[PageBlock]:
    """Đọc PDF → danh sách ``PageBlock`` (text-không-bảng + bảng) theo từng trang.

    ``ocr_min_chars`` > 0 → đánh dấu ``needs_ocr`` cho trang scan (text-layer dưới ngưỡng); 0 (mặc
    định) → bỏ qua phát hiện scan (giữ tương thích cũ)."""
    pages: list[PageBlock] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            found = page.find_tables()
            bboxes = [t.bbox for t in found]
            tables = [t.extract() for t in found]
            text = _text_outside_tables(page, bboxes).strip()
            needs_ocr = _needs_ocr(
                text, tables, _image_coverage(page), ocr_min_chars
            )
            pages.append(
                PageBlock(
                    page_number=page.page_number,
                    text=text,
                    tables=tables,
                    needs_ocr=needs_ocr,
                )
            )
    return pages


def page_count(path: str) -> int:
    """Số trang của PDF (không tải toàn bộ nội dung)."""
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)
