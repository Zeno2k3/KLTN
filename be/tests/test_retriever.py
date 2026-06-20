"""Test hybrid retriever: ÉP đúng RRF (rankedFusion) + alpha 60/40 + query_properties.

Không gọi Weaviate/OpenAI thật — mock VectorStoreIndex + client để ghi lại tham số as_retriever."""

import contextlib

from llama_index.core.vector_stores.types import VectorStoreQueryMode
from weaviate.classes.query import HybridFusion

from app.rag import retriever


class _FakeRetriever:
    def __init__(self, recorder):
        self._recorder = recorder

    def retrieve(self, query):
        self._recorder["query"] = query
        return ["node-a", "node-b"]


class _FakeIndex:
    def __init__(self, recorder):
        self._recorder = recorder

    def as_retriever(self, **kwargs):
        self._recorder.update(kwargs)
        return _FakeRetriever(self._recorder)


def test_hybrid_retrieve_forces_rrf_and_weighting(monkeypatch):
    recorder: dict = {}

    @contextlib.contextmanager
    def fake_client():
        yield object()

    class _FakeVSIndex:
        @staticmethod
        def from_vector_store(vector_store, embed_model):
            return _FakeIndex(recorder)

    monkeypatch.setattr(retriever, "weaviate_client", fake_client)
    monkeypatch.setattr(retriever, "_vector_store", lambda client: object())
    monkeypatch.setattr(retriever, "_embed_model", lambda: object())
    monkeypatch.setattr(retriever, "VectorStoreIndex", _FakeVSIndex)

    out = retriever.hybrid_retrieve("trường tuyển sinh lớp 1", top_k=30)

    assert out == ["node-a", "node-b"]
    assert recorder["query"] == "trường tuyển sinh lớp 1"
    # Hybrid + ưu tiên 60% semantic / 40% keyword.
    assert recorder["vector_store_query_mode"] == VectorStoreQueryMode.HYBRID
    assert recorder["alpha"] == 0.6
    assert recorder["similarity_top_k"] == 30
    # RRF (rankedFusion) + BM25 chỉ chấm trên property text.
    vsk = recorder["vector_store_kwargs"]
    assert vsk["fusion_type"] == HybridFusion.RANKED
    assert vsk["query_properties"] == ["text"]


def test_hybrid_retrieve_defaults_top_k_from_settings(monkeypatch):
    recorder: dict = {}

    @contextlib.contextmanager
    def fake_client():
        yield object()

    class _FakeVSIndex:
        @staticmethod
        def from_vector_store(vector_store, embed_model):
            return _FakeIndex(recorder)

    monkeypatch.setattr(retriever, "weaviate_client", fake_client)
    monkeypatch.setattr(retriever, "_vector_store", lambda client: object())
    monkeypatch.setattr(retriever, "_embed_model", lambda: object())
    monkeypatch.setattr(retriever, "VectorStoreIndex", _FakeVSIndex)
    monkeypatch.setattr(retriever.settings, "retrieval_top_k", 25)

    retriever.hybrid_retrieve("câu hỏi")
    assert recorder["similarity_top_k"] == 25
