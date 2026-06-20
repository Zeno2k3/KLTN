---
name: verify-feature
description: Verify a feature is truly complete before claiming done. Use whenever you are about to say a task or feature is finished, complete, working, or done, or when the user asks to verify, check, or confirm completion — even if not explicitly asked.
---

# Kiểm chứng Tính năng Trước khi Báo Xong

Không bao giờ khẳng định suông là đã thành công. Phải đưa ra bằng chứng.

## Các bước

1. Đọc lại yêu cầu gốc và mục PROGRESS.md liên quan.
2. Gate xanh — Backend (đã activate venv): `cd be && ruff check . && python -m pytest -q`
3. Gate xanh — Frontend: `cd fe && npm run lint && npx tsc --noEmit && CI=true npm test`
4. **Chạy đường code MỚI thật ít nhất một lần** (suite xanh CHƯA chứng minh tính năng chạy):
   - Endpoint → gọi thật bằng curl/httpx, dán request + response thật.
   - Logic/hàm mới → có test bao phủ nó (đỏ-trước-khi-sửa, xanh-sau).
5. Nếu có thay đổi RAG (retriever/prompt/embedding/index): kích hoạt skill `rag-eval`.
6. Với UI: chụp ảnh màn hình / log console rồi đọc lại bằng công cụ Read.
7. Ánh xạ TỪNG tiêu chí chấp nhận vào bằng chứng cụ thể (dán lệnh + output thật).
8. Nếu tiêu chí nào thiếu bằng chứng — kể cả khi suite xanh — thì CHƯA xong, tiếp tục làm.

## Định dạng output

Checklist: tiêu chí → bằng chứng (lệnh + kết quả) → PASS/FAIL.
Chỉ kết luận "hoàn thành" khi mọi dòng đều PASS.
