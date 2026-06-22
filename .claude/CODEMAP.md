<!-- Bản đồ mã — giữ NGẮN GỌN (nạp vào ngữ cảnh mỗi phiên). Cập nhật khi cấu trúc đổi. -->

## Backend `be/` (FastAPI async)

- Điểm vào: [be/app/main.py](be/app/main.py) — tạo `app`, CORS, lifespan (`init_tracing` Phoenix + init/close Redis), mount `api_router`, route `/`.
- Khởi chạy dev: [be/scripts/run.py](be/scripts/run.py) (uvicorn). Seed dữ liệu: [be/scripts/seed.py](be/scripts/seed.py) (admin `admin@lumina.local`/`admin123`).
- Định tuyến: [be/app/api/v1/router.py](be/app/api/v1/router.py) gắn các route dưới `/api/v1`.
  - Health: [be/app/api/v1/routes/health.py](be/app/api/v1/routes/health.py)
  - Auth: [be/app/api/v1/routes/auth.py](be/app/api/v1/routes/auth.py) (register/login/google/logout/me/refresh)
  - **Documents (admin):** [be/app/api/v1/routes/documents.py](be/app/api/v1/routes/documents.py) — `/admin/documents` GET(list)/POST(upload)/DELETE(xoá tất cả), `/{id}` DELETE(xoá lẻ)/PATCH(đổi tên — DB-only), `/{id}/file?download=` GET(xem inline/tải attachment). Tất cả `require_admin`.
- Dependencies (current user, role guard `require_admin`): [be/app/api/deps.py](be/app/api/deps.py)
- Core:
  - Cấu hình (pydantic-settings, đọc `.env`): [be/app/core/config.py](be/app/core/config.py) — gồm `upload_dir/openai_*/weaviate_*/chunk_*/phoenix_*`.
  - DB async (engine, `AsyncSessionLocal`, `Base`, `get_db`): [be/app/core/database.py](be/app/core/database.py)
  - JWT + băm mật khẩu (bcrypt): [be/app/core/security.py](be/app/core/security.py)
  - Redis async + blacklist JWT khi logout: [be/app/core/redis.py](be/app/core/redis.py)
  - **Tracing Phoenix (OTEL):** [be/app/core/observability.py](be/app/core/observability.py) — `init_tracing()` guard `phoenix_enabled`, tự ghép `/v1/traces`.
- **RAG ingest:** [be/app/rag/](be/app/rag/) — `vector_store.py` (Weaviate Cloud + OpenAIEmbedding; `add_nodes/delete_objects/retrieve`), `ingest.py` (pypdf + SentenceSplitter + tiktoken). Mọi thay đổi → bắt buộc skill `rag-eval`.
- Nghiệp vụ: [be/app/services/auth_service.py](be/app/services/auth_service.py) (auth), [be/app/services/document_service.py](be/app/services/document_service.py) (upload + ingest NỀN + delete; `asyncio.to_thread`, commit ngay để ingest nền thấy row).
- Truy cập dữ liệu: [be/app/repositories/](be/app/repositories/) (`user_repository.py`, `role_repository.py`, `document_repository.py`).
- Model (SQLModel/SQLAlchemy): [be/app/models/](be/app/models/) — `user`, `role`, `conversation`, `message`, `document` (+`DocumentChunk`), `evaluation`, `feedback`, `base`.
- Schema request/response: [be/app/schemas/](be/app/schemas/) (`auth.py`, `document.py`).
- Lưu file PDF: `be/storage/uploads/` (gitignored). Migration Alembic: [be/alembic/versions/](be/alembic/versions/) — KHÔNG sửa DB tay.
- Test: [be/tests/conftest.py](be/tests/conftest.py) (SQLite in-memory + Redis giả + Google giả; fixture `admin_client/user_client`), `test_health.py`, `test_auth.py`, `test_documents.py`, `test_ingest.py`.
- **RAG truy vấn/answer (retriever→LLM, RAGAS faithfulness/answer_relevancy): CHƯA dựng** — mới có ingest + retrieval. Khi dựng query: thêm service + RAGAS đầy đủ.

## Frontend `fe/` (Next.js 16 App Router, React 19)

- Layout gốc + providers: [fe/app/layout.tsx](fe/app/layout.tsx), [fe/app/_providers/](fe/app/_providers/) (`AuthProvider`, `ToastProvider`, `Providers`).
- Trang & cụm component theo route (private folder `_components`):
  - Landing: [fe/app/page.tsx](fe/app/page.tsx) + [fe/app/_components/](fe/app/_components/)
  - Auth (login/register): [fe/app/auth/page.tsx](fe/app/auth/page.tsx) + [fe/app/auth/_components/](fe/app/auth/_components/) (`AuthForm`, `AuthBrandPanel`)
  - Chat: [fe/app/chat/page.tsx](fe/app/chat/page.tsx) + [fe/app/chat/_components/](fe/app/chat/_components/) (`ChatThread`, `MessageBubble`, `Composer`, `ChatSidebar`…)
  - Admin: [fe/app/admin/page.tsx](fe/app/admin/page.tsx) + [fe/app/admin/_components/](fe/app/admin/_components/) (`StatsView`, `DocsView`, `PdfDropzone`…)
- Design system dùng lại: [fe/app/components/ui/](fe/app/components/ui/) (`Button`, `TextField`, `Avatar`, `Badge`, `Icon`…), [fe/app/components/common/](fe/app/components/common/) (`AppHeader`, `UserMenu`).
- Gọi backend (cookie auth, tự refresh khi 401): [fe/app/lib/api.ts](fe/app/lib/api.ts) — `authApi` + `documentApi` (list/upload FormData/remove). Map DTO→Doc: [fe/app/lib/documents.ts](fe/app/lib/documents.ts).
- Hook: [fe/app/hooks/](fe/app/hooks/) (`useChat`; `useDocuments` gọi API THẬT — fetch/upload/delete + polling khi `processing`). Tiện ích: [fe/app/lib/time.ts](fe/app/lib/time.ts). Dữ liệu mẫu: [fe/app/lib/data/](fe/app/lib/data/).
- Kiểu TS: [fe/app/types/](fe/app/types/) (`auth`, `chat`, `admin`). Theme/Tailwind v4: [fe/app/globals.css](fe/app/globals.css).
- Alias import: `@/*` → gốc `fe/` (vd `@/app/lib/api`).
- Test (vitest + jsdom): cạnh file nguồn, đặt tên `*.test.ts(x)`.
