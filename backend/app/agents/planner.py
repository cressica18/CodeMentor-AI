"""
Planner Agent (Phase 4).

Pure function: takes the AnalyzerAgent's output plus the retrieved
memory snapshot (existing learning path, study session history) and
produces a structured study plan: a roadmap, milestones, a weekly
schedule, priority topics, and an estimated duration.

Like the Analyzer Agent, this node is deterministic/rule-based so the
graph runs end-to-end without requiring any LLM credentials. The
generated plan is intentionally conservative and explainable — each
weekly goal traces back to a specific weakness or strength from the
analysis.
"""

from __future__ import annotations

from typing import Any

from app.agents.state import AnalyzerResult, MemorySnapshot, PlannerResult

_DEFAULT_DAILY_GOAL_MINUTES = 60


def _estimate_sessions_per_week(preferences: dict[str, Any]) -> int:
    daily_minutes = preferences.get("daily_goal_minutes") or _DEFAULT_DAILY_GOAL_MINUTES
    # Assume ~45 min effective practice per session; cap between 2 and 7.
    sessions = max(2, min(7, round((daily_minutes * 7) / 45 / 7 * 5)))
    return sessions


def _build_milestones(priority_topics: list[str], strengths: list[str]) -> list[dict[str, Any]]:
    milestones: list[dict[str, Any]] = []
    for i, topic in enumerate(priority_topics, start=1):
        milestones.append(
            {
                "order": i,
                "title": f"Reach working competence in {topic}",
                "topic": topic,
                "target_problems_solved": 10 + i * 2,
                "type": "weakness_remediation",
            }
        )
    for j, topic in enumerate(strengths[:2], start=len(priority_topics) + 1):
        milestones.append(
            {
                "order": j,
                "title": f"Push {topic} from strong to expert-level",
                "topic": topic,
                "target_problems_solved": 15,
                "type": "strength_reinforcement",
            }
        )
    if not milestones:
        milestones.append(
            {
                "order": 1,
                "title": "Establish a consistent practice baseline",
                "topic": "general",
                "target_problems_solved": 20,
                "type": "baseline",
            }
        )
    return milestones


def _build_weekly_schedule(
    priority_topics: list[str], sessions_per_week: int, weeks: int
) -> list[dict[str, Any]]:
    schedule: list[dict[str, Any]] = []
    topics = priority_topics or ["mixed practice"]
    for week in range(1, weeks + 1):
        # Rotate through priority topics week over week so early weeks
        # front-load the weakest areas, then cycle for spaced repetition.
        topic = topics[(week - 1) % len(topics)]
        schedule.append(
            {
                "week": week,
                "focus_topic": topic,
                "sessions_planned": sessions_per_week,
                "goal": (
                    f"Solve problems tagged '{topic}' and review past mistakes in this area"
                    if topic != "mixed practice"
                    else "Solve a balanced mix of problems across all tracked topics"
                ),
                "revision": week % 3 == 0,  # every 3rd week is a revision week
            }
        )
    return schedule


def _build_daily_goals(sessions_per_week: int) -> dict[str, Any]:
    return {
        "practice_days_per_week": sessions_per_week,
        "target_problems_per_session": 2,
        "review_minutes_per_session": 15,
    }


def _estimate_duration(num_priority_topics: int, velocity: float) -> str:
    base_weeks = max(4, num_priority_topics * 2)
    if velocity and velocity < 0:
        base_weeks += 2  # declining trajectory → pad the timeline
    return f"{base_weeks} weeks"


def run_planner_agent(analysis: AnalyzerResult, memory: MemorySnapshot) -> PlannerResult:
    """
    Generate a personalized study roadmap from the Analyzer Agent's
    output and the user's existing learning-path / preference memory.
    """
    priority_topics = list(analysis.get("priority_topics") or [])
    strengths = list(analysis.get("strengths") or [])
    velocity = float(analysis.get("improvement_velocity") or 0.0)

    preferences = memory.get("preferences") or {}
    existing_path = memory.get("learning_path") or {}

    sessions_per_week = _estimate_sessions_per_week(preferences)
    duration_str = _estimate_duration(len(priority_topics) or 1, velocity)
    weeks = int(duration_str.split()[0])

    milestones = _build_milestones(priority_topics, strengths)
    weekly_schedule = _build_weekly_schedule(priority_topics, sessions_per_week, weeks)
    daily_goals = _build_daily_goals(sessions_per_week)

    study_plan: dict[str, Any] = {
        "goal": existing_path.get("goal") or "Close priority topic gaps and raise contest rating consistently",
        "current_stage": priority_topics[0] if priority_topics else (existing_path.get("current_stage") or "baseline"),
        "priority_topics": priority_topics,
        "reinforcement_topics": strengths[:2],
        "daily_goals": daily_goals,
        "practice_schedule": weekly_schedule,
        "revision_schedule": [w for w in weekly_schedule if w["revision"]],
        "based_on_analysis_summary": analysis.get("analysis_summary", ""),
    }

    result: PlannerResult = {
        "study_plan": study_plan,
        "milestones": milestones,
        "weekly_schedule": weekly_schedule,
        "priority_topics": priority_topics,
        "estimated_duration": duration_str,
    }
    return result
