"""
AgentService - Phase 4 orchestration + persistence glue.

This is the single entry point the API routes use to trigger the
LangGraph mentor workflow. It:

  1. builds the compiled graph (bound to the current request's DB
     session via a MemoryService factory),
  2. streams the graph node-by-node (astream(..., stream_mode="updates"))
     so each node's execution can be timed and persisted individually,
  3. persists an AgentRun row for the overall execution and one
     AgentTrace row per node (powers the Agent Trace Panel),
  4. persists AnalysisSnapshot / PlannerOutput rows for the
     structured agent outputs (powers the Agent Dashboard / Study
     Planner pages and GET /agents/history),
  5. writes a GraphCheckpoint row per step with the full running
     state (checkpoint preparation, per the Phase 4 spec).

No LangGraph or agent logic lives here - see app/agents/graph.py for
the workflow definition itself.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import build_mentor_graph
from app.core.logging import get_logger
from app.models.agent import AgentRun, AgentTrace, AnalysisSnapshot, PlannerOutput, GraphCheckpoint
from app.models.user import User
from app.services.memory_service import MemoryService, MemoryNotFoundError
from app.services.recommender_service import RecommenderService

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _get_user(self, cf_handle: str) -> User:
        result = await self._db.execute(select(User).where(User.cf_handle == cf_handle))
        user = result.scalar_one_or_none()
        if not user:
            raise MemoryNotFoundError(
                f"No user found for cf_handle={cf_handle!r} - ingest a Codeforces profile for this "
                "handle first via POST /api/v1/codeforces/ingest."
            )
        return user

    async def run_orchestrator(self, cf_handle: str, run_type: str = "full") -> dict[str, Any]:
        user = await self._get_user(cf_handle)
        thread_id = f"mentor-{cf_handle}-{uuid.uuid4().hex[:8]}"

        run = AgentRun(
            user_id=user.id,
            cf_handle=cf_handle,
            run_type=run_type,
            status="running",
            thread_id=thread_id,
        )
        self._db.add(run)
        await self._db.commit()
        await self._db.refresh(run)

        run_started = time.perf_counter()
        traces: list[AgentTrace] = []
        final_state: dict[str, Any] = {}

        try:
            graph = build_mentor_graph(
                lambda: MemoryService(self._db),
                lambda: RecommenderService(self._db),
            )
            initial_state = {
                "cf_handle": cf_handle,
                "thread_id": thread_id,
                "run_type": run_type,
                "trace": [],
            }

            step_index = 0
            node_started = time.perf_counter()

            async for update in graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_update in update.items():
                    node_finished = time.perf_counter()
                    duration_ms = int((node_finished - node_started) * 1000)

                    final_state.update(node_update or {})

                    trace_row = AgentTrace(
                        agent_run_id=run.id,
                        step_index=step_index,
                        node_name=node_name,
                        status="completed",
                        input_summary={"thread_id": thread_id},
                        output_summary=self._summarize_node_output(node_name, node_update or {}),
                        tool_calls=[],
                        started_at=_utcnow(),
                        finished_at=_utcnow(),
                        duration_ms=duration_ms,
                    )
                    self._db.add(trace_row)
                    await self._db.commit()
                    await self._db.refresh(trace_row)
                    traces.append(trace_row)

                    checkpoint = GraphCheckpoint(
                        thread_id=thread_id,
                        agent_run_id=run.id,
                        step_index=step_index,
                        node_name=node_name,
                        state=self._serialize_state(final_state),
                    )
                    self._db.add(checkpoint)
                    await self._db.commit()

                    step_index += 1
                    node_started = time.perf_counter()

            analysis = final_state.get("analysis") or {}
            plan = final_state.get("plan") or {}

            analysis_snapshot = None
            planner_output = None

            if analysis:
                analysis_snapshot = AnalysisSnapshot(
                    user_id=user.id,
                    agent_run_id=run.id,
                    strengths=analysis.get("strengths"),
                    weaknesses=analysis.get("weaknesses"),
                    priority_topics=analysis.get("priority_topics"),
                    improvement_velocity=analysis.get("improvement_velocity"),
                    analysis_summary=analysis.get("analysis_summary"),
                    raw_output=self._serialize_state(analysis),
                )
                self._db.add(analysis_snapshot)
                await self._db.commit()
                await self._db.refresh(analysis_snapshot)

            if plan:
                planner_output = PlannerOutput(
                    user_id=user.id,
                    agent_run_id=run.id,
                    analysis_snapshot_id=analysis_snapshot.id if analysis_snapshot else None,
                    study_plan=plan.get("study_plan"),
                    milestones=plan.get("milestones"),
                    weekly_schedule=plan.get("weekly_schedule"),
                    priority_topics=plan.get("priority_topics"),
                    estimated_duration=plan.get("estimated_duration"),
                    raw_output=self._serialize_state(plan),
                )
                self._db.add(planner_output)
                await self._db.commit()
                await self._db.refresh(planner_output)

            run.status = "completed"
            run.finished_at = _utcnow()
            run.duration_ms = int((time.perf_counter() - run_started) * 1000)
            await self._db.commit()
            await self._db.refresh(run)

            return {
                "run": run,
                "traces": traces,
                "analysis": analysis,
                "plan": plan,
                "recommendations": final_state.get("recommendations") or {},
            }

        except Exception as exc:  # noqa: BLE001 - surfaced to the API layer as a 500 with detail
            logger.exception("Agent orchestrator run failed for cf_handle=%s", cf_handle)
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = _utcnow()
            run.duration_ms = int((time.perf_counter() - run_started) * 1000)
            await self._db.commit()
            raise

    async def run_analyzer_only(self, cf_handle: str) -> dict[str, Any]:
        """POST /agents/analyze - runs the graph tagged as an 'analyze' run."""
        return await self.run_orchestrator(cf_handle, run_type="analyze")

    async def run_planner_only(self, cf_handle: str) -> dict[str, Any]:
        """
        POST /agents/plan - runs the full graph (Planner depends on
        Analyzer's output per the spec'd linear flow) tagged as a 'plan' run
        so callers that only care about the plan can hit a clearly-named route.
        """
        return await self.run_orchestrator(cf_handle, run_type="plan")

    async def get_history(self, cf_handle: Optional[str] = None, limit: int = 50) -> list[AgentRun]:
        stmt = select(AgentRun)
        if cf_handle:
            stmt = stmt.where(AgentRun.cf_handle == cf_handle)
        stmt = stmt.order_by(desc(AgentRun.started_at)).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_traces(self, agent_run_id: int) -> list[AgentTrace]:
        result = await self._db.execute(
            select(AgentTrace).where(AgentTrace.agent_run_id == agent_run_id).order_by(AgentTrace.step_index)
        )
        return list(result.scalars().all())

    async def get_run(self, agent_run_id: int) -> AgentRun:
        result = await self._db.execute(select(AgentRun).where(AgentRun.id == agent_run_id))
        run = result.scalar_one_or_none()
        if not run:
            raise MemoryNotFoundError(f"No agent run with id={agent_run_id}")
        return run

    async def get_latest_analysis(self, cf_handle: str) -> Optional[AnalysisSnapshot]:
        user = await self._get_user(cf_handle)
        result = await self._db.execute(
            select(AnalysisSnapshot)
            .where(AnalysisSnapshot.user_id == user.id)
            .order_by(desc(AnalysisSnapshot.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_plan(self, cf_handle: str) -> Optional[PlannerOutput]:
        user = await self._get_user(cf_handle)
        result = await self._db.execute(
            select(PlannerOutput)
            .where(PlannerOutput.user_id == user.id)
            .order_by(desc(PlannerOutput.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _summarize_node_output(node_name: str, node_update: dict[str, Any]) -> dict[str, Any]:
        if node_name == "RetrieveMemory":
            memory = node_update.get("memory") or {}
            return {
                "topic_ratings_count": len(memory.get("topic_ratings") or []),
                "has_cf_analytics": bool(memory.get("cf_analytics")),
            }
        if node_name == "AnalyzerAgent":
            analysis = node_update.get("analysis") or {}
            return {
                "strengths": analysis.get("strengths"),
                "weaknesses": analysis.get("weaknesses"),
                "priority_topics": analysis.get("priority_topics"),
            }
        if node_name == "PlannerAgent":
            plan = node_update.get("plan") or {}
            return {
                "estimated_duration": plan.get("estimated_duration"),
                "milestones_count": len(plan.get("milestones") or []),
            }
        if node_name == "RecommenderAgent":
            recs = node_update.get("recommendations") or {}
            return {
                "recommendations_count": len(recs.get("recommendations") or []),
                "strategies_used": list((recs.get("strategy") or {}).keys()),
            }
        if node_name == "PersistMemory":
            return {"persisted": node_update.get("persisted", False)}
        return {}

    @staticmethod
    def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
        import json

        try:
            json.dumps(state, default=str)
            return state
        except TypeError:
            return json.loads(json.dumps(state, default=str))
