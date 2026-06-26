"""Test E2E RAGAgentWorkflow (đa tác tử) với agent mock — không mạng. Kiểm: nhánh direct
short-circuit; fan-out N sub-query → fan-in khử trùng → synthesize; vòng Critic→revise bị chặn ở
``critic_max_revisions``; rỗng ngữ cảnh → câu trả lời 'không có thông tin'."""

from types import SimpleNamespace

from app.core.config import settings
from app.rag.agents import critic, planner, retrieval_agent
from app.rag.agents import workflow as wf
from app.rag.agents.critic import CriticVerdict


def _node(nid, score=0.5):
    return SimpleNamespace(node=SimpleNamespace(node_id=nid), score=score)


def _wire_rag(monkeypatch):
    """Định tuyến 'rag' + planner ra 2 sub-query (mặc định cho các test nhánh rag)."""
    monkeypatch.setattr(wf, "route_query", lambda q, h: "rag")
    monkeypatch.setattr(settings, "query_router_enabled", True)
    monkeypatch.setattr(planner, "plan", lambda q, h: ["sub A", "sub B"])


async def test_direct_short_circuits(monkeypatch):
    monkeypatch.setattr(wf, "route_query", lambda q, h: "direct")
    monkeypatch.setattr(wf, "_answer_direct", lambda q, h: "Chào phụ huynh!")
    # planner/retrieve KHÔNG được gọi ở nhánh direct.
    monkeypatch.setattr(
        planner, "plan", lambda q, h: (_ for _ in ()).throw(AssertionError("không gọi"))
    )

    result = await wf.answer_question_agentic("xin chào", history=[])
    assert result.answer == "Chào phụ huynh!"
    assert result.sources == []


async def test_fanout_fanin_dedup_and_synthesize(monkeypatch):
    _wire_rag(monkeypatch)
    monkeypatch.setattr(settings, "critic_max_revisions", 1)

    # Hai sub-query, cùng chia sẻ node "dup" → fan-in phải khử trùng còn 3 node.
    def fake_retrieve(sq):
        if sq == "sub A":
            return ([_node("dup", 0.9), _node("a1", 0.5)], 1)
        return ([_node("dup", 0.8), _node("b1", 0.7)], 1)

    monkeypatch.setattr(retrieval_agent, "retrieve_for_subquery", fake_retrieve)

    seen = {}

    def fake_synth(query, merged, feedback=None):
        seen["n"] = len(merged)
        return "Trả lời [1].", [{"index": 1, "snippet": "s"}], "[1] ctx"

    monkeypatch.setattr(wf, "synthesize", fake_synth)
    monkeypatch.setattr(
        critic,
        "critique",
        lambda a, c, s, q: CriticVerdict(
            answer=a, cited_indices={1}, cited_spans={1: ["q"]}, wants_revision=False
        ),
    )

    result = await wf.answer_question_agentic("hồ sơ và độ tuổi lớp 1?", history=[])
    assert seen["n"] == 3  # dup, a1, b1
    assert result.answer == "Trả lời [1]."
    assert [s["index"] for s in result.sources] == [1]
    assert result.sources[0]["cited_spans"] == ["q"]


async def test_revise_loop_bounded(monkeypatch):
    _wire_rag(monkeypatch)
    monkeypatch.setattr(settings, "critic_max_revisions", 1)
    monkeypatch.setattr(
        retrieval_agent, "retrieve_for_subquery", lambda sq: ([_node("x")], 1)
    )

    synth_calls = []

    def fake_synth(query, merged, feedback=None):
        synth_calls.append(feedback)
        return ("nháp" if feedback is None else "đã sửa"), [{"index": 1}], "ctx"

    monkeypatch.setattr(wf, "synthesize", fake_synth)

    critic_calls = {"n": 0}

    def fake_critique(a, c, s, q):
        critic_calls["n"] += 1
        # LUÔN muốn sửa → nếu không có cap sẽ lặp vô hạn.
        return CriticVerdict(
            answer=a, cited_indices={1}, cited_spans={}, wants_revision=True, feedback="sửa"
        )

    monkeypatch.setattr(critic, "critique", fake_critique)

    result = await wf.answer_question_agentic("q", history=[])
    # max_revisions=1 → synth gọi 2 lần (nháp + 1 revise); critic 2 lần; rồi chốt bản đã sửa.
    assert synth_calls == [None, "sửa"]
    assert critic_calls["n"] == 2
    assert result.answer == "đã sửa"


async def test_empty_context_returns_no_info(monkeypatch):
    _wire_rag(monkeypatch)
    monkeypatch.setattr(
        retrieval_agent, "retrieve_for_subquery", lambda sq: ([], 1)
    )
    # synthesize/critic KHÔNG được gọi khi không có node nào.
    monkeypatch.setattr(
        wf, "synthesize", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không gọi"))
    )

    result = await wf.answer_question_agentic("câu không có tài liệu", history=[])
    assert result.answer == wf._NO_CONTEXT_ANSWER
    assert result.sources == []
