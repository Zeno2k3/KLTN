# KLTN — Lumina

Đồ án tốt nghiệp (KLTN): ứng dụng **chatbot RAG**. Monorepo gồm hai phần độc lập:

| Thư mục | Vai trò | Stack | Tài liệu |
|---|---|---|---|
| `be/` | REST API backend | FastAPI · Python 3.14 · SQLAlchemy 2 (async) · PostgreSQL · Redis · LlamaIndex + OpenAI | [be/README.md](be/README.md) |
| `fe/` | Giao diện người dùng | Next.js 16 · React 19 · TypeScript · Tailwind v4 (App Router) | [fe/README.md](fe/README.md) |

Backend phục vụ frontend qua HTTP. FE chạy ở `http://localhost:3000`, BE ở `http://localhost:8000` (đã cấu hình sẵn CORS giữa hai bên).

## Đọc trước khi làm việc trong từng phần

- **`be/`** — chi tiết kiến trúc, luồng request, lệnh chạy/migrate/test ở [be/README.md](be/README.md).
- **`fe/`** — @fe/AGENTS.md ⚠️ Next.js 16 có breaking changes so với kiến thức cũ; đọc guide trong `node_modules/next/dist/docs/` trước khi viết code FE. Quy ước thư mục & lệnh ở [fe/README.md](fe/README.md).

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
- Đặt logic vào `services/`/`repositories/`, **không** để business logic trong route handler.

## Frontend (tóm tắt)

- App Router; các trang hiện có: `/` (landing), `/auth`, `/chat`, `/admin`.
- Alias path: `@/*` trỏ về gốc `fe/` (ví dụ `import x from "@/app/lib/..."`).
- UI port từ thiết kế "Lumina" (xem memory [[lumina-design-source]]).

## Môi trường & quy ước

- **OS: Windows + PowerShell.** Đường dẫn dùng `\`. Tạo venv: `py -3.14 -m venv .venv` rồi `.venv\Scripts\activate`.
- Biến môi trường BE đọc từ `be/.env` (copy từ `be/.env.example`) — **không commit `.env`**.
- CI (`.github/workflows/python-app.yml`) chỉ chạy cho backend khi push/PR vào `main`: flake8 + pytest.
- Code & tài liệu trong dự án viết bằng **tiếng Việt**; giữ nhất quán khi thêm comment/doc.
