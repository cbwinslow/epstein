# Epstein Project - Agents and Tools Documentation

## Overview

This document describes the agents and tools available for the Epstein document processing pipeline. All agents are designed to be OpenAI-compatible and can be integrated with various AI platforms.

## Directory Structure

```
agents/           # Agent implementations
├── epstein_data_processor.py

tools/            # Tool definitions and utilities
├── epstein_tools.py

config/           # Configuration files
├── agent_config.json

schemas/          # JSON schemas for data structures
├── epstein_schema.json
```

## Agents

### Epstein Data Processor Agent

**Location**: `agents/epstein_data_processor.py`

**Description**: Specialized agent for PDF document processing with OCR, NER, embeddings, and vector search capabilities.

**Capabilities**:
- OCR processing using Tesseract
- Text extraction from PDF documents
- Named Entity Recognition (PERSON, ORG, LOC, etc.)
- Vector embeddings generation
- Semantic search functionality

**OpenAI Functions**:
1. `process_document` - Process documents with specified operations
2. `search_similar_documents` - Vector similarity search
3. `get_task_status` - Check task processing status

**Usage Example**:
```python
from agents.epstein_data_processor import EpsteinDataProcessor

agent = EpsteinDataProcessor()
result = await agent.process_document(
    file_path="document.pdf",
    operations=["ocr", "extract_text", "ner", "embeddings"]
)
```

## Tools

### Epstein Tools Suite

**Location**: `tools/epstein_tools.py`

**Description**: Collection of tools for pipeline management, database operations, and vector search.

**Available Tools**:
1. `run_epstein_pipeline` - Execute full processing pipeline
2. `query_epstein_database` - SQL database queries
3. `search_vector_embeddings` - Semantic vector search
4. `get_pipeline_status` - Pipeline status monitoring
5. `analyze_document_entities` - Entity analysis
6. `export_processing_results` - Data export functionality

**Usage Example**:
```python
from tools.epstein_tools import EpsteinTools

tools = EpsteinTools()
result = await tools.run_pipeline(
    config_path="config.json",
    documents=["doc1.pdf", "doc2.pdf"]
)
```

## Configuration

### Agent Configuration

**Location**: `config/agent_config.json`

Contains configuration for:
- Agent capabilities and versions
- Model configurations (embedding models, NER models)
- Database connection settings
- Processing parameters
- OpenAI compatibility settings
- Security and monitoring configurations

**Key Settings**:
- `embedding_model`: text-embedding-ada-002
- `ner_model`: en_core_web_sm
- `postgres_dsn`: PostgreSQL connection string
- `qdrant_url`: Vector database URL
- `batch_size`: Processing batch size (10)

## Data Schemas

### Epstein Schema

**Location**: `schemas/epstein_schema.json`

Defines JSON schemas for:
- **Document**: Document metadata and processing status
- **Entity**: Named entity extraction results
- **Chunk**: Text chunks with embeddings
- **Processing Task**: Task execution tracking
- **Search Result**: Search query results
- **Export Format**: Data export structures

## Integration with OpenAI

All tools and agents are OpenAI-compatible and support:

### Function Calling
```json
{
  "type": "function",
  "function": {
    "name": "process_document",
    "description": "Process a PDF document...",
    "parameters": { ... }
  }
}
```

### Streaming Support
- Real-time task status updates
- Progress monitoring
- Error handling with detailed messages

### Response Formats
- JSON responses with structured data
- Error handling with status codes
- Metadata for audit trails

## Security Features

- **Redaction**: Automatic PII redaction
- **Audit Logging**: Complete operation audit trail
- **Access Control**: Role-based access control
- **Encryption**: AES-256 data encryption

## Monitoring and Metrics

- **Metrics Collection**: Prometheus-compatible metrics
- **Performance Tracking**: Task duration and success rates
- **Resource Monitoring**: Memory and CPU usage
- **Error Tracking**: Comprehensive error logging

## Usage Patterns

### Document Processing Pipeline
1. Upload documents to the system
2. Call `run_epstein_pipeline` with configuration
3. Monitor progress with `get_pipeline_status`
4. Retrieve results with `query_epstein_database`
5. Export data using `export_processing_results`

### Semantic Search
1. Generate query embeddings
2. Use `search_vector_embeddings` for similar documents
3. Analyze entities with `analyze_document_entities`
4. Export search results as needed

### Batch Processing
1. Configure batch settings in `agent_config.json`
2. Process multiple documents simultaneously
3. Monitor task queue and status
4. Handle failures and retries automatically

## API Endpoints

When configured as a service, the following endpoints are available:

- `POST /api/v1/process` - Document processing
- `GET /api/v1/status` - Pipeline status
- `POST /api/v1/search` - Semantic search
- `GET /api/v1/documents/{id}` - Document retrieval
- `POST /api/v1/export` - Data export

## Error Handling

All operations include comprehensive error handling:
- Detailed error messages
- Error codes for programmatic handling
- Retry mechanisms for transient failures
- Fallback options for degraded service

## Performance Considerations

- **Batch Processing**: Optimize for throughput
- **Caching**: Embedding and text caching
- **Parallel Processing**: Multi-core utilization
- **Memory Management**: Streaming for large files

## Security and Compliance

- **Data Privacy**: PII detection and redaction
- **Access Control**: Role-based permissions
- **Audit Trails**: Complete operation logging
- **Encryption**: At-rest and in-transit encryption

## Extensibility

The system is designed for extensibility:
- Plugin architecture for new processors
- Configurable model backends
- Custom entity types
- Additional export formats
- Integration with external services

## Troubleshooting

### Common Issues
1. **Memory Errors**: Reduce batch size or enable streaming
2. **Slow Processing**: Check model configuration and batch settings
3. **Database Errors**: Verify connection strings and permissions
4. **Search Failures**: Ensure embeddings are generated and indexed

### Debug Mode
Enable debug logging in configuration:
```json
{
  "monitoring": {
    "log_level": "DEBUG",
    "enable_metrics": true
  }
}
```

## Future Enhancements

Planned improvements include:
- Additional OCR engines (ABBYY, Amazon Textract)
- Custom entity recognition models
- Advanced semantic search algorithms
- Real-time collaboration features
- Cloud-native deployment options
