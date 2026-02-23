# Epstein Next Improvements v4

Included in `epstein_full_project_bundle_v4.zip`.

---

## 1) GitHub Release workflow

**File:** `.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: write

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Create source bundle zip
        run: |
          set -euo pipefail
          ZIP_NAME="epstein_full_project_bundle_${GITHUB_REF_NAME}.zip"
          zip -r "$ZIP_NAME" . \
            -x ".git/*" \
            -x "epstein_artifacts/*" \
            -x "vector-stack/*" \
            -x ".epstein/*" \
            -x ".venv/*" \
            -x "__pycache__/*" \
            -x "*.pyc" \
            -x ".rulebook-ai/*"
          echo "ZIP_NAME=$ZIP_NAME" >> $GITHUB_ENV

      - name: Create GitHub Release + upload asset
        uses: softprops/action-gh-release@v2
        with:
          files: ${{ env.ZIP_NAME }}
```

---

## 2) Enhanced environment doctor

**File:** `scripts/doctor.py`

Adds checks for:
- port collisions (5432, 6333, 6334)
- disk free space (MIN_FREE_GB env override)
- docker volumes listing health

(Full file is in the repo zip.)

---

## 3) AI Agent Runbook

**File:** `docs/AI_AGENT_RUNBOOK.md`

Contains:
- required evidence citation template (doc_id + chunk_id + offsets + source_url + excerpt)
- allowed/disallowed outputs rules
- operational playbooks

---

## Docs index updated

**File:** `docs/INDEX.md`
- now includes `docs/AI_AGENT_RUNBOOK.md`

