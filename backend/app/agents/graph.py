"""
LangGraph workflow definition.

    START -> RetrieveMemory -> AnalyzerAgent -> PlannerAgent -> RecommenderAgent -> PersistMemory -> END

Phase 5 extends the Phase 4 linear flow with a RecommenderAgent node
between Planner and Persist, per the Phase 5 spec. No conditional
routing, reflection loops, or RAG are introduced — those remain
deferred to future phases.

Memory retrieval/persistence and the Recommender's CF API + problem
pool lookups are async (DB + network I/O), so each node is an async
function and the graph is invoked with `await graph.ainvoke(...)`.

Node implementations here are intentionally thin — they call into
`app/agents/analyzer.py` / `app/agents/planner.py` / `app/agents/recommender.py`
for the actual (pure, synchronous) computation, and into
`MemoryService` / `RecommenderService` for I/O. This keeps the
LangGraph wiring itself trivial to read and test.
"""

from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import StateGraph, START, END

from app.agents.analyzer import run_analyzer_agent
from app.agents.planner import run_planner_agent
from app.agents.state import MentorGraphState
from app.core.logging import get_logger
from app.services.memory_service import MemoryService
from app.services.recommender_service import RecommenderService

logger = get_logger(__name__)

NODE_RETRIEVE_MEMORY = "RetrieveMemory"
NODE_ANALYZER_AGENT = "AnalyzerAgent"
NODE_PLANNER_AGENT = "PlannerAgent"
NODE_RECOMMENDER_AGENT = "RecommenderAgent"
NODE_PERSIST_MEMORY = "PersistMemory"

GRAPH_NODE_ORDER = [
    NODE_RETRIEVE_MEMORY,
    NODE_ANALYZER_AGENT,
    NODE_PLANNER_AGENT,
    NODE_RECOMMENDER_AGENT,
    NODE_PERSIST_MEMORY,
]


def _record_step(state: MentorGraphState, node_name: str, input_summary: dict, output_summary: dict) -> dict[str, Any]:
    """Append a trace entry to the running `trace` list in graph state."""
    trace = list(state.get("trace") or [])
    trace.append(
        {
            "node": node_name,
            "input_summary": input_summary,
            "output_summary": output_summary,
        }
    )
    return {"trace": trace}


def make_retrieve_memory_node(memory_service_factory: Callable[[], MemoryService]):
    async def retrieve_memory(state: MentorGraphState) -> dict[str, Any]:
        cf_handle = state["cf_handle"]
        svc = memory_service_factory()

        profile = await svc.get_or_create_profile(cf_handle)
        topic_ratings = await svc.get_topic_ratings(cf_handle)
        learning_path = await svc.get_or_create_learning_path(cf_handle)
        recent_sessions = await svc.get_study_sessions(cf_handle, limit=10)
        recent_recs = await svc.get_recommendations(cf_handle, limit=10)
        progress_snapshots = await svc.get_progress_snapshots(cf_handle, limit=10)
        preferences = await svc.get_or_create_preferences(cf_handle)
        user = await svc._get_user_by_handle(cf_handle)  # noqa: SLF001 — internal helper reused intentionally

        cf_analytics = user.cf_analytics or {}

        memory_snapshot = {
            "cf_handle": cf_handle,
            "cf_analytics": cf_analytics,
            "profile": {
                "improvement_velocity": profile.improvement_velocity,
                "strengths": profile.strengths,
                "weaknesses": profile.weaknesses,
                "current_streak_days": profile.current_streak_days,
            },
            "topic_ratings": [
                {
                    "topic": tr.topic,
                    "rating": tr.rating,
                    "is_strength": tr.is_strength,
                    "is_weakness": tr.is_weakness,
                    "problems_solved": tr.problems_solved,
                    "problems_failed": tr.problems_failed,
                }
                for tr in topic_ratings
            ],
            "learning_path": {
                "goal": learning_path.goal,
                "current_stage": learning_path.current_stage,
                "progress_percent": learning_path.progress_percent,
                "state": learning_path.state,
            },
            "recent_study_sessions": [
                {"topic": s.topic, "problems_solved": s.problems_solved, "problems_attempted": s.problems_attempted}
                for s in recent_sessions
            ],
            "recent_recommendations": [
                {"rec_type": r.rec_type, "payload": r.payload, "status": r.status} for r in recent_recs
            ],
            "progress_snapshots": [
                {"rating": p.rating, "snapshot_at": p.snapshot_at.isoformat() if p.snapshot_at else None}
                for p in progress_snapshots
            ],
            "preferences": {
                "preferred_difficulty": preferences.preferred_difficulty,
                "preferred_topics": preferences.preferred_topics,
                "daily_goal_minutes": preferences.daily_goal_minutes,
            },
        }

        update = _record_step(
            state,
            NODE_RETRIEVE_MEMORY,
            input_summary={"cf_handle": cf_handle},
            output_summary={
                "has_cf_analytics": bool(cf_analytics),
                "topic_ratings_count": len(topic_ratings),
                "recent_sessions_count": len(recent_sessions),
            },
        )
        update["memory"] = memory_snapshot
        return update

    return retrieve_memory


async def analyzer_agent_node(state: MentorGraphState) -> dict[str, Any]:
    memory = state.get("memory") or {}
    analysis = run_analyzer_agent(memory)  # type: ignore[arg-type]

    update = _record_step(
        state,
        NODE_ANALYZER_AGENT,
        input_summary={"cf_handle": state.get("cf_handle")},
        output_summary={
            "strengths": analysis.get("strengths"),
            "weaknesses": analysis.get("weaknesses"),
            "priority_topics": analysis.get("priority_topics"),
            "improvement_velocity": analysis.get("improvement_velocity"),
        },
    )
    update["analysis"] = analysis
    return update


async def planner_agent_node(state: MentorGraphState) -> dict[str, Any]:
    analysis = state.get("analysis") or {}
    memory = state.get("memory") or {}
    plan = run_planner_agent(analysis, memory)  # type: ignore[arg-type]

    update = _record_step(
        state,
        NODE_PLANNER_AGENT,
        input_summary={"priority_topics": analysis.get("priority_topics")},
        output_summary={
            "estimated_duration": plan.get("estimated_duration"),
            "milestones_count": len(plan.get("milestones") or []),
            "weekly_schedule_weeks": len(plan.get("weekly_schedule") or []),
        },
    )
    update["plan"] = plan
    return update


def make_recommender_agent_node(recommender_service_factory: Callable[[], RecommenderService]):
    async def recommender_agent_node(state: MentorGraphState) -> dict[str, Any]:
        cf_handle = state["cf_handle"]
        analysis = state.get("analysis") or {}
        svc = recommender_service_factory()

        result = await svc.generate_recommendations(cf_handle, analysis)  # type: ignore[arg-type]

        recommendations_payload = {
            "recommendations": result["recommendations"],
            "strategy": result["strategy"],
            "reasoning": result["reasoning"],
        }

        update = _record_step(
            state,
            NODE_RECOMMENDER_AGENT,
            input_summary={"cf_handle": cf_handle, "priority_topics": analysis.get("priority_topics")},
            output_summary={
                "recommendations_count": len(result["recommendations"]),
                "strategies_used": list(result["strategy"].keys()),
            },
        )
        update["recommendations"] = recommendations_payload
        # Stash DB ids so PersistMemory / the API layer can reference the
        # already-persisted rows without re-querying.
        update["_recommendation_session_id"] = result["session"].id
        return update

    return recommender_agent_node


def make_persist_memory_node(memory_service_factory: Callable[[], MemoryService]):
    async def persist_memory(state: MentorGraphState) -> dict[str, Any]:
        cf_handle = state["cf_handle"]
        analysis = state.get("analysis") or {}
        plan = state.get("plan") or {}
        svc = memory_service_factory()

        # Sync strengths/weaknesses onto the long-term UserProfile so
        # future RetrieveMemory calls (and the existing Phase 3 frontend
        # memory pages) see the agent's latest findings.
        await svc.update_profile(
            cf_handle,
            strengths=analysis.get("strengths"),
            weaknesses=analysis.get("weaknesses"),
        )

        # Sync the generated study plan onto the long-term LearningPath.
        study_plan = plan.get("study_plan") or {}
        await svc.update_learning_path(
            cf_handle,
            goal=study_plan.get("goal"),
            current_stage=study_plan.get("current_stage"),
            state={**study_plan, "milestones": plan.get("milestones"), "weekly_schedule": plan.get("weekly_schedule")},
        )

        # BUG 1 fix: persist a TopicRating row per topic the Analyzer scored
        # (was previously computed but never written, so the table stayed
        # at 0 rows regardless of how many runs executed).
        topic_ratings = await svc.sync_topic_ratings_from_analysis(cf_handle, analysis)

        # BUG 2 fix: persist a LearningMilestone row per milestone the
        # Planner generated (same class of bug — computed, never written).
        milestones = await svc.sync_milestones_from_plan(cf_handle, plan.get("milestones") or [])

        # BUG 3 fix: record that a full mentor workflow run happened, so
        # `study_sessions` reflects agent activity, not just solve/skip
        # clicks from the recommendations UI.
        priority_topics = analysis.get("priority_topics") or []
        await svc.record_workflow_session(
            cf_handle,
            session_type="mentor_workflow",
            topic=priority_topics[0] if priority_topics else None,
            notes=f"Full mentor workflow run; {len(topic_ratings)} topic ratings, {len(milestones)} milestones synced.",
        )

        update = _record_step(
            state,
            NODE_PERSIST_MEMORY,
            input_summary={"cf_handle": cf_handle},
            output_summary={
                "profile_updated": True,
                "learning_path_updated": True,
                "topic_ratings_synced": len(topic_ratings),
                "milestones_synced": len(milestones),
            },
        )
        update["persisted"] = True
        return update

    return persist_memory


def build_mentor_graph(
    memory_service_factory: Callable[[], MemoryService],
    recommender_service_factory: Callable[[], RecommenderService] | None = None,
):
    """
    Compile the LangGraph mentor workflow.

    `memory_service_factory` / `recommender_service_factory` are
    injected (rather than constructing services inline) so the same
    graph definition can be reused against any `AsyncSession` —
    production DB session or a test SQLite session — without
    rebuilding the graph per request.

    `recommender_service_factory` defaults to building a
    `RecommenderService` over the same session as the memory service
    when not explicitly provided (kept optional for backwards
    compatibility with any Phase 4 caller that only passes one
    factory).
    """
    if recommender_service_factory is None:
        recommender_service_factory = lambda: RecommenderService(memory_service_factory()._db)  # noqa: E731,SLF001

    graph = StateGraph(MentorGraphState)

    graph.add_node(NODE_RETRIEVE_MEMORY, make_retrieve_memory_node(memory_service_factory))
    graph.add_node(NODE_ANALYZER_AGENT, analyzer_agent_node)
    graph.add_node(NODE_PLANNER_AGENT, planner_agent_node)
    graph.add_node(NODE_RECOMMENDER_AGENT, make_recommender_agent_node(recommender_service_factory))
    graph.add_node(NODE_PERSIST_MEMORY, make_persist_memory_node(memory_service_factory))

    graph.add_edge(START, NODE_RETRIEVE_MEMORY)
    graph.add_edge(NODE_RETRIEVE_MEMORY, NODE_ANALYZER_AGENT)
    graph.add_edge(NODE_ANALYZER_AGENT, NODE_PLANNER_AGENT)
    graph.add_edge(NODE_PLANNER_AGENT, NODE_RECOMMENDER_AGENT)
    graph.add_edge(NODE_RECOMMENDER_AGENT, NODE_PERSIST_MEMORY)
    graph.add_edge(NODE_PERSIST_MEMORY, END)

    return graph.compile()