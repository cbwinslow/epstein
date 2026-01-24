# Documentation Index

## Overview

This is the master index for all Epstein project documentation. Documents are organized by category for easy navigation.

## Quick Start

- [README](../README.md) - Project overview and getting started
- [Quick Start OCR Workflow](QUICK_START_OCR_WORKFLOW.md) - Fast track to running OCR workflow
- [User Instructions Manual](../USER_INSTRUCTIONS_MANUAL.md) - Comprehensive user guide

## Architecture & Structure

- [Repository Structure](REPOSITORY_STRUCTURE.md) - Directory organization and file layout
- [Agent Capability Matrix](AGENT_CAPABILITY_MATRIX.md) - Complete agent inventory and capabilities
- [Agent Configuration Schema](../schemas/agent_config_schema.json) - JSON schema for agent configuration

## Setup & Installation

- [Tools and MCP Servers](TOOLS_AND_MCP_SERVERS.md) - Required tools and services
- [Cloudflare R2 Setup](CLOUDFLARE_R2_SETUP.md) - Cloud storage configuration
- [Bootstrap Scripts](../scripts/) - Environment setup scripts

## Workflows & Guides

### OCR Processing
- [OCR Workflow Guide](OCR_WORKFLOW_GUIDE.md) - Complete OCR workflow documentation
- [OCR Workflow Storage Options](OCR_WORKFLOW_STORAGE_OPTIONS.md) - Storage and distribution options
- [Quick Start OCR](QUICK_START_OCR_WORKFLOW.md) - Fast track OCR setup

### Mission Control
- [Mission Control](MISSION_CONTROL.md) - Web-based monitoring dashboard
- [Mission Control App](../tools/mission_control/README.md) - Dashboard application guide

## MCP Servers

- [Epstein Comprehensive MCP Server](../mcp_servers/epstein_comprehensive/README.md) - Complete API server
- [Epstein Files Downloader MCP](../mcp_servers/epstein_files_downloader/README.md) - Document download server

## Agent System

### Core Documentation
- [Agents Overview](../agents/README.md) - Agent system introduction
- [Agent Capability Matrix](AGENT_CAPABILITY_MATRIX.md) - Detailed agent capabilities
- [Base Agent Class](../agents/base_agent.py) - Agent base class implementation

### Agent-Specific Documentation
- [Epstein Data Processor](../knowledge_base/agents/core/epstein_data_processor.md)
- [Document Analysis Agent](../knowledge_base/agents/core/document_analysis.md)
- [Vector DB Analyzer](../knowledge_base/agents/database/vector_db_analyzer.md)
- [Multi-Agent Orchestrator](../knowledge_base/agents/orchestration/multi_agent_orchestrator.md)
- [GovInfo Downloader](../knowledge_base/agents/specialized/govinfo_downloader.md)

## Knowledge Base

### Guides
- [AI Agent Workflow Guide](../knowledge_base/ai_agent_workflow_guide.md) - Agent usage patterns
- [Rulebook AI Integration](../knowledge_base/rulebook_ai_integration.md) - Rulebook-AI setup
- [Features](../knowledge_base/features.md) - Project features overview

### Reference
- [System Requirements](../knowledge_base/srs.md) - Software Requirements Specification
- [Requirements](../knowledge_base/requirements.md) - Project requirements
- [Agents Index](../knowledge_base/agents.md) - Agent documentation index
- [Knowledge Base Index](../knowledge_base/index.md) - KB navigation

### Data Sources
- [DOJ Releases 2024](../knowledge_base/doj_releases_2024.md) - Department of Justice releases

## Planning & Tasks

- [Comprehensive Task Plan](planning/COMPREHENSIVE_TASK_PLAN.md)
- [Enhanced Master Tasks](planning/ENHANCED_MASTER_TASKS.md)
- [Master Tasks](planning/MASTER_TASKS.md)
- [Project Enhancement Summary](planning/PROJECT_ENHANCEMENT_SUMMARY.md)
- [Pipeline Master Task Methodology](planning/epstein_pipeline_master_task_methodology_checklist.md)

## Development

### Configuration
- [Agent Configuration](../config/agent_config.json) - Agent settings
- [Environment Example](../epstein/.env.example) - Environment variables
- [Docker Compose](../compose.yml) - Container orchestration

### Scripts
- [Doctor Script](../scripts/doctor.py) - Health check utility
- [Ingestion Pipeline](../scripts/ingestion_pipeline.py) - Data ingestion
- [Collect Task Logs](../scripts/collect_task_logs.py) - Log aggregation
- [Verify Bundles](../scripts/verify_bundle.sh) - Bundle verification

### Testing
- [Test Suite](../tests/) - Unit and integration tests
- [Running Tests](../Makefile) - Make targets for testing

## Reference Files

### Snapshot Bundles
- [Docker First Foundation Bundle](files/epstein_files_project_bundle_docker_first_foundation/) - Reference implementation

### Schemas
- [Agent Config Schema](../schemas/agent_config_schema.json) - Agent configuration
- [Epstein Schema](../schemas/epstein_schema.json) - Data models

## Changelog & Status

- [Changelog](CHANGELOG.md) - Version history and changes
- [Project Status Report](planning/project_status_report.md) - Current status

## External Resources

### GitHub
- [Issues](https://github.com/cbwinslow/epstein/issues) - Bug reports and feature requests
- [Workflows](../.github/workflows/) - CI/CD pipelines
- [Copilot Instructions](../.github/copilot-instructions.md) - AI assistant guidelines

### Tools
- [Mission Control Dashboard](../tools/mission_control/) - Monitoring UI
- [Epstein Tools](../tools/epstein_tools.py) - Core utilities
- [Advanced Analysis Tools](../tools/advanced_analysis_tools.py) - Analysis utilities

## Documentation Standards

### File Naming
- `UPPERCASE.md` - Important top-level documents
- `Sentence_Case.md` - Guides and tutorials
- `lowercase.md` - Reference and technical docs

### Document Structure
All documentation should include:
1. Title and overview
2. Table of contents (for long docs)
3. Prerequisites/requirements
4. Step-by-step instructions
5. Examples
6. Troubleshooting
7. Related documentation links
8. Version and last updated date

### Maintenance
- Review quarterly for accuracy
- Update examples when code changes
- Archive outdated docs to `docs/archive/`
- Update this index when adding new docs

## Contributing to Documentation

1. **Check for duplicates** - Review existing docs before creating new ones
2. **Follow standards** - Use consistent formatting and structure
3. **Add examples** - Include practical examples and code samples
4. **Link appropriately** - Add to this index and link from related docs
5. **Keep updated** - Update docs when features change

## Getting Help

- **Documentation Issues**: File issue with `documentation` label
- **Technical Questions**: Check Knowledge Base first
- **Feature Requests**: File issue with `enhancement` label
- **Bug Reports**: Include steps to reproduce

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0  
**Maintainer**: Epstein Project Team

## Document Status Legend

- ✅ Complete and up-to-date
- 🚧 Under development
- ⚠️ Needs review/update
- 📋 Planned
- 🗄️ Archived
