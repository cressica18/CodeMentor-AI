"""phase5 problem recommendation engine

Revision ID: 0003_phase5_recommendations
Revises: 0002_phase4_agents
Create Date: 2026-06-30

Creates the Phase 5 tables backing the Problem Recommender Agent:
recommendation_sessions, recommended_problems, problem_attempts.

Assumes Phase 1-4 tables (users, agent_runs, ...) already exist.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_phase5_recommendations"
down_revision = "0002_phase4_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_run_id", sa.Integer(), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_reasoning", sa.Text(), nullable=True),
        sa.Column("recommendation_strategy", sa.JSON(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_recommendation_sessions_user_generated", "recommendation_sessions", ["user_id", "generated_at"]
    )

    op.create_table(
        "recommended_problems",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "recommendation_session_id",
            sa.Integer(),
            sa.ForeignKey("recommendation_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("contest_id", sa.Integer(), nullable=True),
        sa.Column("index", sa.String(length=10), nullable=False),
        sa.Column("problem_name", sa.String(length=300), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("recommendation_type", sa.String(length=30), nullable=False, server_default="reinforcement"),
        sa.Column("recommendation_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("recommendation_reason", sa.Text(), nullable=True),
        sa.Column("difficulty_match_score", sa.Float(), nullable=True),
        sa.Column("estimated_solve_minutes", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(length=300), nullable=True),
        sa.Column("solved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("skipped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bookmarked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recommended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "contest_id", "index", "recommendation_session_id",
            name="uq_recommended_problems_user_problem_session",
        ),
    )
    op.create_index("ix_recommended_problems_user_created", "recommended_problems", ["user_id", "recommended_at"])

    op.create_table(
        "problem_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "recommended_problem_id",
            sa.Integer(),
            sa.ForeignKey("recommended_problems.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("contest_id", sa.Integer(), nullable=True),
        sa.Column("index", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="attempted"),
        sa.Column("time_spent_minutes", sa.Integer(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_problem_attempts_user_problem", "problem_attempts", ["user_id", "contest_id", "index"])


def downgrade() -> None:
    op.drop_index("ix_problem_attempts_user_problem", table_name="problem_attempts")
    op.drop_table("problem_attempts")

    op.drop_index("ix_recommended_problems_user_created", table_name="recommended_problems")
    op.drop_table("recommended_problems")

    op.drop_index("ix_recommendation_sessions_user_generated", table_name="recommendation_sessions")
    op.drop_table("recommendation_sessions")
