"""Nhãn relevance TỰ ĐỘNG (chuẩn chính) — xác định, tái lập, không mạng/LLM.

Một chunk LIÊN QUAN tới câu hỏi nếu nó chứa bằng chứng của đáp án vàng. Hai tín hiệu (trên văn bản
đã chuẩn hóa: NFC → bỏ dấu → lowercase → gộp khoảng trắng, GIỮ NGUYÊN token số/mã như "1.893",
"43/2019/qh14"):

1. **Overlap đoạn vàng** (chính): tỉ lệ *trigram từ* của ``reference_context`` xuất hiện trong chunk
   (trigram-recall) ≥ ``overlap_threshold``. Trigram phân biệt tốt hơn bag-of-words → tránh khớp
   tràn lan do từ thông dụng/văn bản gần giống nhau giữa các phường.
2. **Khớp từ khóa HIẾM** (phụ): TẤT CẢ ``expected_keywords`` xuất hiện (khớp ranh giới từ) VÀ có ít
   nhất một keyword "đặc trưng" — hiếm trong corpus (document-frequency ≤ ``rare_df``) khi truyền
   ``keyword_df``, hoặc fallback theo độ đặc thù khi không có df (dùng cho unit-test). Điều kiện df
   chặn keyword chung chung (URL, "xét tuyển", mã đề án dùng nhiều nơi) gây dương tính giả.

Chunk liên quan nếu THỎA (1) HOẶC (2). Negative (không có đáp án) xử lý ở tầng trên (ép R_q=∅).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence


def strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt: đ/Đ → d/D, rồi NFD loại ký tự kết hợp."""
    s = s.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if not unicodedata.combining(c))


def normalize(s: str | None) -> str:
    """NFC → bỏ dấu → lowercase → gộp khoảng trắng → strip. Giữ nguyên token số/mã."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = strip_accents(s).lower()
    return re.sub(r"\s+", " ", s).strip()


def _words(s: str) -> list[str]:
    return [w for w in normalize(s).split(" ") if w]


def trigrams(s: str | None) -> set[tuple[str, ...]]:
    """Tập trigram từ (3-gram). Câu < 3 từ → một tuple chứa toàn bộ từ."""
    w = _words(s or "")
    if len(w) < 3:
        return {tuple(w)} if w else set()
    return {tuple(w[i : i + 3]) for i in range(len(w) - 2)}


def trigram_recall(reference_context: str | None, chunk_text: str | None) -> float:
    """|trigram(ref) ∩ trigram(chunk)| / |trigram(ref)|. 0.0 nếu ref rỗng."""
    ref = trigrams(reference_context)
    if not ref:
        return 0.0
    return len(ref & trigrams(chunk_text)) / len(ref)


def keyword_present(keyword_norm: str, chunk_norm: str) -> bool:
    """Khớp keyword theo RANH GIỚI TỪ (để "8" không khớp trong "1.893"/"458")."""
    if not keyword_norm:
        return False
    return bool(
        re.search(r"(?<![a-z0-9])" + re.escape(keyword_norm) + r"(?![a-z0-9])", chunk_norm)
    )


def _is_specific(keyword_norm: str) -> bool:
    """Fallback (không có df): keyword đặc thù nếu dài ≥ 3, có chữ cái, hoặc có dấu phân tách."""
    return (
        len(keyword_norm) >= 3
        or bool(re.search(r"[a-z]", keyword_norm))
        or bool(re.search(r"[^a-z0-9]", keyword_norm))
    )


def _keyword_hit(
    expected_keywords: Sequence[str],
    chunk_norm: str,
    keyword_df: Mapping[str, int] | None,
    rare_df: int,
) -> bool:
    ks = [normalize(k) for k in expected_keywords if normalize(k)]
    if not ks or not all(keyword_present(k, chunk_norm) for k in ks):
        return False
    if keyword_df is not None:
        return any(keyword_df.get(k, 10**9) <= rare_df for k in ks)
    return any(_is_specific(k) for k in ks)


def is_relevant(
    chunk_text: str | None,
    reference_context: str | None,
    expected_keywords: Sequence[str] | None,
    *,
    overlap_threshold: float = 0.5,
    keyword_df: Mapping[str, int] | None = None,
    rare_df: int = 3,
) -> bool:
    """Nhãn liên quan nhị phân: trigram-recall ≥ θ HOẶC khớp đủ keyword hiếm."""
    if trigram_recall(reference_context, chunk_text) >= overlap_threshold:
        return True
    if expected_keywords:
        return _keyword_hit(
            expected_keywords, normalize(chunk_text), keyword_df, rare_df
        )
    return False
