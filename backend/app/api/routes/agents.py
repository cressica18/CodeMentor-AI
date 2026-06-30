"""
Agent API routes - Phase 4.

Namespaced under /api/v1/agents. Thin wrappers around AgentService;
no orchestration or persistence logic lives here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryNotFoundError
from app.schemas import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunRead,
    AgentTraceRead,
    AnalyzerOutput,
    PlannerOutputSchema,
    AnalysisSnapshotRead,
    PlannerOutputRead,
    RecommenderOutput,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def _not_found(exc: MemoryNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def _build_run_result(result: dict) -> AgentRunResult:
    analysis = result.get("analysis") or {}
    plan = result.get("plan") or {}
    recommendations = result.get("recommendations") or {}
    return AgentRunResult(
        run=AgentRunRead.model_validate(result["run"]),
        traces=[AgentTraceRead.model_validate(t) for t in result["traces"]],
        analysis=AnalyzerOutput(**{k: v for k, v in analysis.items() if not k.startswith("_")}) if analysis else None,
        plan=PlannerOutputSchema(**plan) if plan else None,
        recommendations=RecommenderOutput(**recommendations) if recommendations else None,
    )


@router.post("/analyze", response_model=AgentRunResult)
async def analyze(payload: AgentRunRequest, db: AsyncSession = Depends(get_db)):
    """Run RetrieveMemory -> AnalyzerAgent (graph still executes Planner+Persist; tagged as an 'analyze' run)."""
    svc = AgentService(db)
    try:
        result = await svc.run_analyzer_only(payload.cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    return _build_run_result(result)


@router.post("/plan", response_model=AgentRunResult)
async def plan(payload: AgentRunRequest, db: AsyncSession = Depends(get_db)):
    """Run the full mentor graph, tagged as a 'plan' run - returns the generated study plan."""
    svc = AgentService(db)
    try:
        result = await svc.run_planner_only(payload.cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    return _build_run_result(result)


@router.post("/run", response_model=AgentRunResult)
async def run(payload: AgentRunRequest, db: AsyncSession = Depends(get_db)):
    """Run the full orchestrator workflow: RetrieveMemory -> AnalyzerAgent -> PlannerAgent -> PersistMemory."""
    svc = AgentService(db)
    try:
        result = await svc.run_orchestrator(payload.cf_handle, run_type="full")
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    return _build_run_result(result)


@router.get("/history", response_model=list[AgentRunRead])
async def history(
    cf_handle: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    svc = AgentService(db)
    runs = await svc.get_history(cf_handle=cf_handle, limit=limit)
    return [AgentRunRead.model_validate(r) for r in runs]


@router.get("/traces", response_model=list[AgentTraceRead])
async def traces(
    agent_run_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    svc = AgentService(db)
    try:
        await svc.get_run(agent_run_id)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    rows = await svc.get_traces(agent_run_id)
    return [AgentTraceRead.model_validate(t) for t in rows]


@router.get("/analysis/{cf_handle}/latest", response_model=AnalysisSnapshotRead)
async def latest_analysis(cf_handle: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    try:
        snapshot = await svc.get_latest_analysis(cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No analysis runs yet for cf_handle={cf_handle!r}")
    return snapshot


@router.get("/plan/{cf_handle}/latest", response_model=PlannerOutputRead)
async def latest_plan(cf_handle: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    try:
        output = await svc.get_latest_plan(cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    if output is None:
        raise HTTPException(status_code=404, detail=f"No planner runs yet for cf_handle={cf_handle!r}")
    return output
