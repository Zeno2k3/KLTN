"""Lớp giám khảo ĐỐI CHỨNG bằng LLM (OpenAI/ChatGPT) cho eval retrieval.

Chấm nhị phân: một chunk có LIÊN QUAN tới câu hỏi không (có chứa bằng chứng khớp đáp án vàng). Dùng
OpenAI Chat Completions (gpt-4o-mini), ``temperature=0`` cho tái lập, ``response_format=json_object``
để parse chắc; cache kết quả theo khóa ``(id_câu, node_id)`` (chạy lại miễn phí); chạy song song bằng
thread pool. KHÔNG phải nguồn nhãn chính — chỉ để tính Cohen's κ với nhãn tự động.

Lưu ý phương pháp: giám khảo OpenAI dùng CÙNG nhà cung cấp với embedder (text-embedding-3-small) →
có thể có thiên lệch cùng-nhà. Vì nhãn tự động là chuẩn chính, đây chỉ là lớp xác nhận; ghi rõ trong
báo cáo để minh bạch.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from app.core.config import settings

_SYSTEM = (
    "Bạn là giám khảo đánh giá độ liên quan trong hệ thống truy hồi (RAG) tuyển sinh tiểu học. "
    "Cho một CÂU HỎI, ĐÁP ÁN ĐÚNG, ĐOẠN VÀNG (ngữ cảnh chuẩn chứa đáp án) và một ĐOẠN ỨNG VIÊN do "
    "hệ thống truy hồi trả về. Hãy quyết định ĐOẠN ỨNG VIÊN có LIÊN QUAN hay không: liên quan nghĩa "
    "là đoạn đó chứa bằng chứng trực tiếp giúp trả lời câu hỏi (trùng thông tin với đáp án/đoạn "
    "vàng). Chỉ xét nội dung đoạn ứng viên; bỏ qua văn phong. Trả về DUY NHẤT JSON: "
    '{"relevant": true|false}.'
)


@dataclass(frozen=True)
class JudgeItem:
    """Một cặp cần chấm. ``key`` duy nhất (vd ``"<id_câu>::<node_id>"``) để cache."""

    key: str
    question: str
    ground_truth: str
    reference_context: str
    chunk_text: str


def _build_prompt(it: JudgeItem) -> str:
    return (
        f"CÂU HỎI:\n{it.question}\n\n"
        f"ĐÁP ÁN ĐÚNG:\n{it.ground_truth}\n\n"
        f"ĐOẠN VÀNG:\n{it.reference_context}\n\n"
        f"ĐOẠN ỨNG VIÊN:\n{it.chunk_text}\n\n"
        'Đoạn ứng viên có liên quan không? Trả về JSON {"relevant": true|false}.'
    )


def _parse_relevant(text: str) -> bool | None:
    """Trích bool ``relevant`` từ phản hồi (robust)."""
    text = (text or "").strip()
    try:
        return bool(json.loads(text).get("relevant"))
    except Exception:  # noqa: BLE001
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return bool(json.loads(text[start : end + 1]).get("relevant"))
        except Exception:  # noqa: BLE001
            pass
    low = text.lower()
    if '"relevant": true' in low or '"relevant":true' in low:
        return True
    if '"relevant": false' in low or '"relevant":false' in low:
        return False
    return None


def _call_openai(client: OpenAI, prompt: str, tries: int = 4) -> bool | None:
    """Gọi OpenAI chat (temperature=0, JSON). Retry khi lỗi; None nếu thất bại."""
    for attempt in range(1, tries + 1):
        try:
            resp = client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
                timeout=60,
            )
            return _parse_relevant(resp.choices[0].message.content or "")
        except Exception:  # noqa: BLE001 — rate limit/mạng → retry
            time.sleep(2 * attempt)
    return None


def judge_all(
    items: list[JudgeItem],
    cache_path: str | Path,
    max_workers: int = 8,
) -> dict[str, bool]:
    """Chấm tất cả ``items`` (bỏ qua item đã có trong cache). Trả {key: relevant_bool}.

    Cache là JSON {key: bool}. Mục None (thất bại) KHÔNG ghi cache để lần sau thử lại."""
    cache_path = Path(cache_path)
    cache: dict[str, bool] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    todo = [it for it in items if it.key not in cache]
    if not settings.openai_api_key:
        raise RuntimeError(
            "Thiếu OPENAI_API_KEY trong .env — không thể chạy giám khảo OpenAI."
        )

    if todo:
        client = OpenAI(api_key=settings.openai_api_key)

        def work(it: JudgeItem) -> tuple[str, bool | None]:
            return it.key, _call_openai(client, _build_prompt(it))

        done = 0
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for key, verdict in pool.map(work, todo):
                if verdict is not None:
                    cache[key] = verdict
                done += 1
                if done % 25 == 0:
                    print(f"    LLM-judge: {done}/{len(todo)}")
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(
                        json.dumps(cache, ensure_ascii=False), encoding="utf-8"
                    )

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    return {it.key: cache[it.key] for it in items if it.key in cache}
