"""Verify THẬT (DoD) đường code mới: Router + Query Rewriting + đường 'direct'.

Chạy ở venv chính (be/.venv), gọi OpenAI/Cohere/Weaviate THẬT:
    PYTHONUTF8=1 ./.venv/Scripts/python.exe eval/verify_router_rewrite.py

Không phụ thuộc HTTP/DB/Redis — gọi thẳng pipeline để chứng minh hành vi mới. Bật Phoenix tracing
nếu đã cấu hình endpoint (mỗi câu là 1 trace có span route_query/rewrite_query/retrieve/synthesize).
"""

from __future__ import annotations

import logging

from app.core.observability import init_tracing
from app.rag import query_engine, query_rewriter, query_router

logging.disable(logging.WARNING)


def _line(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    init_tracing()

    _line("1) ROUTER — phân loại trực tiếp (rag vs direct)")
    for q in [
        "Hồ sơ nhập học lớp 1 gồm những giấy tờ gì?",
        "Chỉ tôi cách nấu canh chua cá lóc",
        "Xin chào, bạn là ai?",
    ]:
        print(f"  [{query_router.route_query(q, []):6}]  {q}")

    _line("2) REWRITE — condense câu follow-up theo lịch sử")
    history = [
        {"role": "user", "content": "Trường Tiểu học Lumina tuyển sinh khi nào?"},
        {"role": "assistant", "content": "Trường nhận hồ sơ từ tháng 7 hằng năm."},
    ]
    follow = "thế còn học phí thì sao?"
    print(f"  Lịch sử: {history}")
    print(f"  Câu gốc      : {follow}")
    print(f"  Câu viết lại : {query_rewriter.rewrite_query(follow, history)}")

    _line("3) DIRECT — chào hỏi (answer_question, history=[])")
    res = query_engine.answer_question("Xin chào!", history=[])
    print(f"  answer : {res.answer}")
    print(f"  sources: {res.sources}")

    _line("4) DIRECT — câu NGOÀI phạm vi (answer_question)")
    res = query_engine.answer_question("Thủ đô nước Pháp là gì?", history=[])
    print(f"  answer : {res.answer}")
    print(f"  sources: {res.sources}")

    _line("5) FULL RAG đa lượt — lượt 2 dùng câu đã viết lại để truy hồi")
    try:
        turn1 = "Trẻ mấy tuổi thì đủ điều kiện vào lớp 1?"
        r1 = query_engine.answer_question(turn1, history=[])
        print(f"  [Lượt 1] {turn1}")
        print(f"    -> {r1.answer[:160]}")
        print(f"    nguồn: {[s.get('filename') for s in r1.sources]}")

        hist = [
            {"role": "user", "content": turn1},
            {"role": "assistant", "content": r1.answer},
        ]
        turn2 = "thế hồ sơ cần những gì?"
        r2 = query_engine.answer_question(turn2, history=hist)
        print(f"  [Lượt 2 - follow-up] {turn2}")
        print(f"    -> {r2.answer[:160]}")
        print(f"    nguồn: {[s.get('filename') for s in r2.sources]}")
        print(f"    trace_id: {r2.trace_id}")
    except Exception as exc:  # noqa: BLE001 — script verify, chỉ log
        print(f"  (Bỏ qua phần full-RAG: {type(exc).__name__}: {exc})")


if __name__ == "__main__":
    main()
