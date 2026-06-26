# PROGRESS

## 2026-06-27 — Lớp điều phối ĐA TÁC TỬ (event-driven multi-agent) sau pipeline tuyến tính

**Mục tiêu:** Nâng RAG mô-đun tuyến tính (`query_engine.answer_question`) lên hệ **đa tác tử** đúng
nghĩa (cho KLTN): Planner phân rã câu hỏi → nhiều Retrieval agent chạy SONG SONG (fan-out) → Synthesis
gộp đa nguồn (fan-in) → Critic phản biện + vòng viết lại (agent-to-agent). Dựng bằng
`llama-index-workflows` (đã có, trước nay chưa dùng). Nguyên tắc: TÁI DÙNG code đã test
(`route_query`/`retrieve_and_rerank`/`synthesize`/`citation_verifier`), workflow async chỉ điều phối.

**Thêm/sửa:**
- `app/core/config.py`: cờ `rag_multi_agent_enabled` (mặc định **False** — đường cũ không đổi) +
  `planner_*`, `retrieval_grade_*`, `retrieval_max_rounds`, `critic_model`, `critic_max_revisions`.
- `app/rag/agents/`: `events.py`, `planner.py`, `retrieval_agent.py` (tự-chấm + lặp), `synthesis.py`
  (merge khử trùng node), `critic.py` (bọc `citation_verifier` + quyết accept/revise), `workflow.py`
  (`RAGAgentWorkflow` + entry async `answer_question_agentic`).
- `app/rag/query_engine.py`: `synthesize(..., feedback=None)` (backward-compat, cho vòng revise).
- `app/services/chat_service.py`: rẽ nhánh theo cờ, GIỮ `wait_for` timeout → 503.
- Test mới: `test_planner_agent`, `test_retrieval_agent`, `test_critic_agent`, `test_agent_workflow`.

**Bằng chứng:** `ruff check .` sạch · `pytest -q` = **186 passed** (gồm 19 test mới; đường cũ không
hồi quy). **Chạy THẬT** (OpenAI+Cohere+Weaviate) câu "Hồ sơ và độ tuổi tuyển sinh lớp 1?" →
Planner tách **2 sub-query** → trả lời có trích dẫn [3][4][6] từ PDF Bến Cát/Bình Hưng Hòa, 28.5s,
**trace_id `fb5279bfddda8bd8d52795ad9694937d`** (Phoenix Cloud, project kltn-rag).

**CHƯA xong (theo DoD):** RAGAS A/B chưa chạy — `eval/dataset.json` (12 câu Côn Đảo/Bình Thạnh) **lệch
corpus LIVE** (Bến Cát/Bình Hưng Hòa). Phải re-ingest đúng doc HOẶC viết lại dataset theo corpus rồi
mới đo off-vs-on (xem memory `rag-eval-harness-state`).

## 2026-06-26 — Sửa mất dấu tiếng Việt khi parse (ép vision parse_mode)

**Triệu chứng:** Một số block trong chunk mất dấu phụ ("Độc lập"→"Đc lp", "Tăng cường"→"Tăng cưng",
"Số:"→"S6"), xen kẽ block đủ dấu. KHÔNG phải lỗi chunking — text hỏng sẵn từ LlamaParse trước khi vào
LLM chunker (chunker ghép verbatim nên bê nguyên lỗi).

**Nguyên nhân:** PDF "lai" — phần dùng font có bảng ToUnicode lỗi → text-layer nhúng bị strip dấu phụ;
phần font tốt thì đủ dấu. LlamaParse mặc định (`parse_page_with_llm`) **ưu tiên đọc text-layer**, OCR chỉ
áp cho ảnh nhúng → kế thừa nguyên lỗi font ở các đoạn đó.

**Sửa:** Thêm `llamaparse_parse_mode` (config, mặc định **`parse_page_with_lvm`**) — render mỗi trang →
Large Vision Model đọc, BỎ QUA text-layer. Gửi qua REST trong `_upload` (`data["parse_mode"]`). Đánh đổi:
chậm hơn (~14.8s→33.6s/11 trang) + tốn credit. **Phải re-ingest tài liệu cũ** (xóa + upload lại) để
chunk sạch dấu; nên chạy `rag-eval` sau re-ingest. Test: assert `_upload` gửi `parse_mode`/`language`.

**Bằng chứng:** `ruff` sạch · `pytest -q` = **167 passed**. Chạy THẬT (An Hội Đông) mode vision →
11 trang/33.6s, trang 1 đủ dấu: "ỦY BAN NHÂN DÂN", "**Số: 2056**" (đúng), "CỘNG HÒA…", "Độc lập - Tự do".

## 2026-06-26 — Khắc phục lỗi 499 khi upload LlamaParse (timeout tách pha + retry)

**Bối cảnh:** Upload PDF/DOCX thỉnh thoảng fail `HTTPStatusError 499` ở `/parsing/upload`. 499 = "Client
Closed Request" (nginx): httpx phía BE đóng kết nối trước khi LlamaCloud trả xong — chủ yếu do timeout 120s
áp chung cho cả pha *write* (đẩy file lớn/mạng chậm) hoặc sự cố proxy/mạng thoáng qua. `_upload` cũ KHÔNG
có retry → một lần 499 là cả lần ingest fail.

**Sửa (chỉ tầng parse/ingest — KHÔNG đụng retrieval/prompt/embedding → không cần RAGAS):**
- `app/rag/parse.py`: `httpx.Timeout(connect=10, read=120, write=600, pool=10)` — pha write có ngân sách
  riêng & rộng. Thêm `_request_with_retry(send, what)`: thử lại 429/499/5xx + lỗi transport httpx
  (Timeout/Connect/RemoteProtocol), backoff lũy thừa + jitter; **4xx khác raise ngay**. Upload mở lại file
  MỖI lần thử (không resume được). Bọc retry cho upload + poll + result.
- `app/core/config.py`: thêm `llamaparse_upload_write_timeout=600`, `llamaparse_max_retries=4`,
  `llamaparse_retry_base_delay=2.0`.
- `tests/test_parse.py`: 3 test mới — 499→499→200 (retry thành công, mở lại file), 400 (không retry),
  hết lượt thử → raise. Patch `time.sleep`.

**Bằng chứng:** `ruff check .` sạch · `pytest -q` = **167 passed**. Chạy THẬT `parse_document` 1 PDF
(An Hội Đông) → upload 200 → poll 200 → result 200 → **11 trang/14.8s**, dấu tiếng Việt nguyên
("ỦY BAN NHÂN DÂN", "CỘNG HÒA…"), 12 block phân loại đúng.

## 2026-06-24 — Thay tiền xử lý PDF/DOCX bằng LlamaParse + LLM chunking trên markdown

**Bối cảnh:** Bỏ pipeline trích xuất cũ (pdfplumber + OCR Vision + python-docx + xử lý font lỗi) →
LlamaParse (cloud) parse PDF/DOCX → markdown sạch theo trang (server lo OCR/bảng/font/dấu), rồi LLM
chunk trên markdown. Plan: `C:\Users\mquan\.claude\plans\glistening-kindling-origami.md`.

**Quyết định:** markdown-native tới chunking · xóa hẳn pipeline cũ · nối cả tài liệu (Điều/Khoản tràn
trang KHÔNG bị cắt) · LLM chunking (ghép verbatim + validate phân hoạch + fallback) · metadata GIỮ
NGUYÊN 12 (Weaviate) + 5 (DB) trường, KHÔNG migration.

**LlamaParse qua REST httpx (KHÔNG SDK):** SDK `llama-cloud`/`llama-cloud-services` dùng `pydantic.v1`
→ VỠ import trên Py3.14 (`no validator found for UndefinedType`). Dùng REST trực tiếp
(`api.cloud.llamaindex.ai/api/v1/parsing`: upload→poll→`result/json`). 0 dep mới (httpx có sẵn). Kết quả
per-page có `items` ĐÃ PHÂN LOẠI (heading/text/table + `rows` grid bảng) → dùng làm block nguyên tử
(bỏ regex `structure.py`). Header/footer LlamaParse tách sẵn → `md` sạch (bỏ `clean.py`). Job CACHE
theo nội dung.

**File MỚI:** [parse.py](be/app/rag/parse.py) (ParsedPage/ParsedBlock, span `rag.ingest.parse`),
[md_chunker.py](be/app/rag/md_chunker.py) (LLM gộp block→ChunkNode; port `_make_node`/`_doc_ref_id`/
`_validate_partition`; bảng→chunk riêng, `table_data` từ `rows`; prompt mới `_CHUNK_SYSTEM_PROMPT`).
**XÓA:** `extract.py`, `ocr.py`, `docx_extract.py`, `clean.py`, `chunker.py`, `structure.py`. **SỬA:**
[document_service.py](be/app/services/document_service.py) (`ingest_document`: parse→doc_metadata+
title_metadata→md_chunker→add_nodes→save; bỏ routing .docx/OCR/clean), [doc_metadata.py](be/app/rag/doc_metadata.py)
(đọc `ParsedPage.md`, strip `#`/`*`), [ingest.py](be/app/rag/ingest.py) (chỉ còn `count_tokens`),
[config.py](be/app/core/config.py) (thêm `llama_cloud_api_key`/`llamaparse_*`; bỏ `ocr_*`/`garbled_*`/
`clean_*`; giữ `chunk_llm_*`/`chunker_model`). `requirements*.txt` gỡ python-docx/pdfplumber/pypdf/
pypdfium2/pdfminer.six. `.env.example` thêm `LLAMA_CLOUD_API_KEY`.

**Kiểm chứng (CHẠY THẬT, log thật):** `ruff` sạch · `pytest` **152 passed** (+test_parse/test_md_chunker/
test_doc_metadata; xóa test_extract/ocr/docx/clean/chunker) · **parse + LLM chunk THẬT** PDF 18 trang →
47 chunk (4 bảng): LLM gộp đúng mục 4–9 bị LlamaParse cắt nhầm `# 4.` vào Phần A; heading_path lồng
`['B...','I...']`; nối liền câu ngắt trang; `table_data` grid đúng (ô rỗng=None). DOCX 1 trang → 2 chunk
OK · **FULL ingest THẬT** (Postgres+Weaviate+OpenAI+LlamaParse) doc test → DB chunk + `weaviate_uuid` +
`table_data`, doc_type/ward/school_year đúng, rồi XÓA dọn (gỡ vector+file).

**rag-eval (RAGAS) — ĐÃ CHẠY (theo yêu cầu: xóa toàn bộ corpus, ingest 1 PDF Bình Thạnh qua pipeline mới,
eval 8 câu Bình Thạnh+chung = dataset[4:], filter BẬT):** dump
[eval/results/llamaparse_bt.json](be/eval/results/llamaparse_bt.json) · venv ragas 3.11 · Cohere
`rerank-multilingual-v3.0` top_n=6 · gpt-4o-mini.

| Metric | Pipeline MỚI (LlamaParse, 8 câu) | Baseline CŨ (README: 12 câu, 2 doc, filter) |
|---|---|---|
| faithfulness | **0.8333** | 0.8333 |
| answer_relevancy | 0.4692 | 0.4632 |
| context_precision (w/ ref) | 0.8296 | 0.8217 |
| context_recall | **1.0000** | 0.8750 |

Không so trực tiếp (8 câu/1 doc vs 12 câu/2 doc) nhưng pipeline mới **bằng/nhỉnh** mọi metric; `context_recall`
lên **1.0** (chunk LlamaParse truy hồi đủ ngữ cảnh), faithfulness giữ 0.83 (không tăng bịa). `answer_relevancy`
thấp do câu từ chối học phí (Q12) bị RAGAS chấm ~0 (đúng kỳ vọng). Thêm `--dataset` cho run_pipeline_dump.py.

**Sửa Phoenix trace (bug):** script standalone (eval/ingest) KHÔNG gọi `init_tracing()` (chỉ chạy trong
lifespan app) → Phoenix TRỐNG. Đã thêm `init_tracing()` vào [run_pipeline_dump.py](be/eval/run_pipeline_dump.py)
+ [ingest_docs.py](be/eval/ingest_docs.py). Verify THẬT: query + re-ingest sinh trace ở project `kltn-rag`
(`SimpleSpanProcessor` export ngay; spans `rag.ingest.parse`/`rag.ingest.chunk` + auto-instrument LLM/embedding).

**Trạng thái corpus + còn lại:** đã **XÓA TOÀN BỘ** 5 doc cũ (theo yêu cầu) → Weaviate/DB giờ CHỈ còn
Bình Thạnh (46 chunk pipeline mới). Muốn dùng production đầy đủ phải **re-ingest** các doc khác (An Đông/
An Khánh/Côn Đảo…) qua pipeline mới. FE không đổi (vẫn nhận .pdf/.docx).

## 2026-06-24 — Hỗ trợ định dạng DOCX (python-docx) — tái dùng pipeline từ bước [2]

**Bối cảnh:** Trước đó chỉ nhận PDF (DOCX → 415). Thêm hỗ trợ `.docx` mà KHÔNG đụng pipeline lõi —
nhờ kiến trúc đã tách `list[PageBlock]` làm ranh giới.

- **`python-docx==1.2.0`** (lxml 6.1.1 có sẵn trên Py3.14) → requirements.txt + requirements-deploy.txt.
- **[be/app/rag/docx_extract.py](be/app/rag/docx_extract.py)** (MỚI): `extract_docx(path)->list[PageBlock]`
  — `doc.paragraphs` (text, KHÔNG gồm ô bảng) + `doc.tables` (lưới ô = None nếu rỗng). DOCX không có
  trang → 1 PageBlock, `needs_ocr=False`. KHÔNG cần OCR/garbled.
- **Định tuyến theo đuôi** ([document_service.py](be/app/services/document_service.py)): `save_upload`
  nhận `.pdf`/`.docx` (lưu đúng đuôi), `create_document` mime theo đuôi, `ingest_document` route
  `.docx`→extract_docx / pdf→extract_with_tables (OCR tự bỏ qua). `_ALLOWED_EXT` + `media_type_for`.
  Route serve file dùng media_type theo đuôi. FE [PdfDropzone.tsx](fe/app/admin/_components/PdfDropzone.tsx)
  `accept` + nhãn `.pdf, .docx`.
- **Sửa [title_metadata.py](be/app/rag/title_metadata.py)**: dùng `Path(name).stem` (bỏ MỌI đuôi) —
  trước chỉ strip `.pdf$` nên `.docx` kẹt vào tên ward.

**Kiểm chứng (đã chạy thật):** `ruff` sạch · `pytest` **177 passed** (+5: test_docx, upload-docx,
title-docx) · FE `lint`+`tsc`+`vitest` **77 passed** · **ingest 1 .docx thật end-to-end**:
ward=`Tân Bình`, year=`2026-2027`, type=`ke_hoach`, 4 chunk — chunk bảng có
`table_data=[['Bậc học','Chỉ tiêu'],['Lớp 1','1.234'],['Lớp 6','987']]` [C]; filter
`{ward,school_year}` retrieve trả đúng 4 chunk từ file .docx [B]. (Doc test bịa đã xóa khỏi Weaviate.)
**Hạn chế:** ô gộp (merged cell) docx có thể lặp; xem inline docx trên trình duyệt sẽ tải về.

## 2026-06-24 — Hoàn thiện tiền xử lý: 3 nhóm (C table_data + QA · A clean · B metadata filter)

**Bối cảnh:** Đối chiếu pipeline tiền xử lý với 5 yêu cầu → #1 (trích scan/bảng) đạt; #2 làm sạch,
#3 bảng cấu trúc, #4 metadata lọc, #5 QA mới đạt một phần/chưa có. Triển khai theo thứ tự rủi ro
tăng dần C→A→B. Plan: `C:\Users\mquan\.claude\plans\toasty-greeting-finch.md`.

**Nhóm C — bảng cấu trúc + QA mẫu** (rủi ro hồi quy ~0; không đổi embed/retrieval):
- `ChunkNode.table_data` mang lưới bảng thô; cột `DocumentChunk.table_data` JSON
  ([be/app/models/document.py](be/app/models/document.py)); persist ở [document_service.py](be/app/services/document_service.py).
  Migration `c3d4e5f6a7b8` (revises b2c3d4e5f6a7).
- Script READ-ONLY [be/scripts/qa_sample.py](be/scripts/qa_sample.py): lấy mẫu ngẫu nhiên + cờ toàn
  vẹn (EMPTY_CONTENT, TABLE_NO_DATA, CONTEXT_IN_CONTENT, TOKEN_OUTLIER…), exit≠0 nếu cờ nặng.
- **Phát hiện:** pdfplumber over-detect bảng — dòng tiêu đề trang 1 bị tách thành "bảng" 14 cột vụn
  (false-positive). table_data carry verbatim (đúng); là vấn đề table-detection upstream, ngoài scope.

**Nhóm A — làm sạch** ([be/app/rag/clean.py](be/app/rag/clean.py)): gỡ header/footer lặp (band+tần
suất khuôn, digit→#), gỡ số trang, gộp khoảng trắng, nối từ ngắt dòng, chuẩn dấu câu. BẢO TOÀN `\n`
(Khoản nguyên tử); KHÔNG đụng bảng. Chèn **SAU** `extract_doc_metadata` (cần letterhead cho
issuing_body) **TRƯỚC** `build_nodes`. Cờ `clean_*` (config). PDF thật 18 trang: số trang "2" đầu
trang bị gỡ, nội dung giữ nguyên.

**Nhóm B — metadata lọc TỪ TÊN FILE** (quyết định với user: parse từ title, KHÔNG từ nội dung; địa
bàn cấp **phường/xã giữ nguyên**, không quy về quận/huyện):
- [be/app/rag/title_metadata.py](be/app/rag/title_metadata.py): parse năm học (chịu `2026 - 2027` /
  `2026 2027` / `20262027` → `2026-2027`) + phường/xã (sau "phường|xã|đặc khu"). Canonical theo
  whitelist [be/app/rag/wards_data.py](be/app/rag/wards_data.py) (**156 phường/xã sinh từ corpus thật
  158 file**). [be/app/rag/query_filters.py](be/app/rag/query_filters.py): `extract_filters` dựng
  `MetadataFilters` (EQ, AND) từ câu hỏi; ward qua whitelist-substring (tránh false-positive "xã hội").
- Cột `Document.school_year/ward` (migration `d4e5f6a7b8c9`); thêm vào `node.metadata` (property lọc
  Weaviate, excluded khỏi embed/LLM). Nối vào [query_engine.py](be/app/rag/query_engine.py)
  `answer_question` (đang `filters=None`) + **fallback-on-empty**. Schema `DocumentResponse` +2 trường.

**Kiểm chứng (đã chạy thật):** `ruff` sạch · `pytest` **172 passed** (+36 test mới: test_clean,
test_qa_sample, test_title_metadata, test_query_filters, mở rộng test_chunker/test_documents/test_query_engine)
· 2 migration up/down/up trên **Postgres thật** OK · PDF thật: trích table_data (bảng trang 13 7×4
đúng) + clean gỡ số trang · `extract_filters` câu hỏi thật: "phường Bình Thạnh năm học 2026-2027"→
{ward,school_year}, "Củ Chi"→{ward} (không cần từ khóa), "xã hội hóa"→không lọc.

**RAGAS + live query (đã chạy thật 2026-06-24):**
- Dựng lại `eval/dataset.json` (12 câu, grounded Côn Đảo + Bình Thạnh, 8/12 kích hoạt filter). Script
  mới `eval/ingest_docs.py` (ingest qua pipeline thật) + thêm cờ `--filter` cho `run_pipeline_dump.py`.
- **Re-ingest thật** 2 doc qua pipeline A+B+clean: Bình Thạnh (ward=Bình Thạnh, 80 chunk), Côn Đảo
  (ward=Côn Đảo, 28 chunk) — metadata set đúng → Nhóm B chạy end-to-end. Filter ở query-time lấy đúng
  doc (Bình Thạnh "1.159 HS", Cao Văn Ngọc…).
- **RAGAS** (so filter TẮT vs BẬT, cùng corpus đã clean): faithfulness **0.75→0.83** (+0.083);
  precision/recall lệch nhẹ trong nhiễu (corpus 2 phường → filter muted, lợi ích thật cần đủ 158 phường).
- CÒN: cô lập Nhóm A (clean) cần re-ingest `CLEAN_ENABLED=false`; eval trên full corpus 158 doc (tốn
  hơn). Số/diễn giải đầy đủ ở [be/eval/README.md](be/eval/README.md).

## 2026-06-24 — Cấu hình deploy: BE → Render/Railway (Docker), FE → Vercel

**Vấn đề:** Deploy `be/` lên Vercel lỗi `ModuleNotFoundError: No module named 'setuptools.backends'`.
Nguyên nhân gốc: [be/pyproject.toml](be/pyproject.toml) khai báo `build-backend =
"setuptools.backends.legacy:build"` — module KHÔNG tồn tại (đúng phải là `setuptools.build_meta`).
Nhưng sâu xa hơn: BE phụ thuộc torch/transformers/… (image >1GB) + cần pool DB/Redis + ổ đĩa +
timeout dài → **về cơ bản không hợp serverless Vercel** (giới hạn 250MB). → Tách: FE lên Vercel, BE
lên nền tảng container.

**Giải pháp:**
- Sửa `build-backend` → `setuptools.build_meta` ([be/pyproject.toml](be/pyproject.toml)).
- [be/app/core/config.py](be/app/core/config.py): thêm `field_validator` ép `postgres://` /
  `postgresql://` → `postgresql+asyncpg://` (Render/Railway cấp URL driver đồng bộ; app+Alembic async).
  Kèm 4 test [be/tests/test_config.py](be/tests/test_config.py).
- [be/requirements-deploy.txt](be/requirements-deploy.txt): subset 152 gói, BỎ reranker-local
  (torch/transformers/sentence-transformers/accelerate/peft/scikit-learn/scipy…), eval RAGAS
  (datasets/ir_datasets…), dev/test (pytest/ruff/coverage). An toàn vì các lib này import LƯỜI
  (chỉ khi `RERANK_PROVIDER=sentence-transformers`; prod dùng Cohere). Image 1.17GB thay vì ~3.5GB.
- [be/Dockerfile](be/Dockerfile) multi-stage (builder có build-essential, runtime gọn),
  [be/.dockerignore](be/.dockerignore), [render.yaml](render.yaml) blueprint, [DEPLOY.md](DEPLOY.md).
- Cookie xuyên domain (FE↔BE khác domain): cần `COOKIE_SECURE=true` + `COOKIE_SAMESITE=none` +
  `ALLOWED_ORIGINS=["https://<fe>.vercel.app"]`. FE đặt `NEXT_PUBLIC_API_URL=<be-url>` (tự ghép /api/v1).

**Kiểm chứng (đã chạy thật):** `ruff check .` sạch · `pytest` 136 passed · venv sạch cài
requirements-deploy.txt import `app.main` OK · `docker build` thành công (mọi gói có wheel cp314
linux) · container `--network none`: import + `SentenceSplitter` offline + cohere/weaviate/asyncpg/redis
OK · boot uvicorn rồi curl: `GET /`→200 `{"name":"KLTN API",...}`, `GET /api/v1/health`→200
`{"status":"ok",...}` · Redis vắng → suy giảm mượt (warn, không sập).

**Sửa flaky test (phát hiện khi chạy lại gate):** 3 test cũ trong
[be/tests/test_query_engine.py](be/tests/test_query_engine.py) (`...reranks_builds_sources...`,
`...excludes_metadata_from_snippet`, `...rag_route_retrieves_with_rewritten_query`) đi qua
`synthesize`→verifier nhưng KHÔNG pin `citation_verify_enabled` và KHÔNG mock `verify_answer`. Do
`.env` đặt `CITATION_VERIFY_ENABLED=true`, chúng gọi LLM verifier THẬT → `sources` bị lọc theo
`cited_indices` LLM trả về (non-deterministic) → `IndexError` lúc đỏ lúc xanh. Sửa: pin
`citation_verify_enabled=False` cho 3 test này (chúng kiểm retrieve→rerank→sources, không phải
verifier — verifier đã có test riêng 219/243/259). Khôi phục cam kết "không gọi mạng" ở docstring;
suite từ ~15s còn ~5.5s. KHÔNG đụng mã sản phẩm `query_engine.py`.

**Lưu ý:** Không chạm logic RAG (chunking/embedding/retriever/prompt) → không cần rag-eval. Disk lưu
PDF trên Render cần plan ≥ starter; plan free thì PDF tải lên là tạm.

## 2026-06-24 — Sửa dialog xác nhận xóa cuộc trò chuyện (FE)

**Vấn đề:** Dialog "Xóa cuộc trò chuyện" đặt sai trọng tâm thị giác — nút phá hủy **"Xóa"** đỏ
đặc nổi bật nhất (dễ bấm nhầm), nút an toàn **"Hủy"** mờ; nền sau dialog chỉ phủ màu (không blur);
dialog đóng giật (unmount tức thì).

**Giải pháp (FE thuần, không đụng RAG/DB):**
- Đảo ưu tiên nút trong [ConfirmDialog.tsx](fe/app/components/common/ConfirmDialog.tsx): Hủy →
  `variant="primary"` (teal đặc, nổi bật); Xóa (variant `danger`) → map sang `danger-outline`
  (viền + chữ đỏ, nền trong suốt). Giữ vị trí Hủy-trái / Xóa-phải.
- Thêm variant `danger-outline` vào [Button.tsx](fe/app/components/ui/Button.tsx) + class
  `.gw-btn--danger-outline` trong [globals.css](fe/app/globals.css) (tái dùng token `--danger-*`).
- Overlay: nền `rgba(0,0,0,0.4)` + `backdrop-filter: blur(6px)` (kèm `-webkit-`). Giữ click-nền =
  hủy + Esc = hủy (đã có sẵn).
- Transition mở/đóng ~220ms: fade-IN bằng CSS `@keyframes` (`gw-fade-in` overlay, `gw-msg-rise`
  dialog) — giá trị nghỉ opacity 1 nên KHÔNG kẹt vô hình khi timer/rAF bị tab ẩn throttle;
  fade-OUT bằng inline transition + giữ DOM 220ms rồi unmount (`mounted` state).

**Lưu ý:** Tránh `requestAnimationFrame`/`setState đồng bộ trong effect` (ESLint
`react-hooks/set-state-in-effect`) — mount điều chỉnh trong render, unmount qua `setTimeout`.

**Test:** [ConfirmDialog.test.tsx](fe/app/components/common/ConfirmDialog.test.tsx) +2 ca: phân vai
nút (Hủy=primary, Xóa=danger-outline, không còn danger đặc) và click-nền-đóng.

**Bằng chứng:** Gate xanh (lint + tsc + 77 test). Render thật qua Next dev server (đo computed
style): Hủy `rgb(31,153,153)`/chữ trắng; Xóa nền trong suốt, viền `rgb(229,72,77)`, chữ
`rgb(193,52,56)`; overlay `rgba(0,0,0,0.4)` + `blur(6px)`; opacity nghỉ = 1; click nền → fade-out →
unmount. (`preview_screenshot` treo trong môi trường headless — tab `visibilityState: hidden`.)

## 2026-06-23 — Sửa lỗi font tiếng Việt khi chunking PDF thuần (native-text)

**Vấn đề:** PDF scan trích tốt (OCR Vision), nhưng PDF "thuần" mới thêm bị **lỗi font** trong chunk.
Chẩn đoán trên file thật: KHÔNG phải symbol-mojibake mà là **diacritic bị strip** — pdfplumber
(pdfminer.six) đọc ToUnicode hỏng → tiếng Việt KHÔNG DẤU thuần ASCII ("CỘNG HÒA"→"CONG HOA",
"tuyển sinh"→"tuyen sinh"). OCR cũ chỉ chạy khi text-layer < 50 ký tự nên trang native garbled (>50)
lọt lưới. PDFium re-extract KHÔNG cứu được (cùng ToUnicode hỏng).

**Giải pháp (phân tầng, fail-safe — tất cả ở tầng [extract.py](be/app/rag/extract.py)):**
NFC normalize → `_looks_garbled` (heuristic thuần) → PDFium retry → route OCR + drop tables.
- `_looks_garbled` 4 tín hiệu OR: (s) ký tự rác PUA/control > 2%; (b) symbol lạ > 20%; (a) không
  khớp stopword (có dấu + ASCII-fold) → scramble; **(d) là tiếng Việt (đủ stopword) NHƯNG mật độ ký
  tự dấu < 1% → diacritic strip** (tín hiệu chính cho bug này). Gate độ dài 200 ký tự chống oan.
- Trang garbled: `needs_ocr=True` + `tables=[]` → tái dùng đường OCR Vision sẵn có (ghi đè text).
  `_needs_ocr(force=True)` bypass short-circuit `_has_real_table`. Cờ tắt `garbled_detect_enabled`.
- Config mới ([config.py](be/app/core/config.py)): `garbled_detect_enabled`, `garbled_min_chars=200`,
  `garbled_min_words=20`, `garbled_stopword_ratio=0.03`, `garbled_foreign_ratio=0.20`,
  `garbled_suspicious_ratio=0.02`, `garbled_diacritic_ratio=0.01`.

**Bằng chứng (đã chạy thật):**
- Gate: `ruff check` PASS · pytest **132 passed** (+11 test mới [test_extract.py](be/tests/test_extract.py)).
- Chẩn đoán read-only 3 PDF thật: file lỗi 8931 (13/14 trang garbled) bị bắt; file sạch 5677
  (29tr, stopword 0.12–0.18) **0 false-positive**; file scan 103ee (text rỗng) đi đường scan cũ.
- Pipeline thật `extract→OCR` (OpenAI Vision): "CONG HOA XA HOI" → **"CỘNG HÒA XÃ HỘI…"** (14/14 trang).
- **Re-ingest thật doc id=26** ("Kế hoạch tuyển sinh phường An Khánh"): 46 chunk lỗi → **45 chunk
  sạch dấu** trong Weaviate+DB (đọc lại `DocumentChunk.content` xác nhận).
- Eval nhắm doc 26: hỏi có dấu → trả lời đúng "năm học 2026-2027 [1]" trích đúng doc 26.

**rag-eval (RAGAS) — LƯU Ý dataset lệch corpus:** [dataset.json](be/eval/dataset.json) toàn câu "đặc
khu Côn Đảo" nhưng corpus hiện tại là An Khánh/An Đông (doc 24/25/26) → nhiều câu từ chối đúng →
RAGAS thấp (faithfulness 0.50, recall 0.56) KHÔNG so được baseline 2026-06-20 (corpus Côn Đảo khác).
**Không phải hồi quy do thay đổi này** (chỉ đụng extraction doc 26). Đã sửa harness lỗi thời
[run_pipeline_dump.py](be/eval/run_pipeline_dump.py): `synthesize()` nay trả 3-tuple `(answer,
sources, context)` nhưng harness unpack 2 → `ValueError`. Cần làm lại dataset khớp corpus mới.

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
- Gate: `ruff check` PASS · pytest **121 passed** (+10 test verifier, +3 test pipeline);
  FE `lint`+`tsc`+`vitest` **75 passed** (+3 test highlight sub-chunk).
- **Chạy thật `verify_answer` với OpenAI gpt-4o-mini** (kịch bản lớp1/lớp6): câu "lớp 6"
  `in_scope=False` → **DROP**; answer sạch; `cited_spans` chứa quote nguyên văn; trace đẩy lên
  **Phoenix Cloud** (project kltn-rag).
- **E2E thật qua HTTP** (uvicorn + Postgres/DBngin + Weaviate 139 chunk + Cohere + OpenAI,
  `CITATION_VERIFY_ENABLED=true`, đăng nhập thật): `POST /chat/ask` "Đối tượng ưu tiên xét tuyển
  lớp 1" → **200**, answer **loại bỏ** câu lớp-6 ("học sinh đã hoàn thành chương trình tiểu học…"),
  `sources` lọc còn [1][2], `cited_spans` **gọn chỉ lớp 1** (không span nào chứa "(đối với lớp 6)").
- **Chụp SourceDrawer** (FE dev :3000 nạp source mới): trong CÙNG chunk gộp lớp1+lớp6, chỉ đoạn
  "…đúng độ tuổi quy định (đối với lớp 1)" được `<mark>` tô đậm; phần "(đối với lớp 6); nhóm này
  cũng bao gồm…" KHÔNG tô. markCount=5, không mark nào chứa "lớp 6".

**File:** mới [citation_verifier.py](be/app/rag/citation_verifier.py),
[test_citation_verifier.py](be/tests/test_citation_verifier.py); sửa
[query_engine.py](be/app/rag/query_engine.py), [config.py](be/app/core/config.py),
[chat.py](be/app/schemas/chat.py), [test_query_engine.py](be/tests/test_query_engine.py); FE
[chat.ts](fe/app/types/chat.ts), [lib/chat.ts](fe/app/lib/chat.ts),
[citations.ts](fe/app/lib/citations.ts), [SourceDrawer.tsx](fe/app/components/common/SourceDrawer.tsx),
[SourceChips.tsx](fe/app/chat/_components/SourceChips.tsx). **Không cần migration** (cited_spans
nằm trong `context_sources` JSONB).

### rag-eval golden set (thủ công — RAGAS không chạy Py3.14): tìm & sửa 2 lỗi
Chạy 3 câu vàng (1 dễ off-scope + 2 sạch), so TRƯỚC (chỉ Lớp A) vs SAU (A+B). **Phát hiện 2 lỗi**:
1. **Off-scope ngầm leak**: câu lớp-6 diễn đạt lại không có chữ "lớp 6" → judge phán `in_scope=True`
   → không drop. 2. **Over-drop câu META**: judge drop nhầm chào hỏi / disclaimer "chưa có thông tin" /
   mời liên hệ nhà trường (vì `supported=False`).
**Sửa prompt judge** ([citation_verifier.py](be/app/rag/citation_verifier.py)): (a) phân loại câu
DỮ KIỆN vs META — META không cần nguồn, luôn `keep`; (b) suy ra CẤP LỚP từng câu ("đã hoàn thành
chương trình tiểu học"/"vào lớp 6"/"THCS" = ngoài phạm vi lớp 1); (c) `supporting_quote` lấy đoạn
NGẮN NHẤT đúng phạm vi (không kèm "(đối với lớp 6)"). **Sau sửa**: Q1 off-scope DROP đúng, Q2/Q3
giữ câu META (0 false-drop), quote gọn (xác nhận qua drawer).

### Hardening: parse JSON verifier chịu lỗi
Qua HTTP thấy fail-safe ~30% (LLM json_object thỉnh thoảng bọc ```` ```json ```` hoặc kèm prose).
`_parse_verdicts` giờ bóc fence + trích `{...}` ngoài cùng; verdict lẻ thiếu field → bỏ qua câu đó
(giữ nguyên) thay vì nuốt cả lượt. Test mới `test_parse_strips_code_fences_and_skips_bad_verdict`.

### Còn lại
- Cờ `CITATION_VERIFY_ENABLED` vẫn **tắt mặc định**; bật ở .env khi muốn dùng (đã xác nhận cải thiện).
- Cosmetic nhỏ: drop câu giữa danh sách đôi khi mất 1 dòng trống (markdown vẫn render ổn).
- Golden set mới 3 câu — mở rộng thêm nếu cần số liệu đầy đủ hơn.

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
