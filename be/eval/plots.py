"""Sinh biểu đồ matplotlib từ kết quả sweep (eval/results/retrieval_sweep.json).

Tạo PNG vào eval/results/figs/:
  1. heatmap_recall.png      — Recall@k theo alpha × k (nhìn vùng tham số tốt nhất)
  2. alpha_curves.png        — Recall/Precision/F1 vs alpha tại k chọn (tìm alpha*)
  3. recall_saturation.png   — Recall@k vs k tại alpha* (điểm bão hòa → retrieval_top_k*)
  4. favors_breakdown.png    — Recall vs alpha tách theo favors (giải thích trade-off)
  5. rerank_curve.png        — Precision/Recall/F1/nDCG @n sau rerank (chọn rerank_top_n*)
  6. agreement.png           — Cohen's κ + tỉ lệ đồng ý auto vs Gemini

Chạy: PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

_RESULTS = Path(__file__).parent / "results"
_FIGS = _RESULTS / "figs"
plt.rcParams["font.family"] = "DejaVu Sans"  # hỗ trợ dấu tiếng Việt


def _load() -> dict:
    return json.loads((_RESULTS / "retrieval_sweep.json").read_text(encoding="utf-8"))


def _alphas(cfg: dict) -> list[float]:
    return cfg["alpha_grid"]


def heatmap_recall(res: dict) -> None:
    cfg = res["config"]
    alphas, ks = _alphas(cfg), cfg["k_grid"]
    grid = [[res["overall"][f"{a:.1f}"][str(k)]["recall"] for k in ks] for a in alphas]
    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(grid, aspect="auto", cmap="viridis", origin="lower")
    ax.set_xticks(range(len(ks)), [str(k) for k in ks])
    ax.set_yticks(range(len(alphas)), [f"{a:.1f}" for a in alphas])
    ax.set_xlabel("top_k")
    ax.set_ylabel("alpha (1.0 = thuần vector, 0.0 = thuần keyword)")
    ax.set_title("Recall@k theo alpha × top_k (nhãn tự động)")
    for i in range(len(alphas)):
        for j in range(len(ks)):
            ax.text(j, i, f"{grid[i][j]:.2f}", ha="center", va="center",
                    color="white" if grid[i][j] < 0.6 else "black", fontsize=7)
    fig.colorbar(im, ax=ax, label="Recall")
    a_star = res["selection"]["alpha_star"]
    ax.axhline(alphas.index(a_star), color="red", lw=1.2, ls="--")
    fig.tight_layout()
    fig.savefig(_FIGS / "heatmap_recall.png", dpi=130)
    plt.close(fig)


def alpha_curves(res: dict) -> None:
    cfg = res["config"]
    alphas = _alphas(cfg)
    ksel = str(cfg["k_select"])
    rec = [res["overall"][f"{a:.1f}"][ksel]["recall"] for a in alphas]
    prec = [res["overall"][f"{a:.1f}"][ksel]["precision"] for a in alphas]
    f1 = [res["overall"][f"{a:.1f}"][ksel]["f1"] for a in alphas]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(alphas, rec, "o-", label=f"Recall@{cfg['k_select']}")
    ax.plot(alphas, prec, "s-", label=f"Precision@{cfg['k_select']}")
    ax.plot(alphas, f1, "^-", label=f"F1@{cfg['k_select']}")
    a_star = res["selection"]["alpha_star"]
    ax.axvline(a_star, color="green", ls="--", lw=1.5, label=f"alpha* = {a_star}")
    ax.axvline(cfg["current_config"]["hybrid_alpha"], color="gray", ls=":", lw=1.5,
               label=f"alpha hiện tại = {cfg['current_config']['hybrid_alpha']}")
    ax.set_xlabel("alpha")
    ax.set_ylabel("giá trị metric")
    ax.set_title(f"Recall / Precision / F1 @ top_k={cfg['k_select']} theo alpha")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(_FIGS / "alpha_curves.png", dpi=130)
    plt.close(fig)


def recall_saturation(res: dict) -> None:
    cfg = res["config"]
    ks = cfg["k_grid"]
    a_star = res["selection"]["alpha_star"]
    topk = res["selection"]["retrieval_top_k_star"]
    rec = [res["overall"][f"{a_star:.1f}"][str(k)]["recall"] for k in ks]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(ks, rec, "o-", color="tab:blue")
    ax.axvline(topk, color="red", ls="--", lw=1.5, label=f"retrieval_top_k* = {topk}")
    ax.axvline(cfg["current_config"]["retrieval_top_k"], color="gray", ls=":",
               label=f"top_k hiện tại = {cfg['current_config']['retrieval_top_k']}")
    ax.set_xlabel("top_k")
    ax.set_ylabel("Recall@k")
    ax.set_title(f"Đường bão hòa Recall@k tại alpha* = {a_star}")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(_FIGS / "recall_saturation.png", dpi=130)
    plt.close(fig)


def favors_breakdown(res: dict) -> None:
    cfg = res["config"]
    alphas = _alphas(cfg)
    ksel = str(cfg["k_select"])
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for fav, g in res["by_favors"].items():
        n = g["0.0"]["n"]
        ys = [g[f"{a:.1f}"][ksel]["recall"] for a in alphas]
        ax.plot(alphas, ys, "o-", label=f"{fav} (n={n})")
    a_star = res["selection"]["alpha_star"]
    ax.axvline(a_star, color="green", ls="--", lw=1.2, label=f"alpha* = {a_star}")
    ax.set_xlabel("alpha")
    ax.set_ylabel(f"Recall@{cfg['k_select']}")
    ax.set_title("Recall theo alpha tách theo nhóm favors (sparse/dense/both)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(_FIGS / "favors_breakdown.png", dpi=130)
    plt.close(fig)


def rerank_curve(res: dict) -> None:
    if not res.get("rerank"):
        return
    ns = sorted(res["rerank"], key=int)
    x = [int(n) for n in ns]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for key, mark in [("precision", "s-"), ("recall", "o-"), ("f1", "^-"), ("ndcg", "d-")]:
        ax.plot(x, [res["rerank"][n][key] for n in ns], mark, label=f"{key}@n")
    n_star = res["selection"]["rerank_top_n_star"]
    ax.axvline(n_star, color="green", ls="--", lw=1.5, label=f"rerank_top_n* = {n_star}")
    ax.axvline(res["config"]["current_config"]["rerank_top_n"], color="gray", ls=":",
               label=f"top_n hiện tại = {res['config']['current_config']['rerank_top_n']}")
    ax.set_xlabel("n (số chunk sau rerank)")
    ax.set_ylabel("giá trị metric")
    ax.set_title(f"Metric @n sau rerank Cohere (alpha* = {res['selection']['alpha_star']})")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(_FIGS / "rerank_curve.png", dpi=130)
    plt.close(fig)


def agreement_chart(res: dict) -> None:
    a = res.get("agreement")
    if not a:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["Cohen's κ", "Đồng ý thô", "Tỉ lệ + (auto)", "Tỉ lệ + (LLM)"]
    vals = [a["kappa"], a["raw_agreement"], a["auto_pos_rate"], a["gemini_pos_rate"]]
    bars = ax.bar(labels, vals, color=["tab:green", "tab:blue", "tab:orange", "tab:purple"])
    for b, v in zip(bars, vals, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}", ha="center", fontsize=10)
    ax.set_ylim(min(0, min(vals)) - 0.05, 1.05)
    ax.set_title(f"Đối chứng nhãn tự động vs LLM-judge ({a['judge_model']}, {a['n_pairs']} cặp)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(_FIGS / "agreement.png", dpi=130)
    plt.close(fig)


def main() -> None:
    _FIGS.mkdir(parents=True, exist_ok=True)
    res = _load()
    heatmap_recall(res)
    alpha_curves(res)
    recall_saturation(res)
    favors_breakdown(res)
    rerank_curve(res)
    agreement_chart(res)
    print(f"Đã ghi PNG vào {_FIGS}:")
    for p in sorted(_FIGS.glob("*.png")):
        print("  ", p.name)


if __name__ == "__main__":
    main()
