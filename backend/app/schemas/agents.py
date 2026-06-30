"""
Phase 4 — Pydantic schemas for the agentic workflow layer.

Mirrors the conventions of app/schemas/memory.py: kept in its own module
and re-exported from app/schemas/__init__.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ── Requests ────────────────────────────────────────────────────────────


class AgentRunRequest(BaseModel):
    cf_handle: str = Field(..., min_length=1, max_length=100)


# ── Analyzer Agent ──────────────────────────────────────────────────────


class AnalyzerOutput(BaseModel):
    """Shape returned by the Analyzer Agent node (matches PHASE 4 spec)."""

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    priority_topics: list[str] = Field(default_factory=list)
    improvement_velocity: float = 0.0
    analysis_summary: str = ""


class AnalysisSnapshotRead(BaseModel):
    id: int
    user_id: int
    agent_run_id: Optional[int] = None
    strengths: Optional[list] = None
    weaknesses: Optional[list] = None
    priority_topics: Optional[list] = None
    improvement_velocity: Optional[float] = None
    analysis_summary: Optional[str] = None
    raw_output: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Planner Agent ───────────────────────────────────────────────────────


class PlannerOutputSchema(BaseModel):
    """Shape returned by the Planner Agent node (matches PHASE 4 spec)."""

    study_plan: dict[str, Any] = Field(default_factory=dict)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    weekly_schedule: list[dict[str, Any]] = Field(default_factory=list)
    priority_topics: list[str] = Field(default_factory=list)
    estimated_duration: str = ""


class PlannerOutputRead(BaseModel):
    id: int
    user_id: int
    agent_run_id: Optional[int] = None
    analysis_snapshot_id: Optional[int] = None
    study_plan: Optional[dict] = None
    milestones: Optional[list] = None
    weekly_schedule: Optional[list] = None
    priority_topics: Optional[list] = None
    estimated_duration: Optional[str] = None
    raw_output: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Recommender Agent (Phase 5) ───────────────────────────────────────


class RecommendedProblemItem(BaseModel):
    contest_id: Optional[int] = None
    index: str
    problem_name: str
    rating: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    recommendation_type: str
    recommendation_score: float = 0.0
    recommendation_reason: Optional[str] = None
    difficulty_match_score: Optional[float] = None
    estimated_solve_minutes: Optional[int] = None
    url: Optional[str] = None


class RecommenderOutput(BaseModel):
    recommendations: list[RecommendedProblemItem] = Field(default_factory=list)
    strategy: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""


# ── Orchestrator / runs ─────────────────────────────────────────────────


class AgentRunRead(BaseModel):
    id: int
    user_id: int
    cf_handle: str
    run_type: str
    status: str
    thread_id: str
    error: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    model_config = {"from_attributes": True}


class AgentTraceRead(BaseModel):
    id: int
    agent_run_id: int
    step_index: int
    node_name: str
    status: str
    input_summary: Optional[dict] = None
    output_summary: Optional[dict] = None
    tool_calls: Optional[list] = None
    error: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    model_config = {"from_attributes": True}


class AgentRunResult(BaseModel):
    """Full result of an orchestrator run — what POST /agents/run returns."""

    run: AgentRunRead
    traces: list[AgentTraceRead]
    analysis: Optional[AnalyzerOutput] = None
    plan: Optional[PlannerOutputSchema] = None
    recommendations: Optional[RecommenderOutput] = None


class AgentHistoryEntry(BaseModel):
    run: AgentRunRead
    analysis_summary: Optional[str] = None
    estimated_duration: Optional[str] = None
