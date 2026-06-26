"""Đánh giá retrieval_top_k TỐI ƯU tại alpha CỐ ĐỊNH (mặc định 0.6) — ĐO SAU RERANK, có trace Phoenix.

Khác với việc chỉ nhìn "trần Recall ứng viên": script này đo tác động THẬT của ``retrieval_top_k``
lên kết quả CUỐI (sau Cohere rerank, cắt còn ``top_n``). retrieval_top_k là độ sâu tập ứng viên đưa
vào reranker → top_k lớn cho reranker nhiều cơ hội kéo chunk vàng nằm sâu lên, nhưng quá lớn thì
thêm nhiễu/độ trễ.

Phương pháp (chính xác + tiết kiệm rate-limit Cohere Trial 10/phút):
1. Mỗi câu: retrieve THẬT top-MAX_K tại alpha (qua LlamaIndex → trace embedding + Weaviate hybrid),
   rồi rerank THẬT TOÀN BỘ (top_n=MAX_K, qua Cohere → trace) để lấy điểm rerank per-doc.
2. Cross-encoder chấm điểm ĐỘC LẬP từng cặp (query, doc) → mô phỏng mọi top_k bằng cách lọc tập
   ứng viên ``hybrid_order[:top_k]`` rồi giữ thứ tự rerank. KIỂM CHỨNG: rerank thật top-30 trên vài
   câu mẫu, so khớp top-5 với mô phỏng (phải trùng khớp).
3. Với mỗi (top_k, top_n): Precision/Recall/F1/nDCG/MRR theo nhãn tự động; kèm baseline KHÔNG rerank.

Chạy (venv chính):
    PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/topk_eval_at_alpha.py --alpha 0.6
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.observability import init_tracing  # noqa: E402
from app.rag.vector_store import weaviate_client  # noqa: E402
from eval import metrics, relevance  # noqa: E402
from eval.retrieval_sweep import (  # noqa: E402
    MAX_K,
    RERANK_SLEEP,
    _agg,
    auto_relevant_set,
    build_index,
    build_keyword_df,
    fetch_corpus,
    load_dataset,
    retrieve,
)

_HERE = Path(__file__).parent
_RESULTS = _HERE / "results"

TOPK_GRID = [5, 8, 10, 15, 20, 30, 40, 50]
TOPN_GRID = [1, 2, 3, 4, 5, 6, 8, 10]
TOPN_FOCUS = 4  # top_n cố định để xếp hạng top_k (đề xuất từ bước trước)
VERIFY_TOPK = 30  # kiểm chứng mô phỏng vs rerank thật ở độ sâu này
VERIFY_SAMPLE = 8


def _rerank_order(reranker, nodes, query):
    """Rerank THẬT toàn bộ nodes → list uuid theo điểm rerank giảm dần (có retry cho 429)."""
    for attempt in range(1, 6):
        try:
            time.sleep(RERANK_SLEEP)
            out = reranker.postprocess_nodes(nodes, query_str=query)
            return [str(n.node.node_id) for n in out]
        except Exception as exc:  # noqa: BLE001 — 429 → chờ rồi thử lại
            print(f"  rerank retry {attempt}/5 ({type(exc).__name__})")
            time.sleep(20 * attempt)
    raise RuntimeError("Rerank thất bại")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.6)
    args = ap.parse_args()
    alpha = args.alpha

    init_tracing()  # ← mọi retrieve/rerank lên Phoenix (project kltn-rag)
    print(
        f"Tracing Phoenix: enabled={settings.phoenix_enabled} → {settings.phoenix_project_name}"
    )

    from llama_index.postprocessor.cohere_rerank import CohereRerank

    data = load_dataset()

    with weaviate_client() as client:
        corpus = fetch_corpus(client)
        norms = {u: relevance.normalize(c["text"]) for u, c in corpus.items()}
        kw_df = build_keyword_df(data, norms)
        rel_auto = {it["id"]: auto_relevant_set(it, corpus, kw_df) for it in data}
        answerable = [it["id"] for it in data if rel_auto[it["id"]]]
        print(
            f"alpha={alpha} | corpus={len(corpus)} chunk | answerable={len(answerable)} câu | "
            f"top_k grid={TOPK_GRID} | rerank=toàn bộ top-{MAX_K}"
        )

        index = build_index(client)
        reranker_full = CohereRerank(
            api_key=settings.cohere_api_key, model=settings.rerank_model, top_n=MAX_K
        )
        reranker_verify = CohereRerank(
            api_key=settings.cohere_api_key, model=settings.rerank_model, top_n=5
        )

        hybrid_order: dict[str, list[str]] = {}
        rerank_order: dict[str, list[str]] = {}
        verify_rows: list[dict] = []
        t0 = time.perf_counter()
        for i, qid in enumerate(answerable, start=1):
            item = next(it for it in data if it["id"] == qid)
            nodes = retrieve(index, item["question"], alpha, MAX_K)  # trace
            hybrid_order[qid] = [str(n.node.node_id) for n in nodes]
            rerank_order[qid] = _rerank_order(
                reranker_full, nodes, item["question"]
            )  # trace
            # kiểm chứng phương pháp trên VERIFY_SAMPLE câu đầu
            if i <= VERIFY_SAMPLE:
                cand = set(hybrid_order[qid][:VERIFY_TOPK])
                sub_nodes = [n for n in nodes if str(n.node.node_id) in cand]
                real_top5 = _rerank_order(reranker_verify, sub_nodes, item["question"])[
                    :5
                ]
                sim_top5 = [u for u in rerank_order[qid] if u in cand][:5]
                verify_rows.append(
                    {
                        "qid": qid,
                        "match": real_top5 == sim_top5,
                        "real": real_top5,
                        "sim": sim_top5,
                    }
                )
            print(f"[{i}/{len(answerable)}] {qid} ({time.perf_counter() - t0:.0f}s)")

    # ---- mô phỏng top_k × top_n ----
    def sim_metrics(top_k: int, top_n: int) -> dict:
        rbq, base_rbq = [], []
        for qid in answerable:
            cand = hybrid_order[qid][:top_k]
            cset = set(cand)
            rer = [u for u in rerank_order[qid] if u in cset][:top_n]
            rbq.append(
                ([1 if u in rel_auto[qid] else 0 for u in rer], len(rel_auto[qid]))
            )
            base = cand[:top_n]
            base_rbq.append(
                ([1 if u in rel_auto[qid] else 0 for u in base], len(rel_auto[qid]))
            )
        m = _agg(rbq, top_n)
        m["mrr"] = metrics.mean_ignore_nan([metrics.reciprocal_rank(r) for r, _ in rbq])
        b = _agg(base_rbq, top_n)
        b["mrr"] = metrics.mean_ignore_nan(
            [metrics.reciprocal_rank(r) for r, _ in base_rbq]
        )
        return {"rerank": m, "baseline": b}

    grid = {
        str(tk): {str(tn): sim_metrics(tk, tn) for tn in TOPN_GRID} for tk in TOPK_GRID
    }

    # chọn top_k* tại top_n cố định: max F1 (tie-break Recall) — bão hòa lợi ích
    def score(tk: int) -> tuple[float, float]:
        m = grid[str(tk)][str(TOPN_FOCUS)]["rerank"]
        return (m["f1"], m["recall"])

    topk_star = max(TOPK_GRID, key=score)
    # điểm bão hòa: top_k nhỏ nhất đạt ≥ 99% Recall@TOPN_FOCUS của top_k=MAX_K
    rec_max = grid[str(MAX_K)][str(TOPN_FOCUS)]["rerank"]["recall"]
    topk_sat = next(
        (
            tk
            for tk in TOPK_GRID
            if rec_max > 0
            and grid[str(tk)][str(TOPN_FOCUS)]["rerank"]["recall"] >= 0.99 * rec_max
        ),
        MAX_K,
    )

    out = {
        "alpha": alpha,
        "n_answerable": len(answerable),
        "corpus_chunks": len(corpus),
        "rerank_model": settings.rerank_model,
        "topk_grid": TOPK_GRID,
        "topn_grid": TOPN_GRID,
        "topn_focus": TOPN_FOCUS,
        "grid": grid,
        "topk_star_f1": topk_star,
        "topk_saturation": topk_sat,
        "verify": verify_rows,
        "current_config": {
            "hybrid_alpha": settings.hybrid_alpha,
            "retrieval_top_k": settings.retrieval_top_k,
            "rerank_top_n": settings.rerank_top_n,
        },
    }
    _RESULTS.mkdir(parents=True, exist_ok=True)
    (_RESULTS / "topk_eval_at_alpha.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ---- in tóm tắt ----
    n_ok = sum(1 for v in verify_rows if v["match"])
    print(
        f"\nKiểm chứng phương pháp (mô phỏng vs rerank thật top-{VERIFY_TOPK}, top-5): "
        f"{n_ok}/{len(verify_rows)} câu KHỚP HOÀN TOÀN"
    )

    print(
        f"\n===== retrieval_top_k tại alpha={alpha}, SAU rerank @top_n={TOPN_FOCUS} "
        f"(nhãn tự động, {len(answerable)} câu) ====="
    )
    print("top_k | Prec   Recall  F1     nDCG   MRR   | (no-rerank Recall@n)")
    for tk in TOPK_GRID:
        m = grid[str(tk)][str(TOPN_FOCUS)]["rerank"]
        b = grid[str(tk)][str(TOPN_FOCUS)]["baseline"]
        mark = " *" if tk == topk_star else ("sat" if tk == topk_sat else "  ")
        print(
            f"{tk:5d}{mark}| {m['precision']:.3f}  {m['recall']:.3f}  {m['f1']:.3f}  "
            f"{m['ndcg']:.3f}  {m['mrr']:.3f} |   {b['recall']:.3f}"
        )

    print(f"\nRecall@{TOPN_FOCUS} theo top_k × top_n (sau rerank):")
    header = "top_k\\n | " + "  ".join(f"n={tn:<2d}" for tn in TOPN_GRID)
    print(header)
    for tk in TOPK_GRID:
        row = "  ".join(
            f"{grid[str(tk)][str(tn)]['rerank']['recall']:.3f}" for tn in TOPN_GRID
        )
        print(f"{tk:6d} | {row}")

    print(
        f"\n→ retrieval_top_k* (max F1@{TOPN_FOCUS}) = {topk_star} | "
        f"bão hòa Recall (≥99% trần) = {topk_sat} | config hiện tại = {settings.retrieval_top_k}"
    )
    print(f"Đã ghi: {_RESULTS / 'topk_eval_at_alpha.json'}")


if __name__ == "__main__":
    main()
