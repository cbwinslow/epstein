# Epstein Project

A comprehensive data processing pipeline for analyzing PDF documents with OCR, text extraction, Named Entity Recognition (NER), embeddings generation, and vector search capabilities.

## Quick Links

- 📖 [**Documentation Index**](docs/INDEX.md) - Complete documentation catalog
- 🚀 [**Quick Start Guide**](docs/QUICK_START_OCR_WORKFLOW.md) - Get started in minutes
- 🤖 [**Agent Capability Matrix**](docs/AGENT_CAPABILITY_MATRIX.md) - AI agent system overview
- 🔌 [**MCP Server**](mcp_servers/epstein_comprehensive/README.md) - API access to all functionality
- 📂 [**Repository Structure**](docs/REPOSITORY_STRUCTURE.md) - Project organization

## Overview

The Epstein project provides a complete pipeline for processing government documents, with capabilities including:

- **OCR Processing**: Convert scanned PDFs to searchable text
- **Text Extraction**: Extract and clean text from documents
- **Entity Recognition**: Identify people, organizations, locations, dates
- **Vector Embeddings**: Generate semantic embeddings for search
- **Database Storage**: PostgreSQL for structured data, Qdrant for vector search
- **Multi-Agent System**: Specialized AI agents for different tasks
- **MCP Servers**: RESTful APIs for programmatic access

## Main Components

- **[`/agents/`](agents/)** - AI agent implementations (9 specialized agents)
- **[`/epstein/`](epstein/)** - Core pipeline code for document processing
- **[`/mcp_servers/`](mcp_servers/)** - Model Context Protocol servers
- **[`/tools/`](tools/)** - Reusable tools and Mission Control dashboard
- **[`/scripts/`](scripts/)** - Utility scripts for operations
- **[`/docs/`](docs/)** - Comprehensive documentation
- **[`/knowledge_base/`](knowledge_base/)** - Knowledge base for AI agents
- **[`/tests/`](tests/)** - Test suite

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- PostgreSQL 15+
- Qdrant vector database

### Quick Start

```bash
# 1. Health check
python scripts/doctor.py

# 2. Bootstrap environment
make bootstrap

# 3. Start services
make vectordb-up

# 4. Initialize pipeline
make pipeline-init

# 5. Run pipeline
make pipeline-run

# 6. Load results
make db-load
```

For detailed setup instructions, see:
- [Tools and Services](docs/TOOLS_AND_MCP_SERVERS.md)
- [Quick Start OCR Workflow](docs/QUICK_START_OCR_WORKFLOW.md)
- [User Manual](USER_INSTRUCTIONS_MANUAL.md)

## Key Features

### OCR Workflow
Automated GitHub Actions workflow for document processing:
- Download from DOJ, FBI, House Oversight sources
- OCR processing with Tesseract
- Text extraction and manifest generation
- Optional Cloudflare R2 upload
- GitHub releases for datasets

[Quick Start Guide](docs/QUICK_START_OCR_WORKFLOW.md) | [Full Documentation](docs/OCR_WORKFLOW_GUIDE.md)

### AI Agent System
9 specialized agents for different tasks:
- **Epstein Data Processor** - Core document processing
- **Entity Extraction Agent** - NER and relationship extraction
- **Vector DB Analyzer** - Semantic search and analysis
- **Database Troubleshooter** - PostgreSQL optimization
- **Pipeline Monitor** - Health monitoring and alerts
- **Document Analysis Agent** - Content analysis
- **Codex Agent** - Code generation and explanation
- **GovInfo Downloader** - Government document retrieval
- **Multi-Agent Orchestrator** - Task coordination

[Agent Documentation](docs/AGENT_CAPABILITY_MATRIX.md) | [Agent README](agents/README.md)

### MCP Servers
RESTful API servers for programmatic access:
- **Comprehensive MCP Server** - Complete API for all functionality
- **Files Downloader MCP** - Document download management

[API Documentation](mcp_servers/epstein_comprehensive/README.md)

## Architecture

```
┌─────────────────────────────────────────────┐
│         AI Agent System (9 Agents)          │
│  Document Processing | Entity Extraction    │
│  Vector Search | Database | Monitoring      │
└─────────────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Pipeline │  │   MCP    │  │  Tools   │
│  Engine  │  │  Servers │  │  & UI    │
└──────────┘  └──────────┘  └──────────┘
      │              │              │
      └──────────────┼──────────────┘
                     ▼
         ┌──────────────────────┐
         │   Data Storage       │
         │ PostgreSQL | Qdrant  │
         └──────────────────────┘
```

## Development

### Available Commands

```bash
make bootstrap       # Setup environment
make doctor          # Health checks
make lint            # Code quality checks
make test            # Run tests
make format          # Format code
make pipeline-run    # Run pipeline
make db-load         # Load data to database
```

See [Makefile](Makefile) for all commands.

### Project Structure

```
epstein/
├── agents/          # AI agent implementations
├── mcp_servers/     # MCP protocol servers
├── tools/           # Reusable tools
├── epstein/         # Core pipeline code
├── scripts/         # Utility scripts
├── docs/            # Documentation
├── tests/           # Test suite
└── knowledge_base/  # AI agent knowledge
```

See [Repository Structure](docs/REPOSITORY_STRUCTURE.md) for details.

## Documentation

- 📖 [**Documentation Index**](docs/INDEX.md) - Complete catalog
- 🏗️ [Repository Structure](docs/REPOSITORY_STRUCTURE.md) - Organization guide
- 🤖 [Agent Capability Matrix](docs/AGENT_CAPABILITY_MATRIX.md) - Agent overview
- 🔌 [MCP Server API](mcp_servers/epstein_comprehensive/README.md) - API reference
- 📚 [Knowledge Base](knowledge_base/index.md) - Technical knowledge
- 🔧 [User Manual](USER_INSTRUCTIONS_MANUAL.md) - Complete user guide

## Support

- **Issues**: [GitHub Issues](https://github.com/cbwinslow/epstein/issues)
- **Documentation**: [docs/](docs/) directory
- **Examples**: [examples/](examples/) directory

## License

See repository for license information.

---

**Version**: 2.0.0  
**Last Updated**: 2026-01-15  
**Maintainer**: Epstein Project Team
