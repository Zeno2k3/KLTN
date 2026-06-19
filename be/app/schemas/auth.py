"""Pydantic schema cho xác thực — request/response của các endpoint /auth."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, EmailStr, Field

if TYPE_CHECKING:
    from app.models.user import User


class RegisterRequest(BaseModel):
    """Dữ liệu đăng ký tài khoản bằng email + mật khẩu."""

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Dữ liệu đăng nhập bằng email + mật khẩu.

    Email dùng ``str`` (không ``EmailStr``): chỉ để tra cứu, không cần validate
    định dạng RFC — tránh từ chối email hợp lệ đã lưu (vd domain .local của admin seed).
    """

    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class GoogleLoginRequest(BaseModel):
    """Access token Google (OAuth implicit) lấy từ frontend qua useGoogleLogin."""

    access_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    """Thông tin người dùng trả về cho frontend (không kèm token — token ở cookie)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str
    avatar_url: str | None = None
    is_active: bool

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        """Map từ ORM User (role là quan hệ) sang response (role là tên chuỗi)."""
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role.name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
        )
