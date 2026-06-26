"""RetrievalAgent: retrieve cho MỘT sub-query, tự chấm đủ/thiếu rồi retrieve lại (vòng lặp).

Đây là năng lực "tự chủ" mà pipeline tuyến tính (một lượt, không lặp) không có:
  1. Trích filter từ sub-query (TÁI DÙNG ``query_filters.extract_filters``) → ``retrieve_and_rerank``
     (TÁI DÙNG). Rỗng + có filter → retry KHÔNG filter (cùng fallback như ``answer_question``).
  2. SELF-GRADE: LLM chấm "ngữ cảnh đã đủ trả lời sub-query chưa?". Thiếu & còn lượt → tự viết lại
     truy vấn (``refined_query``) và retrieve lại, tối đa ``retrieval_max_rounds`` vòng.

Fail-safe: grader lỗi → coi như đủ (dừng lặp), không chặn. LLM grader RIÊNG (``retrieval_grader_model``
→ fallback chat model). Gọi qua LlamaIndex → Phoenix auto-trace."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI

from app.core.config import settings
from app.rag import query_filters
from app.rag.agents._jsonio import extract_json_object
from app.rag.query_engine import _build_context, retrieve_and_rerank

if TYPE_CHECKING:
    from llama_index.core.schema import NodeWithScore

logger = logging.getLogger(__name__)

_GRADER_SYSTEM_PROMPT = """\
Bạn là bộ CHẤM ĐỘ ĐỦ NGỮ CẢNH cho trợ lý tuyển sinh LỚP 1 TIỂU HỌC. Bạn nhận TRUY VẤN và NGỮ CẢNH
(các đoạn tài liệu đã truy hồi). Đánh giá: ngữ cảnh đã ĐỦ thông tin để trả lời TRUY VẤN chưa?

- ĐỦ (có đoạn chứa thông tin trả lời được) → sufficient=true, refined_query="".
- THIẾU / không liên quan → sufficient=false, và viết refined_query: một truy vấn tìm kiếm KHÁC
  (dùng từ đồng nghĩa, cụ thể hơn, hoặc nêu rõ phường/năm/loại giấy tờ) để tìm tài liệu tốt hơn.
  Giữ tiếng Việt, ngắn gọn.

CHỈ in ra JSON đúng cấu trúc, không giải thích:
{"sufficient": <true|false>, "refined_query": "<chuỗi>"}"""

_llm: OpenAI | None = None


def _get_llm() -> OpenAI:
    """LLM grader riêng (singleton module). Model ``retrieval_grader_model`` (fallback chat model)."""
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.retrieval_grader_model or settings.openai_chat_model,
            api_key=settings.openai_api_key,
        )
    return _llm


def _retrieve_once(query: str) -> list[NodeWithScore]:
    """Một vòng retrieve+rerank với fallback-no-filter (giống ``answer_question``)."""
    filters = (
        query_filters.extract_filters(query) if settings.query_filter_enabled else None
    )
    nodes = retrieve_and_rerank(query, filters)
    if not nodes and filters is not None and settings.filter_fallback_on_empty:
        nodes = retrieve_and_rerank(query, None)
    return nodes


def _grade(subquery: str, nodes: list[NodeWithScore]) -> dict | None:
    """LLM chấm đủ/thiếu → ``{"sufficient", "refined_query"}``. None nếu lỗi (caller coi như đủ)."""
    try:
        context, _ = _build_context(nodes)
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=_GRADER_SYSTEM_PROMPT),
            ChatMessage(
                role=MessageRole.USER,
                content=(
                    f"TRUY VẤN: {subquery}\n\nNGỮ CẢNH:\n{context}\n\n"
                    "Ngữ cảnh đã đủ trả lời TRUY VẤN chưa? Trả JSON."
                ),
            ),
        ]
        response = _get_llm().chat(messages, response_format={"type": "json_object"})
        return json.loads(extract_json_object(response.message.content or ""))
    except Exception:  # noqa: BLE001 — grader không được chặn pipeline
        logger.exception("Retrieval grader lỗi — coi như đủ (dừng lặp).")
        return None


def retrieve_for_subquery(subquery: str) -> tuple[list[NodeWithScore], int]:
    """Retrieve cho sub-query, tự chấm + lặp ≤ ``retrieval_max_rounds``. Trả (nodes, số vòng đã chạy)."""
    max_rounds = max(1, settings.retrieval_max_rounds)
    query = subquery
    nodes: list[NodeWithScore] = []
    rounds = 0

    for r in range(1, max_rounds + 1):
        rounds = r
        nodes = _retrieve_once(query)
        # Vòng cuối / tắt self-grade / không có gì để chấm → dừng.
        if not settings.retrieval_grade_enabled or r == max_rounds or not nodes:
            break
        grade = _grade(subquery, nodes)
        if grade is None or grade.get("sufficient", True):
            break
        refined = (grade.get("refined_query") or "").strip()
        if not refined or refined == query:
            break  # không có truy vấn mới → khỏi lặp vô ích
        query = refined

    return nodes, rounds
