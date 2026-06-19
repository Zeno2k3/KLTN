"""Business logic xác thực: đăng ký, đăng nhập (local + Google), refresh, đăng xuất.

Route chỉ validate input rồi gọi các hàm ở đây (theo kiến trúc phân tầng).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import blacklist_jti, is_blacklisted
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories import role_repository, user_repository
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)

DEFAULT_ROLE = "user"

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def _resolve_default_role_id(db: AsyncSession) -> int:
    role = await role_repository.get_by_name(db, DEFAULT_ROLE)
    if role is None:
        # Chưa seed roles → lỗi cấu hình hệ thống.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chưa seed vai trò mặc định. Chạy: python scripts/seed.py",
        )
    return role.id


async def register(db: AsyncSession, data: RegisterRequest) -> User:
    existing = await user_repository.get_by_email(db, data.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email đã được đăng ký.",
        )
    role_id = await _resolve_default_role_id(db)
    user = User(
        role_id=role_id,
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        auth_provider="local",
    )
    return await user_repository.create(db, user)


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await user_repository.get_by_email(db, email)
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email hoặc mật khẩu không đúng.",
    )
    if user is None:
        raise invalid
    if user.password_hash is None:
        # Tài khoản tạo qua Google chưa đặt mật khẩu local.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản này đăng nhập bằng Google.",
        )
    if not verify_password(password, user.password_hash):
        raise invalid
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa.",
        )
    return user


async def google_login(db: AsyncSession, access_token: str) -> User:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chưa cấu hình GOOGLE_CLIENT_ID ở backend.",
        )

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Đăng nhập Google thất bại.",
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1) Xác thực access token + kiểm audience (token phải được cấp cho app của ta,
        #    chống dùng token của ứng dụng khác để đăng nhập nhờ).
        ti = await client.get(
            GOOGLE_TOKENINFO_URL, params={"access_token": access_token}
        )
        if ti.status_code != 200:
            logger.warning("Google tokeninfo lỗi %s: %s", ti.status_code, ti.text)
            raise invalid
        tokeninfo = ti.json()
        if settings.google_client_id not in {
            tokeninfo.get("aud"),
            tokeninfo.get("azp"),
        }:
            logger.warning(
                "Google token sai audience: aud=%s azp=%s",
                tokeninfo.get("aud"),
                tokeninfo.get("azp"),
            )
            raise invalid

        # 2) Lấy hồ sơ người dùng (tên, ảnh đại diện).
        ui = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if ui.status_code != 200:
            logger.warning("Google userinfo lỗi %s: %s", ui.status_code, ui.text)
            raise invalid
        info = ui.json()

    google_sub = info.get("sub") or tokeninfo.get("sub")
    email = info.get("email") or tokeninfo.get("email")
    if not google_sub or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản Google thiếu email.",
        )
    name = info.get("name") or email.split("@")[0]
    picture = info.get("picture")

    # 1) Đã từng đăng nhập bằng Google.
    user = await user_repository.get_by_google_sub(db, google_sub)
    if user is not None:
        return user

    # 2) Email đã tồn tại (tài khoản local) → liên kết với Google.
    user = await user_repository.get_by_email(db, email)
    if user is not None:
        user.google_sub = google_sub
        if not user.avatar_url and picture:
            user.avatar_url = picture
        await db.flush()
        return user

    # 3) Tạo tài khoản mới từ Google.
    role_id = await _resolve_default_role_id(db)
    user = User(
        role_id=role_id,
        name=name,
        email=email,
        password_hash=None,
        auth_provider="google",
        google_sub=google_sub,
        avatar_url=picture,
    )
    return await user_repository.create(db, user)


def issue_tokens(user: User) -> tuple[str, str]:
    """Cấp cặp (access_token, refresh_token) cho user."""
    access = create_access_token(user.id, user.role.name)
    refresh = create_refresh_token(user.id, user.role.name)
    return access, refresh


async def _blacklist_token(token: str) -> None:
    """Đưa jti của token vào blacklist với TTL bằng thời gian còn lại tới exp."""
    payload = decode_token(token)
    if not payload:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return
    ttl = int(exp - datetime.now(timezone.utc).timestamp())
    await blacklist_jti(jti, ttl)


async def refresh(db: AsyncSession, refresh_token: str) -> tuple[User, str, str]:
    """Xoay vòng refresh token: kiểm tra hợp lệ, blacklist token cũ, cấp cặp mới."""
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token không hợp lệ.",
    )
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != TOKEN_TYPE_REFRESH:
        raise invalid
    jti = payload.get("jti")
    if not jti or await is_blacklisted(jti):
        raise invalid
    user = await user_repository.get_by_id(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise invalid

    await _blacklist_token(refresh_token)  # vô hiệu hóa refresh token cũ
    access, new_refresh = issue_tokens(user)
    return user, access, new_refresh


async def logout(access_token: str | None, refresh_token: str | None) -> None:
    """Đăng xuất: blacklist cả access và refresh token hiện tại."""
    if access_token:
        await _blacklist_token(access_token)
    if refresh_token:
        await _blacklist_token(refresh_token)
