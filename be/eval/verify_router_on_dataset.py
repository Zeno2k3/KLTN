"""Eval thủ công (thay RAGAS — không cài được trên Py3.14): kiểm Router KHÔNG phân loại nhầm câu
hỏi tuyển sinh THẬT trong dataset thành 'direct' (false-direct = hồi quy chính của tính năng này).

Chạy: PYTHONUTF8=1 PYTHONPATH=. ./.venv/Scripts/python.exe eval/verify_router_on_dataset.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.rag import query_router

logging.disable(logging.WARNING)

_DATASET = Path(__file__).parent / "dataset.json"


def main() -> None:
    data = json.loads(_DATASET.read_text(encoding="utf-8"))
    rag = direct = 0
    for i, item in enumerate(data, start=1):
        q = item["question"]
        route = query_router.route_query(q, [])
        if route == "rag":
            rag += 1
        else:
            direct += 1
        print(f"[{i}/{len(data)}] {route:6} | {q}")
    print("\n--- KẾT QUẢ ---")
    print(f"rag   : {rag}/{len(data)}  (mong đợi = toàn bộ — câu hỏi tuyển sinh thật)")
    print(f"direct: {direct}/{len(data)} (false-direct → hồi quy nếu > 0)")


if __name__ == "__main__":
    main()
