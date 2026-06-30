"""
Shared fixtures for the test suite.

Phase 3 introduces tests that need a real (but disposable) database to
verify actual persistence/retrieval behavior rather than mocking the
session, as Phase 1/2 tests do for pure API-shape checks. We use an
in-memory SQLite database via aiosqlite for this — fast, dependency-light,
and exercises the real SQLAlchemy models end-to-end.

Note: SQLite doesn't enforce all PostgreSQL-specific behavior (e.g. some
JSON/array nuances), but for Phase 3's CRUD-shaped memory tables it is a
faithful enough stand-in for unit/integration testing without requiring a
running Postgres instance in CI.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models import User  # noqa: F401 — ensures User table registers on Base.metadata

# Import memory models so their tables register on Base.metadata too
from app.models import memory as _memory_models  # noqa: F401

# Import Phase 4 agent models so their tables register on Base.metadata too
from app.models import agent as _agent_models  # noqa: F401

# Import Phase 5 recommendation engine models so their tables register too
from app.models import recommendation_engine as _recommendation_models  # noqa: F401


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    session_maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_user(db_session: AsyncSession) -> User:
    """A baseline user that memory records can attach to."""
    user = User(cf_handle="memtest_user", current_rating=1400, max_rating=1500)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ── Phase 5 — never hit the live Codeforces API in tests ───────────────────
#
# RecommenderService talks to two external dependencies: the real CF
# problem pool (ProblemPoolService) and the user's real solved-problem
# history (CodeforcesClient.get_solved_problems). Both are monkeypatched
# here, autouse, so every test — including the Phase 4 orchestrator tests,
# which now also exercise the Recommender node — runs fully offline with
# deterministic, in-memory fixture data instead of live network calls.

_FAKE_PROBLEM_POOL = [
    {"contest_id": 1, "index": "A", "name": "Watermelon", "rating": 800, "tags": ["math", "brute force"]},
    {"contest_id": 4, "index": "A", "name": "Watermelon", "rating": 800, "tags": ["math", "brute force"]},
    {"contest_id": 71, "index": "A", "name": "Way Too Long Words", "rating": 800, "tags": ["strings"]},
    {"contest_id": 231, "index": "A", "name": "Team", "rating": 800, "tags": ["greedy"]},
    {"contest_id": 580, "index": "C", "name": "Kefa and Park", "rating": 1500, "tags": ["dfs and similar", "graphs", "trees"]},
    {"contest_id": 1547, "index": "F", "name": "Array Stabilization", "rating": 1700, "tags": ["graphs", "shortest paths"]},
    {"contest_id": 1632, "index": "D", "name": "New Year Concert", "rating": 1900, "tags": ["dp", "greedy"]},
    {"contest_id": 1234, "index": "D", "name": "Distinct Characters Queries", "rating": 2100, "tags": ["dsu", "graphs"]},
    {"contest_id": 4, "index": "C", "name": "Registration System", "rating": 1300, "tags": ["math"]},
    {"contest_id": 1, "index": "B", "name": "Spreadsheet", "rating": 1600, "tags": ["math", "implementation"]},
]


@pytest_asyncio.fixture
async def mock_cf_network(monkeypatch):
    """
    Opt-in fixture (NOT autouse) — request it explicitly in any test that
    exercises RecommenderService / the full LangGraph workflow so those
    tests run offline against deterministic fixture data instead of the
    live Codeforces API. Phase 2's own CodeforcesClient tests intentionally
    do NOT use this fixture, since they test the real HTTP layer via respx.
    """
    from app.services.problem_pool_service import ProblemPoolService
    from app.codeforces.client import CodeforcesClient

    async def _fake_get_pool(cls, force_refresh: bool = False):
        return list(_FAKE_PROBLEM_POOL)

    async def _fake_get_solved_problems(self, handle: str):
        return []

    monkeypatch.setattr(ProblemPoolService, "get_pool", classmethod(_fake_get_pool))
    monkeypatch.setattr(CodeforcesClient, "get_solved_problems", _fake_get_solved_problems)
    yield
