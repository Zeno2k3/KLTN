@AGENTS.md

# Frontend (`fe/`) — Next.js 16

Giao diện chatbot "Lumina". **Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4.**
Chi tiết tech stack, cấu trúc thư mục khuyến nghị & lệnh: [README.md](README.md).

## ⚠️ Next.js 16 — đọc trước khi code

Phiên bản này có **breaking changes** so với kiến thức cũ (async `params`/`searchParams`, caching mặc định, các API đã đổi…). **Đọc guide trong `node_modules/next/dist/docs/`** cho phần liên quan trước khi viết, và tôn trọng deprecation notices.

## Cấu trúc hiện tại

```
proxy.ts                    # (gốc fe/) bảo vệ route — Next 16 đổi tên middleware→proxy
app/
├── layout.tsx              # root layout — font, metadata, bọc <Providers>
├── globals.css             # Tailwind v4 + theme toàn cục
├── _providers/             # client providers: Providers, AuthProvider (useAuth), ToastProvider (useToast)
├── components/
│   ├── ui/                 # primitive: Button, Avatar, AvatarGroup, IconBox,
│   │                       #   Badge, SectionHeading, TextField, Icon, LuminaLogo
│   └── common/             # dùng chung ≥2 trang: LogoLockup, LogoBadge, AppHeader, UserMenu
├── types/                  # kiểu dùng chung: chat.ts, admin.ts, auth.ts
├── lib/                    # tiện ích & dữ liệu: time.ts, api.ts (gọi BE), data/{landing,auth,chat,admin}
├── hooks/                  # logic tách khỏi UI: useChat, useDocuments
├── page.tsx                # "/" landing (ghép các section)
├── _components/            # section riêng của landing (LandingNav, LandingHero…)
├── auth/                   # "/auth" — page.tsx + _components (AuthBrandPanel, AuthForm)
├── chat/                   # "/chat" — page.tsx + _components (ChatSidebar, ChatThread…)
└── admin/                  # "/admin" — page.tsx + _components (AdminHeader, StatsView…)
```

**Quy ước component:** dùng ở ≥2 route → `app/components/**`; dùng đúng 1 route → `_components/` riêng của route đó. Đặt logic/state vào `hooks/`, dữ liệu tĩnh vào `lib/data/`, kiểu vào `types/`, provider vào `_providers/`.

## Lệnh

```bash
npm run dev      # dev server → http://localhost:3000
npm run build    # build production
npm run start    # chạy production
npm run lint     # eslint
```

## Xác thực (auth)

Token nằm trong **httpOnly cookie** (JS không đọc được) — mọi request gọi BE phải kèm `credentials: "include"`.

- **API client (`app/lib/api.ts`):** `apiFetch` luôn `credentials: "include"`, **tự refresh** khi 401 (gọi `/auth/refresh` 1 lần rồi thử lại). `authApi`: `register`, `login`, `loginWithGoogle(accessToken)`, `logout`, `me`. Lỗi ném `ApiError(message, status)`.
- **AuthProvider (`useAuth`):** state `user`/`loading`; methods `login`/`register`/`loginWithGoogle`/`logout`/`refreshUser`; gọi `/me` lúc mount để khôi phục phiên. Kiểu ở `types/auth.ts` (`Role`, `User` — khớp snake_case của BE: `avatar_url`, `is_active`).
- **ToastProvider (`useToast`):** `showToast(message, type)` hiện toast góc trái dưới (tự ẩn ~3.5s). Sau đăng nhập dùng **điều hướng cứng** (`window.location`) nên toast được giữ qua `sessionStorage` (key `lumina_toast`) để hiện ở trang đích.
- **Bảo vệ route:** `proxy.ts` (ở gốc `fe/`, **không** phải `middleware.ts` — Next 16) chặn `/chat`,`/admin` khi thiếu cookie `refresh_token` → redirect `/auth`. Quyền admin thực thi thật ở BE; trang admin thêm gate client-side qua `useAuth`.
- **Đăng nhập:** `AuthForm` gọi `useAuth().login/register` (email) hoặc `useGoogleLogin` (Google, luồng access token) → gửi BE → điều hướng theo vai trò: `admin → /admin`, `user → /chat`.
- **Google:** cần `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (fe/.env.local) **trùng** `GOOGLE_CLIENT_ID` (be/.env); test trên đúng `http://localhost:3000` (origin đã đăng ký ở Google Console). Thư viện: `@react-oauth/google` (`GoogleOAuthProvider` trong `Providers`).
- **Đăng xuất:** `UserMenu` (header chat & admin) mở hộp xác nhận → `logout()` → toast + về `/`.

## Quy ước

- **Alias `@/*`** trỏ về gốc `fe/`: `import LuminaLogo from "@/app/components/ui/LuminaLogo"`.
- **Tailwind v4** — cấu hình qua CSS (`globals.css`) + `@tailwindcss/postcss`; không dùng `tailwind.config.js` kiểu cũ.
- Mặc định **Server Components**; chỉ thêm `"use client"` khi cần state/effect/event handler (provider, AuthForm, UserMenu… đều là client).
- Gọi backend tại `http://localhost:8000` (CORS đã mở sẵn cho `localhost:3000`); base URL lấy từ `NEXT_PUBLIC_API_URL`. Biến `NEXT_PUBLIC_*` đặt ở `fe/.env.local` (copy từ `.env.example`) — **chỉ nạp khi khởi động `npm run dev`**, đổi xong phải restart.
- UI port từ thiết kế "Lumina" (xem memory [[lumina-design-source]]).
- Text UI & comment viết bằng **tiếng Việt**.
