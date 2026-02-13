# Epstein Pipeline — Rules of Engagement (rulebook-ai pack)

You are working inside a repository that implements a **provenance-safe document analysis pipeline** for large PDF releases.

## Non-negotiables
- **Accuracy, traceability, and auditability > speed.**
- Never "invent" findings. Every claim must have an evidence trail:
  - `doc_id` (sha256) → source URL → artifact paths → offsets (chunk start/end) → extracted text.
- Prefer **idempotent** operations. If a step is re-run, it must not corrupt existing state.
- Avoid destructive actions by default. If deletion is needed, require an explicit flag and log it.

## Repository conventions
- Run everything through `make` when possible.
- Favor cross-platform execution:
  - If a step depends on system packages, prefer `docker compose` or provide OS-specific install notes.
- Any new scripts must:
  - include robust logging,
  - validate inputs,
  - fail loudly on critical errors, but continue when safe.

## How you should work
- When changing pipeline logic, update:
  - the matching doc in `memory/` (architecture + invariants),
  - and any schema migration notes.
- If you introduce a new dependency, add it to:
  - `requirements.txt` or `pyproject.toml` (whichever the repo uses),
  - and the bootstrap instructions.

## Audit trail requirements
- All pipeline steps must produce:
  - a run record (timestamp, version, inputs),
  - and a failures record (error, stack trace, doc_id).
- When writing to Postgres, store:
  - doc-level provenance (hashes, URLs, timestamps),
  - chunk offsets, and deterministic chunk IDs.

## Guardrails for publishable output
- Anything in `safe_exports/` must be review-friendly:
  - no raw PII,
  - references back to the underlying evidence.

## Linting, Formatting & Syntax Rules 🔧
- All committed Python code must pass project linters and formatters before merging.
  - Use `uv` to install dev tooling and `uv lock` to keep `uv.lock` committed and reproducible.
  - Run formatting and linting locally via `uv run pre-commit run --all-files` or rely on CI to enforce checks.
- Formatting:
  - Use `black` with a line length of **100** chars.
  - Use `isort --profile black` for imports ordering.
  - Let `ruff` perform auto-fixes where appropriate (`ruff --fix`).
- Type checking:
  - Use `mypy` for static typing checks. Keep `mypy` settings aligned in `pyproject.toml`.
- CI & pre-commit:
  - Add `.pre-commit-config.yaml` to the repository root to run `ruff`, `black`, `isort`, `mypy`, and basic hygiene hooks.
  - CI must fail the build if linting/type checks fail.
- Tests:
  - Add `pytest` tests for new functionality and ensure deterministic behavior where possible.

## Commands you will use frequently
- `make vectordb-up` / `make vectordb-down`
- `make pipeline-run`
- `make db-load`
- `make embed`
- `make search Q="..."` (semantic search)

## MCP Server Usage Rules (Added 2024-12-31)

### Server Management
- Always start MCP server before running AI agents that depend on it
- Verify server health with `GET /health` before bulk operations
- Monitor server logs for errors and warnings
- Gracefully shutdown server to complete in-progress downloads

### Download Operations
- **Rate Limiting**: Respect source rate limits (default: max 5 concurrent downloads)
- **Retry Logic**: Use exponential backoff for failed downloads (default: 3 attempts)
- **Verification**: Always verify checksums after download
- **Resumability**: Use resume flags to continue interrupted downloads
- **Logging**: All downloads must be logged with source URL and timestamp

### Error Handling
- Never silently fail - log all errors with context
- Implement retry logic for transient failures
- Provide clear error messages with actionable information
- Track failed downloads for manual review

### Manifest Files
- Generate manifest files for all download operations
- Include: URL, timestamp, SHA-256, file size, metadata
- Store manifests in `manifests/` directory
- Use JSONL format for easy parsing and resumability

## AI Agent Development Rules (Added 2024-12-31)

### General Principles
- **Single Responsibility**: Each agent should have one clear purpose
- **Type Safety**: Use Pydantic models for all inputs and outputs
- **Error Isolation**: Agent failures should not cascade
- **Observability**: All operations must be logged and traceable

### PydanticAI Integration
- Use PydanticAI framework for all new AI agents
- Define structured tools with clear type signatures
- Implement validation for all tool inputs
- Provide comprehensive tool descriptions for LLMs

### MCP Protocol Compliance
- All agents must support standard MCP endpoints
- Implement health checks: `GET /health`
- Provide status reporting: `GET /status`
- Support graceful shutdown signals

### Documentation Requirements
- Document all agent capabilities in `knowledge_base/agents.md` (append-only)
- Include usage examples with real code
- Document error scenarios and handling
- Maintain version history and changelog

### Testing Standards
- Unit tests for all agent tools
- Integration tests with MCP server
- End-to-end workflow tests
- Error scenario coverage

## Document Processing Rules (Added 2024-12-31)

### Download Phase
- Verify source URLs before initiating downloads
- Check available disk space before bulk operations
- Use atomic writes to prevent partial files
- Generate checksums immediately after download

### Extraction Phase
- Apply ZIP slip protections for all archives
- Validate archive integrity before extraction
- Preserve original files (never modify source)
- Track extracted files in manifest

### Pipeline Phase
- Maintain chunk offsets for traceability
- Store document provenance (source URL, timestamp, hash)
- Never modify original text during extraction
- Keep all metadata in structured format

### Security Rules
- Never execute downloaded content
- Validate all file paths to prevent directory traversal
- Use secure temporary directories for extraction
- Clean up temporary files after processing

## Rulebook-AI Integration (Added 2024-12-31)

### Using Rulebook-AI Packs
- Load rules from `rulebook_packs/epstein-pipeline-pack/rules/RULES.md`
- Apply pack-specific validation rules
- Document pack dependencies in project docs
- Keep packs in sync with project standards

### Creating Custom Packs
- Follow rulebook-ai pack structure
- Include comprehensive RULES.md in pack
- Provide usage examples in USAGE.md
- Document tools in tools/README.md
- Maintain project context in memory/PROJECT_CONTEXT.md

### Pack Validation
- Run `python scripts/validate_rulebook_packs.py` before commits
- Ensure YAML syntax is valid
- Verify all referenced files exist
- Check for required sections in RULES.md

## Documentation Standards (Added 2024-12-31)

### Append-Only Files
The following files are APPEND-ONLY and must never have content removed:
- `knowledge_base/agents.md`
- `docs/RULES.md`
- Any file marked as "append-only" in its header

### Updating Append-Only Files
- Always add new content at the end
- Include date and context for additions
- Never modify or remove existing content
- Use clear section headers for new content

### Knowledge Base Maintenance
- Update `knowledge_base/` when adding new features
- Keep documentation in sync with code
- Include practical examples in all docs
- Cross-reference related documentation

### Changelog Requirements
- Document all significant changes
- Include version numbers and dates
- Describe impact on existing functionality
- Link to relevant issues/PRs

## CI/CD Rules (Added 2024-12-31)

### GitHub Actions Requirements
- All workflows must use pinned action versions (e.g., `@v4`)
- Include timeout limits on all jobs (max 30 min)
- Use matrix builds for multi-version testing
- Cache dependencies where possible

### Pre-commit Hooks
- Run `pre-commit run --all-files` before pushing
- Fix all linting errors before commit
- Ensure tests pass locally before pushing
- Verify docs build successfully

### Testing in CI
- Run doctor checks: `make doctor-check`
- Validate rulebook packs
- Verify bundle integrity
- Run full test suite

### Artifact Management
- Upload build artifacts for debugging
- Store test results and coverage reports
- Keep artifacts for 30 days minimum

## Large Release Download Rules (Added 2026-01-07)

- Use pagination (`offset` + `limit`) for releases exceeding 1M documents.
- Keep `page_size` aligned with source limits (default 100).
- Respect `max_requests_per_minute` and `polite_delay_seconds`.
- Prefer batch archives (ZIP) for transport/storage; record archive names in manifests.
- Include logs for failed builds

## Security Standards (Added 2024-12-31)

### Data Handling
- All downloaded documents are public records
- No PII redaction required (public domain)
- Maintain complete audit trail
- Store checksums for verification

### Secrets Management
- Never commit secrets to repository
- Use environment variables for sensitive data
- Keep `.env` files in `.gitignore`
- Use GitHub Secrets for CI/CD

### Dependency Security
- Pin all dependency versions
- Run security scans regularly
- Update dependencies for security patches
- Document known vulnerabilities

### Access Control
- Use least privilege for all operations
- Implement proper authentication
- Log all access attempts
- Review access logs regularly

## GitHub Marketplace Integration (Added 2024-12-31)

### Recommended Tools
- **Sentry**: Error tracking and performance monitoring
- **CodeRabbit**: AI-powered code review
- **Sourcery**: Python code quality and refactoring
- **Agent Toolkit**: GitHub Copilot agent development
- **OpenHands**: Multi-agent orchestration
- **Jules**: Autonomous coding assistant

### Integration Guidelines
- Configure tools via `.github/` workflows
- Document tool usage in project docs
- Review tool recommendations in PRs
- Maintain tool configurations in version control

### Quality Gates
- CodeRabbit review required for complex changes
- Sourcery suggestions reviewed for Python code
- Security scans pass before merge
- All tests pass in CI

---

**Note**: This RULES.md file is append-only. All additions are dated and clearly marked. Last updated: 2024-12-31

---

## Large Release Download Rules (Added 2026-01-07)

- Use pagination (`offset` + `limit`) for releases exceeding 1M documents.
- Keep `page_size` aligned with source limits (default 100).
- Respect `max_requests_per_minute` and `polite_delay_seconds`.
- Prefer batch archives (ZIP) for transport/storage; record archive names in manifests.
