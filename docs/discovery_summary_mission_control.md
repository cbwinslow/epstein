# Discovery: Mission Control TUI — Summary

## What I checked
- `docs/TASKS.md` — master task checklist (Ingestion, Database, Storage, OCR & Parsing, Ops)
- `epstein_pipeline_master_task_methodology_checklist.md` — detailed phasing and acceptance tests (Phases 0-10)
- `epstein_master_tasks_microgoals_git_hub_issues_automation.md` — master tasks generation workflow (`tasks/master_tasks.yml` -> `scripts/gen_issues_from_tasks.py`)
- `docs/TOOLS_AND_MCP_SERVERS.md` — lists system & Python deps and services (Qdrant, Postgres), doctor checks
- `docs/OBSERVABILITY.md` and `docs/ARCHITECTURE.md` — architecture, existing observability notes (minimal) and required instrumentation points
- `agents/` — multiple agent implementations (orchestrator, pipeline_monitor, epstein_data_processor, vector_db_analyzer, db_troubleshooter, document_analysis_agent, entity_extraction_agent)
- rulebook-ai memory/tasks area — contains task plans and agent rules (possible overlap in automation/agent workflows)

## Key findings
- There is already a strong task structure and an issue-generation workflow; `tasks/master_tasks.yml` is referenced by tooling (`write_docs.sh`) but may not yet include Mission Control tasks.
- Agents and an orchestrator are present (`agents/multi_agent_orchestrator.py`) which Mission Control should interface with; this avoids duplicating agent logic — the TUI should orchestrate, not reimplement.
- Observability is currently light: `docs/OBSERVABILITY.md` suggests structured logging and simple metrics; this is an opportunity to integrate OpenTelemetry for traces and metrics.
- There is existing CI / doctor patterns for adding new service checks (`scripts/doctor.py` and `docs/TOOLS_AND_MCP_SERVERS.md`).
- Rulebook / memory files reference external agent platforms (Cursor / CLINE etc.); we must avoid duplicating work those rulebooks or agents already automate.

## Risk / duplication check
- Avoid duplicating functionality in agents (e.g., `pipeline_monitor`, `epstein_data_processor`). Mission Control should call, visualize, and orchestrate existing agents rather than duplicate their logic.
- Check `tasks/master_tasks.yml` and `scripts/gen_issues_from_tasks.py` before creating new issues; add Mission Control tasks to that file to leverage existing issue automation.

## Quick recommendations (next steps)
1. Add 'Mission Control' tasks to `tasks/master_tasks.yml` and generate issues via `scripts/gen_issues_from_tasks.py`.
2. Build small, incremental PoC: a Textual-based TUI with panes (tasks, agents, logs, CLI) that uses the `MultiAgentOrchestrator` API.
3. Add OpenTelemetry instrumentation to agents and the TUI; add a `scripts/doctor.py` check for OTLP endpoint optionally.
4. Add an `integrations/lang/` package with adapters for LangChain, LangSmith, LangGraph, LangFuse, and Langroid (research exact PyPI names and license).
5. Document the design decisions in `docs/MISSION_CONTROL.md` and record an ADR in `docs/DECISIONS.md`.

---

## Files created by this discovery
- `docs/discovery_summary_mission_control.md` (this file)
- `docs/MISSION_CONTROL.md` (skeleton, see next file)


*Next action: write an initial design doc with concrete features, a UI layout, and a minimal implementation plan.*
