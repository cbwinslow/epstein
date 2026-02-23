# RECOMMENDATIONS (2026-02-02 02:58:22)

## Repository Structure & Branching
- Create a long-lived `master` branch (default) and protect it with required PR reviews and status checks.
- Keep feature work on short-lived branches (e.g., `feature/<topic>`), merging via pull requests.
- Add a `release` or `stable` branch only if you need parallel maintenance for deployments.

## Tags & Releases
- Adopt semantic version tags (e.g., `v1.2.3`) and create annotated tags for releases.
- Maintain a changelog (e.g., `CHANGES.md`) with release notes that correspond to tags.

## Commit Hygiene
- Use conventional commits (e.g., `feat:`, `fix:`, `docs:`) to improve readability and enable automated changelogs.
- Avoid rewriting shared history unless strictly necessary.

## GitHub/PR Workflow
- Ensure PR templates exist to standardize reviews.
- Enable branch protection rules, including required checks/tests, on `master`.
- Use GitHub Actions (if desired) to run tests and linting on PRs.

## Project Governance
- Add/maintain `RULES.md` or `CONTRIBUTING.md` to document workflow, coding standards, and review policies.
- Keep `AGENTS.md` up to date for agent and automation guidance if needed.
