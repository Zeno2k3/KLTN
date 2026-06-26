"""Quét rerank_top_n TỐI ƯU tại alpha CỐ ĐỊNH (mặc định 0.6).

Tái dùng cache truy hồi (`results/_cache/retrieval_raw.json` + `corpus.json`) → KHÔNG gọi lại
Weaviate. Với mỗi câu answerable: lấy top-MAX_K UUID tại alpha cố định, dựng lại node từ text
corpus, gọi Cohere rerank THẬT, rồi tính Precision/Recall/F1/nDCG/MRR cho n = 1..RERANK_EVAL_N.
Nhãn relevance = nhãn tự động (đồng nhất với retrieval_sweep.py).

Chạy (venv chính):
    PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/rerank_topn_at_alpha.py --alpha 0.6
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core.schema import NodeWithScore, TextNode  # noqa: E402

from app.core.config import settings  # noqa: E402
from eval import metrics, relevance  # noqa: E402
from eval.retrieval_sweep import (  # noqa: E402
    MAX_K,
    RERANK_EVAL_N,
    RERANK_SLEEP,
    _agg,
    auto_relevant_set,
    build_keyword_df,
    load_dataset,
)

_HERE = Path(__file__).parent
_RESULTS = _HERE / "results"
_CACHE = _RESULTS / "_cache"


def _akey(alpha: float) -> str:
    return f"{alpha:.1f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.6)
    args = ap.parse_args()
    alpha = args.alpha

    ranked = json.loads((_CACHE / "retrieval_raw.json").read_text(encoding="utf-8"))
    corpus = json.loads((_CACHE / "corpus.json").read_text(encoding="utf-8"))
    data = load_dataset()

    # nhãn tự động (toàn corpus) — đồng nhất với harness
    norms = {u: relevance.normalize(c["text"]) for u, c in corpus.items()}
    kw_df = build_keyword_df(data, norms)
    rel_auto = {it["id"]: auto_relevant_set(it, corpus, kw_df) for it in data}
    answerable = [it["id"] for it in data if rel_auto[it["id"]]]
    print(
        f"alpha cố định = {alpha} | answerable = {len(answerable)} câu | "
        f"corpus = {len(corpus)} chunk | rerank tới n={RERANK_EVAL_N}"
    )

    from llama_index.postprocessor.cohere_rerank import CohereRerank

    reranker = CohereRerank(
        api_key=settings.cohere_api_key,
        model=settings.rerank_model,
        top_n=RERANK_EVAL_N,
    )

    rbq: list[tuple[list[int], int]] = []
    base_rbq: list[tuple[list[int], int]] = []  # trước rerank (hybrid thuần) để đối chứng
    for i, qid in enumerate(answerable, start=1):
        item = next(it for it in data if it["id"] == qid)
        uuids = ranked[qid][_akey(alpha)][:MAX_K]
        nodes = [
            NodeWithScore(node=TextNode(id_=u, text=corpus[u]["text"]), score=1.0 / r)
            for r, u in enumerate(uuids, start=1)
        ]
        for attempt in range(1, 6):
            try:
                time.sleep(RERANK_SLEEP)  # Cohere Trial 10/phút
                reranked = reranker.postprocess_nodes(nodes, query_str=item["question"])
                break
            except Exception as exc:  # noqa: BLE001 — 429 → chờ rồi thử lại
                print(f"  rerank retry {attempt}/5 ({type(exc).__name__})")
                time.sleep(20 * attempt)
        else:
            raise RuntimeError(f"Rerank thất bại: {qid}")
        ruuids = [str(n.node.node_id) for n in reranked]
        rels = [1 if u in rel_auto[qid] else 0 for u in ruuids]
        rbq.append((rels, len(rel_auto[qid])))
        base_rels = [1 if u in rel_auto[qid] else 0 for u in uuids]
        base_rbq.append((base_rels, len(rel_auto[qid])))
        if i % 10 == 0:
            print(f"  rerank {i}/{len(answerable)}")

    rerank: dict[str, dict] = {}
    for n in range(1, RERANK_EVAL_N + 1):
        m = _agg(rbq, n)
        m["mrr"] = metrics.mean_ignore_nan(
            [metrics.reciprocal_rank(r) for r, _ in rbq]
        )
        rerank[str(n)] = m

    n_star_f1 = max(range(1, RERANK_EVAL_N + 1), key=lambda n: rerank[str(n)]["f1"])

    # đối chứng: hybrid thuần (không rerank) tại cùng các n
    base = {str(n): _agg(base_rbq, n) for n in range(1, RERANK_EVAL_N + 1)}

    out = {
        "alpha": alpha,
        "n_answerable": len(answerable),
        "rerank_model": settings.rerank_model,
        "rerank": rerank,
        "baseline_hybrid": base,
        "rerank_top_n_star_f1": n_star_f1,
        "current_rerank_top_n": settings.rerank_top_n,
    }
    (_RESULTS / "rerank_topn_at_alpha.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n===== rerank_top_n tại alpha={alpha} (nhãn tự động, n={len(answerable)} câu) =====")
    print(" n | Prec   Recall  F1     nDCG   MRR   | (hybrid Recall@n)")
    for n in range(1, RERANK_EVAL_N + 1):
        m, b = rerank[str(n)], base[str(n)]
        mark = " *" if n == n_star_f1 else "  "
        print(
            f"{n:2d}{mark}| {m['precision']:.3f}  {m['recall']:.3f}  {m['f1']:.3f}  "
            f"{m['ndcg']:.3f}  {m['mrr']:.3f} |   {b['recall']:.3f}"
        )
    print(f"\n→ rerank_top_n* (max F1) = {n_star_f1} | config hiện tại = {settings.rerank_top_n}")
    print(f"Đã ghi: {_RESULTS / 'rerank_topn_at_alpha.json'}")


if __name__ == "__main__":
    main()
