# KLTN — Lumina

Đồ án tốt nghiệp (KLTN): ứng dụng **chatbot RAG**. Monorepo gồm hai phần độc lập:

| Thư mục | Vai trò              | Stack                                                                                   | Tài liệu                     |
| ------- | -------------------- | --------------------------------------------------------------------------------------- | ---------------------------- |
| `be/`   | REST API backend     | FastAPI · Python 3.14 · SQLAlchemy 2 (async) · PostgreSQL · Redis · LlamaIndex + OpenAI | [be/README.md](be/README.md) |
| `fe/`   | Giao diện người dùng | Next.js 16 · React 19 · TypeScript · Tailwind v4 (App Router)                           | [fe/README.md](fe/README.md) |

Backend phục vụ frontend qua HTTP. FE chạy ở `http://localhost:3000`, BE ở `http://localhost:8000` (đã cấu hình sẵn CORS giữa hai bên).

## Đọc trước khi làm việc trong từng phần

- **`be/`** — chi tiết kiến trúc, luồng request, lệnh chạy/migrate/test ở [be/CLAUDE.md](be/CLAUDE.md).
- **`fe/`** — @fe/CLAUDE.md trước khi viết code FE. Quy ước thư mục & lệnh ở [fe/README.md](fe/README.md).

## Lệnh thường dùng

### Backend (`be/`)

```bash
python scripts/run.py                 # chạy dev server (hoặc: fastapi dev app/main.py)
pytest                                # chạy test
pytest --cov=app --cov-report=html    # test + coverage
ruff check . && ruff format .         # lint + format
alembic revision --autogenerate -m "..."   # tạo migration
alembic upgrade head                  # áp dụng migration
```

### Frontend (`fe/`)

```bash
npm run dev      # dev server
npm run build    # build production
npm run lint     # eslint
```

## Kiến trúc backend (tóm tắt)

Phân tầng rõ ràng — một request đi qua:

```
routes/ (validate qua schema) → deps.py (DI: db session, auth) → services/ (business logic) → repositories/ (truy vấn DB) → models/ (ORM)
```

- `app/core/` — `config.py` (settings từ `.env`), `database.py` (async engine/session), `security.py` (JWT + bcrypt).
- `app/api/v1/routes/` — mỗi file = một nhóm endpoint; gộp tại `router.py`.
- `app/models/` — schema đã dựng (9 bảng: `roles`/`users`, `conversations`/`messages`, `*_feedbacks`, `documents`/`document_chunks`, `message_evaluations`). Vector RAG ở **Weaviate Cloud**, đánh giá chất lượng bằng **RAGAS + Arize Phoenix**. Chi tiết: [be/CLAUDE.md](be/CLAUDE.md).
- Đặt logic vào `services/`/`repositories/`, **không** để business logic trong route handler.

## Frontend (tóm tắt)

- App Router; các trang hiện có: `/` (landing), `/auth`, `/chat`, `/admin`.
- Alias path: `@/*` trỏ về gốc `fe/` (ví dụ `import x from "@/app/lib/..."`).
- UI port từ thiết kế "Lumina" (xem memory [[lumina-design-source]]).

## Môi trường & quy ước

- **OS: Windows + PowerShell.** Đường dẫn dùng `\`. Tạo venv: `py -3.14 -m venv .venv` rồi `.venv\Scripts\activate`.
- Biến môi trường BE đọc từ `be/.env` (copy từ `be/.env.example`) — **không commit `.env`**.
- **DB `kltn_db` phải tạo với `ENCODING 'UTF8'`** — cluster Windows mặc định WIN1252, không lưu được tiếng Việt.
- CI (`.github/workflows/python-app.yml`) chỉ chạy cho backend khi push/PR vào `main`: flake8 + pytest.
- Code & tài liệu trong dự án viết bằng **tiếng Việt**; giữ nhất quán khi thêm comment/doc.
