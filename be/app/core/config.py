from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "KLTN API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/kltn_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-this-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Cookie (httpOnly cookie giữ access/refresh token)
    cookie_secure: bool = False  # True khi chạy production qua HTTPS
    cookie_samesite: str = "lax"  # dev cùng localhost: "lax"; prod khác domain: "none"
    cookie_domain: str | None = None

    # Google OAuth (đăng nhập bằng Google — xác thực ID token ở backend)
    google_client_id: str = ""

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Lưu trữ file PDF tải lên (đường dẫn tương đối gốc be/ hoặc tuyệt đối)
    upload_dir: str = "storage/uploads"
    max_upload_mb: int = 25

    # OpenAI (embedding tài liệu RAG + LLM tổng hợp câu trả lời)
    openai_api_key: str = ""
    openai_embed_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    # Weaviate Cloud (vector store)
    weaviate_url: str = ""
    weaviate_api_key: str = ""
    weaviate_collection: str = "DocumentChunk"
    # Tên property chứa text trong collection (LlamaIndex mặc định "text"); BM25 chỉ
    # nên chấm điểm property này (tránh nhiễu từ "_node_content").
    weaviate_text_key: str = "text"

    # Chunking (SentenceSplitter)
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Retrieval hybrid (BM25 keyword + vector semantic, hợp nhất RRF)
    # alpha=1.0 thuần vector, 0.0 thuần keyword; 0.6 ⇒ ưu tiên 60% semantic / 40% keyword.
    hybrid_alpha: float = 0.6
    retrieval_top_k: int = 30  # số ứng viên sau hybrid+RRF, trước khi rerank

    # Reranker. provider="cohere" → API đa ngữ (0 RAM, nhanh; mặc định vì ViRanker 2.2GB
    # không nạp nổi trên máy RAM thấp → segfault). provider="sentence-transformers" → local.
    rerank_provider: str = "cohere"  # "cohere" | "sentence-transformers"
    # Tên model THEO provider: Cohere → "rerank-multilingual-v3.0"; local → "namdp-ptit/ViRanker".
    rerank_model: str = "rerank-multilingual-v3.0"
    rerank_top_n: int = 6  # số chunk cuối cùng đưa vào LLM
    cohere_api_key: str = ""  # bắt buộc khi provider="cohere" (lấy ở dashboard.cohere.com)

    # Nạp sẵn (warm-up) reranker lúc startup. CHỈ cần cho reranker LOCAL (nạp model); với
    # Cohere API để False (tránh tốn 1 call thừa). Tắt ở test/CI.
    rerank_warmup: bool = False
    # Số luồng CPU cho cross-encoder LOCAL (0 = giữ mặc định torch). Không áp cho Cohere.
    rerank_num_threads: int = 0

    # HuggingFace Hub (CHỈ dùng khi provider="sentence-transformers"). Sau khi pre-download về
    # cache, bật offline để khởi tạo chỉ đọc đĩa thay vì gọi mạng.
    hf_home: str = ""  # thư mục cache model (rỗng = mặc định ~/.cache/huggingface)
    hf_token: str = ""  # tùy chọn: hết warning "unauthenticated" + tải nhanh hơn lần đầu
    hf_hub_offline: bool = False  # True SAU KHI đã có cache: khởi tạo không chạm mạng

    # Timeout (giây) cho toàn pipeline RAG; vượt → 503 thân thiện thay vì treo vô hạn.
    rag_timeout_seconds: float = 60.0

    # Arize Phoenix (tracing LLM/embedding qua OTEL). Tắt → không khởi tạo tracing.
    phoenix_enabled: bool = True
    phoenix_collector_endpoint: str = ""
    phoenix_api_key: str = ""
    phoenix_project_name: str = "kltn-rag"


settings = Settings()
