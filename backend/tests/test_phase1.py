import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_ping():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/health/ping")
    assert r.status_code == 200
    assert r.json() == {"ping": "pong"}


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/")
    assert r.status_code == 200
    assert "CodeMentor AI" in r.json()["message"]


# NOTE: this used to assert the Phase 1 placeholder ("Hello! I'm CodeMentor
# AI. You said: 'Hello!'. Agent logic coming in Phase 4!"). Phase 5.1 wires
# /chat to the real RetrieveMemory -> Analyzer -> Planner -> Recommender ->
# Persist pipeline (BUG 6), so the assertions below check the new contract:
# a real, memory-grounded reply that also persists chat history.
@pytest.mark.asyncio
async def test_chat_runs_real_agent_pipeline_and_persists_history(db_session, mock_cf_network):
    from app.db.session import get_db
    from app.models.user import User
    from app.models.session import ChatSession
    from sqlalchemy import select

    user = User(cf_handle="tourist", current_rating=1450, max_rating=1500, cf_analytics={})
    db_session.add(user)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/chat",
                json={"session_id": "test-session-001", "cf_handle": "tourist", "message": "Hello!"},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["message"]["role"] == "assistant"
        # No more hardcoded placeholder text:
        assert "Agent logic coming in Phase 4" not in data["message"]["content"]
        assert "tourist" in data["message"]["content"]
        assert data["agent_trace"]

        # BUG 6 fix: the turn must persist onto the long-lived ChatSession.
        result = await db_session.execute(select(ChatSession).where(ChatSession.session_id == "test-session-001"))
        chat_session = result.scalar_one_or_none()
        assert chat_session is not None
        roles = [m["role"] for m in (chat_session.messages or [])]
        assert roles == ["user", "assistant"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_unknown_handle_returns_friendly_error(db_session):
    from app.db.session import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/chat",
                json={"session_id": "test-session-002", "cf_handle": "no_such_handle", "message": "hi"},
            )
        assert r.status_code == 200
        data = r.json()
        assert "no_such_handle" in data["message"]["content"]
    finally:
        app.dependency_overrides.clear()