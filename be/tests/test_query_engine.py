"""Test pipeline trả lời: rerank lấy top_n, ráp nguồn trích dẫn, ràng buộc prompt, ngắn mạch
khi không có ngữ cảnh. Mock retriever/reranker/LLM — không gọi mạng hay model thật."""

from types import SimpleNamespace

from llama_index.core.schema import NodeWithScore, TextNode

from app.rag import query_engine


def _node(text, doc_id, filename, uuid, score):
    node = TextNode(
        text=text, id_=uuid, metadata={"document_id": doc_id, "filename": filename}
    )
    return NodeWithScore(node=node, score=score)


def test_answer_question_reranks_builds_sources_and_calls_llm(monkeypatch):
    # Tách router/rewrite/verifier ra khỏi test này (tập trung kiểm retrieve→rerank→synthesize).
    monkeypatch.setattr(query_engine.settings, "query_router_enabled", False)
    monkeypatch.setattr(query_engine.settings, "query_rewrite_enabled", False)
    monkeypatch.setattr(query_engine.settings, "citation_verify_enabled", False)
    candidates = [
        _node(f"đoạn nội dung {i}", 1, "quy-che.pdf", f"uuid-{i}", 0.5 + i)
        for i in range(10)
    ]
    monkeypatch.setattr(query_engine, "hybrid_retrieve", lambda q, k, f: candidates)

    class FakeReranker:
        def postprocess_nodes(self, nodes, query_str=None):
            self.seen_query = query_str
            return nodes[:3]  # top_n = 3

    fake_reranker = FakeReranker()
    monkeypatch.setattr(query_engine, "_get_reranker", lambda: fake_reranker)

    captured: dict = {}

    class FakeLLM:
        def chat(self, messages):
            captured["messages"] = messages
            return SimpleNamespace(
                message=SimpleNamespace(content="Trường nhận hồ sơ từ tháng 7 [1].")
            )

    monkeypatch.setattr(query_engine, "_get_llm", lambda: FakeLLM())

    result = query_engine.answer_question("Khi nào nhận hồ sơ?")

    assert result.answer == "Trường nhận hồ sơ từ tháng 7 [1]."
    assert fake_reranker.seen_query == "Khi nào nhận hồ sơ?"
    # Chỉ giữ top_n=3 nguồn, đúng metadata + weaviate uuid.
    assert len(result.sources) == 3
    assert result.sources[0]["document_id"] == 1
    assert result.sources[0]["filename"] == "quy-che.pdf"
    assert result.sources[0]["weaviate_uuid"] == "uuid-0"

    system_msg = captured["messages"][0].content
    user_msg = captured["messages"][1].content
    assert "CHỈ trả lời dựa trên" in system_msg  # ràng buộc chống bịa
    assert "PHẠM VI" in system_msg  # Lớp A: yêu cầu lọc theo phạm vi câu hỏi
    assert "đoạn nội dung 0" in user_msg  # ngữ cảnh đã rerank được đưa vào prompt
    assert "Khi nào nhận hồ sơ?" in user_msg


def test_sources_score_is_json_serializable():
    # Reranker thật trả score kiểu np.float32 → KHÔNG JSON-serializable; _build_context
    # phải ép về float thuần để lưu được vào cột JSONB (bug bắt được khi chạy HTTP thật).
    import json

    import numpy as np

    ns = _node("Nội dung", 1, "a.pdf", "u1", 0.0)
    ns.score = np.float32(0.0459)  # gán sau khởi tạo để giữ nguyên numpy type
    _, sources = query_engine._build_context([ns])

    json.dumps(sources)  # không được ném TypeError
    assert type(sources[0]["score"]) is float


def test_answer_question_short_circuits_without_context(monkeypatch):
    monkeypatch.setattr(query_engine.settings, "query_router_enabled", False)
    monkeypatch.setattr(query_engine.settings, "query_rewrite_enabled", False)
    monkeypatch.setattr(query_engine, "hybrid_retrieve", lambda q, k, f: [])

    def _boom():
        raise AssertionError("Không được gọi reranker/LLM khi không có ngữ cảnh")

    monkeypatch.setattr(query_engine, "_get_reranker", lambda: _boom())
    monkeypatch.setattr(query_engine, "_get_llm", lambda: _boom())

    result = query_engine.answer_question("Câu hỏi không có tài liệu")
    assert result.sources == []
    assert "chưa" in result.answer.lower()


def test_answer_question_excludes_metadata_from_snippet(monkeypatch):
    monkeypatch.setattr(query_engine.settings, "query_router_enabled", False)
    monkeypatch.setattr(query_engine.settings, "query_rewrite_enabled", False)
    monkeypatch.setattr(query_engine.settings, "citation_verify_enabled", False)
    # snippet/ngữ cảnh dùng text THUẦN, không lẫn "document_id: ..." vào câu trả lời.
    node = _node("Nội dung thuần tuý", 7, "a.pdf", "uuid-x", 1.0)
    monkeypatch.setattr(query_engine, "hybrid_retrieve", lambda q, k, f: [node])
    monkeypatch.setattr(
        query_engine,
        "_get_reranker",
        lambda: SimpleNamespace(postprocess_nodes=lambda nodes, query_str=None: nodes),
    )

    captured: dict = {}

    monkeypatch.setattr(
        query_engine,
        "_get_llm",
        lambda: SimpleNamespace(
            chat=lambda messages: (
                captured.update(messages=messages)
                or SimpleNamespace(message=SimpleNamespace(content="ok"))
            )
        ),
    )

    result = query_engine.answer_question("hỏi")
    assert result.sources[0]["snippet"] == "Nội dung thuần tuý"
    assert "document_id" not in captured["messages"][1].content


# --- Tiền xử lý: Router (rag/direct) + Query Rewriting ---


def test_answer_question_direct_route_short_circuits(monkeypatch):
    # Router='direct' → trả lời thẳng, KHÔNG retrieve/rerank/synthesize, sources rỗng.
    monkeypatch.setattr(query_engine.settings, "query_router_enabled", True)
    monkeypatch.setattr(query_engine, "route_query", lambda q, h: "direct")

    def _boom(*args, **kwargs):
        raise AssertionError("Đường 'direct' không được retrieve")

    monkeypatch.setattr(query_engine, "retrieve_and_rerank", _boom)
    monkeypatch.setattr(
        query_engine,
        "_get_llm",
        lambda: SimpleNamespace(
            chat=lambda messages: SimpleNamespace(
                message=SimpleNamespace(content="Chào phụ huynh, tôi là LuminaAI!")
            )
        ),
    )

    result = query_engine.answer_question("xin chào", history=[])
    assert result.sources == []
    assert result.answer == "Chào phụ huynh, tôi là LuminaAI!"


def test_answer_question_rag_route_retrieves_with_rewritten_query(monkeypatch):
    # Router='rag' + có lịch sử → retrieve nhận CÂU ĐÃ VIẾT LẠI (không phải câu follow-up gốc).
    monkeypatch.setattr(query_engine.settings, "query_router_enabled", True)
    monkeypatch.setattr(query_engine.settings, "query_rewrite_enabled", True)
    monkeypatch.setattr(query_engine.settings, "citation_verify_enabled", False)
    monkeypatch.setattr(query_engine, "route_query", lambda q, h: "rag")
    monkeypatch.setattr(
        query_engine,
        "rewrite_query",
        lambda q, h: "Học phí trường Lumina là bao nhiêu?",
    )

    seen: dict = {}

    def _fake_retrieve(query, filters=None):
        seen["query"] = query
        return [_node("nội dung học phí", 1, "a.pdf", "u1", 1.0)]

    monkeypatch.setattr(query_engine, "retrieve_and_rerank", _fake_retrieve)
    monkeypatch.setattr(
        query_engine,
        "_get_llm",
        lambda: SimpleNamespace(
            chat=lambda messages: SimpleNamespace(
                message=SimpleNamespace(content="Học phí là 2 triệu/tháng [1].")
            )
        ),
    )

    history = [
        {"role": "user", "content": "Trường Lumina tuyển sinh khi nào?"},
        {"role": "assistant", "content": "Từ tháng 7."},
    ]
    result = query_engine.answer_question("thế còn học phí?", history=history)
    assert seen["query"] == "Học phí trường Lumina là bao nhiêu?"
    assert result.answer == "Học phí là 2 triệu/tháng [1]."
    assert result.sources[0]["filename"] == "a.pdf"


# --- Hậu kiểm trích nguồn (citation verifier) trong pipeline ---


def _two_source_pipeline(monkeypatch, answer_text):
    """Dựng pipeline mock (router/rewrite tắt) trả 2 nguồn + synthesize ra ``answer_text``."""
    monkeypatch.setattr(query_engine.settings, "query_router_enabled", False)
    monkeypatch.setattr(query_engine.settings, "query_rewrite_enabled", False)
    nodes = [
        _node("nội dung 1", 1, "a.pdf", "u1", 0.9),
        _node("nội dung 2", 2, "b.pdf", "u2", 0.8),
    ]
    monkeypatch.setattr(query_engine, "hybrid_retrieve", lambda q, k, f: nodes)
    monkeypatch.setattr(
        query_engine,
        "_get_reranker",
        lambda: SimpleNamespace(postprocess_nodes=lambda ns, query_str=None: ns),
    )
    monkeypatch.setattr(
        query_engine,
        "_get_llm",
        lambda: SimpleNamespace(
            chat=lambda messages: SimpleNamespace(
                message=SimpleNamespace(content=answer_text)
            )
        ),
    )


def test_answer_question_runs_verifier_when_enabled(monkeypatch):
    from app.rag import citation_verifier

    _two_source_pipeline(monkeypatch, "Câu 1 [1]. Câu 2 [2].")
    monkeypatch.setattr(query_engine.settings, "citation_verify_enabled", True)

    def _fake_verify(answer, context, sources, query):
        # Giả lập DROP câu 2 (source 2 bị loại), gắn cited_spans cho source 1.
        return citation_verifier.VerificationResult(
            answer="Câu 1 [1].",
            cited_indices={1},
            cited_spans={1: ["nội dung 1"]},
            ok=True,
            dropped_count=1,
        )

    monkeypatch.setattr(citation_verifier, "verify_answer", _fake_verify)

    result = query_engine.answer_question("hỏi")
    assert result.answer == "Câu 1 [1]."
    assert [s["index"] for s in result.sources] == [1]  # source 2 đã bị lọc
    assert result.sources[0]["cited_spans"] == ["nội dung 1"]


def test_answer_question_skips_verifier_when_disabled(monkeypatch):
    from app.rag import citation_verifier

    _two_source_pipeline(monkeypatch, "Câu 1 [1]. Câu 2 [2].")
    monkeypatch.setattr(query_engine.settings, "citation_verify_enabled", False)

    def _boom(*args, **kwargs):
        raise AssertionError("verify_answer KHÔNG được gọi khi tắt cờ")

    monkeypatch.setattr(citation_verifier, "verify_answer", _boom)

    result = query_engine.answer_question("hỏi")
    assert result.answer == "Câu 1 [1]. Câu 2 [2]."  # synthesize gốc, không hiệu đính
    assert len(result.sources) == 2


def test_answer_question_verifier_failsafe(monkeypatch):
    from app.rag import citation_verifier

    _two_source_pipeline(monkeypatch, "Câu 1 [1]. Câu 2 [2].")
    monkeypatch.setattr(query_engine.settings, "citation_verify_enabled", True)

    def _fake_verify(answer, context, sources, query):
        # ok=False → fail-safe: pipeline phải giữ answer + sources GỐC.
        return citation_verifier.VerificationResult(
            answer="(không dùng)", cited_indices=set(), cited_spans={}, ok=False
        )

    monkeypatch.setattr(citation_verifier, "verify_answer", _fake_verify)

    result = query_engine.answer_question("hỏi")
    assert result.answer == "Câu 1 [1]. Câu 2 [2]."  # giữ answer gốc
    assert len(result.sources) == 2
    assert "cited_spans" not in result.sources[0]  # không gắn span khi fail-safe
