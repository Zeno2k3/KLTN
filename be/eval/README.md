# RAGAS eval harness cho pipeline hỏi-đáp RAG

Đánh giá retrieval + chất lượng câu trả lời sau khi đổi pipeline (chunking / embedding /
retriever / rerank / prompt). Theo CLAUDE.md: thay đổi RAG phải có số RAGAS trước khi coi là xong.

## Cấu trúc

- `dataset.json` — bộ câu hỏi tuyển sinh + `ground_truth` (căn cứ trên corpus thật).
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

## Kết quả gần nhất (2026-06-20, 8 câu hỏi, top_k=30 → RRF → rerank top_n=6 → gpt-4o-mini)

| Metric | ViRanker | bge-reranker-v2-m3 |
|---|---|---|
| faithfulness | 0.9375 | 0.9375 |
| answer_relevancy | 0.4201 | 0.4757 |
| context_precision (w/ ref) | 0.7781 | 0.8283 |
| context_recall | 0.8125 | 0.8750 |

`answer_relevancy` thấp do 2 câu hỏi từ chối đúng (ngoài corpus) bị RAGAS chấm 0. Trên tập nhỏ
này bge nhỉnh hơn (chủ yếu câu lớp 1). Đổi model = 1 dòng `settings.rerank_model`.
