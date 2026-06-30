"""
Problem Recommender Agent (Phase 5).

Pure function, exactly like `app/agents/analyzer.py` and
`app/agents/planner.py`: no I/O, no DB access, no network calls. All
real-world data (the Codeforces problem pool, the user's solved
problems, their current rating) is fetched by the calling service
layer (`app/services/recommender_service.py` / the LangGraph
`RecommenderAgent` node in `app/agents/graph.py`) and passed in here as
plain data structures.

This keeps the recommendation engine itself fast, deterministic, and
unit-testable — and, per the Phase 5 spec, guarantees it can never
fabricate a problem: every recommendation is selected from the
`problem_pool` argument, which the caller populates exclusively from
https://codeforces.com/api/problemset.problems.

Strategies implemented (per the Phase 5 spec):
  - reinforcement : weak-topic problems near the user's current rating
  - advancement   : harder problems in topics the user has mastered
  - recovery      : easier problems, triggered by a recent fail streak
  - contest_prep  : a balanced A/B/C-style spread across topics
"""

from __future__ import annotations

from typing import Any, Iterable

_NOISE_TAGS = {"*special", "implementation"}

# Per-strategy (low, high) offsets applied to the user's current rating
# to build the target difficulty window for problem selection.
_REINFORCEMENT_WINDOW = (-200, 100)
_ADVANCEMENT_WINDOW = (100, 300)
_RECOVERY_WINDOW = (-400, -100)
_CONTEST_PREP_WINDOW = (-100, 200)

_DEFAULT_TARGET_COUNT = {
    "reinforcement": 4,
    "advancement": 2,
    "recovery": 2,
    "contest_prep": 3,
}


def _clean_tags(tags: Iterable[str]) -> list[str]:
    return [t for t in tags if t and t not in _NOISE_TAGS]


def _round_to_cf_rating(value: float) -> int:
    """CF problem ratings are always multiples of 100."""
    return max(800, int(round(value / 100.0) * 100))


def _difficulty_match_score(problem_rating: int, target_rating: int) -> float:
    diff = abs(problem_rating - target_rating)
    return round(max(0.0, 1.0 - diff / 400.0), 3)


def _estimate_solve_minutes(rating: int | None) -> int:
    if rating is None:
        return 30
    # Rough heuristic: higher rating ⇒ longer expected solve time.
    if rating < 1200:
        return 15
    if rating < 1600:
        return 30
    if rating < 2000:
        return 45
    if rating < 2400:
        return 60
    return 90


def _problem_url(contest_id: int | None, index: str) -> str | None:
    if contest_id is None:
        return None
    return f"https://codeforces.com/problemset/problem/{contest_id}/{index}"


def _select_problems(
    problem_pool: list[dict[str, Any]],
    target_rating: int,
    topics: list[str] | None,
    exclude_keys: set[tuple[int | None, str]],
    count: int,
    recommendation_type: str,
    reason_template: str,
) -> list[dict[str, Any]]:
    """
    Rank `problem_pool` by closeness to `target_rating` (optionally
    requiring tag overlap with `topics`), filter out anything already
    solved or already recommended, and return the top `count`.
    """
    topic_set = set(topics or [])
    candidates: list[tuple[int, dict[str, Any]]] = []

    for p in problem_pool:
        key = (p.get("contest_id"), p.get("index"))
        if key in exclude_keys:
            continue
        rating = p.get("rating")
        if rating is None:
            continue

        tags = _clean_tags(p.get("tags") or [])
        if topic_set and not (topic_set & set(tags)):
            continue

        distance = abs(rating - target_rating)
        candidates.append((distance, p))

    candidates.sort(key=lambda c: c[0])

    results: list[dict[str, Any]] = []
    seen_keys: set[tuple[int | None, str]] = set()
    for _, p in candidates:
        key = (p.get("contest_id"), p.get("index"))
        if key in seen_keys:
            continue
        seen_keys.add(key)

        rating = p["rating"]
        matched_topic = next((t for t in _clean_tags(p.get("tags") or []) if t in topic_set), None)
        reason = reason_template.format(
            topic=matched_topic or "mixed practice",
            rating=rating,
        )

        results.append(
            {
                "contest_id": p.get("contest_id"),
                "index": p.get("index"),
                "problem_name": p.get("name"),
                "rating": rating,
                "tags": _clean_tags(p.get("tags") or []),
                "recommendation_type": recommendation_type,
                "recommendation_score": _difficulty_match_score(rating, target_rating),
                "difficulty_match_score": _difficulty_match_score(rating, target_rating),
                "recommendation_reason": reason,
                "estimated_solve_minutes": _estimate_solve_minutes(rating),
                "url": _problem_url(p.get("contest_id"), p.get("index")),
            }
        )
        if len(results) >= count:
            break

    return results


def run_recommender_agent(
    analysis: dict[str, Any],
    current_rating: int | None,
    problem_pool: list[dict[str, Any]],
    solved_keys: set[tuple[int | None, str]],
    recent_recommendation_keys: set[tuple[int | None, str]] | None = None,
    negative_streak: int = 0,
) -> dict[str, Any]:
    """
    Generate problem recommendations from the Analyzer Agent's output
    plus the user's real Codeforces solve history and the real CF
    problem pool.

    Returns a dict with:
      - recommendations: list[dict]   (flat list across all strategies)
      - strategy: dict                (per-strategy breakdown + windows used)
      - reasoning: str                (human-readable agent trace summary)
    """
    weaknesses = list(analysis.get("weaknesses") or [])
    strengths = list(analysis.get("strengths") or [])
    priority_topics = list(analysis.get("priority_topics") or weaknesses)

    base_rating = current_rating or 1200
    exclude = set(solved_keys) | set(recent_recommendation_keys or set())

    recommendations: list[dict[str, Any]] = []
    strategy_breakdown: dict[str, Any] = {}

    # ── Reinforcement: weak topics, near-current rating ──────────────
    if priority_topics:
        lo, hi = _REINFORCEMENT_WINDOW
        target = _round_to_cf_rating(base_rating + (lo + hi) / 2)
        picks = _select_problems(
            problem_pool,
            target_rating=target,
            topics=priority_topics,
            exclude_keys=exclude,
            count=_DEFAULT_TARGET_COUNT["reinforcement"],
            recommendation_type="reinforcement",
            reason_template="Targets your weak topic '{topic}' at a rating ({rating}) close to your current level — builds the fundamentals you're missing.",
        )
        recommendations.extend(picks)
        exclude |= {(p["contest_id"], p["index"]) for p in picks}
        strategy_breakdown["reinforcement"] = {
            "target_rating": target,
            "topics": priority_topics,
            "count": len(picks),
        }

    # ── Recovery: triggered by a recent fail/negative streak ─────────
    if negative_streak and negative_streak > 0:
        lo, hi = _RECOVERY_WINDOW
        target = _round_to_cf_rating(base_rating + (lo + hi) / 2)
        picks = _select_problems(
            problem_pool,
            target_rating=target,
            topics=priority_topics or None,
            exclude_keys=exclude,
            count=_DEFAULT_TARGET_COUNT["recovery"],
            recommendation_type="recovery",
            reason_template="A confidence-rebuilding problem ({rating}) after a recent rough patch — easier than your usual range on purpose.",
        )
        recommendations.extend(picks)
        exclude |= {(p["contest_id"], p["index"]) for p in picks}
        strategy_breakdown["recovery"] = {
            "target_rating": target,
            "triggered_by_negative_streak": negative_streak,
            "count": len(picks),
        }

    # ── Advancement: topics already strong, pushed harder ─────────────
    if strengths:
        lo, hi = _ADVANCEMENT_WINDOW
        target = _round_to_cf_rating(base_rating + (lo + hi) / 2)
        picks = _select_problems(
            problem_pool,
            target_rating=target,
            topics=strengths,
            exclude_keys=exclude,
            count=_DEFAULT_TARGET_COUNT["advancement"],
            recommendation_type="advancement",
            reason_template="You've shown mastery in '{topic}' — this harder problem ({rating}) pushes that strength further.",
        )
        recommendations.extend(picks)
        exclude |= {(p["contest_id"], p["index"]) for p in picks}
        strategy_breakdown["advancement"] = {
            "target_rating": target,
            "topics": strengths,
            "count": len(picks),
        }

    # ── Contest prep: balanced A/B/C-style spread, no topic filter ───
    lo, hi = _CONTEST_PREP_WINDOW
    target = _round_to_cf_rating(base_rating + (lo + hi) / 2)
    picks = _select_problems(
        problem_pool,
        target_rating=target,
        topics=None,
        exclude_keys=exclude,
        count=_DEFAULT_TARGET_COUNT["contest_prep"],
        recommendation_type="contest_prep",
        reason_template="Contest-style practice ({rating}) — the kind of problem you'll see as an A/B/C in your next contest.",
    )
    recommendations.extend(picks)
    strategy_breakdown["contest_prep"] = {"target_rating": target, "count": len(picks)}

    reasoning_parts = [f"Generated {len(recommendations)} recommendation(s) from the live Codeforces problemset."]
    if priority_topics:
        reasoning_parts.append(f"Reinforcement focused on: {', '.join(priority_topics[:5])}.")
    if negative_streak:
        reasoning_parts.append(f"Recovery problems added due to a {negative_streak}-contest negative streak.")
    if strengths:
        reasoning_parts.append(f"Advancement problems push strengths: {', '.join(strengths[:3])}.")
    reasoning_parts.append("Contest-prep problems round out the set for general competition readiness.")

    return {
        "recommendations": recommendations,
        "strategy": strategy_breakdown,
        "reasoning": " ".join(reasoning_parts),
    }
