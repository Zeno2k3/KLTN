from pydantic import field_validator
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

    # LlamaParse (LlamaCloud) — parse PDF/DOCX → markdown sạch theo trang; server lo OCR/bảng/font/dấu.
    # Gọi REST API trực tiếp bằng httpx (SDK llama-cloud dùng pydantic.v1 → vỡ trên Python 3.14).
    llama_cloud_api_key: str = ""
    llamaparse_base_url: str = "https://api.cloud.llamaindex.ai/api/v1/parsing"
    llamaparse_language: str = "vi"  # ngôn ngữ OCR/parse
    llamaparse_poll_interval: float = 3.0  # giây giữa các lần poll trạng thái job
    llamaparse_max_wait_seconds: float = 180.0  # trần chờ job hoàn tất (vượt → ingest failed)
    llamaparse_http_timeout: float = 120.0  # timeout mỗi request httpx (upload/poll/result)

    # Chunking — LLM chunker trên markdown LlamaParse (xem app/rag/md_chunker.py).
    # Block = item LlamaParse (heading/text/table). LLM GỘP block liền kề + sinh context; code ghép
    # nội dung VERBATIM. ``chunk_size`` là NGƯỠNG MỀM gộp block nhỏ ở fallback; ``chunk_overlap`` fallback.
    chunk_size: int = 512
    chunk_overlap: int = 64
    # LLM chunker: model RIÊNG (rỗng → fallback openai_chat_model). KHÔNG dùng singleton LLM chung.
    chunker_model: str = ""
    chunk_llm_enabled: bool = True  # tắt → fallback gộp block theo kích thước (xác định, không gọi LLM)
    # Region (batch block) <= ngưỡng token này → emit fallback, KHÔNG gọi LLM (tiết kiệm token).
    chunk_llm_min_tokens: int = 400
    # Trần token mỗi batch block gửi LLM (chặn prompt quá to với tài liệu dài).
    chunk_llm_region_max_tokens: int = 2500

    # Retrieval hybrid (BM25 keyword + vector semantic, hợp nhất RRF)
    # alpha=1.0 thuần vector, 0.0 thuần keyword; 0.6 ⇒ ưu tiên 60% semantic / 40% keyword.
    hybrid_alpha: float = 0.6
    retrieval_top_k: int = 30  # số ứng viên sau hybrid+RRF, trước khi rerank

    # Lọc metadata khi truy xuất (app/rag/query_filters.py). Trích năm học + phường/xã TỪ CÂU HỎI
    # rồi dựng MetadataFilters (EQ, AND) áp cho cả nhánh BM25 lẫn vector. Chỉ lọc khi câu hỏi nêu rõ.
    query_filter_enabled: bool = True
    # Fallback an toàn: filter ra 0 kết quả → retry KHÔNG filter (tránh "biến mất" tài liệu do
    # over-filter hoặc object Weaviate cũ thiếu property). Đặt False để thấy đúng kết quả-rỗng.
    filter_fallback_on_empty: bool = True

    # Tiền xử lý truy vấn (chạy TRƯỚC retrieve, trong cùng span rag.answer).
    # - Router: phân loại câu hỏi "rag" (cần tài liệu) vs "direct" (chào hỏi/ngoài phạm vi → LLM
    #   trả lời thẳng, không truy hồi) → chặn câu lạc đề bị kéo nhầm chunk tương đồng.
    # - Rewrite (condense-question): viết lại câu follow-up thành câu độc lập theo lịch sử để
    #   truy hồi đúng (giải bài toán hội thoại đa lượt). Chỉ chạy khi có lịch sử.
    query_router_enabled: bool = True
    query_rewrite_enabled: bool = True
    # Sliding window: số message gần nhất của hội thoại đưa vào router/rewriter (bao token).
    chat_history_window: int = 5
    # Model RIÊNG từng bước (rỗng → fallback openai_chat_model). Để sau này gắn model rẻ/nhanh cho
    # router/rewriter mà không đụng model synthesize chính. KHÔNG dùng singleton LLM chung.
    router_model: str = ""
    rewrite_model: str = ""

    # Reranker. provider="cohere" → API đa ngữ (0 RAM, nhanh; mặc định vì ViRanker 2.2GB
    # không nạp nổi trên máy RAM thấp → segfault). provider="sentence-transformers" → local.
    rerank_provider: str = "cohere"  # "cohere" | "sentence-transformers"
    # Tên model THEO provider: Cohere → "rerank-multilingual-v3.0"; local → "namdp-ptit/ViRanker".
    rerank_model: str = "rerank-multilingual-v3.0"
    rerank_top_n: int = 6  # số chunk cuối cùng đưa vào LLM
    cohere_api_key: str = (
        ""  # bắt buộc khi provider="cohere" (lấy ở dashboard.cohere.com)
    )

    # Nạp sẵn (warm-up) reranker lúc startup. CHỈ cần cho reranker LOCAL (nạp model); với
    # Cohere API để False (tránh tốn 1 call thừa). Tắt ở test/CI.
    rerank_warmup: bool = False
    # Số luồng CPU cho cross-encoder LOCAL (0 = giữ mặc định torch). Không áp cho Cohere.
    rerank_num_threads: int = 0

    # HuggingFace Hub (CHỈ dùng khi provider="sentence-transformers"). Sau khi pre-download về
    # cache, bật offline để khởi tạo chỉ đọc đĩa thay vì gọi mạng.
    hf_home: str = ""  # thư mục cache model (rỗng = mặc định ~/.cache/huggingface)
    hf_token: str = (
        ""  # tùy chọn: hết warning "unauthenticated" + tải nhanh hơn lần đầu
    )
    hf_hub_offline: bool = False  # True SAU KHI đã có cache: khởi tạo không chạm mạng

    # Timeout (giây) cho toàn pipeline RAG; vượt → 503 thân thiện thay vì treo vô hạn.
    rag_timeout_seconds: float = 60.0

    # Hậu kiểm trích nguồn (post-hoc citation attribution + verification). Chạy SAU synthesize:
    # gán đúng nguồn cho từng câu (attribution + verbatim quote) rồi judge support/in_scope → DROP
    # câu sai phạm vi/không nguồn, sửa marker lệch. Fail-safe: lỗi/timeout → giữ answer gốc, KHÔNG
    # chặn. Mặc định tắt để rollout an toàn (bật qua .env sau khi rag-eval xác nhận cải thiện).
    citation_verify_enabled: bool = False
    verifier_timeout_seconds: float = (
        20.0  # timeout riêng bước verify (nằm trong rag_timeout chung)
    )
    # LLM RIÊNG cho bước verify (rỗng → fallback openai_chat_model). KHÔNG dùng singleton LLM chung.
    # Một call structured-output làm cả attribution (gán nguồn + verbatim quote) lẫn judge.
    verifier_model: str = ""

    # Arize Phoenix (tracing LLM/embedding qua OTEL). Tắt → không khởi tạo tracing.
    phoenix_enabled: bool = True
    phoenix_collector_endpoint: str = ""
    phoenix_api_key: str = ""
    phoenix_project_name: str = "kltn-rag"

    @field_validator("database_url", mode="after")
    @classmethod
    def _force_asyncpg_driver(cls, v: str) -> str:
        """Ép driver async cho Postgres URL do host cấp.

        Render/Railway/Heroku cấp ``DATABASE_URL`` dạng ``postgres://`` hoặc
        ``postgresql://`` (driver đồng bộ). App + Alembic chạy async toàn bộ nên cần
        ``postgresql+asyncpg://``. URL đã ghi rõ ``+asyncpg`` (hoặc dialect khác) giữ
        nguyên — chỉ vá khi thiếu driver.
        """
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v


settings = Settings()
