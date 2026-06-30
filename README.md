# CodeMentor AI

CodeMentor AI is a full-stack application that analyzes a user's Codeforces competitive programming history and turns it into a personalized mentoring workflow. A FastAPI backend orchestrates a multi-agent LangGraph pipeline that evaluates a user's strengths and weaknesses, builds a study plan, and recommends real Codeforces problems, while a React frontend presents the resulting analytics, plan, and recommendations in an interactive dashboard.

## Overview

Competitive programmers on Codeforces accumulate a large amount of historical data — contest results, submission history, rating changes — but turning that data into an actionable study routine is left entirely to the user. CodeMentor AI addresses this by ingesting a Codeforces handle, computing structured analytics from the public Codeforces API, and running that data through a sequence of deterministic, rule-based agents that:

- identify topic-level strengths and weaknesses,
- generate a milestone-based study plan with a weekly schedule,
- recommend specific, real Codeforces problems suited to the user's current level, and
- persist all of this to a database so future sessions build on prior history rather than starting from scratch.

A chat interface, backed by the Google Gemini API (with a deterministic template fallback when no API key is configured), lets the user ask questions about their own analysis, plan, and recommendations in natural language.

## Features

**Codeforces analytics**
- Full ingestion of a Codeforces handle via the public Codeforces API (user info, rating history, submissions, problem set)
- Computed analytics: current/max rating, rank, solved-problem counts, contest participation, tag-level strength/weakness breakdown, rating trend, and a submission activity heatmap
- Cached profile lookups, with an explicit `force_refresh` / `refresh` option to re-fetch live data

**AI mentor workflow**
- A LangGraph-orchestrated, five-node pipeline (Retrieve Memory → Analyzer → Planner → Recommender → Persist Memory) that runs end-to-end from a single API call
- Deterministic, rule-based agents that require no LLM credentials to execute
- A one-button "Analyze My Profile" flow on the frontend that chains Codeforces ingestion, the full agent run, and recommendation retrieval automatically

**Study planning**
- Milestone generation per priority topic, with target problem counts
- A week-by-week schedule, including periodic revision weeks
- Estimated time-to-completion based on rating trajectory and user-configured daily goal minutes
- An editable Learning Path page backed by persistent state

**Problem recommendation engine**
- Four recommendation strategies — reinforcement, advancement, recovery, and contest preparation — selected based on the user's analyzed weaknesses, strengths, and recent solve streak
- Every recommended problem is drawn from the live Codeforces `problemset.problems` endpoint; the agent does not fabricate problems
- Recommendations are filtered against the user's actual solved problems and recently-shown recommendations to avoid repeats
- Per-problem difficulty-match scoring, estimated solve time, and a human-readable recommendation reason

**Learning memory system**
- Long-term `UserProfile`, per-topic `TopicRating`, `LearningPath`, and `UserPreference` records
- Short-term, per-chat-session memory (`SessionMemory`) holding a rolling conversation buffer and scratch agent state
- Historical records: `StudySession`, `LearningMilestone`, `Recommendation`, and `ProgressSnapshot`
- A single `MemoryService` layer providing CRUD and an aggregate overview across all of the above

**Progress tracking**
- Point-in-time rating/topic snapshots used to compute improvement velocity
- A rating-over-time chart and dedicated Progress Tracking page

**Chat assistant**
- A Gemini-backed conversational endpoint that grounds replies in the user's actual strengths, weaknesses, active study plan, milestones, recent study sessions, and current recommendations
- Falls back to a deterministic, memory-grounded template reply if no Gemini API key is configured or the API call fails
- Persists every message to both the long-lived chat session record and the short-term session memory buffer

**Agent tracing**
- Every orchestrator run is persisted as an `AgentRun` with one `AgentTrace` row per graph node, recording per-node duration and output summary
- A frontend Agent Trace Panel renders the node-by-node execution (including thread/run identifiers) for transparency into what each agent did and why

**User analytics and dashboards**
- A System Status dashboard (the original health/status view) showing live API health
- A Mentor Dashboard combining CF profile stats, strengths/weaknesses, the study plan with a visual roadmap, recommended problem cards, and the agent trace panel in one view
- A dedicated, filterable (pending / solved / bookmarked) problem browser

## System Architecture

CodeMentor AI follows a layered backend architecture (API → services → agents/data) paired with a component-based React frontend. The agent workflow is a linear LangGraph state machine sitting between the API layer and the persistence layer.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                           │
│  Pages: Home · Mentor Dashboard · Chat · CF Profile · Learning Path ·   │
│  Problems · Memory (Overview/Profile/History/Progress/Preferences) ·    │
│  Agent Dashboard · Study Planner · System Status                       │
│  axios client (src/utils/api.ts) ──────────────────────────────────┐    │
└──────────────────────────────────────────────────────────────────┼────┘
                                                                     │ HTTP / JSON
                                                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI, /api/v1)                      │
│  routes: health · users · chat · codeforces · memory · agents ·        │
│          recommendations                                               │
└───────────┬─────────────────────────────────────────────┬─────────────┘
            │                                              │
            ▼                                              ▼
┌────────────────────────────┐               ┌─────────────────────────────┐
│       Services layer        │               │     Agent / LangGraph layer │
│  CodeforcesService          │               │  START                      │
│  MemoryService              │◄─────────────►│   → RetrieveMemory          │
│  AgentService                │               │   → AnalyzerAgent           │
│  RecommenderService          │               │   → PlannerAgent            │
│  ProblemPoolService           │              │   → RecommenderAgent        │
└───────────┬─────────────────┘               │   → PersistMemory           │
            │                                  │  END                        │
            ▼                                  └──────────────┬──────────────┘
┌────────────────────────────┐                                │
│   SQLAlchemy (async) ORM    │◄───────────────────────────────┘
│   PostgreSQL                │
└───────────┬─────────────────┘
            │
            ▼
┌────────────────────────────┐
│   External: Codeforces API  │   (problemset.problems, user.info,
│   External: Gemini API      │    user.rating, user.status)
└────────────────────────────┘
```

**Frontend** — A Vite + React + TypeScript single-page application using React Router for navigation and Tailwind CSS for styling. Components are organized by domain (codeforces, agents, memory, recommendations) and communicate with the backend through a shared axios client.

**Backend** — A FastAPI application exposing a versioned REST API under `/api/v1`. On startup, the application attempts to initialize the database connection but degrades gracefully (continues running, reporting `database: unreachable` on the health endpoint) if PostgreSQL is not available.

**Database** — PostgreSQL accessed through SQLAlchemy's async ORM (`asyncpg` driver) for the application and a synchronous driver (`psycopg2`) for Alembic migrations. Schema changes are tracked through Alembic migration scripts.

**Agent workflow** — A LangGraph `StateGraph` of five nodes, compiled once and invoked per request via `graph.ainvoke(...)`. The graph is strictly linear: no conditional routing, branching, or reflection loops are implemented.

**External APIs** — The public Codeforces REST API (`https://codeforces.com/api`) for all competitive programming data, and the Google Gemini API (`gemini-2.5-flash`, called directly over its REST endpoint via `httpx`) for natural-language chat replies.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Router 6, Tailwind CSS, axios |
| Backend | FastAPI, Uvicorn, Pydantic v2 / pydantic-settings |
| Database | PostgreSQL, SQLAlchemy 2.0 (async, `asyncpg`), Alembic migrations |
| AI / Agent Framework | LangGraph, LangChain core, Google Gemini (via `langchain-google-genai` and direct REST calls), LangSmith (optional tracing) |
| Data Visualization | Recharts (rating trend, progress, tag charts), custom heatmap component |
| External APIs | Codeforces public API, Google Gemini API |
| Development Tools | pytest, pytest-asyncio, respx (HTTP mocking), aiosqlite (in-memory test DB), ESLint, ngrok-free local dev scripts (`scripts/`) |

## Project Structure

```
CodeMentor-AI/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # health, users, chat, codeforces, memory, agents, recommendations
│   │   ├── agents/             # analyzer.py, planner.py, recommender.py, graph.py, state.py
│   │   ├── codeforces/         # client.py, analytics.py, models.py, exceptions.py
│   │   ├── core/                # config.py, logging.py
│   │   ├── db/                  # async SQLAlchemy session/engine
│   │   ├── models/              # user, session, memory, agent, recommendation_engine ORM models
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # codeforces_service, memory_service, agent_service,
│   │   │                        # recommender_service, problem_pool_service
│   │   ├── tools/                # codeforces_tools.py (LangGraph tool wrapper)
│   │   └── main.py               # FastAPI app + lifespan
│   ├── alembic/                 # migration environment + versioned scripts
│   ├── tests/                   # test_phase1.py … test_phase5.py, conftest.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/          # agents/, codeforces/, layout/, memory/, recommendations/, ui/
│   │   ├── pages/                # Home, Mentor Dashboard, Chat, CF Profile, Learning Path,
│   │   │                        # Problems, Memory*, Agent Dashboard, Study Planner, Status
│   │   ├── hooks/                # useActiveHandle, useCFProfile, useMemoryOverview
│   │   ├── utils/                # api.ts (axios client), cn.ts
│   │   ├── styles/               # globals.css (Tailwind)
│   │   └── router.tsx
│   ├── package.json
│   └── .env.example
├── scripts/
│   ├── run_backend.sh           # venv setup + uvicorn
│   ├── run_frontend.sh          # npm install + vite dev
│   └── test_backend.sh
└── README.md
```

## Core Components

### Backend

**FastAPI application** (`app/main.py`) — Configures CORS from the `ALLOWED_ORIGINS` setting, registers the versioned API router, and uses an async context manager (`lifespan`) to initialize the database on startup and close the connection on shutdown. Database initialization failures are logged as warnings rather than raised, so the API remains usable without a running PostgreSQL instance.

**Services layer** (`app/services/`) — Each service wraps a single area of responsibility behind an async interface used by the API routes and the agent graph nodes:
- `CodeforcesService` — ingestion, caching, and retrieval of CF profile analytics
- `MemoryService` — single point of access for every long-term, short-term, and historical memory entity, plus an aggregate `get_overview()`
- `AgentService` — streams the compiled LangGraph node-by-node, timing and persisting each step (`AgentRun`, `AgentTrace`, `AnalysisSnapshot`, `PlannerOutput`, `GraphCheckpoint`)
- `RecommenderService` — fetches the live CF problem pool and the user's solved problems, invokes the pure recommender function, and persists results
- `ProblemPoolService` — an in-process, TTL-cached (6 hour) wrapper around the CF problem set, filtered to rated, contest-linked problems

**Database layer** (`app/db/`, `app/models/`) — An async SQLAlchemy engine/session factory and a declarative `Base`. ORM models are grouped by domain: `User`/`ChatSession` (core), `UserProfile`/`TopicRating`/`LearningPath`/`SessionMemory`/`StudySession`/`LearningMilestone`/`Recommendation`/`ProgressSnapshot`/`UserPreference`/`AgentCheckpoint` (memory), `AgentRun`/`AgentTrace`/`AnalysisSnapshot`/`PlannerOutput`/`GraphCheckpoint` (agent execution), and `RecommendedProblem`/`ProblemAttempt`/`RecommendationSession` (recommendation engine).

**Agent layer** (`app/agents/`) — Typed state definitions (`MentorGraphState`, `MemorySnapshot`, `AnalyzerResult`, `PlannerResult`) and three pure, synchronous functions (`run_analyzer_agent`, `run_planner_agent`, `run_recommender_agent`) with no I/O, wired together by `graph.py` into a compiled LangGraph `StateGraph`.

**Codeforces integration** (`app/codeforces/`) — An async HTTP client (`CodeforcesClient`) wrapping the public Codeforces API with retry and exponential backoff, typed Pydantic response models, and a dedicated exception hierarchy (`CFHandleNotFound`, `CFAPIError`, `CFRateLimitError`). A separate, pure `analytics.py` module converts raw API responses into the structured analytics blob stored on each `User` row.

**Recommendation engine** (`app/agents/recommender.py`) — Implements four selection strategies (reinforcement, advancement, recovery, contest prep), each operating over a caller-supplied problem pool and the user's real solve history, so recommendations are always traceable to an actual Codeforces problem.

### Frontend

**React architecture** — A component-driven SPA built with Vite, using functional components and hooks throughout. UI primitives (`HealthBadge`, `Skeleton`) sit under `components/ui`, with domain-specific components grouped under `components/codeforces`, `components/agents`, `components/memory`, and `components/recommendations`.

**Routing** — `react-router-dom`'s `createBrowserRouter`, with a single `AppLayout` wrapping all routes and a nested route table covering the home, mentor dashboard, chat, CF profile, learning path, problems, memory (overview/profile/history/progress/preferences), agent dashboard, study planner, and system status pages.

**State management** — Local component state and custom hooks (`useActiveHandle`, `useCFProfile`, `useMemoryOverview`) rather than a global state library; data is fetched directly from the backend per page via the shared axios client in `utils/api.ts`.

**Visualization components** — `RatingChart`, `DifficultyChart`, `TagCharts`, and `ActivityHeatmap` (built on Recharts and custom SVG) render CF profile analytics; `LearningRoadmap` visualizes planner milestones.

**Dashboard system** — `MentorHomePage` provides the single-button entry point (handle input → ingest → full agent run → recommendations, with a live step indicator); `MentorDashboardPage` is the consolidated product view; `DashboardPage` (mounted at `/status`) is the original system-health view preserved from the project's first phase.

### Multi-Agent Workflow

The LangGraph workflow is a strict linear sequence: `START → RetrieveMemory → AnalyzerAgent → PlannerAgent → RecommenderAgent → PersistMemory → END`. No conditional routing or reflection loops are implemented.

- **Retrieve Memory** — An async node that loads the user's full memory snapshot (profile, topic ratings, learning path, recent study sessions, recent recommendations, progress snapshots, preferences, and cached CF analytics) through `MemoryService` and assembles it into a single `MemorySnapshot` passed to the rest of the graph.
- **Analyzer Agent** — A pure function that computes strengths, weaknesses, priority topics, improvement velocity, rating trajectory, and topic confidence scores from the memory snapshot, producing a human-readable analysis summary. Deterministic and requires no external API calls.
- **Planner Agent** — A pure function that turns the Analyzer's output, plus the existing learning path and preferences, into milestones, a week-by-week schedule (including periodic revision weeks), daily/weekly goals, and an estimated completion duration.
- **Recommender Agent** — Fetches the live Codeforces problem pool and the user's actual solved problems, then applies the reinforcement / advancement / recovery / contest-prep strategies to select real, unsolved, non-repeated problems matched to the analysis.
- **Persist Memory** — Writes the analysis (strengths/weaknesses) back onto the long-term `UserProfile`, the generated plan onto `LearningPath`, per-topic results onto `TopicRating`, milestones onto `LearningMilestone`, and records a `StudySession` row marking that a full mentor workflow run occurred.

Every node's input/output summary is recorded into a running trace list, which `AgentService` persists as `AgentRun` and `AgentTrace` rows and which the frontend's Agent Trace Panel renders.

## Database Schema

The schema is organized into four groups of related tables, all created additively across migrations `0001_phase3_memory`, `0002_phase4_agents`, and `0003_phase5_recommendations`:

**Core** — `users` (Codeforces handle, rating, cached `cf_analytics` JSON blob) and `chat_sessions` (one row per chat session, with a JSON message list and summary), linked by foreign key.

**Memory** — `user_profile`, `topic_rating`, `learning_path`, and `user_preference` hold long-term, per-user state. `session_memory` holds short-term, per-chat-session scratch state. `study_session`, `learning_milestone`, `recommendation`, and `progress_snapshot` form the historical record that the analyzer and planner read from. `agent_checkpoint` exists as schema preparation for a future `BaseCheckpointSaver` implementation and is not currently written to by any agent.

**Agent execution** — `agent_runs` (one row per orchestrator execution), `agent_traces` (one row per graph node per run, with timing and output summary), `analysis_snapshots` and `planner_outputs` (one row per completed run), and `graph_checkpoints` (full running state per step).

**Recommendation engine** — `recommendation_sessions` (one row per recommendation generation call), `recommended_problems` (individual problem recommendations with status tracking — pending/solved/skipped/bookmarked), and `problem_attempts` (a row per solve/skip/bookmark/attempt action against a recommended problem).

All tables are linked back to a `User` (directly or via `cf_handle`), so every entity in the system is scoped to a single Codeforces profile.

## API Endpoints

All routes are mounted under `/api/v1`.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Application status, environment, active LLM provider, database reachability |
| GET | `/health/ping` | Liveness check |
| POST | `/users` | Create a user record for a Codeforces handle |
| GET | `/users/{cf_handle}` | Retrieve a user record |
| POST | `/chat` | Agent- and Gemini-backed chat turn, grounded in persisted memory |
| POST | `/chat/session` | Create a new chat session |
| POST | `/codeforces/ingest` | Full ingestion: fetch CF data, compute analytics, persist, return |
| GET | `/codeforces/{handle}` | Cached or freshly-fetched analytics (`?refresh=true` to force) |
| GET | `/codeforces/{handle}/summary` | Lightweight profile summary |
| GET | `/memory/overview/{cf_handle}` | Aggregate profile + topic ratings + learning path + preferences |
| GET / PUT | `/memory/profile/{cf_handle}` | Long-term user profile |
| POST | `/memory/profile/{cf_handle}/streak` | Update study streak |
| GET / PUT | `/memory/topics/{cf_handle}` | Per-topic skill ratings |
| GET / PUT | `/memory/learning-path/{cf_handle}` | Learning path state |
| GET / POST | `/memory/study-sessions/{cf_handle}` | Study session history |
| POST | `/memory/study-sessions/{session_db_id}/end` | Close out a study session |
| GET / POST | `/memory/milestones/{cf_handle}` | Learning milestones |
| GET / PUT | `/memory/session/{session_id}` | Short-term session memory |
| POST | `/memory/session/{session_id}/messages` | Append a message to session memory |
| POST | `/memory/session/{session_id}/summary` | Summarize a session |
| GET / POST | `/memory/recommendations/{cf_handle}` | Stored recommendation records (Phase 3 table) |
| PATCH | `/memory/recommendations/item/{recommendation_id}` | Update a stored recommendation |
| GET / POST | `/memory/progress/{cf_handle}` | Rating/topic progress snapshots |
| GET | `/memory/chat-sessions/{cf_handle}` | Chat session summaries |
| GET / PUT | `/memory/preferences/{cf_handle}` | User preferences |
| POST | `/agents/analyze` | Run the full graph, tagged as an analysis run |
| POST | `/agents/plan` | Run the full graph, tagged as a planning run |
| POST | `/agents/run` | Run the full orchestrator workflow end to end |
| GET | `/agents/history` | List past agent runs (optionally filtered by handle) |
| GET | `/agents/traces` | Per-node trace for a given run |
| GET | `/agents/analysis/{cf_handle}/latest` | Latest persisted analysis |
| GET | `/agents/plan/{cf_handle}/latest` | Latest persisted plan |
| POST | `/recommendations/generate` | Generate fresh problem recommendations for a handle |
| GET | `/recommendations/{cf_handle}` | List recommendations (filter by `pending`/`solved`/`bookmarked`) |
| PATCH | `/recommendations/item/{id}` | Update a recommendation's status (solve/skip/bookmark/attempt) |

Note: the three `POST /agents/*` routes all execute the same linear graph; "analyze" and "plan" runs are the full graph tagged by intent, since conditional routing is not implemented.

## Key Features Demonstration

1. **User enters a Codeforces handle** on the home page and clicks "Analyze My Profile."
2. **Analytics generation** — the frontend calls `POST /codeforces/ingest`, which fetches the user's live Codeforces data and computes rating, tag, and activity analytics.
3. **Weakness analysis** — `POST /agents/run` executes the full LangGraph workflow; the Analyzer Agent scores topic-level strengths and weaknesses from the freshly ingested analytics and existing memory.
4. **Study plan creation** — the Planner Agent turns the analysis into milestones and a weekly schedule.
5. **Problem recommendation** — the Recommender Agent selects real Codeforces problems matched to the user's weaknesses, strengths, and recent solve streak.
6. **Memory persistence** — the Persist Memory node writes strengths/weaknesses, the study plan, topic ratings, and milestones back to the database.
7. **Progress tracking** — subsequent visits to `/memory/progress` and the Mentor Dashboard reflect the persisted history, and each new agent run builds on top of it rather than starting over.

## Installation

### Backend Setup

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edit .env and set at minimum GEMINI_API_KEY

uvicorn app.main:app --reload --port 8000
```

The backend runs at `http://localhost:8000`; interactive API docs are available at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend

npm install

cp .env.example .env

npm run dev
```

The frontend runs at `http://localhost:5173`.

### Environment Variables

**Backend (`backend/.env`)**

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key, used by the chat endpoint for LLM-generated replies. If unset, chat falls back to a deterministic template reply. |
| `OPENAI_API_KEY` | Optional fallback LLM provider key. |
| `DATABASE_URL` | Async PostgreSQL connection string (`postgresql+asyncpg://...`), used by the application at runtime. |
| `SYNC_DATABASE_URL` | Synchronous PostgreSQL connection string (`postgresql+psycopg2://...`), used by Alembic. |
| `LANGCHAIN_TRACING_V2` | Enables LangSmith tracing of agent runs when set to `true`. |
| `LANGCHAIN_API_KEY` | LangSmith API key, required if tracing is enabled. |
| `LANGCHAIN_PROJECT` | LangSmith project name. |
| `APP_ENV` | `development` or `production`; controls log verbosity. |
| `SECRET_KEY` | Application secret key. |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins for the frontend. |

**Frontend (`frontend/.env`)**

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Base URL of the backend API (defaults to `http://localhost:8000`). |

PostgreSQL is optional for basic API exploration — the application starts and serves requests even when the database is unreachable, reporting that status on `GET /health`. A working database is required for any endpoint that reads or writes persisted data.

## Running the Application

**Start the backend**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Start the frontend**
```bash
cd frontend
npm run dev
```

**Run migrations** (against a real PostgreSQL instance configured via `DATABASE_URL` / `SYNC_DATABASE_URL`)
```bash
cd backend

# If the database is new, create the base (Phase 1/2) tables first:
python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"

# Apply all tracked migrations:
alembic upgrade head
```

**Run tests**
```bash
cd backend
source .venv/bin/activate
pytest -q
```

Convenience scripts are also provided under `scripts/`: `run_backend.sh` (creates the virtual environment, installs dependencies, and starts uvicorn), `run_frontend.sh` (installs npm dependencies and starts the Vite dev server), and `test_backend.sh`.

## Testing

The backend test suite is organized by development phase, with 74 tests across five files (`backend/tests/test_phase1.py` through `test_phase5.py`):

- **Phase 1** — basic API liveness and the original chat stub
- **Phase 2** — the Codeforces client and analytics engine, including real-HTTP-shape tests via `respx`
- **Phase 3** — memory persistence and retrieval across every memory entity, run against an in-memory SQLite database, plus API-level tests over the `/memory` routes
- **Phase 4** — unit tests for the pure analyzer/planner functions, an integration test that compiles and runs the actual LangGraph workflow, `AgentService` persistence tests, and API tests for every `/agents` route
- **Phase 5** — unit tests for the recommender agent (including a test asserting it never recommends a problem outside the supplied pool), `ProblemPoolService` filtering, `RecommenderService` persistence, a full graph trace-order test, and API tests for the `/recommendations` routes

Tests run against an in-memory SQLite database (`aiosqlite`) via fixtures in `conftest.py`, so the full suite does not require a running PostgreSQL instance. A separate, opt-in `mock_cf_network` fixture lets recommender tests run offline against deterministic fixture data, while the Codeforces client's own tests still exercise the live request/response shape through `respx`.

Run the full suite with:
```bash
cd backend
pytest -q
```

Or a single phase:
```bash
pytest tests/test_phase4.py -v
```

## Design Decisions

**Deterministic, rule-based agents instead of LLM-driven reasoning.** The Analyzer, Planner, and Recommender agents are implemented as pure functions with no I/O and no LLM calls. This keeps the core workflow fast, fully unit-testable, and runnable without any API key, at the cost of less nuanced reasoning than an LLM-backed agent would provide. An LLM-backed reasoning layer on top of the existing deterministic output is a natural extension point rather than a replacement.

**Linear LangGraph workflow.** The graph has no conditional routing or reflection loops. This trades adaptability (the workflow cannot currently decide to skip or repeat a step based on intermediate results) for predictability and straightforward testing of the full pipeline.

**Graceful degradation without a database.** The FastAPI application starts and serves non-persistent endpoints even if PostgreSQL is unreachable, rather than failing to boot. This makes local exploration of the API (via `/docs`) possible before a database is configured, at the cost of allowing the application to run in a state where most endpoints will fail.

**Gemini called directly via REST instead of through an SDK.** The chat endpoint calls the Gemini REST API directly using `httpx` (already a project dependency for the Codeforces client) rather than adding the Gemini Python SDK. This avoids an additional dependency, at the cost of manually constructing the request/response handling that an SDK would otherwise provide.

**Recommendations are constrained to a real problem pool.** The Recommender Agent receives the Codeforces problem set as an explicit argument and is structurally unable to invent a problem; this is enforced and verified by a dedicated unit test. The tradeoff is that recommendation quality depends entirely on the freshness and completeness of the cached problem pool.

**Alembic introduced after initial schema creation.** Early tables were created via `Base.metadata.create_all()` rather than migrations; Alembic was introduced once the schema began evolving across phases, so the first migration assumes the base tables already exist (created via `init_db()`) rather than creating them itself.

## Future Improvements

Based on the existing architecture, realistic next steps include:

- An Explainer Agent and Reflection Agent, both referenced in the memory schema's design but not yet implemented
- Conditional routing or a reflection loop in the LangGraph workflow, so the orchestrator can adapt based on intermediate agent output
- An LLM-backed reasoning layer on top of the deterministic Analyzer/Planner/Recommender output
- Authentication and per-user access control, since the application currently scopes data by Codeforces handle without any login system
- Deployment configuration (containerization, CI) — none is currently present in the repository
- Expanding the LangSmith integration beyond optional tracing into a structured observability dashboard

## License

This project does not use any license. 
