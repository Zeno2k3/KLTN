# PROGRESS

## 2026-06-22 — OCR fallback cho PDF scan ảnh (mọi loại PDF)

**Vấn đề:** PDF scan ảnh (không có lớp text) → pdfplumber ra rỗng → ingest báo lỗi
"Không trích xuất được văn bản". Cần xử lý MỌI loại PDF (text/scan/hỗn hợp).

**Giải pháp — pipeline trích xuất phân tầng (fail-last):**
- [Tầng 1] pdfplumber (PDF text) → mỗi trang đánh dấu `needs_ocr` nếu text-layer dưới ngưỡng.
- [Tầng 2] OCR chỉ trang scan: pypdfium2 render ảnh → **OpenAI Vision** (gpt-4o-mini) qua LlamaIndex
  `ImageBlock` → Phoenix auto-trace → ghi đè `page.text`. [be/app/rag/ocr.py](be/app/rag/ocr.py).
- [Tầng 3] structure + chunker như cũ. Chỉ raise lỗi khi cả OCR cũng rỗng.

**Quyết định (người dùng chọn):** OpenAI Vision (không dùng Tesseract local — máy RAM thấp, sai dấu,
mất bảng); model `gpt-4o-mini`; vượt `ocr_max_pages=50` → **ingest failed** (không để thiếu nội dung
mà báo ready).

**Fix theo phản biện đối kháng (workflow ultracode):**
- Phát hiện scan không chỉ dựa `len(text)<50`: chỉ loại khi **bảng có ô thật** (`_has_real_table`) +
  xét **độ phủ ảnh** (`_image_coverage`) → bắt cả trang scan có watermark/header text mỏng, tránh
  trang scan bị "bảng rỗng" của pdfplumber chặn OCR.
- `_get_llm` có `timeout` + `max_retries` (1 trang treo không kẹt cả lượt).
- Mở `PdfDocument` 1 lần/tài liệu; ảnh chỉ ở RAM (không ghi đĩa); log chỉ số trang (PII).
- Strip ```` ``` ```` mà vision model hay bọc quanh output.

**Bằng chứng:** ruff PASS · pytest **109 passed** (+8 test OCR). Verify thật: tạo PDF scan giả
(ảnh PIL chữ tiếng Việt, không lớp text) → `needs_ocr=True` → ingest **status=ready** (trước fail),
3 chunk khôi phục đúng tiếng Việt + heading_path (Điều 1/2) + Khoản nguyên vẹn. Đã dọn dẹp.

**File:** mới [ocr.py](be/app/rag/ocr.py), [test_ocr.py](be/tests/test_ocr.py); sửa
[config.py](be/app/core/config.py), [extract.py](be/app/rag/extract.py),
[document_service.py](be/app/services/document_service.py). Không cần migration.

**Hạn chế:** bảng trong trang scan → markdown inline trong text (`has_table=False`), không vào
`page.tables`. Tài liệu scan rất dài (>50 trang) → failed (tăng `OCR_MAX_PAGES` nếu cần).

---

## 2026-06-22 — Nâng cấp RAG Chunking (structure-aware + LLM + Contextual Retrieval)

**Mục tiêu:** sửa lỗi chunk cắt giữa Khoản, mất ngữ cảnh, không đọc bảng (văn bản hành chính VN).

### Đã làm
- **Trích xuất:** `pypdf` → `pdfplumber` ([be/app/rag/extract.py](be/app/rag/extract.py)) — đọc bảng,
  crop vùng bảng khỏi text (tránh trùng lặp). Bảng dùng `find_tables()` mặc định (lines); KHÔNG dùng
  text-strategy (tạo bảng giả từ văn xuôi).
- **Cấu trúc:** [be/app/rag/structure.py](be/app/rag/structure.py) — regex Phần/Mục/Điều/Khoản/Điểm/
  Phụ lục (Roman I–X), `segment()` → Section + `heading_path`.
- **Chunker:** [be/app/rag/chunker.py](be/app/rag/chunker.py) — **Khoản nguyên tử** (tách block theo
  Khoản trước; `chunk_size` = ngưỡng mềm gộp Khoản nhỏ, không cắt giữa Khoản). LLM **chỉ gộp block +
  sinh `context`** (content ghép verbatim, không bịa); fallback rule-based khi LLM lỗi. Bảng→markdown
  node độc lập (`has_table`). **Contextual Retrieval**: `context` prepend vào `node.text` (embed+BM25).
- **Metadata văn bản:** [be/app/rag/doc_metadata.py](be/app/rag/doc_metadata.py) — auto-extract
  doc_type/issued_date/issuing_body (regex + LLM).
- **DB:** migration `b2c3d4e5f6a7` thêm cột chunk (heading_path/context/chunk_type/has_table/
  page_number) + doc (doc_type/issued_date/issuing_body). Model [be/app/models/document.py].
- **Wiring:** [be/app/services/document_service.py](be/app/services/document_service.py) `ingest_document`
  dùng pipeline mới; lưu metadata cả Postgres lẫn Weaviate.
- **Fix Weaviate:** `TextNode` cần `ref_doc_id` (UUID) — `chunker._doc_ref_id` (uuid5) gán SOURCE,
  nếu không Weaviate từ chối (`doc_id/document_id` kiểu UUID, None không hợp lệ). `add_nodes` GIỜ raise
  khi `client.batch.failed_objects` (trước nuốt lỗi → ready nhưng 0 vector).
- **Test:** [be/tests/test_chunker.py](be/tests/test_chunker.py) (10 test) — Khoản không cắt, Khoản dài
  1 chunk, bảng độc lập, LLM fallback/fidelity, metadata, context prepend.

### Bằng chứng (đã chạy thật)
- Gate: `ruff check` PASS, `pytest` **101 passed**.
- Migration `alembic upgrade head` chạy thật trên PG; cột mới xác minh.
- Ingest thật 1 PDF (OpenAI+Weaviate): status=ready, 27–28 chunk, Weaviate 27 object có
  heading_path/chunk_type/doc_type, `text` bắt đầu bằng context; retrieve trả chunk mới + context LLM.
  doc_type=quyet_dinh, issued_date=16/06/2025 (auto-extract). Đã dọn doc verify.
- **Eval before/after** (cùng input, khác thuật toán): Khoản toàn vẹn OLD **87%** (40/46) → NEW
  **100%** (46/46); heading_path/context 0 → ~100%.

### Hạn chế / việc tiếp theo
- **RAGAS không chạy được trên Py3.14** (xem memory) → dùng eval Khoản-integrity + retrieval sanity
  thay thế. Cân nhắc venv riêng nếu cần số RAGAS đầy đủ.
- **Phoenix endpoint chưa cấu hình** ở env này (span `rag.ingest.chunk` + LLM qua LlamaIndex đã sẵn
  trace khi set endpoint).
- **Phải re-ingest tài liệu cũ** (doc 16) để có metadata mới (chunk cũ heading=None).
- `issuing_body` đôi khi dính dòng tiêu ngữ (header 2 cột bị pdfplumber gộp) — tinh chỉnh regex sau.
