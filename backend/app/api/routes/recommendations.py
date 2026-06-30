"""
Recommendations API routes — Phase 5.

Namespaced under /api/v1/recommendations. Thin wrappers around
RecommenderService; no recommendation logic lives here (see
app/agents/recommender.py for the pure engine).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.agent_service import AgentService
from app.services.recommender_service import RecommenderService
from app.services.memory_service import MemoryNotFoundError
from app.schemas import (
    GenerateRecommendationsRequest,
    RecommendedProblemRead,
    ProblemActionRequest,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _not_found(exc: MemoryNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/generate", response_model=list[RecommendedProblemRead])
async def generate_recommendations(
    payload: GenerateRecommendationsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate fresh problem recommendations for a handle.

    Runs the latest Analyzer Agent output (re-running the analyzer if
    none exists yet) through the Problem Recommender Agent, which
    matches against the real, live Codeforces problemset.
    """
    agent_svc = AgentService(db)
    rec_svc = RecommenderService(db)

    try:
        latest_analysis = await agent_svc.get_latest_analysis(payload.cf_handle)
        if latest_analysis is None:
            # No analysis yet for this handle — run the full graph once
            # so Analyzer/Planner/Recommender all populate together.
            await agent_svc.run_orchestrator(payload.cf_handle, run_type="full")
            rows = await rec_svc.get_recommendations(payload.cf_handle, limit=50)
            return [RecommendedProblemRead.model_validate(r) for r in rows]

        analysis_dict = {
            "strengths": latest_analysis.strengths or [],
            "weaknesses": latest_analysis.weaknesses or [],
            "priority_topics": latest_analysis.priority_topics or [],
            "improvement_velocity": latest_analysis.improvement_velocity or 0.0,
            "analysis_summary": latest_analysis.analysis_summary or "",
            "_extra": (latest_analysis.raw_output or {}).get("_extra", {}),
        }
        result = await rec_svc.generate_recommendations(payload.cf_handle, analysis_dict)
        return [RecommendedProblemRead.model_validate(r) for r in result["recommended_problems"]]
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/{cf_handle}", response_model=list[RecommendedProblemRead])
async def list_recommendations(
    cf_handle: str,
    status: str | None = Query(default=None, description="pending | solved | bookmarked"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    svc = RecommenderService(db)
    try:
        rows = await svc.get_recommendations(cf_handle, status=status, limit=limit)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    return [RecommendedProblemRead.model_validate(r) for r in rows]


@router.patch("/item/{recommended_problem_id}", response_model=RecommendedProblemRead)
async def update_recommendation(
    recommended_problem_id: int,
    payload: ProblemActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark a recommended problem as solved / skipped / bookmarked / attempted."""
    svc = RecommenderService(db)
    try:
        row = await svc.update_problem_status(
            recommended_problem_id, payload.action, payload.time_spent_minutes
        )
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    return RecommendedProblemRead.model_validate(row)
