# Tiến độ dự án

## Đã xong

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

- Cân nhắc thêm test cho đường code thật (auth flow FE, `lib/api.ts` mock fetch) thay vì chỉ smoke test.
- Khi bắt đầu dựng RAG pipeline: tạo service riêng + bắt buộc skill `rag-eval` (RAGAS + Phoenix).

## Ghi chú

- Máy: Windows 11 + Git Bash; `jq` KHÔNG cài; venv BE ở `be/.venv/Scripts/`; FE dùng eslint (không prettier).
  Chi tiết ràng buộc hook: xem memory `windows-hooks-setup`.
- **Gate hiện tại (Stop hook, mỗi lượt) — BE:** `ruff check .` + `pytest -q`; **FE:** `npm run lint` +
  `npx tsc --noEmit` + `vitest run`. Tất cả đang xanh. Hook chạy ~30s mỗi lần kết thúc lượt.
- `.claude/` vẫn đang untracked trong git — cần `git add .claude PROGRESS.md` rồi commit để cấu hình được chia sẻ.
