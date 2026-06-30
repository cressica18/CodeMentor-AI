"""
Codeforces API routes — Phase 2.

POST /api/v1/codeforces/ingest   — full ingestion pipeline
GET  /api/v1/codeforces/{handle} — return cached or freshly-fetched analytics
GET  /api/v1/codeforces/{handle}/summary — lightweight summary
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.codeforces.client import CodeforcesClient
from app.codeforces.exceptions import CFHandleNotFound, CFAPIError
from app.services.codeforces_service import CodeforcesService
from app.schemas import (
    CFIngestRequest,
    CFProfileResponse,
    CFProfileSummary,
    ErrorResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/codeforces", tags=["codeforces"])


# ── helpers ────────────────────────────────────────────────────────────────

def _cf_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, CFHandleNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=502, detail=f"Codeforces API error: {exc}")


def _analytics_to_summary(analytics: dict) -> CFProfileSummary:
    return CFProfileSummary(
        handle=analytics["handle"],
        display_name=analytics.get("display_name"),
        current_rating=analytics.get("current_rating"),
        max_rating=analytics.get("max_rating"),
        rank=analytics.get("rank"),
        solved_count=analytics.get("solved_count", 0),
        contests_participated=analytics.get("contests_participated", 0),
        weakest_tags=analytics.get("weakest_tags", []),
        strongest_tags=analytics.get("strongest_tags", []),
    )


# ── routes ─────────────────────────────────────────────────────────────────

@router.post(
    "/ingest",
    response_model=CFProfileResponse,
    summary="Ingest Codeforces profile",
    responses={
        404: {"model": ErrorResponse, "description": "Handle not found on Codeforces"},
        502: {"model": ErrorResponse, "description": "Codeforces API error"},
    },
)
async def ingest_profile(
    payload: CFIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> CFProfileResponse:
    """
    Fetch all data from the Codeforces API for the given handle,
    compute analytics, persist to the database, and return the full
    analytics payload.

    Pass `force_refresh=true` to bypass any cached data.
    """
    handle = payload.cf_handle.strip()
    logger.info("Ingest request handle=%s force=%s", handle, payload.force_refresh)

    try:
        async with CodeforcesClient() as cf:
            svc = CodeforcesService(cf, db)

            # Return cached data if available and refresh not forced
            if not payload.force_refresh:
                cached = await svc.get_cached_profile(handle)
                if cached:
                    logger.info("Returning cached profile for handle=%s", handle)
                    return CFProfileResponse(**cached)

            analytics = await svc.ingest_profile(handle)
            return CFProfileResponse(**analytics)

    except (CFHandleNotFound, CFAPIError) as exc:
        raise _cf_error_to_http(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected error during ingestion for handle=%s", handle)
        raise HTTPException(
            status_code=500, detail=f"Internal error: {exc}"
        ) from exc


@router.get(
    "/{handle}",
    response_model=CFProfileResponse,
    summary="Get cached CF analytics",
    responses={
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def get_profile(
    handle: str,
    refresh: bool = Query(False, description="Re-fetch from Codeforces API"),
    db: AsyncSession = Depends(get_db),
) -> CFProfileResponse:
    """
    Return analytics for `handle`.  If the profile has never been
    ingested, automatically triggers a live fetch.  Pass `?refresh=true`
    to force a re-fetch.
    """
    handle = handle.strip()
    try:
        async with CodeforcesClient() as cf:
            svc = CodeforcesService(cf, db)

            if not refresh:
                cached = await svc.get_cached_profile(handle)
                if cached:
                    return CFProfileResponse(**cached)

            analytics = await svc.ingest_profile(handle)
            return CFProfileResponse(**analytics)

    except (CFHandleNotFound, CFAPIError) as exc:
        raise _cf_error_to_http(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected error for handle=%s", handle)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


@router.get(
    "/{handle}/summary",
    response_model=CFProfileSummary,
    summary="Lightweight profile summary",
)
async def get_profile_summary(
    handle: str,
    db: AsyncSession = Depends(get_db),
) -> CFProfileSummary:
    """
    Return a lightweight profile summary (no heatmap / full trend data).
    Useful for sidebar widgets and quick checks.
    """
    handle = handle.strip()
    try:
        async with CodeforcesClient() as cf:
            svc = CodeforcesService(cf, db)
            cached = await svc.get_cached_profile(handle)
            if cached:
                return _analytics_to_summary(cached)
            analytics = await svc.ingest_profile(handle)
            return _analytics_to_summary(analytics)

    except (CFHandleNotFound, CFAPIError) as exc:
        raise _cf_error_to_http(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected error for handle=%s", handle)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
