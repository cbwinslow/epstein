# Epstein Files Project - User Instructions Manual

**Version**: 1.0  
**Last Updated**: January 7, 2026  
**Current Status**: Active Development  

---

## 🎯 Quick Start Overview

This repository contains a comprehensive document processing pipeline for the Epstein Files project, including document download, OCR processing, entity extraction, and semantic search capabilities.

**Current Collection**: 14,753 files (14,672 DOJ + 81 Congressional)  
**Target**: 25,000+ files with full processing pipeline operational

---

## 📁 Repository Structure

```
/home/cbwinslow/epstein/epstein/
├── README.md                           # Basic project overview
├── Makefile                          # Main build and automation commands
├── docker-compose.yml                # Container orchestration
├── .env.example                      # Environment variables template
├── pyproject.toml                    # Python dependencies
├── 
├── epstein/                          # Main pipeline code
│   ├── epstein_files_pipeline.py     # Core processing pipeline
│   ├── db_ingest_artifacts.py        # Database ingestion
│   ├── qdrant_embed_chunks.py        # Vector embeddings
│   └── qdrant_semantic_search.py     # Semantic search
│
├── agents/                           # AI agents and utilities
│   ├── multi_agent_orchestrator.py   # Agent coordination
│   ├── document_analysis_agent.py    # Document analysis
│   ├── entity_extraction_agent.py    # NER processing
│   ├── pipeline_monitor.py           # Processing monitoring
│   └── vector_db_analyzer.py         # Vector database analysis
│
├── scripts/                          # Utility scripts
│   ├── bootstrap_dev.sh             # Development environment setup
│   ├── doctor.py                    # System health checks
│   ├── vector_db_bootstrap.sh       # Database setup
│   └── ingestion_pipeline.py        # Data ingestion
│
├── docs/                            # Comprehensive documentation
│   ├── TOOLS_AND_MCP_SERVERS.md     # Required tools and services
│   ├── ARCHITECTURE.md              # System architecture
│   ├── MISSION_CONTROL.md           # Web interface guide
│   └── MULTI_AGENT_SYSTEM_GUIDE.md  # Agent system documentation
│
└── config/                          # Configuration files
    └── agent_config.json            # Agent configurations
```

---

## 🚀 Quick Start Guide

### Step 1: Prerequisites Check

Run the system health check to verify your environment:

```bash
# Check system requirements and dependencies
python scripts/doctor.py

# Or use the Docker-based health check
make doctor
```

### Step 2: Environment Setup

Choose your preferred setup method:

#### Option A: Automated Bootstrap (Recommended)

```bash
# Complete development environment setup
./scripts/bootstrap_dev.sh

# Verify setup
make doctor-check
```

#### Option B: Manual Docker Setup

```bash
# Start required services (PostgreSQL + Qdrant)
make bootstrap

# Check service status
make status

# Verify databases are accessible
python scripts/doctor.py --check-db
```

### Step 3: Basic Pipeline Execution

```bash
# Initialize pipeline configuration
make pipeline-init

# Run the complete document processing pipeline
make pipeline-run

# Load processed data into database
make db-load
```

### Step 4: Verify Installation

```bash
# Run tests to ensure everything works
make test

# Check pipeline health
curl -s http://localhost:8080/api/v1/health | jq .
```

---

## 🛠️ Detailed Component Guide

### 1. Document Processing Pipeline

#### Core Pipeline (`epstein_files_pipeline.py`)

**Purpose**: End-to-end document processing from download to search-ready data.

**Main Features**:
- Document URL discovery from trusted sources
- Safe, idempotent PDF downloads with manifest tracking
- OCR processing for scanned documents
- Text extraction and chunking with overlap
- Named Entity Recognition (NER)
- Vector embedding generation
- Database ingestion and indexing

**Usage**:

```bash
# Initialize configuration with default sources
python epstein/epstein_files_pipeline.py init-config --out ./config.json

# Run full pipeline
python epstein/epstein_files_pipeline.py run --config ./config.json

# Regenerate safe exports from existing data
python epstein/epstein_files_pipeline.py export-safe --config ./config.json
```

**Configuration Options**:
- `seed_urls`: Trusted document sources
- `output_dir`: Processing output location
- `allow_domains`: Security domain restrictions
- `enable_ocr`: OCR processing toggle
- `chunk_chars`: Text chunking size (default: 10,000)
- `spacy_model`: NER model (default: en_core_web_sm)

#### Orchestrator (`pipeline_orchestrator.py`)

**Purpose**: Run the pipeline end-to-end and optionally trigger image OCR, relationship analysis, and Qdrant embeddings.

**Usage**:

```bash
python -m epstein.pipeline_orchestrator \
  --config ./config.json \
  --dsn postgresql://analysis:analysis@localhost:5432/analysis \
  --qdrant-url http://localhost:6333 \
  --run-ingest \
  --run-relationships
```

#### Pipeline Monitoring (`agents/pipeline_monitor.py`)

**Purpose**: Real-time monitoring and progress tracking for long-running operations.

**Features**:
- Processing queue status
- Success/failure rate tracking
- Performance metrics collection
- Error logging and alerting

**Usage**:

```bash
# Check current processing status
python agents/pipeline_monitor.py --status

# View detailed metrics
python agents/pipeline_monitor.py --metrics

# Monitor specific job
python agents/pipeline_monitor.py --job-id <JOB_ID>
```

### 2. Multi-Agent System

#### Agent Orchestrator (`agents/multi_agent_orchestrator.py`)

**Purpose**: Coordinates multiple AI agents for specialized document processing tasks.

**Available Agents**:
- **Document Analysis Agent**: Content analysis and summarization
- **Entity Extraction Agent**: Named Entity Recognition
- **Vector DB Analyzer**: Vector database optimization
- **Pipeline Monitor**: System health and performance monitoring

**Usage**:

```bash
# Start agent orchestrator
python agents/multi_agent_orchestrator.py start

# Run specific agent
python agents/document_analysis_agent.py --document <FILE_PATH>

# Check agent status
python agents/multi_agent_orchestrator.py status
```

#### Individual Agent Usage

**Document Analysis Agent**:
```bash
# Analyze single document
python agents/document_analysis_agent.py analyze --input document.pdf

# Batch analysis
python agents/document_analysis_agent.py batch --input-dir ./documents/

# Export analysis results
python agents/document_analysis_agent.py export --format json --output results.json
```

**Entity Extraction Agent**:
```bash
# Extract entities from text
python agents/entity_extraction_agent.py extract --text "Epstein investigation..."

# Process PDF files
python agents/entity_extraction_agent.py process-pdf --input document.pdf

# Export entity data
python agents/entity_extraction_agent.py export --output entities.jsonl
```

### 3. Database Systems

#### PostgreSQL Integration (`db/`)

**Purpose**: Relational data storage for documents, metadata, and processing results.

**Database Schema**:
- `documents`: Document metadata and content
- `entities`: Extracted entities with provenance
- `chunks`: Text chunks with embeddings
- `processing_runs`: Pipeline execution tracking
- `sources`: Document source tracking

**Usage**:

```bash
# Run database migrations
python db/migrate.py

# Check database connectivity
python scripts/doctor.py --check-db

# Query documents
psql $EPSTEIN_DSN -c "SELECT COUNT(*) FROM documents;"

# View schema
psql $EPSTEIN_DSN -f db/schema.sql
```

#### Qdrant Vector Database

**Purpose**: Vector similarity search for semantic document retrieval.

**Collections**:
- `epstein_chunks`: Document text chunks with embeddings
- `epstein_entities`: Entity vectors for entity search
- `epstein_queries`: Query tracking and optimization

**Usage**:

```bash
# Start Qdrant service
make bootstrap

# Embed chunks into vector database
python epstein/qdrant_embed_chunks.py --input-dir ./epstein_artifacts/chunks/

# Semantic search
python epstein/qdrant_semantic_search.py --query "Epstein investigation evidence"

# Vector database analysis
python agents/vector_db_analyzer.py --analyze
```

### 4. Mission Control Interface

#### Web-Based Interface

**Purpose**: Browser-based interface for system monitoring, search, and analysis.

**Access**: http://localhost:8080/mission-control

**Features**:
- Real-time processing status
- Document search and browse
- Entity network visualization
- Processing queue management
- Export and reporting tools

**Usage**:

```bash
# Start Mission Control
bin/mission-control start

# Check service status
bin/mission-control status

# Configure interface
python -c "from bin.mission_control import setup; setup()"
```

#### API Endpoints

**Search API**:
```bash
# Semantic search
curl -X GET "http://localhost:8080/api/v1/documents/search?q=Epstein" | jq .

# Entity search
curl -X GET "http://localhost:8080/api/v1/entities/search?q=Clinton" | jq .

# Processing status
curl -X GET "http://localhost:8080/api/v1/monitoring/status" | jq .
```

### 5. Utility Scripts

#### System Health Checks (`scripts/doctor.py`)

**Purpose**: Comprehensive system validation and troubleshooting.

**Checks Performed**:
- Docker daemon availability
- Database connectivity (PostgreSQL + Qdrant)
- Python environment setup
- Required system packages
- Service endpoints

**Usage**:

```bash
# Quick health check
python scripts/doctor.py

# Database connectivity check
python scripts/doctor.py --check-db

# Detailed system report
python scripts/doctor.py --detailed

# Fix common issues
python scripts/doctor.py --fix
```

#### Database Bootstrap (`scripts/vector_db_bootstrap.sh`)

**Purpose**: Initialize and configure vector database infrastructure.

**Usage**:

```bash
# Start all services
./scripts/vector_db_bootstrap.sh up

# Start with PostgreSQL
./scripts/vector_db_bootstrap.sh --enable-postgres true up

# Stop services
./scripts/vector_db_bootstrap.sh down

# Reset databases
./scripts/vector_db_bootstrap.sh reset
```

#### Data Ingestion (`scripts/ingestion_pipeline.py`)

**Purpose**: Bulk data ingestion and processing coordination.

**Usage**:

```bash
# Ingest DOJ documents
python scripts/ingestion_pipeline.py --source doj --input-dir ./data/doj/

# Ingest Congressional documents
python scripts/ingestion_pipeline.py --source congress --input-dir ./data/congress/

# Resume interrupted ingestion
python scripts/ingestion_pipeline.py --resume --job-id <JOB_ID>
```

---

## 🔧 Makefile Commands Reference

### Development Commands

```bash
# Show all available commands
make help

# Development environment setup
make bootstrap

# System health check
make doctor

# Check service status
make status

# Stop all services
make down
```

### Pipeline Commands

```bash
# Initialize pipeline configuration
make pipeline-init

# Run document processing pipeline
make pipeline-run

# Load processed data into database
make db-load

# Generate safe exports
make export-safe
```

### Testing Commands

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration

# Run tests with coverage
make test-coverage

# Run tests in watch mode
make test-watch
```

### Code Quality Commands

```bash
# Format code
make format

# Run linting
make lint

# Type checking
make type-check

# Pre-commit validation
make pre-commit
```

---

## 📊 System Requirements

### Hardware Requirements

**Minimum**:
- 8GB RAM
- 50GB disk space
- 4 CPU cores
- Internet connection

**Recommended**:
- 16GB RAM
- 200GB disk space
- 8 CPU cores
- SSD storage

### Software Requirements

**Operating System**: Ubuntu 20.04+, macOS 10.15+, Windows 10+ (WSL2)

**Required Software**:
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.10+
- uv (Python package manager)

**System Packages**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose python3 python3-pip

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Python Dependencies

**Core Dependencies**:
- requests, beautifulsoup4, lxml, tqdm, pydantic
- pdfminer.six, spacy, psycopg[binary]
- qdrant-client, python-dotenv

**Install via uv**:
```bash
uv add requests beautifulsoup4 lxml tqdm pydantic pdfminer.six spacy psycopg[binary] qdrant-client python-dotenv
```

---

## 🚨 Troubleshooting Guide

### Common Issues and Solutions

#### 1. Docker Services Not Starting

**Problem**: Services fail to start or are not accessible.

**Solutions**:
```bash
# Check Docker daemon status
sudo systemctl status docker

# Restart Docker service
sudo systemctl restart docker

# Check port conflicts
netstat -tlnp | grep :5432
netstat -tlnp | grep :6333

# View Docker logs
docker compose logs qdrant
docker compose logs postgres
```

#### 2. Database Connection Issues

**Problem**: Cannot connect to PostgreSQL or Qdrant.

**Solutions**:
```bash
# Verify environment variables
echo $EPSTEIN_DSN
echo $QDRANT_URL

# Test PostgreSQL connection
python -c "
import psycopg2
conn = psycopg2.connect('$EPSTEIN_DSN')
print('PostgreSQL: Connected successfully')
conn.close()
"

# Test Qdrant connection
python -c "
import qdrant_client
client = qdrant_client.QdrantClient(url='$QDRANT_URL')
print('Qdrant: Connected successfully')
print(f'Collections: {len(client.get_collections().collections)}')
"
```

#### 3. Pipeline Processing Failures

**Problem**: Documents fail to process or OCR fails.

**Solutions**:
```bash
# Check disk space
df -h

# Verify Python dependencies
uv sync

# Check spaCy model
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('spaCy model OK')"

# View processing logs
tail -f ./epstein_artifacts/run.log

# Restart pipeline with verbose logging
python epstein/epstein_files_pipeline.py run --config ./config.json --verbose
```

#### 4. Memory Issues During Processing

**Problem**: System runs out of memory during large document batches.

**Solutions**:
```bash
# Reduce batch size in configuration
# Edit config.json:
{
  "max_workers": 2,
  "chunk_chars": 5000,
  "chunk_overlap_chars": 750
}

# Process documents in smaller batches
python epstein/epstein_files_pipeline.py run --config ./config_batch1.json
python epstein/epstein_files_pipeline.py run --config ./config_batch2.json
```

#### 5. Agent System Issues

**Problem**: Multi-agent system not responding or agents failing.

**Solutions**:
```bash
# Restart agent orchestrator
python agents/multi_agent_orchestrator.py restart

# Check agent health
python agents/multi_agent_orchestrator.py health-check

# Restart individual agent
python agents/document_analysis_agent.py --restart

# Clear agent cache
rm -rf ./agents/.cache/
```

### Performance Optimization

#### For Large Document Collections

1. **Increase Workers**: 
   ```json
   {
     "max_workers": 8,
     "chunk_chars": 15000,
     "chunk_overlap_chars": 2000
   }
   ```

2. **Enable Parallel Processing**:
   ```bash
   # Process multiple sources simultaneously
   python scripts/ingestion_pipeline.py --source doj --parallel &
   python scripts/ingestion_pipeline.py --source congress --parallel &
   ```

3. **Optimize Database Queries**:
   ```bash
   # Add database indexes
   psql $EPSTEIN_DSN -f scripts/add_indexes.sql
   ```

#### For Limited Resources

1. **Reduce Memory Usage**:
   ```json
   {
     "max_workers": 1,
     "enable_ocr": false,
     "chunk_chars": 3000,
     "spacy_model": "en_core_web_sm"
   }
   ```

2. **Process in Batches**:
   ```bash
   # Process 100 documents at a time
   find ./documents -name "*.pdf" | head -100 | xargs -I {} python process_single.py {}
   ```

---

## 📈 Monitoring and Observability

### Real-Time Monitoring

**System Health Dashboard**: http://localhost:8080/mission-control

**Key Metrics to Monitor**:
- Processing queue length
- Success/failure rates
- Database connection health
- Memory and CPU usage
- Vector database performance

### Log Analysis

**Pipeline Logs**:
```bash
# View recent processing logs
tail -f ./epstein_artifacts/run.log

# Search for errors
grep ERROR ./epstein_artifacts/run.log

# Monitor specific document processing
grep "doc_id.*ABC123" ./epstein_artifacts/run.log
```

**Database Logs**:
```bash
# PostgreSQL logs
docker compose logs postgres

# Qdrant logs
docker compose logs qdrant
```

### Performance Metrics

**Query Performance**:
```bash
# Check database query performance
python scripts/db_performance_check.py

# Analyze vector search performance
python scripts/vector_search_benchmark.py
```

---

## 🔒 Security Considerations

### Data Privacy

- All processing uses publicly released documents
- Basic PII redaction enabled by default
- No personal data storage beyond document content
- Audit logging for all data access

### Access Control

- API key authentication for Mission Control
- Database access restricted to application
- No public endpoint exposure
- Environment variable security

### Best Practices

1. **Regular Security Updates**:
   ```bash
   # Update dependencies
   uv sync
   
   # Update system packages
   sudo apt update && sudo apt upgrade
   ```

2. **Access Monitoring**:
   ```bash
   # Monitor API access
   tail -f ./logs/access.log
   
   # Check authentication logs
   grep "auth" ./logs/application.log
   ```

3. **Data Validation**:
   ```bash
   # Verify document integrity
   python scripts/validate_documents.py --check-hashes
   
   # Validate database consistency
   python scripts/db_consistency_check.py
