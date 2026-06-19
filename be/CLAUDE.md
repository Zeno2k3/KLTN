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
- `app/core/` — `config.py` (settings từ `.env` qua pydantic-settings), `database.py` (async engine/session, `Base`), `security.py` (JWT qua python-jose; hash mật khẩu bằng thư viện `bcrypt` **trực tiếp** — passlib không tương thích bcrypt 5.x).
- `app/api/v1/routes/` — mỗi file = một nhóm endpoint; đăng ký tại `router.py`. Prefix `/api/v1`.
- `app/schemas/` — Pydantic request/response models, tách khỏi ORM `models/`.

## Mô hình dữ liệu (`models/`)

Schema khởi tạo ở migration `91b4361ad459`. ORM theo SQLAlchemy 2.0 (`Mapped`/`mapped_column`), comment tiếng Việt, **import hết tại `app/models/__init__.py`** (đã `import app.models` trong `alembic/env.py`). `created_at`/`updated_at` qua mixin ở `models/base.py`.

- **Phân quyền:** `roles` 1—\* `users` (role đơn qua `users.role_id`, ON DELETE RESTRICT). Mật khẩu lưu hash bcrypt ở `users.password_hash`.
- **Hội thoại:** `users` 1—\* `conversations` 1—\* `messages`. `messages.sender_type` = enum `message_sender` (`user`/`assistant`); `context_sources` (JSONB) lưu nguồn RAG trích dẫn; `trace_id` đối chiếu trace **Arize Phoenix**.
- **Đánh giá người dùng:** `message_feedbacks` (1:1 mỗi tin nhắn, rating ±1 like/dislike) và `conversation_feedbacks` (1:1 mỗi hội thoại, rating 1–5 sao).
- **Tài liệu RAG:** `documents` (metadata PDF, `status` enum `document_status`) 1—\* `document_chunks`. **Vector embedding KHÔNG ở Postgres** — nằm ở **Weaviate Cloud**; `document_chunks.weaviate_uuid` map sang object Weaviate để đồng bộ/xóa & truy vết.
- **Đánh giá chất lượng RAG:** `message_evaluations` lưu điểm **RAGAS** (faithfulness, answer_relevancy, context_precision/recall) theo từng câu trả lời.

Xóa user/hội thoại xóa dây chuyền (ON DELETE CASCADE); xóa user chỉ set NULL `documents.uploaded_by` (giữ kho tri thức). Số liệu admin cơ bản truy vấn trực tiếp (COUNT/GROUP BY), không có bảng tổng hợp.

## Lệnh

```bash
python scripts/run.py                       # dev server → http://localhost:8000
python scripts/seed.py                      # seed roles (admin/user) + admin mặc định
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
- **DB `kltn_db` phải là UTF8** — cluster Windows mặc định WIN1252 không lưu được tiếng Việt; tạo lại bằng `CREATE DATABASE kltn_db WITH ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C'`. Script in tiếng Việt ra console: đặt `PYTHONIOENCODING=utf-8`.
- Thêm bảng mới → tạo model trong `models/`, **import vào `app/models/__init__.py`**, rồi `alembic revision --autogenerate`. Migration tạo ENUM mới thì **drop ENUM thủ công trong `downgrade()`** (Postgres không tự drop khi xóa bảng → up lại sau down sẽ lỗi "type already exists").
- Comment/doc viết bằng **tiếng Việt**.

⚠️ CI (`.github/workflows/python-app.yml`) chạy flake8 + pytest khi push/PR vào `main` (môi trường CI dùng Python 3.10) — giữ code pass được cả hai bước.
