"""phase4 agentic workflow infrastructure

Revision ID: 0002_phase4_agents
Revises: 0001_phase3_memory
Create Date: 2026-06-30

Creates the agentic workflow tables for Phase 4: agent_runs,
agent_traces, analysis_snapshots, planner_outputs, graph_checkpoints.

Assumes Phase 1-3 tables (users, chat_sessions, and the Phase 3 memory
tables) already exist.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_phase4_agents"
down_revision = "0001_phase3_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("cf_handle", sa.String(length=100), nullable=False, index=True),
        sa.Column("run_type", sa.String(length=30), nullable=False, server_default="full"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("thread_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_agent_runs_user_started", "agent_runs", ["user_id", "started_at"])

    op.create_table(
        "agent_traces",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("agent_run_id", sa.Integer(), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="completed"),
        sa.Column("input_summary", sa.JSON(), nullable=True),
        sa.Column("output_summary", sa.JSON(), nullable=True),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_agent_traces_run_step", "agent_traces", ["agent_run_id", "step_index"])

    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_run_id", sa.Integer(), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("strengths", sa.JSON(), nullable=True),
        sa.Column("weaknesses", sa.JSON(), nullable=True),
        sa.Column("priority_topics", sa.JSON(), nullable=True),
        sa.Column("improvement_velocity", sa.Float(), nullable=True),
        sa.Column("analysis_summary", sa.Text(), nullable=True),
        sa.Column("raw_output", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_index("ix_analysis_snapshots_user_created", "analysis_snapshots", ["user_id", "created_at"])

    op.create_table(
        "planner_outputs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_run_id", sa.Integer(), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("analysis_snapshot_id", sa.Integer(), sa.ForeignKey("analysis_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("study_plan", sa.JSON(), nullable=True),
        sa.Column("milestones", sa.JSON(), nullable=True),
        sa.Column("weekly_schedule", sa.JSON(), nullable=True),
        sa.Column("priority_topics", sa.JSON(), nullable=True),
        sa.Column("estimated_duration", sa.String(length=100), nullable=True),
        sa.Column("raw_output", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_index("ix_planner_outputs_user_created", "planner_outputs", ["user_id", "created_at"])

    op.create_table(
        "graph_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("thread_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("agent_run_id", sa.Integer(), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_graph_checkpoints_thread_step", "graph_checkpoints", ["thread_id", "step_index"])


def downgrade() -> None:
    op.drop_index("ix_graph_checkpoints_thread_step", table_name="graph_checkpoints")
    op.drop_table("graph_checkpoints")

    op.drop_index("ix_planner_outputs_user_created", table_name="planner_outputs")
    op.drop_table("planner_outputs")

    op.drop_index("ix_analysis_snapshots_user_created", table_name="analysis_snapshots")
    op.drop_table("analysis_snapshots")

    op.drop_index("ix_agent_traces_run_step", table_name="agent_traces")
    op.drop_table("agent_traces")

    op.drop_index("ix_agent_runs_user_started", table_name="agent_runs")
    op.drop_table("agent_runs")
