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

## Getting Started

See `docs/` for detailed documentation.

- Tools & services: `docs/TOOLS_AND_MCP_SERVERS.md` documents required system packages, Python deps, and local service endpoints (Qdrant/Postgres).
- Canonical bundle snapshots: `docs/files/epstein_files_project_bundle_docker_first_foundation/` contains file snapshots (Makefile, compose.yml, Dockerfile, etc.).
- Quick run order: `bootstrap` → `vectordb-up` → `pipeline-init` → `pipeline-run` → `db-load`
