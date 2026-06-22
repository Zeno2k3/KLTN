"""Auto-extract metadata cấp văn bản (doc_type / issued_date / issuing_body / doc_name).

Quét phần đầu (1–2 trang) bằng regex; nếu còn trường thiếu thì gọi MỘT lần LLM xác nhận. LLM RIÊNG
cho bước này (không chung singleton), qua LlamaIndex → Phoenix auto-trace. Lỗi → trả phần regex
(không bao giờ chặn ingest). Không log nội dung văn bản (có thể chứa PII).
"""

from __future__ import annotations

import json
import logging
import re

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI

from app.core.config import settings
from app.rag.extract import PageBlock

logger = logging.getLogger(__name__)

DOC_TYPES = ("ke_hoach", "quyet_dinh", "thong_tu", "khac")

_TYPE_KEYWORDS = [
    ("ke_hoach", re.compile(r"KẾ\s+HOẠCH")),
    ("quyet_dinh", re.compile(r"QUYẾT\s+ĐỊNH")),
    ("thong_tu", re.compile(r"THÔNG\s+TƯ")),
]

_DATE_RE = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.IGNORECASE)
_NUMBER_RE = re.compile(r"Số\s*:\s*([0-9][0-9A-Za-zĐ/\.\-]*)", re.IGNORECASE)
_BODY_RE = re.compile(
    r"^(ỦY BAN NHÂN DÂN|BỘ GIÁO DỤC|SỞ GIÁO DỤC|PHÒNG GIÁO DỤC|HỘI ĐỒNG|CHÍNH PHỦ)[^\n]*",
    re.IGNORECASE | re.MULTILINE,
)

_llm: OpenAI | None = None


def _get_llm() -> OpenAI:
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.chunker_model or settings.openai_chat_model,
            api_key=settings.openai_api_key,
        )
    return _llm


def _header_text(pages: list[PageBlock], max_pages: int = 2) -> str:
    return "\n".join(p.text for p in pages[:max_pages]).strip()


def _regex_extract(header: str) -> dict:
    out: dict = {"doc_type": None, "issued_date": None, "issuing_body": None, "doc_name": None}
    for label, pat in _TYPE_KEYWORDS:
        if pat.search(header):
            out["doc_type"] = label
            break
    m = _DATE_RE.search(header)
    if m:
        d, mth, y = m.groups()
        out["issued_date"] = f"{int(d):02d}/{int(mth):02d}/{y}"
    b = _BODY_RE.search(header)
    if b:
        out["issuing_body"] = b.group(0).strip()
    num = _NUMBER_RE.search(header)
    if num:
        out["doc_name"] = f"Số {num.group(1)}"
    return out


_LLM_SYSTEM = """\
Bạn trích metadata của một văn bản hành chính tiếng Việt từ phần ĐẦU văn bản.
CHỈ in JSON, không giải thích, dạng:
{"doc_type":"ke_hoach|quyet_dinh|thong_tu|khac","issued_date":"dd/mm/yyyy hoặc \\"\\"","issuing_body":"...","doc_name":"..."}
Nếu không xác định được trường nào, để chuỗi rỗng."""


def _llm_extract(header: str) -> dict:
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=_LLM_SYSTEM),
        ChatMessage(role=MessageRole.USER, content=f"PHẦN ĐẦU VĂN BẢN:\n{header[:2000]}"),
    ]
    resp = _get_llm().chat(messages)
    s = (resp.message.content or "").strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Không tìm thấy JSON.")
    data = json.loads(s[start : end + 1])
    if data.get("doc_type") not in DOC_TYPES:
        data["doc_type"] = "khac"
    return data


def extract_doc_metadata(pages: list[PageBlock], filename: str | None = None) -> dict:
    """Trả {doc_type, issued_date, issuing_body, doc_name}. Regex trước, LLM bù khi thiếu.

    Không bao giờ raise: lỗi LLM → giữ kết quả regex. ``doc_name`` fallback về ``filename``."""
    header = _header_text(pages)
    result = _regex_extract(header)

    missing = [k for k, v in result.items() if not v]
    if header and missing and settings.chunk_llm_enabled and settings.openai_api_key:
        try:
            llm_data = _llm_extract(header)
            for k in result:
                if not result[k] and llm_data.get(k):
                    result[k] = str(llm_data[k]).strip() or None
        except Exception:  # noqa: BLE001 — không chặn ingest
            logger.warning("doc_metadata: LLM extract lỗi — dùng kết quả regex.")

    if not result.get("doc_type"):
        result["doc_type"] = "khac"
    if not result.get("doc_name"):
        result["doc_name"] = filename
    return result
