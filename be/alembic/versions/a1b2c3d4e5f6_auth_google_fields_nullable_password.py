"""auth: google fields + nullable password

Revision ID: a1b2c3d4e5f6
Revises: 91b4361ad459
Create Date: 2026-06-19 19:30:00.000000

Thêm hỗ trợ đăng nhập bằng Google:
- users.password_hash → nullable (tài khoản Google không có mật khẩu)
- users.auth_provider ("local"/"google"), users.google_sub (unique), users.avatar_url
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "91b4361ad459"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.String(length=20),
            server_default=sa.text("'local'"),
            nullable=False,
        ),
    )
    op.add_column(
        "users", sa.Column("google_sub", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users", sa.Column("avatar_url", sa.String(length=512), nullable=True)
    )
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(length=255), nullable=True
    )
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    # Đưa password_hash về NOT NULL — chỉ an toàn nếu không có tài khoản Google.
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(length=255), nullable=False
    )
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "auth_provider")
