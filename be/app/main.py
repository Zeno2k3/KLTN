import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.observability import init_tracing
from app.core.redis import close_redis, init_redis
from app.rag import query_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    init_tracing()  # OTEL → Phoenix (no-op nếu tắt); trước khi có request RAG
    await init_redis()
    if settings.rerank_warmup:
        # Nạp model reranker 1 lần lúc startup (qua thread, không kẹt event loop) → request
        # đầu của người dùng không phải gánh chi phí tải model. Lỗi warm-up KHÔNG chặn app.
        try:
            await asyncio.to_thread(query_engine.warmup)
        except Exception:
            logger.exception(
                "Warm-up reranker thất bại — app vẫn khởi động bình thường."
            )
    yield
    # shutdown
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"name": settings.app_name, "version": settings.app_version}
