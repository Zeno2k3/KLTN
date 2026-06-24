"""Test hàm thuần của script QA mẫu (compute_flags, select_sample) — không cần DB/mạng."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # để import gói scripts

from scripts import qa_sample  # noqa: E402


def _chunk(**kw) -> SimpleNamespace:
    base = {
        "content": "nội dung chunk bình thường",
        "has_table": False,
        "table_data": None,
        "context": None,
        "token_count": 10,
        "weaviate_uuid": "u-1",
        "heading_path": "Điều 1",
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_clean_chunk_has_no_flags():
    assert qa_sample.compute_flags(_chunk(), chunk_size=512) == []


def test_flag_table_without_data():
    flags = qa_sample.compute_flags(
        _chunk(has_table=True, table_data=None, content="| a | b |"), chunk_size=512
    )
    assert "TABLE_NO_DATA" in flags


def test_flag_table_md_mismatch():
    flags = qa_sample.compute_flags(
        _chunk(
            has_table=True,
            table_data={"grid": [["a", "b"]]},
            content="không có markdown",
        ),
        chunk_size=512,
    )
    assert "TABLE_MD_MISMATCH" in flags


def test_flag_context_leak():
    flags = qa_sample.compute_flags(
        _chunk(context="Trích từ X.", content="Trích từ X. nội dung gốc"),
        chunk_size=512,
    )
    assert "CONTEXT_IN_CONTENT" in flags


def test_flag_empty_and_uuid_null():
    flags = qa_sample.compute_flags(
        _chunk(content="   ", weaviate_uuid=None), chunk_size=512
    )
    assert "EMPTY_CONTENT" in flags
    assert "WEAVIATE_UUID_NULL" in flags


def test_flag_token_outlier():
    flags = qa_sample.compute_flags(_chunk(token_count=2000), chunk_size=512)
    assert "TOKEN_OUTLIER" in flags


def test_compute_flags_is_readonly():
    c = _chunk(has_table=True, table_data=None)
    before = vars(c).copy()
    qa_sample.compute_flags(c, chunk_size=512)
    assert vars(c) == before  # KHÔNG sửa input


def test_select_sample_deterministic_subset_readonly():
    rows = list(range(100))
    a = qa_sample.select_sample(rows, 5, seed=42)
    b = qa_sample.select_sample(rows, 5, seed=42)
    assert a == b  # cùng seed → cùng mẫu (tái lập)
    assert len(a) == 5 and set(a) <= set(rows)
    assert rows == list(range(100))  # không sửa input


def test_select_sample_returns_all_when_fewer_than_n():
    assert qa_sample.select_sample([1, 2], 5, seed=1) == [1, 2]
