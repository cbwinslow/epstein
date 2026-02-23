# Repository Structure

## Overview

This document describes the organization of the Epstein Project repository and the purpose of each major directory.

## Directory Structure

```
epstein/
├── .github/                    # GitHub configuration and workflows
│   ├── workflows/             # CI/CD workflows
│   ├── ISSUE_TEMPLATE/        # Issue templates
│   └── copilot-instructions.md
├── agents/                     # AI agent implementations
│   ├── core/                  # Core agents (document processor, etc.)
│   ├── *.py                   # Individual agent implementations
│   ├── README.md              # Agent documentation
│   └── agent_config.json      # Agent configuration
├── config/                     # Configuration files
│   └── agent_config.json      # Agent configuration schema
├── db/                         # Database scripts and migrations
│   └── migrate.py
├── docs/                       # Documentation
│   ├── architecture/          # Architecture diagrams and designs
│   ├── planning/              # Planning documents and task lists
│   ├── files/                 # Snapshot bundles and reference files
│   └── *.md                   # Various documentation files
├── epstein/                    # Main pipeline code
│   ├── utils/                 # Utility modules
│   ├── *.py                   # Pipeline scripts
│   ├── compose.yml            # Docker compose configuration
│   └── pyproject.toml         # Python project configuration
├── examples/                   # Example usage scripts
│   ├── multi_agent_usage_example.py
│   └── pydantic_downloader_agent.py
├── integrations/              # Third-party integrations
├── knowledge_base/            # Knowledge base and documentation
│   ├── agents/                # Agent-specific documentation
│   └── *.md                   # Various knowledge base documents
├── lib/                        # Shared library code
├── logs/                       # Log files (ignored by git)
├── mcp_servers/               # Model Context Protocol servers
│   └── epstein_files_downloader/  # File downloader MCP server
├── projects/                   # Subprojects and bundles
├── rulebook_packs/            # Rulebook-AI integration packs
├── schemas/                    # JSON schemas
├── scripts/                    # Utility scripts
│   ├── archive/               # Archived scripts
│   ├── doctor.py              # Health check script (canonical)
│   └── *.sh, *.py             # Various utility scripts
├── tasks/                      # Task definitions and tracking
├── tests/                      # Test suite
│   ├── test_agents.py
│   ├── test_tools_import.py
│   └── *.py                   # Various test files
├── tools/                      # Tool implementations
│   ├── mission_control/       # Mission control dashboard
│   ├── epstein_tools.py       # Core tools
│   └── advanced_analysis_tools.py
└── vector-stack/              # Vector database stack (Qdrant)
```

## Key Directories

### `/agents/`
Contains all AI agent implementations. Each agent is a specialized component that handles specific tasks:
- **Core agents**: Document processing, entity extraction, analysis
- **Database agents**: Vector DB analyzer, PostgreSQL troubleshooter
- **Orchestration**: Multi-agent coordinator and pipeline monitor
- **Configuration**: `agent_config.json` defines capabilities and settings

### `/epstein/`
Main pipeline code for document processing:
- OCR processing
- Text extraction
- Named Entity Recognition (NER)
- Embeddings generation
- Vector search integration

### `/mcp_servers/`
Model Context Protocol (MCP) servers that expose functionality as APIs:
- File downloader server for government documents
- (Future) Pipeline orchestration server
- (Future) Vector search server

### `/tools/`
Reusable tools and utilities:
- `epstein_tools.py`: Core pipeline tools
- `advanced_analysis_tools.py`: Advanced analysis capabilities
- `mission_control/`: Web-based monitoring dashboard

### `/scripts/`
Utility scripts for maintenance and operations:
- `doctor.py`: Health check and validation (canonical version)
- `collect_task_logs.py`: Task log aggregation
- Bootstrap scripts for various environments

### `/docs/`
Comprehensive documentation:
- **planning/**: Task plans and project tracking
- **architecture/**: System design documents
- **files/**: Reference snapshots and bundles
- Guides for OCR workflow, setup, and usage

### `/knowledge_base/`
Knowledge base for AI agents and developers:
- Agent documentation and workflows
- System requirements and specifications
- Integration guides

### `/tests/`
Test suite covering:
- Unit tests for agents and tools
- Integration tests
- Database tests
- OpenTelemetry tests

## File Organization Principles

1. **Separation of Concerns**: Code, configuration, documentation, and tests in separate directories
2. **Agent-Centric**: Agents are first-class components with dedicated directory
3. **MCP-First**: MCP servers provide API access to all major functionality
4. **Documentation-Driven**: Comprehensive docs for all components
5. **Test Coverage**: Tests mirror the source structure

## Naming Conventions

- **Python files**: `snake_case.py`
- **Directories**: `lowercase` or `snake_case`
- **Documentation**: `UPPERCASE.md` for important docs, `Sentence_Case.md` for guides
- **Configuration**: `*.json` for configs, `*.toml` for Python packaging

## Build Artifacts (Ignored by Git)

- `__pycache__/`: Python bytecode
- `epstein_artifacts/`: Pipeline output
- `logs/`: Log files
- `*.pyc`, `*.pyo`: Compiled Python
- `.mypy_cache/`, `.pytest_cache/`: Tool caches
- Vector database storage

## Getting Started

1. See [README.md](../README.md) for project overview
2. See [docs/QUICK_START_OCR_WORKFLOW.md](QUICK_START_OCR_WORKFLOW.md) for OCR workflow
3. See [knowledge_base/ai_agent_workflow_guide.md](../knowledge_base/ai_agent_workflow_guide.md) for agent usage
4. See [mcp_servers/epstein_files_downloader/README.md](../mcp_servers/epstein_files_downloader/README.md) for MCP server

## Maintenance

- Run `python scripts/doctor.py` to check system health
- Run `make lint` to check code quality
- Run `make test` to run test suite
- See [Makefile](../Makefile) for all available commands

---

**Last Updated**: 2026-01-15
**Maintainer**: Epstein Project Team
