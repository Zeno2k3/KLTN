"""Test RetrievalAgent: vòng lặp tự-chấm. Đủ → 1 vòng; thiếu → viết lại + retrieve lại; chặn ở
``retrieval_max_rounds``; grader lỗi/tắt → dừng. Patch ``_retrieve_once`` + ``_grade`` (không mạng)."""

from types import SimpleNamespace

from app.core.config import settings
from app.rag.agents import retrieval_agent


def _node(nid, score=0.5):
    return SimpleNamespace(node=SimpleNamespace(node_id=nid), score=score)


def _patch_retrieve(monkeypatch):
    """Thay _retrieve_once bằng bộ ghi lại các truy vấn đã gọi; trả 1 node mỗi lần."""
    calls = []

    def fake(query):
        calls.append(query)
        return [_node(f"n{len(calls)}")]

    monkeypatch.setattr(retrieval_agent, "_retrieve_once", fake)
    return calls


def test_single_round_when_sufficient(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_max_rounds", 2)
    monkeypatch.setattr(settings, "retrieval_grade_enabled", True)
    calls = _patch_retrieve(monkeypatch)
    monkeypatch.setattr(retrieval_agent, "_grade", lambda sq, nodes: {"sufficient": True})

    nodes, rounds = retrieval_agent.retrieve_for_subquery("hồ sơ lớp 1")
    assert rounds == 1
    assert calls == ["hồ sơ lớp 1"]
    assert len(nodes) == 1


def test_loops_on_insufficient_then_uses_refined_query(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_max_rounds", 2)
    monkeypatch.setattr(settings, "retrieval_grade_enabled", True)
    calls = _patch_retrieve(monkeypatch)
    monkeypatch.setattr(
        retrieval_agent,
        "_grade",
        lambda sq, nodes: {"sufficient": False, "refined_query": "giấy tờ tuyển sinh lớp 1"},
    )

    nodes, rounds = retrieval_agent.retrieve_for_subquery("hồ sơ lớp 1")
    assert rounds == 2
    # Vòng 1 dùng câu gốc; vòng 2 dùng refined_query.
    assert calls == ["hồ sơ lớp 1", "giấy tờ tuyển sinh lớp 1"]


def test_capped_at_max_rounds(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_max_rounds", 2)
    monkeypatch.setattr(settings, "retrieval_grade_enabled", True)
    calls = _patch_retrieve(monkeypatch)
    # Luôn thiếu → nếu không cap sẽ lặp mãi; phải dừng ở 2.
    monkeypatch.setattr(
        retrieval_agent,
        "_grade",
        lambda sq, nodes: {"sufficient": False, "refined_query": "x"},
    )

    _, rounds = retrieval_agent.retrieve_for_subquery("q")
    assert rounds == 2
    assert len(calls) == 2


def test_grade_error_stops(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_max_rounds", 3)
    monkeypatch.setattr(settings, "retrieval_grade_enabled", True)
    calls = _patch_retrieve(monkeypatch)
    monkeypatch.setattr(retrieval_agent, "_grade", lambda sq, nodes: None)  # lỗi → coi như đủ

    _, rounds = retrieval_agent.retrieve_for_subquery("q")
    assert rounds == 1
    assert len(calls) == 1


def test_grade_disabled_single_round(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_max_rounds", 3)
    monkeypatch.setattr(settings, "retrieval_grade_enabled", False)
    calls = _patch_retrieve(monkeypatch)

    def _boom(sq, nodes):
        raise AssertionError("grader không được gọi khi tắt")

    monkeypatch.setattr(retrieval_agent, "_grade", _boom)
    _, rounds = retrieval_agent.retrieve_for_subquery("q")
    assert rounds == 1
    assert len(calls) == 1
