"""Test parse metadata từ TÊN FILE (app/rag/title_metadata.py) — theo quy ước data thật."""

from __future__ import annotations

from app.rag import title_metadata as tm
from app.rag.wards_data import canonical_ward, find_ward_in_text


def test_parse_year_all_formats():
    assert tm.parse_year("... 2026 - 2027 phường X") == "2026-2027"  # có gạch + space
    assert (
        tm.parse_year("..., năm học 2026 2027.pdf") == "2026-2027"
    )  # space, không gạch
    assert tm.parse_year("năm học 20262027") == "2026-2027"  # dính liền
    assert tm.parse_year("2026-2027") == "2026-2027"
    assert tm.parse_year("không có năm") is None


def test_parse_ward_pattern_year_then_ward():
    meta = tm.parse_title_metadata(
        "Kế hoạch huy động trẻ tuyển sinh 2026 - 2027 phường Bình Thạnh.pdf"
    )
    assert meta == {"school_year": "2026-2027", "ward": "Bình Thạnh"}


def test_parse_title_metadata_docx_extension():
    # Bỏ ĐUÔI .docx (Path.stem) → ward không bị kẹt ".docx".
    meta = tm.parse_title_metadata(
        "Kế hoạch huy động trẻ tuyển sinh 2026 - 2027 phường Tân Bình.docx"
    )
    assert meta == {"school_year": "2026-2027", "ward": "Tân Bình"}


def test_parse_ward_pattern_quyet_dinh_with_comma():
    name = (
        "QUYẾT ĐỊNH Phê duyệt Kế hoạch huy động trẻ ra lớp và tuyển sinh vào các "
        "lớp đầu cấp trên địa bàn phường An Phú Đông, năm học 2026 2027.pdf"
    )
    meta = tm.parse_title_metadata(name)
    assert meta["ward"] == "An Phú Đông"  # tên nhiều chữ, dừng ở dấu phẩy
    assert meta["school_year"] == "2026-2027"


def test_parse_ward_xa_and_dac_khu():
    assert (
        tm.parse_title_metadata("... 2026 - 2027 xã Phước Hòa.pdf")["ward"]
        == "Phước Hòa"
    )
    name = "QUYẾT ĐỊNH ... trên địa bàn đặc khu Côn Đảo, năm học 2026 2027.pdf"
    assert tm.parse_title_metadata(name)["ward"] == "Côn Đảo"


def test_parse_ward_none_when_no_locality():
    meta = tm.parse_title_metadata(
        "Huy động trẻ ra lớp và tuyển sinh vào các lớp đầu cấp Hội Đông.pdf"
    )
    assert meta["ward"] is None  # không có từ khóa phường/xã/đặc khu
    assert meta["school_year"] is None


def test_canonical_ward_case_insensitive():
    assert canonical_ward("bình thạnh") == "Bình Thạnh"  # canonical hóa theo whitelist
    assert canonical_ward("KHÔNG TỒN TẠI") is None


def test_find_ward_in_text_for_question():
    # Câu hỏi free-form, có/không có từ khóa "phường".
    assert (
        find_ward_in_text("hồ sơ tuyển sinh phường Bình Thạnh cần gì?") == "Bình Thạnh"
    )
    assert find_ward_in_text("tuyển sinh ở bình hưng hòa năm nay") == "Bình Hưng Hòa"
    # Ưu tiên tên DÀI nhất (Bình Hưng Hòa, không phải Bình Hưng).
    assert find_ward_in_text("bình hưng hòa") == "Bình Hưng Hòa"
    # "xã hội hóa" KHÔNG được nhận nhầm là xã (không có tên whitelist khớp).
    assert find_ward_in_text("chủ trương xã hội hóa giáo dục") is None
    assert find_ward_in_text("câu hỏi chung không nêu địa bàn") is None
