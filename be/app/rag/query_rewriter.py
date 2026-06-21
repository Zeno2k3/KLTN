"""Query rewriting (condense-question): viết lại câu follow-up thành câu ĐỘC LẬP theo lịch sử.

Giải bài toán hội thoại đa lượt: câu như "thế còn học phí thì sao?" thiếu ngữ cảnh → BM25/embedding
truy hồi sai. Rewriter dựa vào lịch sử bổ sung ngữ cảnh ("học phí trường X năm 2025 là bao nhiêu?").
Câu đã viết lại dùng cho CẢ truy hồi lẫn synthesize.

Chỉ chạy khi CÓ lịch sử (lượt đầu: trả nguyên văn, tiết kiệm 1 lời gọi). LLM RIÊNG cho bước này
(model = ``settings.rewrite_model``, rỗng → fallback ``openai_chat_model``). Gọi qua LlamaIndex →
Phoenix auto-trace. Module TỰ CHỨA, không import ``query_engine``."""

from __future__ import annotations

import logging

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_REWRITE_SYSTEM_PROMPT = """\
Bạn là bộ viết lại truy vấn cho hệ thống tìm kiếm tài liệu tuyển sinh tiểu học.

Dựa vào LỊCH SỬ HỘI THOẠI, hãy viết lại CÂU HỎI HIỆN TẠI thành MỘT câu hỏi ĐỘC LẬP, đầy đủ ngữ
cảnh, có thể hiểu được mà không cần đọc lại lịch sử (thay đại từ/phần tỉnh lược bằng thực thể cụ
thể đã nhắc trước đó: tên trường, năm học, đối tượng...).

Quy tắc:
- Giữ NGUYÊN ý định và NGÔN NGỮ (tiếng Việt) của câu hỏi gốc.
- KHÔNG trả lời câu hỏi, KHÔNG thêm thông tin mới, KHÔNG giải thích.
- Nếu câu hỏi hiện tại đã đầy đủ ngữ cảnh, trả lại NGUYÊN VĂN.
- CHỈ in ra câu hỏi đã viết lại, không thêm gì khác."""

_llm: OpenAI | None = None


def _get_llm() -> OpenAI:
    """LLM riêng của rewriter (singleton trong module). Model ``rewrite_model`` (fallback chat model)."""
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.rewrite_model or settings.openai_chat_model,
            api_key=settings.openai_api_key,
        )
    return _llm


def _format_history(history: list[dict]) -> str:
    """Ghép sliding window các tin gần nhất thành văn bản ngắn cho prompt viết lại."""
    window = history[-settings.chat_history_window :] if history else []
    lines = []
    for message in window:
        who = "Phụ huynh" if message.get("role") == "user" else "Trợ lý"
        lines.append(f"{who}: {(message.get('content') or '').strip()}")
    return "\n".join(lines)


def rewrite_query(query: str, history: list[dict] | None = None) -> str:
    """Viết lại câu hỏi thành câu độc lập theo lịch sử.

    History rỗng → trả nguyên văn (không gọi LLM). Output rỗng / lỗi → fallback câu gốc."""
    history = history or []
    if not history:
        return query

    hist_text = _format_history(history)
    user_content = (
        f"LỊCH SỬ HỘI THOẠI (gần nhất):\n{hist_text}\n\n"
        f"CÂU HỎI HIỆN TẠI: {query}\n\n"
        "Câu hỏi độc lập đã viết lại:"
    )
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=_REWRITE_SYSTEM_PROMPT),
        ChatMessage(role=MessageRole.USER, content=user_content),
    ]
    try:
        response = _get_llm().chat(messages)
        rewritten = (response.message.content or "").strip()
    except Exception:
        logger.exception("Rewriter LLM lỗi — dùng câu gốc.")
        return query
    return rewritten or query
