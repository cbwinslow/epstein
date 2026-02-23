# Multi-Agent System Testing Guide

This directory contains comprehensive tests for the Epstein Multi-Agent Analysis System with OpenTelemetry instrumentation.

## Test Structure

```
tests/
├── test_agents.py              # Core agent tests
├── test_telemetry.py           # OpenTelemetry instrumentation tests
├── test_integration.py         # Integration tests
├── run_tests.py                # Test runner with telemetry
├── requirements.txt            # Testing dependencies
└── README.md                   # This file
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
python tests/run_tests.py

# Or use pytest directly
pytest tests/ -v
```

### With Coverage

```bash
# Run tests with coverage report
pytest tests/ --cov=agents --cov=tools --cov-report=html

# View coverage report
open htmlcov/index.html
```

### With OpenTelemetry

```bash
# Run tests with telemetry tracking
python tests/run_tests.py

# This will:
# - Track all test executions
# - Measure test performance
# - Generate telemetry metrics
# - Save metrics to JSON file
```

## Test Categories

### 1. Unit Tests (`test_agents.py`)

Tests individual agent functionality:

- **VectorDBAnalyzer**: Collection analysis, performance benchmarking, optimization
- **DatabaseTroubleshooter**: Health checks, index analysis, query optimization
- **PipelineMonitor**: Health monitoring, performance trends, anomaly detection
- **MultiAgentOrchestrator**: Task coordination, workflow execution, result aggregation

### 2. Telemetry Tests (`test_telemetry.py`)

Tests OpenTelemetry instrumentation:

- Span creation and management
- Metric recording and export
- Error tracking and reporting
- Performance measurement

### 3. Integration Tests (`test_integration.py`)

Tests end-to-end workflows:

- Comprehensive analysis workflow
- Troubleshooting workflows
- Performance optimization workflows
- Multi-agent coordination

## Test Configuration

### Environment Variables

```bash
# Database configuration
export POSTGRES_DSN="postgresql://test:test@localhost:5432/test_db"
export QDRANT_URL="http://localhost:6333"

# Telemetry configuration
export OTEL_SERVICE_NAME="epstein-test-suite"
export OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"
export OTEL_TRACES_EXPORTER="console,otlp"
export OTEL_METRICS_EXPORTER="console,otlp"
```

### Test Database Setup

```bash
# Start test databases with Docker
docker-compose -f tests/docker-compose.test.yml up -d

# Run migrations
python db/migrate.py

# Seed test data
python tests/seed_test_data.py
```

## Writing New Tests

### Basic Test Structure

```python
import pytest
from agents.telemetry import get_telemetry

class TestMyAgent:
    @pytest.fixture
    def agent(self):
        return MyAgent(config={})
    
    @pytest.fixture
    def telemetry(self):
        return get_telemetry(
            service_name="test-my-agent",
            enable_console_export=False
        )
    
    @pytest.mark.asyncio
    async def test_my_method(self, agent, telemetry):
        with telemetry.create_span("test_my_method"):
            result = await agent.my_method()
            assert result["status"] == "success"
```

### Testing with Mocks

```python
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_with_mocks(self, agent, telemetry):
    with patch.object(agent, 'external_service') as mock_service:
        mock_service.return_value = {"data": "test"}
        
        with telemetry.create_span("test_with_mocks"):
            result = await agent.process()
            assert result["data"] == "test"
```

## Test Metrics

The test suite tracks the following metrics:

- **Test Execution Count**: Number of tests executed
- **Test Duration**: Time taken for each test
- **Test Success Rate**: Percentage of passing tests
- **Agent Performance**: Performance metrics for each agent
- **Error Rates**: Frequency and types of errors
- **Resource Usage**: CPU, memory, and disk usage during tests

## Continuous Integration

### GitHub Actions

Tests are automatically run on:
- Pull requests
- Pushes to main branch
- Scheduled daily runs

### Test Reports

Test reports are generated in multiple formats:
- **HTML**: `htmlcov/index.html` - Interactive coverage report
- **JSON**: `coverage.json` - Machine-readable coverage data
- **Terminal**: Console output with summary
- **Telemetry**: `test_metrics_*.json` - OpenTelemetry metrics

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure parent directory is in Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Database Connection Errors**
   ```bash
   # Check database services are running
   docker-compose ps
   
   # Verify connection strings
   psql $POSTGRES_DSN -c "SELECT 1"
   ```

3. **Qdrant Connection Errors**
   ```bash
   # Check Qdrant is running
   curl http://localhost:6333/collections
   ```

### Debug Mode

```bash
# Run tests with debug logging
pytest tests/ -v --log-cli-level=DEBUG

# Run specific test
pytest tests/test_agents.py::TestVectorDBAnalyzer::test_analyze_collection_success -v

# Run with pdb debugger
pytest tests/ --pdb
```

## Performance Benchmarks

Expected test performance:

- **Unit Tests**: < 5 seconds total
- **Integration Tests**: < 30 seconds total
- **Full Test Suite**: < 60 seconds total

If tests are slower, check:
- Database connection latency
- Mock configuration
- Resource availability

## Coverage Goals

Target coverage levels:

- **Overall**: > 80%
- **Critical Paths**: > 95%
- **Error Handling**: > 90%
- **Agent Methods**: > 85%

## Contributing

When adding new tests:

1. Follow existing test structure
2. Use appropriate fixtures
3. Add telemetry spans for tracking
4. Include both success and error cases
5. Update this README with new test categories

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
