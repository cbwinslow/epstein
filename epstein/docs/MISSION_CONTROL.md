# Mission Control — TUI / CLI Design (initial)

## Vision
A command-line / TUI "Mission Control" for Epstein that provides a central operational console to:
- View and manage master tasks and agent-driven tasks
- Launch pipeline runs and monitor progress
- Inspect agent status, logs, and traces
- Execute reproducible sample workflows (RAG queries, orchestration runs)
- Integrate language/agent libraries (LangChain, LangSmith, LangFuse, LangGraph, Langroid) as optional backends
- Provide telemetry (traces, metrics) via OpenTelemetry for observability

## Core requirements
- Lightweight CLI entrypoint: `mission-control` (executable script in `bin/`)
- TUI with split panes: Tasks | Agents | Logs | Command/Action
- Responsive: non-blocking calls to agents via `MultiAgentOrchestrator` (async)
- Pluggable adapters for Lang backends under `integrations/lang/`
- Config-driven (env vars + `config/` entries). Add OTEL config to `.env.example`.
- Tests for UI components and instrumentation

## Suggested tech stack
- TUI: Textual (preferred) or Rich+prompt_toolkit
- Telemetry: `opentelemetry-sdk`, `opentelemetry-instrumentation-logging` (basic), OTLP exporter (optional)
- Lang adapters: optional packages installed via `uv` when needed
- Async orchestration: leverage existing `MultiAgentOrchestrator` (async APIs)

## UI Layout (Panes)
- Left: Task list (master tasks & runtime tasks) — selectable, shows status, start/stop actions
- Top-right: Agent status / health (list of agents, status badges, last-run timestamps)
- Middle-right: Logs stream / trace links (searchable)
- Bottom: Command input / quick actions (run pipeline, run analysis, open file, export findings)

## Integration points
- Agents: use existing agent APIs (e.g., `MultiAgentOrchestrator.run_troubleshooting_workflow`) to run jobs
- Telemetry: instrument task creation/finish, agent calls, and important UI commands
- Lang libs: adapter interface like `LangAdapter.run(prompt, context)` returning structured output and logs

## Concrete first milestones
1. Discovery + mapping (done via docs/discovery_summary_mission_control.md)
2. Create design ADR and config schema (`docs/DECISIONS.md`, add `.env.example` entries for OTEL)
3. Minimal Textual PoC with panes and a stubbed tasks list
4. Add calls to `MultiAgentOrchestrator` to list agent status and run a sample job
5. Add OTEL instrumentation (console exporter) and a doctor check
6. Implement 1 Lang adapter (LangChain) as proof-of-concept and add example RAG query

## Safety & methodology notes
- TUI should not execute destructive operations without explicit confirmation
- Follow the project's methodology checklist and preflight rules (Phase 0 from `epstein_pipeline_master_task_methodology_checklist.md`)
- Add tests that assert no destructive behavior by default

---

*Next step: implement milestone (3) — Textual PoC (prototype-tui) and wire to `MultiAgentOrchestrator`'s status endpoint.*
