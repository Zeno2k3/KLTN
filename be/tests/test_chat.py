"""Test hỏi-đáp RAG: service lưu đúng 2 tin nhắn (user+assistant) + nguồn + trace; endpoint
yêu cầu đăng nhập, trả câu trả lời, và nối tiếp được hội thoại. Pipeline RAG được MOCK."""

import time
from uuid import uuid4

import pytest

import app.main as app_main
from app.models.base import MessageSender
from app.models.document import Document, DocumentChunk
from app.rag import query_engine
from app.repositories import conversation_repository
from app.services import chat_service


def _fake_answer(
    answer="Trường nhận hồ sơ từ tháng 7 [1].", sources=None, trace_id="trace-1"
):
    def _impl(question, history=None, filters=None):
        return query_engine.AnswerResult(
            answer=answer,
            sources=sources
            if sources is not None
            else [{"index": 1, "document_id": 1, "filename": "quy-che.pdf"}],
            trace_id=trace_id,
        )

    return _impl


@pytest.mark.asyncio
async def test_service_persists_user_and_assistant_messages(conv_session, monkeypatch):
    session, user_id = conv_session
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())

    outcome = await chat_service.ask(
        session, user_id=user_id, question="Khi nào nộp hồ sơ?"
    )

    msgs = await conversation_repository.list_messages(session, outcome.conversation_id)
    assert [m.sender_type for m in msgs] == [
        MessageSender.user,
        MessageSender.assistant,
    ]
    assert msgs[0].content == "Khi nào nộp hồ sơ?"
    assert msgs[1].content == outcome.answer
    assert msgs[1].context_sources == [
        {"index": 1, "document_id": 1, "filename": "quy-che.pdf"}
    ]
    assert msgs[1].trace_id == "trace-1"


@pytest.mark.asyncio
async def test_service_uses_multi_agent_path_when_flag_enabled(
    conv_session, monkeypatch
):
    """Cờ ``rag_multi_agent_enabled=True`` → service gọi ``answer_question_agentic`` (đường đa tác
    tử), KHÔNG gọi ``answer_question`` (tuyến tính); vẫn lưu answer + sources + trace như thường."""
    session, user_id = conv_session
    import app.rag.agents.workflow as agent_wf

    monkeypatch.setattr(chat_service.settings, "rag_multi_agent_enabled", True)

    def _linear_boom(*a, **k):
        raise AssertionError("không được dùng answer_question khi cờ đa tác tử bật")

    monkeypatch.setattr(chat_service.query_engine, "answer_question", _linear_boom)

    async def _fake_agentic(question, history=None, filters=None):
        return query_engine.AnswerResult(
            answer="Trả lời đa tác tử [1].",
            sources=[{"index": 1, "document_id": 2, "filename": "ben-cat.pdf"}],
            trace_id="agentic-trace",
        )

    monkeypatch.setattr(agent_wf, "answer_question_agentic", _fake_agentic)

    outcome = await chat_service.ask(
        session, user_id=user_id, question="Hồ sơ và độ tuổi lớp 1?"
    )

    assert outcome.answer == "Trả lời đa tác tử [1]."
    msgs = await conversation_repository.list_messages(session, outcome.conversation_id)
    assert msgs[1].content == "Trả lời đa tác tử [1]."
    assert msgs[1].trace_id == "agentic-trace"
    assert msgs[1].context_sources == [
        {"index": 1, "document_id": 2, "filename": "ben-cat.pdf"}
    ]


@pytest.mark.asyncio
async def test_service_passes_pruned_history_to_engine(conv_session, monkeypatch):
    """Service truyền lịch sử (sliding window) vào engine, KHÔNG gồm câu hỏi hiện tại.

    Lượt 1 (hội thoại mới) → history rỗng. Lượt 2 (nối tiếp) → đúng các tin trước đó."""
    session, user_id = conv_session
    captured: dict = {}

    def _impl(question, history=None, filters=None):
        captured["history"] = history
        return query_engine.AnswerResult(answer="ok", sources=[], trace_id=None)

    monkeypatch.setattr(chat_service.query_engine, "answer_question", _impl)
    monkeypatch.setattr(chat_service.settings, "chat_history_window", 5)

    out = await chat_service.ask(session, user_id=user_id, question="Câu một?")
    assert captured["history"] == []  # hội thoại mới → chưa có lịch sử

    await chat_service.ask(
        session,
        user_id=user_id,
        question="Câu hai?",
        conversation_id=out.conversation_id,
    )
    # Lịch sử = 2 tin của lượt 1 (user + assistant), KHÔNG chứa "Câu hai?".
    assert [h["role"] for h in captured["history"]] == ["user", "assistant"]
    assert [h["content"] for h in captured["history"]] == ["Câu một?", "ok"]
    assert all("Câu hai?" != h["content"] for h in captured["history"])


@pytest.mark.asyncio
async def test_service_rejects_foreign_conversation(conv_session, monkeypatch):
    session, user_id = conv_session
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())

    # Hội thoại của người khác → 404 (không lộ/ghi đè hội thoại không thuộc về mình).
    other = await conversation_repository.create(session, user_id=user_id + 999)
    await session.commit()

    with pytest.raises(Exception) as exc:
        await chat_service.ask(
            session,
            user_id=user_id,
            question="hỏi",
            conversation_id=other.id,
        )
    assert getattr(exc.value, "status_code", None) == 404


@pytest.mark.asyncio
async def test_service_rejects_empty_question(conv_session):
    session, user_id = conv_session
    with pytest.raises(Exception) as exc:
        await chat_service.ask(session, user_id=user_id, question="   ")
    assert getattr(exc.value, "status_code", None) == 400


# --- Timeout pipeline RAG → 503 thân thiện (không treo) ---


@pytest.mark.asyncio
async def test_service_raises_503_on_rag_timeout(conv_session, monkeypatch):
    """RAG vượt ``rag_timeout_seconds`` → HTTPException 503 thay vì treo vô hạn."""
    session, user_id = conv_session

    def _slow(question, history=None, filters=None):
        time.sleep(0.2)  # lâu hơn timeout đặt bên dưới
        return query_engine.AnswerResult(answer="muộn", sources=[], trace_id=None)

    monkeypatch.setattr(chat_service.query_engine, "answer_question", _slow)
    monkeypatch.setattr(chat_service.settings, "rag_timeout_seconds", 0.02)

    with pytest.raises(Exception) as exc:
        await chat_service.ask(session, user_id=user_id, question="Câu hỏi chậm?")
    assert getattr(exc.value, "status_code", None) == 503
    assert "thử lại" in getattr(exc.value, "detail", "")


# --- Warm-up reranker lúc startup (lifespan) ---


async def _run_lifespan_with_stubs(monkeypatch, *, warmup_enabled):
    """Chạy lifespan với init_tracing/redis bị vô hiệu; trả số lần warmup được gọi."""
    calls: list[int] = []
    monkeypatch.setattr(app_main, "init_tracing", lambda: None)

    async def _noop():
        return None

    monkeypatch.setattr(app_main, "init_redis", _noop)
    monkeypatch.setattr(app_main, "close_redis", _noop)
    monkeypatch.setattr(query_engine, "warmup", lambda: calls.append(1))
    monkeypatch.setattr(app_main.settings, "rerank_warmup", warmup_enabled)

    async with app_main.lifespan(app_main.app):
        pass
    return calls


@pytest.mark.asyncio
async def test_lifespan_warms_up_reranker_when_enabled(monkeypatch):
    calls = await _run_lifespan_with_stubs(monkeypatch, warmup_enabled=True)
    assert calls == [1]


@pytest.mark.asyncio
async def test_lifespan_skips_warmup_when_disabled(monkeypatch):
    calls = await _run_lifespan_with_stubs(monkeypatch, warmup_enabled=False)
    assert calls == []


# --- Chọn reranker theo provider (mặc định Cohere API) ---


def test_get_reranker_cohere_uses_api_key_and_model(monkeypatch):
    """provider='cohere' → khởi tạo CohereRerank với đúng api_key/model/top_n."""
    import llama_index.postprocessor.cohere_rerank as cohere_mod

    captured = {}

    class _FakeCohere:
        def __init__(self, api_key, model, top_n):
            captured.update(api_key=api_key, model=model, top_n=top_n)

    monkeypatch.setattr(cohere_mod, "CohereRerank", _FakeCohere)
    monkeypatch.setattr(query_engine, "_reranker", None)
    monkeypatch.setattr(query_engine.settings, "rerank_provider", "cohere")
    monkeypatch.setattr(
        query_engine.settings, "rerank_model", "rerank-multilingual-v3.0"
    )
    monkeypatch.setattr(query_engine.settings, "rerank_top_n", 6)
    monkeypatch.setattr(query_engine.settings, "cohere_api_key", "test-key")

    reranker = query_engine._get_reranker()
    assert isinstance(reranker, _FakeCohere)
    assert captured == {
        "api_key": "test-key",
        "model": "rerank-multilingual-v3.0",
        "top_n": 6,
    }


def test_get_reranker_cohere_missing_key_raises(monkeypatch):
    """provider='cohere' nhưng thiếu COHERE_API_KEY → RuntimeError rõ ràng (không gọi mạng mù)."""
    monkeypatch.setattr(query_engine, "_reranker", None)
    monkeypatch.setattr(query_engine.settings, "rerank_provider", "cohere")
    monkeypatch.setattr(query_engine.settings, "cohere_api_key", "")
    with pytest.raises(RuntimeError, match="COHERE_API_KEY"):
        query_engine._get_reranker()


@pytest.mark.asyncio
async def test_ask_endpoint_requires_auth(client):
    resp = await client.post("/api/v1/chat/ask", json={"question": "Hỏi gì đó?"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ask_endpoint_answers_and_continues_conversation(
    user_client, monkeypatch
):
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())

    resp = await user_client.post(
        "/api/v1/chat/ask", json={"question": "Khi nào tuyển sinh lớp 1?"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"].startswith("Trường nhận hồ sơ")
    assert body["sources"][0]["filename"] == "quy-che.pdf"
    conversation_id = body["conversation_id"]

    # Gọi tiếp với conversation_id → cùng hội thoại.
    resp2 = await user_client.post(
        "/api/v1/chat/ask",
        json={"question": "Hồ sơ gồm những gì?", "conversation_id": conversation_id},
    )
    assert resp2.status_code == 200
    assert resp2.json()["conversation_id"] == conversation_id


@pytest.mark.asyncio
async def test_ask_endpoint_validates_blank_question(user_client):
    resp = await user_client.post("/api/v1/chat/ask", json={"question": ""})
    assert resp.status_code == 422  # pydantic min_length=1


# --- Đọc lịch sử hội thoại (sidebar) ---


@pytest.mark.asyncio
async def test_list_conversations_returns_summary_with_last_message(
    conv_session, monkeypatch
):
    session, user_id = conv_session
    monkeypatch.setattr(
        chat_service.query_engine,
        "answer_question",
        _fake_answer(answer="Trường nhận hồ sơ từ tháng 7."),
    )
    out = await chat_service.ask(session, user_id=user_id, question="Câu hỏi một?")

    summaries = await chat_service.list_conversations(session, user_id=user_id)
    assert len(summaries) == 1
    assert summaries[0].id == out.conversation_id
    assert summaries[0].title == "Câu hỏi một?"
    # last_message = tin nhắn cuối (của assistant).
    assert summaries[0].last_message == "Trường nhận hồ sơ từ tháng 7."


@pytest.mark.asyncio
async def test_get_conversation_returns_messages_with_sources(
    conv_session, monkeypatch
):
    session, user_id = conv_session
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())
    out = await chat_service.ask(
        session, user_id=user_id, question="Khi nào tuyển sinh?"
    )

    detail = await chat_service.get_conversation(
        session, user_id=user_id, conversation_id=out.conversation_id
    )
    assert detail.id == out.conversation_id
    assert [str(m.sender_type) for m in detail.messages] == ["user", "assistant"]
    assert detail.messages[1].sources[0].filename == "quy-che.pdf"


@pytest.mark.asyncio
async def test_get_conversation_foreign_raises_404(conv_session):
    session, user_id = conv_session
    other = await conversation_repository.create(session, user_id=user_id + 999)
    await session.commit()
    with pytest.raises(Exception) as exc:
        await chat_service.get_conversation(
            session, user_id=user_id, conversation_id=other.id
        )
    assert getattr(exc.value, "status_code", None) == 404


@pytest.mark.asyncio
async def test_conversations_endpoint_requires_auth(client):
    resp = await client.get("/api/v1/chat/conversations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_and_get_conversation_via_api(user_client, monkeypatch):
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())
    ask = await user_client.post(
        "/api/v1/chat/ask", json={"question": "Khi nào tuyển sinh lớp 1?"}
    )
    cid = ask.json()["conversation_id"]

    lst = await user_client.get("/api/v1/chat/conversations")
    assert lst.status_code == 200
    item = next(c for c in lst.json() if c["id"] == cid)
    assert item["title"] == "Khi nào tuyển sinh lớp 1?"
    assert item["last_message"]  # có snippet tin cuối

    msgs = await user_client.get(f"/api/v1/chat/conversations/{cid}/messages")
    assert msgs.status_code == 200
    detail = msgs.json()
    assert [m["sender_type"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["sources"][0]["filename"] == "quy-che.pdf"


@pytest.mark.asyncio
async def test_get_conversation_missing_returns_404(user_client):
    resp = await user_client.get("/api/v1/chat/conversations/99999/messages")
    assert resp.status_code == 404


# --- Đổi tên hội thoại ---


@pytest.mark.asyncio
async def test_rename_conversation_updates_title(conv_session, monkeypatch):
    session, user_id = conv_session
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())
    out = await chat_service.ask(session, user_id=user_id, question="Tên cũ?")

    summary = await chat_service.rename_conversation(
        session, user_id=user_id, conversation_id=out.conversation_id, title="Tên mới"
    )
    assert summary.id == out.conversation_id
    assert summary.title == "Tên mới"

    refetched = await conversation_repository.get_by_id(session, out.conversation_id)
    assert refetched.title == "Tên mới"


@pytest.mark.asyncio
async def test_rename_conversation_foreign_raises_404(conv_session):
    session, user_id = conv_session
    other = await conversation_repository.create(session, user_id=user_id + 999)
    await session.commit()
    with pytest.raises(Exception) as exc:
        await chat_service.rename_conversation(
            session, user_id=user_id, conversation_id=other.id, title="Hack"
        )
    assert getattr(exc.value, "status_code", None) == 404


@pytest.mark.asyncio
async def test_rename_conversation_rejects_blank_title(conv_session, monkeypatch):
    session, user_id = conv_session
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())
    out = await chat_service.ask(session, user_id=user_id, question="Câu hỏi?")
    with pytest.raises(Exception) as exc:
        await chat_service.rename_conversation(
            session, user_id=user_id, conversation_id=out.conversation_id, title="   "
        )
    assert getattr(exc.value, "status_code", None) == 400


@pytest.mark.asyncio
async def test_rename_endpoint_requires_auth(client):
    resp = await client.patch("/api/v1/chat/conversations/1", json={"title": "X"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rename_via_api(user_client, monkeypatch):
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())
    ask = await user_client.post("/api/v1/chat/ask", json={"question": "Tên gốc?"})
    cid = ask.json()["conversation_id"]

    resp = await user_client.patch(
        f"/api/v1/chat/conversations/{cid}", json={"title": "Tên đã đổi"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "Tên đã đổi"

    lst = await user_client.get("/api/v1/chat/conversations")
    item = next(c for c in lst.json() if c["id"] == cid)
    assert item["title"] == "Tên đã đổi"


@pytest.mark.asyncio
async def test_rename_via_api_validates_blank_title(user_client, monkeypatch):
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())
    ask = await user_client.post("/api/v1/chat/ask", json={"question": "Hỏi?"})
    cid = ask.json()["conversation_id"]
    resp = await user_client.patch(
        f"/api/v1/chat/conversations/{cid}", json={"title": ""}
    )
    assert resp.status_code == 422  # pydantic min_length=1


# --- Xóa hội thoại ---


@pytest.mark.asyncio
async def test_delete_conversation_removes_it(conv_session, monkeypatch):
    session, user_id = conv_session
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())
    out = await chat_service.ask(session, user_id=user_id, question="Sẽ bị xóa?")

    await chat_service.delete_conversation(
        session, user_id=user_id, conversation_id=out.conversation_id
    )
    assert await conversation_repository.get_by_id(session, out.conversation_id) is None
    # (Cascade xóa messages do FK ``ON DELETE CASCADE`` của Postgres lo; SQLite test
    #  không bật FK nên không kiểm ở đây — đã phủ gián tiếp qua test API trả 404.)


@pytest.mark.asyncio
async def test_delete_conversation_foreign_raises_404(conv_session):
    session, user_id = conv_session
    other = await conversation_repository.create(session, user_id=user_id + 999)
    await session.commit()
    with pytest.raises(Exception) as exc:
        await chat_service.delete_conversation(
            session, user_id=user_id, conversation_id=other.id
        )
    assert getattr(exc.value, "status_code", None) == 404


@pytest.mark.asyncio
async def test_delete_endpoint_requires_auth(client):
    resp = await client.delete("/api/v1/chat/conversations/1")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_via_api(user_client, monkeypatch):
    monkeypatch.setattr(chat_service.query_engine, "answer_question", _fake_answer())
    ask = await user_client.post("/api/v1/chat/ask", json={"question": "Xóa tôi?"})
    cid = ask.json()["conversation_id"]

    resp = await user_client.delete(f"/api/v1/chat/conversations/{cid}")
    assert resp.status_code == 204, resp.text

    # Vắng khỏi danh sách + đọc lại 404.
    lst = await user_client.get("/api/v1/chat/conversations")
    assert all(c["id"] != cid for c in lst.json())
    msgs = await user_client.get(f"/api/v1/chat/conversations/{cid}/messages")
    assert msgs.status_code == 404


@pytest.mark.asyncio
async def test_delete_via_api_missing_returns_404(user_client):
    resp = await user_client.delete("/api/v1/chat/conversations/99999")
    assert resp.status_code == 404


# --- Bảng trích dẫn: đọc tài liệu + đoạn text (GET /chat/documents/{id}) ---


async def _seed_document(session_maker, *, chunks: list[tuple[int, str, bool]]):
    """Tạo 1 tài liệu + các chunk (chunk_index, content, có_uuid) → trả document_id."""
    async with session_maker() as s:
        doc = Document(
            filename="bang-hoc-phi.pdf",
            file_path="/tmp/bang-hoc-phi.pdf",
            page_count=9,
        )
        s.add(doc)
        await s.commit()
        await s.refresh(doc)
        s.add_all(
            [
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=content,
                    weaviate_uuid=uuid4() if has_uuid else None,
                )
                for idx, content, has_uuid in chunks
            ]
        )
        await s.commit()
        return doc.id


@pytest.mark.asyncio
async def test_get_document_detail_returns_ordered_chunks(doc_session):
    """Service: trả tài liệu + chunk đúng thứ tự ``chunk_index`` + uuid dạng chuỗi."""
    doc = Document(filename="hp.pdf", file_path="/tmp/hp.pdf", page_count=5)
    doc_session.add(doc)
    await doc_session.commit()
    await doc_session.refresh(doc)
    doc_session.add_all(
        [
            DocumentChunk(
                document_id=doc.id,
                chunk_index=1,
                content="Đoạn hai",
                weaviate_uuid=uuid4(),
            ),
            DocumentChunk(document_id=doc.id, chunk_index=0, content="Đoạn một"),
        ]
    )
    await doc_session.commit()

    detail = await chat_service.get_document_detail(doc_session, doc.id)
    assert detail.filename == "hp.pdf"
    assert detail.page_count == 5
    assert detail.chunk_count == 2
    assert [c.chunk_index for c in detail.chunks] == [0, 1]  # sắp theo chunk_index
    assert detail.chunks[0].content == "Đoạn một"
    assert detail.chunks[0].weaviate_uuid is None
    assert isinstance(detail.chunks[1].weaviate_uuid, str)


@pytest.mark.asyncio
async def test_get_document_detail_missing_raises_404(doc_session):
    with pytest.raises(Exception) as exc:
        await chat_service.get_document_detail(doc_session, 99999)
    assert getattr(exc.value, "status_code", None) == 404


@pytest.mark.asyncio
async def test_get_document_endpoint_returns_chunks(user_client_db):
    client, session_maker = user_client_db
    doc_id = await _seed_document(
        session_maker,
        chunks=[(0, "Đoạn không", True), (1, "Đoạn một", False)],
    )

    resp = await client.get(f"/api/v1/chat/documents/{doc_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == doc_id
    assert body["filename"] == "bang-hoc-phi.pdf"
    assert body["page_count"] == 9
    assert body["chunk_count"] == 2
    assert [c["chunk_index"] for c in body["chunks"]] == [0, 1]
    assert body["chunks"][0]["content"] == "Đoạn không"
    assert isinstance(body["chunks"][0]["weaviate_uuid"], str)
    assert body["chunks"][1]["weaviate_uuid"] is None


@pytest.mark.asyncio
async def test_get_document_endpoint_missing_returns_404(user_client):
    resp = await user_client.get("/api/v1/chat/documents/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_document_endpoint_requires_auth(client):
    resp = await client.get("/api/v1/chat/documents/1")
    assert resp.status_code == 401
