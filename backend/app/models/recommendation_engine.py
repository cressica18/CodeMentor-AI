"""
Phase 5 — Problem Recommender Agent persistence layer.

These tables are additive to the Phase 3 `recommendations` table
(generic, agent-agnostic recommendation storage). They are specific to
*Codeforces problems* recommended by the new Recommender Agent and
carry the structured fields (contest_id, index, rating, tags,
difficulty match score, etc.) the Phase 5 frontend needs to render
problem cards without re-deriving them from `Recommendation.payload`.

No agent logic lives here — pure persistence, consistent with
app/models/memory.py and app/models/agent.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    JSON,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RecommendedProblem(Base):
    """A single real Codeforces problem recommended to a user."""

    __tablename__ = "recommended_problems"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "contest_id", "index", "recommendation_session_id",
            name="uq_recommended_problems_user_problem_session",
        ),
        Index("ix_recommended_problems_user_created", "user_id", "recommended_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recommendation_sessions.id", ondelete="SET NULL"), nullable=True
    )

    contest_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    index: Mapped[str] = mapped_column(String(10), nullable=False)
    problem_name: Mapped[str] = mapped_column(String(300), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # "reinforcement" | "advancement" | "recovery" | "contest_prep"
    recommendation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="reinforcement")
    recommendation_score: Mapped[float] = mapped_column(Float, default=0.0)
    recommendation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_solve_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    url: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # User interaction state
    solved: Mapped[bool] = mapped_column(Boolean, default=False)
    attempted: Mapped[bool] = mapped_column(Boolean, default=False)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)

    recommended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<RecommendedProblem user_id={self.user_id} {self.contest_id}{self.index} type={self.recommendation_type}>"


class ProblemAttempt(Base):
    """A user-reported attempt at a recommended (or any) CF problem."""

    __tablename__ = "problem_attempts"
    __table_args__ = (Index("ix_problem_attempts_user_problem", "user_id", "contest_id", "index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recommended_problem_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recommended_problems.id", ondelete="SET NULL"), nullable=True
    )

    contest_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    index: Mapped[str] = mapped_column(String(10), nullable=False)

    # "solved" | "attempted" | "skipped"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="attempted")
    time_spent_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    def __repr__(self) -> str:
        return f"<ProblemAttempt user_id={self.user_id} {self.contest_id}{self.index} status={self.status}>"


class RecommendationSession(Base):
    """One execution of the Problem Recommender Agent for a user."""

    __tablename__ = "recommendation_sessions"
    __table_args__ = (Index("ix_recommendation_sessions_user_generated", "user_id", "generated_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)

    agent_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_strategy: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    def __repr__(self) -> str:
        return f"<RecommendationSession user_id={self.user_id} at={self.generated_at}>"
