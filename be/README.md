# Backend — FastAPI

REST API xây dựng bằng **FastAPI**, **Python 3.14**, **SQLAlchemy 2** (async) và **PostgreSQL**.

## Tech Stack

| Công nghệ | Phiên bản | Mô tả |
|---|---|---|
| Python | 3.14.6 | Runtime |
| FastAPI | 0.137.2 | Web framework |
| Uvicorn | 0.49.0 | ASGI server |
| Pydantic v2 | 2.13.4 | Data validation & settings |
| SQLAlchemy | 2.0.51 | Async ORM |
| Alembic | 1.18.4 | Database migrations |
| asyncpg | 0.31.0 | PostgreSQL async driver |
| Redis | 8.0.0 | Cache |
| python-jose | 3.5.0 | JWT authentication |
| passlib + bcrypt | 1.7.4 | Password hashing |
| Ruff | 0.15.17 | Linter & formatter |
| pytest | 9.1.0 | Testing |

## Cấu trúc thư mục

```
be/
├── app/                        # Package ứng dụng chính
│   │
│   ├── main.py                 # Khởi tạo FastAPI app, CORS, lifespan, include router
│   │
│   ├── core/                   # Cấu hình nền tảng
│   │   ├── config.py           # Settings đọc từ .env (pydantic-settings)
│   │   ├── database.py         # Async engine, session factory, Base model
│   │   └── security.py         # JWT encode/decode, bcrypt hash/verify
│   │
│   ├── api/                    # HTTP layer
│   │   ├── deps.py             # Dependency injection (get_db, get_current_user)
│   │   └── v1/
│   │       ├── router.py       # Gộp tất cả routes của v1
│   │       └── routes/         # Một file = một nhóm endpoint
│   │           └── health.py   # GET /api/v1/health
│   │
│   ├── models/                 # SQLAlchemy ORM models (ánh xạ bảng DB)
│   ├── schemas/                # Pydantic schemas (request body, response)
│   ├── services/               # Business logic, không phụ thuộc HTTP
│   ├── repositories/           # Data access layer, tương tác DB
│   └── utils/                  # Hàm tiện ích dùng chung
│
├── alembic/                    # Database migrations
│   ├── versions/               # Các file migration
│   ├── env.py                  # Cấu hình async migration
│   └── script.py.mako          # Template sinh migration
│
├── tests/                      # Test suite
│   ├── api/                    # Test theo endpoint
│   └── test_health.py
│
├── scripts/
│   └── run.py                  # Chạy uvicorn programmatically
│
├── .env.example                # Template biến môi trường
├── .gitignore
├── alembic.ini                 # Cấu hình Alembic
├── pyproject.toml              # Cấu hình project, ruff, pytest, coverage
└── requirements.txt            # Dependencies
```

### Luồng xử lý một request

```
Request
  → api/v1/routes/*.py     (validate input qua Schema)
  → api/deps.py            (inject DB session, xác thực token)
  → services/*.py          (business logic)
  → repositories/*.py      (truy vấn DB qua SQLAlchemy)
  → models/*.py            (ORM model)
  → Response (Schema)
```

## Cài đặt & Chạy

```bash
# Tạo virtual environment với Python 3.14
py -3.14 -m venv .venv

# Kích hoạt venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# Cài dependencies
pip install -r requirements.txt

# Cấu hình môi trường
cp .env.example .env
# Chỉnh sửa .env với thông tin DB, secret key...

# Chạy development server (http://localhost:8000)
python scripts/run.py
# hoặc
fastapi dev app/main.py

# Chạy production
fastapi run app/main.py
```

## Database Migrations

```bash
# Tạo migration mới
alembic revision --autogenerate -m "mô tả thay đổi"

# Áp dụng migration
alembic upgrade head

# Rollback 1 bước
alembic downgrade -1
```

## Testing

```bash
# Chạy toàn bộ test
pytest

# Chạy với coverage report
pytest --cov=app --cov-report=html

# Chạy một file cụ thể
pytest tests/test_health.py -v
```

## API Docs

Sau khi chạy server, truy cập:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Biến môi trường

Xem [.env.example](.env.example) để biết danh sách đầy đủ. Các biến quan trọng:

| Biến | Mô tả |
|---|---|
| `DATABASE_URL` | Connection string PostgreSQL |
| `SECRET_KEY` | Khóa bí mật ký JWT |
| `ALLOWED_ORIGINS` | Danh sách origin cho CORS (frontend URL) |
| `DEBUG` | `true` để bật auto-reload và SQL logging |
