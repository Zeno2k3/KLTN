"""Fixture dùng chung cho test: app client với DB SQLite in-memory + Redis giả.

Test không cần Postgres/Redis thật:
- DB: SQLite in-memory (StaticPool giữ 1 connection để dữ liệu tồn tại giữa các request),
  chỉ tạo 2 bảng ``roles``/``users`` và seed sẵn role admin/user.
- Redis blacklist: thay bằng set trong RAM.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.deps as deps_mod
import app.services.auth_service as svc_mod
from app.core.database import Base, get_db
from app.main import app
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
