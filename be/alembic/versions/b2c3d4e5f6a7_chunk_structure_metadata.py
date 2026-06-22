"""chunk structure metadata

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22 10:00:00.000000

Nâng cấp chunking structure-aware + Contextual Retrieval:
- documents: doc_type / issued_date / issuing_body (auto-extract từ header văn bản).
- document_chunks: heading_path (JSON breadcrumb) / context (đoạn Contextual Retrieval) /
  chunk_type / has_table / page_number.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # documents — metadata cấp văn bản
    op.add_column("documents", sa.Column("doc_type", sa.String(length=50), nullable=True))
    op.add_column(
        "documents", sa.Column("issued_date", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("issuing_body", sa.String(length=255), nullable=True)
    )

    # document_chunks — metadata cấu trúc
    op.add_column("document_chunks", sa.Column("heading_path", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("context", sa.Text(), nullable=True))
    op.add_column(
        "document_chunks", sa.Column("chunk_type", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "has_table",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "document_chunks", sa.Column("page_number", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("document_chunks", "page_number")
    op.drop_column("document_chunks", "has_table")
    op.drop_column("document_chunks", "chunk_type")
    op.drop_column("document_chunks", "context")
    op.drop_column("document_chunks", "heading_path")
    op.drop_column("documents", "issuing_body")
    op.drop_column("documents", "issued_date")
    op.drop_column("documents", "doc_type")
