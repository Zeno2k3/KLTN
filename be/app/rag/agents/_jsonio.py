"""Tiện ích bóc khối JSON ``{...}`` từ output LLM (chịu được rào ```json và prose kèm theo).

Dùng chung cho Planner + Retrieval grader. Tách riêng để khỏi lặp logic (citation_verifier có bản
tương đương ``_extract_json`` nhưng module đó tự chứa, không export)."""

from __future__ import annotations

import re


def extract_json_object(content: str) -> str:
    """Trả chuỗi ``{...}`` ngoài cùng trong ``content``; bóc rào ```json nếu có."""
    content = (content or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        content = content.rsplit("```", 1)[0]
    i, j = content.find("{"), content.rfind("}")
    return content[i : j + 1] if i >= 0 and j > i else content
