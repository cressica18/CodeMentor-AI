"""
Phase 4 tests - agentic workflow.

Mirrors the structure/conventions of tests/test_phase3.py: unit tests
for the pure analyzer/planner functions, integration tests against a
real (in-memory SQLite) DB for the orchestrator + LangGraph execution,
and API endpoint tests via httpx AsyncClient with the DB dependency
overridden.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import get_db
from app.models.user import User
from app.models.agent import AgentRun, AgentTrace, AnalysisSnapshot, PlannerOutput, GraphCheckpoint
from app.agents.analyzer import run_analyzer_agent
from app.agents.planner import run_planner_agent
from app.agents.graph import build_mentor_graph
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService
from app.services.recommender_service import RecommenderService


@pytest_asyncio.fixture(autouse=True)
async def _auto_mock_cf_network(mock_cf_network):
    """Phase 4's full orchestrator run now also executes RecommenderAgent."""
    yield


SAMPLE_CF_ANALYTICS = {
    "handle": "memtest_user",
    "current_rating": 1450,
    "max_rating": 1500,
    "solved_count": 120,
    "contests_participated": 15,
    "success_rate": 0.42,
    "total_submissions": 300,
    "accepted_count": 126,
    "weakest_tags": [
        {"tag": "graphs", "acRate": 0.2},
        {"tag": "dp", "acRate": 0.3},
        {"tag": "segment_trees", "acRate": 0.25},
    ],
    "strongest_tags": [
        {"tag": "math", "acRate": 0.9},
        {"tag": "greedy", "acRate": 0.85},
    ],
    "tag_ac_rates": {"graphs": 0.2, "dp": 0.3, "segment_trees": 0.25, "math": 0.9, "greedy": 0.85},
    "rating_trend": [
        {"contestId": 1, "contest": "Round A", "date": "2026-01-01", "timestamp": 1735689600, "oldRating": 1300, "newRating": 1350, "delta": 50, "rank": 100},
        {"contestId": 2, "contest": "Round B", "date": "2026-02-01", "timestamp": 1738368000, "oldRating": 1350, "newRating": 1330, "delta": -20, "rank": 500},
        {"contestId": 3, "contest": "Round C", "date": "2026-03-01", "timestamp": 1740787200, "oldRating": 1330, "newRating": 1450, "delta": 120, "rank": 50},
    ],
}


# -- Analyzer Agent (pure function) unit tests -----------------------------


def test_analyzer_agent_produces_required_fields():
    memory = {
        "cf_handle": "memtest_user",
        "cf_analytics": SAMPLE_CF_ANALYTICS,
        "profile": {"improvement_velocity": None},
        "topic_ratings": [],
    }
    result = run_analyzer_agent(memory)

    assert set(["strengths", "weaknesses", "priority_topics", "improvement_velocity", "analysis_summary"]).issubset(result.keys())
    assert "graphs" in result["weaknesses"]
    assert "math" in result["strengths"]
    assert isinstance(result["improvement_velocity"], float)
    assert isinstance(result["analysis_summary"], str) and len(result["analysis_summary"]) > 0


def test_analyzer_agent_merges_long_term_topic_ratings():
    memory = {
        "cf_handle": "memtest_user",
        "cf_analytics": SAMPLE_CF_ANALYTICS,
        "profile": {"improvement_velocity": 1.5},
        "topic_ratings": [
            {"topic": "binary_search", "rating": 0.1, "is_weakness": True, "is_strength": False},
        ],
    }
    result = run_analyzer_agent(memory)
    assert "binary_search" in result["weaknesses"]
    assert result["improvement_velocity"] == 1.5


def test_analyzer_agent_handles_empty_memory_gracefully():
    result = run_analyzer_agent({"cf_handle": "nobody", "cf_analytics": {}, "profile": {}, "topic_ratings": []})
    assert result["strengths"] == []
    assert result["weaknesses"] == []
    assert result["improvement_velocity"] == 0.0
    assert "nobody" in result["analysis_summary"]


# -- Planner Agent (pure function) unit tests ------------------------------


def test_planner_agent_produces_required_fields():
    analysis = run_analyzer_agent(
        {"cf_handle": "memtest_user", "cf_analytics": SAMPLE_CF_ANALYTICS, "profile": {}, "topic_ratings": []}
    )
    memory = {"preferences": {"daily_goal_minutes": 90}, "learning_path": {}}
    plan = run_planner_agent(analysis, memory)

    assert set(["study_plan", "milestones", "weekly_schedule", "priority_topics", "estimated_duration"]).issubset(plan.keys())
    assert isinstance(plan["milestones"], list) and len(plan["milestones"]) > 0
    assert isinstance(plan["weekly_schedule"], list) and len(plan["weekly_schedule"]) > 0
    assert plan["estimated_duration"].endswith("weeks")
    assert plan["priority_topics"] == analysis["priority_topics"]


def test_planner_agent_pads_duration_on_declining_trajectory():
    analysis = {"priority_topics": ["graphs"], "strengths": [], "improvement_velocity": -2.0, "analysis_summary": ""}
    plan_declining = run_planner_agent(analysis, {})

    analysis_up = {**analysis, "improvement_velocity": 2.0}
    plan_improving = run_planner_agent(analysis_up, {})

    declining_weeks = int(plan_declining["estimated_duration"].split()[0])
    improving_weeks = int(plan_improving["estimated_duration"].split()[0])
    assert declining_weeks > improving_weeks


def test_planner_agent_falls_back_to_baseline_with_no_topics():
    analysis = {"priority_topics": [], "strengths": [], "improvement_velocity": 0.0, "analysis_summary": ""}
    plan = run_planner_agent(analysis, {})
    assert any(m["type"] == "baseline" for m in plan["milestones"])


# -- LangGraph + orchestrator integration tests ----------------------------


@pytest_asyncio.fixture
async def user_with_analytics(db_session) -> User:
    user = User(cf_handle="agentuser", current_rating=1450, max_rating=1500, cf_analytics=SAMPLE_CF_ANALYTICS)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_langgraph_compiles_and_runs_full_workflow(db_session, user_with_analytics):
    graph = build_mentor_graph(lambda: MemoryService(db_session))
    initial_state = {"cf_handle": user_with_analytics.cf_handle, "thread_id": "t1", "run_type": "full", "trace": []}

    final_state = await graph.ainvoke(initial_state)

    assert "memory" in final_state
    assert "analysis" in final_state
    assert "plan" in final_state
    assert "recommendations" in final_state
    assert final_state.get("persisted") is True
    assert final_state["analysis"]["weaknesses"]
    assert final_state["plan"]["estimated_duration"].endswith("weeks")


@pytest.mark.asyncio
async def test_langgraph_persists_to_memory_layer(db_session, user_with_analytics):
    graph = build_mentor_graph(lambda: MemoryService(db_session))
    await graph.ainvoke({"cf_handle": user_with_analytics.cf_handle, "thread_id": "t2", "run_type": "full", "trace": []})

    svc = MemoryService(db_session)
    profile = await svc.get_or_create_profile(user_with_analytics.cf_handle)
    learning_path = await svc.get_or_create_learning_path(user_with_analytics.cf_handle)

    assert profile.weaknesses  # synced from AnalyzerAgent
    assert learning_path.state  # synced from PlannerAgent


@pytest.mark.asyncio
async def test_agent_service_run_orchestrator_persists_run_and_traces(db_session, user_with_analytics):
    svc = AgentService(db_session)
    result = await svc.run_orchestrator(user_with_analytics.cf_handle, run_type="full")

    assert result["run"].status == "completed"
    assert result["run"].thread_id.startswith("mentor-agentuser-")
    assert len(result["traces"]) == 5
    node_names = [t.node_name for t in result["traces"]]
    assert node_names == ["RetrieveMemory", "AnalyzerAgent", "PlannerAgent", "RecommenderAgent", "PersistMemory"]
    assert result["analysis"]["weaknesses"]
    assert result["plan"]["milestones"]


@pytest.mark.asyncio
async def test_agent_service_persists_analysis_snapshot_and_planner_output(db_session, user_with_analytics):
    svc = AgentService(db_session)
    await svc.run_orchestrator(user_with_analytics.cf_handle, run_type="full")

    from sqlalchemy import select

    snap_result = await db_session.execute(select(AnalysisSnapshot).where(AnalysisSnapshot.user_id == user_with_analytics.id))
    snapshots = list(snap_result.scalars().all())
    assert len(snapshots) == 1

    plan_result = await db_session.execute(select(PlannerOutput).where(PlannerOutput.user_id == user_with_analytics.id))
    plans = list(plan_result.scalars().all())
    assert len(plans) == 1
    assert plans[0].analysis_snapshot_id == snapshots[0].id


@pytest.mark.asyncio
async def test_agent_service_writes_graph_checkpoints(db_session, user_with_analytics):
    svc = AgentService(db_session)
    result = await svc.run_orchestrator(user_with_analytics.cf_handle, run_type="full")

    from sqlalchemy import select

    cp_result = await db_session.execute(
        select(GraphCheckpoint).where(GraphCheckpoint.agent_run_id == result["run"].id).order_by(GraphCheckpoint.step_index)
    )
    checkpoints = list(cp_result.scalars().all())
    assert len(checkpoints) == 5
    assert checkpoints[-1].node_name == "PersistMemory"
    assert checkpoints[-1].state.get("persisted") is True


@pytest.mark.asyncio
async def test_agent_service_get_history_and_traces(db_session, user_with_analytics):
    svc = AgentService(db_session)
    await svc.run_orchestrator(user_with_analytics.cf_handle, run_type="full")

    history = await svc.get_history(cf_handle=user_with_analytics.cf_handle)
    assert len(history) == 1

    traces = await svc.get_traces(history[0].id)
    assert len(traces) == 5


@pytest.mark.asyncio
async def test_agent_service_run_fails_for_unknown_handle(db_session):
    svc = AgentService(db_session)
    from app.services.memory_service import MemoryNotFoundError

    with pytest.raises(MemoryNotFoundError):
        await svc.run_orchestrator("no_such_handle", run_type="full")


# -- API endpoint tests (FastAPI TestClient, real SQLite DB via override) --


@pytest.mark.asyncio
async def test_agents_run_endpoint(db_session, user_with_analytics):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post("/api/v1/agents/run", json={"cf_handle": user_with_analytics.cf_handle})
            assert r.status_code == 200
            body = r.json()
            assert body["run"]["status"] == "completed"
            assert len(body["traces"]) == 5
            assert body["analysis"]["weaknesses"]
            assert body["plan"]["milestones"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_agents_analyze_and_plan_endpoints(db_session, user_with_analytics):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r1 = await ac.post("/api/v1/agents/analyze", json={"cf_handle": user_with_analytics.cf_handle})
            assert r1.status_code == 200
            assert r1.json()["run"]["run_type"] == "analyze"

            r2 = await ac.post("/api/v1/agents/plan", json={"cf_handle": user_with_analytics.cf_handle})
            assert r2.status_code == 200
            assert r2.json()["run"]["run_type"] == "plan"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_agents_history_and_traces_endpoints(db_session, user_with_analytics):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            run_resp = await ac.post("/api/v1/agents/run", json={"cf_handle": user_with_analytics.cf_handle})
            run_id = run_resp.json()["run"]["id"]

            hist = await ac.get("/api/v1/agents/history", params={"cf_handle": user_with_analytics.cf_handle})
            assert hist.status_code == 200
            assert len(hist.json()) == 1

            tr = await ac.get("/api/v1/agents/traces", params={"agent_run_id": run_id})
            assert tr.status_code == 200
            assert len(tr.json()) == 5
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_agents_run_endpoint_404_for_unknown_handle(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post("/api/v1/agents/run", json={"cf_handle": "ghost_user"})
            assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_agents_latest_analysis_and_plan_endpoints(db_session, user_with_analytics):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/api/v1/agents/run", json={"cf_handle": user_with_analytics.cf_handle})

            r1 = await ac.get(f"/api/v1/agents/analysis/{user_with_analytics.cf_handle}/latest")
            assert r1.status_code == 200
            assert r1.json()["weaknesses"]

            r2 = await ac.get(f"/api/v1/agents/plan/{user_with_analytics.cf_handle}/latest")
            assert r2.status_code == 200
            assert r2.json()["milestones"]
    finally:
        app.dependency_overrides.clear()
