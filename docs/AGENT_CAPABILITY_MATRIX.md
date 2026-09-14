# Agent Capability Matrix

## Overview

This document provides a comprehensive matrix of all agents in the Epstein system, their capabilities, dependencies, and status.

## Agent Matrix

| Agent | Version | Status | Capabilities | Dependencies | MCP Server |
|-------|---------|--------|--------------|--------------|------------|
| **Epstein Data Processor** | 1.0.0 | ✅ Active | Document Processing, Entity Extraction, Vector Search | PostgreSQL, Qdrant, spaCy, OCRmyPDF | ❌ |
| **Vector DB Analyzer** | 1.0.0 | ✅ Active | Vector Search, Analysis, Monitoring | Qdrant | ❌ |
| **Database Troubleshooter** | 1.0.0 | ✅ Active | Database Query, Troubleshooting, Monitoring | PostgreSQL | ❌ |
| **Pipeline Monitor** | 1.0.0 | ✅ Active | Monitoring, Analysis | OpenTelemetry | ❌ |
| **Document Analysis Agent** | 1.0.0 | ✅ Active | Document Processing, Analysis | spaCy, transformers | ❌ |
| **Entity Extraction Agent** | 1.0.0 | ✅ Active | Entity Extraction, Analysis | spaCy, transformers | ❌ |
| **Codex Agent** | 0.1.0 | ✅ Active | Code Generation | OpenAI API (optional) | ❌ |
| **GovInfo Downloader** | 1.0.0 | ✅ Active | Downloading | requests, BeautifulSoup | ✅ MCP |
| **Multi-Agent Orchestrator** | 1.0.0 | ✅ Active | Orchestration | All agents | ❌ |

## Capability Details

### Document Processing
**Agents**: Epstein Data Processor, Document Analysis Agent

**What it does**:
- OCR processing of PDF documents
- Text extraction and preprocessing
- Document structure analysis
- Content classification

**Tools**:
- `process_document(file_path, operations)` - Process a document with specified operations
- `extract_text(file_path)` - Extract text from document
- `analyze_structure(file_path)` - Analyze document structure

**Use Cases**:
- Processing government document releases
- Converting scanned PDFs to searchable text
- Extracting metadata from documents

---

### Entity Extraction
**Agents**: Entity Extraction Agent, Epstein Data Processor

**What it does**:
- Named Entity Recognition (NER)
- Entity disambiguation
- Relationship extraction
- Knowledge graph construction

**Tools**:
- `extract_entities(text, entity_types)` - Extract named entities from text
- `extract_relationships(text)` - Extract entity relationships
- `build_knowledge_graph(entities, relationships)` - Build knowledge graph

**Use Cases**:
- Identifying people, organizations, locations in documents
- Finding connections between entities
- Building searchable knowledge bases

---

### Vector Search
**Agents**: Vector DB Analyzer, Epstein Data Processor

**What it does**:
- Semantic search using embeddings
- Similarity analysis
- Clustering and classification
- Collection management

**Tools**:
- `search_vectors(query, collection, limit)` - Semantic search
- `get_similar_documents(doc_id, limit)` - Find similar documents
- `analyze_collection(collection_name)` - Analyze vector collection

**Use Cases**:
- Finding semantically similar documents
- Clustering related documents
- Question answering over document corpus

---

### Database Query
**Agents**: Database Troubleshooter

**What it does**:
- SQL query execution
- Query optimization
- Index management
- Performance analysis

**Tools**:
- `execute_query(sql, params)` - Execute SQL query
- `analyze_query_performance(sql)` - Analyze query execution plan
- `get_table_stats(table_name)` - Get table statistics

**Use Cases**:
- Querying document metadata
- Performance optimization
- Database health monitoring

---

### Analysis
**Agents**: Document Analysis Agent, Vector DB Analyzer, Pipeline Monitor

**What it does**:
- Content analysis
- Quality assessment
- Performance analysis
- Trend detection

**Tools**:
- `analyze_content(text)` - Analyze document content
- `assess_quality(document)` - Assess document quality
- `detect_trends(metrics)` - Detect trends in metrics

**Use Cases**:
- Document quality assessment
- System performance analysis
- Anomaly detection

---

### Monitoring
**Agents**: Pipeline Monitor, Vector DB Analyzer, Database Troubleshooter

**What it does**:
- Health monitoring
- Performance tracking
- Error detection
- Alerting

**Tools**:
- `check_health()` - Check system health
- `get_metrics()` - Get performance metrics
- `detect_issues()` - Detect potential issues

**Use Cases**:
- System health monitoring
- Performance tracking
- Error alerting

---

### Orchestration
**Agents**: Multi-Agent Orchestrator

**What it does**:
- Task coordination
- Agent communication
- Workflow management
- Result aggregation

**Tools**:
- `orchestrate_workflow(workflow_spec)` - Execute multi-agent workflow
- `delegate_task(agent_id, task)` - Delegate task to agent
- `aggregate_results(results)` - Aggregate results from multiple agents

**Use Cases**:
- Complex multi-step processing workflows
- Parallel task execution
- Coordinated analysis

---

### Code Generation
**Agents**: Codex Agent

**What it does**:
- Code generation
- Code explanation
- Test generation
- Code review

**Tools**:
- `generate_code(prompt, language)` - Generate code from prompt
- `explain_code(code)` - Explain code functionality
- `suggest_tests(code)` - Suggest test cases

**Use Cases**:
- Pipeline script generation
- Test case creation
- Code documentation

---

### Downloading
**Agents**: GovInfo Downloader

**What it does**:
- Document discovery
- Bulk downloading
- Progress tracking
- Checksum verification

**Tools**:
- `list_collections()` - List available document collections
- `download_collection(collection_id)` - Download entire collection
- `get_download_status(task_id)` - Check download progress

**Use Cases**:
- Downloading government documents
- Bulk data acquisition
- Dataset preparation

---

### Troubleshooting
**Agents**: Database Troubleshooter

**What it does**:
- Issue detection
- Root cause analysis
- Fix recommendations
- Auto-recovery

**Tools**:
- `diagnose_issue(symptoms)` - Diagnose database issues
- `recommend_fixes(issue)` - Recommend fixes
- `apply_fix(fix_id)` - Apply automated fix

**Use Cases**:
- Database performance issues
- Connection problems
- Data corruption detection

---

## Agent Interactions

### Common Workflows

#### 1. Document Processing Pipeline
```
GovInfo Downloader → Epstein Data Processor → Entity Extraction Agent → Vector DB Analyzer
```

1. **GovInfo Downloader** discovers and downloads documents
2. **Epstein Data Processor** performs OCR and text extraction
3. **Entity Extraction Agent** extracts entities and relationships
4. **Vector DB Analyzer** generates embeddings and enables search

#### 2. Analysis Workflow
```
Document Analysis Agent → Entity Extraction Agent → Multi-Agent Orchestrator
```

1. **Document Analysis Agent** analyzes document structure and quality
2. **Entity Extraction Agent** identifies key entities
3. **Multi-Agent Orchestrator** aggregates and presents results

#### 3. Monitoring Workflow
```
Pipeline Monitor → Database Troubleshooter → Vector DB Analyzer
```

1. **Pipeline Monitor** tracks overall system health
2. **Database Troubleshooter** monitors PostgreSQL
3. **Vector DB Analyzer** monitors Qdrant

---

## Agent Dependencies

### System Dependencies
- Python 3.10+
- Docker & Docker Compose
- PostgreSQL 15+
- Qdrant 1.9+

### Python Dependencies
- Core: `pydantic`, `python-dotenv`, `loguru`
- Document Processing: `pdfminer.six`, `spacy`, `OCRmyPDF`
- Database: `psycopg[binary]`, `qdrant-client`
- Web: `requests`, `beautifulsoup4`, `lxml`
- Optional: `openai`, `transformers`, `torch`

---

## Configuration

All agents are configured via `/config/agent_config.json`. See [Agent Configuration Schema](../schemas/agent_config_schema.json) for details.

Example agent configuration:
```json
{
  "agent_name": {
    "name": "Agent Name",
    "description": "Agent description",
    "version": "1.0.0",
    "capabilities": ["document_processing", "analysis"],
    "dependencies": ["spacy", "transformers"],
    "model_config": {
      "embedding_model": "text-embedding-ada-002"
    },
    "tools": [
      {
        "name": "tool_name",
        "description": "Tool description",
        "parameters": {}
      }
    ]
  }
}
```

---

## Development Guidelines

### Adding a New Agent

1. **Inherit from BaseAgent**: All agents should inherit from `agents/base_agent.py`
2. **Implement Required Methods**: `get_metadata()`, `initialize()`, `shutdown()`
3. **Define Tools**: Create well-documented tools with clear parameters
4. **Add Configuration**: Update `config/agent_config.json`
5. **Register Agent**: Use `AgentRegistry` to register your agent
6. **Add Tests**: Create tests in `tests/test_<agent_name>.py`
7. **Document**: Update this capability matrix and agent README

### Tool Design Best Practices

1. **Clear Naming**: Use descriptive `snake_case` names
2. **Type Hints**: Always use type hints for parameters and returns
3. **Docstrings**: Comprehensive docstrings with examples
4. **Error Handling**: Graceful error handling with informative messages
5. **Validation**: Validate inputs using Pydantic models
6. **Async Support**: Use `async/await` for I/O-bound operations
7. **Idempotent**: Tools should be safe to call multiple times

---

## Status Legend

- ✅ **Active**: Fully implemented and tested
- 🚧 **Development**: Currently under development
- 📋 **Planned**: Planned for future implementation
- ⚠️ **Deprecated**: No longer recommended for use
- ❌ **Disabled**: Temporarily disabled

---

## Future Enhancements

### Planned Agents
1. **Relationship Discovery Agent** - Advanced relationship extraction
2. **Timeline Analysis Agent** - Temporal analysis and reconstruction
3. **Summary Generation Agent** - Automated document summarization
4. **Quality Control Agent** - Automated QC and validation
5. **Export Agent** - Multi-format export capabilities

### Planned Features
1. **Agent Communication Protocol** - Standardized inter-agent messaging
2. **Dynamic Agent Loading** - Load agents on-demand
3. **Agent Versioning** - Support multiple versions simultaneously
4. **Performance Profiling** - Built-in performance analysis
5. **Auto-scaling** - Dynamic resource allocation

---

**Last Updated**: 2026-01-15
**Version**: 2.0.0
**Maintainer**: Epstein Project Team
