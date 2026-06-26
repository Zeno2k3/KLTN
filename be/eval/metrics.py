"""Các metric truy hồi (IR) THUẦN — không mạng, không phụ thuộc nặng → unit-test được.

Đầu vào chuẩn của hầu hết hàm: ``rels`` = danh sách nhãn liên quan 0/1 THEO THỨ TỰ HẠNG (rank) của
kết quả truy hồi (rels[0] là kết quả hạng 1). ``total_relevant`` = tổng số chunk liên quan của câu
hỏi trong toàn corpus (mẫu số cho Recall). Trả ``float('nan')`` khi không xác định (vd Recall khi
câu không có chunk liên quan) để bên gọi tự lọc bằng ``math.isnan``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def precision_at_k(rels: Sequence[int], k: int) -> float:
    """Precision@k = (số liên quan trong top-k) / k."""
    if k <= 0:
        return float("nan")
    top = rels[:k]
    return sum(1 for r in top if r) / k


def recall_at_k(rels: Sequence[int], total_relevant: int, k: int) -> float:
    """Recall@k = (số liên quan trong top-k) / tổng số liên quan. NaN nếu không có chunk liên quan."""
    if total_relevant <= 0:
        return float("nan")
    hit = sum(1 for r in rels[:k] if r)
    return hit / total_relevant


def f1_at_k(rels: Sequence[int], total_relevant: int, k: int) -> float:
    """F1@k = trung bình điều hòa của Precision@k và Recall@k. NaN nếu Recall không xác định."""
    p = precision_at_k(rels, k)
    r = recall_at_k(rels, total_relevant, k)
    if math.isnan(p) or math.isnan(r) or (p + r) == 0:
        return 0.0 if not math.isnan(r) else float("nan")
    return 2 * p * r / (p + r)


def hit_at_k(rels: Sequence[int], k: int) -> float:
    """Hit@k = 1.0 nếu có ít nhất một kết quả liên quan trong top-k, ngược lại 0.0."""
    return 1.0 if any(rels[:k]) else 0.0


def reciprocal_rank(rels: Sequence[int]) -> float:
    """1/(hạng của kết quả liên quan ĐẦU TIÊN); 0.0 nếu không có liên quan nào (dùng cho MRR)."""
    for i, r in enumerate(rels, start=1):
        if r:
            return 1.0 / i
    return 0.0


def dcg_at_k(rels: Sequence[int], k: int) -> float:
    """DCG@k với gain nhị phân: sum rel_i / log2(i+1) (i tính từ 1)."""
    return sum((1.0 / math.log2(i + 1)) for i, r in enumerate(rels[:k], start=1) if r)


def ndcg_at_k(rels: Sequence[int], total_relevant: int, k: int) -> float:
    """nDCG@k = DCG@k / IDCG@k; IDCG là xếp hạng lý tưởng (mọi liên quan dồn lên đầu).

    NaN nếu câu không có chunk liên quan (IDCG = 0)."""
    if total_relevant <= 0:
        return float("nan")
    ideal_hits = min(total_relevant, k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    if idcg == 0:
        return float("nan")
    return dcg_at_k(rels, k) / idcg


def mean_ignore_nan(values: Sequence[float]) -> float:
    """Trung bình bỏ qua NaN; NaN nếu rỗng sau khi lọc."""
    xs = [v for v in values if not math.isnan(v)]
    return sum(xs) / len(xs) if xs else float("nan")


def cohen_kappa(a: Sequence[int], b: Sequence[int]) -> float:
    """Hệ số đồng thuận Cohen's κ giữa hai bộ nhãn nhị phân (0/1) cùng độ dài.

    κ = (p_o - p_e) / (1 - p_e); p_o = tỉ lệ đồng ý quan sát, p_e = đồng ý kỳ vọng ngẫu nhiên.
    Trả 1.0 khi hai bộ giống hệt; xử lý cạnh khi mọi nhãn giống nhau (p_e = 1) → trả 1.0 nếu khớp
    hoàn toàn, ngược lại 0.0.
    """
    if len(a) != len(b):
        raise ValueError("hai bộ nhãn phải cùng độ dài")
    n = len(a)
    if n == 0:
        return float("nan")
    agree = sum(1 for x, y in zip(a, b, strict=True) if x == y)
    p_o = agree / n
    pa1 = sum(1 for x in a if x) / n
    pb1 = sum(1 for x in b if x) / n
    p_e = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if p_e >= 1.0:
        return 1.0 if p_o >= 1.0 else 0.0
    return (p_o - p_e) / (1 - p_e)
