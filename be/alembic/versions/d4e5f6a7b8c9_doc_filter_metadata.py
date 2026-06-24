"""doc filter metadata (school_year, ward)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-24 13:00:00.000000

Nhóm B: metadata lọc truy xuất parse TỪ TÊN FILE — năm học + địa bàn cấp phường/xã (giữ nguyên,
không quy về quận/huyện). Cũng đẩy vào node.metadata để Weaviate lọc; cần re-ingest doc cũ.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "documents", sa.Column("school_year", sa.String(length=20), nullable=True)
    )
    op.add_column("documents", sa.Column("ward", sa.String(length=120), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("documents", "ward")
    op.drop_column("documents", "school_year")
