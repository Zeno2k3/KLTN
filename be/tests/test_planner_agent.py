"""Test PlannerAgent: phân rã câu hỏi → sub-query. Câu đơn → 1 sub-query; câu phức → nhiều; cap ở
``planner_max_subqueries``; lỗi LLM → fallback [câu]; tắt planner → [câu đã condense]. Mock LLM."""

from types import SimpleNamespace

from app.core.config import settings
from app.rag.agents import planner


def _fake_llm(content):
    return SimpleNamespace(
        chat=lambda messages, **kw: SimpleNamespace(
            message=SimpleNamespace(content=content)
        )
    )


class _RaiseLLM:
    def chat(self, messages, **kw):
        raise RuntimeError("network down")


def test_plan_single_returns_one(monkeypatch):
    monkeypatch.setattr(
        planner, "_get_llm", lambda: _fake_llm('{"subqueries": ["hồ sơ lớp 1"]}')
    )
    assert planner.plan("hồ sơ lớp 1", []) == ["hồ sơ lớp 1"]


def test_plan_decomposes_multiple(monkeypatch):
    monkeypatch.setattr(
        planner,
        "_get_llm",
        lambda: _fake_llm('{"subqueries": ["hồ sơ lớp 1", "độ tuổi lớp 1"]}'),
    )
    out = planner.plan("hồ sơ và độ tuổi lớp 1?", [])
    assert out == ["hồ sơ lớp 1", "độ tuổi lớp 1"]


def test_plan_caps_at_max(monkeypatch):
    monkeypatch.setattr(settings, "planner_max_subqueries", 2)
    monkeypatch.setattr(
        planner, "_get_llm", lambda: _fake_llm('{"subqueries": ["a", "b", "c", "d"]}')
    )
    assert planner.plan("nhiều ý", []) == ["a", "b"]


def test_plan_fallback_on_llm_error(monkeypatch):
    monkeypatch.setattr(planner, "_get_llm", lambda: _RaiseLLM())
    assert planner.plan("câu gốc", []) == ["câu gốc"]


def test_plan_fallback_on_bad_json(monkeypatch):
    # JSON thiếu khoá 'subqueries' → _decompose trả [query]; plan giữ nguyên.
    monkeypatch.setattr(planner, "_get_llm", lambda: _fake_llm('{"foo": 1}'))
    assert planner.plan("câu gốc", []) == ["câu gốc"]


def test_plan_disabled_returns_query_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "planner_enabled", False)
    # Không patch LLM: nếu planner gọi LLM khi tắt sẽ lỗi → test bảo đảm KHÔNG gọi.
    monkeypatch.setattr(planner, "_get_llm", lambda: _RaiseLLM())
    assert planner.plan("câu đơn", []) == ["câu đơn"]


def test_plan_condenses_with_history(monkeypatch):
    # Có lịch sử → condense trước (TÁI DÙNG rewrite_query). Tắt phân rã để chỉ kiểm bước condense.
    monkeypatch.setattr(settings, "planner_enabled", False)
    monkeypatch.setattr(
        planner, "rewrite_query", lambda q, h: "Học phí lớp 1 trường Lumina là bao nhiêu?"
    )
    out = planner.plan(
        "thế còn học phí?",
        [{"role": "user", "content": "Trường Lumina tuyển sinh lớp 1 khi nào?"}],
    )
    assert out == ["Học phí lớp 1 trường Lumina là bao nhiêu?"]
