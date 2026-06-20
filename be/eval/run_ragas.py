"""Eval harness (bước 2): tính RAGAS trên dataset đã dump bởi run_pipeline_dump.py.

RAGAS không cài được ở venv chính (Python 3.14 thiếu wheel; scikit-network cần build C++).
→ Chạy ở venv riêng Python 3.11 (xem README). Cần OPENAI_API_KEY trong môi trường.

    export OPENAI_API_KEY=...   # nạp từ be/.env
    ./_ragas_venv/Scripts/python.exe eval/run_ragas.py eval/results/viranker.json
"""

from __future__ import annotations

import json
import math
import sys

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import EvaluationDataset, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)


def main() -> None:
    inp = sys.argv[1] if len(sys.argv) > 1 else "eval/results/viranker.json"
    with open(inp, encoding="utf-8") as f:
        data = json.load(f)

    llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    emb = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
    samples = [
        {
            "user_input": d["question"],
            "response": d["answer"],
            "retrieved_contexts": d["contexts"] or ["(không có ngữ cảnh)"],
            "reference": d["ground_truth"],
        }
        for d in data
    ]
    dataset = EvaluationDataset.from_list(samples)
    metrics = [
        Faithfulness(),
        ResponseRelevancy(),
        LLMContextPrecisionWithReference(),
        LLMContextRecall(),
    ]
    result = evaluate(dataset=dataset, metrics=metrics, llm=llm, embeddings=emb)

    df = result.to_pandas()
    meta = {"user_input", "response", "retrieved_contexts", "reference"}
    cols = [c for c in df.columns if c not in meta]
    print(f"\n=== RAGAS: {inp} ===")
    for c in cols:
        vals = [
            v for v in df[c].tolist() if isinstance(v, (int, float)) and not math.isnan(v)
        ]
        if vals:
            print(f"  {c:38s}: {sum(vals) / len(vals):.4f}")


if __name__ == "__main__":
    main()
