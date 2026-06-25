# Hướng dẫn chạy đánh giá RAGAS (từng bước)

> File này là **hướng dẫn thao tác**. Phần tham chiếu cấu trúc + kết quả lịch sử xem [README.md](README.md).

RAGAS chấm 4 chỉ số chất lượng RAG. Theo `CLAUDE.md`: **mọi thay đổi pipeline** (chunking / embedding /
retriever / rerank / prompt) phải có số RAGAS trước khi coi là "Xong".

---

## 0. Bức tranh tổng quát — 2 bước, 2 môi trường (venv)

```
dataset.json ──(Bước 1: venv chính .venv, Py3.14)──> results/*.json ──(Bước 2: venv _ragas_venv, Py3.11)──> 4 metric
              run_pipeline_dump.py  (chạy pipeline THẬT)            run_ragas.py  (tính RAGAS)
```

**Vì sao 2 venv?** RAGAS kéo `scikit-network` (cần biên dịch C++, chưa có wheel cho Python 3.14) →
không cài được ở venv chính. Phải dựng venv **Python 3.11** riêng (`be/_ragas_venv`) chỉ để tính metric.

---

## 1. Chuẩn bị (làm 1 lần)

### 1.1. Hai venv
- **Venv chính** `be/.venv` (Python 3.14) — đã có, chạy pipeline thật (Bước 1).
- **Venv RAGAS** `be/_ragas_venv` (Python 3.11) — nếu **chưa có**, dựng:
  ```bash
  cd be
  python -m venv _ragas_venv                                   # phải là Python 3.11
  ./_ragas_venv/Scripts/python.exe -m pip install "ragas<0.3"
  # langchain 1.x bỏ module ragas import cứng → ghim 0.3.x:
  ./_ragas_venv/Scripts/python.exe -m pip install \
      "langchain-core<0.4" "langchain-community<0.4" "langchain<0.4" "langchain-openai<0.3"
  ```

### 1.2. Khóa API trong `be/.env`
- `OPENAI_API_KEY` — dùng ở **cả 2 bước** (LLM tổng hợp + LLM chấm RAGAS + embedding).
- `COHERE_API_KEY` — rerank ở Bước 1.
- `WEAVIATE_URL` / `WEAVIATE_API_KEY` — vector store.

### 1.3. ⚠️ Corpus phải đã ingest vào Weaviate (gài bẫy số 1)
`dataset.json` gồm **12 câu** căn cứ 2 tài liệu: **đặc khu Côn Đảo** + **phường Bình Thạnh** (năm học
2026-2027). **Thiếu doc nào → 4 câu của doc đó ra ngữ cảnh rỗng → số RAGAS vô nghĩa.**

Kiểm nhanh có bao nhiêu doc trong DB:
```bash
cd be
PYTHONUTF8=1 ./.venv/Scripts/python.exe -c "import asyncio; from sqlalchemy import select, func; from app.core.database import AsyncSessionLocal; from app.models.document import Document; \
import sys; sys.stdout.reconfigure(encoding='utf-8'); \
print(asyncio.run((lambda: __import__('app.core.database'))()) ) " 2>/dev/null
```
hoặc đơn giản mở trang admin tài liệu. Nếu thiếu, **ingest trước** (tên file phải có **năm học + phường/xã**
để parse `school_year`/`ward` — xem quy ước trong memory dự án):
```bash
PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/ingest_docs.py \
    "duong/dan/...phuong Binh Thanh, nam hoc 2026-2027.pdf" \
    "duong/dan/...dac khu Con Dao, nam hoc 2026-2027.pdf"
```

---

## 2. Chạy đánh giá (mỗi lần đo)

> Tất cả lệnh chạy **từ thư mục `be/`**. `PYTHONUTF8=1` để Windows in tiếng Việt không lỗi cp1252.

### Bước 1 — Dump pipeline THẬT → JSON
Chạy retrieve (hybrid BM25 + vector) → Cohere rerank → LLM tổng hợp trên từng câu, ghi
`{question, answer, contexts, ground_truth}`:
```bash
cd be
# Đúng đường người dùng thật (BẬT metadata filter Nhóm B):
PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/run_pipeline_dump.py --filter --out eval/results/llamaparse.json
```

### Bước 2 — Tính RAGAS từ file dump
```bash
export OPENAI_API_KEY="$(grep '^OPENAI_API_KEY=' .env | cut -d= -f2- | tr -d '\r')"
PYTHONUTF8=1 ./_ragas_venv/Scripts/python.exe eval/run_ragas.py eval/results/llamaparse.json
```
In ra 4 dòng metric (trung bình trên toàn dataset).

---

## 3. Đọc kết quả — 4 metric

| Metric | Hỏi điều gì | Cao = tốt khi |
|---|---|---|
| **faithfulness** | Câu trả lời có **bám ngữ cảnh** không (không bịa)? | Mỗi khẳng định đều suy ra được từ context |
| **answer_relevancy** | Câu trả lời có **đúng trọng tâm** câu hỏi không? | Trả lời thẳng, không lan man |
| **context_precision** (w/ ref) | Ngữ cảnh truy hồi có **đúng/ít rác** không? | Chunk liên quan xếp trên |
| **context_recall** | Ngữ cảnh có **đủ** để trả lời không? | Truy hồi không bỏ sót dữ kiện |

> Lưu ý diễn giải: câu **từ chối đúng** (vd hỏi học phí → "không có thông tin") thường bị RAGAS chấm
> `answer_relevancy ≈ 0` — kéo trung bình xuống dù hành vi ĐÚNG. Đọc theo từng câu, đừng chỉ nhìn trung bình.

---

## 4. Tùy chọn & A/B

| Cờ (Bước 1) | Tác dụng |
|---|---|
| `--out <path>` | **(bắt buộc)** đường dẫn file dump |
| `--filter` | bật metadata filter Nhóm B (`extract_filters` + fallback-on-empty) như `answer_question` thật. **Bỏ cờ = filter TẮT** |
| `--reranker <model>` | ghi đè `rerank_model` để A/B (vd `BAAI/bge-reranker-v2-m3`) |
| `--dataset <path>` | dùng dataset khác / subset (khi chỉ ingest 1 doc) |

**A/B filter TẮT vs BẬT** (cô lập tác dụng metadata filter trên cùng corpus):
```bash
PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/run_pipeline_dump.py        --out eval/results/nofilter.json
PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/run_pipeline_dump.py --filter --out eval/results/filter.json
export OPENAI_API_KEY="$(grep '^OPENAI_API_KEY=' .env | cut -d= -f2- | tr -d '\r')"
PYTHONUTF8=1 ./_ragas_venv/Scripts/python.exe eval/run_ragas.py eval/results/nofilter.json
PYTHONUTF8=1 ./_ragas_venv/Scripts/python.exe eval/run_ragas.py eval/results/filter.json
```

---

## 5. Lỗi thường gặp (troubleshooting)

| Triệu chứng | Nguyên nhân & cách xử lý |
|---|---|
| `contexts` rỗng / metric thấp bất thường | **Chưa ingest corpus** vào Weaviate (mục 1.3) — ingest 2 doc rồi chạy lại |
| `ModuleNotFoundError` khi chạy `run_ragas.py` | Sai venv — phải dùng `_ragas_venv/Scripts/python.exe`, không phải `.venv` |
| Lỗi import `langchain_community...vertexai` | Chưa ghim langchain 0.3.x — chạy lại lệnh pip ở mục 1.1 |
| `UnicodeEncodeError ... charmap` | Thiếu `PYTHONUTF8=1` đầu lệnh (Windows cp1252) |
| Bước 2 báo thiếu key | Chưa `export OPENAI_API_KEY=...` cho shell chạy venv ragas |
| Lỗi SSL/timeout giữa chừng | Bình thường với cloud — `run_pipeline_dump.py` đã tự retry 4 lần/câu |

---

## 6. Phoenix trace (kèm theo)

Bước 1 nay **tự gọi `init_tracing()`** → mỗi lần dump, các span retrieve/rerank/synthesize + call
LLM/embedding xuất hiện ở Phoenix project **`kltn-rag`**. Dùng để soi chi tiết từng câu khi metric bất thường.
