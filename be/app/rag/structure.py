"""Nhận diện cấu trúc phân cấp văn bản hành chính tiếng Việt bằng regex.

Cấu trúc: Phần A/B/C → Mục I/II/III → Điều N → Khoản (dấu ``-``) → Điểm (i)/(a).

``segment`` đi từng dòng, duy trì ngăn xếp tiêu đề (Phần/Mục/Điều/Phụ lục) và gom nội dung
thành các ``Section`` — mỗi Section là khối nội dung dưới MỘT ``heading_path`` (breadcrumb).
Khoản/Điểm KHÔNG phải tiêu đề → nằm trong ``Section.text`` (chunker mới cắt theo ranh giới Khoản).

Hàm thuần, không gọi mạng/LLM → dễ unit-test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.rag.extract import PageBlock

# Roman I–X tường minh (đề xuất gốc thiếu VII–X; alternation cố định tránh khớp rỗng).
_ROMAN = r"(?:I|II|III|IV|V|VI|VII|VIII|IX|X)"

STRUCTURE_PATTERNS: dict[str, re.Pattern] = {
    # Phụ lục: "Phụ lục 1", "Phụ lục 4a".
    "phu_luc": re.compile(r"^Phụ\s*lục\s+\d+[a-z]?\b", re.IGNORECASE),
    # Mục: "Mục III", hoặc roman đứng đầu "III." / "III)".
    "muc": re.compile(rf"^(?:Mục\s+{_ROMAN}\b|{_ROMAN}[.)]\s+\S)"),
    # Điều: "Điều 5", "Điều 5." (chuẩn QĐ/TT), hoặc số + tiêu đề HOA "5. NỘI DUNG".
    "dieu": re.compile(r"^(?:Điều\s+\d+\b|\d+\.\s+[A-ZĐÀ-Ỹ])"),
    # Phần: chữ HOA đơn + "." + tiêu đề viết HOA ("A. NHỮNG QUY ĐỊNH CHUNG").
    "phan": re.compile(r"^[A-Z]\.\s+\S"),
    # Điểm: "(i)", "(ii)", "(a)".
    "diem": re.compile(r"^\((?:[ivxIVX]+|[a-z])\)\s*"),
    # Khoản: gạch đầu dòng "- ...".
    "khoan": re.compile(r"^-\s+\S"),
}

# Cấp của tiêu đề trong breadcrumb (số nhỏ = cấp cao). Khoản/Điểm KHÔNG nằm đây (là nội dung).
HEADING_LEVELS: dict[str, int] = {"phan": 0, "phu_luc": 0, "muc": 1, "dieu": 2}


@dataclass
class Section:
    """Khối nội dung dưới một ``heading_path`` (breadcrumb đầy đủ)."""

    heading_path: list[str] = field(default_factory=list)
    text: str = ""
    page_number: int = 1


def _is_upperish(s: str) -> bool:
    """Phần lớn ký tự CHỮ trong chuỗi là HOA (bỏ qua số/dấu/space)."""
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    return sum(c.isupper() for c in letters) / len(letters) >= 0.6


def classify_line(line: str) -> str | None:
    """Phân loại MỘT dòng → loại cấu trúc, hoặc None nếu là nội dung/continuation.

    Thứ tự ưu tiên: phụ lục → mục (roman) → điều → phần → điểm → khoản. Mục đặt trước Phần vì
    roman "I."/"V."/"X." cũng khớp mẫu Phần ``[A-Z].``."""
    line = line.strip()
    if not line:
        return None
    if STRUCTURE_PATTERNS["phu_luc"].match(line):
        return "phu_luc"
    if STRUCTURE_PATTERNS["muc"].match(line):
        return "muc"
    if STRUCTURE_PATTERNS["dieu"].match(line):
        return "dieu"
    # Phần: cần phần tiêu đề viết HOA để tránh nhầm câu thường "A. xyz".
    if STRUCTURE_PATTERNS["phan"].match(line) and _is_upperish(line[2:].strip()):
        return "phan"
    if STRUCTURE_PATTERNS["diem"].match(line):
        return "diem"
    if STRUCTURE_PATTERNS["khoan"].match(line):
        return "khoan"
    return None


def segment(pages: list[PageBlock]) -> list[Section]:
    """Gom văn bản nhiều trang thành các ``Section`` theo ranh giới tiêu đề.

    Tiêu đề (Phần/Mục/Điều/Phụ lục) → đóng section đang gom rồi cập nhật breadcrumb. Khoản/Điểm và
    dòng thường → nội dung của section hiện hành. ``page_number`` = trang chứa dòng nội dung đầu tiên.
    """
    sections: list[Section] = []
    current: dict[int, str] = {}  # cấp → text tiêu đề
    cur_path: list[str] = []
    buf: list[str] = []
    buf_page: int | None = None

    def flush() -> None:
        nonlocal buf, buf_page
        text = "\n".join(buf).strip()
        if text:
            sections.append(
                Section(
                    heading_path=list(cur_path),
                    text=text,
                    page_number=buf_page or 1,
                )
            )
        buf = []
        buf_page = None

    for page in pages:
        for raw in page.text.split("\n"):
            line = raw.strip()
            if not line:
                continue
            kind = classify_line(line)
            if kind in HEADING_LEVELS:
                flush()
                lvl = HEADING_LEVELS[kind]
                current[lvl] = line
                for deeper in [d for d in current if d > lvl]:
                    del current[deeper]
                cur_path = [current[k] for k in sorted(current)]
            else:
                if buf_page is None:
                    buf_page = page.page_number
                buf.append(line)
    flush()
    return sections


def heading_path_for_page(sections: list[Section], page_number: int) -> list[str]:
    """Breadcrumb gần nhất áp dụng cho một trang (cho table node ở trang chỉ có bảng).

    Lấy ``heading_path`` của section bắt đầu ở trang <= ``page_number`` muộn nhất; [] nếu chưa có."""
    chosen: list[str] = []
    for sec in sections:
        if sec.page_number <= page_number:
            chosen = sec.heading_path
        else:
            break
    return chosen
