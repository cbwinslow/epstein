"""
Pytest configuration and fixtures for Epstein Files Pipeline tests.

This module provides:
- Fixtures for all test layers (unit, integration, e2e)
- Mock configurations
- Database/test service setup/teardown
- Common test utilities
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

import pytest


# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_data_dir(project_root) -> Path:
    """Return test data directory."""
    return project_root / "tests" / "fixtures"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for tests."""
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables for testing."""
    env_vars = {
        "EPSTEIN_ENV": "test",
        "EPSTEIN_DEBUG": "true",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_DB": "test",
        "QDRANT_URL": "http://localhost:6334",
        "MCP_PORT": "8766",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        yield env_vars


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "env": "test",
        "debug": True,
        "database": {
            "postgres_host": "localhost",
            "postgres_port": 5432,
            "postgres_user": "test",
            "postgres_password": "test",
            "postgres_db": "test",
            "qdrant_url": "http://localhost:6334",
            "qdrant_collection": "test_documents",
        },
        "mcp": {
            "host": "0.0.0.0",
            "port": 8766,
            "base_url": "http://localhost:8766",
            "download_dir": "./test_downloads",
            "max_concurrent_downloads": 2,
            "retry_attempts": 2,
        },
        "pipeline": {
            "batch_size": 5,
            "chunk_size": 256,
            "chunk_overlap": 25,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        },
    }


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL connection."""
    with patch("psycopg.connect") as mock_conn:
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.return_value = mock_cursor
        yield mock_conn


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client."""
    with patch("qdrant_client.QdrantClient") as mock_client:
        yield mock_client


@pytest.fixture
def mock_openai():
    """Mock OpenAI API."""
    with patch("openai.OpenAI") as mock_client:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_client.return_value.chat.completions.create.return_value = mock_response
        yield mock_client


@pytest.fixture
def mock_spacy():
    """Mock spaCy model."""
    with patch("spacy.load") as mock_nlp:
        mock_doc = Mock()
        mock_doc.ents = []
        mock_doc.sents = []
        mock_nlp.return_value = Mock(
            __call__=Mock(return_value=mock_doc),
            pipe=Mock(return_value=[mock_doc]),
        )
        yield mock_nlp


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_document_text() -> str:
    """Sample document text for testing."""
    return """
    JEFFREY EPSTEIN
    FLIGHT LOG ENTRY
    
    Date: January 15, 2001
    Aircraft: N919JE
    From: Palm Beach, FL
    To: New York, NY
    
    Passengers:
    - John Doe
    - Jane Smith
    
    Notes: Standard flight to Teterboro Airport.
    """


@pytest.fixture
def sample_metadata() -> Dict[str, Any]:
    """Sample document metadata."""
    return {
        "document_id": "abc123def456",
        "source_url": "https://www.justice.gov/epstein/disclosure1.pdf",
        "title": "Epstein Flight Log 2001",
        "document_type": "flight_log",
        "date": "2001-01-15",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "file_size": 1024000,
        "file_format": "pdf",
    }


@pytest.fixture
def sample_entities() -> list:
    """Sample NER entities."""
    return [
        {"text": "Jeffrey Epstein", "label": "PERSON", "start": 0, "end": 16},
        {"text": "Palm Beach", "label": "GPE", "start": 45, "end": 55},
        {"text": "New York", "label": "GPE", "start": 59, "end": 68},
        {"text": "January 15, 2001", "label": "DATE", "start": 28, "end": 44},
        {"text": "N919JE", "label": "FAC", "start": 37, "end": 43},
    ]


@pytest.fixture
def sample_embeddings() -> list:
    """Sample embedding vectors."""
    import numpy as np

    np.random.seed(42)
    return np.random.rand(5, 384).tolist()


# ============================================================================
# HTTP Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_http_response():
    """Mock HTTP response."""

    def _create_response(
        status: int = 200,
        json_data: Optional[Dict] = None,
        text: str = "",
    ):
        response = Mock()
        response.status_code = status
        response.json = Mock(return_value=json_data or {})
        response.text = text
        response.raise_for_status = Mock()
        if status >= 400:
            response.raise_for_status.side_effect = Exception(f"HTTP {status}")
        return response

    return _create_response


# ============================================================================
# Test Utilities
# ============================================================================


def create_test_file(path: Path, content: str = "test content"):
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def calculate_file_hash(path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    import hashlib

    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_db: Requires database connection")
    config.addinivalue_line("markers", "requires_mcp: Requires MCP server")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on location."""
    for item in items:
        if "test_" in item.nodeid:
            if "integration" in item.nodeid:
                item.add_marker(pytest.mark.integration)
            elif "e2e" in item.nodeid or "end_to_end" in item.nodeid:
                item.add_marker(pytest.mark.e2e)
            else:
                item.add_marker(pytest.mark.unit)
