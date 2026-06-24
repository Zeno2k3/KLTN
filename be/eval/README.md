# RAGAS eval harness cho pipeline hỏi-đáp RAG

Đánh giá retrieval + chất lượng câu trả lời sau khi đổi pipeline (chunking / embedding /
retriever / rerank / prompt). Theo CLAUDE.md: thay đổi RAG phải có số RAGAS trước khi coi là xong.

## Cấu trúc

- `dataset.json` — bộ câu hỏi tuyển sinh + `ground_truth` (căn cứ trên corpus thật). **12 câu** căn
  cứ 2 tài liệu **đặc khu Côn Đảo** + **phường Bình Thạnh** (năm học 2026-2027): 4 câu theo Côn Đảo,
  4 câu theo Bình Thạnh (gồm 1 câu từ chối học phí), 4 câu chung (quy trình/đăng ký/năm học).
  8/12 câu nêu rõ phường + năm → **kích hoạt metadata filter** (đánh giá đúng Nhóm B). ⚠️ **Bắt buộc
  ingest 2 doc này** (lý tưởng cả corpus) vào Weaviate trước khi chạy, nếu không retrieval sẽ rỗng.
- `run_pipeline_dump.py` — chạy pipeline THẬT (hybrid → rerank → LLM), dump `{question, answer,
  contexts, ground_truth}` ra `results/`. Chạy ở **venv chính** (`be/.venv`, Python 3.14).
- `run_ragas.py` — tính 4 metric RAGAS từ file dump. Chạy ở **venv ragas riêng** (Python 3.11).
- `results/` — output dump + dùng làm bằng chứng.

## Vì sao 2 venv?

RAGAS kéo `scikit-network` cần biên dịch C++ và chưa có wheel cho Python 3.14 → không cài được ở
venv chính. Dựng venv 3.11 riêng (có sẵn wheel), cô lập khỏi app:

```bash
python -m venv _ragas_venv                                  # python 3.11
./_ragas_venv/Scripts/python.exe -m pip install "ragas<0.3"
# langchain 1.x bỏ langchain_community.chat_models.vertexai mà ragas import cứng → hạ về 0.3.x:
./_ragas_venv/Scripts/python.exe -m pip install \
    "langchain-core<0.4" "langchain-community<0.4" "langchain<0.4" "langchain-openai<0.3"
```

## Chạy

```bash
cd be
# 1) Dump pipeline (venv chính). A/B: thêm --reranker BAAI/bge-reranker-v2-m3
PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/run_pipeline_dump.py --out eval/results/viranker.json

# 2) Tính RAGAS (venv 3.11). Nạp key từ .env, không in ra:
export OPENAI_API_KEY="$(grep '^OPENAI_API_KEY=' .env | cut -d= -f2- | tr -d '\r')"
PYTHONUTF8=1 ./_ragas_venv/Scripts/python.exe eval/run_ragas.py eval/results/viranker.json
```

## Kết quả (2026-06-24, 12 câu, corpus Côn Đảo + Bình Thạnh đã re-ingest qua pipeline A+B)

Cohere `rerank-multilingual-v3.0` · top_n=6 · gpt-4o-mini. So **filter TẮT vs BẬT** (cùng corpus đã
clean → cô lập Nhóm B). Dump: `results/dump_nofilter.json`, `results/dump_filter.json`.

| Metric | filter TẮT | filter BẬT (A+B) | Δ |
|---|---|---|---|
| faithfulness | 0.7500 | **0.8333** | **+0.083** |
| answer_relevancy | 0.4795 | 0.4632 | −0.016 |
| context_precision (w/ ref) | 0.8653 | 0.8217 | −0.044 |
| context_recall | 0.9167 | 0.8750 | −0.042 |

**Diễn giải:** filter nâng **faithfulness** (LLM chỉ thấy ngữ cảnh đúng phường → ít trộn nhầm dữ kiện
phường khác); precision/recall lệch nhẹ trong biên độ nhiễu (12 câu, ±0.04 ≈ 0.5 câu). Trên corpus
NHỎ (2 phường) giá trị filter bị **muted** vì retrieval đã gần đúng dù không lọc; lợi ích thật sự
(chặn nhầm phường) chỉ rõ trên **corpus đầy đủ 158 phường**. `answer_relevancy` thấp do 2 câu từ chối
đúng (Q12 học phí, Q2 lớp 6) bị RAGAS chấm ~0.

**Chưa cô lập Nhóm A (clean):** cả hai run đều dùng text ĐÃ clean. Muốn đo riêng clean → re-ingest với
`CLEAN_ENABLED=false` rồi dump+ragas (clean chỉ gỡ ~43 ký tự số trang/18 trang nên tác động dự kiến nhỏ).

### Cũ (2026-06-20, corpus An Khánh/An Đông — KHÔNG so trực tiếp được)
faithfulness 0.9375 · answer_relevancy 0.42–0.48 · context_precision 0.78–0.83 · context_recall 0.81–0.88.
