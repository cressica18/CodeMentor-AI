"""
Chat route — Phase 5.1 fix (+ Gemini integration).

Was a Phase 1 stub that echoed the user's message with a hardcoded
"Agent logic coming in Phase 4!" placeholder and never touched the
database at all. This wires it up to the real RetrieveMemory ->
Analyzer -> Planner -> Recommender -> Persist pipeline for context,
sends that context to Gemini for the actual reply, and persists the
conversation either way (BUG 6).

Gemini is called directly over its REST API via httpx (already a
project dependency — see app/codeforces/client.py) rather than adding
a new SDK dependency. `GEMINI_API_KEY` is read from `.env` via
`app.core.config.Settings` (already declared there — `settings.gemini_api_key`).
If the key is missing, the call fails, or the response is malformed,
this falls back to the previous deterministic, memory-grounded
template reply so chat never goes fully dark.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas import ChatMessage, ChatRequest, ChatResponse
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryNotFoundError, MemoryService

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_GEMINI_MODEL = "gemini-2.5-flash"
_GEMINI_URL_TEMPLATE = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent"
)
_GEMINI_TIMEOUT_SECONDS = 20.0


def _compose_reply(cf_handle: str, message: str, analysis: dict, plan: dict, recommendations: dict) -> str:
    """Deterministic fallback reply, grounded in persisted memory —
    strengths/weaknesses, the current study plan, and the latest problem
    recommendations. Used only when Gemini is unavailable or errors out.
    """
    strengths = analysis.get("strengths") or []
    weaknesses = analysis.get("weaknesses") or []
    study_plan = plan.get("study_plan") or {}
    recs = recommendations.get("recommendations") or []

    parts = [f"Hi, I'm CodeMentor AI. Here's where {cf_handle} stands right now."]

    if strengths:
        parts.append(f"Your strongest areas are {', '.join(strengths[:3])}.")
    if weaknesses:
        parts.append(f"I'd focus next on {', '.join(weaknesses[:3])} — those are your current weak spots.")
    if study_plan.get("goal"):
        parts.append(f"Your active study plan goal: {study_plan['goal']}.")
    if recs:
        top = recs[0]
        parts.append(
            f"A good next problem: {top.get('problem_name')} ({top.get('rating')} rated, "
            f"tagged {', '.join((top.get('tags') or [])[:2])})."
        )

    parts.append(
        f'Regarding "{message.strip()}" — let me know if you want me to dig into a specific topic, '
        "your study plan, or recommendations."
    )
    return " ".join(parts)


def _build_mentor_context(
    cf_handle: str,
    profile,
    analysis: dict,
    plan: dict,
    milestones: list,
    recent_sessions: list,
    recommendations: dict,
) -> dict:
    """Collect the pieces of persistent memory the mentor prompt needs:
    user profile, strengths, weaknesses, milestones, recent study
    sessions, and recommendations."""
    return {
        "cf_handle": cf_handle,
        "profile": {
            "current_streak_days": getattr(profile, "current_streak_days", None),
            "improvement_velocity": getattr(profile, "improvement_velocity", None),
            "bio": getattr(profile, "bio", None),
        },
        "strengths": analysis.get("strengths") or [],
        "weaknesses": analysis.get("weaknesses") or [],
        "study_plan": plan.get("study_plan") or {},
        "milestones": [
            {
                "title": m.title if hasattr(m, "title") else m.get("title"),
                "milestone_type": m.milestone_type if hasattr(m, "milestone_type") else m.get("type"),
            }
            for m in (milestones or [])[:5]
        ],
        "recent_study_sessions": [
            {
                "topic": s.topic if hasattr(s, "topic") else s.get("topic"),
                "problems_solved": s.problems_solved if hasattr(s, "problems_solved") else s.get("problems_solved"),
                "problems_attempted": (
                    s.problems_attempted if hasattr(s, "problems_attempted") else s.get("problems_attempted")
                ),
            }
            for s in (recent_sessions or [])[:5]
        ],
        "recommendations": (recommendations.get("recommendations") or [])[:5],
    }


def _build_mentor_prompt(context: dict, message: str) -> str:
    """Construct the prompt sent to Gemini, grounding it in the user's
    persistent memory so the reply is specific, not generic."""
    profile = context["profile"]
    lines = [
        "You are CodeMentor AI, an expert competitive-programming mentor for Codeforces users.",
        f"You are mentoring the user with Codeforces handle '{context['cf_handle']}'.",
        "",
        "Here is everything you know about this student:",
        f"- Strengths: {', '.join(context['strengths']) or 'none recorded yet'}",
        f"- Weaknesses: {', '.join(context['weaknesses']) or 'none recorded yet'}",
        f"- Current streak (days): {profile.get('current_streak_days')}",
        f"- Improvement velocity: {profile.get('improvement_velocity')}",
        f"- Active study plan: {context['study_plan'].get('goal') or 'none set yet'}",
    ]

    if context["milestones"]:
        lines.append("- Milestones in progress: " + ", ".join(m["title"] for m in context["milestones"]))
    if context["recent_study_sessions"]:
        sessions_desc = ", ".join(
            f"{s.get('topic') or 'general'} ({s.get('problems_solved')}/{s.get('problems_attempted')} solved)"
            for s in context["recent_study_sessions"]
        )
        lines.append(f"- Recent study sessions: {sessions_desc}")
    if context["recommendations"]:
        recs_desc = ", ".join(
            f"{r.get('problem_name')} ({r.get('rating')})" for r in context["recommendations"]
        )
        lines.append(f"- Current problem recommendations: {recs_desc}")

    lines += [
        "",
        f'The student just said: "{message.strip()}"',
        "",
        "Respond as their mentor: be specific, reference the student's actual strengths/weaknesses/plan/"
        "recommendations above where relevant, and keep the reply concise (3-6 sentences) and encouraging.",
    ]
    return "\n".join(lines)


async def _call_gemini(prompt: str) -> str | None:
    """Send `prompt` to the Gemini API. Returns the model's text reply,
    or None if the key is missing, the request fails, or the response
    can't be parsed — the caller falls back to the template reply."""
    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        logger.warning("GEMINI_API_KEY not configured; falling back to template chat reply.")
        return None

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        async with httpx.AsyncClient(timeout=_GEMINI_TIMEOUT_SECONDS) as client:
            response = await client.post(
                _GEMINI_URL_TEMPLATE,
                params={"key": api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            logger.warning("Gemini API returned no candidates; falling back to template chat reply.")
            return None
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        logger.warning("Gemini API call failed (%s); falling back to template chat reply.", exc)
        return None


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Real agent-backed, Gemini-powered chat turn.

    1. Persist the incoming user message onto both the long-lived
       ChatSession row (`chat_sessions`) and the short-term SessionMemory
       buffer (`session_memories`).
    2. Reuse the latest Analyzer/Planner/Recommender output if one
       exists for this handle; otherwise run the full mentor graph once.
    3. Load profile, strengths, weaknesses, milestones, recent study
       sessions, and recommendations, and build a mentor prompt from them.
    4. Send the prompt to Gemini; fall back to the deterministic template
       reply if the Gemini call fails for any reason.
    5. Persist the reply back onto both session stores.
    """
    memory_svc = MemoryService(db)
    agent_svc = AgentService(db)

    try:
        await memory_svc.get_or_create_chat_session(payload.session_id, payload.cf_handle)
        await memory_svc.append_chat_message(payload.session_id, payload.cf_handle, "user", payload.message)
        await memory_svc.append_message(payload.session_id, "user", payload.message)

        latest_analysis = await agent_svc.get_latest_analysis(payload.cf_handle)
        latest_plan = await agent_svc.get_latest_plan(payload.cf_handle)

        if latest_analysis is None or latest_plan is None:
            run_result = await agent_svc.run_orchestrator(payload.cf_handle, run_type="chat")
            analysis = run_result.get("analysis") or {}
            plan = run_result.get("plan") or {}
            recommendations = run_result.get("recommendations") or {}
            agent_trace = [
                {"step": t.node_name, "duration_ms": t.duration_ms, "output_summary": t.output_summary}
                for t in run_result.get("traces") or []
            ]
        else:
            analysis = {
                "strengths": latest_analysis.strengths or [],
                "weaknesses": latest_analysis.weaknesses or [],
                "priority_topics": latest_analysis.priority_topics or [],
            }
            plan = {
                "study_plan": latest_plan.study_plan or {},
                "milestones": latest_plan.milestones or [],
            }
            overview = await memory_svc.get_overview(payload.cf_handle)
            recommendations = {
                "recommendations": [
                    {
                        "problem_name": (r.payload or {}).get("problem_name") if isinstance(r.payload, dict) else None,
                        "rating": (r.payload or {}).get("rating") if isinstance(r.payload, dict) else None,
                        "tags": (r.payload or {}).get("tags") if isinstance(r.payload, dict) else [],
                    }
                    for r in overview["recent_recommendations"]
                ]
            }
            agent_trace = [{"step": "reused_latest_agent_output", "note": "Analysis/plan already on file."}]

        # Profile, milestones, and recent study sessions come straight from
        # persistent memory regardless of which branch above ran.
        profile = await memory_svc.get_or_create_profile(payload.cf_handle)
        milestones = await memory_svc.get_milestones(payload.cf_handle, limit=5)
        recent_sessions = await memory_svc.get_study_sessions(payload.cf_handle, limit=5)

        mentor_context = _build_mentor_context(
            payload.cf_handle, profile, analysis, plan, milestones, recent_sessions, recommendations
        )
        prompt = _build_mentor_prompt(mentor_context, payload.message)

        gemini_reply = await _call_gemini(prompt)
        if gemini_reply:
            reply_text = gemini_reply
            agent_trace = (agent_trace or []) + [{"step": "GeminiReply", "model": _GEMINI_MODEL}]
        else:
            reply_text = _compose_reply(payload.cf_handle, payload.message, analysis, plan, recommendations)
            agent_trace = (agent_trace or []) + [{"step": "TemplateFallbackReply", "note": "Gemini unavailable or failed."}]

        await memory_svc.append_chat_message(payload.session_id, payload.cf_handle, "assistant", reply_text)
        await memory_svc.append_message(payload.session_id, "assistant", reply_text)

        return ChatResponse(
            session_id=payload.session_id,
            message=ChatMessage(role="assistant", content=reply_text),
            agent_trace=agent_trace,
        )
    except MemoryNotFoundError as exc:
        return ChatResponse(
            session_id=payload.session_id,
            message=ChatMessage(
                role="assistant",
                content=(
                    f"I don't have a Codeforces profile on file for '{payload.cf_handle}' yet — "
                    "ingest it first via the profile page, then chat with me."
                ),
            ),
            agent_trace=[{"step": "error", "note": str(exc)}],
        )


@router.post("/session")
async def create_session(cf_handle: str, db: AsyncSession = Depends(get_db)):
    """Create (and persist) a new chat session for the given handle."""
    session_id = str(uuid.uuid4())
    memory_svc = MemoryService(db)
    try:
        await memory_svc.get_or_create_chat_session(session_id, cf_handle)
    except MemoryNotFoundError:
        # No CF profile ingested yet — still hand back a session id so the
        # frontend can proceed; the chat_sessions row is created lazily on
        # the first successful chat() call once the handle exists.
        pass
    return {"session_id": session_id, "cf_handle": cf_handle}