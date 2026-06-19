"""Dependency injection: DB session, lấy user hiện tại, kiểm tra phân quyền."""

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import is_blacklisted
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.models.user import User
from app.repositories import user_repository

# Tên cookie httpOnly giữ token (BE set, FE gửi tự động kèm credentials).
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"

# auto_error=False: cookie là chính, header chỉ là fallback (Swagger/test).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_session(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession]:
    yield db


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    header_token: str | None = Depends(oauth2_scheme),
) -> User:
    """Lấy user hiện tại từ access token (ưu tiên cookie, fallback header Bearer)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không xác thực được phiên đăng nhập.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get(ACCESS_COOKIE_NAME) or header_token
    if not token:
        raise credentials_exception

    payload = decode_token(token)
    if not payload or payload.get("type") != TOKEN_TYPE_ACCESS:
        raise credentials_exception

    jti = payload.get("jti")
    if not jti or await is_blacklisted(jti):
        raise credentials_exception

    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception

    user = await user_repository.get_by_id(db, int(sub))
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(
    *role_names: str,
) -> Callable[..., Coroutine[Any, Any, User]]:
    """Tạo dependency yêu cầu user có một trong các vai trò chỉ định, nếu không → 403."""

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập tài nguyên này.",
            )
        return current_user

    return checker


# Dependency dùng sẵn cho các endpoint chỉ dành cho quản trị viên.
require_admin = require_roles("admin")
