"""Test structure-aware + LLM chunker (hàm thuần; LLM được mock — không gọi mạng).

Tập trung các RÀNG BUỘC CỨNG:
- Không bao giờ cắt giữa Khoản; Khoản dài vẫn là một chunk.
- Bảng luôn là node độc lập (has_table=True), không lẫn vào text node.
- LLM lỗi/không hợp lệ → fallback rule-based, nội dung được bảo toàn verbatim.
- context được prepend vào node.text; content lưu DB là nguyên văn (không kèm context).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.core.config import settings
from app.rag import chunker
from app.rag.extract import PageBlock
from app.rag.structure import Section, classify_line, segment

DOC_META = {"doc_name": "Kế hoạch tuyển sinh 2025", "doc_type": "ke_hoach"}

_THREE_KHOAN = (
    "- Giấy khai sinh bản sao có công chứng theo quy định hiện hành của pháp luật Việt Nam.\n"
    "- Sổ hộ khẩu hoặc giấy tờ chứng minh nơi cư trú hợp lệ của học sinh tại địa bàn tuyển sinh.\n"
    "- Đơn đăng ký dự tuyển theo mẫu do nhà trường ban hành và hướng dẫn phụ huynh kê khai."
)


class _FakeResp:
    def __init__(self, content: str):
        self.message = SimpleNamespace(content=content)


class _FakeLLM:
    def __init__(self, content: str | None = None, exc: Exception | None = None):
        self._content = content
        self._exc = exc

    def chat(self, messages):  # noqa: ANN001 — chữ ký tối thiểu cho mock
        if self._exc is not None:
            raise self._exc
        return _FakeResp(self._content)


# --------------------------------------------------------------------------- #
# structure
# --------------------------------------------------------------------------- #
def test_structure_classify():
    assert classify_line("Phụ lục 4a") == "phu_luc"
    assert classify_line("Mục III") == "muc"
    assert classify_line("VII. Điều khoản thi hành") == "muc"  # roman VII–X
    assert classify_line("X. Tổ chức thực hiện") == "muc"
    assert classify_line("Điều 5. Hồ sơ tuyển sinh") == "dieu"
    assert classify_line("A. NHỮNG QUY ĐỊNH CHUNG") == "phan"
    assert classify_line("(i) trường hợp đúng tuyến") == "diem"
    assert classify_line("- Giấy khai sinh bản sao") == "khoan"
    assert classify_line("Đây là câu nội dung bình thường.") is None


def test_segment_builds_heading_path():
    pages = [PageBlock(page_number=1, text="Điều 5. Hồ sơ tuyển sinh\n" + _THREE_KHOAN)]
    sections = segment(pages)
    assert len(sections) == 1
    assert sections[0].heading_path == ["Điều 5. Hồ sơ tuyển sinh"]
    assert sections[0].text.count("\n- ") == 2  # 3 khoản


# --------------------------------------------------------------------------- #
# Khoản nguyên tử
# --------------------------------------------------------------------------- #
def test_rule_based_split_never_breaks_khoan(monkeypatch):
    monkeypatch.setattr(settings, "chunk_llm_enabled", False)  # ép rule-based
    monkeypatch.setattr(settings, "chunk_size", 20)  # ngưỡng nhỏ → buộc tách nhiều chunk
    section = Section(heading_path=["Điều 5"], text=_THREE_KHOAN, page_number=1)

    chunks = [c for c, _ctx, _t in chunker.chunk_section(section, DOC_META)]

    assert len(chunks) >= 2  # đã tách
    blocks = chunker.split_into_khoan_blocks(_THREE_KHOAN)
    assert len(blocks) == 3
    # Mỗi Khoản phải nằm TRỌN trong đúng một chunk (không bị cắt đôi).
    for block in blocks:
        assert sum(block in c for c in chunks) == 1


def test_long_single_khoan_stays_one_chunk(monkeypatch):
    monkeypatch.setattr(settings, "chunk_llm_enabled", False)
    monkeypatch.setattr(settings, "chunk_size", 20)
    long_khoan = "- " + ("nội dung rất dài của một khoản duy nhất " * 50).strip()
    section = Section(heading_path=["Điều 9"], text=long_khoan, page_number=1)

    chunks = list(chunker.chunk_section(section, DOC_META))

    assert len(chunks) == 1  # Khoản nguyên tử dù vượt chunk_size
    assert chunks[0][0] == long_khoan


# --------------------------------------------------------------------------- #
# Bảng độc lập
# --------------------------------------------------------------------------- #
def test_table_is_independent_node(monkeypatch):
    monkeypatch.setattr(settings, "chunk_llm_enabled", False)
    pages = [
        PageBlock(
            page_number=1,
            text="Điều 1. Học phí\n- Mức học phí năm học 2025 theo bảng dưới đây.",
            tables=[[["Khoản mục", "Số tiền"], ["Học phí", "500000"]]],
        )
    ]
    nodes = chunker.build_nodes(pages, document_id=7, filename="hp.pdf", doc_meta=DOC_META)

    tables = [n for n in nodes if n.has_table]
    texts = [n for n in nodes if not n.has_table]
    assert len(tables) == 1
    assert tables[0].chunk_type == "table"
    assert "|" in tables[0].node.text and "Học phí" in tables[0].node.text
    # Markdown bảng KHÔNG được lẫn vào bất kỳ text node nào.
    assert all("| ---" not in t.node.text for t in texts)
    assert all(t.has_table is False for t in texts)


# --------------------------------------------------------------------------- #
# LLM grouping + fallback + fidelity
# --------------------------------------------------------------------------- #
def test_llm_chunker_groups_and_keeps_content_verbatim(monkeypatch):
    monkeypatch.setattr(settings, "chunk_llm_enabled", True)
    monkeypatch.setattr(settings, "chunk_llm_min_tokens", 1)  # luôn kích LLM
    blocks = chunker.split_into_khoan_blocks(_THREE_KHOAN)
    payload = json.dumps(
        [
            {"blocks": [0, 1], "context": "Hồ sơ tuyển sinh — phần giấy tờ.", "chunk_type": "list"},
            {"blocks": [2], "context": "Hồ sơ tuyển sinh — đơn đăng ký.", "chunk_type": "text"},
        ]
    )
    monkeypatch.setattr(chunker, "_get_llm", lambda: _FakeLLM(content=payload))
    section = Section(heading_path=["Điều 5"], text=_THREE_KHOAN, page_number=1)

    out = chunker.chunk_section(section, DOC_META)

    assert len(out) == 2
    # content GHÉP từ block verbatim (không lấy từ text LLM).
    assert out[0][0] == blocks[0] + "\n" + blocks[1]
    assert out[1][0] == blocks[2]
    assert out[0][1] == "Hồ sơ tuyển sinh — phần giấy tờ."  # context của LLM


def test_llm_chunker_fallback_on_error(monkeypatch):
    monkeypatch.setattr(settings, "chunk_llm_enabled", True)
    monkeypatch.setattr(settings, "chunk_llm_min_tokens", 1)
    monkeypatch.setattr(settings, "chunk_size", 20)
    monkeypatch.setattr(
        chunker, "_get_llm", lambda: _FakeLLM(exc=RuntimeError("LLM sập"))
    )
    section = Section(heading_path=["Điều 5"], text=_THREE_KHOAN, page_number=1)

    chunks = [c for c, _ctx, _t in chunker.chunk_section(section, DOC_META)]

    assert chunks  # vẫn ra chunk (fallback rule-based)
    for block in chunker.split_into_khoan_blocks(_THREE_KHOAN):
        assert sum(block in c for c in chunks) == 1  # nội dung bảo toàn, không cắt Khoản


def test_llm_chunker_fallback_on_invalid_partition(monkeypatch):
    monkeypatch.setattr(settings, "chunk_llm_enabled", True)
    monkeypatch.setattr(settings, "chunk_llm_min_tokens", 1)
    # Phân hoạch THIẾU block 2 → không phủ hết → phải fallback (giữ nguyên nội dung).
    bad = json.dumps([{"blocks": [0, 1], "context": "x"}])
    monkeypatch.setattr(chunker, "_get_llm", lambda: _FakeLLM(content=bad))
    section = Section(heading_path=["Điều 5"], text=_THREE_KHOAN, page_number=1)

    chunks = [c for c, _ctx, _t in chunker.chunk_section(section, DOC_META)]

    full = "\n".join(chunks)
    for block in chunker.split_into_khoan_blocks(_THREE_KHOAN):
        assert block in full  # không mất block nào


# --------------------------------------------------------------------------- #
# Metadata + contextual prepend
# --------------------------------------------------------------------------- #
def test_node_metadata_complete(monkeypatch):
    monkeypatch.setattr(settings, "chunk_llm_enabled", False)
    pages = [PageBlock(page_number=3, text="Điều 2. Đối tượng\n" + _THREE_KHOAN)]
    nodes = chunker.build_nodes(pages, document_id=11, filename="kh.pdf", doc_meta=DOC_META)

    assert nodes
    for n in nodes:
        md = n.node.metadata
        assert md["document_id"] == 11
        assert "heading_path" in md and md["heading_path"]
        assert md["chunk_type"] in {"text", "list", "mixed", "table"}
        assert md["page_number"] == 3


def test_context_prepended_to_text(monkeypatch):
    monkeypatch.setattr(settings, "chunk_llm_enabled", False)
    pages = [PageBlock(page_number=1, text="Điều 2. Đối tượng\n" + _THREE_KHOAN)]
    nodes = chunker.build_nodes(pages, document_id=1, filename="kh.pdf", doc_meta=DOC_META)

    n = nodes[0]
    assert n.context  # có context xác định từ heading
    assert n.node.text.startswith(n.context)  # context đã prepend vào vector text
    assert n.context not in n.content  # content lưu DB là NGUYÊN VĂN (không kèm context)
