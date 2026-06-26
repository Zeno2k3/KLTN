"""PlannerAgent: phân rã câu hỏi phức thành các sub-query ĐỘC LẬP để retrieve riêng.

Bước này KHÔNG có ở pipeline tuyến tính (vốn chỉ một truy vấn). Câu hỏi gộp nhiều ý / nhiều phường /
nhiều năm → tách mỗi cái thành một sub-query tự đủ nghĩa → nhiều Retrieval agent chạy song song.

Trước khi tách: condense câu follow-up theo lịch sử (TÁI DÙNG ``rewrite_query``) để sub-query độc lập
ngữ cảnh hội thoại. Câu đơn → trả về đúng một sub-query (chính câu đã condense). Fail-safe: lỗi LLM
→ trả ``[câu]`` (không chặn pipeline).

LLM RIÊNG (model ``planner_model``, rỗng → fallback ``openai_chat_model``) — theo quy ước per-step,
KHÔNG singleton chung. Gọi qua LlamaIndex → Phoenix auto-trace."""

from __future__ import annotations

import json
import logging

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI

from app.core.config import settings
from app.rag.agents._jsonio import extract_json_object
from app.rag.query_rewriter import rewrite_query

logger = logging.getLogger(__name__)

_PLANNER_SYSTEM_PROMPT = """\
Bạn là bộ LẬP KẾ HOẠCH TRUY VẤN cho trợ lý tư vấn tuyển sinh LỚP 1 TIỂU HỌC. Nhiệm vụ: đọc CÂU HỎI
và tách thành các truy vấn con (sub-query) ĐỘC LẬP để tra cứu tài liệu.

QUY TẮC:
1. Câu hỏi chỉ hỏi MỘT ý đơn → trả về đúng MỘT sub-query là chính câu đó (không bịa thêm).
2. Câu hỏi gộp NHIỀU ý (vd vừa hỏi hồ sơ vừa hỏi độ tuổi), hoặc nhắc NHIỀU phường/xã, hoặc NHIỀU
   năm học → tách mỗi ý / mỗi phường / mỗi năm thành một sub-query riêng.
3. Mỗi sub-query phải TỰ ĐỦ NGHĨA: giữ rõ phường/xã, năm học, "lớp 1" nếu câu gốc có nêu. KHÔNG thêm
   thông tin không có trong câu gốc.
4. Tối đa {max_subqueries} sub-query. Giữ nguyên tiếng Việt, ngắn gọn.

CHỈ in ra JSON đúng cấu trúc, không giải thích, không thêm ký tự nào:
{{"subqueries": ["...", "..."]}}"""

_llm: OpenAI | None = None


def _get_llm() -> OpenAI:
    """LLM riêng của planner (singleton trong module). Model ``planner_model`` (fallback chat model)."""
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.planner_model or settings.openai_chat_model,
            api_key=settings.openai_api_key,
        )
    return _llm


def _decompose(query: str) -> list[str]:
    """Gọi LLM tách ``query`` thành list sub-query (JSON). Raise nếu parse lỗi → caller fail-safe."""
    system = _PLANNER_SYSTEM_PROMPT.format(
        max_subqueries=settings.planner_max_subqueries
    )
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=system),
        ChatMessage(
            role=MessageRole.USER,
            content=f"CÂU HỎI: {query}\n\nTách thành các sub-query (JSON).",
        ),
    ]
    response = _get_llm().chat(messages, response_format={"type": "json_object"})
    data = json.loads(extract_json_object(response.message.content or ""))
    subs = data.get("subqueries")
    if not isinstance(subs, list):
        return [query]
    return [str(s) for s in subs]


def plan(query: str, history: list[dict] | None = None) -> list[str]:
    """Trả danh sách sub-query (≥1). Condense theo lịch sử trước, rồi tách nếu ``planner_enabled``."""
    history = history or []

    effective = query
    if settings.query_rewrite_enabled and history:
        try:
            effective = rewrite_query(query, history)
        except Exception:  # noqa: BLE001 — condense lỗi không được chặn pipeline
            logger.exception("Planner: rewrite lỗi — dùng câu gốc.")
            effective = query

    if not settings.planner_enabled:
        return [effective]

    try:
        subs = _decompose(effective)
    except Exception:  # noqa: BLE001 — tách lỗi → fallback một sub-query
        logger.exception("Planner: phân rã lỗi — dùng nguyên câu làm 1 sub-query.")
        return [effective]

    subs = [s.strip() for s in subs if s and s.strip()]
    if not subs:
        return [effective]
    return subs[: settings.planner_max_subqueries]
