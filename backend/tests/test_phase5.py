"""
Phase 5 tests — Problem Recommender Agent + recommendation engine.

Mirrors the structure/conventions of tests/test_phase4.py. The live
Codeforces network calls (problem pool + solved problems) are
monkeypatched offline via the autouse `mock_cf_network` fixture in
conftest.py, so these tests are fully deterministic.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.db.session import get_db
from app.models.user import User
from app.models.recommendation_engine import RecommendedProblem, RecommendationSession, ProblemAttempt
from app.agents.recommender import run_recommender_agent
from app.agents.graph import build_mentor_graph
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService
from app.services.recommender_service import RecommenderService
from app.services.problem_pool_service import ProblemPoolService


SAMPLE_POOL = [
    {"contest_id": 1, "index": "A", "name": "Watermelon", "rating": 800, "tags": ["math", "brute force"]},
    {"contest_id": 580, "index": "C", "name": "Kefa and Park", "rating": 1500, "tags": ["dfs and similar", "graphs", "trees"]},
    {"contest_id": 1547, "index": "F", "name": "Array Stabilization", "rating": 1700, "tags": ["graphs", "shortest paths"]},
    {"contest_id": 1632, "index": "D", "name": "New Year Concert", "rating": 1900, "tags": ["dp", "greedy"]},
    {"contest_id": 1234, "index": "D", "name": "Distinct Characters Queries", "rating": 2100, "tags": ["dsu", "graphs"]},
    {"contest_id": 4, "index": "C", "name": "Registration System", "rating": 1300, "tags": ["math"]},
]

SAMPLE_ANALYSIS = {
    "strengths": ["math"],
    "weaknesses": ["graphs"],
    "priority_topics": ["graphs"],
    "improvement_velocity": -0.5,
    "analysis_summary": "test summary",
    "_extra": {"contest_behavior": {"negative_streak": 1}},
}


# -- Recommender Agent (pure function) unit tests --------------------------


def test_recommender_agent_never_fabricates_problems():
    """Every recommendation must come from the supplied problem_pool — no invented problems."""
    result = run_recommender_agent(
        SAMPLE_ANALYSIS, current_rating=1400, problem_pool=SAMPLE_POOL, solved_keys=set()
    )
    pool_keys = {(p["contest_id"], p["index"]) for p in SAMPLE_POOL}
    for rec in result["recommendations"]:
        assert (rec["contest_id"], rec["index"]) in pool_keys


def test_recommender_agent_excludes_solved_problems():
    solved = {(1, "A"), (4, "C")}
    result = run_recommender_agent(
        SAMPLE_ANALYSIS, current_rating=1400, problem_pool=SAMPLE_POOL, solved_keys=solved
    )
    for rec in result["recommendations"]:
        assert (rec["contest_id"], rec["index"]) not in solved


def test_recommender_agent_excludes_recently_recommended():
    recent = {(580, "C")}
    result = run_recommender_agent(
        SAMPLE_ANALYSIS,
        current_rating=1400,
        problem_pool=SAMPLE_POOL,
        solved_keys=set(),
        recent_recommendation_keys=recent,
    )
    for rec in result["recommendations"]:
        assert (rec["contest_id"], rec["index"]) not in recent


def test_recommender_agent_reinforcement_targets_weak_topics():
    result = run_recommender_agent(
        SAMPLE_ANALYSIS, current_rating=1400, problem_pool=SAMPLE_POOL, solved_keys=set()
    )
    reinforcement = [r for r in result["recommendations"] if r["recommendation_type"] == "reinforcement"]
    assert reinforcement
    for r in reinforcement:
        assert "graphs" in r["tags"]


def test_recommender_agent_recovery_only_when_negative_streak():
    no_streak = run_recommender_agent(
        SAMPLE_ANALYSIS, current_rating=1400, problem_pool=SAMPLE_POOL, solved_keys=set(), negative_streak=0
    )
    with_streak = run_recommender_agent(
        SAMPLE_ANALYSIS, current_rating=1400, problem_pool=SAMPLE_POOL, solved_keys=set(), negative_streak=3
    )
    assert "recovery" not in no_streak["strategy"]
    assert "recovery" in with_streak["strategy"]


def test_recommender_agent_returns_reasoning_and_strategy():
    result = run_recommender_agent(
        SAMPLE_ANALYSIS, current_rating=1400, problem_pool=SAMPLE_POOL, solved_keys=set()
    )
    assert isinstance(result["reasoning"], str) and len(result["reasoning"]) > 0
    assert isinstance(result["strategy"], dict) and len(result["strategy"]) > 0


def test_recommender_agent_handles_empty_pool_gracefully():
    result = run_recommender_agent(SAMPLE_ANALYSIS, current_rating=1400, problem_pool=[], solved_keys=set())
    assert result["recommendations"] == []


# -- ProblemPoolService -----------------------------------------------------


@pytest.mark.asyncio
async def test_problem_pool_service_returns_only_rated_problems(monkeypatch):
    """Confirms the pool-builder filters to problems with both contest_id and rating set."""
    from app.codeforces.models import CFProblem

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get_problemset(self):
            return [
                CFProblem(contestId=1, index="A", name="Has Rating", rating=800, tags=["math"]),
                CFProblem(contestId=2, index="B", name="No Rating", rating=None, tags=["math"]),
            ]

    import app.services.problem_pool_service as mod

    monkeypatch.setattr(mod, "CodeforcesClient", _FakeClient)
    ProblemPoolService._cache = None
    pool = await ProblemPoolService.get_pool(force_refresh=True)
    assert len(pool) == 1
    assert pool[0]["name"] == "Has Rating"


# -- LangGraph + RecommenderService integration tests -----------------------


@pytest_asyncio.fixture
async def user_for_recs(db_session) -> User:
    user = User(cf_handle="recuser", current_rating=1400, max_rating=1500)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_recommender_service_persists_session_and_problems(db_session, user_for_recs, mock_cf_network):
    svc = RecommenderService(db_session)
    result = await svc.generate_recommendations(user_for_recs.cf_handle, SAMPLE_ANALYSIS)

    assert result["recommended_problems"]
    assert result["session"].id is not None

    session_result = await db_session.execute(
        select(RecommendationSession).where(RecommendationSession.user_id == user_for_recs.id)
    )
    sessions = list(session_result.scalars().all())
    assert len(sessions) == 1

    rec_result = await db_session.execute(
        select(RecommendedProblem).where(RecommendedProblem.user_id == user_for_recs.id)
    )
    rows = list(rec_result.scalars().all())
    assert len(rows) == len(result["recommended_problems"])
    assert all(r.recommendation_session_id == sessions[0].id for r in rows)


@pytest.mark.asyncio
async def test_recommender_service_update_problem_status_solve(db_session, user_for_recs, mock_cf_network):
    svc = RecommenderService(db_session)
    result = await svc.generate_recommendations(user_for_recs.cf_handle, SAMPLE_ANALYSIS)
    problem = result["recommended_problems"][0]

    updated = await svc.update_problem_status(problem.id, "solve")
    assert updated.solved is True
    assert updated.attempted is True

    attempt_result = await db_session.execute(
        select(ProblemAttempt).where(ProblemAttempt.recommended_problem_id == problem.id)
    )
    attempts = list(attempt_result.scalars().all())
    assert len(attempts) == 1
    assert attempts[0].status == "solved"


@pytest.mark.asyncio
async def test_recommender_service_update_problem_status_bookmark(db_session, user_for_recs, mock_cf_network):
    svc = RecommenderService(db_session)
    result = await svc.generate_recommendations(user_for_recs.cf_handle, SAMPLE_ANALYSIS)
    problem = result["recommended_problems"][0]

    updated = await svc.update_problem_status(problem.id, "bookmark")
    assert updated.bookmarked is True


@pytest.mark.asyncio
async def test_recommender_service_get_recommendations_filters_by_status(db_session, user_for_recs, mock_cf_network):
    svc = RecommenderService(db_session)
    result = await svc.generate_recommendations(user_for_recs.cf_handle, SAMPLE_ANALYSIS)
    first = result["recommended_problems"][0]
    await svc.update_problem_status(first.id, "solve")

    solved = await svc.get_recommendations(user_for_recs.cf_handle, status="solved")
    pending = await svc.get_recommendations(user_for_recs.cf_handle, status="pending")

    assert any(r.id == first.id for r in solved)
    assert all(r.id != first.id for r in pending)


@pytest.mark.asyncio
async def test_langgraph_full_workflow_includes_recommender(db_session, user_for_recs, mock_cf_network):
    graph = build_mentor_graph(lambda: MemoryService(db_session), lambda: RecommenderService(db_session))
    final_state = await graph.ainvoke(
        {"cf_handle": user_for_recs.cf_handle, "thread_id": "rt1", "run_type": "full", "trace": []}
    )

    assert "recommendations" in final_state
    assert final_state["recommendations"]["recommendations"]
    node_names = [t["node"] for t in final_state["trace"]]
    assert node_names == ["RetrieveMemory", "AnalyzerAgent", "PlannerAgent", "RecommenderAgent", "PersistMemory"]


@pytest.mark.asyncio
async def test_agent_service_run_persists_recommended_problems(db_session, user_for_recs, mock_cf_network):
    svc = AgentService(db_session)
    result = await svc.run_orchestrator(user_for_recs.cf_handle, run_type="full")

    assert result["recommendations"]["recommendations"]

    rec_result = await db_session.execute(
        select(RecommendedProblem).where(RecommendedProblem.user_id == user_for_recs.id)
    )
    rows = list(rec_result.scalars().all())
    assert len(rows) == len(result["recommendations"]["recommendations"])


# -- API endpoint tests ------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_recommendations_endpoint(client, db_session, user_for_recs, mock_cf_network):
    resp = await client.post("/api/v1/recommendations/generate", json={"cf_handle": user_for_recs.cf_handle})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    assert "recommendation_type" in body[0]
    assert "url" in body[0]


@pytest.mark.asyncio
async def test_list_recommendations_endpoint(client, db_session, user_for_recs, mock_cf_network):
    await client.post("/api/v1/recommendations/generate", json={"cf_handle": user_for_recs.cf_handle})
    resp = await client.get(f"/api/v1/recommendations/{user_for_recs.cf_handle}")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


@pytest.mark.asyncio
async def test_update_recommendation_endpoint(client, db_session, user_for_recs, mock_cf_network):
    gen_resp = await client.post("/api/v1/recommendations/generate", json={"cf_handle": user_for_recs.cf_handle})
    problem_id = gen_resp.json()[0]["id"]

    resp = await client.patch(f"/api/v1/recommendations/item/{problem_id}", json={"action": "solve"})
    assert resp.status_code == 200
    assert resp.json()["solved"] is True


@pytest.mark.asyncio
async def test_update_recommendation_endpoint_invalid_action_rejected(client, db_session, user_for_recs, mock_cf_network):
    gen_resp = await client.post("/api/v1/recommendations/generate", json={"cf_handle": user_for_recs.cf_handle})
    problem_id = gen_resp.json()[0]["id"]

    resp = await client.patch(f"/api/v1/recommendations/item/{problem_id}", json={"action": "explode"})
    assert resp.status_code == 422  # pydantic pattern validation rejects unknown actions


@pytest.mark.asyncio
async def test_agents_run_endpoint_includes_recommendations(client, db_session, user_for_recs, mock_cf_network):
    resp = await client.post("/api/v1/agents/run", json={"cf_handle": user_for_recs.cf_handle})
    assert resp.status_code == 200
    body = resp.json()
    assert body["recommendations"] is not None
    assert len(body["recommendations"]["recommendations"]) > 0
    assert len(body["traces"]) == 5
