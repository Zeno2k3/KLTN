"""Fixture dùng chung cho test: app client với DB SQLite in-memory + Redis giả.

Test không cần Postgres/Redis thật:
- DB: SQLite in-memory (StaticPool giữ 1 connection để dữ liệu tồn tại giữa các request),
  chỉ tạo 2 bảng ``roles``/``users`` và seed sẵn role admin/user.
- Redis blacklist: thay bằng set trong RAM.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.deps as deps_mod
import app.services.auth_service as svc_mod
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.conversation import Conversation
from app.models.document import Document, DocumentChunk
from app.models.message import Message
from app.models.role import Role
from app.models.user import User


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c, tables=[Role.__table__, User.__table__]
            )
        )

    test_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Seed roles admin/user
    async with test_session() as s:
        s.add_all(
            [
                Role(name="admin", description="Quản trị viên"),
                Role(name="user", description="Người dùng"),
            ]
        )
        await s.commit()

    async def override_get_db():
        async with test_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Redis blacklist giả (in-memory)
    blacklist: set[str] = set()

    async def fake_blacklist_jti(jti, ttl_seconds):
        if jti and ttl_seconds > 0:
            blacklist.add(jti)

    async def fake_is_blacklisted(jti):
        return jti in blacklist

    monkeypatch.setattr(svc_mod, "blacklist_jti", fake_blacklist_jti)
    monkeypatch.setattr(svc_mod, "is_blacklisted", fake_is_blacklisted)
    monkeypatch.setattr(deps_mod, "is_blacklisted", fake_is_blacklisted)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class _FakeGoogleClient:
    """Giả lập httpx.AsyncClient cho tokeninfo + userinfo của Google."""

    idinfo = {
        "sub": "google-sub-123",
        "email": "google.user@gmail.com",
        "name": "Google User",
        "picture": "https://example.com/avatar.png",
    }

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, **kwargs):
        if "tokeninfo" in url:
            return _FakeResponse(
                200,
                {
                    "aud": "test-client-id",
                    "azp": "test-client-id",
                    "sub": self.idinfo["sub"],
                    "email": self.idinfo["email"],
                },
            )
        if "userinfo" in url:
            return _FakeResponse(200, self.idinfo)
        return _FakeResponse(404, {})


@pytest.fixture
def fake_google(monkeypatch):
    """Giả lập Google (tokeninfo + userinfo) qua httpx — không gọi mạng thật."""
    monkeypatch.setattr(svc_mod.settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(svc_mod.httpx, "AsyncClient", _FakeGoogleClient)
    return _FakeGoogleClient.idinfo


async def _build_authed_client(monkeypatch, role_name):
    """Client httpx đã gắn cookie xác thực sẵn cho 1 user vai trò ``role_name``.

    Khác fixture ``client``: thêm bảng documents/document_chunks và tạo user thật trong
    DB (vì ``require_admin`` kiểm tra vai trò theo DB, không theo claim token)."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c,
                tables=[
                    Role.__table__,
                    User.__table__,
                    Document.__table__,
                    DocumentChunk.__table__,
                    Conversation.__table__,
                    Message.__table__,
                ],
            )
        )

    test_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with test_session() as s:
        s.add_all(
            [
                Role(name="admin", description="Quản trị viên"),
                Role(name="user", description="Người dùng"),
            ]
        )
        await s.commit()
        role = await s.scalar(select(Role).where(Role.name == role_name))
        user = User(
            role_id=role.id,
            name=f"{role_name}-test",
            email=f"{role_name}@test.local",
            password_hash="x",
            auth_provider="local",
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        user_id = user.id

    async def override_get_db():
        async with test_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async def fake_is_blacklisted(jti):
        return False

    monkeypatch.setattr(deps_mod, "is_blacklisted", fake_is_blacklisted)

    token = create_access_token(user_id, role_name)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={deps_mod.ACCESS_COOKIE_NAME: token},
    ) as c:
        # Trả thêm session_maker để test có thể seed dữ liệu vào ĐÚNG DB của request.
        yield c, test_session

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def doc_session():
    """Session SQLite riêng (bảng documents + document_chunks) cho test tầng repository."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c, tables=[Document.__table__, DocumentChunk.__table__]
            )
        )
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def conv_session():
    """Session SQLite riêng (roles/users/conversations/messages) + sẵn 1 user, cho test
    tầng service hỏi-đáp. Trả (session, user_id)."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c,
                tables=[
                    Role.__table__,
                    User.__table__,
                    Conversation.__table__,
                    Message.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        role = Role(name="user", description="Người dùng")
        session.add(role)
        await session.commit()
        await session.refresh(role)
        user = User(
            role_id=role.id,
            name="user-test",
            email="chat@test.local",
            password_hash="x",
            auth_provider="local",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield session, user.id
    await engine.dispose()


@pytest_asyncio.fixture
async def admin_client(monkeypatch):
    async for c, _ in _build_authed_client(monkeypatch, "admin"):
        yield c


@pytest_asyncio.fixture
async def user_client(monkeypatch):
    async for c, _ in _build_authed_client(monkeypatch, "user"):
        yield c


@pytest_asyncio.fixture
async def user_client_db(monkeypatch):
    """Như ``user_client`` nhưng trả thêm ``(client, session_maker)`` để seed dữ liệu (tài liệu,
    chunk…) vào đúng DB SQLite mà request sẽ đọc."""
    async for pair in _build_authed_client(monkeypatch, "user"):
        yield pair
