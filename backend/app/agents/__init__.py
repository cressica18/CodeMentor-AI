"""
Phase 4 — agentic workflow package.

Contains the LangGraph state definition (`state.py`), the Analyzer and
Planner agent node implementations (`analyzer.py`, `planner.py`), and
the compiled LangGraph workflow (`graph.py`):

    START -> RetrieveMemory -> AnalyzerAgent -> PlannerAgent -> PersistMemory -> END

Orchestration (invoking the graph + persisting AgentRun/AgentTrace rows)
lives in app/services/agent_service.py, kept separate so this package
stays pure agent/graph logic.
"""
