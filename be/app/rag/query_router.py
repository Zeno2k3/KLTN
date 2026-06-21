"""LLM Router: phân loại truy vấn ``rag`` (cần tài liệu) vs ``direct`` (chào hỏi / ngoài phạm vi).

Chạy TRƯỚC retrieve trong span ``rag.answer``. Câu rõ ràng ngoài phạm vi tuyển sinh tiểu học bị
định tuyến ``direct`` → trả lời thẳng, KHÔNG truy hồi — tránh việc embedding tương đồng kéo nhầm
tài liệu rồi LLM cố trả lời (bug "câu ngoài phạm vi vẫn được trả lời").

LLM RIÊNG cho bước này (model = ``settings.router_model``, rỗng → fallback ``openai_chat_model``)
— KHÔNG dùng chung singleton với synthesize, để sau gắn model rẻ/nhanh. Gọi qua LlamaIndex →
Phoenix auto-trace. Module TỰ CHỨA, không import ``query_engine`` (tránh import vòng + mock độc lập
trong test)."""

from __future__ import annotations

import logging

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

ROUTE_RAG = "rag"
ROUTE_DIRECT = "direct"

_ROUTER_SYSTEM_PROMPT = """\
Bạn là bộ định tuyến cho trợ lý tư vấn TUYỂN SINH TIỂU HỌC. Nhiệm vụ: đọc CÂU HỎI HIỆN TẠI (kèm
lịch sử nếu có) và phân loại thành đúng MỘT nhãn:

- RAG: câu hỏi cần tra cứu tài liệu tuyển sinh tiểu học (hồ sơ, học phí, độ tuổi, tuyến/khu vực,
  mốc thời gian, điều kiện, thủ tục, chính sách...). KỂ CẢ câu hỏi nối tiếp ("thế còn...?",
  "trường đó...?") nếu lịch sử cho thấy đang bàn về tuyển sinh tiểu học.
- DIRECT: chào hỏi, cảm ơn, hỏi về chính trợ lý, hoặc câu RÕ RÀNG ngoài phạm vi tuyển sinh tiểu
  học (nấu ăn, thể thao, cấp học khác, kiến thức chung...).

CHỈ in ra đúng MỘT từ: RAG hoặc DIRECT. Không giải thích, không thêm ký tự nào khác."""

_llm: OpenAI | None = None


def _get_llm() -> OpenAI:
    """LLM riêng của router (singleton trong module). Model ``router_model`` (fallback chat model)."""
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.router_model or settings.openai_chat_model,
            api_key=settings.openai_api_key,
        )
    return _llm


def _format_history(history: list[dict]) -> str:
    """Ghép sliding window các tin gần nhất thành văn bản ngắn cho prompt phân loại."""
    window = history[-settings.chat_history_window :] if history else []
    lines = []
    for message in window:
        who = "Phụ huynh" if message.get("role") == "user" else "Trợ lý"
        lines.append(f"{who}: {(message.get('content') or '').strip()}")
    return "\n".join(lines)


def route_query(query: str, history: list[dict] | None = None) -> str:
    """Phân loại truy vấn → ``rag`` | ``direct``.

    Default an toàn ``rag`` khi LLM trả output lạ hoặc lỗi: không làm mất khả năng trả lời câu hỏi
    thật; phần ngoài-phạm-vi còn lọt vẫn được 2 lớp chặn hạ nguồn (``_NO_CONTEXT_ANSWER`` khi
    retrieve rỗng + quy tắc từ chối trong system prompt synthesize) xử lý."""
    history = history or []
    hist_text = _format_history(history)
    user_content = (
        f"LỊCH SỬ HỘI THOẠI (gần nhất):\n{hist_text}\n\n" if hist_text else ""
    ) + f"CÂU HỎI HIỆN TẠI: {query}\n\nPhân loại CÂU HỎI HIỆN TẠI: RAG hay DIRECT?"
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=_ROUTER_SYSTEM_PROMPT),
        ChatMessage(role=MessageRole.USER, content=user_content),
    ]
    try:
        response = _get_llm().chat(messages)
        label = (response.message.content or "").strip().upper()
    except Exception:
        logger.exception("Router LLM lỗi — mặc định 'rag' (không chặn câu hỏi thật).")
        return ROUTE_RAG

    if "DIRECT" in label and "RAG" not in label:
        return ROUTE_DIRECT
    return ROUTE_RAG
