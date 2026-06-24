# syntax=docker/dockerfile:1
#
# Image deploy cho backend RAG (be/). Dùng được trên Render, Railway, Fly.io, Cloud Run...
# Build 2 tầng: tầng builder có sẵn compiler (phòng gói nào không có wheel cho linux/py3.14),
# tầng runtime chỉ copy site-packages đã cài → image gọn, không kèm compiler.
#
# Reranker mặc định là Cohere API nên image KHÔNG cài torch/transformers/sentence-transformers
# (xem requirements-deploy.txt). Nếu đổi sang reranker LOCAL, build với requirements.txt đầy đủ.

# ---------- Tầng builder: cài dependencies ----------
FROM python:3.14-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# build-essential: phòng trường hợp một gói chỉ có sdist (phải biên dịch). Không lọt vào image cuối.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-deploy.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-deploy.txt

# ---------- Tầng runtime: gọn, chỉ chứa thứ cần để chạy ----------
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy packages + scripts (uvicorn, alembic) đã cài từ tầng builder.
COPY --from=builder /install /usr/local

# Copy mã nguồn (xem .dockerignore để biết phần bị loại: venv, tests, eval, storage, .env...).
COPY . .

# Render/Railway tự cấp PORT qua biến môi trường; fallback 8000 khi chạy local.
ENV PORT=8000
EXPOSE 8000

# Chạy migration (idempotent) rồi khởi động server. Dùng sh -c để $PORT được giãn nở.
# Lưu ý: nếu scale > 1 instance, nên chuyển "alembic upgrade head" sang lệnh pre-deploy của
# nền tảng (vd Render preDeployCommand) để tránh nhiều instance migrate đồng thời.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
