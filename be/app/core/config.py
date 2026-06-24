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

    # Chunking — structure-aware + LLM chunker (xem app/rag/chunker.py).
    # LƯU Ý NGỮ NGHĨA: ``chunk_size`` KHÔNG còn là cap cứng. Khoản là đơn vị nguyên tử
    # (1 Khoản = 1 chunk, không bao giờ cắt giữa Khoản dù dài). ``chunk_size`` chỉ là NGƯỠNG MỀM
    # để GỘP nhiều Khoản nhỏ liền kề vào cùng một chunk; một Khoản đơn vượt ngưỡng vẫn giữ nguyên.
    chunk_size: int = 512
    chunk_overlap: int = 64
    # LLM chunker: model RIÊNG cho bước chia chunk (rỗng → fallback openai_chat_model).
    # KHÔNG dùng singleton LLM chung (mỗi bước RAG giữ LLM/model riêng).
    chunker_model: str = ""
    chunk_llm_enabled: bool = (
        True  # tắt → chỉ dùng rule-based (xác định, không gọi LLM)
    )
    # Section <= ngưỡng này → emit thẳng 1 chunk, KHÔNG gọi LLM chia (tiết kiệm chi phí token).
    chunk_llm_min_tokens: int = 400

    # OCR — tầng fallback cho PDF scan ảnh (không có lớp text). Render trang → ảnh → OpenAI Vision
    # (qua LlamaIndex ImageBlock → Phoenix auto-trace). Chỉ chạy cho trang bị đánh dấu cần OCR.
    ocr_enabled: bool = True
    ocr_provider: str = (
        "openai"  # "openai" (vision-LLM) | "tesseract" (chưa triển khai)
    )
    ocr_model: str = ""  # rỗng → fallback openai_chat_model (gpt-4o-mini có vision)
    # Trang có text-layer < ngưỡng ký tự (và không có bảng thật) → coi là trang scan cần OCR.
    ocr_min_chars: int = 50
    ocr_dpi: int = 200  # DPI render trang → ảnh (cân chất lượng OCR vs token ảnh)
    ocr_max_pages: int = (
        50  # số trang scan/tài liệu vượt ngưỡng → ingest FAILED (chặn cost token)
    )
    ocr_timeout_seconds: float = (
        60.0  # timeout mỗi call vision (tránh treo cả lượt OCR)
    )

    # Phát hiện text native-PDF bị mojibake (font VNI/TCVN3 hoặc subset-font thiếu ToUnicode CMap →
    # pdfminer.six trả codepoint sai). Trang garbled được thử lại bằng PDFium rồi mới fallback OCR.
    garbled_detect_enabled: bool = True  # cờ tắt khẩn cấp (rollback không cần deploy)
    garbled_min_chars: int = (
        200  # gate độ dài: dưới ngưỡng KHÔNG kết luận garbled (chống oan)
    )
    garbled_min_words: int = 20  # tối thiểu số từ mới xét tín hiệu stopword
    garbled_stopword_ratio: float = (
        0.03  # tỉ lệ trúng stopword tiếng Việt < ngưỡng → nghi garbled
    )
    garbled_foreign_ratio: float = (
        0.20  # tỉ lệ ký tự "lạ" (symbol) > ngưỡng → nghi garbled
    )
    # Ký tự RÁC chắc chắn (PUA / control / replacement / unassigned — subset-font thiếu ToUnicode hay
    # sinh ra) — ngưỡng thấp vì chỉ cần vài % là đủ kết luận font hỏng.
    garbled_suspicious_ratio: float = 0.02
    # Mật độ ký tự CÓ DẤU tiếng Việt tối thiểu: font hỏng kiểu PHỔ BIẾN NHẤT map glyph có dấu về chữ
    # ASCII trần ("CỘNG HÒA"→"CONG HOA") → text là tiếng Việt nhưng ~0% ký tự dấu. Dưới ngưỡng + vẫn
    # nhận ra là tiếng Việt (đủ stopword) → diacritic bị strip → route OCR để lấy lại dấu.
    garbled_diacritic_ratio: float = 0.01

    # Retrieval hybrid (BM25 keyword + vector semantic, hợp nhất RRF)
    # alpha=1.0 thuần vector, 0.0 thuần keyword; 0.6 ⇒ ưu tiên 60% semantic / 40% keyword.
    hybrid_alpha: float = 0.6
    retrieval_top_k: int = 30  # số ứng viên sau hybrid+RRF, trước khi rerank

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
