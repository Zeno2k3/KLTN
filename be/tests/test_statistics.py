"""Test endpoint /admin/stats: số liệu tổng hợp theo mốc thời gian + phân quyền.

Seed phụ huynh/hội thoại/tin nhắn với ``created_at`` đặt tường minh (trong kỳ, kỳ
trước, ngoài kỳ) rồi xác nhận count, % thay đổi, bucket biểu đồ, lọc role chính xác.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.base import DocumentStatus, MessageSender
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.role import Role
from app.models.user import User

NOW = datetime.now(UTC)


def _ago(**kw) -> datetime:
    return NOW - timedelta(**kw)


async def _add_conversation(session, user_id, created, messages):
    """Tạo 1 hội thoại + danh sách tin nhắn ``(sender, created_at)`` với thời điểm tường minh."""
    conv = Conversation(user_id=user_id, title="t", created_at=created, updated_at=created)
    session.add(conv)
    await session.flush()
    for sender, created_at in messages:
        session.add(
            Message(
                conversation_id=conv.id,
                sender_type=sender,
                content="x",
                created_at=created_at,
            )
        )
    await session.flush()


async def _seed(session_maker):
    """Dựng dữ liệu nền dùng chung cho các test (range mặc định 30 ngày).

    Kỳ hiện tại = 30 ngày qua; kỳ trước = [60..30 ngày trước]. Kết quả mong đợi:
    - conversations: 4 (kỳ này) / 1 (kỳ trước) → +300%
    - answered (assistant): 2 / 1 → +100%
    - active_parents (role=user, có message 'user'): 2 (P1,P2) / 1 (P1) → +100%
      (hội thoại của admin KHÔNG được tính nhờ lọc role)
    - total_documents: 2
    """
    async with session_maker() as s:
        user_role = await s.scalar(select(Role).where(Role.name == "user"))
        admin = await s.scalar(select(User).where(User.email == "admin@test.local"))

        p1 = User(role_id=user_role.id, name="P1", email="p1@test.local", password_hash="x")
        p2 = User(role_id=user_role.id, name="P2", email="p2@test.local", password_hash="x")
        s.add_all([p1, p2])
        await s.flush()

        # P1 — kỳ hiện tại: 2 hội thoại, mỗi hội thoại 1 user + 1 assistant
        await _add_conversation(
            s, p1.id, _ago(days=1),
            [(MessageSender.user, _ago(days=1)), (MessageSender.assistant, _ago(days=1))],
        )
        await _add_conversation(
            s, p1.id, _ago(days=5),
            [(MessageSender.user, _ago(days=5)), (MessageSender.assistant, _ago(days=5))],
        )
        # P1 — kỳ trước (40 ngày trước): 1 hội thoại 1 user + 1 assistant
        await _add_conversation(
            s, p1.id, _ago(days=40),
            [(MessageSender.user, _ago(days=40)), (MessageSender.assistant, _ago(days=40))],
        )
        # P2 — kỳ hiện tại: 1 hội thoại chỉ có user message
        await _add_conversation(
            s, p2.id, _ago(days=2), [(MessageSender.user, _ago(days=2))]
        )
        # Admin — kỳ hiện tại: 1 hội thoại có user message → KHÔNG tính vào phụ huynh
        await _add_conversation(
            s, admin.id, _ago(days=3), [(MessageSender.user, _ago(days=3))]
        )
        # P1 — ngoài mọi kỳ (100 ngày trước)
        await _add_conversation(
            s, p1.id, _ago(days=100), [(MessageSender.user, _ago(days=100))]
        )

        s.add_all([
            Document(filename="a.pdf", file_path="/tmp/a.pdf", status=DocumentStatus.ready),
            Document(filename="b.pdf", file_path="/tmp/b.pdf", status=DocumentStatus.ready),
        ])
        await s.commit()


@pytest.mark.asyncio
async def test_stats_counts_and_deltas(admin_client_db):
    client, session_maker = admin_client_db
    await _seed(session_maker)

    resp = await client.get("/api/v1/admin/stats", params={"range": "30d"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["range"] == "30d"
    assert body["conversations"] == {"value": 4, "delta_pct": 300.0}
    assert body["answered_questions"] == {"value": 2, "delta_pct": 100.0}
    assert body["active_parents"] == {"value": 2, "delta_pct": 100.0}
    assert body["total_documents"] == 2
    # Chủ đề (1 chủ đề duy nhất) = số lượt trò chuyện kỳ này
    assert body["topic"]["count"] == 4


@pytest.mark.asyncio
async def test_stats_chart_has_six_buckets_summing_window(admin_client_db):
    client, session_maker = admin_client_db
    await _seed(session_maker)

    body = (await client.get("/api/v1/admin/stats", params={"range": "30d"})).json()
    chart = body["chart"]
    assert len(chart) == 6
    # Tổng các cột = số hội thoại trong kỳ hiện tại (4)
    assert sum(b["count"] for b in chart) == 4
    assert all(isinstance(b["label"], str) and b["label"] for b in chart)


@pytest.mark.asyncio
async def test_stats_default_range_is_30d(admin_client_db):
    client, _ = admin_client_db
    body = (await client.get("/api/v1/admin/stats")).json()
    assert body["range"] == "30d"


@pytest.mark.asyncio
async def test_stats_empty_db_returns_zeros_and_null_delta(admin_client_db):
    client, _ = admin_client_db
    body = (await client.get("/api/v1/admin/stats", params={"range": "7d"})).json()
    assert body["range"] == "7d"
    assert body["conversations"] == {"value": 0, "delta_pct": None}
    assert body["total_documents"] == 0
    assert len(body["chart"]) == 6


@pytest.mark.asyncio
async def test_stats_invalid_range_rejected(admin_client_db):
    client, _ = admin_client_db
    resp = await client.get("/api/v1/admin/stats", params={"range": "1y"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stats_forbidden_for_non_admin(user_client):
    resp = await user_client.get("/api/v1/admin/stats")
    assert resp.status_code == 403
