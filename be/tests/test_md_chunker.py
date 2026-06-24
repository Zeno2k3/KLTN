"""Test app/rag/md_chunker.py — LLM chunk markdown LlamaParse.

Logic thuần (validate phân hoạch, gộp, ghép verbatim, bảng→grid, ref_doc_id, excluded keys) test
CHẠY THẬT offline trên dữ liệu thật. Đường LLM dùng output JSON CÓ KIỂM SOÁT (không bịa thành công):
chỉ kiểm code GHÉP/validate đúng — đường gọi LLM thật nghiệm thu ở bước ingest thật."""

from types import SimpleNamespace

import pytest
from llama_index.core.schema import NodeRelationship

from app.rag import md_chunker
from app.rag.md_chunker import _doc_ref_id, _merge_block_texts, _validate_partition
from app.rag.parse import ParsedBlock, ParsedPage


def _page(page_number, blocks):
    return ParsedPage(page_number=page_number, md="", blocks=blocks)


def _h(value, lvl=1):
    return ParsedBlock(type="heading", value=value, md=f"{'#' * lvl} {value}", level=lvl)


def _t(md):
    return ParsedBlock(type="text", value=md, md=md)


def _tbl(md, rows):
    return ParsedBlock(type="table", value="", md=md, rows=rows)


def _fake_llm(content):
    return SimpleNamespace(
        chat=lambda messages: SimpleNamespace(
            message=SimpleNamespace(content=content)
        )
    )


# --- Logic thuần ---
def test_validate_partition_ok():
    assert _validate_partition([{"blocks": [0, 1]}, {"blocks": [2]}], 3) == [[0, 1], [2]]


def test_validate_partition_rejects_gap():
    with pytest.raises(ValueError):
        _validate_partition([{"blocks": [0, 2]}], 3)


def test_validate_partition_rejects_incomplete_coverage():
    with pytest.raises(ValueError):
        _validate_partition([{"blocks": [0]}], 3)


def test_validate_partition_rejects_overlap():
    with pytest.raises(ValueError):
        _validate_partition([{"blocks": [0, 1]}, {"blocks": [1, 2]}], 3)


def test_merge_block_texts_keeps_blocks_atomic(monkeypatch):
    monkeypatch.setattr(md_chunker.settings, "chunk_size", 4)  # nhỏ → mỗi block 1 chunk
    out = _merge_block_texts(["một hai ba bốn năm", "sáu bảy tám chín mười"])
    assert len(out) == 2  # không bao giờ tách một block, nhưng không gộp khi vượt ngưỡng


# --- LLM grouping: ghép verbatim từ JSON có kiểm soát ---
def test_llm_group_assembles_verbatim(monkeypatch):
    blocks = [(1, _t("đoạn A")), (1, _t("đoạn B")), (2, _t("đoạn C"))]
    canned = (
        '[{"blocks":[0,1],"heading_path":["Điều 1"],"context":"ctx1","chunk_type":"text"},'
        '{"blocks":[2],"heading_path":["Điều 1"],"context":"ctx2","chunk_type":"text"}]'
    )
    monkeypatch.setattr(md_chunker, "_get_llm", lambda: _fake_llm(canned))
    out = md_chunker._llm_group(blocks, ["Điều 1"], {"doc_name": "x"})
    assert len(out) == 2
    content0, hp0, ctx0, ctype0, page0 = out[0]
    assert content0 == "đoạn A\n\nđoạn B"  # ghép verbatim theo chỉ số block
    assert hp0 == ["Điều 1"] and ctx0 == "ctx1" and ctype0 == "text" and page0 == 1
    assert out[1][0] == "đoạn C"


def test_llm_group_invalid_partition_raises(monkeypatch):
    blocks = [(1, _t("a")), (1, _t("b"))]
    monkeypatch.setattr(md_chunker, "_get_llm", lambda: _fake_llm('[{"blocks":[0]}]'))
    with pytest.raises(ValueError):  # thiếu block 1 → phân hoạch không phủ hết
        md_chunker._llm_group(blocks, [], {})


# --- build_nodes: fallback (không LLM) ---
def test_build_nodes_fallback_no_llm(monkeypatch):
    monkeypatch.setattr(md_chunker.settings, "chunk_llm_enabled", False)
    pages = [
        _page(1, [_h("A. YÊU CẦU"), _t("1. nội dung khoản một")]),
        _page(2, [_t("2. nội dung khoản hai")]),  # tràn trang → KHÔNG cắt (gộp)
    ]
    nodes = md_chunker.build_nodes(
        pages,
        document_id=7,
        filename="kh.pdf",
        doc_meta={"school_year": "2026-2027", "ward": "Bình Thạnh"},
    )
    assert nodes
    for cn in nodes:
        # ref_doc_id UUID5 ổn định (gotcha Weaviate)
        assert cn.node.relationships[NodeRelationship.SOURCE].node_id == _doc_ref_id(7)
        # metadata bị loại khỏi embed/LLM, gồm school_year/ward
        assert "school_year" in cn.node.excluded_embed_metadata_keys
        assert "ward" in cn.node.excluded_llm_metadata_keys
    joined = "\n".join(cn.content for cn in nodes)
    assert "nội dung khoản một" in joined
    assert "nội dung khoản hai" in joined  # cả 2 trang đều có mặt
    assert nodes[0].page_number == 1  # page_number từ block đầu


def test_build_nodes_table_chunk(monkeypatch):
    monkeypatch.setattr(md_chunker.settings, "chunk_llm_enabled", False)
    rows = [["Ngày", "Việc"], ["1/5", None]]
    tbl = _tbl("| Ngày | Việc |\n| --- | --- |\n| 1/5 |  |", rows)
    nodes = md_chunker.build_nodes([_page(3, [_h("VIII. KHUNG"), tbl])], document_id=1)
    tables = [cn for cn in nodes if cn.has_table]
    assert len(tables) == 1
    cn = tables[0]
    assert cn.chunk_type == "table"
    assert cn.table_data == rows  # lưới lấy thẳng từ block.rows
    assert cn.page_number == 3
    assert "| Ngày | Việc |" in cn.content


def test_build_nodes_uses_llm_when_enabled(monkeypatch):
    monkeypatch.setattr(md_chunker.settings, "chunk_llm_min_tokens", 0)  # ép gọi LLM
    canned = '[{"blocks":[0,1],"heading_path":["Điều 5"],"context":"về tuyển sinh","chunk_type":"text"}]'
    monkeypatch.setattr(md_chunker, "_get_llm", lambda: _fake_llm(canned))
    nodes = md_chunker.build_nodes(
        [_page(1, [_t("đoạn một"), _t("đoạn hai")])], document_id=2
    )
    assert len(nodes) == 1
    assert nodes[0].heading_path == ["Điều 5"]
    assert nodes[0].context == "về tuyển sinh"
    assert nodes[0].content == "đoạn một\n\nđoạn hai"
    # node.text = context + "\n\n" + content (context vào embed/BM25)
    assert nodes[0].node.text.startswith("về tuyển sinh")
    assert nodes[0].content not in nodes[0].context  # content lưu riêng, sạch context
