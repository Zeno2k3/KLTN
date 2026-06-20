#!/usr/bin/env bash
# PostToolUse: định dạng file vừa được ghi. KHÔNG bao giờ chặn -> luôn exit 0.
# Không phụ thuộc jq: tự bóc file_path từ JSON bằng grep/sed và chuẩn hoá path Windows.
INPUT=$(cat)

# Bóc "file_path" mà không cần jq; đổi \\ (escape trong JSON) -> / để dùng được trên Git Bash/Windows.
FILE=$(printf '%s' "$INPUT" \
  | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' \
  | head -1 \
  | sed -E 's/.*:[[:space:]]*"//; s/"$//' \
  | sed 's#\\\\#/#g')

[ -z "$FILE" ] && exit 0
[ ! -f "$FILE" ] && exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
# Tìm 'ruff' của venv theo ĐƯỜNG DẪN TUYỆT ĐỐI (không nạp 'D:/...' vào PATH vì ':' phá PATH trên MSYS).
RUFF="ruff"
for v in .venv venv env; do
  if [ -x "$ROOT/be/$v/Scripts/ruff.exe" ]; then RUFF="$ROOT/be/$v/Scripts/ruff.exe"; break
  elif [ -x "$ROOT/be/$v/bin/ruff" ]; then RUFF="$ROOT/be/$v/bin/ruff"; break
  fi
done

case "$FILE" in
  *.py)
    "$RUFF" format "$FILE" 2>/dev/null || true
    "$RUFF" check --fix "$FILE" 2>/dev/null || true
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
    # Dự án FE dùng eslint (không có prettier). --fix là best-effort, không chặn.
    ( cd "$ROOT/fe" && npx eslint --fix "$FILE" 2>/dev/null ) || true
    ;;
esac
exit 0
