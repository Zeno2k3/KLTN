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

## Quan sát & bảo mật

- Tracing: Arize Phoenix qua OpenInference (móc vào llama-index-instrumentation). Lỗi runtime → Sentry.
- Auth: JWT (python-jose), mật khẩu băm bằng passlib/bcrypt. KHÔNG log token hay PII.
- Bí mật qua biến môi trường (.env, không commit).

## Test

- Chạy: `python -m pytest -q`. Test là async (pytest-asyncio).
- Endpoint mới hoặc thay đổi pipeline phải có test trước khi coi là xong.
