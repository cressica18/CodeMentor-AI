"""
LangChain tool wrappers for Codeforces API operations.

These tools expose the Codeforces client methods as LangChain BaseTool
subclasses so they can be plugged directly into a LangGraph StateGraph
agent (Analyzer, Recommender, Planner) in a later phase.

Phase 2 registers them but does NOT wire them into an agent graph.
They are importable and callable standalone for testing.
"""

from __future__ import annotations

from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.codeforces.client import CodeforcesClient
from app.codeforces.analytics import build_full_analytics
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── input schemas ──────────────────────────────────────────────────────────

class CFHandleInput(BaseModel):
    handle: str = Field(..., description="Codeforces user handle, e.g. 'tourist'")


class CFSubmissionsInput(BaseModel):
    handle: str = Field(..., description="Codeforces user handle")
    count: int = Field(500, description="Number of recent submissions to fetch (max 10000)")


# ── tools ──────────────────────────────────────────────────────────────────

class GetCFUserInfoTool(BaseTool):
    """Fetch basic Codeforces user profile (rating, rank, country, etc.)."""

    name: str = "get_cf_user_info"
    description: str = (
        "Fetch the Codeforces profile for a given handle. "
        "Returns handle, rank, current rating, max rating, country, organization."
    )
    args_schema: Type[BaseModel] = CFHandleInput

    def _run(self, handle: str) -> dict[str, Any]:
        raise NotImplementedError("Use arun() — this tool is async-only.")

    async def _arun(self, handle: str) -> dict[str, Any]:
        async with CodeforcesClient() as cf:
            user = await cf.get_user_info(handle)
        return user.model_dump(by_alias=False)


class GetCFRatingHistoryTool(BaseTool):
    """Fetch full contest rating history for a Codeforces user."""

    name: str = "get_cf_rating_history"
    description: str = (
        "Fetch the complete contest rating history for a Codeforces user. "
        "Returns a list of contests with old/new rating and rank."
    )
    args_schema: Type[BaseModel] = CFHandleInput

    def _run(self, handle: str) -> list[dict]:
        raise NotImplementedError("Use arun().")

    async def _arun(self, handle: str) -> list[dict]:
        async with CodeforcesClient() as cf:
            history = await cf.get_rating_history(handle)
        return [r.model_dump(by_alias=False) for r in history]


class GetCFSubmissionsTool(BaseTool):
    """Fetch recent Codeforces submissions for a user."""

    name: str = "get_cf_submissions"
    description: str = (
        "Fetch recent submission records for a Codeforces user. "
        "Each record includes the problem, verdict, and timestamp."
    )
    args_schema: Type[BaseModel] = CFSubmissionsInput

    def _run(self, handle: str, count: int = 500) -> list[dict]:
        raise NotImplementedError("Use arun().")

    async def _arun(self, handle: str, count: int = 500) -> list[dict]:
        async with CodeforcesClient() as cf:
            subs = await cf.get_submissions(handle, count=count)
        return [s.model_dump(by_alias=False) for s in subs]


class GetCFSolvedProblemsTool(BaseTool):
    """Return a deduplicated list of problems a user has solved on Codeforces."""

    name: str = "get_cf_solved_problems"
    description: str = (
        "Return a deduplicated list of problems the user has accepted (AC) "
        "on Codeforces, including tags and difficulty ratings."
    )
    args_schema: Type[BaseModel] = CFHandleInput

    def _run(self, handle: str) -> list[dict]:
        raise NotImplementedError("Use arun().")

    async def _arun(self, handle: str) -> list[dict]:
        async with CodeforcesClient() as cf:
            solved = await cf.get_solved_problems(handle)
        return [p.model_dump(by_alias=False) for p in solved]


class AnalyzeCFProfileTool(BaseTool):
    """
    Comprehensive Codeforces analytics: fetches all data and returns
    the full analytics payload (rating trend, tag breakdown, heatmap, etc.).
    """

    name: str = "analyze_cf_profile"
    description: str = (
        "Perform a comprehensive analysis of a Codeforces user profile. "
        "Returns current/max rating, strongest/weakest tags, difficulty "
        "distribution, submission success rate, and activity heatmap. "
        "Use this when you need a full picture of a user's performance."
    )
    args_schema: Type[BaseModel] = CFHandleInput

    def _run(self, handle: str) -> dict[str, Any]:
        raise NotImplementedError("Use arun().")

    async def _arun(self, handle: str) -> dict[str, Any]:
        async with CodeforcesClient() as cf:
            user = await cf.get_user_info(handle)
            rating_history = await cf.get_rating_history(handle)
            all_subs = await cf.get_submissions(handle)
            solved = await cf.get_solved_problems(handle)

        return build_full_analytics(
            user=user,
            rating_history=rating_history,
            all_submissions=all_subs,
            solved_problems=solved,
        )


# ── tool registry (for future agent assembly) ──────────────────────────────

CF_TOOLS: list[BaseTool] = [
    GetCFUserInfoTool(),
    GetCFRatingHistoryTool(),
    GetCFSubmissionsTool(),
    GetCFSolvedProblemsTool(),
    AnalyzeCFProfileTool(),
]
