"""chunk table_data

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-24 12:00:00.000000

Nhóm C: lưu lưới bảng thô của chunk bảng dạng JSON ({"grid": [[ô...]]}) để render/QA/đối chiếu.
Chỉ ở Postgres, KHÔNG đẩy lên Weaviate (vector chỉ giữ markdown trong node.text).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("document_chunks", sa.Column("table_data", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("document_chunks", "table_data")
