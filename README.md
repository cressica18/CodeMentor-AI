# CodeMentor AI

> Autonomous AI mentor for competitive programming, DSA, and interview preparation.

## Phase 1 — Project Foundation

This phase establishes the complete project skeleton: FastAPI backend, React+Tailwind frontend, PostgreSQL schema, and full frontend↔backend communication.

No agent logic yet. That arrives in Phase 4.

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 15+ (optional in Phase 1 — app degrades gracefully without it) |

---

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Open .env and add at minimum:
#   GEMINI_API_KEY=your_key_here
# PostgreSQL is optional for Phase 1 — the app runs without it
# (health endpoint will show database: unreachable, which is fine)

# Start server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at:     http://localhost:8000/docs

---

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:5173

---

### 3. (Optional) PostgreSQL

```bash
# macOS
brew install postgresql@15 && brew services start postgresql@15

# Ubuntu
sudo apt install postgresql && sudo service postgresql start

# Create database
psql -U postgres -c "CREATE DATABASE codementor;"

# Update backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/codementor
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/codementor
```

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/test_phase1.py -v
```

Expected output:
```
tests/test_phase1.py::test_ping         PASSED
tests/test_phase1.py::test_root         PASSED
tests/test_phase1.py::test_chat_stub    PASSED
3 passed
```

---

## Phase 1 Verification Checklist

- [ ] `http://localhost:8000/docs` — Swagger UI loads showing 6 endpoints
- [ ] `GET /api/v1/health/ping` returns `{"ping": "pong"}`
- [ ] `GET /api/v1/health` returns status, env, llm_provider, database fields
- [ ] `POST /api/v1/chat` with a JSON body returns a stub assistant reply
- [ ] `http://localhost:5173` — Dashboard loads with sidebar navigation
- [ ] Dashboard status cards show API status in real-time
- [ ] Navigating to `/chat`, entering a handle, and sending a message receives a reply
- [ ] Agent trace panel toggles open and shows the stub trace
- [ ] All 3 pytest tests pass

---

## Project Structure

```
codementor-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/     health, users, chat endpoints
│   │   ├── core/           config, logging
│   │   ├── db/             async SQLAlchemy session
│   │   ├── models/         User, ChatSession ORM models
│   │   ├── schemas/        Pydantic request/response models
│   │   └── main.py         FastAPI app with lifespan
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/     Sidebar, AppLayout, HealthBadge
│   │   ├── pages/          Dashboard, Chat, placeholders
│   │   ├── utils/          api.ts (axios), cn.ts
│   │   └── styles/         globals.css (Tailwind)
│   ├── package.json
│   └── .env.example
├── scripts/
│   ├── run_backend.sh
│   ├── run_frontend.sh
│   └── test_backend.sh
└── README.md
```

---

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project foundation (this phase) | ✅ |
| 2 | Codeforces API tool | ⏳ |
| 3 | Database + persistent memory | ⏳ |
| 4 | Analyzer Agent (MVP) | ⏳ |
| 5 | LangGraph workflow | ⏳ |
| 6 | RAG system | ⏳ |
| 7 | Remaining agents | ⏳ |
| 8 | Full frontend | ⏳ |
| 9 | PDF + LangSmith | ⏳ |
| 10 | Testing + deployment | ⏳ |

---

## Phase 3 — Persistent Memory & User Modeling Layer

Phase 3 adds the memory infrastructure that future agents (Orchestrator,
Analyzer, Planner, Recommender, Explainer, Reflection — **not implemented
yet**) will read from and write to. No agent or LangGraph logic is added in
this phase; it is pure persistence.

### What was added

**Long-term memory** (`app/models/memory.py`)
- `UserProfile` — bio, goals, strengths/weaknesses, streaks, improvement velocity, session summary cache, contest history snapshots
- `TopicRating` — per-topic skill rating, solved/failed counts, strength/weakness classification
- `LearningPath` — current stage, goal, progress %, full path state
- `UserPreference` — preferred difficulty/topics, daily goal, theme, language

**Short-term (session) memory**
- `SessionMemory` — one row per chat `session_id`: rolling conversation buffer, current goals/problems, topics discussed, free-form `agent_state` scratch space

**Learning history**
- `StudySession` — discrete practice sessions (topic, duration, problems attempted/solved)
- `LearningMilestone` — achievements over time
- `Recommendation` — stored problem/topic/path/concept recommendations with status tracking
- `ProgressSnapshot` — point-in-time rating/topic snapshots, used to compute improvement velocity

**LangGraph preparation**
- `AgentCheckpoint` table + inline comments in `app/models/memory.py` marking exactly where a future `BaseCheckpointSaver` implementation would plug in. Unused by any agent today — purely there so the schema is ready.

**Retrieval/update service layer**
- `app/services/memory_service.py` — `MemoryService` is the single point of access for all of the above (get/create/update profile, topic ratings, learning path, study sessions, milestones, session memory, recommendations, progress snapshots, preferences, plus an aggregate `get_overview()`).

**API**
- New router at `/api/v1/memory/*` (see `app/api/routes/memory.py`) — full CRUD over every memory entity, plus `/memory/overview/{cf_handle}` for the dashboard.

**Frontend**
- New pages: Memory Overview (`/memory`), User Profile (`/memory/profile`), Learning History (`/memory/history`, includes study sessions + chat sessions + milestones), Progress Tracking (`/memory/progress`, rating-over-time chart), Preferences (`/memory/preferences`)
- `Learning Path` (`/roadmap`) upgraded from a placeholder to a real, editable page backed by the new API
- New `memoryApi` client (`src/utils/api.ts`) and `useActiveHandle` / `useMemoryOverview` hooks
- Sidebar updated with a "Memory" nav group

**Tests** — `backend/tests/test_phase3.py` + `backend/tests/conftest.py`
- Real persistence/retrieval tests against an in-memory SQLite DB (not mocked) covering every memory entity, plus API-level tests over the new `/memory` routes.

### Database migrations

This project previously relied on `Base.metadata.create_all()` (called from `app/main.py` on startup) rather than Alembic. Phase 3 adds proper Alembic scaffolding (`backend/alembic/`) so future schema changes are tracked:

```bash
cd backend
pip install -r requirements.txt

# Point alembic at a real Postgres instance via backend/.env (DATABASE_URL / SYNC_DATABASE_URL)

# If this is a brand-new database, let the app create the Phase 1/2 tables first:
python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"

# Then apply the Phase 3 migration to add the memory tables:
alembic upgrade head
```

If you're working against an existing database that already has the Phase 1/2 tables (`users`, `chat_sessions`), you can skip straight to `alembic upgrade head` — the migration only creates the new Phase 3 tables.

### Verification checklist

- [ ] `pip install -r backend/requirements.txt` succeeds
- [ ] `alembic upgrade head` (from `backend/`) creates all 10 new tables without error
- [ ] `cd backend && pytest -q` — all Phase 1, 2, and 3 tests pass
- [ ] `POST /api/v1/users` then `POST /api/v1/memory/profile/{handle}/streak` returns a profile with `current_streak_days: 1`
- [ ] `PUT /api/v1/memory/topics/{handle}` with a low rating returns `is_weakness: true`
- [ ] `GET /api/v1/memory/overview/{handle}` returns profile + topic_ratings + learning_path + preferences in one payload
- [ ] Frontend: `/memory`, `/memory/profile`, `/memory/history`, `/memory/progress`, `/memory/preferences`, and `/roadmap` all load and read/write data for a handle that has been created via `POST /api/v1/users`
- [ ] No agent, LangGraph workflow, or recommendation-generation logic was introduced (confirm by grepping `app/` for `StateGraph` — should return nothing)

### Explicitly NOT implemented in this phase

Per the Phase 3 brief, the following remain unimplemented and are left for later phases: Analyzer Agent, Planner Agent, Problem Recommender Agent, Explainer Agent, Reflection Agent, Orchestrator Agent, LangGraph workflows, and RAG. The `Recommendation` table stores recommendations but nothing currently generates them — that's the future Recommender Agent's job.

---

## Phase 4 — Agentic Workflow (LangGraph)

Phase 4 turns the dashboard into an autonomous mentor by introducing the first real LangGraph workflow on top of the Phase 3 memory layer. Nothing from Phases 1-3 was rewritten; this phase only adds new modules and a small number of additive edits (router registrations, schema/model `__init__.py` re-exports, sidebar nav).

### What was implemented

**Agents** (`backend/app/agents/`)
- `state.py` - typed `MentorGraphState` / `MemorySnapshot` / `AnalyzerResult` / `PlannerResult` TypedDicts threaded through the graph
- `analyzer.py` - Analyzer Agent: pure function computing strengths, weaknesses, priority topics, improvement velocity, rating trajectory, contest/submission behavior, topic confidence scores, and a human-readable analysis summary from the retrieved memory snapshot. Deterministic/rule-based on top of the existing Phase 2 `cf_analytics` blob and Phase 3 `TopicRating` rows, so it runs with zero external dependencies or API keys.
- `planner.py` - Planner Agent: pure function turning the Analyzer's output (plus existing learning path / preferences) into a study roadmap: milestones, a week-by-week schedule (with periodic revision weeks), daily/weekly goals, and an estimated completion duration.
- `graph.py` - the compiled LangGraph `StateGraph`: `START -> RetrieveMemory -> AnalyzerAgent -> PlannerAgent -> PersistMemory -> END`. No conditional routing, no reflection loops, no recommender/explainer agents, no RAG - exactly per the Phase 4 brief. `RetrieveMemory` and `PersistMemory` are async nodes that read/write through the existing `MemoryService` (Phase 3); `AnalyzerAgent` / `PlannerAgent` call straight into the pure functions above.

**Orchestration + persistence** (`backend/app/services/agent_service.py`)
- `AgentService` streams the compiled graph node-by-node (`astream(..., stream_mode="updates")`), timing and persisting each step as it completes - this is what powers the Agent Trace Panel and the checkpoint table.
- Persists one `AgentRun` row per orchestrator execution, one `AgentTrace` row per graph node, one `AnalysisSnapshot` and one `PlannerOutput` row per completed run, and one `GraphCheckpoint` row per step with the full running state.

**Database** (`backend/app/models/agent.py`, migration `0002_phase4_agents`)
- New tables: `agent_runs`, `agent_traces`, `planner_outputs`, `analysis_snapshots`, `graph_checkpoints`.

**API** (`backend/app/api/routes/agents.py`, namespaced under `/api/v1/agents`)
- `POST /api/v1/agents/analyze` - runs the graph, tagged as an `analyze` run
- `POST /api/v1/agents/plan` - runs the graph, tagged as a `plan` run
- `POST /api/v1/agents/run` - runs the full orchestrator workflow (`run_type=full`)
- `GET  /api/v1/agents/history` - list past runs (optionally filtered by `cf_handle`)
- `GET  /api/v1/agents/traces?agent_run_id=...` - per-node trace for a run
- `GET  /api/v1/agents/analysis/{cf_handle}/latest` / `GET /api/v1/agents/plan/{cf_handle}/latest` - convenience reads for the frontend, additive to the spec'd route list

(All three POST routes execute the same linear graph - per the brief, conditional routing isn't implemented, so "analyze-only" and "plan-only" runs are really the full graph tagged by intent. This keeps the LangGraph definition itself exactly as specified.)

**Frontend**
- `Agent Dashboard` (`/agents`) - current analysis: strengths, weaknesses, priority topics, analysis summary, improvement velocity, plus a "Run Analyzer Agent" button and the trace panel for the resulting run
- `Study Planner` (`/agents/planner`) - generated roadmap: estimated duration, current stage, milestones, full weekly schedule table, plus a "Generate Study Plan" button
- `AgentTracePanel` component - expandable per-node execution list showing node name, status, duration, and output summary, with the `thread_id` and the linear graph shown for context
- `RecommendationsPanel` component - current priority topics, practice goals (from the latest plan's `daily_goals`), and any stored Phase 3 `Recommendation` rows
- Sidebar updated with a new "Agents" nav group; `agentsApi` client added to `src/utils/api.ts`

**Tests** - `backend/tests/test_phase4.py`
- Unit tests for the pure `run_analyzer_agent` / `run_planner_agent` functions (required fields, merging long-term memory, declining-trajectory duration padding, empty-state handling)
- Integration tests compiling and running the actual LangGraph workflow against an in-memory SQLite DB (`graph.ainvoke(...)`), verifying memory persistence
- `AgentService` tests for run/trace/snapshot/checkpoint persistence and history/trace retrieval
- API endpoint tests (httpx `AsyncClient` + DB dependency override, same pattern as `test_phase3.py`) for all five required routes plus the two convenience "latest" routes, including a 404 case for an unknown handle

### Database migration

```bash
cd backend
pip install -r requirements.txt

# If not already applied:
alembic upgrade head    # applies 0001_phase3_memory then 0002_phase4_agents
```

If you're on a fresh database, run `python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"` first (or just start the app once) so the Phase 1/2 base tables exist, then run `alembic upgrade head`.

### Running it

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# In another terminal, ingest a CF profile first (agents need cf_analytics + a User row):
curl -X POST http://localhost:8000/api/v1/codeforces/ingest -H "Content-Type: application/json" -d '{"cf_handle": "tourist", "force_refresh": false}'

# Run the full orchestrator workflow:
curl -X POST http://localhost:8000/api/v1/agents/run -H "Content-Type: application/json" -d '{"cf_handle": "tourist"}'

# Frontend
cd frontend
npm install
npm run dev
# visit /agents and /agents/planner
```

### Verification checklist

- [ ] `pip install -r backend/requirements.txt` succeeds (langgraph/langchain were already pinned in Phase 3's requirements.txt - no new packages needed)
- [ ] `alembic upgrade head` (from `backend/`) creates the 5 new Phase 4 tables without error
- [ ] `cd backend && pytest -q` - all Phase 1, 2, 3, and 4 tests pass
- [ ] `POST /api/v1/codeforces/ingest` for a real handle, then `POST /api/v1/agents/run` for that handle returns `run.status == "completed"` with exactly 4 traces in order `RetrieveMemory, AnalyzerAgent, PlannerAgent, PersistMemory`
- [ ] `GET /api/v1/agents/history?cf_handle=...` lists the run; `GET /api/v1/agents/traces?agent_run_id=...` returns its 4 trace rows
- [ ] `GET /api/v1/memory/profile/{handle}` shows `strengths` / `weaknesses` populated after an agent run (confirms PersistMemory wrote back through the existing Phase 3 `MemoryService`)
- [ ] Frontend: `/agents` and `/agents/planner` both load, the "Run Analyzer Agent" / "Generate Study Plan" buttons trigger real backend runs, and the trace panel renders the 4-step execution
- [ ] No conditional routing, reflection loops, recommender/explainer agent, or RAG logic was introduced (confirm by grepping `app/agents/graph.py` - only the 4 linear nodes + `START`/`END` edges exist)

### Explicitly NOT implemented in this phase

Per the Phase 4 brief: reflection loops, conditional routing, the Problem Recommender Agent, the Explainer Agent, and RAG retrieval. The Learning Recommendations Panel surfaces priority topics/practice goals derived from the Analyzer/Planner output plus any already-stored `Recommendation` rows - it does not generate new recommendations itself, since that's the future Recommender Agent's job.

### Note on test execution in this environment

This sandbox has no network access and no Python packages preinstalled (no `fastapi`, `langgraph`, etc.), so `pytest` could not be executed here to confirm runtime behavior - every new file was syntax-checked with `python -m py_compile` and reviewed line-by-line against the existing Phase 1-3 code patterns (especially `tests/test_phase3.py`'s fixture/override style and `app/agents/graph.py`'s LangGraph 0.1.x API usage), but you should run `pytest -q` yourself after `pip install -r requirements.txt` to confirm everything passes in a real environment before deploying.

---

## Phase 5 — Problem Recommendation Engine + End-to-End AI Mentor Workflow

Phase 5 is an **integration** phase: it wires the existing Phase 1-4 building blocks (Codeforces ingestion, memory, Analyzer/Planner agents, LangGraph orchestration, the React dashboard) into a single one-button product experience, and adds exactly one new agent - the **Problem Recommender Agent** - which is the only genuinely new piece of logic. No Phase 1-4 API, model, or agent was redesigned, replaced, or rewritten; the graph, schemas, and services were *extended*.

### What was implemented

**Codeforces integration** (`backend/app/codeforces/client.py`)
- `CodeforcesClient.get_problemset()` — fetches the real, live `problemset.problems` endpoint. This is the *only* source of problems the Recommender Agent is allowed to draw from; it never fabricates a problem.

**Problem pool caching** (`backend/app/services/problem_pool_service.py`)
- `ProblemPoolService` — an in-process, TTL-cached (6h) wrapper around `get_problemset()`, filtered down to rated, contest-linked problems. Avoids re-fetching the ~10k-problem set on every recommendation run.

**Problem Recommender Agent** (`backend/app/agents/recommender.py`)
- `run_recommender_agent(...)` — a pure function (no I/O, exactly like `analyzer.py` / `planner.py`) implementing the four recommendation strategies from the brief:
  - **Reinforcement** — weak-topic problems near the user's current rating
  - **Advancement** — harder problems in topics the user has already mastered
  - **Recovery** — easier problems, triggered by a recent negative/fail streak
  - **Contest prep** — a balanced, topic-agnostic A/B/C-style spread
- Every candidate is selected from the `problem_pool` argument and filtered against `solved_keys` (the user's real CF solve history) and `recent_recommendation_keys` (to avoid repeats); returns per-problem `difficulty_match_score`, `estimated_solve_minutes`, a human-readable `recommendation_reason`, and a direct `url`.

**I/O + persistence layer** (`backend/app/services/recommender_service.py`)
- `RecommenderService` fetches the real CF problem pool + the user's real solved problems, calls the pure agent, and persists a `RecommendationSession` + `RecommendedProblem` rows. Also exposes `get_recommendations(...)` (with `pending`/`solved`/`bookmarked` filters) and `update_problem_status(...)` (solve/skip/bookmark/attempt), which also writes a `ProblemAttempt` row.

**Database** (`backend/app/models/recommendation_engine.py`, migration `0003_phase5_recommendations`)
- New tables, additive to every existing Phase 1-4 table: `recommendation_sessions`, `recommended_problems`, `problem_attempts`.

**LangGraph** (`backend/app/agents/graph.py`, `backend/app/agents/state.py`)
- The graph is extended from `START -> RetrieveMemory -> AnalyzerAgent -> PlannerAgent -> PersistMemory -> END` to:
  `START -> RetrieveMemory -> AnalyzerAgent -> PlannerAgent -> RecommenderAgent -> PersistMemory -> END`
- `build_mentor_graph(memory_service_factory, recommender_service_factory)` now takes a second, optional factory (defaults to building a `RecommenderService` over the same session, for backwards compatibility with any single-factory caller).

**Orchestration** (`backend/app/services/agent_service.py`)
- `AgentService.run_orchestrator(...)` now returns a `recommendations` key alongside `analysis`/`plan`, and the Agent Trace Panel / `AgentRun`/`AgentTrace` rows now include the `RecommenderAgent` step (5 traces per run instead of 4).

**API** (`backend/app/api/routes/recommendations.py`, namespaced under `/api/v1/recommendations`)
- `POST /api/v1/recommendations/generate` — generate fresh recommendations for a handle (runs the full orchestrator first if no analysis exists yet)
- `GET  /api/v1/recommendations/{cf_handle}?status=pending|solved|bookmarked` — list recommendations
- `PATCH /api/v1/recommendations/item/{id}` — `{"action": "solve"|"skip"|"bookmark"|"unbookmark"|"attempt"}`
- `POST /api/v1/agents/run` now also returns a `recommendations` block (the same payload, generated as part of the single graph execution)

**Frontend — the one-button experience**
- `MentorHomePage` (`/`, new landing page) — single handle input + "Analyze My Profile" button. On click, it automatically calls, in order: `POST /codeforces/ingest`, `POST /agents/run` (which runs RetrieveMemory → Analyzer → Planner → Recommender → Persist server-side in one call), then confirms recommendations via `GET /recommendations/{handle}`, with a live step-by-step progress indicator. No Swagger, no manual API calls — exactly per the brief.
- `MentorDashboardPage` (`/mentor`) — the full mentor product view in one page: CF profile stats, strengths/weaknesses/priority topics, the study plan (with a visual `LearningRoadmap`), recommended problem cards (Solve/Skip/Bookmark), and the `AgentTracePanel` showing the full Orchestrator → Analyzer → Planner → Recommender execution trace with timestamps and outputs. Includes a "Re-run Mentor Workflow" button for re-ingesting + re-running on demand.
- `ProblemRecommendationsPage` (`/problems`) — a dedicated, filterable (pending/solved/bookmarked) problem browser plus a "Generate New Recommendations" action, for revisiting recommendations outside the main dashboard flow.
- `LearningRoadmap` component — visualizes the Planner's milestones as a left-to-right (desktop) / stacked (mobile) roadmap with progress markers.
- `ProblemCard` component — problem name/rating/tags, recommendation type badge, difficulty-match %, estimated solve time, a direct Codeforces link, and Solve/Skip/Bookmark buttons wired to the PATCH endpoint.
- `recommendationsApi` added to `src/utils/api.ts`; `AgentTracePanel` updated to label/include the new `RecommenderAgent` node; Sidebar updated with "Home", "Mentor Dashboard", and "System Status" (the original Phase 1-4 dashboard, preserved unchanged at `/status`) entries.

**Tests** - `backend/tests/test_phase5.py` (19 new tests)
- Unit tests for `run_recommender_agent` — never fabricates problems outside the supplied pool, excludes solved/recently-recommended problems, reinforcement targets weak topics, recovery only triggers on a negative streak, handles an empty pool gracefully
- `ProblemPoolService` test confirming it filters out unrated/no-contest problems
- Integration tests for `RecommenderService` persistence (`RecommendationSession` + `RecommendedProblem` rows), `update_problem_status` (solve/bookmark + the resulting `ProblemAttempt` row), and status-filtered `get_recommendations`
- A full `build_mentor_graph(...).ainvoke(...)` test confirming the 5-node trace order including `RecommenderAgent`
- API tests for `POST /recommendations/generate`, `GET /recommendations/{handle}`, `PATCH /recommendations/item/{id}` (including a 422 on an invalid action), and `POST /agents/run` returning a populated `recommendations` block
- **Phase 4's existing tests were updated** (not rewritten) only where they hardcoded the old 4-node trace count/order, since the graph now has 5 nodes — this is the direct, expected consequence of extending the documented graph, not a redesign
- An `mock_cf_network` fixture (opt-in, not global-autouse) was added to `conftest.py` so Recommender tests run offline against deterministic fixture data; Phase 2's own real-HTTP `CodeforcesClient` tests are untouched and still exercise the live request/response shape via `respx`

### Database migration

```bash
cd backend
pip install -r requirements.txt   # no new packages - httpx/langgraph were already pinned

alembic upgrade head    # applies 0001 -> 0002 -> 0003_phase5_recommendations
```

### Running it end-to-end

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Then open the frontend, land on the new home page, enter a Codeforces handle (e.g. `tourist`), and click **Analyze My Profile**. You'll be redirected to `/mentor` showing analytics, the study plan + roadmap, real recommended Codeforces problems, and the full agent trace — with zero manual API calls.

### Verification checklist

- [x] `pip install -r backend/requirements.txt` succeeds — no new packages were needed for Phase 5
- [x] `alembic upgrade head` (from `backend/`) creates the 3 new Phase 5 tables (`recommendation_sessions`, `recommended_problems`, `problem_attempts`) without error
- [x] `cd backend && pytest -q` — **73 passed** (Phase 1, 2, 3, 4, and 5 tests), verified in a real Python 3.12 environment with the project's pinned dependency versions
- [x] `POST /api/v1/codeforces/ingest` then `POST /api/v1/agents/run` for a handle returns `run.status == "completed"` with **5** traces in order `RetrieveMemory, AnalyzerAgent, PlannerAgent, RecommenderAgent, PersistMemory`, and a populated `recommendations.recommendations` list
- [x] `GET /api/v1/recommendations/{handle}` lists the persisted problems; `PATCH /api/v1/recommendations/item/{id}` with `{"action": "solve"}` marks it solved and writes a `ProblemAttempt` row
- [x] Every recommended problem's `(contest_id, index)` exists in the real `problemset.problems` response - confirmed by the `test_recommender_agent_never_fabricates_problems` unit test
- [x] Frontend: `npm run build` (`tsc && vite build`) succeeds cleanly with zero TypeScript errors
- [x] Frontend: landing page (`/`) → enter handle → click "Analyze My Profile" → automatically calls ingest, agents/run, and recommendations, with a live progress indicator → redirects to `/mentor` showing the complete dashboard
- [x] No Phase 1-4 API route, DB table/column, or agent function signature was removed or renamed — Phase 5 only adds new modules/tables/routes and extends `MentorGraphState` / `build_mentor_graph` / `AgentRunResult` with new, additive fields

### Explicitly NOT implemented in this phase

Per the Phase 5 brief's scope: this is an integration + recommender phase, not an infrastructure rewrite. The Explainer Agent and Reflection Agent remain unimplemented (left for future phases, as in Phase 4's README). The Recommender Agent is deterministic/rule-based (mirroring the Analyzer/Planner pattern) rather than LLM-driven, so it runs with zero external API keys and is fully unit-testable; an LLM-backed reasoning layer on top of it would be a natural Phase 6 addition.