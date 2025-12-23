# Epstein Pipeline — Tool Starters

This folder exists so rulebook-ai can copy "starter tools" into projects.
In this repo, tool starters are small helper notes and example commands.

## Quickstart
```bash
make vectordb-up
make pipeline-run
make db-load
make embed
make search Q="test query"
```

## When debugging
- Confirm Docker is running
- Confirm Postgres + Qdrant containers are healthy
- Confirm DSN is set (or `make` defaults are correct)
- Confirm the pipeline produced artifacts under `data/`