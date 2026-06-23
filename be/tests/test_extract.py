"""Test tầng trích xuất PDF — phát hiện mojibake font tiếng Việt + chuẩn hóa NFC + route OCR.

Toàn bộ là hàm THUẦN (không gọi mạng/LLM). Ràng buộc kiểm:
- ``_looks_garbled``: tiếng Việt sạch → False; mojibake (PUA/symbol/scramble) → True; gate độ dài và
  bảng-số chống false-positive.
- ``_normalize_table``: NFC hợp nhất diacritic tách rời, giữ ``None``.
- ``_needs_ocr(force=True)``: bỏ qua short-circuit bảng (trang font-lỗi vẫn phải OCR).
- ``extract_with_tables``: trang garbled → ``needs_ocr=True`` + drop ``tables``; PDFium retry cứu được
  trang → KHÔNG OCR.
"""

from __future__ import annotations

import unicodedata

from app.rag import extract
from app.rag.extract import _looks_garbled, _needs_ocr, _normalize_table

# Một bảng "thật" (có ô không rỗng) — dùng kiểm short-circuit của _needs_ocr.
_REAL_TABLE = [[["Khoản mục", "Số tiền"], ["Học phí", "500000"]]]

# Đoạn văn hành chính tiếng Việt THẬT (>200 ký tự, dày stopword "của/các/có/trong/được/không…").
_CLEAN_VI = (
    "Ủy ban nhân dân thành phố ban hành kế hoạch tuyển sinh lớp một năm học này. "
    "Các trường tiểu học trên địa bàn có trách nhiệm tiếp nhận hồ sơ của học sinh "
    "trong độ tuổi quy định. Phụ huynh cần nộp đầy đủ giấy tờ theo hướng dẫn để được "
    "xét tuyển vào trường đúng tuyến. Nhà trường không được thu thêm bất kỳ khoản phí "
    "nào ngoài quy định của thành phố này."
)


# --------------------------------------------------------------------------- #
# _looks_garbled — tiếng Việt sạch KHÔNG bị nghi
# --------------------------------------------------------------------------- #
def test_looks_garbled_clean_vietnamese_false():
    assert len(_CLEAN_VI) >= 200
    assert _looks_garbled(_CLEAN_VI) is False


# --------------------------------------------------------------------------- #
# _looks_garbled — các kiểu mojibake đều bị bắt
# --------------------------------------------------------------------------- #
def test_looks_garbled_symbol_heavy_true():
    # VNI/TCVN3 map dấu sang ký hiệu lạ (¬ ® © « » ¨) → tỉ lệ symbol cao bất thường.
    garble = "abc¬®©«»¨ def¬®©«»¨ " * 12
    assert len(garble) >= 200
    assert _looks_garbled(garble) is True


def test_looks_garbled_pua_chars_true():
    # Subset-font thiếu ToUnicode → glyph rơi vào Private Use Area (rác chắc chắn).
    pua = " abc  def " * 16
    assert len(pua) >= 200
    assert _looks_garbled(pua) is True


def test_looks_garbled_scrambled_words_true():
    # Chữ bị scramble thành từ vô nghĩa (không trúng stopword nào) dù không có ký tự lạ.
    scrambled = "blorp fnusk gwemp hkruvd zlonti pwasq rtmexu vbnoik " * 5
    assert len(scrambled) >= 200
    assert _looks_garbled(scrambled) is True


def test_looks_garbled_diacritics_stripped_true():
    # LỖI FONT PHỔ BIẾN NHẤT (quan sát thực tế): glyph có dấu map về ASCII trần — vẫn là tiếng Việt
    # (nhiều "va/cac/cua/trong/co/theo") nhưng ~0% ký tự dấu → phải bị bắt và route OCR.
    folded = (
        "CONG HOA XA HOI CHU NGHIA VIET NAM Doc lap Tu do Hanh phuc. KE HOACH huy dong "
        "tre ra lop va tuyen sinh vao cac lop dau cap nam hoc nay. Cac truong tieu hoc tren "
        "dia ban co trach nhiem tiep nhan ho so cua hoc sinh trong do tuoi quy dinh theo "
        "huong dan cua thanh pho va cac van ban co lien quan den cong tac tuyen sinh dau cap."
    )
    assert len(folded) >= 200
    assert _looks_garbled(folded) is True


# --------------------------------------------------------------------------- #
# _looks_garbled — chống false-positive
# --------------------------------------------------------------------------- #
def test_looks_garbled_short_text_false():
    # Dù trông lạ nhưng dưới gate độ dài (200) → KHÔNG kết luận garbled.
    assert _looks_garbled("®®®®® ¬¬¬¬¬ ©©©©©") is False


def test_looks_garbled_number_table_false():
    # Phần text còn lại sau khi tách bảng: chủ yếu số, ít từ → không kích tín hiệu nào.
    numbers = " ".join(str(i) for i in range(1, 80))
    assert len(numbers) >= 200
    assert _looks_garbled(numbers) is False


# --------------------------------------------------------------------------- #
# _normalize_table — NFC hợp nhất diacritic tách rời
# --------------------------------------------------------------------------- #
def test_normalize_table_nfc():
    nfd = unicodedata.normalize("NFD", "Học phí")
    assert not unicodedata.is_normalized("NFC", nfd)  # đầu vào ở dạng tách (NFD)
    out = _normalize_table([[nfd, None], ["Đối tượng", "2025"]])
    assert out[0][0] == "Học phí"  # đã hợp nhất về codepoint dựng sẵn
    assert unicodedata.is_normalized("NFC", out[0][0])
    assert out[0][1] is None  # ô None giữ nguyên


# --------------------------------------------------------------------------- #
# _needs_ocr — force bypass short-circuit bảng
# --------------------------------------------------------------------------- #
def test_needs_ocr_force_bypasses_table():
    # Trang font-lỗi có bảng (cũng garbled): force=True → vẫn OCR dù _has_real_table.
    assert _needs_ocr("x" * 300, _REAL_TABLE, 0.0, 50, force=True) is True
    # force=False (mặc định) giữ hành vi cũ: có bảng thật → không OCR.
    assert _needs_ocr("x" * 300, _REAL_TABLE, 0.0, 50, force=False) is False


# --------------------------------------------------------------------------- #
# extract_with_tables — luồng phân tầng (fakes, không đọc PDF thật)
# --------------------------------------------------------------------------- #
class _FakeTable:
    def __init__(self, grid):
        self.bbox = (0.0, 0.0, 10.0, 10.0)
        self._grid = grid

    def extract(self):
        return self._grid


class _FakePage:
    def __init__(self, grid):
        self.page_number = 1
        self.width = 600
        self.height = 800
        self.images = []
        self._grid = grid

    def find_tables(self):
        return [_FakeTable(self._grid)]


class _FakePdfplumber:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakePdfiumDoc:
    def close(self):
        pass


def _patch_pdf_layer(monkeypatch, page):
    monkeypatch.setattr(
        extract.pdfplumber, "open", lambda path: _FakePdfplumber([page])
    )
    monkeypatch.setattr(extract.pdfium, "PdfDocument", lambda path: _FakePdfiumDoc())
    monkeypatch.setattr(extract, "_image_coverage", lambda pg: 0.0)


def test_garbled_page_sets_needs_ocr_and_drops_tables(monkeypatch):
    page = _FakePage([["Khoản", "Số"], ["Học phí", "500000"]])
    _patch_pdf_layer(monkeypatch, page)
    monkeypatch.setattr(
        extract, "_text_outside_tables", lambda pg, bb: "đoạn nghi ngờ lỗi font"
    )
    monkeypatch.setattr(extract, "_looks_garbled", lambda text: True)
    monkeypatch.setattr(extract, "_pdfium_page_text", lambda pdf, idx: "")  # retry fail

    pages = extract.extract_with_tables("x.pdf", ocr_min_chars=50)

    assert pages[0].needs_ocr is True  # vẫn garbled → route OCR
    assert pages[0].tables == []  # bảng garbled bị drop (OCR sẽ markdownize)


def test_pdfium_retry_rescues_page(monkeypatch):
    page = _FakePage([["Khoản", "Số"], ["Học phí", "500000"]])
    _patch_pdf_layer(monkeypatch, page)
    rescued = "Nội dung tiếng Việt sạch sau khi PDFium đọc lại đúng toàn bộ trang một cách rõ ràng."
    monkeypatch.setattr(
        extract, "_text_outside_tables", lambda pg, bb: "GARBLED original text"
    )
    # garbled cho text gốc, sạch cho ứng viên PDFium.
    monkeypatch.setattr(extract, "_looks_garbled", lambda text: "GARBLED" in text)
    monkeypatch.setattr(extract, "_pdfium_page_text", lambda pdf, idx: rescued)

    pages = extract.extract_with_tables("x.pdf", ocr_min_chars=50)

    assert pages[0].needs_ocr is False  # PDFium cứu được → KHÔNG OCR
    assert pages[0].text == rescued  # dùng bản PDFium
    assert pages[0].tables == []  # PDFium không crop bảng → drop tránh đếm 2 lần
