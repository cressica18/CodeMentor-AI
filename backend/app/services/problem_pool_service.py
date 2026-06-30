"""
ProblemPoolService — Phase 5.

Fetches and caches the real Codeforces problemset
(`problemset.problems`) so the Recommender Agent always matches
against actual CF problems instead of fabricating any. The full
problemset is ~10k+ problems and does not change meaningfully within a
single process lifetime, so it is cached in-process with a TTL rather
than re-fetched on every recommendation run.
"""

from __future__ import annotations

import time
from typing import Any

from app.codeforces.client import CodeforcesClient
from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 hours — the CF problemset rarely changes intra-day


class ProblemPoolService:
    """Singleton-style in-process cache around `problemset.problems`."""

    _cache: list[dict[str, Any]] | None = None
    _cached_at: float = 0.0

    @classmethod
    async def get_pool(cls, force_refresh: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if (
            not force_refresh
            and cls._cache is not None
            and (now - cls._cached_at) < _CACHE_TTL_SECONDS
        ):
            return cls._cache

        logger.info("Fetching real Codeforces problemset (problemset.problems)")
        async with CodeforcesClient() as cf:
            problems = await cf.get_problemset()

        pool = [
            {
                "contest_id": p.contest_id,
                "index": p.index,
                "name": p.name,
                "rating": p.rating,
                "tags": p.tags,
            }
            for p in problems
            # Only problems with a known rating + a contest_id are usable
            # for rating-matched recommendations / direct CF URLs.
            if p.contest_id is not None and p.rating is not None
        ]
        cls._cache = pool
        cls._cached_at = now
        logger.info("Cached %d rated Codeforces problems", len(pool))
        return pool
