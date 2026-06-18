# Frontend — Next.js 16

Giao diện người dùng xây dựng bằng **Next.js 16**, **React 19**, **TypeScript** và **Tailwind CSS v4**.

## Tech Stack

| Công nghệ | Phiên bản | Mô tả |
|---|---|---|
| Next.js | 16.2.9 | React framework với App Router |
| React | 19.2.4 | UI library |
| TypeScript | ^5 | Type-safe JavaScript |
| Tailwind CSS | ^4 | Utility-first CSS framework |
| ESLint | ^9 | Linting |

## Cấu trúc thư mục

```
fe/
├── app/                        # App Router (Next.js)
│   ├── layout.tsx              # Root layout — font, metadata, HTML wrapper
│   ├── page.tsx                # Trang chủ "/"
│   └── globals.css             # CSS toàn cục, Tailwind directives
│
├── public/                     # Static assets (ảnh, icon, font tĩnh)
│
├── next.config.ts              # Cấu hình Next.js
├── tsconfig.json               # Cấu hình TypeScript
├── postcss.config.mjs          # Cấu hình PostCSS / Tailwind
└── eslint.config.mjs           # Cấu hình ESLint
```

### Quy ước thư mục khi phát triển

Khi mở rộng, cấu trúc nên theo pattern sau:

```
app/
├── (auth)/                     # Route group — trang đăng nhập/đăng ký
│   ├── login/
│   │   └── page.tsx
│   └── register/
│       └── page.tsx
│
├── (main)/                     # Route group — các trang chính (có layout chung)
│   ├── layout.tsx              # Layout riêng cho nhóm này (sidebar, navbar)
│   ├── dashboard/
│   │   └── page.tsx
│   └── profile/
│       └── page.tsx
│
├── api/                        # API Routes (Next.js server-side)
│   └── [...]/route.ts
│
├── components/                 # Shared UI components
│   ├── ui/                     # Base components (Button, Input, Modal...)
│   └── common/                 # Compound components (Header, Sidebar...)
│
├── hooks/                      # Custom React hooks
├── lib/                        # Utilities, helpers, API client
├── types/                      # TypeScript type definitions
└── stores/                     # State management (Zustand / Jotai...)
```

## Cài đặt & Chạy

```bash
# Cài dependencies
npm install

# Chạy development server (http://localhost:3000)
npm run dev

# Build production
npm run build

# Chạy production
npm run start

# Lint
npm run lint
```

## Alias Path

`tsconfig.json` đã cấu hình alias `@/*` trỏ về root:

```ts
import { Button } from "@/app/components/ui/Button"
```
