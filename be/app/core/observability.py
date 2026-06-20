"""Khởi tạo tracing Arize Phoenix (OTEL) cho các cuộc gọi LLM/embedding qua LlamaIndex.

Guard bằng ``settings.phoenix_enabled`` + có endpoint — tắt thì no-op để dev/test chạy
được mà không cần Phoenix. Mọi lỗi khởi tạo chỉ log cảnh báo, KHÔNG làm sập app
(tracing là phụ trợ, không phải đường dữ liệu chính).
"""

import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

_initialized = False


def init_tracing() -> None:
    """Bật OTEL tracing → Phoenix. Idempotent; gọi 1 lần khi app khởi động."""
    global _initialized
    if _initialized:
        return
    if not settings.phoenix_enabled or not settings.phoenix_collector_endpoint:
        logger.info(
            "Phoenix tracing tắt (phoenix_enabled=%s, có endpoint=%s).",
            settings.phoenix_enabled,
            bool(settings.phoenix_collector_endpoint),
        )
        return
    try:
        from phoenix.otel import register

        # Phoenix Cloud xác thực bằng api key qua biến môi trường.
        if settings.phoenix_api_key:
            os.environ.setdefault("PHOENIX_API_KEY", settings.phoenix_api_key)

        # Endpoint cấu hình thường là URL space gốc; OTLP/HTTP cần path "/v1/traces"
        # (nếu thiếu, exporter POST vào gốc → 405 Method Not Allowed).
        endpoint = settings.phoenix_collector_endpoint.rstrip("/")
        if not endpoint.endswith("/v1/traces"):
            endpoint = f"{endpoint}/v1/traces"

        # auto_instrument=True tự gắn openinference-instrumentation-llama-index →
        # mọi embedding/LLM đi qua LlamaIndex được trace (không có đường gọi "mù").
        register(
            endpoint=endpoint,
            project_name=settings.phoenix_project_name,
            auto_instrument=True,
            set_global_tracer_provider=True,
        )
        _initialized = True
        logger.info(
            "Phoenix tracing đã bật → %s (project=%s)",
            settings.phoenix_collector_endpoint,
            settings.phoenix_project_name,
        )
    except Exception:  # noqa: BLE001 — tracing phụ trợ, không được làm sập app
        logger.exception("Không khởi tạo được Phoenix tracing — bỏ qua, app vẫn chạy.")
