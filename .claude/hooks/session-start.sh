#!/usr/bin/env bash
# SessionStart: in trạng thái dự án ra stdout -> Claude Code nạp vào ngữ cảnh đầu mỗi phiên.
# Mục tiêu: phiên mới có ngay "đang làm gì / cấu trúc ở đâu" mà KHÔNG phải đọc lại cả source.
# KHÔNG bao giờ chặn -> luôn exit 0. Giữ output GỌN (nó tốn token mỗi phiên).
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

echo "# Bối cảnh dự án (tự động nạp đầu phiên — KHÔNG cần đọc lại toàn bộ source)"
echo

echo "## Git"
echo "- Branch: $(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
echo "- 8 commit gần nhất:"
git -C "$ROOT" log --oneline -8 2>/dev/null | sed 's/^/  - /'
# File đang sửa dở (uncommitted) — tín hiệu mạnh về việc đang làm.
CHANGED=$(git -C "$ROOT" status --porcelain 2>/dev/null | head -15)
if [ -n "$CHANGED" ]; then
  echo "- Đang có thay đổi chưa commit:"
  printf '%s\n' "$CHANGED" | sed 's/^/  /'
fi
echo

if [ -f "$ROOT/PROGRESS.md" ]; then
  echo "## PROGRESS.md (trạng thái việc đang làm)"
  cat "$ROOT/PROGRESS.md"
  echo
fi

if [ -f "$ROOT/.claude/CODEMAP.md" ]; then
  echo "## CODEMAP.md (bản đồ mã — nơi tìm thứ cần sửa)"
  cat "$ROOT/.claude/CODEMAP.md"
  echo
fi

echo "> Quy tắc: trước khi grep/đọc rộng cả repo, hãy dùng CODEMAP ở trên để nhảy thẳng tới file đúng."
exit 0
