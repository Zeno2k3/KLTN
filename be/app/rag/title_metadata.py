"""Parse metadata cấp văn bản TỪ TÊN FILE (title): năm học + phường/xã. Hàm THUẦN (không mạng/LLM).

Người dùng đặt tên file nhất quán mỗi batch (xem memory doc-title-metadata-convention) → parse từ
title đáng tin hơn trích từ nội dung. Năm học chuẩn hóa ``YYYY-YYYY``; địa bàn GIỮ NGUYÊN cấp
phường/xã (không quy về quận/huyện — bối cảnh cải cách hành chính 2025).

Quy ước tên file quan sát được (data thật):
- ``…tuyển sinh 2026 - 2027 phường <Tên>.pdf`` / ``… xã <Tên>.pdf`` (năm có gạch, tên ở cuối)
- ``…trên địa bàn phường <Tên>, năm học 2026 2027.pdf`` (năm KHÔNG gạch, tên giữa "địa bàn …" và ',')
- năm dính liền ``20262027``; có cả prefix ``đặc khu`` (Côn Đảo); vài file thiếu phường/xã/năm → None.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.rag.wards_data import canonical_ward

# Năm học: "2026 - 2027", "2026 2027", "2026-2027", hoặc dính liền "20262027".
_YEAR_RE = re.compile(r"(20\d{2})\s*[-–]?\s*(20\d{2})")
# Tên phường/xã/đặc khu: sau từ khóa, dừng ở dấu phẩy / "năm" / chữ số / .pdf / hết chuỗi.
_WARD_RE = re.compile(
    r"(?:phường|xã|đặc\s+khu)\s+(.+?)(?=\s*,|\s+năm\b|\s*\d|\.pdf|$)",
    re.IGNORECASE,
)


def _norm(s: str) -> str:
    """NFC + gộp khoảng trắng + strip (giữ nguyên hoa/thường)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def parse_year(text: str | None) -> str | None:
    """Năm học → "YYYY-YYYY"; None nếu không thấy."""
    m = _YEAR_RE.search(text or "")
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def parse_ward(text: str | None) -> str | None:
    """Tên phường/xã/đặc khu (giữ nguyên cấp), None nếu không thấy từ khóa địa bàn."""
    if not text:
        return None
    m = _WARD_RE.search(text)
    if not m:
        return None
    name = _norm(m.group(1))
    if not name:
        return None
    # Canonical theo whitelist (đảm bảo cùng casing với giá trị query-time → EQ filter khớp);
    # tên lạ (ngoài whitelist) vẫn giữ nguyên để không mất dữ liệu.
    return canonical_ward(name) or name


def parse_title_metadata(name: str | None) -> dict:
    """Trả {"school_year": "YYYY-YYYY"|None, "ward": str|None} từ tên file (bỏ đuôi: .pdf/.docx/…)."""
    stem = Path(name).stem if name else ""
    return {"school_year": parse_year(stem), "ward": parse_ward(stem)}
