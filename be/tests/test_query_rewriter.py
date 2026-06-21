"""Test Query Rewriter (condense-question): history rỗng → trả nguyên văn (KHÔNG gọi LLM); có
history → viết lại; output rỗng → fallback câu gốc; chỉ dùng sliding window N tin gần nhất."""

from types import SimpleNamespace

from app.rag import query_rewriter


def _fake_llm(content):
    return SimpleNamespace(
        chat=lambda messages: SimpleNamespace(message=SimpleNamespace(content=content))
    )


def test_rewrite_skips_when_no_history(monkeypatch):
    def _boom():
        raise AssertionError("Không được gọi LLM khi history rỗng")

    monkeypatch.setattr(query_rewriter, "_get_llm", _boom)
    assert query_rewriter.rewrite_query("Hồ sơ gồm gì?", []) == "Hồ sơ gồm gì?"


def test_rewrite_condenses_with_history(monkeypatch):
    monkeypatch.setattr(
        query_rewriter,
        "_get_llm",
        lambda: _fake_llm("Học phí trường Lumina là bao nhiêu?"),
    )
    out = query_rewriter.rewrite_query(
        "thế còn học phí?",
        [{"role": "user", "content": "Trường Lumina ở đâu?"}],
    )
    assert out == "Học phí trường Lumina là bao nhiêu?"


def test_rewrite_falls_back_to_original_on_empty_output(monkeypatch):
    monkeypatch.setattr(query_rewriter, "_get_llm", lambda: _fake_llm("   "))
    out = query_rewriter.rewrite_query("câu gốc", [{"role": "user", "content": "x"}])
    assert out == "câu gốc"


def test_rewrite_uses_only_sliding_window(monkeypatch):
    monkeypatch.setattr(query_rewriter.settings, "chat_history_window", 5)
    captured = {}

    def _llm():
        def chat(messages):
            captured["user"] = messages[-1].content
            return SimpleNamespace(message=SimpleNamespace(content="ok"))

        return SimpleNamespace(chat=chat)

    monkeypatch.setattr(query_rewriter, "_get_llm", _llm)
    history = [{"role": "user", "content": f"tin {i}"} for i in range(8)]
    query_rewriter.rewrite_query("hỏi", history)
    # Chỉ 5 tin gần nhất (tin 3..7) lọt vào prompt; tin 0..2 bị cắt.
    assert "tin 7" in captured["user"]
    assert "tin 3" in captured["user"]
    assert "tin 2" not in captured["user"]
