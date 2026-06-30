"""
Memory API routes — Phase 3.

All routes are namespaced under /api/v1/memory and keyed by `cf_handle`
(consistent with the rest of the app) except for session-memory routes,
which are keyed by `session_id`.

These endpoints are pure CRUD over the persistence layer in
app/services/memory_service.py. No agent / LLM logic is invoked here —
that begins in Phase 4+.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.memory_service import MemoryService, MemoryNotFoundError
from app.schemas import (
    UserProfileRead,
    UserProfileUpdate,
    TopicRatingRead,
    TopicRatingUpsert,
    LearningPathRead,
    LearningPathUpdate,
    StudySessionCreate,
    StudySessionRead,
    LearningMilestoneCreate,
    LearningMilestoneRead,
    SessionMemoryRead,
    SessionMemoryUpdate,
    SessionMessageAppend,
    SessionSummarySave,
    RecommendationCreate,
    RecommendationRead,
    RecommendationStatusUpdate,
    ProgressSnapshotRead,
    UserPreferenceRead,
    UserPreferenceUpdate,
    ChatSessionSummary,
    MemoryOverview,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


def _not_found(exc: MemoryNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


# ── Overview (drives the frontend memory visualization panels) ─────────────


@router.get("/overview/{cf_handle}", response_model=MemoryOverview)
async def get_overview(cf_handle: str, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_overview(cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


# ── User profile ─────────────────────────────────────────────────────────


@router.get("/profile/{cf_handle}", response_model=UserProfileRead)
async def get_profile(cf_handle: str, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_or_create_profile(cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.put("/profile/{cf_handle}", response_model=UserProfileRead)
async def update_profile(cf_handle: str, payload: UserProfileUpdate, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.update_profile(cf_handle, **payload.model_dump(exclude_unset=True))
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/profile/{cf_handle}/streak", response_model=UserProfileRead)
async def touch_streak(cf_handle: str, db: AsyncSession = Depends(get_db)):
    """Record practice activity for today and update streak counters."""
    svc = MemoryService(db)
    try:
        return await svc.touch_streak(cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


# ── Topic ratings ────────────────────────────────────────────────────────


@router.get("/topics/{cf_handle}", response_model=list[TopicRatingRead])
async def get_topic_ratings(cf_handle: str, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_topic_ratings(cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.put("/topics/{cf_handle}", response_model=TopicRatingRead)
async def upsert_topic_rating(cf_handle: str, payload: TopicRatingUpsert, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.upsert_topic_rating(
            cf_handle,
            topic=payload.topic,
            rating=payload.rating,
            solved=payload.solved,
            failed=payload.failed,
        )
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


# ── Learning path ────────────────────────────────────────────────────────


@router.get("/learning-path/{cf_handle}", response_model=LearningPathRead)
async def get_learning_path(cf_handle: str, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_or_create_learning_path(cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.put("/learning-path/{cf_handle}", response_model=LearningPathRead)
async def update_learning_path(cf_handle: str, payload: LearningPathUpdate, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.update_learning_path(cf_handle, **payload.model_dump(exclude_unset=True))
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


# ── Study sessions (learning history) ───────────────────────────────────


@router.get("/study-sessions/{cf_handle}", response_model=list[StudySessionRead])
async def get_study_sessions(cf_handle: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_study_sessions(cf_handle, limit=limit)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/study-sessions/{cf_handle}", response_model=StudySessionRead, status_code=201)
async def create_study_session(cf_handle: str, payload: StudySessionCreate, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.create_study_session(cf_handle, **payload.model_dump(exclude_unset=True))
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/study-sessions/{session_db_id}/end", response_model=StudySessionRead)
async def end_study_session(session_db_id: int, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.end_study_session(session_db_id)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


# ── Learning milestones ──────────────────────────────────────────────────


@router.get("/milestones/{cf_handle}", response_model=list[LearningMilestoneRead])
async def get_milestones(cf_handle: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_milestones(cf_handle, limit=limit)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/milestones/{cf_handle}", response_model=LearningMilestoneRead, status_code=201)
async def create_milestone(cf_handle: str, payload: LearningMilestoneCreate, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.create_milestone(cf_handle, **payload.model_dump(exclude_unset=True))
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


# ── Session memory (short-term) ──────────────────────────────────────────


@router.get("/session/{session_id}", response_model=SessionMemoryRead)
async def get_session_memory(session_id: str, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    return await svc.get_or_create_session_memory(session_id)


@router.put("/session/{session_id}", response_model=SessionMemoryRead)
async def update_session_memory(session_id: str, payload: SessionMemoryUpdate, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    return await svc.update_session_memory(session_id, **payload.model_dump(exclude_unset=True))


@router.post("/session/{session_id}/messages", response_model=SessionMemoryRead)
async def append_message(session_id: str, payload: SessionMessageAppend, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    return await svc.append_message(session_id, payload.role, payload.content)


@router.post("/session/{session_id}/summary")
async def save_session_summary(session_id: str, payload: SessionSummarySave, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        chat_session = await svc.save_session_summary(session_id, payload.summary)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    return {"session_id": chat_session.session_id, "summary": chat_session.summary}


# ── Recommendations ──────────────────────────────────────────────────────


@router.get("/recommendations/{cf_handle}", response_model=list[RecommendationRead])
async def get_recommendations(cf_handle: str, status: str | None = None, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_recommendations(cf_handle, status=status)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/recommendations/{cf_handle}", response_model=RecommendationRead, status_code=201)
async def create_recommendation(cf_handle: str, payload: RecommendationCreate, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.create_recommendation(cf_handle, **payload.model_dump(exclude_unset=True))
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.patch("/recommendations/item/{recommendation_id}", response_model=RecommendationRead)
async def update_recommendation_status(
    recommendation_id: int, payload: RecommendationStatusUpdate, db: AsyncSession = Depends(get_db)
):
    svc = MemoryService(db)
    try:
        return await svc.update_recommendation_status(recommendation_id, payload.status)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


# ── Progress tracking ────────────────────────────────────────────────────


@router.get("/progress/{cf_handle}", response_model=list[ProgressSnapshotRead])
async def get_progress_snapshots(cf_handle: str, limit: int = 100, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_progress_snapshots(cf_handle, limit=limit)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/progress/{cf_handle}/snapshot", response_model=ProgressSnapshotRead, status_code=201)
async def create_progress_snapshot(cf_handle: str, db: AsyncSession = Depends(get_db)):
    """
    Compute a snapshot from the user's current state (rating + topic
    ratings) and store it. Intended to be called periodically (e.g. after
    each CF ingestion) so improvement velocity can be tracked over time.
    """
    svc = MemoryService(db)
    try:
        user = await svc._get_user_by_handle(cf_handle)  # noqa: SLF001 (internal, same module family)
        topic_ratings = await svc.get_topic_ratings(cf_handle)
        weak = [t.topic for t in topic_ratings if t.is_weakness]
        strong = [t.topic for t in topic_ratings if t.is_strength]
        return await svc.create_progress_snapshot(
            cf_handle,
            rating=user.current_rating,
            solved_count=None,
            topic_ratings={t.topic: t.rating for t in topic_ratings},
            weak_topics=weak,
            strong_topics=strong,
        )
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/chat-sessions/{cf_handle}", response_model=list[ChatSessionSummary])
async def get_chat_sessions(cf_handle: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_chat_sessions(cf_handle, limit=limit)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


# ── User preferences ──────────────────────────────────────────────────────


@router.get("/preferences/{cf_handle}", response_model=UserPreferenceRead)
async def get_preferences(cf_handle: str, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.get_or_create_preferences(cf_handle)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.put("/preferences/{cf_handle}", response_model=UserPreferenceRead)
async def update_preferences(cf_handle: str, payload: UserPreferenceUpdate, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        return await svc.update_preferences(cf_handle, **payload.model_dump(exclude_unset=True))
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
