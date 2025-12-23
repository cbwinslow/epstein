# Epstein Project - GitHub Copilot Instructions

## Project Overview
The Epstein project is a comprehensive data processing pipeline for analyzing PDF documents. It includes OCR (Optical Character Recognition), text extraction, chunking, Named Entity Recognition (NER), embeddings generation, and vector search capabilities using Qdrant and PostgreSQL.

## Key Technologies & Stack
- **Python 3.10** (always use this version)
- **uv** for Python package management
- **Docker** & **Docker Compose** for containerization
- **PostgreSQL** with pgvector extension for structured data
- **Qdrant** for vector search
- **OCR tools**: OCRmyPDF, Tesseract
- **NLP**: spaCy for NER
- **Web scraping**: requests, BeautifulSoup, lxml

## Development Guidelines
- Use `uv` for all Python dependency management
- Always pin Python version to 3.10
- Follow PEP 8 style guidelines
- Use type hints extensively
- Write comprehensive docstrings
- Implement proper error handling and logging
- Use async/await for I/O operations where beneficial

## Code Structure
- `epstein/` - Main pipeline code
- `scripts/` - Utility scripts
- `docs/` - Documentation
- `projects/` - Subprojects and bundles
- `docker/` - Docker configurations

## Common Patterns
- Data classes for configuration
- Factory patterns for pipeline components
- Context managers for resource handling
- Command-line interfaces with Click or argparse

## Database Schema
- `documents` table for metadata
- `document_text` for extracted text
- `chunks` for text chunks with offsets
- `entities` for NER results
- Vector embeddings stored in Qdrant

## Docker Development
- Use `make` commands for common operations
- Bootstrap with `make bootstrap`
- Run pipeline with `make pipeline-run`
- Load data with `make db-load`
- Run health checks with `python scripts/doctor.py` (quick checks) or `python scripts/doctor.py --check-db` (includes Postgres reachability). Use `make doctor-check` in CI to fail on unhealthy services.

## Security & Privacy
- Handle sensitive document data carefully
- Implement redaction where necessary
- Use environment variables for secrets
- Follow data minimization principles

## Testing
- Write unit tests for core functions
- Integration tests for pipeline components
- Use pytest framework
- Mock external dependencies

## Performance Considerations
- Process documents in batches
- Use streaming for large files
- Implement caching where appropriate
- Monitor memory usage with large documents

## AI/LLM Integration
- Use embeddings for semantic search
- Implement hybrid search (keyword + vector)
- Consider fine-tuning for domain-specific NER
- Evaluate model performance metrics

## Deployment
- Container-first approach
- Use Docker Compose for local development
- Implement health checks
- Configure proper logging and monitoring

Remember: This is a research/data processing project. Always prioritize data integrity, reproducibility, and ethical handling of information.
