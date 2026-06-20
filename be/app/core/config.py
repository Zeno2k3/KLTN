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

    # OpenAI (embedding tài liệu RAG)
    openai_api_key: str = ""
    openai_embed_model: str = "text-embedding-3-small"

    # Weaviate Cloud (vector store)
    weaviate_url: str = ""
    weaviate_api_key: str = ""
    weaviate_collection: str = "DocumentChunk"

    # Chunking (SentenceSplitter)
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Arize Phoenix (tracing LLM/embedding qua OTEL). Tắt → không khởi tạo tracing.
    phoenix_enabled: bool = True
    phoenix_collector_endpoint: str = ""
    phoenix_api_key: str = ""
    phoenix_project_name: str = "kltn-rag"


settings = Settings()
