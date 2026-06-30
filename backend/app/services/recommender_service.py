"""
RecommenderService — Phase 5 I/O + persistence glue for the Problem
Recommender Agent.

Mirrors the AgentService / MemoryService split used in Phase 3/4: all
DB access and external (Codeforces) API calls live here; the pure
recommendation logic lives in `app/agents/recommender.py`.

This is the only place that talks to `ProblemPoolService` (the real
Codeforces problemset cache) and to the user's solved-problem history,
so the Recommender Agent can never fabricate a problem — every
candidate comes from the live CF problem pool.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.recommender import run_recommender_agent
from app.codeforces.client import CodeforcesClient
from app.core.logging import get_logger
from app.models.recommendation_engine import (
    RecommendedProblem,
    ProblemAttempt,
    RecommendationSession,
)
from app.models.user import User
from app.services.memory_service import MemoryNotFoundError, MemoryService
from app.services.problem_pool_service import ProblemPoolService

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RecommenderService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _get_user(self, cf_handle: str) -> User:
        result = await self._db.execute(select(User).where(User.cf_handle == cf_handle))
        user = result.scalar_one_or_none()
        if not user:
            raise MemoryNotFoundError(
                f"No user found for cf_handle={cf_handle!r} - ingest a Codeforces profile first."
            )
        return user

    async def _get_cf_handle_by_user_id(self, user_id: int) -> Optional[str]:
        result = await self._db.execute(select(User.cf_handle).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _get_recent_recommended_keys(self, user_id: int, limit: int = 200) -> set[tuple[int | None, str]]:
        result = await self._db.execute(
            select(RecommendedProblem.contest_id, RecommendedProblem.index)
            .where(RecommendedProblem.user_id == user_id)
            .order_by(desc(RecommendedProblem.recommended_at))
            .limit(limit)
        )
        return {(row[0], row[1]) for row in result.all()}

    async def generate_recommendations(
        self,
        cf_handle: str,
        analysis: dict[str, Any],
        agent_run_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Run the full Phase 5 pipeline for one user:
          1. fetch the real CF problem pool (cached)
          2. fetch the user's real solved problems from Codeforces
          3. compute recommendations via the pure recommender agent
          4. persist a RecommendationSession + RecommendedProblem rows

        Returns the same shape as `run_recommender_agent`, plus the
        persisted `session_id` and `recommendation_ids`.
        """
        user = await self._get_user(cf_handle)

        problem_pool = await ProblemPoolService.get_pool()

        async with CodeforcesClient() as cf:
            solved_problems = await cf.get_solved_problems(cf_handle)
        solved_keys = {(p.contest_id, p.index) for p in solved_problems}

        recent_keys = await self._get_recent_recommended_keys(user.id)

        negative_streak = int((analysis.get("_extra") or {}).get("contest_behavior", {}).get("negative_streak", 0))

        result = run_recommender_agent(
            analysis=analysis,
            current_rating=user.current_rating,
            problem_pool=problem_pool,
            solved_keys=solved_keys,
            recent_recommendation_keys=recent_keys,
            negative_streak=negative_streak,
        )

        session = RecommendationSession(
            user_id=user.id,
            agent_run_id=agent_run_id,
            agent_reasoning=result["reasoning"],
            recommendation_strategy=result["strategy"],
            generated_at=_utcnow(),
        )
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)

        rows: list[RecommendedProblem] = []
        for rec in result["recommendations"]:
            row = RecommendedProblem(
                user_id=user.id,
                recommendation_session_id=session.id,
                contest_id=rec["contest_id"],
                index=rec["index"],
                problem_name=rec["problem_name"],
                rating=rec["rating"],
                tags=rec["tags"],
                recommendation_type=rec["recommendation_type"],
                recommendation_score=rec["recommendation_score"],
                recommendation_reason=rec["recommendation_reason"],
                difficulty_match_score=rec["difficulty_match_score"],
                estimated_solve_minutes=rec["estimated_solve_minutes"],
                url=rec["url"],
            )
            self._db.add(row)
            rows.append(row)

        await self._db.commit()
        for row in rows:
            await self._db.refresh(row)

        result["session"] = session
        result["recommended_problems"] = rows

        # BUG 3 fix: recommendation generation is one of the workflow
        # events that should leave a study_sessions trace.
        memory_svc = MemoryService(self._db)
        priority_topics = (analysis.get("priority_topics") or [])
        await memory_svc.record_workflow_session(
            cf_handle,
            session_type="recommendation_generated",
            topic=priority_topics[0] if priority_topics else None,
            notes=f"{len(rows)} problems recommended.",
        )

        return result

    async def get_recommendations(
        self, cf_handle: str, status: Optional[str] = None, limit: int = 50
    ) -> list[RecommendedProblem]:
        user = await self._get_user(cf_handle)
        stmt = select(RecommendedProblem).where(RecommendedProblem.user_id == user.id)
        if status == "pending":
            stmt = stmt.where(
                RecommendedProblem.solved.is_(False),
                RecommendedProblem.skipped.is_(False),
            )
        elif status == "solved":
            stmt = stmt.where(RecommendedProblem.solved.is_(True))
        elif status == "bookmarked":
            stmt = stmt.where(RecommendedProblem.bookmarked.is_(True))
        stmt = stmt.order_by(desc(RecommendedProblem.recommended_at)).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_problem_status(
        self,
        recommended_problem_id: int,
        action: str,
        time_spent_minutes: Optional[int] = None,
    ) -> RecommendedProblem:
        """action: 'solve' | 'skip' | 'bookmark' | 'unbookmark' | 'attempt'"""
        result = await self._db.execute(
            select(RecommendedProblem).where(RecommendedProblem.id == recommended_problem_id)
        )
        problem = result.scalar_one_or_none()
        if not problem:
            raise MemoryNotFoundError(f"No recommended problem with id={recommended_problem_id}")

        if action == "solve":
            problem.solved = True
            problem.attempted = True
        elif action == "skip":
            problem.skipped = True
        elif action == "bookmark":
            problem.bookmarked = True
        elif action == "unbookmark":
            problem.bookmarked = False
        elif action == "attempt":
            problem.attempted = True
        else:
            raise ValueError(f"Unknown action={action!r}")

        problem.updated_at = _utcnow()
        await self._db.commit()
        await self._db.refresh(problem)

        if action in ("solve", "skip", "attempt"):
            status_map = {"solve": "solved", "skip": "skipped", "attempt": "attempted"}
            attempt = ProblemAttempt(
                user_id=problem.user_id,
                recommended_problem_id=problem.id,
                contest_id=problem.contest_id,
                index=problem.index,
                status=status_map[action],
                time_spent_minutes=time_spent_minutes,
            )
            self._db.add(attempt)
            await self._db.commit()

            # BUG 7 fix: solve/skip previously only ever wrote ProblemAttempt
            # rows — study_sessions, topic_ratings, and learning_milestones
            # never reflected the action at all. Wire them all through
            # MemoryService here so a single click updates every table the
            # Memory Overview / Learning History pages read from.
            cf_handle = await self._get_cf_handle_by_user_id(problem.user_id)
            if cf_handle:
                memory_svc = MemoryService(self._db)
                primary_topic = (problem.tags or [None])[0]

                await memory_svc.record_workflow_session(
                    cf_handle,
                    session_type=f"problem_{action}",
                    topic=primary_topic,
                    problems_attempted=1,
                    problems_solved=1 if action == "solve" else 0,
                    duration_minutes=time_spent_minutes,
                    notes=f"{problem.contest_id}{problem.index} — {problem.problem_name}",
                )

                if action == "solve":
                    await memory_svc.touch_streak(cf_handle)
                    for tag in (problem.tags or []):
                        await memory_svc.upsert_topic_rating(cf_handle, topic=tag, solved=True)
                        await memory_svc.advance_milestone_progress(cf_handle, tag)
                elif action == "skip":
                    for tag in (problem.tags or []):
                        await memory_svc.upsert_topic_rating(cf_handle, topic=tag, failed=True)

        return problem