"""phase3 memory infrastructure

Revision ID: 0001_phase3_memory
Revises:
Create Date: 2026-06-30

Creates the persistent memory & user modeling tables for Phase 3:
user_profiles, topic_ratings, learning_paths, study_sessions,
learning_milestones, session_memories, agent_checkpoints,
recommendations, progress_snapshots, user_preferences.

Assumes the Phase 1/2 `users` and `chat_sessions` tables already exist
(created via Base.metadata.create_all during earlier phases). If running
against a fresh database that has never been initialized, run the app
once first (it calls init_db() on startup) or create those tables via
an earlier baseline migration before applying this one.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_phase3_memory"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("goals", sa.JSON(), nullable=True),
        sa.Column("strengths", sa.JSON(), nullable=True),
        sa.Column("weaknesses", sa.JSON(), nullable=True),
        sa.Column("current_streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_practice_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("improvement_velocity", sa.Float(), nullable=True),
        sa.Column("historical_recommendation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("session_summaries", sa.JSON(), nullable=True),
        sa.Column("contest_history_snapshots", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "topic_ratings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("problems_solved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("problems_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_strength", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_weakness", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "topic", name="uq_topic_ratings_user_topic"),
    )
    op.create_index("ix_topic_ratings_user_topic", "topic_ratings", ["user_id", "topic"])

    op.create_table(
        "learning_paths",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("goal", sa.String(length=300), nullable=True),
        sa.Column("current_stage", sa.String(length=200), nullable=True),
        sa.Column("progress_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("topic", sa.String(length=100), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("problems_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("problems_solved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "learning_milestones",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("milestone_type", sa.String(length=100), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("achieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "session_memories",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("session_id", sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("conversation_history", sa.JSON(), nullable=True),
        sa.Column("current_goals", sa.JSON(), nullable=True),
        sa.Column("current_problems", sa.JSON(), nullable=True),
        sa.Column("topics_discussed", sa.JSON(), nullable=True),
        sa.Column("agent_state", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "agent_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("thread_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("checkpoint_id", sa.String(length=100), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("checkpoint_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("thread_id", "checkpoint_id", name="uq_agent_checkpoints_thread_checkpoint"),
    )

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rec_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "progress_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("solved_count", sa.Integer(), nullable=True),
        sa.Column("topic_ratings", sa.JSON(), nullable=True),
        sa.Column("weak_topics", sa.JSON(), nullable=True),
        sa.Column("strong_topics", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("preferred_difficulty", sa.String(length=50), nullable=True),
        sa.Column("preferred_topics", sa.JSON(), nullable=True),
        sa.Column("daily_goal_minutes", sa.Integer(), nullable=True),
        sa.Column("notification_settings", sa.JSON(), nullable=True),
        sa.Column("theme", sa.String(length=30), nullable=True, server_default="dark"),
        sa.Column("language", sa.String(length=30), nullable=True, server_default="en"),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_table("progress_snapshots")
    op.drop_table("recommendations")
    op.drop_table("agent_checkpoints")
    op.drop_table("session_memories")
    op.drop_table("learning_milestones")
    op.drop_table("study_sessions")
    op.drop_table("learning_paths")
    op.drop_index("ix_topic_ratings_user_topic", table_name="topic_ratings")
    op.drop_table("topic_ratings")
    op.drop_table("user_profiles")
