from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ── Health ─────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    env: str
    llm_provider: str
    database: str
    version: str = "0.1.0"


# ── User ───────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    cf_handle: str = Field(..., min_length=1, max_length=100)


class UserRead(BaseModel):
    id: int
    cf_handle: str
    display_name: Optional[str]
    current_rating: Optional[int]
    max_rating: Optional[int]
    topic_ratings: Optional[dict]
    weak_topics: Optional[list]
    learning_path: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    metadata: Optional[dict] = None


class ChatRequest(BaseModel):
    session_id: str
    cf_handle: str
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage
    agent_trace: Optional[list[dict]] = None
    metadata: Optional[dict] = None


# ── Session ────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    cf_handle: str


class SessionRead(BaseModel):
    session_id: str
    user_id: int
    messages: list[ChatMessage]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generic ────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


# ── Codeforces Phase 2 ─────────────────────────────────────────────────────

class CFIngestRequest(BaseModel):
    """Request body for profile ingestion."""
    cf_handle: str = Field(..., min_length=1, max_length=100)
    force_refresh: bool = Field(
        False,
        description="If True, bypass any cached data and re-fetch from CF API"
    )


class TagStat(BaseModel):
    tag: str
    count: int


class TagACRate(BaseModel):
    tag: str
    acRate: float


class RatingPoint(BaseModel):
    contestId: int
    contest: str
    date: str
    timestamp: int
    oldRating: int
    newRating: int
    delta: int
    rank: int


class DifficultyBucket(BaseModel):
    range: str
    count: int


class HeatmapPoint(BaseModel):
    date: str
    count: int


class CFProfileResponse(BaseModel):
    """Full analytics response returned by POST /codeforces/ingest and GET /codeforces/{handle}."""

    handle: str
    display_name: Optional[str]
    rank: Optional[str]
    max_rank: Optional[str]
    current_rating: Optional[int]
    max_rating: Optional[int]
    country: Optional[str]
    organization: Optional[str]
    avatar: Optional[str]
    contribution: int
    friend_of_count: int
    registered_at: Optional[str]

    contests_participated: int
    solved_count: int

    rating_trend: list[RatingPoint]

    most_solved_tags: list[TagStat]
    tag_solve_counts: dict[str, int]
    weakest_tags: list[TagACRate]
    strongest_tags: list[TagACRate]
    tag_ac_rates: dict[str, float]

    difficulty_distribution: list[DifficultyBucket]
    avg_solved_rating: Optional[int]

    total_submissions: int
    accepted_count: int
    success_rate: float
    verdict_distribution: dict[str, int]
    language_distribution: dict[str, int]

    activity_heatmap: list[HeatmapPoint]


class CFProfileSummary(BaseModel):
    """Lightweight summary — used in handle-lookup endpoints."""
    handle: str
    display_name: Optional[str]
    current_rating: Optional[int]
    max_rating: Optional[int]
    rank: Optional[str]
    solved_count: int
    contests_participated: int
    weakest_tags: list[TagACRate]
    strongest_tags: list[TagACRate]


# ── Phase 3 — Memory layer ───────────────────────────────────────────────
# Re-exported here so existing `from app.schemas import X` imports keep
# working uniformly across the codebase.

from app.schemas.memory import (  # noqa: E402
    UserProfileRead,
    UserProfileUpdate,
    TopicRatingRead,
    TopicRatingUpsert,
    LearningPathRead,
    LearningPathUpdate,
    StudySessionCreate,
    StudySessionRead,
    LearningMilestoneCreate,
    LearningMilestoneRead,
    SessionMemoryRead,
    SessionMemoryUpdate,
    SessionMessageAppend,
    SessionSummarySave,
    RecommendationCreate,
    RecommendationRead,
    RecommendationStatusUpdate,
    ProgressSnapshotRead,
    UserPreferenceRead,
    UserPreferenceUpdate,
    ChatSessionSummary,
    MemoryOverview,
)

from .agents import (
    AgentRunRequest,
    AnalyzerOutput,
    AnalysisSnapshotRead,
    PlannerOutputSchema,
    PlannerOutputRead,
    AgentRunRead,
    AgentTraceRead,
    AgentRunResult,
    AgentHistoryEntry,
    RecommendedProblemItem,
    RecommenderOutput,
)

from .recommendations import (
    GenerateRecommendationsRequest,
    RecommendedProblemRead,
    ProblemActionRequest,
)
