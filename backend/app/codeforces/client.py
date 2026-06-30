"""
Async Codeforces API client.

Wraps the public Codeforces API (https://codeforces.com/apiHelp) with:
  - httpx async transport
  - automatic retry with exponential back-off
  - typed Pydantic response models
  - clean error hierarchy for upstream consumers

Prepared for future LangGraph tool integration via the tool-wrapper layer
in app/tools/codeforces_tools.py.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.logging import get_logger
from app.codeforces.models import (
    CFUser,
    CFRatingChange,
    CFSubmission,
    CFProblem,
)
from app.codeforces.exceptions import (
    CFHandleNotFound,
    CFAPIError,
    CFRateLimitError,
)

logger = get_logger(__name__)

_BASE_URL = "https://codeforces.com/api"
_DEFAULT_TIMEOUT = 15.0
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5  # seconds


class CodeforcesClient:
    """
    Thin async wrapper around the Codeforces REST API.

    All methods return parsed Pydantic models so that callers never
    touch raw dicts.  The client is intentionally stateless so it can
    be instantiated once per request (or shared as a singleton inside
    the service layer).
    """

    def __init__(
        self,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._http: httpx.AsyncClient | None = None

    # ── lifecycle ──────────────────────────────────────────────────────────

    async def __aenter__(self) -> "CodeforcesClient":
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=self._timeout,
            headers={"User-Agent": "CodeMentorAI/0.2.0"},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    # ── low-level transport ────────────────────────────────────────────────

    async def _get(self, endpoint: str, **params: Any) -> Any:
        """
        GET `endpoint` with retry + back-off.
        Returns the `result` field of a successful CF response.
        """
        if self._http is None:
            raise RuntimeError(
                "CodeforcesClient must be used as an async context manager"
            )

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = await self._http.get(f"/{endpoint}", params=params)

                if resp.status_code == 429:
                    wait = _BACKOFF_BASE ** (attempt + 1)
                    logger.warning("CF rate-limited; waiting %.1fs", wait)
                    await asyncio.sleep(wait)
                    raise CFRateLimitError("Codeforces rate limit hit")

                resp.raise_for_status()
                body = resp.json()

                if body.get("status") != "OK":
                    comment = body.get("comment", "Unknown Codeforces error")
                    if "not found" in comment.lower() or "handles" in comment.lower():
                        raise CFHandleNotFound(comment)
                    raise CFAPIError(comment)

                return body["result"]

            except (CFHandleNotFound, CFAPIError):
                raise
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                wait = _BACKOFF_BASE ** attempt
                logger.warning(
                    "CF request attempt %d/%d failed (%s); retrying in %.1fs",
                    attempt + 1,
                    self._max_retries,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        raise CFAPIError(
            f"Codeforces API unreachable after {self._max_retries} retries"
        ) from last_exc

    # ── public API methods ─────────────────────────────────────────────────

    async def get_user_info(self, handle: str) -> CFUser:
        """Return profile info for a single CF user."""
        logger.debug("CF get_user_info handle=%s", handle)
        result = await self._get("user.info", handles=handle)
        return CFUser.model_validate(result[0])

    async def get_rating_history(self, handle: str) -> list[CFRatingChange]:
        """Return the full contest rating history for a user."""
        logger.debug("CF get_rating_history handle=%s", handle)
        result = await self._get("user.rating", handle=handle)
        return [CFRatingChange.model_validate(r) for r in result]

    async def get_submissions(
        self, handle: str, count: int = 10_000
    ) -> list[CFSubmission]:
        """
        Return up to `count` most-recent submissions for a user.
        Default 10 000 is the CF API maximum.
        """
        logger.debug("CF get_submissions handle=%s count=%d", handle, count)
        result = await self._get("user.status", handle=handle, count=count)
        return [CFSubmission.model_validate(s) for s in result]

    async def get_problemset(self) -> list[CFProblem]:
        """
        Return the full Codeforces problemset (problemset.problems).

        This is the canonical pool of *real* problems the Phase 5
        Problem Recommender Agent matches against — it never invents
        problems. The endpoint is not handle-scoped, so callers should
        cache the result (see app/services/problem_pool_service.py)
        rather than re-fetching it on every recommendation pass.
        """
        logger.debug("CF get_problemset")
        result = await self._get("problemset.problems")
        problems = result.get("problems", []) if isinstance(result, dict) else []
        return [CFProblem.model_validate(p) for p in problems]

    async def get_solved_problems(self, handle: str) -> list[CFProblem]:
        """
        Convenience helper: filter submissions to unique AC problems.
        Returns a deduplicated list of problems the user has solved.
        """
        submissions = await self.get_submissions(handle)
        seen: set[tuple[int | None, str]] = set()
        solved: list[CFProblem] = []
        for sub in submissions:
            if sub.verdict == "OK":
                key = (sub.problem.contest_id, sub.problem.index)
                if key not in seen:
                    seen.add(key)
                    solved.append(sub.problem)
        return solved
