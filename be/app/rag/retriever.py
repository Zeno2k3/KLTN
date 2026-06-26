"""Truy hồi hybrid (BM25 keyword + vector semantic) hợp nhất bằng RRF cho RAG.

Weaviate thực hiện cả hai nhánh trong MỘT truy vấn ``hybrid``:
- ``alpha`` cân bằng hai nhánh (0.6 ⇒ ưu tiên 60% semantic / 40% keyword);
- ``fusion_type=RANKED`` ⇒ Reciprocal Rank Fusion (RRF, điểm cộng dồn 1/(rank+60));
- ``MetadataFilters`` (nếu có) được áp cho CẢ hai nhánh trong cùng truy vấn.

LlamaIndex ``WeaviateVectorStore.query()`` luôn gọi ``collection.query.hybrid(**params)`` rồi
merge thêm ``vector_store_kwargs`` → ta đẩy ``fusion_type`` + ``query_properties`` qua đó để ÉP
RRF (Weaviate mặc định ``relativeScoreFusion`` từ v1.24) và chỉ chấm BM25 trên property text
(tránh nhiễu từ ``_node_content``).

Client Weaviate v4 đồng bộ → gọi qua ``asyncio.to_thread`` ở tầng service (không chặn event loop).
Embedding query đi qua LlamaIndex ``OpenAIEmbedding`` → Phoenix trace tự động.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from weaviate.classes.query import HybridFusion

from app.core.config import settings
from app.rag.vector_store import _embed_model, _vector_store, weaviate_client

if TYPE_CHECKING:
    from llama_index.core.schema import NodeWithScore
    from llama_index.core.vector_stores.types import MetadataFilters

logger = logging.getLogger(__name__)


def hybrid_retrieve(
    query_text: str,
    top_k: int | None = None,
    filters: MetadataFilters | None = None,
    alpha: float | None = None,
) -> list[NodeWithScore]:
    """Truy hồi top-k chunk bằng hybrid search + RRF.

    Args:
        query_text: câu hỏi của người dùng.
        top_k: số ứng viên trả về (mặc định ``settings.retrieval_top_k`` = 30).
        filters: ``MetadataFilters`` LlamaIndex; Weaviate áp cho cả nhánh keyword lẫn vector.
        alpha: trọng số hybrid (1.0 thuần vector, 0.0 thuần keyword). ``None`` → dùng
            ``settings.hybrid_alpha``. Cho phép eval quét alpha mà không đổi config toàn cục.

    Trả về danh sách ``NodeWithScore`` đã hợp nhất, điểm là điểm hybrid của Weaviate.
    """
    limit = top_k or settings.retrieval_top_k
    effective_alpha = alpha if alpha is not None else settings.hybrid_alpha
    with weaviate_client() as client:
        index = VectorStoreIndex.from_vector_store(
            vector_store=_vector_store(client),
            embed_model=_embed_model(),
        )
        retriever = index.as_retriever(
            vector_store_query_mode=VectorStoreQueryMode.HYBRID,
            alpha=effective_alpha,
            similarity_top_k=limit,
            filters=filters,
            vector_store_kwargs={
                "fusion_type": HybridFusion.RANKED,
                "query_properties": [settings.weaviate_text_key],
            },
        )
        return retriever.retrieve(query_text)
