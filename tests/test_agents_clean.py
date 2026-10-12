"""
Comprehensive tests for multi-agent system with OpenTelemetry instrumentation.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from agents.db_troubleshooter import DatabaseTroubleshooter
from agents.multi_agent_orchestrator import MultiAgentOrchestrator
from agents.pipeline_monitor import PipelineMonitor
from agents.telemetry import AgentTelemetry, get_telemetry

# Import agents
from agents.vector_db_analyzer import VectorDBAnalyzer


class TestTelemetry:
    """Tests for OpenTelemetry instrumentation"""

    @pytest.fixture
    def telemetry(self):
        """Create telemetry instance for testing"""
        return AgentTelemetry(
            service_name="test-telemetry", enable_console_export=False, enable_otlp_export=False
        )

    def test_telemetry_initialization(self, telemetry):
        """Test telemetry initialization"""
        assert telemetry.service_name == "test-telemetry"
        assert telemetry.tracer is not None
        assert telemetry.meter is not None

    @pytest.mark.asyncio
    async def test_trace_agent_execution_async(self, telemetry):
        """Test tracing async agent execution"""

        @telemetry.trace_agent_execution("test_agent")
        async def test_function():
            await asyncio.sleep(0.01)
            return {"status": "success"}

        result = await test_function()
        assert result["status"] == "success"

    def test_trace_agent_execution_sync(self, telemetry):
        """Test tracing sync agent execution"""

        @telemetry.trace_agent_execution("test_agent_sync")
        def test_function():
            return {"status": "success"}

        result = test_function()
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_trace_agent_execution_error(self, telemetry):
        """Test tracing agent execution with error"""

        @telemetry.trace_agent_execution("test_agent_error")
        async def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_function()


class TestVectorDBAnalyzer:
    """Tests for Vector Database Analyzer agent"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing"""
        config = {"qdrant_url": "http://localhost:6333", "default_collection": "test_collection"}
        return VectorDBAnalyzer(config)

    @pytest.mark.asyncio
    async def test_analyze_collection_error_handling(self, analyzer):
        """Test error handling in collection analysis"""
        # Mock connection failure
        with patch.object(analyzer, "_connect_to_qdrant", return_value=False):
            result = await analyzer.analyze_collection("test_collection")

        # Should return error
        assert "error" in result
        assert "Failed to connect" in result["error"]

    @pytest.mark.asyncio
    async def test_benchmark_query_performance(self, analyzer):
        """Test query performance benchmarking"""
        with patch.object(analyzer, "_connect_to_qdrant", return_value=True):
            with patch.object(analyzer, "qdrant_client") as mock_client:
                # Setup mock search results
                mock_result = [Mock(score=0.95), Mock(score=0.87)]
                mock_client.search.return_value = mock_result

                result = await analyzer.benchmark_query_performance(
                    "test_collection", "test query", 10
                )

                # Assertions
                assert "collection_name" in result
                assert "performance" in result


class TestDatabaseTroubleshooter:
    """Tests for Database Troubleshooter agent"""

    @pytest.fixture
    def troubleshooter(self):
        """Create troubleshooter instance for testing"""
        config = {
            "postgres_dsn": "postgresql://test:test@localhost:5432/test",
            "monitoring_interval": 60,
            "slow_query_threshold": 1000,
        }
        return DatabaseTroubleshooter(config)

    @pytest.mark.asyncio
    async def test_check_database_health_error_handling(self, troubleshooter):
        """Test error handling in database health check"""
        with patch.object(troubleshooter, "_create_connection_pool", return_value=False):
            result = await troubleshooter.check_database_health()

        # Should return error
        assert "error" in result
        assert "Failed to connect" in result["error"]


class TestPipelineMonitor:
    """Tests for Pipeline Monitor agent"""

    @pytest.fixture
    def monitor(self):
        """Create monitor instance for testing"""
        config = {"health_check_interval": 30, "task_timeout": 3600, "max_concurrent_tasks": 10}
        return PipelineMonitor(config)

    @pytest.mark.asyncio
    async def test_monitor_pipeline_health(self, monitor):
        """Test pipeline health monitoring"""
        result = await monitor.monitor_pipeline_health()

        # Assertions
        assert "health_status" in result
        assert "health_score" in result
        assert "resource_usage" in result


class TestMultiAgentOrchestrator:
    """Tests for Multi-Agent Orchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = {
            "default_mode": "adaptive",
            "max_concurrent_tasks": 4,
            "enable_a2a_communication": True,
            "enable_error_recovery": True,
        }
        return MultiAgentOrchestrator(config)

    @pytest.mark.asyncio
    async def test_run_health_check(self, orchestrator):
        """Test health check workflow"""
        # Mock agent methods
        with patch.object(
            orchestrator.agents["pipeline_monitor"], "monitor_pipeline_health"
        ) as mock_pipeline:
            with patch.object(
                orchestrator.agents["vector_db_analyzer"], "analyze_all_collections"
            ) as mock_vector:
                with patch.object(
                    orchestrator.agents["db_troubleshooter"], "check_database_health"
                ) as mock_db:
                    # Setup mock results
                    mock_pipeline.return_value = {"health_status": "healthy"}
                    mock_vector.return_value = {"qdrant_status": "healthy"}
                    mock_db.return_value = {"database_health": {"connection_status": "healthy"}}

                    result = await orchestrator.run_health_check()

                    # Assertions
                    assert "workflow_id" in result
                    assert "status" in result
                    assert "results" in result


# Pytest configuration
@pytest.fixture(scope="session", autouse=True)
def setup_telemetry():
    """Setup telemetry for all tests"""
    telemetry = get_telemetry(
        service_name="test-suite", enable_console_export=False, enable_otlp_export=False
    )
    yield telemetry
    telemetry.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
