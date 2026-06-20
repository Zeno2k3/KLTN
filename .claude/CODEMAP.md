<!-- Bản đồ mã — giữ NGẮN GỌN (nạp vào ngữ cảnh mỗi phiên). Cập nhật khi cấu trúc đổi. -->

## Backend `be/` (FastAPI async)

- Điểm vào: [be/app/main.py](be/app/main.py) — tạo `app`, CORS, lifespan (init/close Redis), mount `api_router`, route `/`.
- Khởi chạy dev: [be/scripts/run.py](be/scripts/run.py) (uvicorn). Seed dữ liệu: [be/scripts/seed.py](be/scripts/seed.py).
- Định tuyến: [be/app/api/v1/router.py](be/app/api/v1/router.py) gắn các route dưới `/api/v1`.
  - Health: [be/app/api/v1/routes/health.py](be/app/api/v1/routes/health.py)
  - Auth: [be/app/api/v1/routes/auth.py](be/app/api/v1/routes/auth.py) (register/login/google/logout/me/refresh)
- Dependencies (current user, role guard): [be/app/api/deps.py](be/app/api/deps.py)
- Core:
  - Cấu hình (pydantic-settings, đọc `.env`): [be/app/core/config.py](be/app/core/config.py)
  - DB async (engine, `AsyncSessionLocal`, `Base`, `get_db`): [be/app/core/database.py](be/app/core/database.py)
  - JWT + băm mật khẩu (bcrypt): [be/app/core/security.py](be/app/core/security.py)
  - Redis async + blacklist JWT khi logout: [be/app/core/redis.py](be/app/core/redis.py)
- Nghiệp vụ auth (register/login/google/logout): [be/app/services/auth_service.py](be/app/services/auth_service.py)
- Truy cập dữ liệu: [be/app/repositories/](be/app/repositories/) (`user_repository.py`, `role_repository.py`)
- Model (SQLModel/SQLAlchemy): [be/app/models/](be/app/models/) — `user`, `role`, `conversation`, `message`, `document`, `evaluation`, `feedback`, `base`.
- Schema request/response: [be/app/schemas/auth.py](be/app/schemas/auth.py)
- Migration Alembic: [be/alembic/versions/](be/alembic/versions/) — KHÔNG sửa DB tay; mọi đổi schema qua đây.
- Test: [be/tests/conftest.py](be/tests/conftest.py) (SQLite in-memory + Redis giả + Google giả), `test_health.py`, `test_auth.py`.
- **RAG (LlamaIndex/Weaviate/RAGAS/Phoenix): CHƯA có trong code** — model `document/conversation/message/evaluation/feedback` đã có nhưng pipeline retrieval chưa dựng. Khi thêm: đặt service riêng + bắt buộc skill `rag-eval`.

## Frontend `fe/` (Next.js 16 App Router, React 19)

- Layout gốc + providers: [fe/app/layout.tsx](fe/app/layout.tsx), [fe/app/_providers/](fe/app/_providers/) (`AuthProvider`, `ToastProvider`, `Providers`).
- Trang & cụm component theo route (private folder `_components`):
  - Landing: [fe/app/page.tsx](fe/app/page.tsx) + [fe/app/_components/](fe/app/_components/)
  - Auth (login/register): [fe/app/auth/page.tsx](fe/app/auth/page.tsx) + [fe/app/auth/_components/](fe/app/auth/_components/) (`AuthForm`, `AuthBrandPanel`)
  - Chat: [fe/app/chat/page.tsx](fe/app/chat/page.tsx) + [fe/app/chat/_components/](fe/app/chat/_components/) (`ChatThread`, `MessageBubble`, `Composer`, `ChatSidebar`…)
  - Admin: [fe/app/admin/page.tsx](fe/app/admin/page.tsx) + [fe/app/admin/_components/](fe/app/admin/_components/) (`StatsView`, `DocsView`, `PdfDropzone`…)
- Design system dùng lại: [fe/app/components/ui/](fe/app/components/ui/) (`Button`, `TextField`, `Avatar`, `Badge`, `Icon`…), [fe/app/components/common/](fe/app/components/common/) (`AppHeader`, `UserMenu`).
- Gọi backend (cookie auth, tự refresh khi 401): [fe/app/lib/api.ts](fe/app/lib/api.ts)
- Hook: [fe/app/hooks/](fe/app/hooks/) (`useChat`, `useDocuments`). Tiện ích: [fe/app/lib/time.ts](fe/app/lib/time.ts). Dữ liệu mẫu: [fe/app/lib/data/](fe/app/lib/data/).
- Kiểu TS: [fe/app/types/](fe/app/types/) (`auth`, `chat`, `admin`). Theme/Tailwind v4: [fe/app/globals.css](fe/app/globals.css).
- Alias import: `@/*` → gốc `fe/` (vd `@/app/lib/api`).
- Test (vitest + jsdom): cạnh file nguồn, đặt tên `*.test.ts(x)`.
