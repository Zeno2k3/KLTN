"""SynthesisAgent (phần gộp đa nguồn): hợp nhất node từ NHIỀU sub-query, khử trùng trước synthesize.

Pipeline tuyến tính chỉ có một danh sách node. Đường đa tác tử gom node từ N Retrieval agent → phải
KHỬ TRÙNG (cùng chunk có thể trúng nhiều sub-query) theo ``node_id``, ưu tiên điểm rerank cao, rồi
cắt trần để ngữ cảnh không phình. Việc SOẠN câu trả lời vẫn dùng lại ``query_engine.synthesize``
(prompt + _build_context gốc) — module này chỉ lo bước MERGE."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.schema import NodeWithScore

# Trần số node sau khi gộp đa nguồn (đầu vào LLM synthesize). Đủ rộng cho câu đa phường/đa ý nhưng
# vẫn chặn prompt quá to. Mỗi sub-query vốn đã rerank xuống rerank_top_n (mặc định 6).
_MAX_MERGED_NODES = 10


def merge_nodes(node_lists: list[list[NodeWithScore]]) -> list[NodeWithScore]:
    """Gộp các danh sách node, khử trùng theo ``node_id``, sắp theo score giảm dần, cắt trần.

    Giữ lần XUẤT HIỆN ĐẦU của mỗi node_id (đã là bản có score khi trúng sub-query đầu); sau đó sắp
    toàn bộ theo score để các đoạn liên quan nhất lên đầu ngữ cảnh."""
    seen: set[str] = set()
    merged: list[NodeWithScore] = []
    for nodes in node_lists:
        for ns in nodes or []:
            node_id = ns.node.node_id
            if node_id in seen:
                continue
            seen.add(node_id)
            merged.append(ns)
    merged.sort(key=lambda ns: ns.score if ns.score is not None else 0.0, reverse=True)
    return merged[:_MAX_MERGED_NODES]
