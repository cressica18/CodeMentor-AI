"""Phase 5 — Pydantic schemas for the /recommendations API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GenerateRecommendationsRequest(BaseModel):
    cf_handle: str = Field(..., min_length=1, max_length=100)


class RecommendedProblemRead(BaseModel):
    id: int
    user_id: int
    recommendation_session_id: Optional[int] = None
    contest_id: Optional[int] = None
    index: str
    problem_name: str
    rating: Optional[int] = None
    tags: Optional[list] = None
    recommendation_type: str
    recommendation_score: float
    recommendation_reason: Optional[str] = None
    difficulty_match_score: Optional[float] = None
    estimated_solve_minutes: Optional[int] = None
    url: Optional[str] = None
    solved: bool
    attempted: bool
    skipped: bool
    bookmarked: bool
    recommended_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProblemActionRequest(BaseModel):
    action: str = Field(..., pattern="^(solve|skip|bookmark|unbookmark|attempt)$")
    time_spent_minutes: Optional[int] = None
