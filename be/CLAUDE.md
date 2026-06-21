# Backend (be/) — FastAPI + RAG (pip)

## Môi trường & quy ước

- FastAPI + Uvicorn, Python 3.14, Pydantic v2. Endpoint là `async def`, inject bằng `Depends()`.
- Quản lý package bằng pip + venv. Activate venv trước khi chạy lệnh
  (hook cũng tự dò be/.venv, be/venv, be/env).
- Lint/format: ruff. Test: pytest + pytest-asyncio (+ coverage qua pytest-cov).

## Dữ liệu: SQLModel + SQLAlchemy 2 (async) — BẮT BUỘC async

- Model là lớp `SQLModel`. Truy vấn: `await session.exec(select(Model)...)` với `AsyncSession`.
- DB thật: PostgreSQL qua `asyncpg`. Test: SQLite qua `aiosqlite`.
- KHÔNG dùng engine đồng bộ hay `session.query(...)` kiểu cũ trong đường request (kẹt event loop).
- Mọi thay đổi schema PHẢI qua migration Alembic; không sửa DB thủ công.

## RAG: LlamaIndex Workflows + OpenAI

- Pipeline dựng bằng llama-index-workflows; embedding/LLM qua OpenAI (openai v2; tiktoken đếm token; nltk xử lý text).
- Vector store: Weaviate Cloud _nếu đã nối_ — hiện CHƯA thấy client trong requirements
  (cần: pip install llama-index-vector-stores-weaviate weaviate-client). Mặc định LlamaIndex
  dùng vector store in-memory.
- Redis (redis.asyncio) dùng cache.
- Sửa pipeline (chunking/embedding/retriever/prompt) = thay đổi CÓ RỦI RO hồi quy → kích hoạt skill rag-eval.

### Reranker — mặc định Cohere API (tránh "5 phút"/treo)

- **Bối cảnh:** cross-encoder local `namdp-ptit/ViRanker` = **2.2GB** (XLM-RoBERTa-large). Trên máy
  RAM thấp (vd 7.8GB tổng / <1GB trống) → nạp model **swap đĩa cực chậm rồi segfault**
  (ACCESS_VIOLATION). Đó là "5 phút chưa xong" + "lỗi luôn hệ thống" — KHÔNG phải mạng (tải file
  chỉ ~1s).
- **Giải pháp:** `RERANK_PROVIDER=cohere` (mặc định) → `CohereRerank` (rerank-multilingual-v3.0)
  gọi API: **0 RAM, không tải model, đa ngữ tiếng Việt**. Cần `COHERE_API_KEY` (dashboard.cohere.com).
  Query + đoạn ngữ cảnh gửi tới Cohere; pipeline vốn đã gửi dữ liệu này lên OpenAI nên chỉ thêm
  một nhà cung cấp nhận dữ liệu, không thêm bề mặt PII mới.
- **Tùy chọn local:** máy đủ RAM có thể đặt `RERANK_PROVIDER=sentence-transformers` +
  `RERANK_MODEL=namdp-ptit/ViRanker`; khi đó dùng `RERANK_WARMUP`/`HF_*` (cache + offline).
- `RAG_TIMEOUT_SECONDS`: pipeline vượt ngưỡng → **503 thân thiện** (không treo). Đổi reranker/model
  là thay đổi retrieval → chạy `rag-eval` (RAGAS) trước khi coi là xong.

## Quan sát & bảo mật

- Tracing: Arize Phoenix qua OpenInference (móc vào llama-index-instrumentation). Lỗi runtime → Sentry.
- Auth: JWT (python-jose), mật khẩu băm bằng passlib/bcrypt. KHÔNG log token hay PII.
- Bí mật qua biến môi trường (.env, không commit).

## Test

- Chạy: `python -m pytest -q`. Test là async (pytest-asyncio).
- Endpoint mới hoặc thay đổi pipeline phải có test trước khi coi là xong.
