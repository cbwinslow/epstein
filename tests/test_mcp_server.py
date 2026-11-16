#!/usr/bin/env python3
"""
Comprehensive Test Suite for Epstein Files MCP Server

Tests all MCP server functionality including:
- Server initialization and configuration
- API endpoints and responses
- Download functionality
- Error handling and edge cases
- Performance and concurrency
"""

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Import server components
from mcp_servers.epstein_files_downloader.server import (
    CollectionInfo,
    DocumentInfo,
    DownloadTask,
    EpsteinFilesDownloader,
    ServerConfig,
)

# Test Configuration
TEST_CONFIG = ServerConfig(
    host="127.0.0.1",
    port=8766,  # Use different port for testing
    download_dir=tempfile.mkdtemp(),
    max_concurrent_downloads=2,
    retry_attempts=2,
    retry_delay=1,
)


@pytest.fixture
def test_server():
    """Create test server instance"""
    server = EpsteinFilesDownloader(TEST_CONFIG)
    return server


@pytest.fixture
def test_client(test_server):
    """Create test client for FastAPI app"""
    return TestClient(test_server.app)


# ============================================================================
# Server Initialization Tests
# ============================================================================


class TestServerInitialization:
    """Test server initialization and configuration"""

    def test_server_creation(self, test_server):
        """Test server instance creation"""
        assert test_server is not None
        assert test_server.config.host == TEST_CONFIG.host
        assert test_server.config.port == TEST_CONFIG.port
        assert Path(test_server.config.download_dir).exists()
        assert test_server.status == "initialized"

    def test_download_directory(self, test_server):
        """Test download directory creation"""
        download_dir = Path(test_server.config.download_dir)
        assert download_dir.exists()
        assert download_dir.is_dir()

    def test_http_session(self, test_server):
        """Test HTTP session initialization"""
        assert test_server.session is not None
        assert hasattr(test_server.session, "get")
        assert hasattr(test_server.session, "post")

    def test_fastapi_app(self, test_server):
        """Test FastAPI app initialization"""
        assert test_server.app is not None
        assert hasattr(test_server.app, "get")
        assert hasattr(test_server.app, "post")


# ============================================================================
# API Endpoint Tests
# ============================================================================


class TestAPIEndpoints:
    """Test all API endpoints"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "server" in data
        assert "version" in data
        assert "endpoints" in data

    def test_health_endpoint(self, test_client):
        """Test health endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "active_downloads" in data

    def test_collections_endpoint(self, test_client, mocker):
        """Test collections endpoint"""
        # Mock discover_collections method
        mock_collections = [
            CollectionInfo(
                collection_id="test_coll_1",
                name="Test Collection 1",
                description="Test description",
                url="http://example.com/collection1",
                source="govinfo.gov",
            )
        ]

        mocker.patch.object(
            EpsteinFilesDownloader, "discover_collections", return_value=mock_collections
        )

        response = test_client.get("/collections")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["collection_id"] == "test_coll_1"
        assert data[0]["name"] == "Test Collection 1"

    def test_collection_details_endpoint(self, test_client, mocker):
        """Test collection details endpoint"""
        # Mock discover_collections method
        mock_collections = [
            CollectionInfo(
                collection_id="test_coll_1",
                name="Test Collection 1",
                description="Test description",
                url="http://example.com/collection1",
                source="govinfo.gov",
            )
        ]

        mocker.patch.object(
            EpsteinFilesDownloader, "discover_collections", return_value=mock_collections
        )

        response = test_client.get("/collections/test_coll_1")
        assert response.status_code == 200
        data = response.json()
        assert data["collection_id"] == "test_coll_1"

    def test_collection_not_found(self, test_client, mocker):
        """Test collection not found error"""
        mocker.patch.object(EpsteinFilesDownloader, "discover_collections", return_value=[])

        response = test_client.get("/collections/nonexistent")
        assert response.status_code == 404
        assert "Collection not found" in response.text

    def test_download_endpoint(self, test_client, mocker):
        """Test download endpoint"""
        # Mock download processing
        mocker.patch.object(EpsteinFilesDownloader, "_process_download_queue", return_value=None)

        payload = {"url": "http://example.com/test.pdf", "destination": TEST_CONFIG.download_dir}

        response = test_client.post("/download", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    def test_bulk_download_endpoint(self, test_client, mocker):
        """Test bulk download endpoint"""
        # Mock document listing and download processing
        mock_documents = [
            DocumentInfo(
                document_id="doc_1",
                collection_id="test_coll",
                title="Test Document",
                url="http://example.com/doc1.pdf",
            )
        ]

        mocker.patch.object(
            EpsteinFilesDownloader, "get_collection_documents", return_value=mock_documents
        )

        mocker.patch.object(EpsteinFilesDownloader, "_process_download_queue", return_value=None)

        payload = {"collection_id": "test_coll", "destination": TEST_CONFIG.download_dir}

        response = test_client.post("/download/bulk", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "task_id" in data[0]


# ============================================================================
# Download Functionality Tests
# ============================================================================


class TestDownloadFunctionality:
    """Test download functionality"""

    def test_download_task_creation(self, test_server):
        """Test download task creation"""
        task = DownloadTask(
            task_id="test_task_1",
            url="http://example.com/test.pdf",
            destination=TEST_CONFIG.download_dir,
        )

        assert task.task_id == "test_task_1"
        assert task.url == "http://example.com/test.pdf"
        assert task.status == "pending"
        assert task.progress == 0.0

    def test_safe_filename_generation(self, test_server):
        """Test safe filename generation"""
        safe_name = test_server._generate_safe_filename(
            "http://example.com/Test File (Special).pdf", {"title": "Test Document"}
        )

        assert "Test_Document" in safe_name
        assert safe_name.endswith(".pdf")
        assert all(c.isalnum() or c in ["_", "-", "."] for c in safe_name)

    def test_download_queue_management(self, test_server):
        """Test download queue management"""
        # Add tasks to queue
        task1 = DownloadTask(
            task_id="task_1",
            url="http://example.com/file1.pdf",
            destination=TEST_CONFIG.download_dir,
        )

        task2 = DownloadTask(
            task_id="task_2",
            url="http://example.com/file2.pdf",
            destination=TEST_CONFIG.download_dir,
        )

        test_server.download_queue.put_nowait(task1)
        test_server.download_queue.put_nowait(task2)

        assert test_server.download_queue.qsize() == 2


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_url_download(self, test_client):
        """Test download with invalid URL"""
        payload = {"url": "invalid-url", "destination": TEST_CONFIG.download_dir}

        response = test_client.post("/download", json=payload)
        assert response.status_code in [400, 422]  # Bad request or validation error

    def test_nonexistent_collection(self, test_client, mocker):
        """Test nonexistent collection handling"""
        mocker.patch.object(
            EpsteinFilesDownloader,
            "get_collection_documents",
            side_effect=Exception("Collection not found"),
        )

        payload = {"collection_id": "nonexistent", "destination": TEST_CONFIG.download_dir}

        response = test_client.post("/download/bulk", json=payload)
        assert response.status_code == 500
        assert "Collection not found" in response.text

    def test_invalid_task_id_status(self, test_client):
        """Test invalid task ID for status check"""
        response = test_client.get("/download/status/invalid_task_id")
        assert response.status_code == 404
        assert "Task not found" in response.text


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance and concurrency"""

    def test_concurrent_downloads(self, test_server, mocker):
        """Test concurrent download handling"""

        # Mock async download to avoid actual network calls
        async def mock_download(task):
            await asyncio.sleep(0.1)
            task.status = "completed"
            task.progress = 100.0
            test_server._complete_task(task)

        mocker.patch.object(EpsteinFilesDownloader, "_download_single", side_effect=mock_download)

        # Add multiple tasks
        tasks = []
        for i in range(5):
            task = DownloadTask(
                task_id=f"test_task_{i}",
                url=f"http://example.com/file{i}.pdf",
                destination=TEST_CONFIG.download_dir,
            )
            tasks.append(task)
            test_server.download_queue.put_nowait(task)

        # Process queue
        asyncio.run(test_server._process_download_queue())

        # Verify tasks completed
        assert len(test_server.completed_tasks) == 5
        assert len(test_server.active_tasks) == 0

    def test_response_time(self, test_client, benchmark):
        """Test API response time"""

        def test_endpoint():
            return test_client.get("/health")

        result = benchmark(test_endpoint)
        assert result.status_code == 200
        # Response should be fast (< 100ms)
        assert result.elapsed.total_seconds() < 0.1


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Test integration between components"""

    def test_discovery_to_download_flow(self, test_client, mocker):
        """Test complete flow from discovery to download"""
        # Mock collection discovery
        mock_collections = [
            CollectionInfo(
                collection_id="test_coll",
                name="Test Collection",
                description="Test",
                url="http://example.com/coll",
                source="govinfo",
            )
        ]

        mocker.patch.object(
            EpsteinFilesDownloader, "discover_collections", return_value=mock_collections
        )

        # Mock document listing
        mock_documents = [
            DocumentInfo(
                document_id="doc_1",
                collection_id="test_coll",
                title="Test Doc",
                url="http://example.com/doc.pdf",
            )
        ]

        mocker.patch.object(
            EpsteinFilesDownloader, "get_collection_documents", return_value=mock_documents
        )

        mocker.patch.object(EpsteinFilesDownloader, "_process_download_queue", return_value=None)

        # Step 1: Discover collections
        collections_response = test_client.get("/collections")
        assert collections_response.status_code == 200
        collections = collections_response.json()
        assert len(collections) == 1

        # Step 2: List documents in collection
        collection_id = collections[0]["collection_id"]
        documents_response = test_client.get(f"/collections/{collection_id}/documents")
        assert documents_response.status_code == 200
        documents = documents_response.json()
        assert len(documents) == 1

        # Step 3: Download documents
        download_payload = {"collection_id": collection_id, "destination": TEST_CONFIG.download_dir}

        download_response = test_client.post("/download/bulk", json=download_payload)
        assert download_response.status_code == 200
        download_tasks = download_response.json()
        assert len(download_tasks) == 1

        # Step 4: Check download status
        task_id = download_tasks[0]["task_id"]
        status_response = test_client.get(f"/download/status/{task_id}")
        assert status_response.status_code == 200


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main(
        ["--verbose", "--color=yes", "-x", "-s", __file__]  # Stop on first failure  # Show output
    )
