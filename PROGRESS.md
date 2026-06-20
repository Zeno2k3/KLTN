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
