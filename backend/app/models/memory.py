"""
Phase 3 — Persistent Memory & User Modeling Layer.

This module defines the database tables that back the long-term memory,
short-term (session) memory, and learning-history subsystems described
in the CodeMentor AI architecture document.

These tables are intentionally agent-agnostic: they store structured
state that the future Orchestrator / Analyzer / Planner / Recommender /
Explainer / Reflection agents will read and write. No agent logic lives
here — this is pure persistence.

──────────────────────────────────────────────────────────────────────
LangGraph integration notes (future phases)
──────────────────────────────────────────────────────────────────────
- `SessionMemory` rows are the natural backing store for LangGraph's
  short-term / thread-scoped state. When LangGraph is introduced, a
  `LangGraphCheckpointSaver` implementation can read/write the
  `agent_state` JSON column keyed by `session_id` (== LangGraph
  `thread_id`).
- `UserProfile` + `TopicRating` + `LearningPath` form the long-term
  memory store. A future LangGraph "store" (cross-thread memory) can
  be backed directly by `MemoryService` methods in
  `app/services/memory_service.py`.
- `AgentCheckpoint` below is a forward-looking table for raw
  LangGraph checkpoint blobs once StateGraph workflows are introduced
  in a later phase. It is unused by any agent today.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────
# Long-term memory: user profile
# ──────────────────────────────────────────────────────────────────────────


class UserProfile(Base):
    """
    Extended, agent-facing profile for a user.

    Kept separate from `User` (Phase 1/2) so that Phase 1/2 code paths
    remain untouched. `User` stays the identity + raw CF analytics
    record; `UserProfile` is the mentor's "model of the student".
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-form learning goals, e.g. {"target_rating": 1900, "target_date": "2026-12-01"}
    goals: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Denormalized strengths/weaknesses (topic-level detail lives in TopicRating)
    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    weaknesses: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Streak tracking
    current_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_practice_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Improvement velocity = rating delta per unit time, computed from
    # ProgressSnapshot history. Cached here for cheap dashboard reads.
    improvement_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Stored recommendations summary / historical recommendation count
    historical_recommendation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Rolling list of session summaries (most recent N); full history
    # lives in ChatSession.summary per-row, this is a fast-access cache.
    session_summaries: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Snapshots of contest history at points in time (lightweight; full
    # contest detail comes from the Codeforces ingestion pipeline).
    contest_history_snapshots: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", backref="profile", uselist=False)

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id}>"


# ──────────────────────────────────────────────────────────────────────────
# Long-term memory: per-topic skill ratings
# ──────────────────────────────────────────────────────────────────────────


class TopicRating(Base):
    """Skill rating for a single (user, topic) pair — e.g. 'dp', 'graphs'."""

    __tablename__ = "topic_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_topic_ratings_user_topic"),
        Index("ix_topic_ratings_user_topic", "user_id", "topic"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    topic: Mapped[str] = mapped_column(String(100), nullable=False)

    # Normalized skill score, e.g. 0.0–1.0
    rating: Mapped[float] = mapped_column(Float, default=0.0)

    problems_solved: Mapped[int] = mapped_column(Integer, default=0)
    problems_failed: Mapped[int] = mapped_column(Integer, default=0)

    is_strength: Mapped[bool] = mapped_column(Boolean, default=False)
    is_weakness: Mapped[bool] = mapped_column(Boolean, default=False)

    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<TopicRating user_id={self.user_id} topic={self.topic} rating={self.rating}>"


# ──────────────────────────────────────────────────────────────────────────
# Long-term memory: learning path state
# ──────────────────────────────────────────────────────────────────────────


class LearningPath(Base):
    """
    Current adaptive learning path state for a user.

    `state` holds the full path graph/sequence (format owned by the
    future Planner Agent); this table only persists it.
    """

    __tablename__ = "learning_paths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    goal: Mapped[str | None] = mapped_column(String(300), nullable=True)
    current_stage: Mapped[str | None] = mapped_column(String(200), nullable=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Full path state — stages, prerequisites, target topics, etc.
    state: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<LearningPath user_id={self.user_id} stage={self.current_stage}>"


# ──────────────────────────────────────────────────────────────────────────
# Learning history: study sessions
# ──────────────────────────────────────────────────────────────────────────


class StudySession(Base):
    """A discrete study/practice session (distinct from a chat session)."""

    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    problems_attempted: Mapped[int] = mapped_column(Integer, default=0)
    problems_solved: Mapped[int] = mapped_column(Integer, default=0)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def __repr__(self) -> str:
        return f"<StudySession id={self.id} user_id={self.user_id} topic={self.topic}>"


class LearningMilestone(Base):
    """A discrete achievement / milestone in a user's learning journey."""

    __tablename__ = "learning_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    milestone_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    achieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def __repr__(self) -> str:
        return f"<LearningMilestone id={self.id} title={self.title}>"


# ──────────────────────────────────────────────────────────────────────────
# Short-term memory: per chat-session working memory
# ──────────────────────────────────────────────────────────────────────────


class SessionMemory(Base):
    """
    Short-term / working memory scoped to a single chat session.

    One row per `session_id` (matches `ChatSession.session_id`). This
    is the table future LangGraph thread-scoped checkpointing will
    read from / write to (see module docstring).
    """

    __tablename__ = "session_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Rolling conversation buffer: list[{"role": ..., "content": ..., "ts": ...}]
    conversation_history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    current_goals: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    current_problems: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    topics_discussed: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Free-form scratch space for whichever agent owns this turn.
    # Future LangGraph nodes can stash intermediate state here.
    agent_state: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<SessionMemory session_id={self.session_id}>"


class AgentCheckpoint(Base):
    """
    Forward-looking table for raw LangGraph checkpoint blobs.

    NOT used by any agent in Phase 3 — no agents exist yet. This table
    exists purely so the schema is ready when LangGraph StateGraph
    workflows + checkpointing are introduced in a later phase. The
    intended usage is a custom `BaseCheckpointSaver` that serializes
    LangGraph's checkpoint object into `checkpoint_data`, keyed by
    (`thread_id`, `checkpoint_id`).
    """

    __tablename__ = "agent_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    checkpoint_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    checkpoint_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("thread_id", "checkpoint_id", name="uq_agent_checkpoints_thread_checkpoint"),
    )

    def __repr__(self) -> str:
        return f"<AgentCheckpoint thread_id={self.thread_id} checkpoint_id={self.checkpoint_id}>"


# ──────────────────────────────────────────────────────────────────────────
# Recommendations (storage only — recommendation logic is a later phase)
# ──────────────────────────────────────────────────────────────────────────


class Recommendation(Base):
    """A stored recommendation (problem, topic, or path) for a user."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    rec_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "problem" | "topic" | "path" | "concept"
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending|accepted|dismissed|completed
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # which future agent generated it

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} type={self.rec_type} status={self.status}>"


# ──────────────────────────────────────────────────────────────────────────
# Progress tracking
# ──────────────────────────────────────────────────────────────────────────


class ProgressSnapshot(Base):
    """Point-in-time snapshot of a user's overall progress."""

    __tablename__ = "progress_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solved_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    topic_ratings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    weak_topics: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    strong_topics: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    def __repr__(self) -> str:
        return f"<ProgressSnapshot user_id={self.user_id} at={self.snapshot_at}>"


# ──────────────────────────────────────────────────────────────────────────
# User preferences
# ──────────────────────────────────────────────────────────────────────────


class UserPreference(Base):
    """User-configurable preferences consumed by future agents/UI."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    preferred_difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_topics: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    daily_goal_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notification_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    theme: Mapped[str | None] = mapped_column(String(30), default="dark")
    language: Mapped[str | None] = mapped_column(String(30), default="en")

    # Catch-all for anything not yet modeled explicitly.
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id}>"
