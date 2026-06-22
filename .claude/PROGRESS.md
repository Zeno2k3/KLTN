# Tiến độ dự án

## Đã xong

- (2026-06-22) **P13 — Admin: đổi tên (rename) tài liệu PDF (DB-only).**
  - **BE:** `PATCH /api/v1/admin/documents/{id}` body `{filename}` → `document_service.rename_document`
    (trim + non-empty, 404 nếu thiếu, `repo.update_filename`, commit) → `DocumentResponse`. `require_admin`.
    Schema `DocumentRenameRequest` (`filename` min_length=1 max_length=512).
  - **Phạm vi DB-only (cố ý):** chỉ đổi `documents.filename`. KHÔNG đụng vector Weaviate vì metadata
    `filename` của chunk nằm trong blob `_node_content` (LlamaIndex `to_node` dựng metadata từ đó, không từ
    property top-level → update property không propagate; re-ingest thì tốn kém). Cập nhật tới: admin list,
    **bảng trích dẫn chi tiết** (`chat_service.get_document_detail` đọc DB), tên file tải về (`get_document_file`).
    **Hạn chế đã biết:** chip nguồn ở câu trả lời chat MỚI (`query_engine._build_context` đọc metadata Weaviate)
    vẫn hiện tên cũ tới khi re-ingest.
  - **FE:** `documentApi.rename`; `useDocuments.renameDoc` (trim, bỏ qua rỗng, optimistic, refresh()+error khi lỗi);
    `DocRow` inline-edit (nút bút "Đổi tên" → input; Enter lưu/Esc huỷ/blur lưu; `editingRef` chống lưu 2 lần;
    focus+select) — mirror `ConversationItem`. Truyền `onRename` qua DocsView/page.
  - **Test:** BE +5 (rename ok/trim/404/422/403) → **91 passed**; FE +4 hook (optimistic/rỗng/rollback) +1 api
    (`rename` PATCH URL+body) → **68 passed**. ruff+lint+tsc xanh.
  - **Verify THẬT:** curl `PATCH` → 200, list phản ánh tên mới; **FE** (preview :3001, CORS-allowed) đăng nhập admin
    → tab Cơ sở kiến thức có nút "Đổi tên" mỗi dòng → click → input inline focus+pre-fill → gõ tên mới + Enter →
    server có ngay tên mới (UTF-8 tiếng Việt đúng), 0 lỗi console.
  - **Review đối nghịch bắt 1 lỗi thật → đã sửa:** (low) đang inline-edit mà bấm thẳng nút Xoá → `onBlur`
    (mousedown) lưu rename TRƯỚC `onClick` xoá → cùng doc vừa PATCH vừa DELETE → PATCH 404 → hiện lỗi sai.
    Fix: ẩn nút action khi `editing` (mirror ConversationItem) → khử race. Test `DocRow.test.tsx` (+4): nút biến
    mất khi sửa, Enter lưu / Esc huỷ / tên không đổi không gọi API. FE **72 passed**.
  - **Phụ:** gỡ 1 trailing-space trong `query_router.py:48` (prompt) để `ruff check .` xanh — không đổi nội dung prompt.

- (2026-06-22) **P12 — RAG tiền xử lý truy vấn: LLM Router (rag/direct) + Query Rewriting (condense-question).**
  - **Bối cảnh:** pipeline xử lý mỗi câu độc lập, không truyền lịch sử → (1) follow-up đa lượt
    ("thế còn học phí?") truy hồi sai; (2) câu ngoài phạm vi vẫn được trả lời do embedding tương đồng.
  - **Giải pháp — 2 bước tiền xử lý TRƯỚC retrieve, trong cùng span `rag.answer` (1 trace_id):**
    - **Router** `be/app/rag/query_router.py` (`route_query`): phân loại nhị phân `rag` | `direct`
      (LLM riêng `router_model`, fallback `openai_chat_model`); câu chào hỏi/ngoài phạm vi → `direct`
      (không retrieve). Default an toàn `rag` khi parse lỗi; module tự chứa (không import query_engine).
    - **Rewriter** `be/app/rag/query_rewriter.py` (`rewrite_query`): viết lại follow-up thành câu
      ĐỘC LẬP theo lịch sử (sliding window 5 tin). Bỏ qua khi history rỗng. LLM riêng `rewrite_model`.
    - **query_engine** `answer_question(query_text, history=None, filters=None)`: router → nếu
      `direct` trả `_answer_direct` (prompt "tùy loại": chào hỏi đáp tự nhiên / lạc đề từ chối lịch
      sự, `sources=[]`); nếu `rag` (+history) → rewrite → retrieve+synthesize dùng **câu đã viết lại**.
      Span attrs `rag.route`, `rag.rewritten_query`.
    - **chat_service.ask**: fetch `list_messages` TRƯỚC khi lưu câu hỏi mới (câu hiện tại không lọt
      history), prune sliding window `chat_history_window`, truyền `history=` (keyword) vào engine.
    - **config.py**: `query_router_enabled=True`, `query_rewrite_enabled=True`, `chat_history_window=5`,
      `router_model=""`, `rewrite_model=""` (seam swap model từng bước — KHÔNG dùng singleton LLM chung).
  - **Quyết định chốt:** ngoài phạm vi xử lý "tùy loại"; tách 2 lời gọi LLM (router→rewrite);
    synthesize dùng câu đã viết lại; mỗi bước 1 LLM/model riêng.
  - **Test:** **86 passed** (+ `test_query_router.py`, `test_query_rewriter.py`, +2 routing test ở
    `test_query_engine.py`, +1 history test ở `test_chat.py`; cập nhật mock cũ nhận `history`).
    ruff + pytest xanh.
  - **VERIFY THẬT (LLM thật, `eval/verify_router_rewrite.py`):** Router: "cách nấu canh chua"→direct,
    "Xin chào, bạn là ai?"→direct, "Hồ sơ lớp 1..."→rag. Rewrite: "thế còn học phí?" + lịch sử Lumina
    → "Học phí của Trường Tiểu học Lumina là bao nhiêu?". Direct ngoài phạm vi ("Thủ đô Pháp") từ chối
    lịch sự, sources=[]. Full RAG đa lượt: lượt 1 trả "6 tuổi" có nguồn, lượt 2 follow-up dùng câu
    viết lại; trace gửi Phoenix (`trace_id=17e09160...`).
  - **RAGAS:** không cài được trên Py3.14 (chỉ 1 venv `be/.venv`) → eval thủ công thay thế
    (`eval/verify_router_on_dataset.py`): Router phân loại **8/8** câu dataset = `rag`, **0 false-direct**
    → không hồi quy luồng RAG (single-turn: history rỗng ⇒ rewrite bỏ qua ⇒ retrieval y hệt baseline).
  - **Không** migration (route/rewritten_query chỉ ghi qua Phoenix span attr) · **không** đổi FE
    (`sources` vốn optional; direct trả `sources=[]`).

- (2026-06-21) **P11 — Thống kê admin: bỏ mock, dùng dữ liệu thật + bộ chọn mốc thời gian.**
  - **Bối cảnh:** tab Thống kê (`/admin`) trước đây hardcode 3/4 thẻ + biểu đồ + chủ đề (mock trong
    `fe/app/lib/data/admin.ts`, `fe/app/admin/page.tsx`). Nay tổng hợp thật từ Postgres.
  - **BE — endpoint mới `GET /api/v1/admin/stats?range=24h|7d|30d`** (mặc định 30d, `require_admin`):
    - `schemas/statistics.py` (`StatRange` Literal, `Metric{value,delta_pct}`, `ChartBucket`,
      `TopicStat`, `StatsResponse`); `repositories/statistics_repository.py` (COUNT async portable,
      **không `date_trunc`** → chạy cả SQLite test); `services/statistics_service.py` (cửa sổ
      thời gian + % so kỳ liền trước, `delta_pct=null` nếu kỳ trước=0; chia **6 bucket đều**, nhãn
      `HH:mm` cho 24h / `dd/MM` cho 7d-30d); `routes/statistics.py` + đăng ký `router.py`.
    - Số liệu: Phụ huynh hoạt động (distinct user role=`user` có message `user` trong kỳ),
      Lượt trò chuyện (conversations), Câu hỏi đã giải đáp (message `assistant`), Tổng tài liệu;
      Chủ đề = 1 chủ đề "Tư vấn tuyển sinh tiểu học" (= số lượt trò chuyện, theo chốt người dùng).
  - **FE — bỏ mock + bộ chọn kỳ:** `types/admin.ts` (StatsDTO + `DeltaTone`/`value` cho thẻ/topic),
    `lib/api.ts` (`statsApi.get`), `hooks/useStats.ts` (fetch theo range), `StatsView.tsx`
    (`"use client"` + segmented control 24h/7d/30d + map số liệu thật, badge `+%`/`-%`/`mới` đổi màu
    xanh/đỏ/xám), `AdminStatCard`/`BarChart`/`TopicProgressList` nhận tone/caption/value động;
    `page.tsx` bỏ mảng stats hardcode; **xoá** `lib/data/admin.ts`.
  - **Test:** BE **74 passed** (+6: count/delta, 6 bucket, default 30d, empty→0/null, range sai→422,
    non-admin→403); FE **64 passed** (+`useStats.test.tsx` mount/đổi-range/lỗi, +case `statsApi`).
    ruff + ESLint + tsc xanh.
  - **VERIFY THẬT:** curl đăng nhập admin → `GET /admin/stats` 3 mốc HTTP 200 với số thật từ Postgres
    (30d: PH=1, lượt=5, hỏi=6, tài liệu=2, chart 16/06=5). UI dev (:3001, CORS sẵn) đăng nhập thật,
    `/admin` hiển thị đúng các số đó; đổi tab 24h/7d/30d → subtitle/caption/biểu đồ đổi (24h chart
    `[33,0,0,0,33,100]%` khớp API `[1,0,0,0,1,3]`), không lỗi console; đã chụp 3 ảnh.
  - **Không** migration (chỉ đọc bảng sẵn có) · **không** đụng RAG → không cần rag-eval/RAGAS.

- (2026-06-21) **P10 — Sửa reranking quá lâu / treo hệ thống → chuyển reranker sang Cohere API.**
  - **Chẩn đoán (B0, có số đo):** rerank `namdp-ptit/ViRanker` mất ~5 phút rồi **segfault**
    (ACCESS_VIOLATION 0xC0000005). Nguyên nhân gốc KHÔNG phải mạng (tải file chỉ ~1.2s) mà là
    **RAM**: model `model.safetensors` = **2.2GB** (XLM-RoBERTa-large) nhưng máy chỉ **7.8GB RAM /
    0.6GB trống** → nạp model swap đĩa cực chậm rồi OOM-crash. Đối chứng: cross-encoder đa ngữ nhẹ
    118MB nạp OK + predict 0.24s + xếp hạng tiếng Việt đúng (liên quan +0.90 / lạc đề −4.36).
  - **Quyết định người dùng:** ViRanker bất khả thi trên phần cứng này → **dùng reranker qua API**;
    chọn **Cohere Rerank đa ngữ** (`rerank-multilingual-v3.0`).
  - **BE — đổi reranker + chống treo:**
    - `config.py`: `rerank_provider` ("cohere" mặc định | "sentence-transformers"),
      `rerank_model="rerank-multilingual-v3.0"`, `cohere_api_key`, `rag_timeout_seconds` (60s);
      `rerank_warmup` mặc định **False** (API không cần nạp model). Giữ `hf_*`/`rerank_num_threads`
      cho nhánh local tùy chọn.
    - `query_engine._get_reranker()`: rẽ nhánh provider → **Cohere** dùng `CohereRerank` (LlamaIndex,
      qua Phoenix trace; raise RuntimeError nếu thiếu key) | **local** giữ `SentenceTransformerRerank`
      (`device="cpu"`, `_apply_hf_env`). `warmup()` chỉ ý nghĩa cho local.
    - `main.py` lifespan: warm-up (qua `asyncio.to_thread`, lỗi không chặn app) — mặc định tắt với API.
    - `chat_service.ask`: `asyncio.wait_for(to_thread(answer_question), timeout=...)` →
      `TimeoutError` trả **503** "Hệ thống đang xử lý lâu hơn dự kiến, vui lòng thử lại…".
    - `requirements.txt`: +`cohere==6.1.0`, +`llama-index-postprocessor-cohere-rerank==0.9.0`
      (kéo pydantic 2.13.4→2.12.5). `.env.example` + `be/CLAUDE.md`: cấu hình Cohere + ghi chú PII.
  - **Test:** BE **68 passed** (+5: 503 khi timeout, lifespan warm-up bật/tắt, `_get_reranker` chọn
    Cohere đúng tham số + thiếu key→RuntimeError). ruff xanh.
  - **VERIFY THẬT (đã có COHERE_API_KEY):**
    - Rerank thật qua Cohere: 5 đoạn → **0.75s**, xếp hạng tiếng Việt đúng (liên quan cao / lạc đề ~0).
    - Pipeline RAG thật (Weaviate→Cohere→OpenAI) trên tài liệu tuyển sinh đầu cấp TP.HCM: trả lời
      đúng + trích dẫn [1][2], rerank đẩy đúng đoạn (score ~1.0). Trace Phoenix thật mỗi câu
      (vd `0810f6aa…`, `c112ef99…`). Câu ngoài tài liệu (hồ sơ lớp 1) → từ chối đúng (chống bịa).
    - **Eval LLM-as-judge (5 câu, gpt-4o-mini)** — RAGAS native KHÔNG cài được trên Python 3.14/Win
      (xung đột langchain-community 1.x + scikit-network cần C++): **faithfulness 0.96 · answer_relevancy
      1.00 · context_precision 0.92 · context_recall 0.96**; latency min 9.1s / max 20.8s / **avg 12.4s**
      (so với **5 phút + crash** của ViRanker local).
  - **Baseline:** không có số ViRanker để A/B vì model 2.2GB segfault ngay khi nạp → "trước" = hệ thống
    treo/không dùng được; "sau" = chạy ổn định ~10-12s, chất lượng đo được như trên.

- (2026-06-21) **P9 — Trích dẫn nguồn: chip tài liệu dưới tin bot + bảng tài liệu trượt ra (drawer) tô sáng đoạn được trích.**
  - **BE — 1 endpoint chỉ-đọc:** `GET /api/v1/chat/documents/{id}` (auth `get_current_user`, KHÔNG admin; kho
    tài liệu là tri thức chung) → `DocumentDetailOut{id, filename, page_count, chunk_count, chunks[]}`;
    `DocumentChunkOut{chunk_index, content, weaviate_uuid}`. Thêm `document_repository.get_with_chunks`
    (`selectinload`, sắp theo `chunk_index`) + `chat_service.get_document_detail` (404 nếu không có). **KHÔNG
    migration, KHÔNG ingest lại, KHÔNG RAGAS** (chỉ đọc chunk đã lưu). `conftest._build_authed_client` giờ trả
    `(client, session_maker)`; thêm fixture `user_client_db` để seed Document+chunk vào DB của request.
  - **FE — 3 component tái sử dụng:** `lib/citations.ts` (`CitationDocument`/`CitationPara` + `buildCitationDocument`
    + `pageMeta` "Đoạn N / tổng" + `groupSourcesByDocument` gom theo document_id, gom `weaviate_uuid` = tập tô
    sáng); `components/ui/CitationChip.tsx` (pill icon `file-text` + hover-darken `.ch-cite-chip`, `disabled` khi
    `document_id` null); `components/common/SourceDrawer.tsx` (overlay blur + panel trượt phải 460px,
    `panel-slide-in` 240ms, Esc/X/nền đóng; header eyebrow "NGUỒN THAM KHẢO" + tiêu đề + "{kind} · LuminaAi" + X
    tròn; pill meta viền teal; đoạn tô sáng nền `--sun-50` + nhãn "★ ĐOẠN ĐƯỢC TRÍCH DẪN"; loading/error/empty +
    nút thử lại); `chat/_components/SourceChips.tsx` (`"use client"` gói chip + 1 drawer, chỉ 1 mở). `MessageBubble`
    đổi `dedupeSources`→`groupSourcesByDocument` + render `<SourceChips>` (giữ server-safe). `types/chat.ts` +
    `lib/chat.ts`: **giữ `weaviate_uuid`** trên UI `Source` (cần để tô sáng); `Icon.tsx` thêm `file-text`/`x`;
    `globals.css` keyframe `panel-slide-in`.
  - **Test:** BE **63 passed** (+5: service trả chunk đúng thứ tự, 404, API 200/404/401). FE **60 passed** (+17:
    `CitationChip.test`, `SourceDrawer.test` mở/đóng/tô sáng/lỗi, `citations.test` mapper, mở rộng
    `MessageBubble.test` chip bấm-được/gom-nhóm, sửa `chat.test` giữ weaviate_uuid). ruff + lint + tsc xanh.
  - **Verify THẬT E2E (ảnh đã đọc lại):**
    - **HTTP** (BE :8000, mint token): `GET .../documents/11` → **200** với 24 chunk thật (nội dung "ỦY BAN NHÂN
      DÂN ĐẶC KHU CÔN ĐẢO…", `weaviate_uuid` thật); id sai → **404** `{"detail":"Không tìm thấy tài liệu."}`;
      no-auth → **401**.
    - **Trình duyệt** (FE dev :3001 ↔ BE :8000, user test + hội thoại seed trích doc 11): dòng **"Nguồn:"** + chip
      pill teal có icon (hình 1); bấm chip → **drawer trượt phải** khớp mockup (hình 2): header/eyebrow/tiêu đề/X
      tròn, pill **"2 đoạn được trích / 24"**, đoạn đầu **tô sáng cam** + nhãn "★ ĐOẠN ĐƯỢC TRÍCH DẪN" nội dung
      thật; cuộn xuống thấy đoạn thường (hình 3). DOM: 24 đoạn, 2 tô sáng, 2 nhãn.
    - **Đã dọn:** xóa user test + hội thoại seed khỏi DB; xóa file tạm; revert `.claude/launch.json`.
  - **Gotcha verify:** preview browser KHÔNG tới được :8000 khi backend tắt ("Failed to fetch") → khởi động lại
    uvicorn; CORS BE chỉ cho `:3000`/`:3001` → chạy dev verify trên **:3001**; điều hướng preview sang server ngoài
    (:3000) làm kẹt renderer → để preview tự chạy FE trên :3001.
  - **Tinh chỉnh theo đặc tả UI (chốt giá trị cuối):** nhãn "Nguồn:" icon `book` 13px, chữ 12px/600; chip viền
    **`--teal-200`**, chữ 12px/**700**, icon `file` (Lucide), hover nền `--teal-100` + viền `--teal-400` 120ms;
    header drawer icon `file`; overlay **`rgba(12,26,26,.40)` + blur 4px**; keyframe `panel-slide-in`
    **`translateX(24px)+opacity:0→0`** 240ms ease-out. Đã verify lại bằng ảnh (computed style xác nhận viền
    teal-200, overlay .40/blur 4px). FE **60 passed**, lint+tsc xanh.

- (2026-06-21) **P8 — Menu 3 chấm trên ConversationItem: đổi tên (inline) + xóa (có modal xác nhận).**
  - **BE — 2 endpoint mới (kiểm quyền sở hữu → 404):** `PATCH /api/v1/chat/conversations/{id}` (đổi tên, body
    `RenameConversationRequest{title}`, trả `ConversationSummary`) + `DELETE /chat/conversations/{id}` (204,
    cascade xóa messages do FK `ON DELETE CASCADE`). Thêm `conversation_repository.update_title/delete`,
    `chat_service.rename_conversation/delete_conversation` (+ helper `_owned_or_404`). **KHÔNG migration** (cột
    `title` đã có).
  - **FE — menu + inline rename + modal:** `Icon.tsx` thêm `more-vertical` (3 chấm) + `edit` (bút chì);
    `lib/api.ts` `chatApi.renameConversation/deleteConversation` (DELETE dùng `parseEmpty`); `useChat.ts`
    `renameConvo` (optimistic, revert nếu lỗi) + `deleteConvo` (xóa active → mở cuộc mới trống); viết lại
    `ConversationItem.tsx` (nút kebab mẫu `UserMenu` + `stopPropagation`, menu Đổi tên/Xóa, sửa tên inline
    Enter-lưu/Esc-hủy); mới `components/common/ConfirmDialog.tsx` (modal giữa màn hình + overlay, Esc/click nền =
    hủy); `ChatSidebar.tsx` giữ `pendingDelete` + render dialog; `page.tsx` truyền `onRename/onDelete`;
    `globals.css` ẩn/hiện kebab theo hover.
  - **Test:** BE **58 passed** (+10: rename/delete service+API, 404/401/422). FE **46 passed** (11 files;
    +`ConversationItem.test`/`ConfirmDialog.test`, mở rộng `useChat.test` rename/delete). ruff + lint + tsc xanh.
  - **Verify THẬT E2E (ảnh đã đọc lại):**
    - **HTTP** (BE :8000): mint token → `PATCH .../3` đổi tên 200; empty title 422; missing 404; no-auth 401;
      `DELETE .../3` 204; `GET .../3/messages` sau xóa 404; DELETE lại 404.
    - **Trình duyệt** (FE dev :3001 ↔ BE :8000, user `parent.e2e@example.com`): mở kebab → menu **Đổi tên (bút chì)
      / Xóa (thùng rác đỏ)** khớp hình; sửa tên inline → Enter → **reload vẫn giữ tên mới** (PATCH bền vững);
      Xóa → **modal xác nhận giữa màn hình** kèm tên hội thoại (khớp hình 3) → "Xóa" → item biến mất → **reload
      vẫn mất** (DELETE bền vững); xóa cuộc đang mở → tự mở cuộc trò chuyện mới trống; console không lỗi.
    - **Icon khớp hình:** 3 chấm dọc (hình 1), bút chì "Đổi tên" + thùng rác đỏ "Xóa" (hình 2), modal (hình 3).
  - **Gotcha verify:** CORS BE chỉ cho `:3000`/`:3001`; dev server autoPort nhảy sang :63407 → CORS chặn login →
    chạy dev trên **:3001** (origin được phép) để verify. Đã revert config tạm trong `.claude/launch.json`.

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
