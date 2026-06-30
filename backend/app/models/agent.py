"""
Phase 4 — Agentic workflow persistence layer.

This module defines the database tables backing the first real LangGraph
workflow: AgentRun / AgentTrace record every orchestrator execution and
its step-by-step trace, AnalysisSnapshot / PlannerOutput persist the
structured output of the Analyzer and Planner agents, and GraphCheckpoint
stores the raw LangGraph state for each completed (or in-progress) run.

As with the Phase 3 memory tables, this is pure persistence — no agent
or LangGraph logic lives here. See app/agents/ for the graph definition
and app/services/agent_service.py for the orchestration + persistence
glue.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Integer,
    Float,
    JSON,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentRun(Base):
    """One end-to-end execution of the LangGraph orchestrator workflow."""

    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_user_started", "user_id", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cf_handle: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # "analyze" | "plan" | "full" (analyze + plan, the default orchestrator run)
    run_type: Mapped[str] = mapped_column(String(30), default="full")

    # "pending" | "running" | "completed" | "failed"
    status: Mapped[str] = mapped_column(String(30), default="pending")

    # LangGraph thread_id for this run — also used as the key for
    # AgentCheckpoint rows (Phase 3 table) and GraphCheckpoint below.
    thread_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<AgentRun id={self.id} cf_handle={self.cf_handle} status={self.status}>"


class AgentTrace(Base):
    """A single node execution within an AgentRun — one row per graph node."""

    __tablename__ = "agent_traces"
    __table_args__ = (Index("ix_agent_traces_run_step", "agent_run_id", "step_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "RetrieveMemory", "AnalyzerAgent"

    # "started" | "completed" | "failed"
    status: Mapped[str] = mapped_column(String(30), default="completed")

    input_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    output_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<AgentTrace run_id={self.agent_run_id} node={self.node_name} step={self.step_index}>"


class AnalysisSnapshot(Base):
    """Persisted output of a single Analyzer Agent execution."""

    __tablename__ = "analysis_snapshots"
    __table_args__ = (Index("ix_analysis_snapshots_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)

    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    weaknesses: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    priority_topics: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    improvement_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full raw analyzer output (superset of the columns above), for
    # forward-compatibility as the Analyzer Agent grows richer fields.
    raw_output: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AnalysisSnapshot id={self.id} user_id={self.user_id}>"


class PlannerOutput(Base):
    """Persisted output of a single Planner Agent execution."""

    __tablename__ = "planner_outputs"
    __table_args__ = (Index("ix_planner_outputs_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    analysis_snapshot_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("analysis_snapshots.id", ondelete="SET NULL"), nullable=True)

    study_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    milestones: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    weekly_schedule: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    priority_topics: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    estimated_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)

    raw_output: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    def __repr__(self) -> str:
        return f"<PlannerOutput id={self.id} user_id={self.user_id}>"


class GraphCheckpoint(Base):
    """
    Raw LangGraph state snapshot for a run, keyed by thread_id.

    Distinct from the Phase 3 `AgentCheckpoint` table (which is a
    forward-looking, unused placeholder for a future custom
    BaseCheckpointSaver). This table is actively written by the Phase 4
    orchestrator after each node transition so the full graph state is
    inspectable via GET /api/v1/agents/traces.
    """

    __tablename__ = "graph_checkpoints"
    __table_args__ = (Index("ix_graph_checkpoints_thread_step", "thread_id", "step_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True)

    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)

    state: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def __repr__(self) -> str:
        return f"<GraphCheckpoint thread_id={self.thread_id} node={self.node_name} step={self.step_index}>"
