"""Seed dữ liệu nền: vai trò (roles) và tài khoản admin mặc định.

Chạy sau khi `alembic upgrade head`:
    python scripts/seed.py

Idempotent — chạy lại nhiều lần không tạo bản ghi trùng.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Role, User

DEFAULT_ROLES = [
    ("admin", "Quản trị viên hệ thống"),
    ("user", "Người dùng (phụ huynh/thí sinh)"),
]

ADMIN_EMAIL = "admin@lumina.local"
ADMIN_PASSWORD = "admin123"  # nên đổi ngay sau lần đăng nhập đầu tiên
ADMIN_NAME = "Quản trị viên"


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # 1) Vai trò
        roles: dict[str, Role] = {}
        for name, desc in DEFAULT_ROLES:
            role = await session.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name, description=desc)
                session.add(role)
                print(f"Tao role: {name}")
            roles[name] = role
        await session.flush()  # gán id cho các role vừa tạo

        # 2) Tài khoản admin mặc định
        existing = await session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if existing is None:
            session.add(
                User(
                    role_id=roles["admin"].id,
                    name=ADMIN_NAME,
                    email=ADMIN_EMAIL,
                    password_hash=hash_password(ADMIN_PASSWORD),
                )
            )
            print(f"Tao admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        else:
            print("Admin da ton tai, bo qua")

        await session.commit()
    print("Seed xong.")


if __name__ == "__main__":
    asyncio.run(seed())
