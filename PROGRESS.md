# PROGRESS

## 2026-06-23 — Hậu kiểm trích nguồn (post-hoc citation attribution + verification)

**Vấn đề:** câu trả lời lẫn nội dung NGOÀI PHẠM VI câu hỏi (hỏi "đối tượng ưu tiên lớp 1" →
trả lời kèm cả "lớp 6"). KHÔNG phải citation ảo: marker `[n]` trỏ đúng chunk, nhưng chunk gộp
lớp 1 + lớp 6 trong cùng Điều; system prompt không yêu cầu lọc phạm vi → LLM tái tạo cả phần
lớp 6. `sources` lại dựng độc lập, không đối chiếu marker.

**Giải pháp (2 lớp, DROP, fail-safe — người dùng chọn):**
- **Lớp A** — `_SYSTEM_PROMPT` + `_user_prompt` ([query_engine.py](be/app/rag/query_engine.py)):
  thêm nguyên tắc LỌC THEO PHẠM VI (cấp lớp/năm/khu vực/đối tượng).
- **Lớp B** — module mới [citation_verifier.py](be/app/rag/citation_verifier.py): một LLM RIÊNG
  (verifier) đối chiếu TỪNG CÂU với nguồn đã retrieve → gán đúng nguồn (attribution) + trích
  `supporting_quote` verbatim + judge `supported`/`in_scope` → `keep|recite|drop`. DROP câu sai
  phạm vi/không nguồn, sửa marker lệch, lọc lại `sources`, gắn `cited_spans`. 1 call structured
  JSON. **Fail-safe:** lỗi/timeout/drop-hết → giữ answer gốc, `ok=False`, không chặn. Span
  `rag.citation_verify`. Tắt mặc định (`CITATION_VERIFY_ENABLED=false`) để rollout an toàn.
- **FE** — highlight SUB-CHUNK: `SourceOut.cited_spans` → drawer chỉ tô đúng đoạn câu trả lời dựa
  vào (không tô phần lớp 6). [citations.ts](fe/app/lib/citations.ts) `buildCitationDocument` khớp
  span (linh hoạt khoảng trắng, **fallback tô cả chunk** nếu không khớp → tương thích ngược).

**Quyết định:** LLM-judge hậu kỳ (KHÔNG ContextCite — không bắt được off-scope, tốn logits;
KHÔNG mô hình fine-tune — máy RAM thấp, không có bản tiếng Việt). DROP (sửa answer). Cơ sở:
post-hoc thắng generation-time về faithfulness cho high-stakes (paper 2509.21557).

**Bằng chứng (đã chạy thật):**
- Gate: `ruff check` PASS · pytest **120 passed** (+8 test verifier, +3 test pipeline);
  FE `lint`+`tsc`+`vitest` **75 passed** (+3 test highlight sub-chunk).
- **Chạy thật `verify_answer` với OpenAI gpt-4o-mini** (kịch bản lớp1/lớp6): câu "lớp 6"
  `in_scope=False` → **DROP**; answer sạch (`lop6_con_trong_answer=False`); `cited_spans` chứa
  quote nguyên văn; trace đẩy lên **Phoenix Cloud** (project kltn-rag). Đã dọn script tạm.

**File:** mới [citation_verifier.py](be/app/rag/citation_verifier.py),
[test_citation_verifier.py](be/tests/test_citation_verifier.py); sửa
[query_engine.py](be/app/rag/query_engine.py), [config.py](be/app/core/config.py),
[chat.py](be/app/schemas/chat.py), [test_query_engine.py](be/tests/test_query_engine.py); FE
[chat.ts](fe/app/types/chat.ts), [lib/chat.ts](fe/app/lib/chat.ts),
[citations.ts](fe/app/lib/citations.ts), [SourceDrawer.tsx](fe/app/components/common/SourceDrawer.tsx),
[SourceChips.tsx](fe/app/chat/_components/SourceChips.tsx). **Không cần migration** (cited_spans
nằm trong `context_sources` JSONB).

### Việc tiếp theo (cần stack sống — chưa làm)
- **E2E qua HTTP** (`CITATION_VERIFY_ENABLED=true` + uvicorn + Weaviate có dữ liệu + Cohere + auth):
  gọi endpoint chat câu lớp 1 thật, dán request+response, **chụp SourceDrawer** thấy chỉ đoạn lớp 1
  được tô sáng.
- **rag-eval golden set** (Lớp A đổi prompt mặc định → cần đo before/after scope precision, đảm bảo
  không under-answer). RAGAS không chạy Py3.14 → đo thủ công như các lần trước.
- Bật cờ sau khi eval xác nhận cải thiện. Cân nhắc tinh chỉnh prompt judge nếu drop nhầm.

---

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
