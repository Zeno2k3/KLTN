# Backend (`be/`) — FastAPI

REST API cho chatbot RAG. **Python 3.14 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Redis · LlamaIndex + OpenAI.**
Chi tiết đầy đủ (tech stack, cấu trúc, biến môi trường): [README.md](README.md).

## Kiến trúc phân tầng — luồng một request

```
api/v1/routes/   → validate input qua schema (Pydantic)
api/deps.py      → DI: get_db (session), get_current_user (JWT)
services/        → business logic (không phụ thuộc HTTP)
repositories/    → data access, truy vấn DB qua SQLAlchemy
models/          → ORM models
```

**Quy tắc:** business logic nằm ở `services/` / `repositories/`, **không** viết trong route handler. Route chỉ validate input + gọi service.

## Tổ chức code

- `app/main.py` — khởi tạo FastAPI app, CORS, lifespan, include router.
- `app/core/` — `config.py` (settings từ `.env` qua pydantic-settings), `database.py` (async engine/session, `Base`), `security.py` (JWT encode/decode + bcrypt).
- `app/api/v1/routes/` — mỗi file = một nhóm endpoint; đăng ký tại `router.py`. Prefix `/api/v1`.
- `app/schemas/` — Pydantic request/response models, tách khỏi ORM `models/`.

## Lệnh

```bash
python scripts/run.py                       # dev server → http://localhost:8000
pytest                                      # test (asyncio_mode=auto)
pytest --cov=app --cov-report=html          # test + coverage
ruff check . && ruff format .               # lint + format
alembic revision --autogenerate -m "..."    # tạo migration
alembic upgrade head                        # áp dụng migration
```

API docs sau khi chạy server: `/docs` (Swagger), `/redoc`.

## Quy ước

- **Async toàn bộ** — DB session, route handler, service đều `async`; `await` cho mọi truy vấn DB.
- Lint/format bằng **ruff** (line-length 88, target `py314`); import sort first-party = `app`.
- Settings đọc từ `be/.env` (copy từ `.env.example`) — **không commit `.env`**.
- Thêm bảng mới → tạo model trong `models/`, import vào nơi Alembic thấy được, rồi `alembic revision --autogenerate`.
- Comment/doc viết bằng **tiếng Việt**.

⚠️ CI (`.github/workflows/python-app.yml`) chạy flake8 + pytest khi push/PR vào `main` (môi trường CI dùng Python 3.10) — giữ code pass được cả hai bước.
