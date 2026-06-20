#!/usr/bin/env bash
#
# Hook Stop: chạy khi Claude muốn kết thúc lượt. Nếu kiểm tra fail -> trả JSON
# block -> Claude buộc phải làm tiếp. Kiểm tra stop_hook_active để tránh vòng lặp.
#
# GHI CHÚ QUAN TRỌNG (Windows/Git Bash):
# - KHÔNG nạp đường dẫn venv kiểu 'D:/...' vào PATH: trên MSYS, ':' là dấu phân tách PATH
#   nên 'D:' làm hỏng entry -> ruff/python của venv không tìm thấy. Vì vậy gọi THẲNG
#   ruff.exe / python.exe theo đường dẫn tuyệt đối (xem BE_RUFF/BE_PY bên dưới).
# - Gate backend: ruff check + pytest. Gate frontend: lint + tsc (+ test nếu có script test).

INPUT=$(cat)
# Tránh vòng lặp vô hạn khi Stop hook tái nhập. Dùng grep để KHÔNG phụ thuộc jq.
if printf '%s' "$INPUT" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Tìm python + ruff của venv theo ĐƯỜNG DẪN TUYỆT ĐỐI (không dựa vào PATH).
BE_PY="python"; BE_RUFF="ruff"
for v in .venv venv env; do
  if [ -x "$ROOT/be/$v/Scripts/python.exe" ]; then           # Windows
    BE_PY="$ROOT/be/$v/Scripts/python.exe"
    [ -x "$ROOT/be/$v/Scripts/ruff.exe" ] && BE_RUFF="$ROOT/be/$v/Scripts/ruff.exe"
    break
  elif [ -x "$ROOT/be/$v/bin/python" ]; then                 # Linux/macOS
    BE_PY="$ROOT/be/$v/bin/python"
    [ -x "$ROOT/be/$v/bin/ruff" ] && BE_RUFF="$ROOT/be/$v/bin/ruff"
    break
  fi
done

# ---- BACKEND (FastAPI / Python 3.14 / pip) ----
if [ -d "$ROOT/be" ]; then
  (
    cd "$ROOT/be" \
      && "$BE_RUFF" check . \
      && "$BE_PY" -m pytest -q
  ) 1>&2 || {
    echo '{"decision":"block","reason":"Backend chưa pass (ruff/pytest). Hãy sửa rồi chạy lại trước khi báo xong. Nếu vừa đổi pipeline RAG (chunking/embedding/retriever/prompt), phải chạy thêm RAGAS eval và đính kèm số liệu — đừng tuyên bố hoàn thành khi chưa có số."}'
    exit 0
  }
fi

# ---- FRONTEND (Next.js 16) — npm/npx lấy từ PATH hệ thống (POSIX, không lỗi) ----
if [ -d "$ROOT/fe" ]; then
  # lint + tsc luôn chạy.
  (
    cd "$ROOT/fe" \
      && npm run lint \
      && npx tsc --noEmit
  ) 1>&2 || {
    echo '{"decision":"block","reason":"Frontend chưa pass (lint/tsc). Hãy sửa rồi chạy lại. Với thay đổi giao diện, phải chụp màn hình và đọc lại bằng công cụ Read để xác nhận, không chỉ dựa vào unit test."}'
    exit 0
  }
  # 'test' chỉ chạy KHI fe đã có script test trong package.json (hiện chưa có test-runner).
  if grep -qE '"test"[[:space:]]*:' "$ROOT/fe/package.json"; then
    ( cd "$ROOT/fe" && CI=true npm test ) 1>&2 || {
      echo '{"decision":"block","reason":"Frontend test fail. Hãy sửa rồi chạy lại trước khi báo xong."}'
      exit 0
    }
  fi
fi

exit 0
