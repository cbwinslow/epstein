# AI Agents - README

**Purpose**: Guide for working with AI agents in the Epstein document analysis system  
**Version**: 1.0  
**Last Updated**: 2025-12-31

## Overview

This directory contains AI agent implementations for automating document analysis tasks. Agents are specialized AI systems that can:

- Extract and analyze entities from documents
- Discover relationships between entities
- Build knowledge graphs
- Verify facts and check consistency
- Generate analysis reports
- Coordinate with other agents for complex tasks

## Current Agents

### Core Agents (Implemented)

1. **`epstein_data_processor.py`**
   - Primary data processing agent
   - Handles OCR, text extraction, NER
   - Generates embeddings
   - Integrates with vector database

2. **`document_analysis_agent.py`**
   - Document understanding and summarization
   - Key information extraction
   - Document classification

3. **`entity_extraction_agent.py`**
   - Named entity recognition
   - Entity disambiguation
   - Entity relationship extraction

4. **`vector_db_analyzer.py`**
   - Vector database operations
   - Semantic search
   - Similarity analysis

5. **`multi_agent_orchestrator.py`**
   - Coordinates multiple agents
   - Task distribution
   - Result aggregation

6. **`govinfo_downloader.py`**
   - Government data collection
   - Document downloading
   - Source management

7. **`pipeline_monitor.py`**
   - Pipeline health monitoring
   - Performance tracking
   - Alert generation

8. **`db_troubleshooter.py`**
   - Database diagnostics
   - Issue detection and resolution
   - Performance optimization

9. **`codex_agent.py`**
   - Code generation (deterministic, no remote execution)
   - Code explanation and advice
   - Test and lint suggestion
   - Useful for generating reproducible code scaffolding for the pipeline

### Planned Agents (Roadmap)

1. **Relationship Discovery Agent**
   - Find connections between entities
   - Build relationship networks
   - Calculate relationship strength

2. **Timeline Analysis Agent**
   - Reconstruct chronological timelines
   - Find temporal patterns
   - Validate date consistency

3. **Pattern Detection Agent**
   - Identify recurring patterns
   - Detect anomalies
   - Find suspicious behaviors

4. **Verification Agent**
   - Fact-check claims
   - Cross-reference sources
   - Assess evidence quality

5. **Conversation Linker Agent**
   - Connect email threads
   - Link communications across documents
   - Reconstruct conversation flows

6. **Flight Analysis Agent**
   - Parse flight manifests
   - Analyze travel patterns
   - Find co-travelers

## Agent Architecture

### Base Agent Pattern

```python
class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.tools = self._register_tools()
        self.memory = AgentMemory()
    
    async def execute(self, task: Task) -> Result:
        """Execute agent task"""
        pass
    
    def _register_tools(self) -> List[Tool]:
        """Register agent tools"""
        pass
```

### Agent Components

1. **Configuration**: Agent-specific settings and parameters
2. **Tools**: Functions the agent can use
3. **Memory**: Short-term and long-term memory
4. **Communication**: Inter-agent messaging
5. **Logging**: Comprehensive activity logs

### Agent Communication

Agents communicate via:
- **Message Passing**: Direct async messages
- **Shared State**: Coordinated state management
- **Event Bus**: Pub/sub for loose coupling
- **MCP Protocol**: Standardized tool calling

## Using Agents

### Example 1: Single Agent

```python
from agents.entity_extraction_agent import EntityExtractionAgent

# Initialize agent
agent = EntityExtractionAgent(config={
    'model': 'en_core_web_trf',
    'confidence_threshold': 0.85
})

# Process document
result = await agent.extract_entities(
    document_id='DOJ_DS01_F123',
    text=document_text
)

# Access results
entities = result.entities
relationships = result.relationships
```

### Example 2: Multi-Agent Coordination

```python
from agents.multi_agent_orchestrator import MultiAgentOrchestrator

# Initialize orchestrator
orchestrator = MultiAgentOrchestrator()

# Coordinate comprehensive analysis
result = await orchestrator.coordinate_comprehensive_analysis(
    collection_name="epstein_documents",
    query_text="Jeffrey Epstein financial transactions"
)

# Results include outputs from all agents
print(result['vector_analysis'])
print(result['entity_extraction'])
print(result['relationship_discovery'])
```

### Example 3: Using PydanticAI Framework

```python
from pydantic_ai import Agent
from agents.tools import knowledge_graph_tools

# Create agent with tools
agent = Agent(
    model='openai:gpt-4',
    system_prompt='''You are an expert document analyst.
    Use the available tools to analyze Epstein documents.''',
    tools=[
        knowledge_graph_tools.find_connections,
        knowledge_graph_tools.search_entities,
        knowledge_graph_tools.build_timeline
    ]
)

# Run agent
result = await agent.run(
    "Find all connections between Person A and Person B"
)
```

## Agent Configuration

### Configuration File Format

```yaml
# agents/config/agent_config.yaml
agents:
  entity_extraction:
    model: "en_core_web_trf"
    confidence_threshold: 0.85
    batch_size: 32
    enable_disambiguation: true
  
  relationship_discovery:
    max_distance: 6
    min_confidence: 0.75
    enable_inference: true
  
  verification:
    require_multiple_sources: true
    min_sources: 2
    cross_reference_enabled: true
```

### Environment Variables

```bash
# Agent configuration
AGENT_LOG_LEVEL=INFO
AGENT_TIMEOUT=300
AGENT_MAX_RETRIES=3

# Model configuration
NER_MODEL=en_core_web_trf
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Database connections
POSTGRES_DSN=postgresql://...
NEO4J_URI=bolt://localhost:7687
QDRANT_URL=http://localhost:6333

# API keys (if needed)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
```

## Developing New Agents

### Step 1: Create Agent Class

```python
# agents/my_new_agent.py
from agents.core.base_agent import BaseAgent
from typing import Dict, Any

class MyNewAgent(BaseAgent):
    """Agent description"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize agent-specific components
    
    async def process(self, input_data: Dict) -> Dict:
        """Main processing method"""
        # Agent logic here
        return results
```

### Step 2: Register Tools

```python
def _register_tools(self) -> List[Tool]:
    """Register agent tools"""
    return [
        Tool(
            name="my_tool",
            description="Tool description",
            function=self.my_tool_function,
            parameters=tool_parameters
        )
    ]
```

### Step 3: Add Tests

```python
# tests/test_my_new_agent.py
import pytest
from agents.my_new_agent import MyNewAgent

@pytest.mark.asyncio
async def test_agent_process():
    agent = MyNewAgent(config={})
    result = await agent.process(test_data)
    assert result['status'] == 'success'
```

### Step 4: Add Documentation

```markdown
# agents/docs/my_new_agent.md

## MyNewAgent

Purpose: [Description]

### Capabilities
- Capability 1
- Capability 2

### Usage
[Examples]

### Configuration
[Config options]
```

## Best Practices

### 1. Error Handling

```python
try:
    result = await agent.process(data)
except AgentError as e:
    logger.error(f"Agent error: {e}")
    # Handle error gracefully
    result = await agent.retry(data)
```

### 2. Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Agent started processing")
logger.debug(f"Processing document: {doc_id}")
logger.warning("Low confidence detected")
logger.error("Processing failed")
```

### 3. Resource Management

```python
async with agent.session() as session:
    result = await session.process(data)
    # Session automatically cleaned up
```

### 4. Performance Optimization

```python
# Batch processing
results = await agent.process_batch(documents)

# Caching
@cached(ttl=3600)
async def get_entities(doc_id):
    return await agent.extract_entities(doc_id)

# Parallel execution
tasks = [agent.process(doc) for doc in documents]
results = await asyncio.gather(*tasks)
```

### 5. Testing

```python
# Unit tests
def test_agent_initialization():
    agent = MyAgent(config)
    assert agent.is_ready()

# Integration tests
@pytest.mark.integration
async def test_agent_with_database():
    agent = MyAgent(config)
    result = await agent.process_with_db(data)
    assert result in database
```

## MCP Server Integration

Agents can be exposed as MCP servers:

```python
# mcp_servers/my_agent/server.py
from mcp import MCPServer
from agents.my_new_agent import MyNewAgent

class MyAgentMCP(MCPServer):
    def __init__(self):
        super().__init__()
        self.agent = MyNewAgent(config)
    
    @mcp_tool
    async def process_document(self, doc_id: str) -> dict:
        """Process document with agent"""
        return await self.agent.process({'doc_id': doc_id})
```

## Monitoring and Observability

### Metrics

```python
from prometheus_client import Counter, Histogram

# Define metrics
agent_requests = Counter(
    'agent_requests_total',
    'Total agent requests',
    ['agent_name', 'status']
)

agent_duration = Histogram(
    'agent_duration_seconds',
    'Agent processing duration',
    ['agent_name']
)

# Use in agent
@agent_duration.labels(agent_name='entity_extraction').time()
async def process(self, data):
    result = await self._process(data)
    agent_requests.labels(
        agent_name='entity_extraction',
        status='success'
    ).inc()
    return result
```

### Health Checks

```python
class AgentHealthCheck:
    async def check_health(self) -> Dict[str, bool]:
        return {
            'database_connected': await self.check_db(),
            'model_loaded': self.model is not None,
            'tools_available': all(t.is_ready() for t in self.tools)
        }
```

## Troubleshooting

### Common Issues

1. **Agent Timeout**
   - Increase timeout in config
   - Check for blocking operations
   - Enable async processing

2. **Memory Issues**
   - Use batch processing
   - Clear cache periodically
   - Monitor memory usage

3. **Model Loading Failures**
   - Verify model path
   - Check model compatibility
   - Review error logs

4. **Tool Errors**
   - Validate tool registration
   - Check tool dependencies
   - Review tool permissions

### Debug Mode

```python
# Enable debug logging
agent = MyAgent(config={'log_level': 'DEBUG'})

# Enable profiling
agent.enable_profiling()

# Inspect agent state
print(agent.get_state())
```

## Resources

### Documentation
- [Agent Development Guide](../docs/AGENT_DEVELOPMENT.md)
- [MCP Server Guide](../docs/MCP_SERVER_SETUP.md)
- [API Documentation](../docs/API.md)

### Examples
- [Multi-Agent Example](../examples/multi_agent_usage_example.py)
- [PydanticAI Example](../examples/pydantic_downloader_agent.py)

### Tools
- Agent monitoring dashboard: http://localhost:9090
- MCP server endpoints: http://localhost:8765
- Logs: `logs/agents/`

## Contributing

### Adding a New Agent

1. Create agent file in `agents/`
2. Implement required methods
3. Add configuration in `agents/config/`
4. Write tests in `tests/`
5. Add documentation
6. Submit PR with agent description

### Code Review Checklist

- [ ] Agent follows base agent pattern
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Tests written and passing
- [ ] Documentation complete
- [ ] Configuration examples provided
- [ ] Performance considered
- [ ] Security reviewed

## Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory

---

**Version**: 1.0  
**Maintainer**: Epstein Project Team  
**Last Updated**: 2025-12-31
