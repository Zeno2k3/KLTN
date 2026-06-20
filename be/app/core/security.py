from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt chỉ dùng tối đa 72 byte đầu của mật khẩu; bcrypt 5.x raise nếu dài hơn
# nên ta cắt thủ công cho an toàn.
_BCRYPT_MAX_BYTES = 72

# Tên loại token đặt trong claim "type" để phân biệt access vs refresh.
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(pw, hashed_password.encode("utf-8"))


def _create_token(
    subject: str | int,
    role: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """Tạo JWT với claim chuẩn: sub, role, type, jti, exp.

    - ``sub``: id người dùng (chuỗi).
    - ``role``: tên vai trò (để phân quyền nhanh, không phải query DB lại).
    - ``type``: ``access`` / ``refresh``.
    - ``jti``: id duy nhất của token, dùng để blacklist khi đăng xuất.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "jti": uuid4().hex,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(
    subject: str | int, role: str, expires_delta: timedelta | None = None
) -> str:
    return _create_token(
        subject,
        role,
        TOKEN_TYPE_ACCESS,
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(
    subject: str | int, role: str, expires_delta: timedelta | None = None
) -> str:
    return _create_token(
        subject,
        role,
        TOKEN_TYPE_REFRESH,
        expires_delta or timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict:
    """Decode JWT, trả về payload hoặc {} nếu token sai/hết hạn."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return {}
