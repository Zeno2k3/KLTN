"""Test hậu kiểm trích nguồn (citation_verifier): DROP câu sai phạm vi, recite marker lệch, gom
cited_spans, và FAIL-SAFE khi LLM lỗi/JSON hỏng. Mock LLM — không gọi mạng."""

import json
from types import SimpleNamespace

from app.rag import citation_verifier


def _fake_llm(payload: str):
    """LLM giả: chat() trả nguyên ``payload`` (chuỗi JSON). Nuốt response_format kwarg."""
    return SimpleNamespace(
        chat=lambda messages, **kwargs: SimpleNamespace(
            message=SimpleNamespace(content=payload)
        )
    )


def _sources(*indices: int) -> list[dict]:
    return [
        {
            "index": i,
            "document_id": i,
            "filename": f"doc{i}.pdf",
            "weaviate_uuid": f"u{i}",
        }
        for i in indices
    ]


def _verdicts(*items: dict) -> str:
    return json.dumps({"verdicts": list(items)})


def test_drop_off_scope_claim(monkeypatch):
    # Câu 2 nói về "lớp 6" trong khi câu hỏi về "lớp 1" → in_scope=false → DROP.
    answer = (
        "Đối tượng ưu tiên gồm trẻ đúng tuyến [1]. "
        "Học sinh hoàn thành tiểu học (đối với lớp 6) [2]."
    )
    payload = _verdicts(
        {
            "sentence_id": 0,
            "attributed_indices": [1],
            "supporting_quote": "trẻ đúng tuyến",
            "supported": True,
            "in_scope": True,
            "action": "keep",
        },
        {
            "sentence_id": 1,
            "attributed_indices": [2],
            "supporting_quote": "",
            "supported": True,
            "in_scope": False,
            "action": "drop",
        },
    )
    monkeypatch.setattr(citation_verifier, "_get_llm", lambda: _fake_llm(payload))

    result = citation_verifier.verify_answer(
        answer, "NGỮ CẢNH", _sources(1, 2), "Đối tượng ưu tiên xét tuyển lớp 1 là ai?"
    )

    assert result.ok is True
    assert "lớp 6" not in result.answer
    assert result.answer == "Đối tượng ưu tiên gồm trẻ đúng tuyến [1]."
    assert result.cited_indices == {1}
    assert result.dropped_count == 1
    assert result.cited_spans == {1: ["trẻ đúng tuyến"]}


def test_recite_fixes_wrong_citation(monkeypatch):
    # Generator gắn [2] nhưng attribution xác nhận nguồn đúng là [1] → recite đổi marker.
    answer = "Hồ sơ cần giấy khai sinh [2]."
    payload = _verdicts(
        {
            "sentence_id": 0,
            "attributed_indices": [1],
            "supporting_quote": "giấy khai sinh",
            "supported": True,
            "in_scope": True,
            "action": "recite",
        },
    )
    monkeypatch.setattr(citation_verifier, "_get_llm", lambda: _fake_llm(payload))

    result = citation_verifier.verify_answer(
        answer, "NGỮ CẢNH", _sources(1, 2), "Hồ sơ gồm gì?"
    )

    assert result.answer == "Hồ sơ cần giấy khai sinh [1]."
    assert result.cited_indices == {1}
    assert result.cited_spans == {1: ["giấy khai sinh"]}
    assert result.dropped_count == 0


def test_keep_in_scope_unchanged(monkeypatch):
    answer = "Độ tuổi vào lớp 1 là 6 tuổi [1]."
    payload = _verdicts(
        {
            "sentence_id": 0,
            "attributed_indices": [1],
            "supporting_quote": "6 tuổi",
            "supported": True,
            "in_scope": True,
            "action": "keep",
        },
    )
    monkeypatch.setattr(citation_verifier, "_get_llm", lambda: _fake_llm(payload))

    result = citation_verifier.verify_answer(
        answer, "NGỮ CẢNH", _sources(1), "Mấy tuổi vào lớp 1?"
    )

    assert result.answer == answer
    assert result.cited_indices == {1}
    assert result.dropped_count == 0
    assert result.cited_spans == {1: ["6 tuổi"]}


def test_failsafe_on_llm_error(monkeypatch):
    answer = "Câu A [1]. Câu B [2]."

    class _RaiseLLM:
        def chat(self, messages, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr(citation_verifier, "_get_llm", lambda: _RaiseLLM())

    result = citation_verifier.verify_answer(answer, "NGỮ CẢNH", _sources(1, 2), "hỏi")

    assert result.ok is False
    assert result.answer == answer  # giữ answer gốc
    assert result.cited_indices == {1, 2}  # giữ nguyên mọi nguồn
    assert result.cited_spans == {}


def test_failsafe_on_malformed_json(monkeypatch):
    answer = "Câu A [1]."
    # JSON hợp lệ nhưng verdict THIẾU field bắt buộc → _parse_verdicts raise → fail-safe.
    payload = json.dumps({"verdicts": [{"sentence_id": 0}]})
    monkeypatch.setattr(citation_verifier, "_get_llm", lambda: _fake_llm(payload))

    result = citation_verifier.verify_answer(answer, "NGỮ CẢNH", _sources(1), "hỏi")

    assert result.ok is False
    assert result.answer == answer


def test_split_sentences_keeps_markers():
    sentences = citation_verifier._split_sentences("A [1]. B [2][3].")
    assert len(sentences) == 2
    assert sentences[0]["cited_indices"] == [1]
    assert sentences[1]["cited_indices"] == [2, 3]


def test_all_dropped_returns_original(monkeypatch):
    answer = "Câu lạc đề 1 [1]. Câu lạc đề 2 [2]."
    payload = _verdicts(
        {
            "sentence_id": 0,
            "attributed_indices": [],
            "supporting_quote": "",
            "supported": False,
            "in_scope": False,
            "action": "drop",
        },
        {
            "sentence_id": 1,
            "attributed_indices": [],
            "supporting_quote": "",
            "supported": False,
            "in_scope": False,
            "action": "drop",
        },
    )
    monkeypatch.setattr(citation_verifier, "_get_llm", lambda: _fake_llm(payload))

    result = citation_verifier.verify_answer(answer, "NGỮ CẢNH", _sources(1, 2), "hỏi")

    # Drop hết → KHÔNG trả answer rỗng cho phụ huynh: giữ answer gốc, ok=False.
    assert result.ok is False
    assert result.answer == answer
    assert result.cited_indices == {1, 2}


def test_cited_spans_aggregated_per_source(monkeypatch):
    answer = "Trẻ 6 tuổi nộp hồ sơ [1]. Hồ sơ gồm khai sinh [1]. Phần lạc đề [2]."
    payload = _verdicts(
        {
            "sentence_id": 0,
            "attributed_indices": [1],
            "supporting_quote": "6 tuổi",
            "supported": True,
            "in_scope": True,
            "action": "keep",
        },
        {
            "sentence_id": 1,
            "attributed_indices": [1],
            "supporting_quote": "khai sinh",
            "supported": True,
            "in_scope": True,
            "action": "keep",
        },
        {
            "sentence_id": 2,
            "attributed_indices": [2],
            "supporting_quote": "",
            "supported": True,
            "in_scope": False,
            "action": "drop",
        },
    )
    monkeypatch.setattr(citation_verifier, "_get_llm", lambda: _fake_llm(payload))

    result = citation_verifier.verify_answer(
        answer, "NGỮ CẢNH", _sources(1, 2), "Hồ sơ lớp 1?"
    )

    assert result.cited_spans == {
        1: ["6 tuổi", "khai sinh"]
    }  # gom theo nguồn, giữ thứ tự
    assert 2 not in result.cited_spans  # câu drop không đóng góp span
    assert result.cited_indices == {1}
    assert result.dropped_count == 1
