"""Vector store Weaviate Cloud + embedding OpenAI cho RAG.

Client Weaviate v4 là đồng bộ (giữ kết nối gRPC) → mở/đóng theo từng thao tác, gọi
trong thread (``asyncio.to_thread``) ở tầng service để KHÔNG chặn event loop.

Embedding đi qua LlamaIndex ``OpenAIEmbedding`` → được Phoenix trace tự động
(openinference-instrumentation-llama-index), không có đường gọi OpenAI "mù".
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING

import weaviate
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from weaviate.classes.init import Auth

from app.core.config import settings

if TYPE_CHECKING:
    from llama_index.core.schema import BaseNode, NodeWithScore

logger = logging.getLogger(__name__)


def _embed_model() -> OpenAIEmbedding:
    return OpenAIEmbedding(
        model=settings.openai_embed_model,
        api_key=settings.openai_api_key,
    )


@contextlib.contextmanager
def weaviate_client() -> Iterator[weaviate.WeaviateClient]:
    """Mở kết nối Weaviate Cloud và đảm bảo đóng sau khi dùng."""
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=settings.weaviate_url,
        auth_credentials=Auth.api_key(settings.weaviate_api_key),
    )
    try:
        yield client
    finally:
        client.close()


def _vector_store(client: weaviate.WeaviateClient) -> WeaviateVectorStore:
    return WeaviateVectorStore(
        weaviate_client=client,
        index_name=settings.weaviate_collection,
    )


def add_nodes(nodes: list[BaseNode]) -> None:
    """Embed + ghi các node vào Weaviate. Mỗi ``node.node_id`` trở thành UUID đối tượng
    Weaviate (lưu lại ở ``DocumentChunk.weaviate_uuid`` để xoá/truy vết).

    Tạo collection tự động nếu chưa tồn tại (LlamaIndex lo phần schema)."""
    if not nodes:
        return
    with weaviate_client() as client:
        storage_context = StorageContext.from_defaults(
            vector_store=_vector_store(client)
        )
        VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            embed_model=_embed_model(),
        )


def delete_objects(weaviate_uuids: list[str]) -> None:
    """Xoá các đối tượng vector theo UUID (lấy từ DB). Bỏ qua UUID không tồn tại."""
    uuids = [u for u in weaviate_uuids if u]
    if not uuids:
        return
    with weaviate_client() as client:
        if not client.collections.exists(settings.weaviate_collection):
            return
        collection = client.collections.get(settings.weaviate_collection)
        for uuid in uuids:
            with contextlib.suppress(Exception):
                collection.data.delete_by_id(uuid)


def delete_collection() -> None:
    """Xoá toàn bộ collection vector (dùng khi 'xoá tất cả tài liệu').

    Collection dành riêng cho chunk tài liệu → drop cả collection là O(1) và sạch hơn
    xoá từng UUID; LlamaIndex tự tạo lại ở lần ingest kế tiếp."""
    with weaviate_client() as client:
        if client.collections.exists(settings.weaviate_collection):
            client.collections.delete(settings.weaviate_collection)


def retrieve(query_text: str, top_k: int = 3) -> list[NodeWithScore]:
    """Truy hồi top-k chunk gần nhất với câu hỏi (dùng cho retrieval sanity / verify)."""
    with weaviate_client() as client:
        index = VectorStoreIndex.from_vector_store(
            vector_store=_vector_store(client),
            embed_model=_embed_model(),
        )
        return index.as_retriever(similarity_top_k=top_k).retrieve(query_text)
