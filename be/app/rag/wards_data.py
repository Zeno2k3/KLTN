"""Whitelist phường/xã/đặc khu — SINH TỪ corpus thật (158 file tuyển sinh 2026-2027).

Mục đích: canonical hóa (case-insensitive) khi parse từ tên file, và nhận diện địa bàn trong CÂU HỎI
người dùng (substring, ưu tiên tên dài nhất) — tránh false-positive kiểu "xã hội" và bắt được câu
không có từ khóa "phường".

Khi corpus đổi (năm học mới / sáp nhập phường), CHẠY LẠI script sinh whitelist từ thư mục data và
cập nhật tập này. (Phương án tự bảo trì: lấy ``distinct(Document.ward)`` từ DB — để sau.)
"""

from __future__ import annotations

WARD_WHITELIST: frozenset[str] = frozenset(
    {
        "An Khánh",
        "An Long",
        "An Nhơn",
        "An Nhơn Tây",
        "An Phú",
        "An Phú Đông",
        "An Đông",
        "Bà Rịa",
        "Bà Điểm",
        "Bàn Cờ",
        "Bàu Bàng",
        "Bàu Lâm",
        "Bình Chánh",
        "Bình Châu",
        "Bình Cơ",
        "Bình Dương",
        "Bình Giã",
        "Bình Hưng",
        "Bình Hưng Hòa",
        "Bình Khánh",
        "Bình Lợi",
        "Bình Lợi Trung",
        "Bình Phú",
        "Bình Qưới",
        "Bình Thạnh",
        "Bình Thới",
        "Bình Tiên",
        "Bình Trưng",
        "Bình Trị Đông",
        "Bình Tân",
        "Bình Tây",
        "Bình Đông",
        "Bảy Hiền",
        "Bắc Tân Uyên",
        "Bến Cát",
        "Bến Thành",
        "Chánh Hiệp",
        "Chánh Hưng",
        "Chánh Phú Hòa",
        "Châu Pha",
        "Châu Đức",
        "Chợ Lớn",
        "Chợ Quán",
        "Cát Lái",
        "Côn Đảo",
        "Cần Giờ",
        "Cầu Kiệu",
        "Cầu Ông Lãnh",
        "Củ Chi",
        "Diên Hồng",
        "Dĩ An",
        "Dầu Tiếng",
        "Gia Định",
        "Gò Vấp",
        "Hiệp Bình",
        "Hiệp Phước",
        "Hòa Bình",
        "Hòa Hiệp",
        "Hòa Hưng",
        "Hòa Hội",
        "Hòa Lợi",
        "Hóc Môn",
        "Hưng Long",
        "Hạnh Thông",
        "Hồ Tràm",
        "Hội Tây",
        "Khánh Hội",
        "Linh Xuân",
        "Long Hòa",
        "Long Hương",
        "Long Hải",
        "Long Nguyên",
        "Long Phước",
        "Long Sơn",
        "Long Trường",
        "Long Điền",
        "Lái Thiêu",
        "Minh Phụng",
        "Minh Thạnh",
        "Ngãi Giao",
        "Nhiêu Lộc",
        "Nhuận Đức",
        "Nhà Bè",
        "Phú An",
        "Phú Giáo",
        "Phú Hòa Đông",
        "Phú Lâm",
        "Phú Lợi",
        "Phú Mỹ",
        "Phú Nhuận",
        "Phú Thuận",
        "Phú Thạnh",
        "Phú Thọ",
        "Phú Định",
        "Phước Hòa",
        "Phước Hải",
        "Phước Long",
        "Phước Thành",
        "Phước Thắng",
        "Sài Gòn",
        "Tam Bình",
        "Tam Long",
        "Tam Thắng",
        "Thanh An",
        "Thuận An",
        "Thuận Giao",
        "Thái Mỹ",
        "Thông Tây Hội",
        "Thường Tân",
        "Thạch An",
        "Thạnh Mỹ Tây",
        "Thọ Hòa",
        "Thới An",
        "Thới Hòa",
        "Thủ Dầu Một",
        "Thủ Đức",
        "Trung Mỹ Tây",
        "Trừ Văn Thố",
        "Tân An Hội",
        "Tân Bình",
        "Tân Hiệp",
        "Tân Hòa",
        "Tân Hưng",
        "Tân Hải",
        "Tân Khánh",
        "Tân Mỹ",
        "Tân Nhựt",
        "Tân Phú",
        "Tân Phước",
        "Tân Sơn",
        "Tân Sơn Hòa",
        "Tân Sơn Nhì",
        "Tân Sơn Nhất",
        "Tân Thuận",
        "Tân Thành",
        "Tân Thới Hiệp",
        "Tân Tạo",
        "Tân Vĩnh Lộc",
        "Tân Đông Hiệp",
        "Tân Định",
        "Tây Nam",
        "Tây Thạnh",
        "Tăng Nhơn Phú",
        "Vĩnh Hội",
        "Vĩnh Lộc",
        "Vĩnh Tân",
        "Vũng Tàu",
        "Vườn Lài",
        "Xuyên Mộc",
        "Xuân Hòa",
        "Xóm Chiếu",
        "Đông Hòa",
        "Đông Hưng Thuận",
        "Đông Thạnh",
        "Đất Đỏ",
        "Đức Nhuận",
    }
)

# Tra cứu canonical theo casefold (case-insensitive). Sắp dài→ngắn để match tên dài trước
# (vd "Bình Hưng Hòa" trước "Bình Hưng").
_BY_CASEFOLD: dict[str, str] = {w.casefold(): w for w in WARD_WHITELIST}
_SORTED_DESC: list[str] = sorted(WARD_WHITELIST, key=len, reverse=True)


def canonical_ward(name: str | None) -> str | None:
    """Map tên đã parse → dạng canonical trong whitelist (khớp casefold chính xác); None nếu lạ."""
    if not name:
        return None
    return _BY_CASEFOLD.get(name.strip().casefold())


def find_ward_in_text(text: str | None) -> str | None:
    """Tìm phường/xã (whitelist) xuất hiện trong ``text`` (case-insensitive), ưu tiên tên DÀI nhất.

    Dùng cho CÂU HỎI người dùng (free-form, có thể thiếu từ khóa 'phường') — tránh false-positive
    'xã hội' vì chỉ khớp đúng tên trong whitelist."""
    if not text:
        return None
    low = text.casefold()
    for ward in _SORTED_DESC:
        if ward.casefold() in low:
            return ward
    return None
