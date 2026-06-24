# Hướng dẫn Deploy

Kiến trúc deploy được khuyến nghị:

| Thành phần | Nền tảng | Lý do |
|---|---|---|
| **FE** (`fe/`, Next.js 16) | **Vercel** | Đúng sở trường của Vercel |
| **BE** (`be/`, FastAPI + RAG) | **Render** / Railway / Fly.io (Docker) | Cần server chạy bền: pool Postgres + Redis, ổ đĩa cho PDF, timeout dài. **Không hợp serverless** (image > 250MB, pipeline RAG vượt timeout serverless) |
| PostgreSQL | Render Postgres / Railway / Neon… | DB phải **UTF8** |
| Vector store | **Weaviate Cloud** | Đã dùng sẵn (dịch vụ ngoài) |

> ⚠️ **Đừng deploy `be/` lên Vercel.** Backend phụ thuộc nhiều thư viện + lưu file + giữ kết nối
> bền → vượt giới hạn serverless. Lỗi `uv sync ... setuptools.backends` ban đầu chỉ là triệu chứng
> đầu tiên; kể cả sửa xong vẫn vướng giới hạn 250MB và timeout.

---

## 0. Chuẩn bị (dịch vụ ngoài)

Cần sẵn các khoá/URL sau (đặt làm biến môi trường, **không commit**):

- `OPENAI_API_KEY` — embedding + LLM tổng hợp
- `COHERE_API_KEY` — reranker (dashboard.cohere.com)
- `WEAVIATE_URL`, `WEAVIATE_API_KEY` — Weaviate Cloud
- `GOOGLE_CLIENT_ID` — đăng nhập Google (Google Cloud Console → OAuth 2.0 Web client)
- `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_API_KEY` — *(tuỳ chọn)* tracing; bỏ qua thì đặt `PHOENIX_ENABLED=false`

---

## 1. Deploy Backend lên Render (Docker)

File hỗ trợ đã có sẵn: [`be/Dockerfile`](be/Dockerfile), [`be/.dockerignore`](be/.dockerignore),
[`be/requirements-deploy.txt`](be/requirements-deploy.txt) (đã bỏ torch/transformers… vì prod dùng
Cohere → image ~1GB thay vì ~3.5GB), và blueprint [`render.yaml`](render.yaml).

### Cách A — Blueprint (tự tạo cả Postgres + Redis + web service)

1. Push repo lên GitHub.
2. Render Dashboard → **New → Blueprint** → chọn repo này → Render đọc `render.yaml`.
3. Render hỏi giá trị các biến `sync:false` → điền: `OPENAI_API_KEY`, `COHERE_API_KEY`,
   `WEAVIATE_URL`, `WEAVIATE_API_KEY`, `GOOGLE_CLIENT_ID`, `ALLOWED_ORIGINS`, `PHOENIX_*`.
   - `ALLOWED_ORIGINS` là **JSON list**, ví dụ: `["https://ten-app.vercel.app"]`
     (chưa biết domain FE thì điền tạm, sửa lại ở bước 3).
4. **Apply** → Render build image, tạo DB + Redis, chạy `alembic upgrade head` rồi khởi động.

> **Lưu ý plan:** `render.yaml` hiện đặt **plan free** (web + Postgres + Redis). Đánh đổi: web **ngủ
> sau 15 phút** không dùng (cold start ~30-50s khi gọi lại), PDF upload **không lưu bền** (mất sau
> deploy/restart/ngủ vì free không có disk), Postgres free **hết hạn sau 90 ngày**. Đủ để demo. Muốn
> chạy liên tục + giữ PDF: đổi web plan sang `starter` và thêm lại block `disk:` (xem ghi chú trong
> `render.yaml`). Redis khai báo `type: keyvalue` (tên mới của Render); tài khoản/CLI cũ dùng `type: redis`.

### Cách B — Tạo thủ công

1. New → **Web Service** → repo này → **Root Directory: `be`**, **Runtime: Docker**.
2. New → **Postgres** và New → **Key Value (Redis)** (cùng region).
3. Trong Web Service → **Environment**, set các biến ở [bảng dưới](#biến-môi-trường-backend),
   nối `DATABASE_URL`/`REDIS_URL` tới 2 dịch vụ vừa tạo (Render có nút *Add from database/service*).

### Biến môi trường Backend

| Biến | Giá trị | Ghi chú |
|---|---|---|
| `DATABASE_URL` | từ Postgres | config tự ép `postgresql://` → `postgresql+asyncpg://` |
| `REDIS_URL` | từ Redis/Key Value | |
| `SECRET_KEY` | chuỗi ngẫu nhiên | ký JWT (Render `generateValue`) |
| `OPENAI_API_KEY` / `COHERE_API_KEY` | bí mật | |
| `WEAVIATE_URL` / `WEAVIATE_API_KEY` | bí mật | |
| `GOOGLE_CLIENT_ID` | OAuth client | |
| `ALLOWED_ORIGINS` | `["https://<fe>.vercel.app"]` | **JSON list**, CORS cho FE |
| `COOKIE_SECURE` | `true` | bắt buộc khi HTTPS |
| `COOKIE_SAMESITE` | `none` | bắt buộc vì FE/BE khác domain |
| `ENVIRONMENT` / `DEBUG` | `production` / `false` | |
| `UPLOAD_DIR` | `/app/storage/uploads` | trỏ vào disk đã mount |

Build xong, kiểm tra: `https://<be>.onrender.com/` trả JSON, và `…/docs` mở Swagger.

---

## 2. Deploy Backend lên Railway (thay cho Render)

Railway tự nhận `be/Dockerfile`:

1. New Project → Deploy from GitHub → chọn repo.
2. Service Settings → **Root Directory: `be`** (Railway sẽ build bằng Dockerfile).
3. Add **PostgreSQL** + **Redis** plugin → Railway tự tạo `DATABASE_URL`, `REDIS_URL`.
4. Variables: thêm các biến bí mật như bảng trên (`COOKIE_SAMESITE=none`, `COOKIE_SECURE=true`,
   `ALLOWED_ORIGINS=[...]`, `UPLOAD_DIR=/app/storage/uploads`).
5. Gắn **Volume** vào `/app/storage` để PDF lưu bền.

---

## 3. Deploy Frontend lên Vercel

1. Vercel → New Project → chọn repo → **Root Directory: `fe`** (Vercel tự nhận Next.js).
2. **Environment Variables**:

   | Biến | Giá trị |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://<be>.onrender.com` (URL backend ở bước 1, **không** kèm `/api/v1`) |
   | `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | cùng client ID với BE |

   FE tự ghép `${NEXT_PUBLIC_API_URL}/api/v1`.
3. Deploy → lấy domain, ví dụ `https://ten-app.vercel.app`.

---

## 4. Nối FE ↔ BE (quan trọng)

Sau khi có domain FE:

1. **CORS:** cập nhật `ALLOWED_ORIGINS` của BE = `["https://ten-app.vercel.app"]` rồi redeploy BE.
2. **Cookie xuyên domain:** đảm bảo BE có `COOKIE_SECURE=true` + `COOKIE_SAMESITE=none`
   (đăng nhập dùng httpOnly cookie; thiếu 2 cờ này trình duyệt sẽ chặn cookie cross-site).
3. **Google OAuth:** trong Google Cloud Console → OAuth client → thêm
   `https://ten-app.vercel.app` vào *Authorized JavaScript origins*.

---

## 5. Sau khi deploy

- **Migration** chạy tự động lúc container khởi động (`alembic upgrade head` trong Dockerfile CMD).
- **Nạp tài liệu:** dùng giao diện admin (upload PDF) hoặc script ingest để đẩy chunk vào Weaviate —
  DB rỗng thì chatbot chưa có gì để trả lời.
- **Kiểm tra nhanh:** `GET /` (JSON), `GET /api/v1/health` (`{"status":"ok"}`), mở FE đăng nhập + chat thử.
