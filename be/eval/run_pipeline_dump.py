"""Eval harness (bước 1): chạy pipeline RAG THẬT trên bộ câu hỏi, dump JSON cho RAGAS.

Chạy ở venv chính (be/.venv):
    PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/run_pipeline_dump.py \
        --out eval/results/viranker.json
A/B đổi reranker:
    ... --reranker BAAI/bge-reranker-v2-m3 --out eval/results/bge.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core.schema import MetadataMode  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.observability import init_tracing  # noqa: E402
from app.rag import query_engine, query_filters  # noqa: E402

logging.disable(logging.WARNING)

_DATASET = Path(__file__).parent / "dataset.json"


def _answer_with_retry(
    question: str, use_filter: bool, tries: int = 4
) -> tuple[str, list[str]]:
    """Pipeline 1 câu, retry khi lỗi mạng (SSL handshake/timeout hay xảy ra với cloud).

    ``use_filter``: mô phỏng đúng đường ``answer_question`` của Nhóm B — dựng MetadataFilters từ câu
    hỏi (extract_filters) + fallback-on-empty (filter rỗng → retry không filter)."""
    for attempt in range(1, tries + 1):
        try:
            filters = query_filters.extract_filters(question) if use_filter else None
            reranked = query_engine.retrieve_and_rerank(question, filters)
            if (
                not reranked
                and filters is not None
                and settings.filter_fallback_on_empty
            ):
                reranked = query_engine.retrieve_and_rerank(question, None)
            contexts = [
                n.node.get_content(metadata_mode=MetadataMode.NONE).strip()
                for n in reranked
            ]
            if reranked:
                # synthesize() trả (answer, sources, context) — eval chỉ cần answer.
                answer, _, _ = query_engine.synthesize(question, reranked)
            else:
                answer = query_engine._NO_CONTEXT_ANSWER
            return answer, contexts
        except Exception as exc:  # noqa: BLE001 — eval script, log & retry
            print(f"  (lỗi {attempt}/{tries}: {type(exc).__name__}) thử lại...")
            time.sleep(3 * attempt)
    raise RuntimeError(f"Thất bại sau {tries} lần: {question}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--reranker", default=None, help="ghi đè settings.rerank_model để A/B"
    )
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--filter",
        action="store_true",
        help="bật metadata filter Nhóm B (extract_filters + fallback) như answer_question",
    )
    ap.add_argument(
        "--dataset",
        default=None,
        help="đường dẫn dataset JSON (mặc định eval/dataset.json) — dùng subset khi chỉ ingest 1 doc",
    )
    args = ap.parse_args()
    if args.reranker:
        settings.rerank_model = args.reranker

    init_tracing()  # OTEL → Phoenix (script standalone không có lifespan app → phải tự bật)

    dataset_path = Path(args.dataset) if args.dataset else _DATASET
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    print(
        "RERANKER:",
        settings.rerank_model,
        "| top_n:",
        settings.rerank_top_n,
        "| filter:",
        args.filter,
    )
    out = []
    for i, item in enumerate(data, start=1):
        question = item["question"]
        t0 = time.perf_counter()
        answer, contexts = _answer_with_retry(question, use_filter=args.filter)
        print(f"[{i}/{len(data)}] ({time.perf_counter() - t0:.1f}s) {question[:50]}")
        print(f"    -> {answer[:90]}")
        out.append(
            {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": item["ground_truth"],
            }
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Đã ghi", out_path)


if __name__ == "__main__":
    main()
