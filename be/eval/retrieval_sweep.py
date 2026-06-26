"""Harness ĐÁNH GIÁ & TỐI ƯU tham số hybrid retrieval (alpha, top_k) — bước thực thi chính.

Quy trình (xem kế hoạch khóa luận):
1. Quét ``alpha ∈ {0.0..1.0}`` × truy hồi tới ``MAX_K`` cho 51 câu (tái dùng 1 client Weaviate +
   1 index → nhanh; mirror đúng cấu hình production: HYBRID + RRF + query_properties).
2. Gán nhãn relevance theo HAI nguồn:
   - TỰ ĐỘNG (chuẩn chính): trigram-recall đoạn vàng + keyword hiếm, trên TOÀN corpus → R_q đầy đủ.
   - GEMINI (đối chứng, provider độc lập): chấm nhị phân trên pool (union top-K qua mọi alpha).
3. Tính Recall@k / Precision@k / F1 / Hit / MRR / nDCG tại mọi (alpha, k); tổng hợp toàn cục + tách
   theo ``favors`` và ``category``; chạy dưới CẢ hai nguồn nhãn để kiểm tính bền của alpha*.
4. Chọn alpha* (max Recall), retrieval_top_k* (điểm bão hòa), rerank_top_n* (Cohere rerank).
5. Cohen's κ giữa nhãn tự động và Gemini (chứng minh độ tin của nhãn tự động).

Chạy (venv chính):
    PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/retrieval_sweep.py
    ... --no-judge      # bỏ lớp Gemini (chỉ nhãn tự động)
    ... --refresh       # bỏ cache truy hồi, gọi Weaviate lại
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import VectorStoreIndex  # noqa: E402
from llama_index.core.vector_stores.types import VectorStoreQueryMode  # noqa: E402
from weaviate.classes.query import HybridFusion  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.observability import init_tracing  # noqa: E402
from app.rag.vector_store import (  # noqa: E402
    _embed_model,
    _vector_store,
    weaviate_client,
)
from eval import metrics, relevance  # noqa: E402
from eval.llm_judge import JudgeItem, judge_all  # noqa: E402

logging.disable(logging.WARNING)

_HERE = Path(__file__).parent
_DATASET = _HERE / "retrieval_eval.jsonl"
_RESULTS = _HERE / "results"
_CACHE = _RESULTS / "_cache"

# Lưới tham số
ALPHA_GRID = [round(i / 10, 1) for i in range(11)]  # 0.0, 0.1, ..., 1.0
MAX_K = 50
K_GRID = [1, 3, 5, 8, 10, 15, 20, 30, 50]
K_SELECT = 10  # mốc k để CHỌN alpha*
POOL_K = 30  # độ sâu gộp pool cho Gemini
RERANK_EVAL_N = 15
RERANK_SLEEP = 6.5  # giãn cách giữa các lệnh rerank (Cohere Trial giới hạn 10 lệnh/phút)
OVERLAP_TH = 0.5
RARE_DF = 3  # keyword df ≤ ngưỡng này mới được tính là anchor đặc trưng


# --------------------------------------------------------------------------- dataset & corpus
def load_dataset() -> list[dict]:
    rows = []
    for line in _DATASET.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def fetch_corpus(client) -> dict[str, dict]:
    col = client.collections.get(settings.weaviate_collection)
    corpus: dict[str, dict] = {}
    for o in col.iterator():
        p = o.properties
        doc_id = p.get("document_id")
        corpus[str(o.uuid)] = {
            "text": p.get(settings.weaviate_text_key) or "",
            "ward": p.get("ward"),
            "document_id": str(doc_id) if doc_id is not None else None,
            "page": p.get("page_number"),
        }
    return corpus


def build_index(client) -> VectorStoreIndex:
    return VectorStoreIndex.from_vector_store(
        vector_store=_vector_store(client), embed_model=_embed_model()
    )


def retrieve(index: VectorStoreIndex, query: str, alpha: float, top_k: int):
    """Mirror production hybrid_retrieve nhưng tái dùng index."""
    retriever = index.as_retriever(
        vector_store_query_mode=VectorStoreQueryMode.HYBRID,
        alpha=alpha,
        similarity_top_k=top_k,
        vector_store_kwargs={
            "fusion_type": HybridFusion.RANKED,
            "query_properties": [settings.weaviate_text_key],
        },
    )
    return retriever.retrieve(query)


def _akey(alpha: float) -> str:
    return f"{alpha:.1f}"


# --------------------------------------------------------------------------- nhãn tự động
def build_keyword_df(data: list[dict], norms: dict[str, str]) -> dict[str, int]:
    """Document-frequency của mỗi keyword (chuẩn hóa) trên corpus → chặn keyword chung chung."""
    df: dict[str, int] = {}
    for item in data:
        for kw in item.get("expected_keywords", []) or []:
            k = relevance.normalize(kw)
            if k and k not in df:
                df[k] = sum(
                    1 for cn in norms.values() if relevance.keyword_present(k, cn)
                )
    return df


def auto_relevant_set(item: dict, corpus: dict, kw_df: dict[str, int]) -> set[str]:
    if item.get("source_doc") == "none":
        return set()
    ref = item.get("reference_context") or ""
    kws = item.get("expected_keywords") or []
    return {
        u
        for u, c in corpus.items()
        if relevance.is_relevant(
            c["text"],
            ref,
            kws,
            overlap_threshold=OVERLAP_TH,
            keyword_df=kw_df,
            rare_df=RARE_DF,
        )
    }


# --------------------------------------------------------------------------- gom metric
def _agg(rels_by_query: list[tuple[list[int], int]], k: int) -> dict[str, float]:
    return {
        "recall": metrics.mean_ignore_nan(
            [metrics.recall_at_k(r, t, k) for r, t in rels_by_query]
        ),
        "precision": metrics.mean_ignore_nan(
            [metrics.precision_at_k(r, k) for r, _ in rels_by_query]
        ),
        "f1": metrics.mean_ignore_nan(
            [metrics.f1_at_k(r, t, k) for r, t in rels_by_query]
        ),
        "hit": metrics.mean_ignore_nan(
            [metrics.hit_at_k(r, k) for r, _ in rels_by_query]
        ),
        "ndcg": metrics.mean_ignore_nan(
            [metrics.ndcg_at_k(r, t, k) for r, t in rels_by_query]
        ),
    }


def sweep_group(ranked: dict, rel_sets: dict, qids: list[str]) -> dict:
    """{alpha: {k: metrics, 'mrr': x, 'n': int}} cho nhóm câu answerable trong qids."""
    out: dict[str, dict] = {}
    answerable = [q for q in qids if len(rel_sets.get(q, set())) > 0]
    for alpha in ALPHA_GRID:
        rels_by_query = []
        for q in answerable:
            uuids = ranked[q][_akey(alpha)]
            rels = [1 if u in rel_sets[q] else 0 for u in uuids]
            rels_by_query.append((rels, len(rel_sets[q])))
        per_k = {str(k): _agg(rels_by_query, k) for k in K_GRID}
        per_k["mrr"] = metrics.mean_ignore_nan(
            [metrics.reciprocal_rank(r) for r, _ in rels_by_query]
        )
        per_k["n"] = len(answerable)
        out[_akey(alpha)] = per_k
    return out


def pick_alpha(overall: dict) -> float:
    return max(
        ALPHA_GRID,
        key=lambda a: (
            overall[_akey(a)][str(K_SELECT)]["recall"],
            overall[_akey(a)][str(K_SELECT)]["f1"],
        ),
    )


def saturation_topk(overall: dict, alpha: float) -> int:
    rec_max = overall[_akey(alpha)][str(MAX_K)]["recall"]
    for k in K_GRID:
        if rec_max > 0 and overall[_akey(alpha)][str(k)]["recall"] >= 0.99 * rec_max:
            return k
    return MAX_K


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    init_tracing()
    _CACHE.mkdir(parents=True, exist_ok=True)
    data = load_dataset()
    print(f"Dataset: {len(data)} câu | alpha grid: {ALPHA_GRID} | MAX_K={MAX_K}")

    raw_cache, corpus_cache = _CACHE / "retrieval_raw.json", _CACHE / "corpus.json"
    if raw_cache.exists() and corpus_cache.exists() and not args.refresh:
        print("Nạp cache truy hồi...")
        ranked = json.loads(raw_cache.read_text(encoding="utf-8"))
        corpus = json.loads(corpus_cache.read_text(encoding="utf-8"))
    else:
        ranked = {}
        with weaviate_client() as client:
            corpus = fetch_corpus(client)
            wards: dict = {}
            for c in corpus.values():
                wards[c["ward"]] = wards.get(c["ward"], 0) + 1
            print(f"Corpus: {len(corpus)} chunk | ward: {wards}")
            index = build_index(client)
            t0 = time.perf_counter()
            for i, item in enumerate(data, start=1):
                ranked[item["id"]] = {}
                for alpha in ALPHA_GRID:
                    for attempt in range(1, 5):
                        try:
                            nodes = retrieve(index, item["question"], alpha, MAX_K)
                            break
                        except Exception as exc:  # noqa: BLE001
                            print(f"  retry {attempt} ({type(exc).__name__})")
                            time.sleep(2 * attempt)
                    else:
                        raise RuntimeError(f"Truy hồi thất bại: {item['id']} a={alpha}")
                    ranked[item["id"]][_akey(alpha)] = [
                        str(n.node.node_id) for n in nodes
                    ]
                print(
                    f"[{i}/{len(data)}] {item['id']} ({time.perf_counter() - t0:.0f}s)"
                )
        raw_cache.write_text(json.dumps(ranked, ensure_ascii=False), encoding="utf-8")
        corpus_cache.write_text(
            json.dumps(corpus, ensure_ascii=False), encoding="utf-8"
        )

    # ---- nhãn tự động (toàn corpus) ----
    norms = {u: relevance.normalize(c["text"]) for u, c in corpus.items()}
    kw_df = build_keyword_df(data, norms)
    rel_auto = {item["id"]: auto_relevant_set(item, corpus, kw_df) for item in data}
    negatives = [it["id"] for it in data if it.get("source_doc") == "none"]
    auto_answerable = [it["id"] for it in data if rel_auto[it["id"]]]
    auto_zero = [
        it["id"] for it in data if not rel_auto[it["id"]] and it["id"] not in negatives
    ]
    print(
        f"Nhãn tự động: answerable={len(auto_answerable)} | negative={len(negatives)} "
        f"| không gán được (multi-hop/cross-doc): {auto_zero}"
    )

    # ---- lớp Gemini (pool) ----
    rel_gem: dict[str, set[str]] = {}
    agreement: dict = {}
    if not args.no_judge:
        items: list[JudgeItem] = []
        pool_by_q: dict[str, set[str]] = {}
        for item in data:
            qid = item["id"]
            pool = set()
            for alpha in ALPHA_GRID:
                pool.update(ranked[qid][_akey(alpha)][:POOL_K])
            pool_by_q[qid] = {u for u in pool if u in corpus}
            for u in pool_by_q[qid]:
                items.append(
                    JudgeItem(
                        key=f"{qid}::{u}",
                        question=item["question"],
                        ground_truth=item.get("ground_truth", ""),
                        reference_context=item.get("reference_context", ""),
                        chunk_text=corpus[u]["text"],
                    )
                )
        print(
            f"LLM-judge ({settings.openai_chat_model}): {len(items)} cặp (pool top-{POOL_K} × mọi alpha)"
        )
        verdicts = judge_all(items, _CACHE / "judge_openai.json")
        for item in data:
            qid = item["id"]
            if item.get("source_doc") == "none":
                rel_gem[qid] = set()
            else:
                rel_gem[qid] = {
                    u for u in pool_by_q[qid] if verdicts.get(f"{qid}::{u}")
                }
        # Cohen's κ trên các cặp pool có cả 2 nhãn
        a_lab, g_lab = [], []
        for item in data:
            if item.get("source_doc") == "none":
                continue
            for u in pool_by_q[item["id"]]:
                key = f"{item['id']}::{u}"
                if key in verdicts:
                    a_lab.append(1 if u in rel_auto[item["id"]] else 0)
                    g_lab.append(1 if verdicts[key] else 0)
        if a_lab:
            agreement = {
                "kappa": metrics.cohen_kappa(a_lab, g_lab),
                "n_pairs": len(a_lab),
                "raw_agreement": sum(
                    1 for x, y in zip(a_lab, g_lab, strict=True) if x == y
                )
                / len(a_lab),
                "auto_pos_rate": sum(a_lab) / len(a_lab),
                "gemini_pos_rate": sum(g_lab) / len(g_lab),
                "judge_model": settings.openai_chat_model,
            }

    # ---- sweep dưới 2 nguồn nhãn ----
    all_ids = [it["id"] for it in data]
    overall_auto = sweep_group(ranked, rel_auto, all_ids)
    favors_g, cat_g = {}, {}
    for it in data:
        favors_g.setdefault(it.get("favors", "?"), []).append(it["id"])
        cat_g.setdefault(it.get("category", "?"), []).append(it["id"])
    by_favors = {f: sweep_group(ranked, rel_auto, qs) for f, qs in favors_g.items()}
    by_category = {c: sweep_group(ranked, rel_auto, qs) for c, qs in cat_g.items()}

    alpha_star = pick_alpha(overall_auto)
    topk_star = saturation_topk(overall_auto, alpha_star)

    overall_gem = sweep_group(ranked, rel_gem, all_ids) if rel_gem else {}
    alpha_star_gem = pick_alpha(overall_gem) if overall_gem else None

    # ---- tầng rerank (Cohere) tại alpha* ----
    rerank, n_star = {}, settings.rerank_top_n
    try:
        from llama_index.postprocessor.cohere_rerank import CohereRerank

        reranker = CohereRerank(
            api_key=settings.cohere_api_key,
            model=settings.rerank_model,
            top_n=RERANK_EVAL_N,
        )
        with weaviate_client() as client:
            index = build_index(client)
            rbq = []
            for i, qid in enumerate(auto_answerable, start=1):
                item = next(it for it in data if it["id"] == qid)
                nodes = retrieve(index, item["question"], alpha_star, MAX_K)
                for attempt in range(1, 6):
                    try:
                        time.sleep(RERANK_SLEEP)  # tôn trọng Cohere Trial 10/phút
                        reranked = reranker.postprocess_nodes(
                            nodes, query_str=item["question"]
                        )
                        break
                    except Exception as exc:  # noqa: BLE001 — 429 → chờ rồi thử lại
                        print(f"  rerank retry {attempt}/{5} ({type(exc).__name__})")
                        time.sleep(20 * attempt)
                else:
                    raise RuntimeError(f"Rerank thất bại: {qid}")
                uuids = [str(n.node.node_id) for n in reranked]
                rels = [1 if u in rel_auto[qid] else 0 for u in uuids]
                rbq.append((rels, len(rel_auto[qid])))
                if i % 10 == 0:
                    print(f"  rerank {i}/{len(auto_answerable)}")
            for n in range(1, RERANK_EVAL_N + 1):
                m = _agg(rbq, n)
                m["mrr"] = metrics.mean_ignore_nan(
                    [metrics.reciprocal_rank(r) for r, _ in rbq]
                )
                rerank[str(n)] = m
        n_star = max(range(1, RERANK_EVAL_N + 1), key=lambda n: rerank[str(n)]["f1"])
    except Exception as exc:  # noqa: BLE001
        print(f"  (bỏ qua rerank: {type(exc).__name__}: {exc})")

    # ---- ghi kết quả ----
    result = {
        "config": {
            "alpha_grid": ALPHA_GRID,
            "k_grid": K_GRID,
            "max_k": MAX_K,
            "k_select": K_SELECT,
            "pool_k": POOL_K,
            "overlap_threshold": OVERLAP_TH,
            "rare_df": RARE_DF,
            "n_questions": len(data),
            "n_auto_answerable": len(auto_answerable),
            "n_negative": len(negatives),
            "auto_unlabeled": auto_zero,
            "corpus_chunks": len(corpus),
            "current_config": {
                "hybrid_alpha": settings.hybrid_alpha,
                "retrieval_top_k": settings.retrieval_top_k,
                "rerank_top_n": settings.rerank_top_n,
            },
        },
        "relevant_counts_auto": {q: len(s) for q, s in rel_auto.items()},
        "overall": overall_auto,
        "by_favors": by_favors,
        "by_category": by_category,
        "overall_gemini": overall_gem,
        "rerank": rerank,
        "agreement": agreement,
        "selection": {
            "alpha_star": alpha_star,
            "alpha_star_gemini": alpha_star_gem,
            "retrieval_top_k_star": topk_star,
            "rerank_top_n_star": n_star,
            "recall_at_select": overall_auto[_akey(alpha_star)][str(K_SELECT)][
                "recall"
            ],
            "recall_at_maxk": overall_auto[_akey(alpha_star)][str(MAX_K)]["recall"],
        },
    }
    _RESULTS.mkdir(parents=True, exist_ok=True)
    (_RESULTS / "retrieval_sweep.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_report(result)
    _print_summary(result)
    print(f"\nĐã ghi: {_RESULTS / 'retrieval_sweep.json'} và retrieval_report.md")


def _print_summary(result: dict) -> None:
    sel, cfg = result["selection"], result["config"]
    print("\n================ TÓM TẮT (nhãn tự động) ================")
    print("alpha | R@5   R@10  R@20  P@5   P@10  F1@10 nDCG@10 MRR")
    for a in cfg["alpha_grid"]:
        o = result["overall"][f"{a:.1f}"]
        mark = " *" if abs(a - sel["alpha_star"]) < 1e-9 else "  "
        print(
            f"{a:.1f}{mark}| {o['5']['recall']:.3f} {o['10']['recall']:.3f} {o['20']['recall']:.3f} "
            f"{o['5']['precision']:.3f} {o['10']['precision']:.3f} {o['10']['f1']:.3f} "
            f"{o['10']['ndcg']:.3f}  {o['mrr']:.3f}"
        )
    print(
        f"\n→ alpha* = {sel['alpha_star']} | retrieval_top_k* = {sel['retrieval_top_k_star']} "
        f"| rerank_top_n* = {sel['rerank_top_n_star']}"
    )
    cc = cfg["current_config"]
    print(
        f"  config hiện tại: alpha={cc['hybrid_alpha']}, top_k={cc['retrieval_top_k']}, top_n={cc['rerank_top_n']}"
    )
    if sel["alpha_star_gemini"] is not None:
        print(
            f"  alpha* theo nhãn LLM-judge = {sel['alpha_star_gemini']} (kiểm tính bền)"
        )
    if result["agreement"]:
        a = result["agreement"]
        print(
            f"  Cohen's κ (auto vs LLM-judge {a['judge_model']}) = {a['kappa']:.3f} "
            f"trên {a['n_pairs']} cặp (đồng ý {a['raw_agreement']:.1%})"
        )


def _write_report(result: dict) -> None:
    cfg, sel = result["config"], result["selection"]
    lines = [
        "# Báo cáo đánh giá & tối ưu Hybrid Retrieval",
        "",
        f"- Dataset: **{cfg['n_questions']}** câu ({cfg['n_auto_answerable']} answerable theo nhãn tự "
        f"động, {cfg['n_negative']} negative) · Corpus **{cfg['corpus_chunks']}** chunk",
        f"- Nhãn tự động: trigram-recall ≥ {cfg['overlap_threshold']} HOẶC đủ keyword hiếm (df ≤ {cfg['rare_df']})",
        f"- Câu nhãn tự động không gán được (multi-hop/cross-doc, báo riêng): {cfg['auto_unlabeled']}",
        f"- Lưới alpha {cfg['alpha_grid']} · MAX_K={cfg['max_k']} · k chọn alpha = {cfg['k_select']}",
        "",
        "## Tham số tối ưu",
        "",
        f"- **alpha\\*** = `{sel['alpha_star']}` (config hiện tại `{cfg['current_config']['hybrid_alpha']}`)",
        f"- **retrieval_top_k\\*** = `{sel['retrieval_top_k_star']}` (bão hòa Recall; config `{cfg['current_config']['retrieval_top_k']}`)",
        f"- **rerank_top_n\\*** = `{sel['rerank_top_n_star']}` (config `{cfg['current_config']['rerank_top_n']}`)",
    ]
    if sel["alpha_star_gemini"] is not None:
        lines.append(
            f"- **alpha\\* theo nhãn LLM-judge** = `{sel['alpha_star_gemini']}` → kiểm tính bền của lựa chọn"
        )
    if result["agreement"]:
        a = result["agreement"]
        lines.append(
            f"- **Cohen's κ** (auto vs LLM-judge `{a['judge_model']}`) = `{a['kappa']:.3f}` "
            f"trên {a['n_pairs']} cặp (đồng ý {a['raw_agreement']:.1%})"
        )
    lines += [
        "",
        "## Quét alpha — nhãn tự động (câu answerable)",
        "",
        "| alpha | R@5 | R@10 | R@20 | R@30 | P@5 | P@10 | F1@10 | nDCG@10 | MRR |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for a in cfg["alpha_grid"]:
        o = result["overall"][f"{a:.1f}"]
        star = " **\\***" if abs(a - sel["alpha_star"]) < 1e-9 else ""
        lines.append(
            f"| {a:.1f}{star} | {o['5']['recall']:.3f} | {o['10']['recall']:.3f} | {o['20']['recall']:.3f} | "
            f"{o['30']['recall']:.3f} | {o['5']['precision']:.3f} | {o['10']['precision']:.3f} | "
            f"{o['10']['f1']:.3f} | {o['10']['ndcg']:.3f} | {o['mrr']:.3f} |"
        )
    if result["overall_gemini"]:
        lines += [
            "",
            "## Quét alpha — nhãn LLM-judge (đối chứng, pool)",
            "",
            "| alpha | R@5 | R@10 | R@20 | R@30 | MRR |",
            "|---|---|---|---|---|---|",
        ]
        for a in cfg["alpha_grid"]:
            o = result["overall_gemini"][f"{a:.1f}"]
            star = (
                " **\\***"
                if sel["alpha_star_gemini"] is not None
                and abs(a - sel["alpha_star_gemini"]) < 1e-9
                else ""
            )
            lines.append(
                f"| {a:.1f}{star} | {o['5']['recall']:.3f} | {o['10']['recall']:.3f} | "
                f"{o['20']['recall']:.3f} | {o['30']['recall']:.3f} | {o['mrr']:.3f} |"
            )
    lines += [
        "",
        f"## Recall@{cfg['k_select']} theo `favors` (giải thích trade-off alpha) — nhãn tự động",
        "",
        "| favors | " + " | ".join(f"α={a:.1f}" for a in cfg["alpha_grid"]) + " |",
        "|---" * (len(cfg["alpha_grid"]) + 1) + "|",
    ]
    for f, g in result["by_favors"].items():
        row = " | ".join(
            f"{g[f'{a:.1f}'][str(cfg['k_select'])]['recall']:.2f}"
            for a in cfg["alpha_grid"]
        )
        lines.append(f"| {f} (n={g['0.0']['n']}) | {row} |")
    if result["rerank"]:
        lines += [
            "",
            f"## Sau rerank (Cohere) tại alpha*={sel['alpha_star']}",
            "",
            "| n | Precision@n | Recall@n | F1@n | nDCG@n |",
            "|---|---|---|---|---|",
        ]
        for n in sorted(result["rerank"], key=int):
            m = result["rerank"][n]
            lines.append(
                f"| {n} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['ndcg']:.3f} |"
            )
    (_RESULTS / "retrieval_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
