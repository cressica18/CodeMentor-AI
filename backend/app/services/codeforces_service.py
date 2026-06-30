"""
CodeforcesService — application-level service layer.

Sits between the API routes and the low-level CF client / analytics
engine.  Responsibilities:
  1. Fetch all raw data from the CF API
  2. Run analytics computations
  3. Persist / update the User record in the database
  4. Return a structured CodeforcesProfile to the route handler

This layer is the natural attachment point for future LangGraph
Analyzer Agent tool calls.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.codeforces.client import CodeforcesClient
from app.codeforces.analytics import build_full_analytics
from app.codeforces.exceptions import CFHandleNotFound, CFAPIError
from app.models.user import User

logger = get_logger(__name__)


class CodeforcesService:
    """
    Orchestrates CF data ingestion for a single handle.

    Usage inside a route:
        async with CodeforcesClient() as cf:
            svc = CodeforcesService(cf, db)
            profile = await svc.ingest_profile("tourist")
    """

    def __init__(self, client: CodeforcesClient, db: AsyncSession) -> None:
        self._cf = client
        self._db = db

    # ── public API ─────────────────────────────────────────────────────────

    async def ingest_profile(self, handle: str) -> dict:
        """
        Full ingestion pipeline:
          1. Fetch user info, rating history, and submissions from CF.
          2. Derive solved problems from submissions.
          3. Compute full analytics.
          4. Upsert the analytics into the User row.
          5. Return the analytics dict (mirrors CFProfileResponse schema).

        Raises:
          CFHandleNotFound  — handle does not exist on Codeforces
          CFAPIError        — upstream API failure
        """
        logger.info("Ingesting CF profile for handle=%s", handle)

        # ── 1. Fetch raw data ──────────────────────────────────────────────
        user_info = await self._cf.get_user_info(handle)
        rating_history = await self._cf.get_rating_history(handle)
        all_submissions = await self._cf.get_submissions(handle)
        solved_problems = await self._cf.get_solved_problems(handle)

        logger.info(
            "Fetched CF data: contests=%d submissions=%d solved=%d",
            len(rating_history),
            len(all_submissions),
            len(solved_problems),
        )

        # ── 2. Compute analytics ───────────────────────────────────────────
        analytics = build_full_analytics(
            user=user_info,
            rating_history=rating_history,
            all_submissions=all_submissions,
            solved_problems=solved_problems,
        )

        # ── 3. Persist to DB ───────────────────────────────────────────────
        await self._upsert_user(handle, analytics)

        return analytics

    async def get_cached_profile(self, handle: str) -> dict | None:
        """
        Return the last-persisted analytics for a handle, or None if the
        user has never been ingested.
        """
        result = await self._db.execute(
            select(User).where(User.cf_handle == handle)
        )
        user: User | None = result.scalar_one_or_none()
        if user is None or user.cf_analytics is None:
            return None
        return user.cf_analytics

    # ── private helpers ────────────────────────────────────────────────────

    async def _upsert_user(self, handle: str, analytics: dict) -> User:
        """
        Create or update the User row with the latest analytics payload.
        """
        result = await self._db.execute(
            select(User).where(User.cf_handle == handle)
        )
        user: User | None = result.scalar_one_or_none()

        if user is None:
            user = User(cf_handle=handle)
            self._db.add(user)
            logger.info("Creating new User row for handle=%s", handle)
        else:
            logger.info("Updating existing User row for handle=%s", handle)

        # Sync profile fields that live as first-class columns
        user.display_name = analytics.get("display_name")
        user.current_rating = analytics.get("current_rating")
        user.max_rating = analytics.get("max_rating")

        # Persist derived weakness/strength lists for future agent use
        user.weak_topics = [
            t["tag"] for t in (analytics.get("weakest_tags") or [])
        ]
        user.topic_ratings = analytics.get("tag_ac_rates", {})

        # Store the full analytics blob for fast cache reads
        user.cf_analytics = analytics

        await self._db.commit()
        await self._db.refresh(user)
        return user
