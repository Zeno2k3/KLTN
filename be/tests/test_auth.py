"""Test luồng xác thực: đăng ký, đăng nhập, /me, refresh, logout, Google, phân quyền."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.deps import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, require_roles
from app.schemas.auth import UserResponse


async def _register(client, email="a@b.com", password="password123", name="Nguyễn A"):
    return await client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@b.com"
    assert body["role"] == "user"  # vai trò mặc định
    # Đăng ký xong tự đăng nhập → có cookie token
    assert ACCESS_COOKIE_NAME in resp.cookies
    assert REFRESH_COOKIE_NAME in resp.cookies


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await _register(client)
    resp = await _register(client)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "a@b.com", "password": "sai-mat-khau"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_and_me(client):
    await _register(client)
    # Đăng nhập (cookie tự lưu trong client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "a@b.com", "password": "password123"},
    )
    assert resp.status_code == 200

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@b.com"


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_token(client):
    await _register(client)
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    assert ACCESS_COOKIE_NAME in resp.cookies


@pytest.mark.asyncio
async def test_logout_blacklists_access_token(client):
    await _register(client)
    # Giữ lại access token trước khi logout để kiểm tra blacklist
    access = client.cookies.get(ACCESS_COOKIE_NAME)

    out = await client.post("/api/v1/auth/logout")
    assert out.status_code == 200

    # Gửi lại access token cũ → phải bị từ chối (đã blacklist)
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_google_login_creates_user(client, fake_google):
    resp = await client.post(
        "/api/v1/auth/google", json={"access_token": "fake-access-token"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == fake_google["email"]
    assert body["role"] == "user"
    assert body["avatar_url"] == fake_google["picture"]
    assert ACCESS_COOKIE_NAME in resp.cookies


@pytest.mark.asyncio
async def test_require_roles_forbids_non_admin():
    checker = require_roles("admin")
    user = SimpleNamespace(role=SimpleNamespace(name="user"))
    with pytest.raises(HTTPException) as exc:
        await checker(current_user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_roles_allows_admin():
    checker = require_roles("admin")
    admin = SimpleNamespace(role=SimpleNamespace(name="admin"))
    assert await checker(current_user=admin) is admin


def test_user_response_accepts_local_domain_email():
    """Email domain đặc biệt (.local của admin seed) không được làm vỡ response (regression)."""
    user = SimpleNamespace(
        id=1,
        name="Quản trị viên",
        email="admin@lumina.local",
        role=SimpleNamespace(name="admin"),
        avatar_url=None,
        is_active=True,
    )
    resp = UserResponse.from_user(user)
    assert resp.email == "admin@lumina.local"
    assert resp.role == "admin"
