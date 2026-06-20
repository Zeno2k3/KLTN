# Frontend (fe/) — Next.js 16 + React 19

## Stack & quy ước

- Next.js 16 App Router. Mặc định là Server Component; chỉ thêm `"use client"` khi cần
  state hoặc sự kiện trình duyệt.
- React 19: ưu tiên Server Actions, `useActionState`, `useOptimistic`, hook `use()`.
- TypeScript strict: không dùng `any`; kiểu tường minh ở ranh giới API.

## Tailwind v4

- Cấu hình kiểu CSS-first: `@import "tailwindcss";` và `@theme { ... }` trong file CSS.
  Thường KHÔNG cần `tailwind.config.js`.
- Dùng design token trong `@theme`; không rải mã màu hardcode khắp nơi.

## Lấy dữ liệu

- Fetch trong Server Component hoặc Server Action; hạn chế `useEffect` gọi API khi có
  thể thay bằng RSC.
- Mọi form có trạng thái loading và error rõ ràng.

## Test & kiểm chứng UI

- Chạy: `npm run lint && npx tsc --noEmit && CI=true npm test`.
- Test-runner: **vitest + jsdom** (cấu hình `fe/vitest.config.ts`, môi trường jsdom,
  `@testing-library/react` cho render). Test đặt cạnh nguồn, tên `*.test.ts(x)`.
  Import tường minh `{ describe, it, expect } from "vitest"` (không bật globals).
- Với thay đổi giao diện: PHẢI chụp màn hình và đọc lại bằng công cụ Read để xác nhận,
  không chỉ dựa vào unit test.
