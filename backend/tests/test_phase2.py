"""
Phase 2 tests — Codeforces data layer.

Test coverage:
  ✓ valid handle retrieval (mocked httpx)
  ✓ invalid handle handling (CFHandleNotFound)
  ✓ contest history parsing
  ✓ submission parsing
  ✓ analytics generation (pure-function tests, no network)
  ✓ API endpoint responses (FastAPI TestClient / AsyncClient)

All network calls are intercepted by respx so tests run fully offline.
"""

from __future__ import annotations

import json
import pytest
import respx
import httpx
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.codeforces.client import CodeforcesClient
from app.codeforces.exceptions import CFHandleNotFound, CFAPIError
from app.codeforces.models import CFUser, CFRatingChange, CFSubmission, CFProblem
from app.codeforces.analytics import (
    compute_rating_trend,
    compute_tag_stats,
    compute_difficulty_distribution,
    compute_submission_stats,
    build_full_analytics,
)

# ── fixtures ───────────────────────────────────────────────────────────────

CF_BASE = "https://codeforces.com/api"

MOCK_USER = {
    "handle": "tourist",
    "firstName": "Gennady",
    "lastName": "Korotkevich",
    "country": "Belarus",
    "rating": 3979,
    "maxRating": 4009,
    "rank": "legendary grandmaster",
    "maxRank": "legendary grandmaster",
    "contribution": 119,
    "friendOfCount": 65000,
    "avatar": "https://userpic.codeforces.org/tourist.jpg",
    "titlePhoto": "https://userpic.codeforces.org/tourist.jpg",
    "lastOnlineTimeSeconds": 1700000000,
    "registrationTimeSeconds": 1268570400,
}

MOCK_RATING_CHANGE = {
    "contestId": 1,
    "contestName": "Codeforces Beta Round 1",
    "handle": "tourist",
    "rank": 3,
    "ratingUpdateTimeSeconds": 1268570400,
    "oldRating": 1500,
    "newRating": 1730,
}

MOCK_PROBLEM = {
    "contestId": 1,
    "index": "A",
    "name": "Theatre Square",
    "type": "PROGRAMMING",
    "rating": 1000,
    "tags": ["math"],
}

MOCK_SUBMISSION = {
    "id": 1,
    "contestId": 1,
    "creationTimeSeconds": 1268570500,
    "relativeTimeSeconds": 100,
    "problem": MOCK_PROBLEM,
    "author": {"participantType": "CONTESTANT"},
    "programmingLanguage": "GNU C++17",
    "verdict": "OK",
    "testset": "TESTS",
    "passedTestCount": 10,
    "timeConsumedMillis": 300,
    "memoryConsumedBytes": 1024,
}

MOCK_WRONG_SUBMISSION = {
    **MOCK_SUBMISSION,
    "id": 2,
    "verdict": "WRONG_ANSWER",
}


def _cf_ok(result):
    return {"status": "OK", "result": result}


def _cf_err(comment):
    return {"status": "FAILED", "comment": comment}


# ── CF client tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_get_user_info_valid_handle():
    """Valid handle → returns CFUser with correct rating."""
    respx.get(f"{CF_BASE}/user.info").mock(
        return_value=httpx.Response(200, json=_cf_ok([MOCK_USER]))
    )
    async with CodeforcesClient() as cf:
        user = await cf.get_user_info("tourist")

    assert isinstance(user, CFUser)
    assert user.handle == "tourist"
    assert user.rating == 3979
    assert user.max_rating == 4009
    assert user.display_name == "Gennady Korotkevich"


@pytest.mark.asyncio
@respx.mock
async def test_get_user_info_invalid_handle():
    """Non-existent handle → raises CFHandleNotFound."""
    respx.get(f"{CF_BASE}/user.info").mock(
        return_value=httpx.Response(
            200,
            json=_cf_err("handles: User with handle nonexistent_xyz not found"),
        )
    )
    async with CodeforcesClient() as cf:
        with pytest.raises(CFHandleNotFound):
            await cf.get_user_info("nonexistent_xyz")


@pytest.mark.asyncio
@respx.mock
async def test_get_rating_history():
    """Rating history is parsed into CFRatingChange models."""
    respx.get(f"{CF_BASE}/user.rating").mock(
        return_value=httpx.Response(200, json=_cf_ok([MOCK_RATING_CHANGE]))
    )
    async with CodeforcesClient() as cf:
        history = await cf.get_rating_history("tourist")

    assert len(history) == 1
    rc = history[0]
    assert isinstance(rc, CFRatingChange)
    assert rc.contest_id == 1
    assert rc.old_rating == 1500
    assert rc.new_rating == 1730
    assert rc.delta == 230


@pytest.mark.asyncio
@respx.mock
async def test_get_submissions():
    """Submissions list is parsed into CFSubmission models."""
    respx.get(f"{CF_BASE}/user.status").mock(
        return_value=httpx.Response(
            200,
            json=_cf_ok([MOCK_SUBMISSION, MOCK_WRONG_SUBMISSION]),
        )
    )
    async with CodeforcesClient() as cf:
        subs = await cf.get_submissions("tourist")

    assert len(subs) == 2
    assert subs[0].verdict == "OK"
    assert subs[1].verdict == "WRONG_ANSWER"
    assert subs[0].problem.tags == ["math"]


@pytest.mark.asyncio
@respx.mock
async def test_get_solved_problems_deduplication():
    """get_solved_problems deduplicates AC submissions for the same problem."""
    # Two AC submissions on the same problem
    dup_sub = {**MOCK_SUBMISSION, "id": 99}
    respx.get(f"{CF_BASE}/user.status").mock(
        return_value=httpx.Response(
            200,
            json=_cf_ok([MOCK_SUBMISSION, dup_sub, MOCK_WRONG_SUBMISSION]),
        )
    )
    async with CodeforcesClient() as cf:
        solved = await cf.get_solved_problems("tourist")

    # Should deduplicate to 1 unique problem
    assert len(solved) == 1
    assert solved[0].name == "Theatre Square"


@pytest.mark.asyncio
@respx.mock
async def test_client_network_error_raises_cfapierror():
    """Network failure after all retries → CFAPIError."""
    respx.get(f"{CF_BASE}/user.info").mock(
        side_effect=httpx.NetworkError("unreachable")
    )
    async with CodeforcesClient(max_retries=1) as cf:
        with pytest.raises(CFAPIError, match="unreachable"):
            await cf.get_user_info("tourist")


# ── analytics engine tests (no network) ───────────────────────────────────

def _make_problem(rating=None, tags=None):
    return CFProblem(
        contestId=1,
        index="A",
        name="Test",
        rating=rating,
        tags=tags or [],
    )


def _make_submission(verdict="OK", tags=None, rating=None):
    prob = _make_problem(rating=rating, tags=tags or [])
    return CFSubmission(
        id=1,
        contestId=1,
        creationTimeSeconds=1700000000,
        problem=prob,
        author={},
        verdict=verdict,
        passedTestCount=1,
        timeConsumedMillis=100,
        memoryConsumedBytes=512,
    )


def test_compute_rating_trend_sorted():
    """Rating trend is returned in chronological order."""
    rc1 = CFRatingChange(
        contestId=2, contestName="Round 2", handle="h",
        rank=1, ratingUpdateTimeSeconds=2000,
        oldRating=1600, newRating=1700,
    )
    rc2 = CFRatingChange(
        contestId=1, contestName="Round 1", handle="h",
        rank=1, ratingUpdateTimeSeconds=1000,
        oldRating=1500, newRating=1600,
    )
    trend = compute_rating_trend([rc1, rc2])
    assert trend[0]["timestamp"] < trend[1]["timestamp"]
    assert trend[0]["newRating"] == 1600
    assert trend[1]["newRating"] == 1700


def test_compute_tag_stats_most_solved():
    """Most-solved tags are correctly counted."""
    problems = [
        _make_problem(tags=["dp", "math"]),
        _make_problem(tags=["dp"]),
        _make_problem(tags=["graphs"]),
    ]
    subs = [_make_submission(tags=["dp"]), _make_submission(tags=["dp"])]
    stats = compute_tag_stats(problems, subs)
    counts = {t["tag"]: t["count"] for t in stats["most_solved_tags"]}
    assert counts["dp"] == 2
    assert counts["math"] == 1
    assert counts["graphs"] == 1


def test_compute_difficulty_distribution_buckets():
    """Problems are bucketed into correct difficulty ranges."""
    problems = [
        _make_problem(rating=800),
        _make_problem(rating=1200),
        _make_problem(rating=1200),
        _make_problem(rating=None),  # unrated
    ]
    result = compute_difficulty_distribution(problems)
    dist = {b["range"]: b["count"] for b in result["distribution"]}
    assert dist.get("800–999", 0) == 1
    assert dist.get("1200–1399", 0) == 2
    assert dist.get("Unrated", 0) == 1
    assert result["avg_solved_rating"] == 1067  # (800+1200+1200)//3


def test_compute_submission_stats_success_rate():
    """Success rate is computed correctly."""
    subs = [
        _make_submission("OK"),
        _make_submission("OK"),
        _make_submission("WRONG_ANSWER"),
        _make_submission("TIME_LIMIT_EXCEEDED"),
    ]
    stats = compute_submission_stats(subs)
    assert stats["total_submissions"] == 4
    assert stats["accepted_count"] == 2
    assert stats["success_rate"] == pytest.approx(0.5)


def test_compute_submission_stats_empty():
    """Empty submission list returns zero values without error."""
    stats = compute_submission_stats([])
    assert stats["total_submissions"] == 0
    assert stats["success_rate"] == 0.0


def test_build_full_analytics_integration():
    """build_full_analytics produces a dict with all required top-level keys."""
    user = CFUser(
        handle="testuser",
        rating=1500,
        maxRating=1800,
        rank="expert",
        maxRank="candidate master",
        contribution=5,
        friendOfCount=100,
        registrationTimeSeconds=1268570400,
    )
    rc = CFRatingChange(
        contestId=1, contestName="Round 1", handle="testuser",
        rank=5, ratingUpdateTimeSeconds=1700000000,
        oldRating=1400, newRating=1500,
    )
    sub = _make_submission("OK", tags=["dp"], rating=1400)
    problem = _make_problem(tags=["dp"], rating=1400)

    analytics = build_full_analytics(
        user=user,
        rating_history=[rc],
        all_submissions=[sub],
        solved_problems=[problem],
    )

    required_keys = [
        "handle", "current_rating", "max_rating", "contests_participated",
        "solved_count", "rating_trend", "most_solved_tags", "weakest_tags",
        "strongest_tags", "difficulty_distribution", "avg_solved_rating",
        "total_submissions", "accepted_count", "success_rate",
        "activity_heatmap",
    ]
    for key in required_keys:
        assert key in analytics, f"Missing key: {key}"

    assert analytics["handle"] == "testuser"
    assert analytics["contests_participated"] == 1
    assert analytics["solved_count"] == 1


# ── API endpoint tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_ingest_endpoint_valid_handle():
    """POST /api/v1/codeforces/ingest returns 200 with full analytics."""
    from unittest.mock import AsyncMock, MagicMock, patch

    respx.get(f"{CF_BASE}/user.info").mock(
        return_value=httpx.Response(200, json=_cf_ok([MOCK_USER]))
    )
    respx.get(f"{CF_BASE}/user.rating").mock(
        return_value=httpx.Response(200, json=_cf_ok([MOCK_RATING_CHANGE]))
    )
    respx.get(f"{CF_BASE}/user.status").mock(
        return_value=httpx.Response(200, json=_cf_ok([MOCK_SUBMISSION]))
    )

    # Mock the DB upsert so we don't need a real PostgreSQL connection
    mock_user = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    from app.db.session import get_db

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.post(
                "/api/v1/codeforces/ingest",
                json={"cf_handle": "tourist", "force_refresh": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    data = r.json()
    assert data["handle"] == "tourist"
    assert data["current_rating"] == 3979
    assert "rating_trend" in data
    assert "most_solved_tags" in data
    assert "activity_heatmap" in data


@pytest.mark.asyncio
@respx.mock
async def test_ingest_endpoint_invalid_handle():
    """POST /api/v1/codeforces/ingest returns 404 for unknown handle."""
    respx.get(f"{CF_BASE}/user.info").mock(
        return_value=httpx.Response(
            200,
            json=_cf_err("handles: User with handle ghost_handle_xyz not found"),
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/api/v1/codeforces/ingest",
            json={"cf_handle": "ghost_handle_xyz", "force_refresh": True},
        )

    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_phase1_tests_still_pass(db_session, mock_cf_network):
    """Regression: all Phase 1 endpoints continue to work in Phase 2+."""
    from app.db.session import get_db
    from app.models.user import User

    user = User(cf_handle="tourist", current_rating=1450, max_rating=1500, cf_analytics={})
    db_session.add(user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            ping = await ac.get("/api/v1/health/ping")
            assert ping.status_code == 200
            assert ping.json() == {"ping": "pong"}

            root = await ac.get("/")
            assert root.status_code == 200
            assert "CodeMentor AI" in root.json()["message"]

            chat = await ac.post(
                "/api/v1/chat",
                json={
                    "session_id": "test-001",
                    "cf_handle": "tourist",
                    "message": "Hello!",
                },
            )
            assert chat.status_code == 200
            assert chat.json()["message"]["role"] == "assistant"
    finally:
        app.dependency_overrides.clear()