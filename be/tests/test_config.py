"""Test chuẩn hoá DATABASE_URL trong Settings (xem app/core/config.py).

Host (Render/Railway/Heroku) cấp URL Postgres dạng driver đồng bộ (``postgres://`` hoặc
``postgresql://``); app + Alembic chạy async nên Settings phải ép về ``postgresql+asyncpg://``.
"""

from app.core.config import Settings


def test_postgres_scheme_normalized_to_asyncpg():
    # Render/Railway nội bộ thường cấp postgresql://
    s = Settings(database_url="postgresql://u:p@host:5432/kltn_db")
    assert s.database_url == "postgresql+asyncpg://u:p@host:5432/kltn_db"


def test_heroku_style_postgres_scheme_normalized():
    # Một số host (Heroku/Railway cũ) cấp postgres:// (thiếu "ql")
    s = Settings(database_url="postgres://u:p@host:5432/kltn_db")
    assert s.database_url == "postgresql+asyncpg://u:p@host:5432/kltn_db"


def test_existing_asyncpg_driver_untouched():
    # URL đã ghi rõ driver async → giữ nguyên, không nhân đôi prefix
    url = "postgresql+asyncpg://u:p@host:5432/kltn_db"
    s = Settings(database_url=url)
    assert s.database_url == url


def test_query_params_preserved():
    s = Settings(database_url="postgresql://u:p@host:5432/kltn_db?application_name=kltn")
    assert (
        s.database_url
        == "postgresql+asyncpg://u:p@host:5432/kltn_db?application_name=kltn"
    )
