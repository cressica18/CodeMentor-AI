"""
Phase 3 — Pydantic schemas for the persistent memory & user modeling layer.

Kept in a dedicated module (rather than appended to app/schemas/__init__.py)
to keep the growing memory surface organized. Re-exported from
app/schemas/__init__.py for convenient `from app.schemas import ...` imports.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ── User Profile ─────────────────────────────────────────────────────────


class UserProfileRead(BaseModel):
    id: int
    user_id: int
    bio: Optional[str] = None
    goals: Optional[dict] = None
    strengths: Optional[list] = None
    weaknesses: Optional[list] = None
    current_streak_days: int
    longest_streak_days: int
    last_practice_date: Optional[datetime] = None
    improvement_velocity: Optional[float] = None
    historical_recommendation_count: int
    session_summaries: Optional[list] = None
    contest_history_snapshots: Optional[list] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    bio: Optional[str] = None
    goals: Optional[dict] = None
    strengths: Optional[list] = None
    weaknesses: Optional[list] = None


# ── Topic Ratings ────────────────────────────────────────────────────────


class TopicRatingRead(BaseModel):
    id: int
    user_id: int
    topic: str
    rating: float
    problems_solved: int
    problems_failed: int
    is_strength: bool
    is_weakness: bool
    last_practiced_at: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopicRatingUpsert(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100)
    rating: Optional[float] = None
    solved: bool = False
    failed: bool = False


# ── Learning Path ────────────────────────────────────────────────────────


class LearningPathRead(BaseModel):
    id: int
    user_id: int
    goal: Optional[str] = None
    current_stage: Optional[str] = None
    progress_percent: float
    state: Optional[dict] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class LearningPathUpdate(BaseModel):
    goal: Optional[str] = None
    current_stage: Optional[str] = None
    progress_percent: Optional[float] = None
    state: Optional[dict] = None


# ── Study Sessions ───────────────────────────────────────────────────────


class StudySessionCreate(BaseModel):
    topic: Optional[str] = None
    duration_minutes: Optional[int] = None
    problems_attempted: int = 0
    problems_solved: int = 0
    notes: Optional[str] = None


class StudySessionRead(BaseModel):
    id: int
    user_id: int
    topic: Optional[str] = None
    duration_minutes: Optional[int] = None
    problems_attempted: int
    problems_solved: int
    notes: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Learning Milestones ──────────────────────────────────────────────────


class LearningMilestoneCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    milestone_type: Optional[str] = None
    extra_data: Optional[dict] = None


class LearningMilestoneRead(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    milestone_type: Optional[str] = None
    extra_data: Optional[dict] = None
    achieved_at: datetime

    model_config = {"from_attributes": True}


# ── Session Memory (short-term) ──────────────────────────────────────────


class SessionMemoryRead(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    conversation_history: Optional[list] = None
    current_goals: Optional[list] = None
    current_problems: Optional[list] = None
    topics_discussed: Optional[list] = None
    agent_state: Optional[dict] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionMemoryUpdate(BaseModel):
    current_goals: Optional[list] = None
    current_problems: Optional[list] = None
    topics_discussed: Optional[list] = None
    agent_state: Optional[dict] = None


class SessionMessageAppend(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class SessionSummarySave(BaseModel):
    summary: str


# ── Recommendations ──────────────────────────────────────────────────────


class RecommendationCreate(BaseModel):
    rec_type: str = Field(..., pattern="^(problem|topic|path|concept)$")
    payload: dict
    reason: Optional[str] = None
    source: Optional[str] = None


class RecommendationRead(BaseModel):
    id: int
    user_id: int
    rec_type: str
    payload: dict
    reason: Optional[str] = None
    status: str
    source: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|accepted|dismissed|completed)$")


# ── Progress Snapshots ───────────────────────────────────────────────────


class ProgressSnapshotRead(BaseModel):
    id: int
    user_id: int
    rating: Optional[int] = None
    solved_count: Optional[int] = None
    topic_ratings: Optional[dict] = None
    weak_topics: Optional[list] = None
    strong_topics: Optional[list] = None
    metrics: Optional[dict] = None
    snapshot_at: datetime

    model_config = {"from_attributes": True}


# ── User Preferences ─────────────────────────────────────────────────────


class UserPreferenceRead(BaseModel):
    user_id: int
    preferred_difficulty: Optional[str] = None
    preferred_topics: Optional[list] = None
    daily_goal_minutes: Optional[int] = None
    notification_settings: Optional[dict] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    extra: Optional[dict] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPreferenceUpdate(BaseModel):
    preferred_difficulty: Optional[str] = None
    preferred_topics: Optional[list] = None
    daily_goal_minutes: Optional[int] = None
    notification_settings: Optional[dict] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    extra: Optional[dict] = None


# ── Chat sessions (long-lived, Phase 1/2 ChatSession table) ──────────────


class ChatSessionSummary(BaseModel):
    session_id: str
    user_id: int
    summary: Optional[str] = None
    messages: Optional[list] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Aggregate dashboard payload ──────────────────────────────────────────


class MemoryOverview(BaseModel):
    """One-shot payload for the frontend's memory visualization panels."""

    profile: Optional[UserProfileRead] = None
    topic_ratings: list[TopicRatingRead] = []
    learning_path: Optional[LearningPathRead] = None
    recent_sessions: list[StudySessionRead] = []
    recent_recommendations: list[RecommendationRead] = []
    recent_milestones: list[LearningMilestoneRead] = []
    progress_snapshots: list[ProgressSnapshotRead] = []
    preferences: Optional[UserPreferenceRead] = None
