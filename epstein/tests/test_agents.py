"""Comprehensive tests for multi-agent system with OpenTelemetry instrumentation."""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import agents
from agents.vector_db_analyzer import VectorDBAnalyzer
from agents.db_troubleshooter import DatabaseTroubleshooter
from agents.pipeline_monitor import PipelineMonitor
from agents.multi_agent_orchestrator import MultiAgentOrchestrator
from agents.telemetry import get_telemetry, AgentTelemetry


class TestVectorDBAnalyzer:
    """Tests for Vector Database Analyzer agent"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing"""
        config = {"qdrant_url": "http://localhost:6333", "default_collection": "test_collection"}
        return VectorDBAnalyzer(config)

    @pytest.fixture
    def telemetry(self):
        """Create telemetry instance for testing"""
        return get_telemetry(
            service_name="test-vector-analyzer",
            enable_console_export=False,
            enable_otlp_export=False,
        )

    @pytest.mark.asyncio
    async def test_analyze_collection_success(self, analyzer, telemetry):
        """Test successful collection analysis"""
        # Mock Qdrant client
        with patch.object(analyzer, "_connect_to_qdrant", return_value=True):
            with patch.object(analyzer, "qdrant_client") as mock_client:
                # Setup mock responses
                mock_collection = Mock()
                mock_collection.status = "green"
                mock_collection.config = Mock()
                mock_collection.config.params = Mock()
                mock_collection.config.params.vectors = Mock()

                mock_client.get_collection.return_value = mock_collection

                # Execute with telemetry
                with telemetry.create_span("test_analyze_collection"):
                    result = await analyzer.analyze_collection("test_collection")

                # Assertions
                assert "collection_name" in result
                assert result["collection_name"] == "test_collection"
                assert "status" in result
                assert "analysis_timestamp" in result

    @pytest.mark.asyncio
    async def test_analyze_collection_error_handling(self, analyzer, telemetry):
        """Test error handling in collection analysis"""
        # Mock connection failure
        with patch.object(analyzer, "_connect_to_qdrant", return_value=False):
            with telemetry.create_span("test_analyze_collection_error"):
                result = await analyzer.analyze_collection("test_collection")

            # Should return error
            assert "error" in result
            assert "Failed to connect" in result["error"]

    @pytest.mark.asyncio
    async def test_benchmark_query_performance(self, analyzer, telemetry):
        """Test query performance benchmarking"""
        with patch.object(analyzer, "_connect_to_qdrant", return_value=True):
            with patch.object(analyzer, "qdrant_client") as mock_client:
                # Setup mock search results
                mock_result = [Mock(score=0.95), Mock(score=0.87)]
                mock_client.search.return_value = mock_result

                # Execute with telemetry
                with telemetry.create_span("test_benchmark_performance"):
                    result = await analyzer.benchmark_query_performance(
                        "test_collection", "test query", 10
                    )

                # Assertions
                assert "collection_name" in result
                assert "performance" in result
                assert "execution_time_ms" in result["performance"]
                assert "results_count" in result["performance"]

    @pytest.mark.asyncio
    async def test_optimize_collection(self, analyzer, telemetry):
        """Test collection optimization recommendations"""
        with patch.object(analyzer, "analyze_collection") as mock_analyze:
            # Setup mock analysis result
            mock_analyze.return_value = {
                "collection_name": "test_collection",
                "vectors_count": 150000,
                "config_analysis": {"vector_size": 1536},
                "issues_detected": [],
            }

            # Execute with telemetry
            with telemetry.create_span("test_optimize_collection"):
                result = await analyzer.optimize_collection("test_collection")

            # Assertions
            assert "collection_name" in result
            assert "optimization_recommendations" in result
            assert "estimated_improvement" in result


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

    @pytest.fixture
    def telemetry(self):
        """Create telemetry instance for testing"""
        return get_telemetry(
            service_name="test-db-troubleshooter",
            enable_console_export=False,
            enable_otlp_export=False,
        )

    @pytest.mark.asyncio
    async def test_check_database_health_success(self, troubleshooter, telemetry):
        """Test successful database health check"""
        with patch.object(troubleshooter, "_create_connection_pool", return_value=True):
            with patch.object(troubleshooter, "db_pool") as mock_pool:
                # Setup mock connection and cursor
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchone.return_value = {
                    "active_connections": 5,
                    "idle_connections": 3,
                    "blocked_queries": 0,
                    "slow_queries": 2,
                }
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
                mock_pool.getconn.return_value.__enter__.return_value = mock_conn

                # Execute with telemetry
                with telemetry.create_span("test_check_database_health"):
                    result = await troubleshooter.check_database_health()

                # Assertions
                assert "database_health" in result
                assert "health_score" in result
                assert "recommendations" in result
                assert result["database_health"]["active_connections"] == 5

    @pytest.mark.asyncio
    async def test_check_indexes(self, troubleshooter, telemetry):
        """Test index analysis"""
        with patch.object(troubleshooter, "_create_connection_pool", return_value=True):
            with patch.object(troubleshooter, "db_pool") as mock_pool:
                # Setup mock connection and cursor
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [
                    {
                        "schemaname": "public",
                        "tablename": "documents",
                        "indexname": "idx_documents_id",
                        "indexdef": "CREATE INDEX...",
                        "size": "10 MB",
                        "idx_scan": 1000,
                        "idx_tup_read": 5000,
                        "idx_tup_fetch": 4500,
                        "efficiency": 90.0,
                        "usage_status": "frequently_used",
                    }
                ]
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
                mock_pool.getconn.return_value.__enter__.return_value = mock_conn

                # Execute with telemetry
                with telemetry.create_span("test_check_indexes"):
                    result = await troubleshooter.check_indexes()

                # Assertions
                assert "indexes" in result
                assert "recommendations" in result
                assert "total_indexes" in result
                assert len(result["indexes"]) > 0

    @pytest.mark.asyncio
    async def test_optimize_database(self, troubleshooter, telemetry):
        """Test comprehensive database optimization"""
        with patch.object(troubleshooter, "check_database_health") as mock_health:
            with patch.object(troubleshooter, "check_indexes") as mock_indexes:
                with patch.object(troubleshooter, "check_table_statistics") as mock_tables:
                    with patch.object(troubleshooter, "analyze_query_performance") as mock_queries:
                        # Setup mock results
                        mock_health.return_value = {
                            "database_health": {"connection_status": "healthy"}
                        }
                        mock_indexes.return_value = {"indexes": [], "recommendations": []}
                        mock_tables.return_value = {"tables": [], "maintenance_needed": []}
                        mock_queries.return_value = {"slow_queries": [], "recommendations": []}

                        # Execute with telemetry
                        with telemetry.create_span("test_optimize_database"):
                            result = await troubleshooter.optimize_database()

                        # Assertions
                        assert "database_health" in result
                        assert "index_analysis" in result
                        assert "table_statistics" in result
                        assert "query_performance" in result
                        assert "optimization_plan" in result


class TestPipelineMonitor:
    """Tests for Pipeline Monitor agent"""

    @pytest.fixture
    def monitor(self):
        """Create monitor instance for testing"""
        config = {"health_check_interval": 30, "task_timeout": 3600, "max_concurrent_tasks": 10}
        return PipelineMonitor(config)

    @pytest.fixture
    def telemetry(self):
        """Create telemetry instance for testing"""
        return get_telemetry(
            service_name="test-pipeline-monitor",
            enable_console_export=False,
            enable_otlp_export=False,
        )

    @pytest.mark.asyncio
    async def test_monitor_pipeline_health(self, monitor, telemetry):
        """Test pipeline health monitoring"""
        # Execute with telemetry
        with telemetry.create_span("test_monitor_pipeline_health"):
            result = await monitor.monitor_pipeline_health()

        # Assertions
        assert "health_status" in result
        assert "health_score" in result
        assert "resource_usage" in result
        assert "task_analysis" in result
        assert "recommendations" in result
        assert "metrics" in result

    @pytest.mark.asyncio
    async def test_monitor_task_execution(self, monitor, telemetry):
        """Test task execution monitoring"""
        # Execute with telemetry
        with telemetry.create_span("test_monitor_task_execution"):
            result = await monitor.monitor_task_execution("task_001", "Test Task")

        # Assertions
        assert "task_id" in result
        assert result["task_id"] == "task_001"
        assert "task_name" in result
        assert "status" in result
        assert "progress" in result

    @pytest.mark.asyncio
    async def test_analyze_performance_trends(self, monitor, telemetry):
        """Test performance trend analysis"""
        # Add some health history first
        for i in range(10):
            await monitor.monitor_pipeline_health()

        # Execute with telemetry
        with telemetry.create_span("test_analyze_performance_trends"):
            result = await monitor.analyze_performance_trends()

        # Assertions
        assert "trends" in result
        assert "anomalies" in result
        assert "recommendations" in result


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

    @pytest.fixture
    def telemetry(self):
        """Create telemetry instance for testing"""
        return get_telemetry(
            service_name="test-orchestrator", enable_console_export=False, enable_otlp_export=False
        )

    @pytest.mark.asyncio
    async def test_run_comprehensive_analysis(self, orchestrator, telemetry):
        """Test comprehensive analysis orchestration"""
        # Mock agent methods
        with patch.object(
            orchestrator.agents["vector_db_analyzer"], "analyze_all_collections"
        ) as mock_vector:
            with patch.object(
                orchestrator.agents["db_troubleshooter"], "optimize_database"
            ) as mock_db:
                with patch.object(
                    orchestrator.agents["pipeline_monitor"], "monitor_pipeline_health"
                ) as mock_pipeline:
                    # Setup mock results
                    mock_vector.return_value = {"qdrant_status": "healthy", "collections": {}}
                    mock_db.return_value = {"database_health": {"connection_status": "healthy"}}
                    mock_pipeline.return_value = {"health_status": "healthy"}

                    # Execute with telemetry
                    with telemetry.create_span("test_comprehensive_analysis"):
                        result = await orchestrator.run_comprehensive_analysis()

                    # Assertions
                    assert "task_id" in result
                    assert "status" in result
                    assert "results" in result
                    assert "report" in result

    @pytest.mark.asyncio
    async def test_run_troubleshooting_workflow(self, orchestrator, telemetry):
        """Test troubleshooting workflow"""
        # Mock agent methods
        with patch.object(
            orchestrator.agents["db_troubleshooter"], "check_database_health"
        ) as mock_health:
            mock_health.return_value = {"database_health": {"connection_status": "healthy"}}

            # Execute with telemetry
            with telemetry.create_span("test_troubleshooting_workflow"):
                result = await orchestrator.run_troubleshooting_workflow("database")

            # Assertions
            assert "workflow_id" in result
            assert "issue_type" in result
            assert result["issue_type"] == "database"
            assert "status" in result
            assert "results" in result

    @pytest.mark.asyncio
    async def test_run_health_check(self, orchestrator, telemetry):
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

                    # Execute with telemetry
                    with telemetry.create_span("test_health_check"):
                        result = await orchestrator.run_health_check()

                    # Assertions
                    assert "workflow_id" in result
                    assert "status" in result
                    assert "results" in result
                    assert "health_assessment" in result
                    assert "overall_status" in result

    def test_get_agent_status(self, orchestrator, telemetry):
        """Test agent status retrieval"""
        # Execute with telemetry
        with telemetry.create_span("test_get_agent_status"):
            result = orchestrator.get_agent_status()

        # Assertions
        assert isinstance(result, dict)
        assert len(result) > 0
        for agent_name, status in result.items():
            assert "status" in status
            assert "capabilities" in status or "tools" in status


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
        assert telemetry.agent_execution_counter is not None
        assert telemetry.agent_error_counter is not None
        assert telemetry.agent_duration_histogram is not None

    @pytest.mark.asyncio
    async def test_trace_agent_execution_async(self, telemetry):
        """Test tracing async agent execution"""

        @telemetry.trace_agent_execution("test_agent")
        async def test_function():
            await asyncio.sleep(0.1)
            return {"status": "success"}

        result = await test_function()

        assert result["status"] == "success"
        assert "test_agent" in telemetry.agent_metrics
        assert telemetry.agent_metrics["test_agent"]["status"] == "completed"

    def test_trace_agent_execution_sync(self, telemetry):
        """Test tracing sync agent execution"""

        @telemetry.trace_agent_execution("test_agent_sync")
        def test_function():
            return {"status": "success"}

        result = test_function()

        assert result["status"] == "success"
        assert "test_agent_sync" in telemetry.agent_metrics
        assert telemetry.agent_metrics["test_agent_sync"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_trace_agent_execution_error(self, telemetry):
        """Test tracing agent execution with error"""

        @telemetry.trace_agent_execution("test_agent_error")
        async def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_function()

        assert "test_agent_error" in telemetry.agent_metrics
        assert telemetry.agent_metrics["test_agent_error"]["status"] == "failed"
        assert "error" in telemetry.agent_metrics["test_agent_error"]

    def test_create_span(self, telemetry):
        """Test custom span creation"""
        with telemetry.create_span("test_span", {"test.attribute": "value"}):
            # Span should be active
            pass

        # Span should be closed after context exit

    def test_get_agent_metrics(self, telemetry):
        """Test agent metrics retrieval"""
        metrics = telemetry.get_agent_metrics()

        assert "agents" in metrics
        assert "timestamp" in metrics
        assert isinstance(metrics["agents"], dict)


class TestIntegration:
    """Integration tests for multi-agent system"""

    @pytest.fixture
    def telemetry(self):
        """Create telemetry instance for testing"""
        return get_telemetry(
            service_name="test-integration", enable_console_export=False, enable_otlp_export=False
        )

    @pytest.mark.asyncio
    async def test_end_to_end_analysis_workflow(self, telemetry):
        """Test end-to-end analysis workflow with telemetry"""
        # Create orchestrator
        orchestrator = MultiAgentOrchestrator()

        # Mock all agent methods
        with patch.object(
            orchestrator.agents["vector_db_analyzer"], "analyze_all_collections"
        ) as mock_vector:
            with patch.object(
                orchestrator.agents["db_troubleshooter"], "optimize_database"
            ) as mock_db:
                with patch.object(
                    orchestrator.agents["pipeline_monitor"], "monitor_pipeline_health"
                ) as mock_pipeline:
                    # Setup mock results
                    mock_vector.return_value = {
                        "qdrant_status": "healthy",
                        "total_collections": 1,
                        "total_vectors": 1000,
                        "collections": {"test_collection": {"status": "green"}},
                    }
                    mock_db.return_value = {
                        "database_health": {"connection_status": "healthy"},
                        "optimization_plan": {"immediate_actions": []},
                    }
                    mock_pipeline.return_value = {"health_status": "healthy", "health_score": 95.0}

                    # Execute workflow with telemetry
                    with telemetry.create_span("test_end_to_end_workflow"):
                        result = await orchestrator.run_comprehensive_analysis()

                    # Verify results
                    assert result["status"] == "completed"
                    assert "results" in result
                    assert "report" in result

                    # Verify telemetry captured metrics
                    metrics = telemetry.get_agent_metrics()
                    assert len(metrics["agents"]) > 0


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
