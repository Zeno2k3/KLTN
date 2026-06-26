"""Event của ``RAGAgentWorkflow`` (đa tác tử). Mỗi Event là một thông điệp trao đổi giữa các @step.

Luồng: ``QueryStarted`` → ``route`` → (``RouteDirect`` | fan-out ``SubQueryRetrieve``) → ``retrieve``
→ ``SubContextReady`` (fan-in) → ``synthesize`` → ``DraftReady`` → ``critique`` → (``StopEvent`` |
``ReviseRequested`` quay lại synthesis)."""

from __future__ import annotations

from typing import Any

from workflows.events import Event, StartEvent


class QueryStarted(StartEvent):
    """Sự kiện khởi động: câu hỏi + lịch sử (sliding window đã prune ở service)."""

    query: str
    history: list[dict] = []
    filters: Any = None  # tuỳ chọn caller; đường đa tác tử tự trích filter theo từng sub-query


class RouteDirect(Event):
    """Router phán: chào hỏi / ngoài phạm vi → trả lời thẳng, KHÔNG retrieve."""


class SubQueryRetrieve(Event):
    """Một sub-query cần retrieve (fan-out: Planner phát nhiều event này)."""

    subquery: str


class SubContextReady(Event):
    """Kết quả retrieve của một sub-query (fan-in: collect đủ N rồi mới synthesize)."""

    subquery: str
    nodes: Any = None  # list[NodeWithScore] — Any vì NodeWithScore không cần validate lại
    rounds: int = 1  # số vòng retrieve đã chạy (self-grade) cho sub-query này


class DraftReady(Event):
    """Bản nháp câu trả lời + ngữ cảnh đã đánh số, chờ Critic phản biện."""

    answer: str
    context: str
    sources: list[dict]
    revision: int = 0


class ReviseRequested(Event):
    """Critic yêu cầu Synthesis viết lại kèm góp ý (vòng agent-to-agent feedback)."""

    feedback: str
    revision: int
