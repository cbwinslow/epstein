# Project Markdown Starter Pack (uv + Python 3.10)

This canvas contains ready-to-copy Markdown files for a fresh repo.

**Recommended repo layout**
```
.
├─ README.md
├─ USAGE.md
├─ AGENTS.md
├─ RULES.md
├─ RESEARCH_LOG.md
├─ PUBLISHING.md
└─ (code)
   ├─ epstein_files_pipeline.py
   └─ cbw_vector_db_bootstrap.sh
```

---

## README.md

```md
# Document Analysis Pipeline (OCR → Chunk → NER → Vector Search)

This repository bootstraps an end-to-end workflow to analyze a public document dump:

1) **Acquire** PDFs from official seed pages (allowlist)
2) **Download** + hash + manifest
3) **OCR** scanned PDFs (OCRmyPDF)
4) **Extract text** + basic redaction
5) **Chunk with overlap**
6) **NER** + structured outputs (JSONL)
7) **Vector DB** (Qdrant) + optional Postgres/pgvector for structured queries

> Goal: produce *auditable*, *repeatable* analysis outputs with provenance.

## Requirements
- Ubuntu (recommended)
- Python **3.10**
- [`uv`](https://github.com/astral-sh/uv) as Python package manager
- Docker + Compose (for Qdrant/Postgres stack)

## Quickstart (Ubuntu)

### 1) System packages
```bash
sudo apt-get update
sudo apt-get install -y \
  ocrmypdf tesseract-ocr ghostscript qpdf poppler-utils \
  wget curl
```

### 2) Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# restart shell (or: source ~/.bashrc)
uv --version
```

### 3) Create Python 3.10 environment
```bash
# If uv manages Python on your system, this will install 3.10 if missing
uv python install 3.10

# Create venv pinned to Python 3.10
uv venv --python 3.10

# Activate
source .venv/bin/activate
python --version
```

### 4) Initialize project dependencies + lock
```bash
# If you do not already have a pyproject.toml
uv init --python 3.10

# Add dependencies (edit as needed)
uv add requests beautifulsoup4 lxml tqdm pydantic pdfminer.six spacy

# Download spaCy model
uv run python -m spacy download en_core_web_sm

# Lock dependencies
uv lock
```

> `uv lock` produces `uv.lock` (commit this).

### 5) Run the PDF pipeline
```bash
uv run python epstein_files_pipeline.py --init-config ./config.json
# Edit config.json seed_urls to point at the official release pages you want
uv run python epstein_files_pipeline.py --config ./config.json run
```

Outputs land in `./epstein_artifacts/`.

### 6) Start vector stack (Qdrant + optional Postgres)
```bash
chmod +x cbw_vector_db_bootstrap.sh
./cbw_vector_db_bootstrap.sh --dir ./vector-stack up
```

## Data outputs
- `epstein_artifacts/downloads/` original PDFs
- `epstein_artifacts/ocr/` OCR’d PDFs
- `epstein_artifacts/text/` extracted text
- `epstein_artifacts/entities/` NER JSONL
- `epstein_artifacts/manifest.jsonl` url + sha256 + bytes

## Notes on responsible publication
- Treat names as **“mentioned”** unless a document explicitly alleges/charges.
- Do **not** republish personal identifiers or victim-identifying info.
- Keep **provenance** (doc_id, URL, page ranges) for every claim.

## License
Choose a license before publishing (MIT/Apache-2.0 are common).
```

---

## USAGE.md

```md
# Usage Guide

This guide assumes:
- Ubuntu
- Python 3.10 via `uv`
- You have copied the scripts into this repo

## 0) One-time setup

### Install system OCR tools
```bash
sudo apt-get update
sudo apt-get install -y ocrmypdf tesseract-ocr ghostscript qpdf poppler-utils
```

### Create a uv-managed Python 3.10 environment
```bash
uv python install 3.10
uv venv --python 3.10
source .venv/bin/activate

uv init --python 3.10
uv add requests beautifulsoup4 lxml tqdm pydantic pdfminer.six spacy
uv run python -m spacy download en_core_web_sm
uv lock
```

## 1) Acquire + OCR + NER

### Create a starter config
```bash
uv run python epstein_files_pipeline.py --init-config ./config.json
```

### Edit config.json
Update:
- `seed_urls`: official pages that contain links to PDFs
- `allow_domains`: keep strict (official sources)
- optional: `chunk_chars`, `chunk_overlap_chars`

### Run pipeline
```bash
uv run python epstein_files_pipeline.py --config ./config.json run
```

### Validate outputs quickly
- Confirm `epstein_artifacts/text/*.txt` exist and are non-empty.
- Spot-check that OCR isn’t upside-down (OCRmyPDF `--rotate-pages` helps).
- Check `manifest.jsonl` for sha256 and source URLs.

## 2) Stand up a vector database

### Qdrant + optional Postgres/pgvector
```bash
chmod +x cbw_vector_db_bootstrap.sh
./cbw_vector_db_bootstrap.sh --dir ./vector-stack up

# Status / health
./cbw_vector_db_bootstrap.sh --dir ./vector-stack status
```

### Endpoints
- Qdrant HTTP: `http://localhost:6333`
- Qdrant gRPC: `localhost:6334`
- Postgres (optional): `postgresql://vector:<password>@localhost:5432/vectordb`

## 3) Recommended analysis workflow

### A) Index hygiene
Before “insights,” ensure:
- OCR is good enough
- you can trace any finding back to **doc_id + page range**

### B) Entity + relationship extraction
- Start with baseline NER (spaCy)
- Add custom patterns for:
  - docket/case IDs
  - tail numbers
  - dates + ranges
  - roles/titles

### C) Retrieval layer (vector + filters)
- Store chunks in Qdrant with payload:
  - doc_id, source_url, chunk_id, page range
- Store structured entities/edges in Postgres

## 4) Outputs you can publish
Recommended publish artifacts:
- A brief summary post
- A methods section describing reproducibility
- A “sources” appendix listing official seed URLs
- A small set of *non-sensitive* charts/tables:
  - most frequent orgs (by mention count)
  - timeline histogram of mentioned dates

## 5) Troubleshooting

### OCRmyPDF missing
```bash
sudo apt-get install -y ocrmypdf
```

### spaCy model missing
```bash
uv run python -m spacy download en_core_web_sm
```

### Docker compose missing
Install Docker Engine + Compose plugin using Docker’s official docs.
```

---

## AGENTS.md

```md
# AI Agents Playbook

This repo is designed to support “agentic” workflows where an AI helper (or multiple) can:
- run the pipeline
- summarize results
- identify high-signal entities and relationships
- generate publishable outputs with citations and provenance

## Agent roles (recommended)

### 1) Collector Agent
**Goal:** Keep acquisition reproducible.
- Maintains `config.json` seed URLs
- Runs acquisition pipeline
- Verifies `manifest.jsonl` integrity

**Commands**
```bash
uv run python epstein_files_pipeline.py --config ./config.json run
```

### 2) OCR / Text QA Agent
**Goal:** Validate extraction quality.
- Spot-checks random docs
- Flags OCR failures
- Suggests OCRmyPDF options for improvements

### 3) Entity Miner Agent
**Goal:** Extract and rank entities.
- Reviews `entities/*.jsonl`
- Produces top-N lists
- Proposes custom entity patterns

### 4) Relationship Builder Agent
**Goal:** Build edges between entities.
- Co-occurrence graph in chunk windows
- Extracts evidence snippets
- Produces ranked “interesting clusters”

### 5) Writer/Publisher Agent
**Goal:** Produce a publishable post.
- Summarizes methods
- Includes “what we did / what we didn’t do”
- Adds citations to official source URLs
- Outputs markdown suitable for Astro

## Guardrails for agents
- Never state or imply guilt. Only report “mentioned” relationships.
- Do not publish victim-identifying data.
- Every claim must include provenance: doc_id + URL + page range or chunk reference.
- Prefer quoting **small snippets** only when necessary and compliant.

## Suggested agent prompts

### Entity Miner prompt
> Read `epstein_artifacts/entities/*.jsonl` and produce top-50 PERSON, ORG, GPE entities. For each, include: count, example evidence snippet (<= 240 chars), and doc_id (sha256) + source URL from manifest. Flag any entities that look like private addresses/phones and mark as sensitive.

### Writer prompt
> Generate a blog post in Markdown with: Methods, Limitations, Results overview, and a Sources appendix listing seed URLs. Do not include sensitive identifiers. Every statistic should cite at least one official source URL.
```

---

## RULES.md

```md
# Project Rules

## Reproducibility
- All runs must write or append to `manifest.jsonl`.
- Preserve originals: never edit PDFs in-place.
- Outputs must be derivable from the inputs + config.

## Provenance
- Every extracted insight must trace back to:
  - `doc_id` (sha256), and
  - `source_url`, and
  - page/chunk reference.

## Safety
- Redact personal identifiers before sharing outputs.
- Do not publish victim-identifying information.
- Treat names as “mentioned,” not accused.

## Data hygiene
- Keep allowlist strict (official domains).
- Avoid mirrors unless explicitly verified.

## Git hygiene
- Commit `uv.lock`.
- Keep secrets out of the repo.
- Add `.env` to `.gitignore`.
```

---

## RESEARCH_LOG.md

```md
# Research Log

Use this as a run journal and publication backbone.

## Run: YYYY-MM-DD
- Seed URLs:
  -
- Config hash:
- Notes:

### Acquisition
- PDFs discovered:
- PDFs downloaded:
- Failures:

### OCR/Text QA
- OCR failures:
- Quality notes:

### Entities
- Top PERSON:
- Top ORG:
- Top DATE:

### Relationships / clusters
- Cluster A:
- Cluster B:

### Publication notes
- What is safe to publish:
- What is sensitive and must remain private:
```

---

## PUBLISHING.md

```md
# Publishing Plan (later)

This repo will publish findings to the CloudCurio blog (Astro) as the first post.

## Output format
- Final post should be Markdown with frontmatter suitable for Astro content collections.
- Keep an appendix of official source URLs.
- Include a “methods + limitations” section.

## Suggested publication artifacts
- `post.md` (main writeup)
- `sources.md` (seed URLs + manifest summary)
- `figures/` (charts generated from non-sensitive aggregates)

## Do not publish
- personal identifiers (emails, phones, addresses, SSNs)
- victim-identifying details
- allegations without clear document evidence + provenance
```

