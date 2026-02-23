# Epstein Master Tasks — Microgoals + Tests + Issue Automation

This canvas is the **operational extension** of the master checklist.

## What I shipped (v5)

### 1) Structured task registry
- **File:** `tasks/master_tasks.yml`
- Contains milestones and microtasks with explicit acceptance tests.

### 2) Issue generator
- **File:** `scripts/gen_issues_from_tasks.py`
- Generates:
  - `issues.json` (for issue creation)
  - `MASTER_TASKS.md` (human checklist)

### 3) GitHub Actions: bootstrap issues
- **File:** `.github/workflows/bootstrap_issues.yml`
- Run manually via **Actions → Bootstrap Issues**
  - `dry_run=true` (default) prints issue titles
  - set `dry_run=false` to actually create issues

### 4) Repo hygiene templates
- `.github/ISSUE_TEMPLATE/00_bug_report.yml`
- `.github/ISSUE_TEMPLATE/01_task.yml`
- `.github/ISSUE_TEMPLATE/02_analysis_finding.yml`
- `.github/pull_request_template.md`

### 5) Methodology + troubleshooting + analysis playbook (if missing)
- `docs/METHODOLOGY.md`
- `docs/TROUBLESHOOTING.md`
- `docs/ANALYSIS_PLAYBOOK.md`

---

## How to use it

### Export tasks locally
```bash
make issues-export
```
Outputs:
- `./issues.json`
- `./MASTER_TASKS.md`

### Create GitHub issues from tasks
1. Push repo to GitHub
2. Go to **Actions → Bootstrap Issues**
3. Run with `dry_run=true` first
4. Re-run with `dry_run=false` to create issues

---

## Analysis discipline reminder

If you create a finding (issue labeled `finding`), include:
- doc_id
- chunk_id
- offsets
- source_url
- excerpt
- confidence

No exceptions.

