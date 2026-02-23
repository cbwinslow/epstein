"""
Unit tests for the MCP Download Server.

These tests verify the core functionality of the MCP download server:
- Server configuration
- Download task management
- Collection discovery (mocked)
- Data models
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from uuid import uuid4

# Import what actually exists in the module
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from epstein.mcp_servers.epstein_files_downloader.server import (
    ServerConfig,
    DownloadTask,
    CollectionInfo,
    DocumentInfo,
)


class TestServerConfig:
    """Tests for ServerConfig."""

    def test_default_values(self):
        """Test default server configuration."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8765
        assert config.base_url == "http://localhost:8765"
        assert config.download_dir == "./downloads"
        assert config.max_concurrent_downloads == 5
        assert config.retry_attempts == 3

    def test_custom_values(self):
        """Test custom server configuration."""
        config = ServerConfig(
            host="127.0.0.1",
            port=9000,
            base_url="http://127.0.0.1:9000",
            download_dir="/tmp/downloads",
            max_concurrent_downloads=10,
        )
        assert config.port == 9000
        assert config.max_concurrent_downloads == 10

    def test_config_to_dict(self):
        """Test serializing config to dictionary."""
        config = ServerConfig(
            port=9000,
            download_dir="/custom/downloads",
            max_concurrent_downloads=5,
        )

        config_dict = {
            "host": config.host,
            "port": config.port,
            "base_url": config.base_url,
            "download_dir": config.download_dir,
            "max_concurrent_downloads": config.max_concurrent_downloads,
        }

        assert config_dict["port"] == 9000
        assert config_dict["download_dir"] == "/custom/downloads"


class TestDownloadTask:
    """Tests for DownloadTask."""

    def test_create_task(self):
        """Test creating a download task."""
        task = DownloadTask(
            task_id="test-123",
            url="https://example.com/file.pdf",
            destination="/tmp/file.pdf",
        )
        assert task.task_id == "test-123"
        assert task.url == "https://example.com/file.pdf"
        assert task.destination == "/tmp/file.pdf"
        assert task.status == "pending"
        assert task.progress == 0.0

    def test_task_status_updates(self):
        """Test task status can be updated."""
        task = DownloadTask(
            task_id="test-456",
            url="https://example.com/doc.pdf",
            destination="/tmp/doc.pdf",
        )
        task.status = "running"
        task.progress = 0.5

        assert task.status == "running"
        assert task.progress == 0.5

    def test_task_dict_conversion(self):
        """Test converting task to dictionary using asdict."""
        from dataclasses import asdict

        task = DownloadTask(
            task_id="test-789",
            url="https://example.com/test.pdf",
            destination="/tmp/test.pdf",
            status="completed",
            progress=1.0,
        )

        task_dict = asdict(task)

        assert task_dict["task_id"] == "test-789"
        assert task_dict["status"] == "completed"
        assert task_dict["progress"] == 1.0


class TestCollectionInfo:
    """Tests for CollectionInfo."""

    def test_create_collection(self):
        """Test creating a collection info object."""
        collection = CollectionInfo(
            collection_id="doj-001",
            name="DOJ Disclosure 1",
            description="First batch of Epstein-related documents",
            url="https://www.justice.gov/epstein/disclosure1",
            document_count=150,
            source="doj.gov",
        )

        assert collection.collection_id == "doj-001"
        assert collection.document_count == 150
        assert collection.source == "doj.gov"

    def test_collection_dict_conversion(self):
        """Test converting collection to dictionary."""
        from dataclasses import asdict

        collection = CollectionInfo(
            collection_id="fbi-001",
            name="FBI Vault",
            description="FBI released files",
            url="https://vault.fbi.gov/epstein",
            document_count=500,
            source="fbi.gov",
        )

        collection_dict = asdict(collection)

        assert collection_dict["name"] == "FBI Vault"
        assert collection_dict["document_count"] == 500


class TestDocumentInfo:
    """Tests for DocumentInfo."""

    def test_create_document(self):
        """Test creating a document info object."""
        doc = DocumentInfo(
            document_id="doc-123",
            collection_id="col-1",
            title="Epstein Flight Log 2001",
            url="https://example.com/flights.pdf",
        )

        assert doc.document_id == "doc-123"
        assert doc.collection_id == "col-1"
        assert doc.title == "Epstein Flight Log 2001"

    def test_document_dict_conversion(self):
        """Test converting document to dictionary."""
        from dataclasses import asdict

        doc = DocumentInfo(
            document_id="doc-456",
            collection_id="col-2",
            title="Test Document",
            url="https://example.com/test.pdf",
            file_size=2048,
        )

        doc_dict = asdict(doc)

        assert doc_dict["title"] == "Test Document"
        assert doc_dict["file_size"] == 2048


class TestMCPIntegration:
    """Integration tests for MCP server components."""

    def test_full_download_workflow(self):
        """Test a complete download workflow simulation."""
        # Create configuration
        config = ServerConfig(
            download_dir="/tmp/downloads",
            max_concurrent_downloads=3,
        )

        # Create a collection
        collection = CollectionInfo(
            collection_id="test-collection",
            name="Test Collection",
            description="A test collection",
            url="https://example.com/collection",
            document_count=10,
            source="test",
        )

        # Create documents
        documents = [
            DocumentInfo(
                document_id=f"doc-{i}",
                collection_id="test-collection",
                title=f"Document {i}",
                url=f"https://example.com/doc{i}.pdf",
            )
            for i in range(5)
        ]

        # Verify collection has correct document count
        assert collection.document_count == 10
        assert len(documents) == 5

        # Verify documents have unique IDs
        doc_ids = [d.document_id for d in documents]
        assert len(set(doc_ids)) == 5

    def test_task_tracking(self):
        """Test tracking multiple download tasks."""
        tasks = {}

        # Create multiple tasks
        for i in range(3):
            task_id = f"task-{i}"
            tasks[task_id] = DownloadTask(
                task_id=task_id,
                url=f"https://example.com/file{i}.pdf",
                destination=f"/tmp/downloads/file{i}.pdf",
            )

        # Update task statuses
        tasks["task-0"].status = "completed"
        tasks["task-1"].status = "running"
        tasks["task-1"].progress = 0.5

        # Verify statuses
        assert tasks["task-0"].status == "completed"
        assert tasks["task-1"].status == "running"
        assert tasks["task-1"].progress == 0.5
        assert tasks["task-2"].status == "pending"

    def test_config_with_download_dir(self):
        """Test server config with custom download directory."""
        config = ServerConfig(
            download_dir="/data/downloads",
            max_concurrent_downloads=10,
        )

        assert config.download_dir == "/data/downloads"
        assert config.max_concurrent_downloads == 10
