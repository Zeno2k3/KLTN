"""Lớp điều phối ĐA TÁC TỬ (event-driven multi-agent) cho RAG.

Bật qua ``settings.rag_multi_agent_enabled``. Khác pipeline tuyến tính ``query_engine.answer_question``
ở chỗ: Planner phân rã câu hỏi → nhiều Retrieval agent chạy SONG SONG (fan-out) → Synthesis gộp đa
nguồn (fan-in) → Critic phản biện + vòng viết lại (agent-to-agent feedback). Dựng bằng
``llama-index-workflows`` (gói ``workflows``); điểm vào ``workflow.answer_question_agentic``.

NGUYÊN TẮC: TÁI SỬ DỤNG, không viết lại. Các agent là hàm SYNC gọi lại code đã test kỹ
(``route_query``, ``retrieve_and_rerank``, ``synthesize``, ``verify_answer``); workflow async chỉ
điều phối và bọc phần chặn qua ``asyncio.to_thread``.
"""
