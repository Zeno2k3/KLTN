"""Test CriticAgent: tái dùng citation_verifier rồi quyết accept/revise. Có DROP → đòi viết lại;
không DROP → chấp nhận bản hiệu đính; verifier fail-safe (ok=False) → giữ answer gốc. Mock verifier."""

from app.rag.agents import critic
from app.rag.citation_verifier import VerificationResult


def _patch_verify(monkeypatch, result):
    monkeypatch.setattr(
        critic.citation_verifier, "verify_answer", lambda a, c, s, q: result
    )


_SOURCES = [{"index": 1}, {"index": 2}]


def test_accept_when_no_drop(monkeypatch):
    _patch_verify(
        monkeypatch,
        VerificationResult(
            answer="Đã hiệu đính [1].",
            cited_indices={1},
            cited_spans={1: ["trích"]},
            ok=True,
            dropped_count=0,
        ),
    )
    v = critic.critique("nháp [1][2].", "ctx", _SOURCES, "q")
    assert v.wants_revision is False
    assert v.answer == "Đã hiệu đính [1]."
    assert v.cited_indices == {1}
    assert v.cited_spans == {1: ["trích"]}


def test_revise_when_dropped(monkeypatch):
    _patch_verify(
        monkeypatch,
        VerificationResult(
            answer="Đã bỏ câu sai.",
            cited_indices={1},
            cited_spans={},
            ok=True,
            dropped_count=2,
        ),
    )
    v = critic.critique("nháp [1][2].", "ctx", _SOURCES, "q")
    assert v.wants_revision is True
    assert v.feedback  # có góp ý gửi Synthesis


def test_failsafe_keeps_original_when_verifier_not_ok(monkeypatch):
    _patch_verify(
        monkeypatch,
        VerificationResult(
            answer="(bị verifier bỏ qua)",
            cited_indices=set(),
            cited_spans={},
            ok=False,
        ),
    )
    v = critic.critique("answer GỐC [1].", "ctx", _SOURCES, "q")
    assert v.wants_revision is False
    assert v.answer == "answer GỐC [1]."  # giữ nguyên bản gốc, không dùng answer của verifier
    assert v.cited_indices == {1, 2}
