"""
Phase 3 tests — persistent memory & user modeling layer.

Coverage:
  ✓ memory persistence       (profile, topic ratings, learning path)
  ✓ memory retrieval         (overview aggregation)
  ✓ profile updates          (bio/goals/streaks)
  ✓ session storage          (short-term SessionMemory)
  ✓ learning history storage (study sessions, milestones)
  ✓ recommendation storage
  ✓ progress tracking        (snapshots + improvement velocity)
  ✓ API endpoint responses   (FastAPI TestClient over the memory routes)
  ✓ database operations      (real SQLite-backed CRUD, not mocked)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import get_db
from app.services.memory_service import MemoryService, MemoryNotFoundError


# ── MemoryService: persistence + retrieval ──────────────────────────────


@pytest.mark.asyncio
async def test_get_or_create_profile_persists(db_session, seeded_user):
    svc = MemoryService(db_session)
    profile = await svc.get_or_create_profile(seeded_user.cf_handle)

    assert profile.user_id == seeded_user.id
    assert profile.current_streak_days == 0

    # Calling again returns the same row, not a duplicate
    profile_again = await svc.get_or_create_profile(seeded_user.cf_handle)
    assert profile_again.id == profile.id


@pytest.mark.asyncio
async def test_profile_not_found_for_unknown_handle(db_session):
    svc = MemoryService(db_session)
    with pytest.raises(MemoryNotFoundError):
        await svc.get_or_create_profile("does_not_exist")


@pytest.mark.asyncio
async def test_update_profile(db_session, seeded_user):
    svc = MemoryService(db_session)
    updated = await svc.update_profile(
        seeded_user.cf_handle,
        bio="Competitive programmer focused on DP and graphs.",
        goals={"target_rating": 1900},
    )
    assert updated.bio.startswith("Competitive programmer")
    assert updated.goals == {"target_rating": 1900}


@pytest.mark.asyncio
async def test_streak_tracking(db_session, seeded_user):
    svc = MemoryService(db_session)

    profile = await svc.touch_streak(seeded_user.cf_handle)
    assert profile.current_streak_days == 1
    assert profile.longest_streak_days == 1

    # Touching again same day should not double-count
    profile = await svc.touch_streak(seeded_user.cf_handle)
    assert profile.current_streak_days == 1

    # Simulate a missed day by manually rewinding last_practice_date
    profile.last_practice_date = datetime.now(timezone.utc) - timedelta(days=3)
    await db_session.commit()
    profile = await svc.touch_streak(seeded_user.cf_handle)
    assert profile.current_streak_days == 1  # streak reset


@pytest.mark.asyncio
async def test_topic_rating_upsert_and_classification(db_session, seeded_user):
    svc = MemoryService(db_session)

    tr = await svc.upsert_topic_rating(seeded_user.cf_handle, topic="graphs", rating=0.2)
    assert tr.is_weakness is True
    assert tr.is_strength is False

    tr = await svc.upsert_topic_rating(seeded_user.cf_handle, topic="graphs", rating=0.9, solved=True)
    assert tr.is_strength is True
    assert tr.problems_solved == 1

    ratings = await svc.get_topic_ratings(seeded_user.cf_handle)
    assert len(ratings) == 1
    assert ratings[0].topic == "graphs"


@pytest.mark.asyncio
async def test_learning_path_create_and_update(db_session, seeded_user):
    svc = MemoryService(db_session)
    path = await svc.get_or_create_learning_path(seeded_user.cf_handle)
    assert path.progress_percent == 0.0

    updated = await svc.update_learning_path(
        seeded_user.cf_handle,
        current_stage="Segment Trees",
        progress_percent=25.0,
        state={"stages": ["DP", "Segment Trees", "Graphs"]},
    )
    assert updated.current_stage == "Segment Trees"
    assert updated.progress_percent == 25.0
    assert updated.state["stages"][1] == "Segment Trees"


@pytest.mark.asyncio
async def test_study_session_lifecycle(db_session, seeded_user):
    svc = MemoryService(db_session)
    session = await svc.create_study_session(
        seeded_user.cf_handle, topic="dp", problems_attempted=3, problems_solved=2
    )
    assert session.ended_at is None

    ended = await svc.end_study_session(session.id)
    assert ended.ended_at is not None

    history = await svc.get_study_sessions(seeded_user.cf_handle)
    assert len(history) == 1
    assert history[0].topic == "dp"


@pytest.mark.asyncio
async def test_learning_milestones(db_session, seeded_user):
    svc = MemoryService(db_session)
    await svc.create_milestone(seeded_user.cf_handle, title="First 1500 solve", milestone_type="rating")
    milestones = await svc.get_milestones(seeded_user.cf_handle)
    assert len(milestones) == 1
    assert milestones[0].title == "First 1500 solve"


@pytest.mark.asyncio
async def test_session_memory_short_term(db_session, seeded_user):
    svc = MemoryService(db_session)
    session_id = "sess-abc-123"

    mem = await svc.append_message(session_id, "user", "What's a segment tree?")
    assert len(mem.conversation_history) == 1

    mem = await svc.append_message(session_id, "assistant", "It's a tree data structure...")
    assert len(mem.conversation_history) == 2

    mem = await svc.update_session_memory(session_id, topics_discussed=["segment_trees"])
    assert mem.topics_discussed == ["segment_trees"]

    # Re-fetching returns the same row (no duplicates per session_id)
    fetched = await svc.get_or_create_session_memory(session_id)
    assert fetched.id == mem.id


@pytest.mark.asyncio
async def test_recommendation_storage_and_status(db_session, seeded_user):
    svc = MemoryService(db_session)
    rec = await svc.create_recommendation(
        seeded_user.cf_handle,
        rec_type="problem",
        payload={"problem_id": "1234A", "title": "Example Problem"},
        reason="Targets weak topic: graphs",
        source="manual",
    )
    assert rec.status == "pending"

    profile = await svc.get_or_create_profile(seeded_user.cf_handle)
    assert profile.historical_recommendation_count == 1

    updated = await svc.update_recommendation_status(rec.id, "accepted")
    assert updated.status == "accepted"

    recs = await svc.get_recommendations(seeded_user.cf_handle, status="accepted")
    assert len(recs) == 1


@pytest.mark.asyncio
async def test_progress_snapshot_and_velocity(db_session, seeded_user):
    svc = MemoryService(db_session)

    s1 = await svc.create_progress_snapshot(seeded_user.cf_handle, rating=1400, solved_count=50)
    s1.snapshot_at = datetime.now(timezone.utc) - timedelta(days=10)
    await db_session.commit()

    s2 = await svc.create_progress_snapshot(seeded_user.cf_handle, rating=1450, solved_count=60)

    snapshots = await svc.get_progress_snapshots(seeded_user.cf_handle)
    assert len(snapshots) == 2

    profile = await svc.get_or_create_profile(seeded_user.cf_handle)
    assert profile.improvement_velocity is not None


@pytest.mark.asyncio
async def test_preferences_defaults_and_update(db_session, seeded_user):
    svc = MemoryService(db_session)
    prefs = await svc.get_or_create_preferences(seeded_user.cf_handle)
    assert prefs.theme == "dark"

    updated = await svc.update_preferences(seeded_user.cf_handle, daily_goal_minutes=45, theme="light")
    assert updated.daily_goal_minutes == 45
    assert updated.theme == "light"


@pytest.mark.asyncio
async def test_overview_aggregates_everything(db_session, seeded_user):
    svc = MemoryService(db_session)
    await svc.upsert_topic_rating(seeded_user.cf_handle, topic="dp", rating=0.5)
    await svc.create_study_session(seeded_user.cf_handle, topic="dp")
    await svc.create_recommendation(
        seeded_user.cf_handle, rec_type="topic", payload={"topic": "dp"}, reason="weak area"
    )

    overview = await svc.get_overview(seeded_user.cf_handle)
    assert overview["profile"].user_id == seeded_user.id
    assert len(overview["topic_ratings"]) == 1
    assert len(overview["recent_sessions"]) == 1
    assert len(overview["recent_recommendations"]) == 1
    assert overview["preferences"] is not None
    assert overview["learning_path"] is not None


# ── API endpoint tests (FastAPI TestClient, real SQLite DB via override) ──


@pytest.mark.asyncio
async def test_memory_api_profile_roundtrip(db_session, seeded_user):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get(f"/api/v1/memory/profile/{seeded_user.cf_handle}")
            assert r.status_code == 200
            assert r.json()["user_id"] == seeded_user.id

            r = await ac.put(
                f"/api/v1/memory/profile/{seeded_user.cf_handle}",
                json={"bio": "Updated via API"},
            )
            assert r.status_code == 200
            assert r.json()["bio"] == "Updated via API"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_memory_api_profile_404_for_unknown_user(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get("/api/v1/memory/profile/ghost_handle")
            assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_memory_api_topic_ratings(db_session, seeded_user):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.put(
                f"/api/v1/memory/topics/{seeded_user.cf_handle}",
                json={"topic": "binary_search", "rating": 0.8, "solved": True},
            )
            assert r.status_code == 200
            assert r.json()["is_strength"] is True

            r = await ac.get(f"/api/v1/memory/topics/{seeded_user.cf_handle}")
            assert r.status_code == 200
            assert len(r.json()) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_memory_api_session_memory(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/memory/session/sess-api-1/messages",
                json={"role": "user", "content": "Explain segment trees"},
            )
            assert r.status_code == 200
            assert len(r.json()["conversation_history"]) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_memory_api_overview(db_session, seeded_user):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get(f"/api/v1/memory/overview/{seeded_user.cf_handle}")
            assert r.status_code == 200
            data = r.json()
            assert "profile" in data
            assert "topic_ratings" in data
            assert "learning_path" in data
    finally:
        app.dependency_overrides.clear()
