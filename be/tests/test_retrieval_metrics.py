"""Test cho harness eval retrieval: metric IR, nhãn tự động relevance, và alpha override.

Toàn bộ THUẦN/không mạng (alpha override dùng mock) → chạy nhanh trong suite. Bao phủ đường code mới
ở eval/metrics.py, eval/relevance.py và tham số ``alpha`` mới của app/rag/retriever.py.
"""

from __future__ import annotations

import contextlib
import math
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import metrics, relevance  # noqa: E402

RELS = [0, 1, 0, 1, 1]  # liên quan ở hạng 2,4,5; total_relevant = 3


# ------------------------------------------------------------------ metrics
def test_precision_recall_hit():
    assert metrics.precision_at_k(RELS, 2) == pytest.approx(0.5)
    assert metrics.precision_at_k(RELS, 5) == pytest.approx(0.6)
    assert metrics.recall_at_k(RELS, 3, 2) == pytest.approx(1 / 3)
    assert metrics.recall_at_k(RELS, 3, 5) == pytest.approx(1.0)
    assert metrics.hit_at_k(RELS, 1) == 0.0
    assert metrics.hit_at_k(RELS, 2) == 1.0


def test_recall_undefined_when_no_relevant():
    assert math.isnan(metrics.recall_at_k(RELS, 0, 5))
    assert math.isnan(metrics.ndcg_at_k(RELS, 0, 5))


def test_f1_and_mrr():
    # tại k=5: p=0.6, r=1.0 → f1 = 2*0.6*1/(1.6) = 0.75
    assert metrics.f1_at_k(RELS, 3, 5) == pytest.approx(0.75)
    assert metrics.reciprocal_rank(RELS) == pytest.approx(0.5)  # liên quan đầu ở hạng 2
    assert metrics.reciprocal_rank([0, 0, 0]) == 0.0


def test_ndcg_known_value():
    # DCG@5 = 1/log2(3)+1/log2(5)+1/log2(6); IDCG@5 = 1/log2(2)+1/log2(3)+1/log2(4)
    dcg = 1 / math.log2(3) + 1 / math.log2(5) + 1 / math.log2(6)
    idcg = 1 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
    assert metrics.ndcg_at_k(RELS, 3, 5) == pytest.approx(dcg / idcg)
    # xếp hạng lý tưởng → nDCG = 1.0
    assert metrics.ndcg_at_k([1, 1, 1, 0, 0], 3, 5) == pytest.approx(1.0)


def test_mean_ignore_nan():
    assert metrics.mean_ignore_nan([1.0, float("nan"), 0.0]) == pytest.approx(0.5)
    assert math.isnan(metrics.mean_ignore_nan([float("nan")]))


def test_cohen_kappa():
    assert metrics.cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == pytest.approx(1.0)  # khớp hoàn toàn
    assert metrics.cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]) == pytest.approx(-1.0)  # nghịch hoàn toàn
    assert metrics.cohen_kappa([1, 1, 1], [1, 1, 1]) == pytest.approx(1.0)  # cạnh: mọi nhãn giống
    with pytest.raises(ValueError):
        metrics.cohen_kappa([1, 0], [1])


# ------------------------------------------------------------------ relevance (nhãn tự động)
def test_relevance_keyword_match():
    chunk = "SĐT đường dây nóng: 0977.977.739, ông Nguyễn Hồng Lâm - Phó Trưởng phòng."
    assert relevance.is_relevant(chunk, "", ["0977.977.739", "Nguyễn Hồng Lâm"])


def test_relevance_accent_insensitive():
    # keyword có dấu, chunk viết thường không dấu vẫn khớp
    assert relevance.is_relevant("can chung chi flyers 12/15 khien", "", ["Flyers", "12/15"])


def test_relevance_overlap_without_keyword():
    ref = "Hệ thống bản đồ số được ứng dụng để xác định chính xác quãng đường đến trường."
    chunk = "Theo kế hoạch tuyển sinh: " + ref + " Ngoài ra còn áp dụng GIS hỗ trợ."
    assert relevance.is_relevant(chunk, ref, [])  # chunk chứa trọn đoạn vàng → trigram-recall cao


def test_relevance_rare_keyword_df_gate():
    # keyword chung chung (df cao) KHÔNG kích hoạt; keyword hiếm (df thấp) thì có
    chunk = "Đăng ký tại https://tuyensinhdaucap.hcm.edu.vn theo phương thức xét tuyển."
    common = relevance.is_relevant(
        chunk, "", ["xét tuyển"], keyword_df={"xet tuyen": 25}, rare_df=3
    )
    rare = relevance.is_relevant(
        chunk,
        "",
        ["tuyensinhdaucap.hcm.edu.vn"],
        keyword_df={"tuyensinhdaucap.hcm.edu.vn": 2},
        rare_df=3,
    )
    assert not common and rare


def test_relevance_negative_no_match():
    chunk = "Học phí mỗi tháng của trường công lập chưa được nêu trong tài liệu."
    assert not relevance.is_relevant(chunk, "Đoạn vàng về đường dây nóng An Hội Đông.", ["0977.977.739"])


# ------------------------------------------------------------------ alpha override (mock, không mạng)
def test_hybrid_retrieve_passes_alpha_override(monkeypatch):
    from app.rag import retriever

    captured: dict = {}
    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = []
    fake_index = MagicMock()

    def _as_retriever(**kwargs):
        captured.clear()
        captured.update(kwargs)
        return fake_retriever

    fake_index.as_retriever.side_effect = _as_retriever

    @contextlib.contextmanager
    def _fake_client():
        yield MagicMock()

    monkeypatch.setattr(retriever, "weaviate_client", _fake_client)
    monkeypatch.setattr(retriever, "_vector_store", lambda c: None)
    monkeypatch.setattr(retriever, "_embed_model", lambda: None)
    monkeypatch.setattr(retriever.VectorStoreIndex, "from_vector_store", lambda **k: fake_index)

    retriever.hybrid_retrieve("câu hỏi", top_k=7, alpha=0.25)
    assert captured["alpha"] == 0.25
    assert captured["similarity_top_k"] == 7

    # alpha=None → fallback settings.hybrid_alpha
    retriever.hybrid_retrieve("câu hỏi", top_k=7)
    assert captured["alpha"] == retriever.settings.hybrid_alpha
