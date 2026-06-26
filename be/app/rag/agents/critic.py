"""CriticAgent: phản biện bản nháp rồi quyết định CHẤP NHẬN hay YÊU CẦU VIẾT LẠI (agent-to-agent).

Nâng cấp ``citation_verifier`` (vốn chỉ hiệu đính tại chỗ) thành tác tử có VÒNG PHẢN HỒI: tái dùng
toàn bộ logic attribution/judge của verifier; nếu phải DROP câu (thiếu nguồn / sai phạm vi) thì coi
bản nháp là "có vấn đề" và gửi feedback về Synthesis để viết lại (workflow giới hạn
``critic_max_revisions`` lần). Khi hết hạn mức / không có vấn đề → chấp nhận bản đã hiệu đính.

Critic LUÔN chạy trong đường đa tác tử (không phụ thuộc ``citation_verify_enabled``). Fail-safe của
verifier (``ok=False``) → chấp nhận answer gốc, không viết lại (không chặn câu trả lời của phụ huynh)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.rag import citation_verifier

# Góp ý gửi Synthesis khi yêu cầu viết lại: nêu lý do chung (có câu bị loại) để LLM tự sửa.
_REVISE_FEEDBACK = (
    "Bản nháp trước có câu bị loại vì KHÔNG có nguồn trong ngữ cảnh hoặc SAI phạm vi câu hỏi "
    "(nhầm cấp lớp/năm/khu vực). Hãy viết lại câu trả lời CHỈ dùng thông tin có trong ngữ cảnh, "
    "đúng phạm vi câu hỏi, và gắn [n] đúng nguồn cho từng ý."
)


@dataclass
class CriticVerdict:
    """Phán quyết của Critic cho một bản nháp."""

    answer: str  # answer đã hiệu đính (DROP câu xấu) hoặc gốc (fail-safe)
    cited_indices: set[int]  # nguồn thực sự được trích sau verify
    cited_spans: dict[int, list[str]] = field(default_factory=dict)  # FE highlight sub-chunk
    wants_revision: bool = False  # True → có câu bị loại, đáng viết lại (workflow quyết hạn mức)
    feedback: str = ""  # góp ý gửi Synthesis khi wants_revision


def critique(
    answer: str, context: str, sources: list[dict], query: str
) -> CriticVerdict:
    """Phản biện bản nháp. Tái dùng ``verify_answer``; suy ra có nên viết lại không từ ``dropped_count``."""
    valid_idx = {s["index"] for s in sources if s.get("index") is not None}

    vr = citation_verifier.verify_answer(answer, context, sources, query)

    # Verifier fail-safe (lỗi/timeout/drop-hết) → giữ answer gốc, KHÔNG viết lại.
    if not vr.ok:
        return CriticVerdict(
            answer=answer,
            cited_indices=set(valid_idx),
            cited_spans={},
            wants_revision=False,
        )

    wants_revision = vr.dropped_count > 0
    return CriticVerdict(
        answer=vr.answer,
        cited_indices=vr.cited_indices,
        cited_spans=vr.cited_spans,
        wants_revision=wants_revision,
        feedback=_REVISE_FEEDBACK if wants_revision else "",
    )
