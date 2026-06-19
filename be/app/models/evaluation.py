"""Model lưu điểm đánh giá chất lượng câu trả lời RAG (RAGAS)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.message import Message


class MessageEvaluation(CreatedAtMixin, Base):
    """Mỗi dòng = một chỉ số RAGAS cho một câu trả lời của assistant.

    metric ví dụ: faithfulness | answer_relevancy | context_precision | context_recall.
    """

    __tablename__ = "message_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    evaluator: Mapped[str | None] = mapped_column(
        String(64), server_default=text("'ragas'")
    )
    run_id: Mapped[str | None] = mapped_column(String(64))  # gom theo 1 lần chạy batch

    message: Mapped[Message] = relationship(back_populates="evaluations")

    __table_args__ = (
        Index(
            "ix_message_evaluations_message_id_metric", "message_id", "metric"
        ),
    )
