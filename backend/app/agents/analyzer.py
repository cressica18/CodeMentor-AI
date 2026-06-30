"""
Analyzer Agent (Phase 4).

Pure function: takes the `MemorySnapshot` produced by the RetrieveMemory
node and returns an `AnalyzerResult`. No I/O, no DB access, no LLM call
is required to produce a correct result — this keeps the node fast,
deterministic, and trivially unit-testable, exactly like the existing
`app/codeforces/analytics.py` module it builds on top of.

If an LLM is configured (`Settings.active_llm != "none"`) a future phase
may enrich `analysis_summary` further; for Phase 4 the summary is built
deterministically so the workflow always succeeds without external
network access or API keys.
"""

from __future__ import annotations

from typing import Any

from app.agents.state import AnalyzerResult, MemorySnapshot
from app.core.logging import get_logger

logger = get_logger(__name__)

# Tags surfaced by the Codeforces analytics engine that aren't really
# "topics" in the mentoring sense — filtered out of priority/strength
# lists so recommendations stay actionable.
_NOISE_TAGS = {"*special", "implementation"}


def _clean_tags(tags: list[str]) -> list[str]:
    return [t for t in tags if t and t not in _NOISE_TAGS]


def _rating_trajectory(rating_trend: list[dict[str, Any]]) -> dict[str, Any]:
    if not rating_trend:
        return {"direction": "unknown", "recent_delta": 0, "contests_considered": 0}
    window = rating_trend[-10:]
    recent_delta = sum(p.get("delta", 0) for p in window)
    direction = "up" if recent_delta > 0 else "down" if recent_delta < 0 else "flat"
    return {
        "direction": direction,
        "recent_delta": recent_delta,
        "contests_considered": len(window),
    }


def _contest_behavior(rating_trend: list[dict[str, Any]]) -> dict[str, Any]:
    if not rating_trend:
        return {"volatility": 0.0, "negative_streak": 0}
    deltas = [p.get("delta", 0) for p in rating_trend]
    avg = sum(deltas) / len(deltas)
    variance = sum((d - avg) ** 2 for d in deltas) / len(deltas)
    volatility = round(variance**0.5, 2)

    streak = 0
    for d in reversed(deltas):
        if d < 0:
            streak += 1
        else:
            break
    return {"volatility": volatility, "negative_streak": streak}


def _submission_behavior(cf_analytics: dict[str, Any]) -> dict[str, Any]:
    return {
        "success_rate": cf_analytics.get("success_rate"),
        "total_submissions": cf_analytics.get("total_submissions"),
        "accepted_count": cf_analytics.get("accepted_count"),
    }


def _topic_confidence_scores(
    topic_ratings: list[dict[str, Any]], tag_ac_rates: dict[str, float]
) -> dict[str, float]:
    """
    Merge Phase 3 long-term `TopicRating` rows (0..1 mentor-maintained
    skill score) with Phase 2 raw CF AC-rate-per-tag into a single
    confidence score per topic, favoring the long-term rating when both
    exist since it accounts for more than raw AC rate (e.g. recency).
    """
    scores: dict[str, float] = dict(tag_ac_rates)
    for tr in topic_ratings:
        topic = tr.get("topic")
        rating = tr.get("rating")
        if topic and rating is not None:
            scores[topic] = round(float(rating), 3)
    return scores


def _build_summary(
    strengths: list[str],
    weaknesses: list[str],
    trajectory: dict[str, Any],
    velocity: float,
    handle: str,
) -> str:
    parts = [f"Analysis for {handle}:"]
    if trajectory["direction"] == "up":
        parts.append(
            f"rating is trending upward (+{trajectory['recent_delta']} over the last "
            f"{trajectory['contests_considered']} contests)."
        )
    elif trajectory["direction"] == "down":
        parts.append(
            f"rating has dipped ({trajectory['recent_delta']} over the last "
            f"{trajectory['contests_considered']} contests) — recent contests warrant review."
        )
    else:
        parts.append("rating has been stable recently.")

    if strengths:
        parts.append(f"Strongest topics: {', '.join(strengths[:5])}.")
    if weaknesses:
        parts.append(f"Weakest topics needing attention: {', '.join(weaknesses[:5])}.")
    if velocity:
        trend_word = "improving" if velocity > 0 else "declining"
        parts.append(f"Improvement velocity is {trend_word} at {round(velocity, 2)} rating/day.")
    return " ".join(parts)


def run_analyzer_agent(memory: MemorySnapshot) -> AnalyzerResult:
    """
    Compute strengths, weaknesses, priority topics, improvement velocity,
    and a human-readable analysis summary from retrieved memory.
    """
    cf_analytics = memory.get("cf_analytics") or {}
    profile = memory.get("profile") or {}
    topic_ratings = memory.get("topic_ratings") or []

    weakest_tag_entries = cf_analytics.get("weakest_tags") or []
    strongest_tag_entries = cf_analytics.get("strongest_tags") or []
    tag_ac_rates = cf_analytics.get("tag_ac_rates") or {}
    rating_trend = cf_analytics.get("rating_trend") or []

    weaknesses = _clean_tags([e["tag"] for e in weakest_tag_entries if "tag" in e])
    strengths = _clean_tags([e["tag"] for e in strongest_tag_entries if "tag" in e])

    # Long-term memory may already have explicit strengths/weaknesses
    # recorded (e.g. from a prior agent run) — merge them in, with
    # long-term memory taking priority for ordering.
    for tr in topic_ratings:
        if tr.get("is_weakness") and tr.get("topic") not in weaknesses:
            weaknesses.insert(0, tr["topic"])
        if tr.get("is_strength") and tr.get("topic") not in strengths:
            strengths.insert(0, tr["topic"])

    # Priority topics = topics most worth practicing next. Weaknesses
    # take priority; if there are none yet (e.g. brand-new profile),
    # fall back to reinforcing existing strengths.
    priority_topics = weaknesses[:6] if weaknesses else strengths[:3]

    trajectory = _rating_trajectory(rating_trend)
    behavior = _contest_behavior(rating_trend)
    submission_behavior = _submission_behavior(cf_analytics)
    confidence_scores = _topic_confidence_scores(topic_ratings, tag_ac_rates)

    velocity = profile.get("improvement_velocity")
    if velocity is None:
        # Derive a rough velocity straight from the rating trend if the
        # Phase 3 cached value isn't available yet (e.g. fewer than two
        # progress snapshots have ever been captured).
        if len(rating_trend) >= 2:
            first, last = rating_trend[0], rating_trend[-1]
            days = max((last.get("timestamp", 0) - first.get("timestamp", 0)) / 86400.0, 1e-6)
            velocity = round((last.get("newRating", 0) - first.get("oldRating", 0)) / days, 4)
        else:
            velocity = 0.0

    summary = _build_summary(strengths, weaknesses, trajectory, velocity, memory.get("cf_handle", "user"))

    bottlenecks = (weaknesses[:3] if behavior["negative_streak"] > 0 else []) or weaknesses[:3]

    result: AnalyzerResult = {
        "strengths": strengths[:10],
        "weaknesses": weaknesses[:10],
        "priority_topics": priority_topics,
        "improvement_velocity": float(velocity or 0.0),
        "analysis_summary": summary,
    }

    # Extra, forward-compatible detail attached for persistence/trace
    # purposes (not part of the strict spec'd AnalyzerOutput schema, but
    # useful in `raw_output` / the Agent Trace panel).
    result["_extra"] = {  # type: ignore[typeddict-item]
        "rating_trajectory": trajectory,
        "contest_behavior": behavior,
        "submission_behavior": submission_behavior,
        "topic_confidence_scores": confidence_scores,
        "learning_bottlenecks": bottlenecks,
    }
    return result
