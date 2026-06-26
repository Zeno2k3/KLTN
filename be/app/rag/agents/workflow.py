"""RAGAgentWorkflow — điều phối ĐA TÁC TỬ bằng ``llama-index-workflows`` (gói ``workflows``).

Các @step là các tác tử trao đổi qua Event (xem ``events.py``):

    route ──direct──► direct_answer ─────────────────────────► StopEvent
      │
      └──rag──► (Planner phân rã) ──fan-out N×SubQueryRetrieve──► retrieve (num_workers)
                                                                     │
                                          fan-in (collect N) ◄───────┘
                                                 │
                                          synthesize ──► DraftReady ──► critique
                                                              ▲              │
                                                              │   accept ────┴──► StopEvent
                                                              └── revise (ReviseRequested)
                                                                     │
                                                                  revise ──► DraftReady (lặp ≤ max)

ĐIỂM VÀO: ``answer_question_agentic`` (async) — bọc span ``rag.answer`` (cùng tên đường cũ để Phoenix
đối chiếu) rồi chạy workflow. Các agent là hàm SYNC chặn → gọi qua ``asyncio.to_thread`` (đa luồng
thật cho retrieve song song vì call mạng OpenAI/Cohere/Weaviate nhả GIL).

Timeout: để ``None`` cho workflow — deadline do ``asyncio.wait_for`` ở ``chat_service`` quản (→ 503),
thống nhất với đường tuyến tính."""

from __future__ import annotations

import asyncio
import logging

from opentelemetry import trace
from workflows import Context, Workflow, step
from workflows.events import StopEvent

from app.core.config import settings
from app.rag.agents import critic, planner, retrieval_agent, synthesis
from app.rag.agents.events import (
    DraftReady,
    QueryStarted,
    ReviseRequested,
    RouteDirect,
    SubContextReady,
    SubQueryRetrieve,
)
from app.rag.query_engine import (
    _NO_CONTEXT_ANSWER,
    AnswerResult,
    _answer_direct,
    _current_trace_id,
    synthesize,
)
from app.rag.query_router import ROUTE_DIRECT, route_query

logger = logging.getLogger(__name__)


class RAGAgentWorkflow(Workflow):
    """Workflow đa tác tử. State (câu hỏi/lịch sử/đếm sub-query/revision/merged_nodes) giữ trong
    ``ctx.store``; Event chỉ mang dữ liệu cần cho fan-in."""

    @step
    async def route(
        self, ctx: Context, ev: QueryStarted
    ) -> RouteDirect | SubQueryRetrieve | None:
        """RouterAgent (TÁI DÙNG route_query) → direct hoặc Planner fan-out các sub-query."""
        await ctx.store.set("query", ev.query)
        await ctx.store.set("history", ev.history or [])
        await ctx.store.set("revision", 0)

        route = "rag"
        if settings.query_router_enabled:
            route = await asyncio.to_thread(route_query, ev.query, ev.history or [])
        if route == ROUTE_DIRECT:
            return RouteDirect()

        subqueries = await asyncio.to_thread(planner.plan, ev.query, ev.history or [])
        await ctx.store.set("num_subqueries", len(subqueries))
        for subquery in subqueries:
            ctx.send_event(SubQueryRetrieve(subquery=subquery))
        return None  # fan-out qua send_event; không emit qua return

    @step
    async def direct_answer(self, ctx: Context, ev: RouteDirect) -> StopEvent:
        """Trả lời thẳng (chào hỏi / ngoài phạm vi), sources=[] — không retrieve."""
        query = await ctx.store.get("query")
        history = await ctx.store.get("history")
        answer = await asyncio.to_thread(_answer_direct, query, history)
        return StopEvent(
            result=AnswerResult(answer=answer, sources=[], trace_id=None)
        )

    @step(num_workers=4)
    async def retrieve(
        self, ctx: Context, ev: SubQueryRetrieve
    ) -> SubContextReady:
        """RetrievalAgent cho MỘT sub-query (tự chấm + lặp). Chạy song song nhờ num_workers."""
        nodes, rounds = await asyncio.to_thread(
            retrieval_agent.retrieve_for_subquery, ev.subquery
        )
        return SubContextReady(subquery=ev.subquery, nodes=nodes, rounds=rounds)

    @step
    async def synthesize_step(
        self, ctx: Context, ev: SubContextReady
    ) -> DraftReady | StopEvent | None:
        """Fan-in: gom đủ N kết quả → gộp đa nguồn (khử trùng) → soạn bản nháp đầu (revision=0)."""
        num = await ctx.store.get("num_subqueries")
        collected = ctx.collect_events(ev, [SubContextReady] * num)
        if collected is None:
            return None  # chưa đủ N — chờ các Retrieval agent còn lại

        merged = synthesis.merge_nodes([c.nodes for c in collected])
        await ctx.store.set("merged_nodes", merged)
        rounds_total = sum(c.rounds for c in collected)
        span = trace.get_current_span()
        span.set_attribute("rag.subqueries", num)
        span.set_attribute("rag.retrieval_rounds", rounds_total)
        span.set_attribute("rag.merged_nodes", len(merged))

        if not merged:
            return StopEvent(
                result=AnswerResult(
                    answer=_NO_CONTEXT_ANSWER, sources=[], trace_id=None
                )
            )

        query = await ctx.store.get("query")
        answer, sources, context = await asyncio.to_thread(synthesize, query, merged)
        return DraftReady(answer=answer, context=context, sources=sources, revision=0)

    @step
    async def revise(self, ctx: Context, ev: ReviseRequested) -> DraftReady:
        """Synthesis viết lại theo feedback của Critic (cùng merged_nodes, không retrieve lại)."""
        query = await ctx.store.get("query")
        merged = await ctx.store.get("merged_nodes")
        answer, sources, context = await asyncio.to_thread(
            synthesize, query, merged, ev.feedback
        )
        return DraftReady(
            answer=answer, context=context, sources=sources, revision=ev.revision
        )

    @step
    async def critique(
        self, ctx: Context, ev: DraftReady
    ) -> ReviseRequested | StopEvent:
        """CriticAgent phản biện. Có vấn đề & còn hạn mức → ReviseRequested; ngược lại → chốt."""
        query = await ctx.store.get("query")
        verdict = await asyncio.to_thread(
            critic.critique, ev.answer, ev.context, ev.sources, query
        )
        revision = await ctx.store.get("revision")

        if verdict.wants_revision and revision < settings.critic_max_revisions:
            await ctx.store.set("revision", revision + 1)
            trace.get_current_span().set_attribute("rag.revisions", revision + 1)
            return ReviseRequested(feedback=verdict.feedback, revision=revision + 1)

        # Chốt: lọc nguồn chỉ còn nguồn thực sự được trích + gắn span highlight cho FE.
        final_sources = [
            s for s in ev.sources if s["index"] in verdict.cited_indices
        ]
        for s in final_sources:
            s["cited_spans"] = verdict.cited_spans.get(s["index"], [])
        trace.get_current_span().set_attribute("rag.revisions", revision)
        return StopEvent(
            result=AnswerResult(
                answer=verdict.answer, sources=final_sources, trace_id=None
            )
        )


async def answer_question_agentic(
    query_text: str,
    history: list[dict] | None = None,
    filters: object = None,  # noqa: ARG001 — đối xứng API; đường đa tác tử tự trích filter mỗi sub-query
) -> AnswerResult:
    """Điểm vào async của pipeline đa tác tử. Trả ``AnswerResult`` (answer + sources + trace_id).

    Bọc span ``rag.answer`` để Phoenix gom toàn bộ lượt (router/planner/retrieve×N/synthesize/critic)
    vào một trace; ``trace_id`` gắn vào kết quả để đối chiếu như đường cũ."""
    history = history or []
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.answer") as span:
        span.set_attribute("rag.query", query_text)
        span.set_attribute("rag.multi_agent", True)
        trace_id = _current_trace_id()

        workflow = RAGAgentWorkflow(timeout=None)
        result = await workflow.run(
            start_event=QueryStarted(query=query_text, history=history, filters=filters)
        )

        if isinstance(result, AnswerResult):
            result.trace_id = trace_id
            return result
        # Phòng hờ: workflow trả kiểu lạ (không nên xảy ra) → bọc lại để service không vỡ.
        logger.error("Workflow đa tác tử trả kiểu lạ: %r", type(result))
        return AnswerResult(answer=str(result), sources=[], trace_id=trace_id)
