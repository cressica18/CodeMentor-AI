"""
Typed state for the LangGraph workflow.

Graph (Phase 5):

    START -> RetrieveMemory -> AnalyzerAgent -> PlannerAgent -> RecommenderAgent -> PersistMemory -> END

`MentorGraphState` is threaded through every node. Each node reads what
it needs and returns a partial dict of updated keys (standard LangGraph
TypedDict-state convention) — LangGraph merges these into the running
state between node executions.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class MemorySnapshot(TypedDict, total=False):
    """Everything RetrieveMemory pulls from the Phase 3 memory layer."""

    cf_handle: str
    cf_analytics: dict[str, Any]
    profile: dict[str, Any]
    topic_ratings: list[dict[str, Any]]
    learning_path: dict[str, Any]
    recent_study_sessions: list[dict[str, Any]]
    recent_recommendations: list[dict[str, Any]]
    progress_snapshots: list[dict[str, Any]]
    preferences: dict[str, Any]


class AnalyzerResult(TypedDict, total=False):
    strengths: list[str]
    weaknesses: list[str]
    priority_topics: list[str]
    improvement_velocity: float
    analysis_summary: str


class PlannerResult(TypedDict, total=False):
    study_plan: dict[str, Any]
    milestones: list[dict[str, Any]]
    weekly_schedule: list[dict[str, Any]]
    priority_topics: list[str]
    estimated_duration: str


class RecommenderResult(TypedDict, total=False):
    recommendations: list[dict[str, Any]]
    strategy: dict[str, Any]
    reasoning: str


class MentorGraphState(TypedDict, total=False):
    """Full graph state threaded through every node."""

    # ── inputs ──
    cf_handle: str
    thread_id: str
    run_type: str  # "analyze" | "plan" | "full"

    # ── populated by RetrieveMemory ──
    memory: MemorySnapshot

    # ── populated by AnalyzerAgent ──
    analysis: AnalyzerResult

    # ── populated by PlannerAgent ──
    plan: PlannerResult

    # ── populated by RecommenderAgent ──
    recommendations: RecommenderResult

    # ── populated by PersistMemory ──
    persisted: bool

    # ── execution bookkeeping (used for the Agent Trace panel) ──
    trace: list[dict[str, Any]]
    error: Optional[str]
