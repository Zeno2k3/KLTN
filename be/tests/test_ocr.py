"""Test tầng OCR fallback (PDF scan) — logic thuần + mock vision-LLM (không gọi mạng).

Ràng buộc kiểm: phát hiện trang scan đúng; cap → raise (ingest failed); lỗi 1 trang không sập cả
lượt; chỉ ghi đè text khi OCR non-empty; trang không cần OCR giữ nguyên.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.rag import ocr
from app.rag.extract import PageBlock, _needs_ocr

_REAL_TABLE = [[["Khoản mục", "Số tiền"], ["Học phí", "500000"]]]
_EMPTY_TABLE = [[["", None], [None, ""]]]  # pdfplumber bắt nhầm trên trang scan


# --------------------------------------------------------------------------- #
# Phát hiện trang scan
# --------------------------------------------------------------------------- #
def test_needs_ocr_detection():
    # Text ngắn, không bảng → cần OCR.
    assert _needs_ocr("vài chữ", [], 0.0, 50) is True
    # Text dài → không cần.
    assert _needs_ocr("x" * 200, [], 0.0, 50) is False
    # Text ngắn nhưng có BẢNG THẬT → không OCR (là trang bảng số, không phải scan).
    assert _needs_ocr("ngắn", _REAL_TABLE, 0.0, 50) is False
    # Bảng RỖNG (pdfplumber bắt nhầm trên scan) → vẫn OCR (không bị 'bảng rỗng' chặn).
    assert _needs_ocr("ngắn", _EMPTY_TABLE, 0.0, 50) is True
    # Ảnh phủ lớn + text-layer mỏng (watermark) dù > min_chars → vẫn OCR.
    assert _needs_ocr("x" * 120, [], 0.7, 50) is True
    # min_chars=0 (tắt phát hiện) → không bao giờ OCR.
    assert _needs_ocr("", [], 0.9, 0) is False


# --------------------------------------------------------------------------- #
# ocr_pages: ghi đè text, cap, skip lỗi
# --------------------------------------------------------------------------- #
class _FakePdf:
    def __init__(self, path):  # noqa: D401, ANN001
        pass

    def close(self):
        pass


def _patch_render(monkeypatch):
    monkeypatch.setattr(ocr.pdfium, "PdfDocument", _FakePdf)
    monkeypatch.setattr(ocr, "render_page_png", lambda pdf, idx, dpi: b"PNG")


def test_ocr_pages_fills_only_targets(monkeypatch):
    _patch_render(monkeypatch)
    monkeypatch.setattr(ocr, "ocr_page_image", lambda png: "VĂN BẢN OCR")
    pages = [
        PageBlock(page_number=1, text="", needs_ocr=True),
        PageBlock(page_number=2, text="đã có text-layer", needs_ocr=False),
    ]
    out = ocr.ocr_pages("x.pdf", pages)
    assert out[0].text == "VĂN BẢN OCR"  # trang scan được điền
    assert out[1].text == "đã có text-layer"  # trang thường giữ nguyên


def test_ocr_pages_empty_result_keeps_original(monkeypatch):
    _patch_render(monkeypatch)
    monkeypatch.setattr(ocr, "ocr_page_image", lambda png: "")  # OCR ra rỗng
    pages = [PageBlock(page_number=1, text="cũ", needs_ocr=True)]
    out = ocr.ocr_pages("x.pdf", pages)
    assert out[0].text == "cũ"  # KHÔNG ghi đè bằng chuỗi rỗng


def test_ocr_pages_cap_raises(monkeypatch):
    _patch_render(monkeypatch)
    monkeypatch.setattr(ocr, "ocr_page_image", lambda png: "x")
    monkeypatch.setattr(settings, "ocr_max_pages", 1)
    pages = [
        PageBlock(page_number=1, text="", needs_ocr=True),
        PageBlock(page_number=2, text="", needs_ocr=True),
    ]
    with pytest.raises(ValueError, match="vượt trần"):
        ocr.ocr_pages("x.pdf", pages)


def test_ocr_pages_one_error_does_not_crash(monkeypatch):
    _patch_render(monkeypatch)
    seq = iter(["", "TRANG 2 OK"])  # trang 1 OCR rỗng, trang 2 ổn
    monkeypatch.setattr(ocr, "ocr_page_image", lambda png: next(seq))
    pages = [
        PageBlock(page_number=1, text="cũ1", needs_ocr=True),
        PageBlock(page_number=2, text="cũ2", needs_ocr=True),
    ]
    out = ocr.ocr_pages("x.pdf", pages)
    assert out[0].text == "cũ1"  # rỗng → giữ nguyên
    assert out[1].text == "TRANG 2 OK"  # vẫn OCR được dù trang trước "hỏng"


def test_ocr_page_image_returns_empty_on_llm_error(monkeypatch):
    class _Boom:
        def chat(self, messages):
            raise RuntimeError("vision API sập")

    monkeypatch.setattr(ocr, "_get_llm", lambda: _Boom())
    assert ocr.ocr_page_image(b"PNG") == ""  # lỗi → "" (không raise)


def test_ocr_page_image_success(monkeypatch):
    resp = SimpleNamespace(message=SimpleNamespace(content="  Điều 1. Nội dung  "))
    monkeypatch.setattr(ocr, "_get_llm", lambda: SimpleNamespace(chat=lambda m: resp))
    assert ocr.ocr_page_image(b"PNG") == "Điều 1. Nội dung"


def test_ocr_strips_code_fence(monkeypatch):
    # vision-LLM hay bọc output trong ```...``` → phải bị loại khỏi nội dung.
    resp = SimpleNamespace(
        message=SimpleNamespace(content="```markdown\nĐiều 1. Hồ sơ\n- Giấy khai sinh\n```")
    )
    monkeypatch.setattr(ocr, "_get_llm", lambda: SimpleNamespace(chat=lambda m: resp))
    assert ocr.ocr_page_image(b"PNG") == "Điều 1. Hồ sơ\n- Giấy khai sinh"
