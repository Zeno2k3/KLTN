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

### Định nghĩa cấp tiểu học: lớp 1, lớp 2, lớp 3, lớp 4, lớp 5 (từ 6 đến 11 tuổi). Câu hỏi về tuyển sinh lớp 1 tiểu học

## PHẠM VI HỆ THỐNG (CHỈ lớp 1 tiểu học)
Hệ thống CHỈ xử lý các câu hỏi liên quan đến tuyển sinh VÀO LỚP 1 tiểu học tại Việt Nam.

### NGOÀI PHẠM VI — trả về DIRECT ngay lập tức:
- Tuyển sinh lớp 6 (vào THCS), lớp 10 (vào THPT), đại học, cao đẳng
- Chuyển trường, học bổng, du học
- Câu hỏi về cấp học khác (mầm non, THCS, THPT, đại học)
- Kiến thức chung, nấu ăn, thể thao, giải trí, chủ đề không liên quan
- Những câu hỏi ngoài phạm vi cấp tiểu học.


### TRONG PHẠM VI — trả về RAG:
- Những câu hỏi liên quan đến tuyển sinh cấp tiểu học, ví dụ:
- Hồ sơ, giấy tờ cần thiết để đăng ký vào lớp 1
- Độ tuổi, điều kiện tuyển sinh lớp 1
- Tuyến/khu vực tuyển sinh (phường, quận, trường công lập)
- Mốc thời gian nộp hồ sơ, lịch tuyển sinh lớp 1
- Học phí, chính sách hỗ trợ khi vào lớp 1
- Thủ tục đăng ký trực tuyến/trực tiếp vào lớp 1
- Trường tư thục, quốc tế tuyển sinh lớp 1
- Chương trình học lớp 1, sách giáo khoa lớp 1, phương pháp dạy học lớp 1
- Câu hỏi nối tiếp ("thế còn...?", "trường đó thì...?") khi lịch sử hội thoại
  đang bàn về tuyển sinh lớp 1 tiểu học

## CHÀO HỎI / HỎI VỀ TRỢ LÝ — trả về DIRECT:
- Xin chào, cảm ơn, tạm biệt
- Bạn là ai, bạn có thể làm gì

## QUY TẮC PHÂN LOẠI
1. Đọc toàn bộ câu hỏi và lịch sử hội thoại (nếu có).
2. Nếu câu hỏi đề cập đến BẤT KỲ cấp học nào KHÁC phạm tiểu học → DIRECT.
3. Nếu câu hỏi liên quan đến tuyển sinh đâu cấp tiểu học → RAG.
4. Nếu không chắc → DIRECT (an toàn hơn là trả lời sai phạm vi).

CHỈ in ra đúng MỘT từ: RAG hoặc DIRECT. Không giải thích, không thêm ký tự nào khác.
"""

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
