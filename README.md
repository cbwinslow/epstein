# Epstein Project

This is the Epstein project filesystem, organized as follows:

- `docs/` - All documentation files (.md)
- `scripts/` - Shell scripts and Python scripts
- `epstein/` - Main Epstein pipeline code and configuration
- `projects/` - Subprojects (opendiscourse, rulebook_pack, project bundles)
- `config/` - Configuration files
- `docker/` - Docker-related files
- `duplicates/` - Archived duplicate files
- `.archive/` - Archived zip files
- `.github/` - GitHub configuration
- `.snapshots/` - Snapshot files

## Main Components

- **Epstein Pipeline**: Core PDF analysis pipeline in `epstein/`
- **Subprojects**: Various related projects in `projects/`
- **Documentation**: Comprehensive docs in `docs/`
- **OCR Workflow**: Automated GitHub Actions workflow for document processing

## Getting Started

See `docs/` for detailed documentation.

- Tools & services: `docs/TOOLS_AND_MCP_SERVERS.md` documents required system packages, Python deps, and local service endpoints (Qdrant/Postgres).
- Canonical bundle snapshots: `docs/files/epstein_files_project_bundle_docker_first_foundation/` contains file snapshots (Makefile, compose.yml, Dockerfile, etc.).
- Quick run order: `bootstrap` → `vectordb-up` → `pipeline-init` → `pipeline-run` → `db-load`

## OCR Workflow (New!)

The project now includes an automated GitHub Actions workflow for downloading and OCR-processing Epstein documents:

- **Quick Start**: See [`docs/QUICK_START_OCR_WORKFLOW.md`](docs/QUICK_START_OCR_WORKFLOW.md)
- **Full Guide**: See [`docs/OCR_WORKFLOW_GUIDE.md`](docs/OCR_WORKFLOW_GUIDE.md)
- **Storage Options**: See [`docs/OCR_WORKFLOW_STORAGE_OPTIONS.md`](docs/OCR_WORKFLOW_STORAGE_OPTIONS.md)
- **Cloudflare R2 Setup**: See [`docs/CLOUDFLARE_R2_SETUP.md`](docs/CLOUDFLARE_R2_SETUP.md)

### Running the OCR Workflow

1. Go to **Actions** tab in GitHub
2. Select **OCR Processing Workflow**
3. Click **Run workflow**
4. Configure sources and options
5. Download results from artifacts

The workflow automates:
- ✅ Downloading documents from DOJ, FBI, House Oversight
- ✅ OCR processing with Tesseract
- ✅ Text extraction and manifest generation
- ✅ Optional upload to Cloudflare R2 for public distribution
- ✅ Optional GitHub releases for versioned datasets
