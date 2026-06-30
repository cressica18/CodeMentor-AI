"""
Analytics engine for Codeforces data.

Takes raw CF API objects (CFUser, CFRatingChange, CFSubmission) and
produces structured analytics that the service layer persists and the
API returns to the frontend.

All functions are pure (no I/O) so they are trivially unit-testable
and can be re-used by future agents without touching the network layer.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from app.codeforces.models import CFUser, CFRatingChange, CFSubmission, CFProblem


# ── helpers ────────────────────────────────────────────────────────────────

def _ts_to_date(ts: int) -> str:
    """Unix timestamp → ISO date string (YYYY-MM-DD)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _ts_to_iso(ts: int) -> str:
    """Unix timestamp → full ISO-8601 UTC string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# ── rating trend ───────────────────────────────────────────────────────────

def compute_rating_trend(
    rating_history: list[CFRatingChange],
) -> list[dict[str, Any]]:
    """
    Convert raw rating history into a sorted list of
    {contest, date, oldRating, newRating, delta} points suitable for
    Recharts LineChart rendering.
    """
    return [
        {
            "contestId": rc.contest_id,
            "contest": rc.contest_name,
            "date": _ts_to_date(rc.rating_update_time_seconds),
            "timestamp": rc.rating_update_time_seconds,
            "oldRating": rc.old_rating,
            "newRating": rc.new_rating,
            "delta": rc.delta,
            "rank": rc.rank,
        }
        for rc in sorted(
            rating_history, key=lambda r: r.rating_update_time_seconds
        )
    ]


# ── tag analytics ──────────────────────────────────────────────────────────

def compute_tag_stats(
    solved_problems: list[CFProblem],
    all_submissions: list[CFSubmission],
) -> dict[str, Any]:
    """
    Returns:
      most_solved_tags  – top-10 tags by number of distinct AC problems
      tag_solve_counts  – full {tag: count} map
      weakest_tags      – tags where AC rate is lowest (min 3 attempts)
      strongest_tags    – tags where AC rate is highest (min 3 attempts)
      tag_ac_rates      – full {tag: rate} map for all attempted tags
    """
    # Count solved problems per tag
    solved_tag_counter: Counter[str] = Counter()
    for problem in solved_problems:
        for tag in problem.tags:
            solved_tag_counter[tag] += 1

    # Build per-tag attempt/AC counters from all submissions
    tag_attempts: Counter[str] = Counter()
    tag_ac: Counter[str] = Counter()
    for sub in all_submissions:
        for tag in sub.problem.tags:
            tag_attempts[tag] += 1
            if sub.verdict == "OK":
                tag_ac[tag] += 1

    # AC rate per tag (only where we have ≥ 3 attempts)
    tag_ac_rates: dict[str, float] = {}
    for tag, attempts in tag_attempts.items():
        if attempts >= 3:
            tag_ac_rates[tag] = round(tag_ac[tag] / attempts, 3)

    sorted_by_rate = sorted(tag_ac_rates.items(), key=lambda x: x[1])

    return {
        "most_solved_tags": [
            {"tag": t, "count": c}
            for t, c in solved_tag_counter.most_common(10)
        ],
        "tag_solve_counts": dict(solved_tag_counter),
        "weakest_tags": [
            {"tag": t, "acRate": r}
            for t, r in sorted_by_rate[:8]
        ],
        "strongest_tags": [
            {"tag": t, "acRate": r}
            for t, r in reversed(sorted_by_rate[-8:])
        ],
        "tag_ac_rates": tag_ac_rates,
    }


# ── difficulty distribution ────────────────────────────────────────────────

def compute_difficulty_distribution(
    solved_problems: list[CFProblem],
) -> list[dict[str, Any]]:
    """
    Group solved problems into difficulty buckets (0–799, 800–999, …
    3000+) for a bar/pie chart.
    """
    buckets: list[tuple[str, int, int]] = [
        ("Unrated", -1, -1),
        ("< 800",    0,  799),
        ("800–999",  800,  999),
        ("1000–1199", 1000, 1199),
        ("1200–1399", 1200, 1399),
        ("1400–1599", 1400, 1599),
        ("1600–1799", 1600, 1799),
        ("1800–1999", 1800, 1999),
        ("2000–2199", 2000, 2199),
        ("2200–2399", 2200, 2399),
        ("2400–2599", 2400, 2599),
        ("2600–2999", 2600, 2999),
        ("3000+",    3000, 99999),
    ]

    counts: dict[str, int] = {label: 0 for label, *_ in buckets}
    total_rated_rating = 0
    rated_count = 0

    for p in solved_problems:
        if p.rating is None:
            counts["Unrated"] += 1
        else:
            for label, lo, hi in buckets[1:]:
                if lo <= p.rating <= hi:
                    counts[label] += 1
                    break
            total_rated_rating += p.rating
            rated_count += 1

    avg_rating = (
        round(total_rated_rating / rated_count) if rated_count else None
    )

    return {
        "distribution": [
            {"range": label, "count": counts[label]}
            for label, *_ in buckets
            if counts[label] > 0
        ],
        "avg_solved_rating": avg_rating,
    }


# ── submission statistics ──────────────────────────────────────────────────

def compute_submission_stats(
    all_submissions: list[CFSubmission],
) -> dict[str, Any]:
    """
    Returns:
      total_submissions
      accepted_count
      success_rate          (0.0 – 1.0)
      verdict_distribution  {verdict: count}
      language_distribution {lang: count}
    """
    if not all_submissions:
        return {
            "total_submissions": 0,
            "accepted_count": 0,
            "success_rate": 0.0,
            "verdict_distribution": {},
            "language_distribution": {},
        }

    verdict_counter: Counter[str] = Counter()
    lang_counter: Counter[str] = Counter()
    accepted = 0

    for sub in all_submissions:
        verdict = sub.verdict or "UNKNOWN"
        verdict_counter[verdict] += 1
        if sub.programming_language:
            lang_counter[sub.programming_language] += 1
        if verdict == "OK":
            accepted += 1

    total = len(all_submissions)
    return {
        "total_submissions": total,
        "accepted_count": accepted,
        "success_rate": round(accepted / total, 3),
        "verdict_distribution": dict(verdict_counter.most_common()),
        "language_distribution": dict(lang_counter.most_common(10)),
    }


# ── activity heatmap ───────────────────────────────────────────────────────

def compute_activity_heatmap(
    all_submissions: list[CFSubmission],
    days: int = 365,
) -> list[dict[str, Any]]:
    """
    Returns a list of {date, count} records for the last `days` days,
    including days with zero submissions.  Suitable for a GitHub-style
    calendar heatmap.
    """
    from datetime import timedelta

    now_ts = datetime.now(timezone.utc)
    cutoff_ts = int((now_ts - timedelta(days=days)).timestamp())

    daily: Counter[str] = Counter()
    for sub in all_submissions:
        if sub.creation_time_seconds >= cutoff_ts:
            day = _ts_to_date(sub.creation_time_seconds)
            daily[day] += 1

    # Enumerate every day in the window so the frontend can render zeros
    result: list[dict[str, Any]] = []
    for i in range(days):
        d = (now_ts - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        result.append({"date": d, "count": daily.get(d, 0)})

    return result


# ── master analytics builder ───────────────────────────────────────────────

def build_full_analytics(
    user: CFUser,
    rating_history: list[CFRatingChange],
    all_submissions: list[CFSubmission],
    solved_problems: list[CFProblem],
) -> dict[str, Any]:
    """
    Orchestrate all sub-computations and return a single analytics blob
    that the service layer persists and the API serialises.
    """
    tag_stats = compute_tag_stats(solved_problems, all_submissions)
    diff_stats = compute_difficulty_distribution(solved_problems)
    sub_stats = compute_submission_stats(all_submissions)
    heatmap = compute_activity_heatmap(all_submissions)
    rating_trend = compute_rating_trend(rating_history)

    return {
        # ── profile summary ──
        "handle": user.handle,
        "display_name": user.display_name,
        "rank": user.rank,
        "max_rank": user.max_rank,
        "current_rating": user.rating,
        "max_rating": user.max_rating,
        "country": user.country,
        "organization": user.organization,
        "avatar": user.avatar,
        "contribution": user.contribution,
        "friend_of_count": user.friend_of_count,
        "registered_at": (
            _ts_to_iso(user.registration_time_seconds)
            if user.registration_time_seconds
            else None
        ),
        # ── contest summary ──
        "contests_participated": len(rating_history),
        "solved_count": len(solved_problems),
        # ── rating ──
        "rating_trend": rating_trend,
        # ── tags ──
        "most_solved_tags": tag_stats["most_solved_tags"],
        "tag_solve_counts": tag_stats["tag_solve_counts"],
        "weakest_tags": tag_stats["weakest_tags"],
        "strongest_tags": tag_stats["strongest_tags"],
        "tag_ac_rates": tag_stats["tag_ac_rates"],
        # ── difficulty ──
        "difficulty_distribution": diff_stats["distribution"],
        "avg_solved_rating": diff_stats["avg_solved_rating"],
        # ── submissions ──
        **sub_stats,
        # ── activity ──
        "activity_heatmap": heatmap,
    }
