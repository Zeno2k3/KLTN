"""Test LLM Router: map output 'RAG'/'DIRECT' → 'rag'/'direct', default an toàn 'rag' khi output
lạ hoặc LLM lỗi, và có đưa lịch sử vào prompt phân loại. Mock LLM — không gọi mạng."""

from types import SimpleNamespace

from app.rag import query_router


def _fake_llm(content):
    return SimpleNamespace(
        chat=lambda messages: SimpleNamespace(message=SimpleNamespace(content=content))
    )


class _RaiseLLM:
    def chat(self, messages):
        raise RuntimeError("network down")


def test_route_rag(monkeypatch):
    monkeypatch.setattr(query_router, "_get_llm", lambda: _fake_llm("RAG"))
    assert query_router.route_query("Hồ sơ nhập học gồm những gì?", []) == "rag"


def test_route_direct(monkeypatch):
    monkeypatch.setattr(query_router, "_get_llm", lambda: _fake_llm("DIRECT"))
    assert query_router.route_query("Chỉ tôi cách nấu canh chua", []) == "direct"


def test_route_defaults_rag_on_garbage_output(monkeypatch):
    # Output không rõ ràng → default 'rag' (không làm mất khả năng trả lời câu hỏi thật).
    monkeypatch.setattr(query_router, "_get_llm", lambda: _fake_llm("¯\\_(ツ)_/¯"))
    assert query_router.route_query("một câu nào đó", []) == "rag"


def test_route_defaults_rag_on_llm_error(monkeypatch):
    monkeypatch.setattr(query_router, "_get_llm", lambda: _RaiseLLM())
    assert query_router.route_query("một câu nào đó", []) == "rag"


def test_route_includes_recent_history_in_prompt(monkeypatch):
    captured = {}

    def _llm():
        def chat(messages):
            captured["user"] = messages[-1].content
            return SimpleNamespace(message=SimpleNamespace(content="RAG"))

        return SimpleNamespace(chat=chat)

    monkeypatch.setattr(query_router, "_get_llm", _llm)
    query_router.route_query(
        "thế còn học phí thì sao?",
        [{"role": "user", "content": "Trường Lumina tuyển sinh khi nào?"}],
    )
    assert "Trường Lumina" in captured["user"]
    assert "thế còn học phí thì sao?" in captured["user"]
