"""Hậu kiểm trích nguồn (post-hoc citation attribution + verification).

Chạy SAU ``synthesize`` trong span ``rag.answer``. Mục tiêu: tách bạch SINH văn bản và TRÍCH
nguồn — không tin vào marker ``[n]`` mà LLM sinh tự gắn, mà dùng một LLM ĐỐI CHIẾU lại từng câu
với các nguồn đã retrieve:

  1. ATTRIBUTION: với mỗi câu, tìm (các) nguồn ``[n]`` thực sự chứa nội dung câu đó + trích đoạn
     NGUYÊN VĂN (``supporting_quote``) để FE highlight đúng đoạn (sub-chunk).
  2. JUDGE: đánh giá ``supported`` (nguồn có chứa ý) và ``in_scope`` (khớp phạm vi câu hỏi) →
     hành động ``keep | recite | drop``.

Hành vi DROP: xóa câu sai phạm vi / không nguồn, sửa marker lệch, lọc lại danh sách nguồn chỉ còn
nguồn thực sự được trích, gắn ``cited_spans`` cho mỗi nguồn.

LLM RIÊNG cho bước này (model = ``verifier_model``, rỗng → fallback ``openai_chat_model``) — KHÔNG
dùng chung singleton với synthesize. Một call structured-output làm CẢ attribution lẫn judge. Gọi
qua LlamaIndex → Phoenix auto-trace; bọc thêm span ``rag.citation_verify``. Module TỰ CHỨA, không
import ``query_engine``.

FAIL-SAFE: mọi lỗi (timeout, JSON hỏng, schema sai, mạng) → trả answer + sources GỐC, ``ok=False``.
Bước này KHÔNG bao giờ raise lên ``answer_question`` (không được chặn câu trả lời của phụ huynh)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI
from opentelemetry import trace

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tách câu: ngắt ở xuống dòng HOẶC sau dấu kết câu (. ! ? …) theo sau bởi khoảng trắng. Giữ delimiter
# trong kết quả split (nhóm bắt) để ráp lại không mất định dạng. KHÔNG ngắt ở ":" (tránh cắt header
# danh sách "Đối tượng ưu tiên 1:").
_SENT_SPLIT = re.compile(r"(\n+|(?<=[.!?…])\s+)")
_ANY_MARKER = re.compile(r"\[(\d+)\]")
# Đuôi dấu kết câu (. ! ? …) — để chèn lại marker TRƯỚC dấu chấm khi "recite".
_TRAILING_PUNCT = re.compile(r"([.!?…]+)\s*$")


@dataclass
class SentenceVerdict:
    sentence_id: int
    sentence_text: str
    generator_indices: list[int]  # [n] generator tự gắn (tham chiếu, có thể sai)
    attributed_indices: list[int]  # nguồn ĐÚNG do attribution suy ra
    supporting_quote: (
        str  # đoạn nguyên văn trong nguồn câu này dựa vào (highlight sub-chunk)
    )
    supported: bool
    in_scope: bool
    action: str  # "keep" | "recite" | "drop"


@dataclass
class VerificationResult:
    answer: str  # answer đã hiệu đính (DROP) hoặc gốc (fail-safe)
    cited_indices: set[int]  # tập nguồn THỰC SỰ được trích sau verify
    cited_spans: dict[
        int, list[str]
    ]  # index nguồn → các verbatim quote (cho FE highlight sub-chunk)
    verdicts: list[SentenceVerdict] = field(default_factory=list)
    ok: bool = True  # False nếu lỗi/timeout/drop-hết → fail-safe giữ answer gốc
    dropped_count: int = 0


# Singleton RIÊNG cho bước verify (lazy). Bọc trong hàm để mock độc lập trong test.
_llm: OpenAI | None = None


def _get_llm() -> OpenAI:
    """LLM verify (model ``verifier_model``, fallback chat model). Một call làm cả attribution+judge."""
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.verifier_model or settings.openai_chat_model,
            api_key=settings.openai_api_key,
            timeout=settings.verifier_timeout_seconds,
        )
    return _llm


_VERIFY_SYSTEM_PROMPT = """\
Bạn là bộ KIỂM TRA TRÍCH DẪN cho trợ lý tư vấn tuyển sinh tiểu học. Bạn nhận: CÂU HỎI của phụ
huynh, NGỮ CẢNH gồm các nguồn đánh số [1], [2], ... (toàn văn), và DANH SÁCH CÂU trong câu trả lời
(mỗi câu có id).

Với MỖI câu, hãy đối chiếu với NGỮ CẢNH và trả về một verdict:
1. attributed_indices: (các) số nguồn trong NGỮ CẢNH THỰC SỰ chứa nội dung câu đó. TỰ đối chiếu nội
   dung — BỎ QUA số nguồn mà câu tự gắn. Nếu không nguồn nào chứa → [].
2. supporting_quote: COPY NGUYÊN VĂN một đoạn ngắn (một cụm/câu) từ nguồn được gán, đúng đoạn làm
   căn cứ cho câu. KHÔNG diễn giải lại, KHÔNG tự viết. Rỗng "" nếu không có nguồn.
3. supported: true nếu có ít nhất một nguồn chứa nội dung câu; ngược lại false.
4. in_scope: true nếu câu KHỚP đúng PHẠM VI câu hỏi (cấp lớp, năm học, khu vực/tuyến, đối tượng).
   false nếu câu nói về phạm vi KHÁC — ví dụ câu hỏi về "lớp 1" nhưng câu trả lời nói về "lớp 6".
5. action:
   - "drop"  nếu in_scope=false HOẶC supported=false.
   - "recite" nếu supported=true VÀ in_scope=true NHƯNG số nguồn câu tự gắn KHÁC attributed_indices.
   - "keep"  nếu supported=true, in_scope=true, và số nguồn đã đúng.

CHỈ in ra JSON đúng cấu trúc sau, không giải thích, không thêm ký tự nào:
{"verdicts": [{"sentence_id": <int>, "attributed_indices": [<int>...], "supporting_quote": "<str>",
"supported": <bool>, "in_scope": <bool>, "action": "keep"|"recite"|"drop"}, ...]}
Mỗi câu đúng MỘT verdict, đủ mọi câu được liệt kê."""


def _split_sentences(answer: str) -> list[dict]:
    """Tách answer thành các câu (đơn vị claim), GIỮ marker [n] và delimiter để ráp lại.

    Trả list ``{"id", "text", "delim", "cited_indices"}`` sao cho
    ``"".join(text + delim)`` ≈ answer gốc. ``text`` gồm cả marker [n] ở cuối câu (nếu có)."""
    parts = _SENT_SPLIT.split(answer)
    sentences: list[dict] = []
    sid = 0
    i = 0
    while i < len(parts):
        text = parts[i]
        delim = parts[i + 1] if i + 1 < len(parts) else ""
        if text.strip():
            cited = [int(m) for m in _ANY_MARKER.findall(text)]
            sentences.append(
                {"id": sid, "text": text, "delim": delim, "cited_indices": cited}
            )
            sid += 1
        elif sentences:
            # Mảnh rỗng/khoảng trắng (vd delimiter dẫn đầu) → dồn vào delim câu trước, giữ định dạng.
            sentences[-1]["delim"] += text + delim
        i += 2
    return sentences


def _recite(text: str, indices: list[int]) -> str:
    """Thay mọi marker [n] trong câu bằng ``indices`` (attribution đã xác nhận đúng).

    Marker thường đứng TRƯỚC dấu kết câu (vd "...khai sinh [2]."): bóc hết marker cũ rồi chèn marker
    mới ngay trước dấu chấm để giữ đúng dấu câu."""
    new_marker = "".join(f"[{i}]" for i in indices)
    core = _ANY_MARKER.sub("", text)
    if not new_marker:
        return re.sub(r"\s{2,}", " ", core).rstrip()
    m = _TRAILING_PUNCT.search(core)
    if m:
        head = core[: m.start()].rstrip()
        return f"{head} {new_marker}{m.group(1)}"
    return f"{core.rstrip()} {new_marker}"


def _build_messages(
    sentences: list[dict], context: str, query: str
) -> list[ChatMessage]:
    listing = "\n".join(
        f"[câu {s['id']}] (đã gắn: "
        f"{''.join(f'[{i}]' for i in s['cited_indices']) or 'không'}) "
        f"{s['text'].strip()}"
        for s in sentences
    )
    user = (
        f"CÂU HỎI: {query}\n\n"
        f"NGỮ CẢNH (các nguồn, toàn văn):\n{context}\n\n"
        f"CÁC CÂU TRẢ LỜI CẦN KIỂM:\n{listing}\n\n"
        "Trả về JSON verdicts cho mọi câu."
    )
    return [
        ChatMessage(role=MessageRole.SYSTEM, content=_VERIFY_SYSTEM_PROMPT),
        ChatMessage(role=MessageRole.USER, content=user),
    ]


def _parse_verdicts(content: str, valid_ids: set[int]) -> dict[int, dict]:
    """Parse JSON verdicts → dict theo sentence_id. Raise nếu cấu trúc hỏng (→ fail-safe)."""
    data = json.loads(content)
    verdicts = data["verdicts"]
    if not isinstance(verdicts, list):
        raise ValueError("verdicts không phải list")
    out: dict[int, dict] = {}
    required = (
        "sentence_id",
        "attributed_indices",
        "supporting_quote",
        "supported",
        "in_scope",
        "action",
    )
    for v in verdicts:
        for key in required:
            if key not in v:
                raise ValueError(f"verdict thiếu field '{key}'")
        sid = int(v["sentence_id"])
        if sid in valid_ids:
            out[sid] = v
    return out


def _run_llm(sentences: list[dict], context: str, query: str) -> dict[int, dict]:
    """Gọi LLM verify (1 call, structured JSON) làm cả attribution + judge."""
    messages = _build_messages(sentences, context, query)
    response = _get_llm().chat(messages, response_format={"type": "json_object"})
    content = (response.message.content or "").strip()
    return _parse_verdicts(content, {s["id"] for s in sentences})


def _apply_verdicts(
    sentences: list[dict], verdicts_by_id: dict[int, dict], valid_idx: set[int]
) -> VerificationResult:
    kept_pieces: list[str] = []
    cited_indices: set[int] = set()
    cited_spans: dict[int, list[str]] = {}
    verdicts: list[SentenceVerdict] = []
    dropped = 0

    for s in sentences:
        gen_idx = [i for i in s["cited_indices"] if i in valid_idx]
        v = verdicts_by_id.get(s["id"])
        if v is None:
            # Không có verdict cho câu này → GIỮ nguyên (an toàn, không bao giờ drop câu chưa xét).
            kept_pieces.append(s["text"] + s["delim"])
            cited_indices.update(gen_idx)
            continue

        action = v["action"]
        attributed = [int(i) for i in v["attributed_indices"] if int(i) in valid_idx]
        quote = (v.get("supporting_quote") or "").strip()
        verdicts.append(
            SentenceVerdict(
                sentence_id=s["id"],
                sentence_text=s["text"].strip(),
                generator_indices=gen_idx,
                attributed_indices=attributed,
                supporting_quote=quote,
                supported=bool(v["supported"]),
                in_scope=bool(v["in_scope"]),
                action=action,
            )
        )

        if action == "drop":
            dropped += 1
            continue

        indices = attributed or gen_idx
        text = (
            _recite(s["text"], indices) if action == "recite" and indices else s["text"]
        )
        kept_pieces.append(text + s["delim"])
        cited_indices.update(indices)
        if quote:
            for i in indices:
                cited_spans.setdefault(i, [])
                if quote not in cited_spans[i]:
                    cited_spans[i].append(quote)

    new_answer = "".join(kept_pieces).strip()
    return VerificationResult(
        answer=new_answer,
        cited_indices=cited_indices,
        cited_spans=cited_spans,
        verdicts=verdicts,
        ok=True,
        dropped_count=dropped,
    )


def verify_answer(
    answer: str, context: str, sources: list[dict], query: str
) -> VerificationResult:
    """Hậu kiểm + hiệu đính câu trả lời. Fail-safe: lỗi → trả answer + sources gốc, ``ok=False``."""
    valid_idx = {s["index"] for s in sources if s.get("index") is not None}

    def _failsafe() -> VerificationResult:
        return VerificationResult(
            answer=answer, cited_indices=set(valid_idx), cited_spans={}, ok=False
        )

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.citation_verify") as span:
        try:
            sentences = _split_sentences(answer)
            span.set_attribute("verify.claims", len(sentences))
            if not sentences:
                span.set_attribute("verify.ok", True)
                span.set_attribute("verify.dropped", 0)
                return VerificationResult(
                    answer=answer, cited_indices=set(valid_idx), cited_spans={}, ok=True
                )

            verdicts_by_id = _run_llm(sentences, context, query)
            result = _apply_verdicts(sentences, verdicts_by_id, valid_idx)

            # Drop hết → KHÔNG trả câu trống cho phụ huynh; giữ answer gốc, ok=False.
            if not result.answer:
                logger.warning(
                    "Citation verify drop hết câu — giữ answer gốc (ok=False)."
                )
                span.set_attribute("verify.ok", False)
                span.set_attribute("verify.dropped", result.dropped_count)
                return _failsafe()

            span.set_attribute("verify.ok", True)
            span.set_attribute("verify.dropped", result.dropped_count)
            return result
        except Exception:
            logger.exception("Citation verify lỗi — giữ answer gốc (không chặn).")
            span.set_attribute("verify.ok", False)
            return _failsafe()
