# Dự án: Agent Tư vấn Tuyển sinh Tiểu học (RAG)

Hệ thống hỏi-đáp RAG tư vấn tuyển sinh tiểu học cho phụ huynh.

## Kiến trúc

- Monorepo: `be/` (API + RAG pipeline), `fe/` (giao diện chat)
- Backend: FastAPI · Python 3.14 · SQLModel + SQLAlchemy 2 (async, asyncpg) · Alembic
  · Redis (async) · LlamaIndex Workflows + OpenAI · pip + venv
- Frontend: Next.js 16 (App Router) · React 19 · TypeScript · Tailwind v4
- Dữ liệu: PostgreSQL · Weaviate Cloud (vector store)
- Quan sát: Arize Phoenix (tracing) + Sentry (lỗi runtime)
- Đánh giá: RAGAS (faithfulness, answer relevancy, context precision/recall)

## Build & test (chạy để kiểm chứng — không bao giờ báo xong nếu chưa chạy)

- Backend (activate venv trước): cd be && ruff check . && python -m pytest -q
- Frontend: cd fe && npm run lint && npx tsc --noEmit && CI=true npm test (test = vitest + jsdom)

## Quy tắc cứng (dữ kiện, không phải lời đề nghị)

- Backend async toàn bộ: truy cập DB qua AsyncSession (`await session.exec(select(...))`); không gọi hàm chặn trong đường async.
- Mọi thay đổi schema DB phải qua migration Alembic; không sửa DB thủ công.
- Không bao giờ tuyên bố hoàn thành cho đến khi hook verify pass VÀ có bằng chứng.
- Thay đổi retrieval / prompt / embedding phải chạy RAGAS eval trước khi coi là xong.
- Mỗi cuộc gọi LLM/retrieval phải được trace qua Phoenix; không thêm đường gọi OpenAI "mù".
- PII học sinh/phụ huynh: không ghi log, không gửi ra ngoài phạm vi cần thiết. Không log token JWT.
- Bí mật (OPENAI*API_KEY, DATABASE_URL, WEAVIATE*\*, SENTRY_DSN) chỉ qua biến môi trường; không hardcode.
- Mỗi phiên một tính năng; cập nhật PROGRESS.md trước khi dừng.

## Định nghĩa "Xong" (Definition of Done)

Suite test xanh là điều kiện CẦN nhưng CHƯA ĐỦ. "Suite xanh" ≠ "tính năng chạy được" —
nếu tính năng mới chưa có test bao phủ thì suite xanh không chứng minh được gì.

Một tính năng chỉ "Xong" khi HỘI ĐỦ:

1. Gate xanh: `ruff check` + `pytest` (BE) và `lint` + `tsc` (FE) đều pass.
2. **Đường code mới được CHẠY THẬT ít nhất một lần** (không chỉ chạy suite test):
   - Endpoint API → gọi thật (curl/httpx) và dán request + response thật.
   - Màn hình/giao diện → chụp màn hình và đọc lại bằng công cụ Read.
   - Thay đổi RAG → chạy `rag-eval` (RAGAS + trace Phoenix), đính kèm số.
3. Mỗi tính năng mới đi kèm ÍT NHẤT một test bao phủ đường code đó (đỏ-trước-khi-sửa,
   xanh-sau-khi-sửa). Không thêm code mới mà bỏ trống test.
4. Bằng chứng (output lệnh / ảnh / trace) đã được mở và đưa cho người dùng xem.

Nếu thiếu bất kỳ mục nào ở trên: CHƯA xong — nói rõ mục nào thiếu, đừng tuyên bố hoàn thành.

## Compact Instructions

Giữ lại: danh sách việc đang làm; thay đổi schema DB (Alembic) và lý do; thay đổi prompt;
kết quả RAGAS gần nhất; lỗi + cách sửa; danh sách file đã sửa.
