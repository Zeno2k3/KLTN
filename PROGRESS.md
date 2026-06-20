# Tiến độ dự án

## Đã xong

- (2026-06-21) **P7 — Hoàn chỉnh chat với AI: FE nối backend thật + lịch sử hội thoại bền vững.**
  - **BE — 2 endpoint đọc lịch sử (trên nền P6):** `GET /api/v1/chat/conversations` (sidebar, kèm snippet tin cuối)
    + `GET /chat/conversations/{id}/messages` (đọc lại, **kiểm quyền sở hữu** → 404 nếu không phải của mình).
    Thêm `conversation_repository.list_by_user` + `latest_message_map` (1 query lấy tin cuối/hội thoại, tránh N+1);
    `chat_service.list_conversations/get_conversation`; schema `ConversationSummary/MessageOut/ConversationDetail`
    (map cột `context_sources`→`sources`, ẩn `trace_id`/FK). KHÔNG migration.
  - **FE — bỏ mock, nối thật:** `lib/api.ts` `chatApi` (ask/listConversations/getMessages); `types/chat.ts`
    (`Source`, `Msg.sources`, `Convo.serverId/loaded/preview`, DTOs); `lib/chat.ts` mapping DTO→model
    (`assistant`→bot); viết lại `hooks/useChat.ts` (gọi API thật, nạp lịch sử lazy khi mở, optimistic user-msg +
    typing, error 401→nhắc đăng nhập, đưa hội thoại vừa trả lời lên đầu); `MessageBubble.tsx` **chip "Nguồn:"**
    (gộp trùng theo document_id, fallback "Tài liệu #id"); `chat/page.tsx` **auth guard** (redirect /auth nếu chưa
    đăng nhập) + banner lỗi; `Composer` disable khi đang chờ AI; bỏ `SEED/SCRIPTED/DEFAULT_REPLY` (giữ `TOPICS`).
  - **Test:** BE **41→47 passed** (+ list/messages 200/404/401, conv_session fixture); FE **36 passed** (9 files;
    +`chat.test`/`useChat.test`/`MessageBubble.test`/`api` chatApi). ruff + lint + tsc đều xanh.
  - **Verify THẬT E2E (ảnh đã đọc lại):**
    - **HTTP** (BE :8000): register→login→`POST /chat/ask` → "Trường THCS Lê Hồng Phong [1]" + 6 nguồn (score là
      float → JSONB OK); `GET /chat/conversations` có hội thoại + snippet; `GET .../1/messages` đủ 2 tin + nguồn.
    - **Trình duyệt** (FE dev :3000 ↔ BE :8000): đăng nhập → /chat → **sidebar nạp hội thoại từ DB** (của user) →
      click mở → render messages + **chip "Nguồn: Tài liệu #11"** → **gửi LIVE** "Phụ huynh nộp hồ sơ…" →
      "…https://tuyensinhdaucap.hcm.edu.vn" + chip; composer disable→enable; đa lượt cùng `conversation_id`.
  - **Gotcha verify:** `next dev` (Turbopack, Next 16) trả **404 mọi sub-route** (/auth, /chat) khi còn `fe/.next`
    cũ từ production `next start` → **xoá `fe/.next`** rồi `preview_start` lại là hết. CORS BE chỉ cho `:3000`
    (SameSite=Lax same-site localhost → cookie qua được :3000→:8000); auth suy giảm mượt khi Redis tắt.
  - User test trong DB dev: `parent.e2e@example.com` (tạo lúc verify, vô hại).

- (2026-06-20) **P6 — Đường hỏi-đáp RAG: Hybrid (BM25+vector) + RRF + cross-encoder rerank + LLM.**
  - **Retrieval (lõi):** `app/rag/retriever.py` `hybrid_retrieve()` — Weaviate-native hybrid qua
    `index.as_retriever(vector_store_query_mode=HYBRID, alpha=0.6, similarity_top_k=30,
    vector_store_kwargs={fusion_type: HybridFusion.RANKED, query_properties:["text"]})`. Mẹo: LlamaIndex
    `WeaviateVectorStore.query()` merge `vector_store_kwargs` vào `collection.query.hybrid()` → ép RRF
    (rankedFusion) + ưu tiên 60% semantic/40% keyword. **Verify live:** điểm hybrid ~0.0167 = 1/(rank+60)
    đúng RRF; collection `text` property `searchable=True` (BM25 bật); 25 chunk.
  - **Rerank:** `app/rag/query_engine.py` dùng `SentenceTransformerRerank` (model `namdp-ptit/ViRanker`,
    cross-encoder, top_n=6) — **KHÔNG dùng FlagEmbeddingReranker** vì FlagEmbedding 1.4 gọi
    `tokenizer.prepare_for_model` đã bị bỏ ở transformers 5.x. Chạy local (giữ PII). Lazy-import.
  - **LLM tổng hợp:** `query_engine.answer_question()` = `retrieve_and_rerank` → `synthesize` (gpt-4o-mini,
    system prompt tiếng Việt: CHỈ dựa ngữ cảnh, không bịa, trích dẫn [n]). Bọc span `rag.answer` → trace_id.
  - **Endpoint:** `POST /api/v1/chat/ask` (`routes/chat.py`, `get_current_user`) → `chat_service.ask`
    (lưu 2 message user+assistant + `context_sources` + `trace_id`, `asyncio.to_thread` cho pipeline chặn);
    `conversation_repository.py`; `schemas/chat.py`. File khác: `ingest.py`/`document_service.py` (gắn
    `filename` vào metadata node), `config.py` (hybrid_alpha/retrieval_top_k/rerank_model/top_n/chat_model).
  - **Schema DB:** KHÔNG migration. Chỉ đổi `Message.context_sources` JSONB → `JSONB().with_variant(JSON(),
    "sqlite")` (DDL Postgres không đổi; cần cho test SQLite).
  - **Bug bắt được khi CHẠY THẬT (mock test bỏ lọt):** reranker trả `score` kiểu `np.float32` → lưu cột
    JSON `TypeError: float32 not JSON serializable`. Sửa: ép `float(ns.score)` trong `_build_context`; thêm
    test `test_sources_score_is_json_serializable`.
  - **Test:** +9 (retriever RRF kwargs ×2, query_engine ×4 gồm serialization, chat service+API ×6 trừ trùng)
    → **41 passed**; ruff xanh.
  - **Chạy thật (bằng chứng):**
    - **HTTP** `POST /api/v1/chat/ask` (httpx ASGI, pipeline THẬT) → **200**, answer
      "…https://tuyensinhdaucap.hcm.edu.vn", 6 sources, DB lưu `['user','assistant']` + context_sources list.
    - **Phoenix:** init_tracing + answer → **TRACE_ID `5ec5d0dd…`** export lên Phoenix Cloud (project kltn-rag).
    - **RAGAS** (`be/eval/`, 8 câu hỏi tuyển sinh, ragas 0.2.15 ở venv Python 3.11 riêng — venv chính 3.14
      thiếu wheel scikit-network):

      | metric | ViRanker | bge-reranker-v2-m3 |
      |---|---|---|
      | faithfulness | 0.9375 | 0.9375 |
      | answer_relevancy | 0.4201 | 0.4757 |
      | context_precision | 0.7781 | 0.8283 |
      | context_recall | 0.8125 | 0.8750 |

      A/B: bge nhỉnh hơn trên tập nhỏ này (chủ yếu câu lớp 1); đổi model = 1 dòng `settings.rerank_model`.
      `answer_relevancy` thấp do 2 câu từ chối-đúng (ngoài corpus) bị RAGAS chấm 0.
  - **Deps:** thêm `torch==2.12.1+cpu`, `sentence-transformers==5.6.0` (+ transformers/accelerate…);
    requirements.txt freeze lại + `--extra-index-url` PyTorch CPU. Harness eval ở `be/eval/` (README + 2 script).

- (2026-06-20) **P5 — Admin PDF: xem lại / tải lại / xoá tất cả (mở rộng P4).**
  - **BE:** `GET /api/v1/admin/documents/{id}/file?download=` → `FileResponse` PDF, `content_disposition_type`
    inline (xem) / attachment (tải), filename gốc; `DELETE /api/v1/admin/documents` (không id) → `delete_all_documents`
    (drop collection Weaviate + xoá mọi file + xoá mọi row), trả `{"deleted": n}`. Tất cả `require_admin`.
    Thêm `vector_store.delete_collection`, `repo.list_file_paths/delete_all` (xoá chunk trước → không phụ thuộc FK
    cascade SQLite), `service.get_document_file/delete_all_documents`.
  - **FE:** DocRow thêm nút **Xem** (eye, `<a target=_blank>`) + **Tải** (download) trỏ `documentApi.fileUrl(id[,true])`
    (link mở thẳng :8000, cookie tự đính); DocsView thêm nút **Xoá tất cả** (`window.confirm`); `useDocuments.deleteAll`;
    `api.fileUrl/removeAll`; icon `eye`/`download`.
  - **Bug FE đã sửa (test bắt được):** optimistic rollback chụp `snapshot` TRONG updater của `setDocs` → updater có
    thể chạy sau khi promise reject → hoàn tác nhầm `[]`. Sửa: `snapshot = docs` đồng bộ (deps `[docs]`), áp cho cả
    `deleteDoc`.
  - **Test:** BE +6 (serve inline/attachment/404/403, delete-all có/rỗng/403) → **28 passed**; FE +3 (deleteAll
    success+rollback, fileUrl) → **21 passed**. ruff + lint + tsc xanh.
  - **Verify THẬT:** curl serve inline (`content-disposition: inline; filename="verify.pdf"`, 200) + download
    (`attachment`); delete-all xoá 6 tài liệu (file đĩa 6→0, DB→[], collection Weaviate drop, không lỗi); **FE**
    (preview :3000) hiện nút Xem/Tải mỗi dòng + "Xoá tất cả"; click "Xem" gọi `GET /file` qua apiFetch (refresh-aware) → 200.
  - **Review đa-tác-tử (đối nghịch) bắt 4 lỗi thật → đã sửa hết (+ test):**
    1. (med) Xoá-đơn dựa FK cascade → mồ côi chunk trên SQLite + đường cascade không có test → `repo.delete` xoá chunk
       TƯỜNG MINH (như `delete_all`); thêm test `test_delete_document_also_deletes_chunks` (fixture `doc_session`).
    2. (low) Side-effect Weaviate/file chạy trước commit → bất nhất nếu commit fail → đổi sang **commit DB trước**, dọn ngoài sau.
    3. (med) Link Xem/Tải qua `<a>` không refresh token → 401 khi access token hết hạn → đổi sang `documentApi.fetchFile`
       (qua apiFetch refresh-aware) → Blob → `window.open`/anchor download; mở tab đồng bộ tránh chặn popup.
    4. (med) Rollback optimistic dùng snapshot cũ → đè mất poll/upload đồng thời → bỏ snapshot, dùng **functional update**
       + `refresh()` đồng bộ server khi lỗi (đặt error SAU refresh để thông báo tồn tại).
  - Sau sửa: **BE 29 passed**, **FE 24 passed** (+5: openDoc xem/tải/lỗi, fetchFile, xoá-chunk), ruff+lint+tsc xanh.

- (2026-06-20) **P4 — Thêm PDF phía Admin: Full RAG ingestion (upload → chunk → embed → Weaviate).**
  - **BE (mới):** `app/rag/` (`vector_store.py` Weaviate Cloud + OpenAIEmbedding `text-embedding-3-small`,
    helper `add_nodes/delete_objects/retrieve`; `ingest.py` pypdf extract + SentenceSplitter 512/64 + tiktoken),
    `services/document_service.py` (upload→lưu đĩa→ingest NỀN→delete; session nền riêng `AsyncSessionLocal`,
    bọc `asyncio.to_thread` để không chặn event loop), `repositories/document_repository.py`,
    `schemas/document.py`, `routes/documents.py` (`/api/v1/admin/documents` POST/GET/DELETE, `require_admin`),
    `core/observability.py` (Phoenix OTEL, guard `phoenix_enabled`, wire vào lifespan).
  - **Config/deps:** thêm `upload_dir/max_upload_mb/openai_*/weaviate_*/chunk_*/phoenix_*` (config + .env.example);
    cài `pypdf`, `arize-phoenix-otel`, `openinference-instrumentation-llama-index`; freeze lại requirements.txt (UTF-8);
    `be/storage/` gitignored. **KHÔNG migration** (bảng `documents/document_chunks` đã có sẵn).
  - **FE (nối API thật, bỏ mock):** `lib/api.ts` `documentApi` (FormData + 204), `lib/documents.ts` map DTO→Doc,
    viết lại `hooks/useDocuments.ts` (fetch thật + upload + delete optimistic + polling khi còn `processing`),
    `types/admin.ts` thêm `failed` + `DocumentDTO`, `DocRow` badge lỗi, `DocsView` loading/error.
  - **Race đã sửa:** ingest nền (session riêng) không thấy document do `get_db` commit muộn → thêm `await db.commit()`
    trong `create_document` để commit NGAY trước khi lên lịch ingest.
  - **2 bug hạ tầng tìm & sửa khi verify:** (1) `UserResponse.email` dùng `EmailStr` → từ chối domain `.local`
    (admin seed `admin@lumina.local`) → login 500. Đổi sang `str` + test hồi quy. (2) Phoenix endpoint `.env` là URL
    space gốc, thiếu `/v1/traces` → span export 405. `init_tracing` tự ghép `/v1/traces`.
  - **Test:** BE +9 (`test_documents.py` mock ingest: upload 201/403/415/list/delete/404; `test_ingest.py` chunk thuần)
    +1 regression auth → **22 passed**, ruff xanh. FE +17 (mapper + hook mock fetch) → lint+tsc+vitest xanh.
  - **Verify THẬT (key của user):** upload curl `sample_tuyensinh.pdf` → status `processing`→`ready` (page_count=1,
    chunk_count=1); DB chunk có `weaviate_uuid`; **retrieval Weaviate** trả đúng chunk (uuid khớp); **Phoenix**
    project `kltn-rag`, endpoint `…/v1/traces`, không lỗi export; **FE** (preview :3000) login admin → tab Cơ sở
    kiến thức hiện danh sách thật + badge "Đã sẵn sàng", **xoá qua UI** giảm còn (1) khớp backend, không lỗi console.
  - **rag-eval:** answer pipeline chưa có → RAGAS faithfulness/answer_relevancy hoãn. Chạy **retrieval eval hit@1**
    trên 2 tài liệu khác chủ đề (tuyển sinh vs bán trú) × 6 câu hỏi → **6/6 = 100%** (retriever định tuyến đúng tài liệu).

- (2026-06-20) **P0 — Sửa lớp hook để thực sự chạy trên Windows.** Trước đó hook không chạy
  → agent báo "xong" mà vẫn lỗi.
  - settings.json: hook gọi qua `bash .claude/hooks/<file>.sh` (path tương đối) thay vì gọi thẳng `.sh`.
  - format.sh: bỏ phụ thuộc `jq` (không cài trên máy); .py dùng `ruff`, JS/TS dùng `eslint --fix` (không có prettier).
  - verify.sh (Stop gate): FE chỉ chạy `npm test` KHI có script test (fe CHƯA có test-runner) → trước đó luôn fail.
  - Sửa 4 nơi hardcode `CI=true npm test` (CLAUDE.md, fe/CLAUDE.md, verify-feature, verify.sh) cho khớp thực tế.
  - Đưa cây code về xanh: `ruff check --fix` + `ruff format` (sắp xếp import + `datetime.UTC` alias) ở
    security.py, auth_service.py, scripts/run.py, scripts/check_db.py. pytest vẫn 12 passed.
  - Bằng chứng: cây xanh → hook exit 0 không chặn; ép cây đỏ → hook trả `{"decision":"block"}`. Đã test đầu-cuối.
  - **Bug block-giả đã tìm & sửa:** hook thật báo backend đỏ dù chạy tay xanh. Nguyên nhân (xác định qua log
    chẩn đoán `_verify_debug.log`): nạp `D:/...` vào PATH làm hỏng PATH trên Git Bash/MSYS (`:` của `D:` là
    dấu phân tách) → `ruff`/`python` venv biến mất → exit 127. Sửa: verify.sh + format.sh gọi THẲNG
    `be/.venv/Scripts/ruff.exe` & `python.exe` theo đường dẫn tuyệt đối, không đụng PATH. Chi tiết: memory `windows-hooks-setup`.

- (2026-06-20) **P1 — Auto-nạp context đầu phiên + siết Definition of Done.**
  - SessionStart hook [.claude/hooks/session-start.sh] in branch + 8 commit gần nhất + file chưa commit +
    PROGRESS.md + CODEMAP.md ra stdout → Claude Code nạp vào ngữ cảnh mỗi phiên (đỡ phải đọc lại cả source).
    Đã đăng ký trong settings.json (`SessionStart`).
  - Sinh [.claude/CODEMAP.md] — bản đồ mã thật (BE: main/router/auth/core/models…; FE: pages/_components/
    components/ui/lib/api…). Ghi rõ RAG pipeline CHƯA có trong code.
  - Siết DoD trong CLAUDE.md + skill verify-feature: "suite xanh ≠ feature chạy"; feature mới phải (a) gate xanh,
    (b) chạy đường code mới thật ít nhất 1 lần (curl/screenshot/rag-eval), (c) có test bao phủ, (d) bằng chứng.
- (2026-06-20) **P2 — Test-runner FE (vitest + jsdom).**
  - Cài `vitest @vitejs/plugin-react jsdom @testing-library/react` (devDeps). Config [fe/vitest.config.ts]
    (jsdom, alias `@/`). Script `test: vitest run`, `test:watch: vitest`.
  - 2 smoke test: [fe/app/lib/time.test.ts] (hàm thuần) + [fe/app/lib/render.smoke.test.tsx] (render React/jsdom).
  - Bật lại `CI=true npm test` trong gate + sửa lại CLAUDE.md/fe/CLAUDE.md. Bằng chứng: Stop hook đầy-đủ chạy
    BE(ruff+pytest 12) + FE(lint+tsc+vitest 4) → exit 0, không chặn.

- (2026-06-20) **P3 — Header trang chủ phản ánh trạng thái đăng nhập (sửa "tưởng bị đăng xuất").**
  - **Triệu chứng người dùng:** đăng nhập xong, đóng/mở lại trình duyệt → tưởng bị đăng xuất.
  - **Chẩn đoán (KHÔNG phải mất phiên):** xác minh bằng trình duyệt thật trên `localhost:3000` rằng
    cookie là persistent (Max-Age access 1800s / refresh 604800s, expiry tương lai), `/refresh` trả 200,
    và `/me` = 200 ở CẢ trang chủ lẫn `/chat` sau khi tải mới (React state về 0, chỉ còn cookie). Phiên KHÔNG mất.
    Đã loại trừ: Edit clear-on-close (TẮT), localhost vs 127.0.0.1, BE down, SECRET_KEY (BE dùng đúng `.env`,
    ổn định qua restart). Gốc rễ: [fe/app/_components/LandingNav.tsx] là Server Component TĨNH, luôn hiện nút
    "Đăng ký" bất kể đăng nhập → người dùng về trang chủ thấy "Đăng ký" nên tưởng mất phiên.
  - **Sửa:** tách cụm nút phải thành client component [fe/app/_components/LandingNavActions.tsx] dùng `useAuth`:
    đã đăng nhập → "Vào chat" + `UserMenu`; chưa → "Đăng ký" + "Hỏi LuminaAi"; đang `loading` → chừa chỗ (tránh nháy).
  - **Test:** [fe/app/_components/LandingNavActions.test.tsx] (mock `useAuth`/`UserMenu`/`Button`) — 3 ca:
    đăng nhập / chưa / loading. Lưu ý: vì `globals` TẮT, phải gọi `cleanup()` thủ công trong `afterEach`
    (nếu không render tích lũy giữa test → fail giả). Gate FE xanh: lint + tsc + **7/7** test.
  - **Phát hiện quan trọng:** `localhost:3000` của user đang chạy **`next start` (production build)**, KHÔNG phải
    `next dev` (header `x-nextjs-prerender:1`, `/_next/webpack-hmr`→404). Production KHÔNG hot-reload → mọi sửa đổi
    FE không hiện cho tới khi **`npm run build && npm run start`** hoặc chạy **`npm run dev`**. Đây là lý do fix
    chưa thấy ở `:3000` khi verify; bằng chứng live của fix cần dev/rebuild.

## Đang làm

- (chưa có)

## Tiếp theo

- **Nối FE chat** gọi `POST /api/v1/chat/ask` (màn hình Lumina) + render câu trả lời & trích dẫn
  (`sources`); hiện endpoint đã xong + verify HTTP thật.
- **Lọc metadata nâng cao** (author/title/published_date): thêm cột `documents` (migration Alembic) +
  form upload nhận trường + gắn vào metadata node + **re-index** data cũ (hiện chunk chỉ có document_id;
  filename mới gắn từ P6 cho data ingest sau này). `hybrid_retrieve(filters=...)` đã sẵn tham số.
- **Chốt model rerank theo RAGAS lớn hơn:** tập eval hiện chỉ 8 câu / 1 tài liệu → bge nhỉnh ViRanker nhưng
  chưa đủ kết luận; mở rộng `be/eval/dataset.json` rồi chạy lại A/B trước khi đổi mặc định.
- (Tuỳ chọn) **LLM sinh câu trả lời qua Ollama** (local) thay gpt-4o-mini: thêm `llm_provider` config; giữ
  embedding OpenAI (đổi embedding = phải re-index). Reranker KHÔNG chuyển Ollama được (cross-encoder).
- Phoenix dùng `SimpleSpanProcessor` (dev) → cân nhắc `BatchSpanProcessor` cho prod (cảnh báo lúc startup).
- **Redis chưa chạy local** → blacklist token logout tạm vô hiệu (suy giảm mượt). Chạy Redis khi cần test logout thật.
- Cân nhắc UI xem/tải lại tài liệu (hiện chỉ list + xoá); endpoint tải PDF gốc nếu cần.

## Ghi chú

- Máy: Windows 11 + Git Bash; `jq` KHÔNG cài; venv BE ở `be/.venv/Scripts/`; FE dùng eslint (không prettier).
  Chi tiết ràng buộc hook: xem memory `windows-hooks-setup`.
- **Gate hiện tại (Stop hook, mỗi lượt) — BE:** `ruff check .` + `pytest -q`; **FE:** `npm run lint` +
  `npx tsc --noEmit` + `vitest run`. Tất cả đang xanh. Hook chạy ~30s mỗi lần kết thúc lượt.
- `.claude/` vẫn đang untracked trong git — cần `git add .claude PROGRESS.md` rồi commit để cấu hình được chia sẻ.
