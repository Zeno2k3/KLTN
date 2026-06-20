"""Test hỏi-đáp RAG: service lưu đúng 2 tin nhắn (user+assistant) + nguồn + trace; endpoint
yêu cầu đăng nhập, trả câu trả lời, và nối tiếp được hội thoại. Pipeline RAG được MOCK."""

import pytest

from app.models.base import MessageSender
from app.rag import query_engine
from app.repositories import conversation_repository
from app.services import chat_service


def _fake_answer(
    answer="Trường nhận hồ sơ từ tháng 7 [1].", sources=None, trace_id="trace-1"
):
    def _impl(question, filters=None):
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
