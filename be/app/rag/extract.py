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
import re
import unicodedata
from dataclasses import dataclass, field

import pdfplumber
import pypdfium2 as pdfium

from app.core.config import settings

logger = logging.getLogger(__name__)

# Kiểu một bảng: danh sách hàng, mỗi hàng là danh sách ô (ô rỗng = None).
Table = list[list[str | None]]

# Stopword tiếng Việt tần suất rất cao — xuất hiện ở MỌI văn bản hành chính bình thường. Mojibake
# (font VNI/TCVN3) biến "của/và/là" thành rác → tỉ lệ trúng tụt về ~0 (tín hiệu phát hiện garbled).
_VI_STOPWORDS: frozenset[str] = frozenset(
    {
        "của",
        "và",
        "là",
        "các",
        "được",
        "trong",
        "cho",
        "không",
        "này",
        "với",
        "để",
        "theo",
        "có",
        "một",
        "những",
        "người",
        "khi",
        "tại",
        "về",
        "đã",
        "phải",
        "như",
        "trên",
        "hoặc",
        "do",
        "từ",
        "đến",
        "thì",
        "sẽ",
        "nếu",
    }
)
# Ký tự HỢP LỆ ngoài chữ-số: dấu câu cơ bản + ký hiệu hay gặp. Chữ Việt có dấu (à, ế, ộ…) là
# ``str.isalnum()`` nên KHÔNG bị tính "lạ"; chỉ glyph sai-map (ª º ¨ © control-char) mới vượt ngưỡng.
_PUNCT_OK: frozenset[str] = frozenset(".,;:!?()[]{}\"'-–—/%°…•·№+=*&@#§")
# Dạng KHÔNG DẤU của stopword — font hỏng phổ biến nhất strip dấu ("của"→"cua", "và"→"va"). Khớp tập
# này → văn bản VẪN là tiếng Việt (chỉ mất dấu); phân biệt với scramble thật (không khớp tập nào).
_VI_STOPWORDS_ASCII: frozenset[str] = frozenset(
    {
        "cua", "va", "la", "cac", "duoc", "trong", "cho", "khong", "nay", "voi",
        "de", "theo", "co", "mot", "nhung", "nguoi", "khi", "tai", "ve", "da",
        "phai", "nhu", "tren", "hoac", "do", "tu", "den", "thi", "se", "neu",
    }
)
# Ký tự CÓ DẤU tiếng Việt (precomposed, NFC). Mật độ tập này ~0 mà vẫn là tiếng Việt → diacritic bị
# strip (kiểu lỗi font phổ biến nhất ở native-PDF tiếng Việt: glyph có dấu map về chữ ASCII trần).
_VI_DIACRITICS_LOWER = (
    "ăâđêôơư"
    "àáảãạằắẳẵặầấẩẫậ"
    "èéẻẽẹềếểễệ"
    "ìíỉĩị"
    "òóỏõọồốổỗộờớởỡợ"
    "ùúủũụừứửữự"
    "ỳýỷỹỵ"
)
_VI_DIACRITICS: frozenset[str] = frozenset(
    _VI_DIACRITICS_LOWER + _VI_DIACRITICS_LOWER.upper()
)


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


def _normalize_table(table: Table) -> Table:
    """NFC từng ô (giữ ``None``). Hợp nhất diacritic tách rời để khớp BM25/embedding như ``text``."""
    return [
        [unicodedata.normalize("NFC", c) if isinstance(c, str) else c for c in row]
        for row in table
    ]


def _is_suspicious_char(c: str) -> bool:
    """Ký tự RÁC chắc chắn của mojibake: PUA (Co), control (Cc), format (Cf), unassigned (Cn),
    replacement (U+FFFD). Bỏ qua \\n\\t\\r (xuống dòng hợp lệ)."""
    if c in "\n\t\r":
        return False
    return c == "�" or unicodedata.category(c) in ("Co", "Cc", "Cf", "Cn")


def _looks_garbled(text: str) -> bool:
    """True nếu text tiếng Việt có dấu hiệu lỗi font (subset-font thiếu ToUnicode / VNI / TCVN3).

    Heuristic THUẦN (không gọi mạng), CHỈ chạy khi text đủ dài (>= ``garbled_min_chars``) để tránh
    false-positive với ASCII ngắn / bảng số / mục lục. Bốn tín hiệu (OR):
      (s) ký tự RÁC (PUA/control/replacement) > ngưỡng-thấp → subset-font thiếu ToUnicode;
      (b) ký tự LẠ symbol (ngoài chữ-số + dấu câu) quá cao → glyph dấu bị map sai (ª º ¨ © …);
      (a) KHÔNG khớp stopword nào (cả có dấu lẫn không dấu) → chữ bị scramble, 'không giống tiếng Việt';
      (d) NHẬN RA là tiếng Việt (đủ stopword) NHƯNG mật độ ký tự dấu ~0 → diacritic bị strip
          ("CỘNG HÒA"→"CONG HOA") — kiểu lỗi font PHỔ BIẾN NHẤT ở native-PDF tiếng Việt.
    Gọi SAU khi đã NFC để combining-char không bị đếm nhầm là 'lạ'."""
    stripped = text.strip()
    if len(stripped) < settings.garbled_min_chars:
        return False

    considered = [c for c in stripped if not c.isspace()]
    if not considered:
        return False

    # (s) Ký tự rác chắc chắn — ngưỡng thấp (vài % là đủ kết luận).
    suspicious = sum(1 for c in considered if _is_suspicious_char(c))
    if (suspicious / len(considered)) > settings.garbled_suspicious_ratio:
        return True

    # (b) Ký tự "lạ" symbol (không phải alnum — đã gồm chữ Việt có dấu — không dấu câu OK).
    foreign = sum(1 for c in considered if not c.isalnum() and c not in _PUNCT_OK)
    if (foreign / len(considered)) > settings.garbled_foreign_ratio:
        return True

    # Stopword: khớp CẢ dạng có dấu lẫn không dấu → phân biệt 'là tiếng Việt' vs 'scramble'.
    tokens = [
        t.strip(".,;:()[]\"'")
        for t in re.split(r"\s+", stripped.lower())
        if any(c.isalpha() for c in t)
    ]
    if len(tokens) < settings.garbled_min_words:
        return False  # quá ít từ (bảng/mục lục) → không đủ cơ sở kết luận.
    hits = sum(1 for t in tokens if t in _VI_STOPWORDS or t in _VI_STOPWORDS_ASCII)
    if (hits / len(tokens)) < settings.garbled_stopword_ratio:
        return True  # (a) không từ chức năng tiếng Việt nào → scramble.

    # (d) LÀ tiếng Việt nhưng gần như KHÔNG có ký tự dấu → diacritic bị strip.
    letters = [c for c in stripped if c.isalpha()]
    if letters:
        diac = sum(1 for c in letters if c in _VI_DIACRITICS)
        if (diac / len(letters)) < settings.garbled_diacritic_ratio:
            return True
    return False


def _pdfium_page_text(pdf: pdfium.PdfDocument, page_index: int) -> str:
    """Re-extract text MỘT trang bằng PDFium (engine KHÁC pdfminer) + NFC. Lỗi → "".

    Dùng cứu trang bị pdfminer đọc garbled trước khi fallback OCR Vision (đắt). PDFium KHÔNG crop
    bảng → caller phải drop ``tables`` khi nhận kết quả này (tránh đếm 2 lần)."""
    try:
        textpage = pdf[page_index].get_textpage()
        raw = textpage.get_text_range()
        return unicodedata.normalize("NFC", raw or "")
    except Exception:  # noqa: BLE001 — retry best-effort, không được làm sập extract
        logger.warning("pdfium retry text lỗi ở trang %s.", page_index + 1)
        return ""


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


def _needs_ocr(
    text: str,
    tables: list[Table],
    img_ratio: float,
    min_chars: int,
    force: bool = False,
) -> bool:
    """Quyết định trang có cần OCR không.

    ``force=True`` (nhánh garbled): trả True ngay, BỎ QUA mọi short-circuit (kể cả ``_has_real_table``)
    — trang font-lỗi có bảng cũng garbled nên vẫn phải OCR. Mặc định ``force=False`` giữ nguyên hành vi
    cũ: cần OCR khi bật ngưỡng (min_chars>0) VÀ không có bảng-thật VÀ (text quá ít HOẶC ảnh phủ phần
    lớn trang trong khi text-layer mỏng). ``not _has_real_table`` để trang scan bị pdfplumber gán 'bảng
    rỗng' KHÔNG thoát OCR (lỗ hổng mất nội dung)."""
    if force:
        return True
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
        logger.warning(
            "pdfplumber: filter bảng lỗi ở trang %s, dùng text đầy đủ.",
            page.page_number,
        )
        return page.extract_text() or ""


def extract_with_tables(path: str, ocr_min_chars: int = 0) -> list[PageBlock]:
    """Đọc PDF → danh sách ``PageBlock`` (text-không-bảng + bảng) theo từng trang.

    ``ocr_min_chars`` > 0 → đánh dấu ``needs_ocr`` cho trang scan (text-layer dưới ngưỡng); 0 (mặc
    định) → bỏ qua phát hiện scan (giữ tương thích cũ).

    Mỗi trang xử lý phân tầng chống mojibake font tiếng Việt:
    NFC normalize → phát hiện garbled → PDFium retry (re-check) → quyết định needs_ocr / drop tables.
    Trang vẫn garbled sau retry: ``needs_ocr=True`` + ``tables=[]`` (bảng cũng garbled cùng font → để
    OCR Vision markdownize vào ``text``). Bật/tắt qua ``garbled_detect_enabled``; chỉ chạy khi OCR bật
    (``ocr_min_chars>0``) vì đích đến của trang garbled là đường OCR."""
    pages: list[PageBlock] = []
    garbled_routed = 0
    detect = settings.garbled_detect_enabled and ocr_min_chars > 0
    # Mở PDFium MỘT lần cho cả tài liệu (tránh parse lại file mỗi trang) — chỉ khi cần retry.
    pdfium_doc = pdfium.PdfDocument(path) if detect else None
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                found = page.find_tables()
                bboxes = [t.bbox for t in found]
                tables = [_normalize_table(t.extract()) for t in found]
                text = unicodedata.normalize(
                    "NFC", _text_outside_tables(page, bboxes).strip()
                )

                force_ocr = False
                if detect and _looks_garbled(text):
                    # Tầng rẻ: thử PDFium (engine khác) trước khi OCR Vision đắt.
                    cand = _pdfium_page_text(pdfium_doc, page.page_number - 1)
                    if cand and not _looks_garbled(cand):
                        text = cand  # CỨU được: PDFium đọc đúng → KHÔNG OCR.
                        tables = []  # PDFium không crop bảng → drop để tránh đếm 2 lần.
                    else:
                        force_ocr = True  # vẫn garbled → rơi xuống OCR Vision.
                        tables = []  # bảng cũng garbled → để OCR markdownize vào text.
                        garbled_routed += 1

                needs_ocr = _needs_ocr(
                    text, tables, _image_coverage(page), ocr_min_chars, force=force_ocr
                )
                pages.append(
                    PageBlock(
                        page_number=page.page_number,
                        text=text,
                        tables=tables,
                        needs_ocr=needs_ocr,
                    )
                )
    finally:
        if pdfium_doc is not None:
            pdfium_doc.close()

    if garbled_routed:
        # KHÔNG log nội dung (PII) — chỉ số đếm để chẩn đoán tỉ lệ trang font-lỗi.
        logger.info("extract: %s trang garbled (font lỗi) → route OCR.", garbled_routed)
    return pages


def page_count(path: str) -> int:
    """Số trang của PDF (không tải toàn bộ nội dung)."""
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)
