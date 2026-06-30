"""
MemoryService — Phase 3 retrieval/update layer for persistent memory.

This is the single point of access future agents (Orchestrator, Analyzer,
Planner, Recommender, Explainer, Reflection — none implemented yet) will
use to read and write a user's long-term memory, session memory, and
learning history. Keeping all access behind this service means agent
code in later phases never needs to touch SQLAlchemy directly.

No agent / LLM / LangGraph logic lives here — this is pure persistence
and retrieval, by design (see Phase 3 objective).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import User
from app.models.session import ChatSession
from app.models.memory import (
    UserProfile,
    TopicRating,
    LearningPath,
    StudySession,
    LearningMilestone,
    SessionMemory,
    Recommendation,
    ProgressSnapshot,
    UserPreference,
)

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryNotFoundError(Exception):
    """Raised when a required memory record does not exist."""


class MemoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    async def _get_user_by_handle(self, cf_handle: str) -> User:
        result = await self._db.execute(select(User).where(User.cf_handle == cf_handle))
        user = result.scalar_one_or_none()
        if not user:
            raise MemoryNotFoundError(f"No user found for cf_handle={cf_handle!r}")
        return user

    # ──────────────────────────────────────────────────────────────────
    # User profile (long-term)
    # ──────────────────────────────────────────────────────────────────

    async def get_or_create_profile(self, cf_handle: str) -> UserProfile:
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = UserProfile(user_id=user.id)
            self._db.add(profile)
            await self._db.commit()
            await self._db.refresh(profile)
        return profile

    async def update_profile(self, cf_handle: str, **fields) -> UserProfile:
        profile = await self.get_or_create_profile(cf_handle)
        for key, value in fields.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(profile)
        return profile

    async def touch_streak(self, cf_handle: str) -> UserProfile:
        """Update streak counters; call once per day a user is active."""
        profile = await self.get_or_create_profile(cf_handle)
        today = _utcnow().date()
        last = profile.last_practice_date.date() if profile.last_practice_date else None

        if last == today:
            pass  # already counted today
        elif last is not None and (today - last).days == 1:
            profile.current_streak_days += 1
        else:
            profile.current_streak_days = 1

        profile.longest_streak_days = max(profile.longest_streak_days, profile.current_streak_days)
        profile.last_practice_date = _utcnow()
        await self._db.commit()
        await self._db.refresh(profile)
        return profile

    async def append_session_summary(self, cf_handle: str, summary: str, max_keep: int = 20) -> UserProfile:
        profile = await self.get_or_create_profile(cf_handle)
        summaries = list(profile.session_summaries or [])
        summaries.append({"summary": summary, "ts": _utcnow().isoformat()})
        profile.session_summaries = summaries[-max_keep:]
        await self._db.commit()
        await self._db.refresh(profile)
        return profile

    # ──────────────────────────────────────────────────────────────────
    # Topic ratings (long-term)
    # ──────────────────────────────────────────────────────────────────

    async def get_topic_ratings(self, cf_handle: str) -> list[TopicRating]:
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(
            select(TopicRating).where(TopicRating.user_id == user.id).order_by(TopicRating.topic)
        )
        return list(result.scalars().all())

    async def upsert_topic_rating(
        self,
        cf_handle: str,
        topic: str,
        rating: Optional[float] = None,
        solved: bool = False,
        failed: bool = False,
        weak_threshold: float = 0.4,
        strong_threshold: float = 0.75,
    ) -> TopicRating:
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(
            select(TopicRating).where(TopicRating.user_id == user.id, TopicRating.topic == topic)
        )
        tr = result.scalar_one_or_none()
        if tr is None:
            tr = TopicRating(
                user_id=user.id, topic=topic, rating=rating or 0.0, problems_solved=0, problems_failed=0
            )
            self._db.add(tr)

        if rating is not None:
            tr.rating = rating
        if solved:
            tr.problems_solved += 1
            tr.last_practiced_at = _utcnow()
        if failed:
            tr.problems_failed += 1
            tr.last_practiced_at = _utcnow()

        tr.is_weakness = tr.rating < weak_threshold
        tr.is_strength = tr.rating >= strong_threshold

        await self._db.commit()
        await self._db.refresh(tr)
        return tr

    # ──────────────────────────────────────────────────────────────────
    # Learning path (long-term)
    # ──────────────────────────────────────────────────────────────────

    async def get_or_create_learning_path(self, cf_handle: str) -> LearningPath:
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(select(LearningPath).where(LearningPath.user_id == user.id))
        path = result.scalar_one_or_none()
        if path is None:
            path = LearningPath(user_id=user.id, state={})
            self._db.add(path)
            await self._db.commit()
            await self._db.refresh(path)
        return path

    async def update_learning_path(self, cf_handle: str, **fields) -> LearningPath:
        path = await self.get_or_create_learning_path(cf_handle)
        for key, value in fields.items():
            if value is not None and hasattr(path, key):
                setattr(path, key, value)
        path.updated_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(path)
        return path

    # ──────────────────────────────────────────────────────────────────
    # Study sessions / learning history
    # ──────────────────────────────────────────────────────────────────

    async def create_study_session(self, cf_handle: str, **fields) -> StudySession:
        user = await self._get_user_by_handle(cf_handle)
        session = StudySession(user_id=user.id, **fields)
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def end_study_session(self, session_id: int) -> StudySession:
        result = await self._db.execute(select(StudySession).where(StudySession.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise MemoryNotFoundError(f"No study session with id={session_id}")
        session.ended_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_study_sessions(self, cf_handle: str, limit: int = 50) -> list[StudySession]:
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(
            select(StudySession)
            .where(StudySession.user_id == user.id)
            .order_by(desc(StudySession.started_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────────────────────────────
    # Learning milestones
    # ──────────────────────────────────────────────────────────────────

    async def create_milestone(self, cf_handle: str, **fields) -> LearningMilestone:
        user = await self._get_user_by_handle(cf_handle)
        milestone = LearningMilestone(user_id=user.id, **fields)
        self._db.add(milestone)
        await self._db.commit()
        await self._db.refresh(milestone)
        return milestone

    async def get_milestones(self, cf_handle: str, limit: int = 50) -> list[LearningMilestone]:
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(
            select(LearningMilestone)
            .where(LearningMilestone.user_id == user.id)
            .order_by(desc(LearningMilestone.achieved_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────────────────────────────
    # Session memory (short-term)
    # ──────────────────────────────────────────────────────────────────

    async def get_or_create_session_memory(self, session_id: str, cf_handle: Optional[str] = None) -> SessionMemory:
        result = await self._db.execute(select(SessionMemory).where(SessionMemory.session_id == session_id))
        mem = result.scalar_one_or_none()
        if mem is None:
            user_id = None
            if cf_handle:
                user = await self._get_user_by_handle(cf_handle)
                user_id = user.id
            mem = SessionMemory(session_id=session_id, user_id=user_id)
            self._db.add(mem)
            await self._db.commit()
            await self._db.refresh(mem)
        return mem

    async def update_session_memory(self, session_id: str, **fields) -> SessionMemory:
        mem = await self.get_or_create_session_memory(session_id)
        for key, value in fields.items():
            if value is not None and hasattr(mem, key):
                setattr(mem, key, value)
        mem.updated_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(mem)
        return mem

    async def append_message(self, session_id: str, role: str, content: str, max_keep: int = 200) -> SessionMemory:
        mem = await self.get_or_create_session_memory(session_id)
        history = list(mem.conversation_history or [])
        history.append({"role": role, "content": content, "ts": _utcnow().isoformat()})
        mem.conversation_history = history[-max_keep:]
        await self._db.commit()
        await self._db.refresh(mem)
        return mem

    async def save_session_summary(self, session_id: str, summary: str) -> ChatSession:
        """Persist a generated summary onto the long-lived ChatSession row."""
        result = await self._db.execute(select(ChatSession).where(ChatSession.session_id == session_id))
        chat_session = result.scalar_one_or_none()
        if chat_session is None:
            raise MemoryNotFoundError(f"No chat session with session_id={session_id!r}")
        chat_session.summary = summary
        chat_session.updated_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(chat_session)
        return chat_session

    async def get_chat_sessions(self, cf_handle: str, limit: int = 50) -> list[ChatSession]:
        """List long-lived chat sessions for a user — powers the Session History page."""
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────────────────────────────
    # Recommendations
    # ──────────────────────────────────────────────────────────────────

    async def create_recommendation(self, cf_handle: str, **fields) -> Recommendation:
        user = await self._get_user_by_handle(cf_handle)
        rec = Recommendation(user_id=user.id, **fields)
        self._db.add(rec)
        await self._db.commit()
        await self._db.refresh(rec)

        # keep the profile's historical counter in sync
        profile = await self.get_or_create_profile(cf_handle)
        profile.historical_recommendation_count += 1
        await self._db.commit()

        return rec

    async def get_recommendations(self, cf_handle: str, status: Optional[str] = None, limit: int = 50) -> list[Recommendation]:
        user = await self._get_user_by_handle(cf_handle)
        stmt = select(Recommendation).where(Recommendation.user_id == user.id)
        if status:
            stmt = stmt.where(Recommendation.status == status)
        stmt = stmt.order_by(desc(Recommendation.created_at)).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_recommendation_status(self, recommendation_id: int, status: str) -> Recommendation:
        result = await self._db.execute(select(Recommendation).where(Recommendation.id == recommendation_id))
        rec = result.scalar_one_or_none()
        if not rec:
            raise MemoryNotFoundError(f"No recommendation with id={recommendation_id}")
        rec.status = status
        rec.updated_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(rec)
        return rec

    # ──────────────────────────────────────────────────────────────────
    # Progress snapshots + improvement velocity
    # ──────────────────────────────────────────────────────────────────

    async def create_progress_snapshot(self, cf_handle: str, **fields) -> ProgressSnapshot:
        user = await self._get_user_by_handle(cf_handle)
        snapshot = ProgressSnapshot(user_id=user.id, **fields)
        self._db.add(snapshot)
        await self._db.commit()
        await self._db.refresh(snapshot)

        await self._recompute_improvement_velocity(cf_handle)
        return snapshot

    async def get_progress_snapshots(self, cf_handle: str, limit: int = 100) -> list[ProgressSnapshot]:
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(
            select(ProgressSnapshot)
            .where(ProgressSnapshot.user_id == user.id)
            .order_by(desc(ProgressSnapshot.snapshot_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _recompute_improvement_velocity(self, cf_handle: str) -> Optional[float]:
        """
        Improvement velocity = rating delta per day, derived from the two
        most recent snapshots. Cached onto UserProfile for cheap reads.
        """
        snapshots = await self.get_progress_snapshots(cf_handle, limit=2)
        if len(snapshots) < 2:
            return None

        newest, prev = snapshots[0], snapshots[1]
        if newest.rating is None or prev.rating is None:
            return None

        def _aware(dt: datetime) -> datetime:
            # Some DB backends (notably SQLite) don't preserve tzinfo even
            # on `DateTime(timezone=True)` columns, returning naive
            # datetimes. Normalize to UTC-aware so subtraction is safe
            # regardless of backend.
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

        days = max((_aware(newest.snapshot_at) - _aware(prev.snapshot_at)).total_seconds() / 86400.0, 1e-6)
        velocity = (newest.rating - prev.rating) / days

        profile = await self.get_or_create_profile(cf_handle)
        profile.improvement_velocity = velocity
        await self._db.commit()
        return velocity

    # ──────────────────────────────────────────────────────────────────
    # User preferences
    # ──────────────────────────────────────────────────────────────────

    async def get_or_create_preferences(self, cf_handle: str) -> UserPreference:
        user = await self._get_user_by_handle(cf_handle)
        result = await self._db.execute(select(UserPreference).where(UserPreference.user_id == user.id))
        prefs = result.scalar_one_or_none()
        if prefs is None:
            prefs = UserPreference(user_id=user.id)
            self._db.add(prefs)
            await self._db.commit()
            await self._db.refresh(prefs)
        return prefs

    async def update_preferences(self, cf_handle: str, **fields) -> UserPreference:
        prefs = await self.get_or_create_preferences(cf_handle)
        for key, value in fields.items():
            if value is not None and hasattr(prefs, key):
                setattr(prefs, key, value)
        prefs.updated_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(prefs)
        return prefs

    # ──────────────────────────────────────────────────────────────────
    # Chat sessions (long-lived; powers Learning History "Chat Sessions")
    # ──────────────────────────────────────────────────────────────────

    async def get_or_create_chat_session(self, session_id: str, cf_handle: str) -> ChatSession:
        """Get the persisted ChatSession row for session_id, creating it if missing.

        This is the piece that was previously skipped entirely — Phase 1's
        chat stub never wrote a row, so `chat_sessions` (and therefore the
        Learning History "Chat Sessions" panel) stayed empty no matter how
        many messages were sent.
        """
        result = await self._db.execute(select(ChatSession).where(ChatSession.session_id == session_id))
        chat_session = result.scalar_one_or_none()
        if chat_session is not None:
            return chat_session

        user = await self._get_user_by_handle(cf_handle)
        chat_session = ChatSession(user_id=user.id, session_id=session_id, messages=[])
        self._db.add(chat_session)
        await self._db.commit()
        await self._db.refresh(chat_session)
        return chat_session

    async def append_chat_message(self, session_id: str, cf_handle: str, role: str, content: str) -> ChatSession:
        """Append a message onto the long-lived ChatSession row (distinct from
        the short-term `SessionMemory.conversation_history` buffer)."""
        chat_session = await self.get_or_create_chat_session(session_id, cf_handle)
        messages = list(chat_session.messages or [])
        messages.append({"role": role, "content": content, "ts": _utcnow().isoformat()})
        chat_session.messages = messages
        chat_session.updated_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(chat_session)
        return chat_session

    # ──────────────────────────────────────────────────────────────────
    # Sync helpers — bridge Analyzer/Planner agent output onto the
    # long-term `topic_ratings` / `learning_milestones` tables.
    #
    # These were the core missing wiring: the Analyzer and Planner agents
    # always *computed* strengths/weaknesses/milestones correctly, but
    # nothing ever called `upsert_topic_rating` / `create_milestone` with
    # that output, so the tables stayed at 0 rows forever.
    # ──────────────────────────────────────────────────────────────────

    async def sync_topic_ratings_from_analysis(self, cf_handle: str, analysis: dict) -> list[TopicRating]:
        """Persist/update one TopicRating row per topic the Analyzer Agent
        scored, using its confidence scores plus strength/weakness flags."""
        confidence_scores: dict = (analysis.get("_extra") or {}).get("topic_confidence_scores") or {}
        strengths = set(analysis.get("strengths") or [])
        weaknesses = set(analysis.get("weaknesses") or [])

        topics = set(confidence_scores) | strengths | weaknesses
        rows: list[TopicRating] = []
        for topic in topics:
            rating = confidence_scores.get(topic)
            row = await self.upsert_topic_rating(
                cf_handle,
                topic=topic,
                rating=rating,
                weak_threshold=0.4,
                strong_threshold=0.75,
            )
            # Confidence score alone may sit just outside the default
            # thresholds for a topic the Analyzer explicitly flagged —
            # honor the agent's explicit call over the threshold heuristic.
            if topic in weaknesses:
                row.is_weakness = True
            if topic in strengths:
                row.is_strength = True
            rows.append(row)

        if rows:
            await self._db.commit()
            for row in rows:
                await self._db.refresh(row)
        return rows

    async def sync_milestones_from_plan(self, cf_handle: str, milestones: list[dict]) -> list[LearningMilestone]:
        """Persist a LearningMilestone row for each milestone the Planner
        Agent generated, skipping ones already recorded (matched by title)
        so re-running the workflow doesn't duplicate rows."""
        if not milestones:
            return []

        existing = await self.get_milestones(cf_handle, limit=500)
        existing_titles = {m.title for m in existing}

        created: list[LearningMilestone] = []
        for m in milestones:
            title = m.get("title")
            if not title or title in existing_titles:
                continue
            milestone = await self.create_milestone(
                cf_handle,
                title=title,
                description=m.get("goal") or f"Planner-generated milestone for topic '{m.get('topic')}'",
                milestone_type=m.get("type"),
                extra_data={
                    "ordering": m.get("order"),
                    "topic": m.get("topic"),
                    "target_problems_solved": m.get("target_problems_solved"),
                    "problems_solved": 0,
                    "completed": False,
                },
            )
            created.append(milestone)
            existing_titles.add(title)
        return created

    async def advance_milestone_progress(self, cf_handle: str, topic: str | None) -> list[LearningMilestone]:
        """Called whenever a problem tagged with `topic` is solved — bumps
        progress on any matching, not-yet-completed milestone and marks it
        complete once its target problem count is reached."""
        if not topic:
            return []
        milestones = await self.get_milestones(cf_handle, limit=500)
        updated: list[LearningMilestone] = []
        for m in milestones:
            extra = dict(m.extra_data or {})
            if extra.get("completed") or extra.get("topic") != topic:
                continue
            extra["problems_solved"] = int(extra.get("problems_solved") or 0) + 1
            target = extra.get("target_problems_solved")
            if target and extra["problems_solved"] >= target:
                extra["completed"] = True
                m.achieved_at = _utcnow()
            m.extra_data = extra
            updated.append(m)
        if updated:
            await self._db.commit()
            for m in updated:
                await self._db.refresh(m)
        return updated

    async def record_workflow_session(
        self,
        cf_handle: str,
        session_type: str,
        topic: str | None = None,
        problems_attempted: int = 0,
        problems_solved: int = 0,
        duration_minutes: int | None = None,
        notes: str | None = None,
    ) -> StudySession:
        """Create a `StudySession` row marking that *something* happened —
        a solve/skip action, a recommendation generation, a study-plan
        generation, or a full mentor workflow run. `StudySession` has no
        dedicated `session_type` column, so it's recorded in `notes`
        (prefixed) to stay queryable without altering the schema."""
        tagged_notes = f"[{session_type}]" + (f" {notes}" if notes else "")
        session = await self.create_study_session(
            cf_handle,
            topic=topic,
            duration_minutes=duration_minutes,
            problems_attempted=problems_attempted,
            problems_solved=problems_solved,
            notes=tagged_notes,
            ended_at=_utcnow() if duration_minutes is not None else None,
        )
        return session

    # ──────────────────────────────────────────────────────────────────
    # Aggregate overview (powers the frontend memory visualization panels)
    # ──────────────────────────────────────────────────────────────────

    async def get_overview(self, cf_handle: str) -> dict:
        profile = await self.get_or_create_profile(cf_handle)
        topic_ratings = await self.get_topic_ratings(cf_handle)
        learning_path = await self.get_or_create_learning_path(cf_handle)
        sessions = await self.get_study_sessions(cf_handle, limit=10)
        recommendations = await self.get_recommendations(cf_handle, limit=10)
        milestones = await self.get_milestones(cf_handle, limit=10)
        snapshots = await self.get_progress_snapshots(cf_handle, limit=30)
        preferences = await self.get_or_create_preferences(cf_handle)

        return {
            "profile": profile,
            "topic_ratings": topic_ratings,
            "learning_path": learning_path,
            "recent_sessions": sessions,
            "recent_recommendations": recommendations,
            "recent_milestones": milestones,
            "progress_snapshots": snapshots,
            "preferences": preferences,
        }