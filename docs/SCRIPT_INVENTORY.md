# Epstein Files Project - Script Inventory

## Overview
This document provides a comprehensive inventory of all scripts in the Epstein Files project, explaining their purpose, functionality, and usage.

## Table of Contents
- [System Health and Setup Scripts](#system-health-and-setup-scripts)
- [Data Ingestion and Download Scripts](#data-ingestion-and-download-scripts)
- [Database Management Scripts](#database-management-scripts)
- [Document Processing Scripts](#document-processing-scripts)
- [Agent Scripts](#agent-scripts)
- [Utility Scripts](#utility-scripts)

## System Health and Setup Scripts

### [`scripts/doctor.py`](scripts/doctor.py)
**Purpose**: System health check and dependency verification
**Functionality**:
- Checks Docker availability and version
- Verifies Docker Compose plugin
- Tests Qdrant vector database connectivity
- Provides status reports with warnings/errors
**Usage**: `python scripts/doctor.py`

### [`scripts/cbw_bootstrap_project_ubuntu.sh`](scripts/cbw_bootstrap_project_ubuntu.sh)
**Purpose**: Project environment setup for Ubuntu systems
**Functionality**:
- Installs system dependencies
- Sets up Python virtual environment
- Configures project structure
- Installs required Python packages
**Usage**: `bash scripts/cbw_bootstrap_project_ubuntu.sh`

## Data Ingestion and Download Scripts

### [`agents/govinfo_downloader.py`](agents/govinfo_downloader.py)
**Purpose**: Enhanced bulk downloader for govinfo.gov documents
**Functionality**:
- Discovers available document collections from govinfo.gov
- Supports pagination for large datasets
- Implements retry logic with configurable delays
- Batch processing with progress tracking
- Comprehensive download reporting
- Collection filtering and selective downloading
**Key Features**:
- Configurable batch sizes and retry attempts
- Progress bars using tqdm
- JSON report generation
- Document metadata preservation
- Collection-based organization
**Usage**:
```bash
# Download all collections
python agents/govinfo_downloader.py -o ./downloads

# Download specific collections
python agents/govinfo_downloader.py -c "collection1,collection2" -o ./downloads

# Report only (no download)
python agents/govinfo_downloader.py --report-only
```

### [`epstein/epstein_files_download_ocr_ner_pipeline_python_optional_ts.py`](epstein/epstein_files_download_ocr_ner_pipeline_python_optional_ts.py)
**Purpose**: Complete pipeline for downloading, OCR, and NER processing
**Functionality**:
- End-to-end document processing workflow
- Download from multiple sources
- OCR processing for scanned documents
- Named Entity Recognition (NER)
- Optional TypeScript integration
**Usage**: `python epstein/epstein_files_download_ocr_ner_pipeline_python_optional_ts.py`

### [`epstein/epstein_files_pipeline.py`](epstein/epstein_files_pipeline.py)
**Purpose**: Core document processing pipeline
**Functionality**:
- Document ingestion and preprocessing
- Text extraction and normalization
- Metadata extraction
- Database integration
**Usage**: `python epstein/epstein_files_pipeline.py`

## Database Management Scripts

### [`db/migrate.py`](db/migrate.py)
**Purpose**: Database migration management
**Functionality**:
- Applies database schema migrations
- Tracks migration history
- Supports rollback functionality
- Schema version management
**Usage**: `python db/migrate.py`

### [`db/schema.sql`](db/schema.sql)
**Purpose**: Canonical database schema definition
**Functionality**:
- Defines all database tables and relationships
- Creates indexes for performance optimization
- Sets up triggers for automatic timestamp updates
- Includes views for common queries
- Comprehensive commenting and documentation
**Key Tables**:
- `sources`: Document source tracking
- `ingestion_runs`: Processing run metadata
- `documents`: Core document metadata
- `extracted_text`: OCR and text extraction results
- `entities`: Named entities from NER
- `relationships`: Entity relationships

## Document Processing Scripts

### [`epstein/qdrant_embed_chunks.py`](epstein/qdrant_embed_chunks.py)
**Purpose**: Document chunking and embedding for Qdrant vector database
**Functionality**:
- Splits documents into chunks
- Generates embeddings using ML models
- Stores embeddings in Qdrant
- Supports semantic search
**Usage**: `python epstein/qdrant_embed_chunks.py`

### [`epstein/qdrant_semantic_search.py`](epstein/qdrant_semantic_search.py)
**Purpose**: Semantic search functionality using Qdrant
**Functionality**:
- Vector similarity search
- Hybrid search (vector + keyword)
- Result ranking and filtering
- Query expansion
**Usage**: `python epstein/qdrant_semantic_search.py`

## Agent Scripts

### [`agents/epstein_data_processor.py`](agents/epstein_data_processor.py)
**Purpose**: Core data processing agent
**Functionality**:
- Document analysis and classification
- Metadata extraction
- Content processing workflows
- Integration with other agents
**Usage**: `python agents/epstein_data_processor.py`

### [`agents/document_analysis_agent.py`](agents/document_analysis_agent.py)
**Purpose**: Document analysis and feature extraction
**Functionality**:
- Text analysis and summarization
- Feature extraction
- Content classification
- Quality assessment
**Usage**: `python agents/document_analysis_agent.py`

### [`agents/entity_extraction_agent.py`](agents/entity_extraction_agent.py)
**Purpose**: Named Entity Recognition and extraction
**Functionality**:
- Entity detection and classification
- Relationship extraction
- Entity resolution
- Knowledge graph construction
**Usage**: `python agents/entity_extraction_agent.py`

### [`agents/vector_db_analyzer.py`](agents/vector_db_analyzer.py)
**Purpose**: Vector database analysis and optimization
**Functionality**:
- Collection analysis
- Performance optimization
- Query analysis
- Index management
**Usage**: `python agents/vector_db_analyzer.py`

### [`agents/db_troubleshooter.py`](agents/db_troubleshooter.py)
**Purpose**: Database troubleshooting and repair
**Functionality**:
- Connection testing
- Query analysis
- Performance diagnostics
- Data integrity checks
**Usage**: `python agents/db_troubleshooter.py`

### [`agents/pipeline_monitor.py`](agents/pipeline_monitor.py)
**Purpose**: Pipeline monitoring and alerting
**Functionality**:
- Real-time pipeline monitoring
- Performance metrics collection
- Alert generation
- Status reporting
**Usage**: `python agents/pipeline_monitor.py`

### [`agents/multi_agent_orchestrator.py`](agents/multi_agent_orchestrator.py)
**Purpose**: Multi-agent coordination and orchestration
**Functionality**:
- Agent task distribution
- Workflow management
- Inter-agent communication
- Resource allocation
**Usage**: `python agents/multi_agent_orchestrator.py`

## Utility Scripts

### [`extract_md_files.py`](extract_md_files.py)
**Purpose**: Markdown file extraction and processing
**Functionality**:
- Extracts markdown files from various sources
- Processes markdown content
- Converts to other formats
**Usage**: `python extract_md_files.py`

### [`write_docs.sh`](write_docs.sh)
**Purpose**: Documentation generation script
**Functionality**:
- Automated documentation generation
- Markdown processing
- Template rendering
**Usage**: `bash write_docs.sh`

## Qdrant Vector Database Scripts

### [`epstein/qdrant_embed_chunks_1.py`](epstein/qdrant_embed_chunks_1.py)
**Purpose**: Alternative chunk embedding implementation
**Functionality**:
- Different chunking strategy
- Alternative embedding models
- Experimental features
**Usage**: `python epstein/qdrant_embed_chunks_1.py`

### [`epstein/qdrant_embed_chunks2.py`](epstein/qdrant_embed_chunks2.py)
**Purpose**: Another alternative chunk embedding implementation
**Functionality**:
- Additional experimental features
- Different optimization approaches
**Usage**: `python epstein/qdrant_embed_chunks2.py`

## Script Categories Summary

### Ingestion Scripts
- `agents/govinfo_downloader.py` - Primary document downloader
- `epstein/epstein_files_download_ocr_ner_pipeline_python_optional_ts.py` - Complete pipeline
- `epstein/epstein_files_pipeline.py` - Core processing pipeline

### Database Scripts
- `db/migrate.py` - Migration management
- `db/schema.sql` - Schema definition

### Vector Database Scripts
- `epstein/qdrant_embed_chunks.py` - Main embedding script
- `epstein/qdrant_embed_chunks_1.py` - Alternative 1
- `epstein/qdrant_embed_chunks2.py` - Alternative 2
- `epstein/qdrant_semantic_search.py` - Search functionality

### Agent Scripts
- `agents/epstein_data_processor.py` - Core processor
- `agents/document_analysis_agent.py` - Analysis
- `agents/entity_extraction_agent.py` - Entity extraction
- `agents/vector_db_analyzer.py` - Vector DB analysis
- `agents/db_troubleshooter.py` - Database troubleshooting
- `agents/pipeline_monitor.py` - Monitoring
- `agents/multi_agent_orchestrator.py` - Orchestration

### System Scripts
- `scripts/doctor.py` - Health checks
- `scripts/cbw_bootstrap_project_ubuntu.sh` - Environment setup

## Missing Scripts Identified

Based on the project requirements, the following scripts are needed but not yet present:

1. **MCP Server for Epstein Files Download** - Need to create a dedicated MCP server
2. **OpenTelemetry Integration Scripts** - For observability and tracing
3. **OpenObservability Integration Scripts** - For monitoring and metrics
4. **OpenRouter SDK Integration** - For AI model access
5. **Comprehensive Ingestion Scripts** - For various document sources
6. **Data Model Validation Scripts** - To verify schema setup
7. **AI Agent Cheat Sheet Generator** - Documentation for AI agents

## Next Steps

1. **Assess Database Setup**: Verify the database schema is properly implemented
2. **Design MCP Server**: Create MCP server for downloading Epstein files
3. **Library Integration**: Set up OpenTelemetry, OpenObservability, and OpenRouter SDKs
4. **Create Modular Scripts**: Develop reusable components for the libraries
5. **Verify Data Model**: Ensure the schema meets all requirements
6. **Create Ingestion Scripts**: Develop comprehensive document ingestion workflows
7. **Design Cheat Sheet**: Create documentation for AI agents
