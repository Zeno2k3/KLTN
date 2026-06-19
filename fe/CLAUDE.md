@AGENTS.md

# Frontend (`fe/`) — Next.js 16

Giao diện chatbot "Lumina". **Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4.**
Chi tiết tech stack, cấu trúc thư mục khuyến nghị & lệnh: [README.md](README.md).

## ⚠️ Next.js 16 — đọc trước khi code

Phiên bản này có **breaking changes** so với kiến thức cũ (async `params`/`searchParams`, caching mặc định, các API đã đổi…). **Đọc guide trong `node_modules/next/dist/docs/`** cho phần liên quan trước khi viết, và tôn trọng deprecation notices.

## Cấu trúc hiện tại

```
app/
├── layout.tsx              # root layout — font, metadata
├── globals.css             # Tailwind v4 + theme toàn cục
├── components/
│   ├── ui/                 # primitive: Button, Avatar, AvatarGroup, IconBox,
│   │                       #   Badge, SectionHeading, TextField, Icon, LuminaLogo
│   └── common/             # dùng chung ≥2 trang: LogoLockup, LogoBadge, AppHeader
├── types/                  # kiểu dùng chung: chat.ts, admin.ts
├── lib/                    # tiện ích & dữ liệu: time.ts, data/{landing,auth,chat,admin}
├── hooks/                  # logic tách khỏi UI: useChat, useDocuments
├── page.tsx                # "/" landing (ghép các section)
├── _components/            # section riêng của landing (LandingNav, LandingHero…)
├── auth/                   # "/auth" — page.tsx + _components (AuthBrandPanel, AuthForm)
├── chat/                   # "/chat" — page.tsx + _components (ChatSidebar, ChatThread…)
└── admin/                  # "/admin" — page.tsx + _components (AdminHeader, StatsView…)
```

**Quy ước component:** dùng ở ≥2 route → `app/components/**`; dùng đúng 1 route → `_components/` riêng của route đó. Đặt logic/state vào `hooks/`, dữ liệu tĩnh vào `lib/data/`, kiểu vào `types/`.

## Lệnh

```bash
npm run dev      # dev server → http://localhost:3000
npm run build    # build production
npm run start    # chạy production
npm run lint     # eslint
```

## Quy ước

- **Alias `@/*`** trỏ về gốc `fe/`: `import LuminaLogo from "@/app/components/ui/LuminaLogo"`.
- **Tailwind v4** — cấu hình qua CSS (`globals.css`) + `@tailwindcss/postcss`; không dùng `tailwind.config.js` kiểu cũ.
- Mặc định **Server Components**; chỉ thêm `"use client"` khi cần state/effect/event handler.
- Gọi backend tại `http://localhost:8000` (CORS đã mở sẵn cho `localhost:3000`).
- UI port từ thiết kế "Lumina" (xem memory [[lumina-design-source]]).
- Text UI & comment viết bằng **tiếng Việt**.
