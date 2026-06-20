"""Pipeline trả lời RAG: hybrid retrieve → cross-encoder rerank → LLM tổng hợp.

Thứ tự: ``hybrid_retrieve`` (top_k=30, RRF) → ``SentenceTransformerRerank`` (cross-encoder
ViRanker, top_n) → LLM OpenAI soạn câu trả lời CHỈ dựa trên ngữ cảnh đã xếp hạng, kèm trích dẫn.

Reranker nạp model ViRanker (XLM-RoBERTa cross-encoder) qua sentence-transformers ``CrossEncoder``
— chạy LOCAL (giữ PII trên máy). Dùng ``SentenceTransformerRerank`` thay vì FlagEmbedding vì
FlagEmbedding 1.4 không tương thích transformers 5.x (gọi ``tokenizer.prepare_for_model`` đã bị bỏ).

Mọi cuộc gọi embedding/LLM đi qua LlamaIndex → Phoenix trace tự động (không có đường OpenAI "mù").
Toàn bộ flow được bọc trong 1 span ``rag.answer`` để lấy ``trace_id`` đối chiếu.

Hàm đồng bộ (LlamaIndex + model rerank local đều chặn) → tầng service gọi qua ``asyncio.to_thread``.
Reranker được import LƯỜI (lazy) để app vẫn import được khi chưa cài sentence-transformers/torch
(test mock ``_get_reranker``)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.schema import MetadataMode
from llama_index.llms.openai import OpenAI
from opentelemetry import trace

from app.core.config import settings
from app.rag.retriever import hybrid_retrieve

if TYPE_CHECKING:
    from llama_index.core.schema import NodeWithScore

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Bạn là trợ lý tư vấn tuyển sinh tiểu học, hỗ trợ phụ huynh. "
    "CHỈ trả lời dựa trên thông tin trong phần NGỮ CẢNH được cung cấp. "
    "Nếu ngữ cảnh không đủ thông tin, hãy nói rõ là chưa có thông tin và khuyên phụ huynh "
    "liên hệ trực tiếp nhà trường — TUYỆT ĐỐI không bịa đặt, không suy diễn ngoài ngữ cảnh. "
    "Trả lời bằng tiếng Việt, ngắn gọn, dễ hiểu; khi dùng thông tin từ một nguồn hãy trích "
    "dẫn số nguồn dạng [n]. Không tiết lộ thông tin cá nhân của học sinh hay phụ huynh."
)

_NO_CONTEXT_ANSWER = (
    "Xin lỗi, hiện chưa tìm thấy tài liệu phù hợp để trả lời câu hỏi này. "
    "Phụ huynh vui lòng liên hệ trực tiếp nhà trường để được hỗ trợ chính xác."
)

# Singleton (model rerank nặng → khởi tạo 1 lần). Bọc trong hàm để mock/được lazy-import.
_reranker: Any = None
_llm: OpenAI | None = None


@dataclass
class AnswerResult:
    """Kết quả trả lời RAG, sẵn sàng cho persistence (``Message.context_sources``) + API."""

    answer: str
    sources: list[dict] = field(default_factory=list)
    trace_id: str | None = None


def _get_reranker() -> Any:
    """Khởi tạo (lazy) cross-encoder reranker (ViRanker qua sentence-transformers).
    Import trong hàm để app không phụ thuộc cứng vào sentence-transformers/torch lúc import
    (CI/test có thể chưa cài)."""
    global _reranker
    if _reranker is None:
        from llama_index.core.postprocessor import SentenceTransformerRerank

        _reranker = SentenceTransformerRerank(
            model=settings.rerank_model,
            top_n=settings.rerank_top_n,
        )
    return _reranker


def _get_llm() -> OpenAI:
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.openai_chat_model,
            api_key=settings.openai_api_key,
        )
    return _llm


def _build_context(nodes: list[NodeWithScore]) -> tuple[str, list[dict]]:
    """Ráp ngữ cảnh cho prompt + danh sách nguồn trích dẫn.

    Dùng text THUẦN (``MetadataMode.NONE``) để không lẫn metadata (vd ``document_id``) vào
    câu trả lời của LLM."""
    blocks: list[str] = []
    sources: list[dict] = []
    for i, ns in enumerate(nodes, start=1):
        node = ns.node
        text = node.get_content(metadata_mode=MetadataMode.NONE).strip()
        document_id = node.metadata.get("document_id")
        filename = node.metadata.get("filename")
        label = filename or (f"tài liệu #{document_id}" if document_id else "tài liệu")
        blocks.append(f"[{i}] (nguồn: {label})\n{text}")
        sources.append(
            {
                "index": i,
                "document_id": document_id,
                "filename": filename,
                "weaviate_uuid": node.node_id,
                "snippet": text[:500],
                # ép về float thuần: reranker/Weaviate trả np.float32 → JSONB không
                # serialize được (bug chỉ lộ khi chạy thật, không lộ ở mock test).
                "score": float(ns.score) if ns.score is not None else None,
            }
        )
    return "\n\n".join(blocks), sources


def _current_trace_id() -> str | None:
    """Lấy trace id (hex 32) của span hiện tại để đối chiếu Phoenix; None nếu tracing tắt."""
    ctx = trace.get_current_span().get_span_context()
    if ctx and ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return None


def _user_prompt(context: str, query_text: str) -> str:
    return (
        f"NGỮ CẢNH:\n{context}\n\n"
        f"CÂU HỎI: {query_text}\n\n"
        "Hãy trả lời dựa trên ngữ cảnh trên."
    )


def retrieve_and_rerank(query_text: str, filters: Any = None) -> list[NodeWithScore]:
    """Hybrid retrieve (top_k=30, RRF) rồi cross-encoder rerank xuống top_n. [] nếu rỗng."""
    candidates = hybrid_retrieve(query_text, settings.retrieval_top_k, filters)
    if not candidates:
        return []
    return _get_reranker().postprocess_nodes(candidates, query_str=query_text)


def synthesize(
    query_text: str, reranked: list[NodeWithScore]
) -> tuple[str, list[dict]]:
    """LLM soạn câu trả lời từ các chunk đã xếp hạng; trả (answer, sources trích dẫn)."""
    context, sources = _build_context(reranked)
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
        ChatMessage(role=MessageRole.USER, content=_user_prompt(context, query_text)),
    ]
    response = _get_llm().chat(messages)
    return (response.message.content or "").strip(), sources


def answer_question(query_text: str, filters: Any = None) -> AnswerResult:
    """Trả lời 1 câu hỏi: hybrid retrieve → rerank → LLM tổng hợp (đồng bộ, chặn).

    ``filters`` là ``MetadataFilters`` LlamaIndex (tuỳ chọn) để thu hẹp truy hồi."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.answer") as span:
        span.set_attribute("rag.query", query_text)
        trace_id = _current_trace_id()

        reranked = retrieve_and_rerank(query_text, filters)
        span.set_attribute("rag.reranked", len(reranked))
        if not reranked:
            return AnswerResult(answer=_NO_CONTEXT_ANSWER, sources=[], trace_id=trace_id)

        answer, sources = synthesize(query_text, reranked)
        return AnswerResult(answer=answer, sources=sources, trace_id=trace_id)
