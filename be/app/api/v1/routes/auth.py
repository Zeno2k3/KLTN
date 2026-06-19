"""Endpoint xác thực: đăng ký, đăng nhập (local + Google), refresh, đăng xuất, /me.

Token được trả qua **httpOnly cookie** (không trả trong body) — frontend gửi kèm
tự động nhờ ``credentials: "include"``.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    get_current_user,
)
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Đặt access + refresh token vào httpOnly cookie."""
    common = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
        "domain": settings.cookie_domain,
    }
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", domain=settings.cookie_domain)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", domain=settings.cookie_domain)


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Đăng ký tài khoản mới rồi tự đăng nhập (đặt cookie)."""
    user = await auth_service.register(db, data)
    access, refresh = auth_service.issue_tokens(user)
    set_auth_cookies(response, access, refresh)
    return UserResponse.from_user(user)


@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await auth_service.authenticate(db, data.email, data.password)
    access, refresh = auth_service.issue_tokens(user)
    set_auth_cookies(response, access, refresh)
    return UserResponse.from_user(user)


@router.post("/google", response_model=UserResponse)
async def google_login(
    data: GoogleLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await auth_service.google_login(db, data.access_token)
    access, refresh = auth_service.issue_tokens(user)
    set_auth_cookies(response, access, refresh)
    return UserResponse.from_user(user)


@router.post("/refresh", response_model=UserResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Cấp lại access token mới từ refresh token trong cookie (xoay vòng refresh)."""
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu refresh token.",
        )
    user, access, new_refresh = await auth_service.refresh(db, token)
    set_auth_cookies(response, access, new_refresh)
    return UserResponse.from_user(user)


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    """Đăng xuất: blacklist token hiện tại và xóa cookie."""
    access = request.cookies.get(ACCESS_COOKIE_NAME)
    refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    await auth_service.logout(access, refresh)
    clear_auth_cookies(response)
    return {"detail": "Đã đăng xuất."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_user(current_user)
