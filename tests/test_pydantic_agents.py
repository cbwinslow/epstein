"""
Integration tests for MCP Server with PydanticAI agents

Tests the integration between PydanticAI agents and the MCP server
"""

from unittest.mock import Mock, patch

import pytest

# Only run if pydantic-ai is installed
pydantic_ai = pytest.importorskip("pydantic_ai", reason="pydantic-ai not installed")

from pydantic import BaseModel
from pydantic_ai import Agent


class TestPydanticAIIntegration:
    """Test PydanticAI integration with MCP server"""

    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test creating a basic agent"""
        agent = Agent(
            model='test',
            system_prompt='You are a test agent'
        )
        assert agent is not None

    @pytest.mark.asyncio
    async def test_agent_with_tools(self):
        """Test agent with custom tools"""
        agent = Agent(
            model='test',
            system_prompt='You are a document retrieval agent'
        )

        @agent.tool
        def list_collections() -> list:
            """List available collections"""
            return ['collection1', 'collection2']

        # Verify tool is registered
        assert len(agent._tools) > 0

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_agent_mcp_integration(self, mock_get):
        """Test agent calling MCP server endpoints"""
        # Mock MCP server response
        mock_response = Mock()
        mock_response.json.return_value = [
            {'collection_id': 'test', 'name': 'Test Collection'}
        ]
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        agent = Agent(
            model='test',
            system_prompt='You are a document retrieval agent'
        )

        @agent.tool
        def list_collections() -> list:
            """List available document collections"""
            import requests
            response = requests.get('http://localhost:8765/collections')
            return response.json()

        # Test tool works
        result = list_collections()
        assert isinstance(result, list)
        assert len(result) > 0


class TestDownloadAgent:
    """Test document download agent"""

    def test_download_request_model(self):
        """Test DownloadRequest Pydantic model"""
        class DownloadRequest(BaseModel):
            collection_id: str
            destination: str

        request = DownloadRequest(
            collection_id='test_collection',
            destination='/tmp/downloads'
        )

        assert request.collection_id == 'test_collection'
        assert request.destination == '/tmp/downloads'

    @pytest.mark.asyncio
    @patch('requests.post')
    async def test_download_agent_tool(self, mock_post):
        """Test download agent tool execution"""
        # Mock download response
        mock_response = Mock()
        mock_response.json.return_value = {
            'task_id': 'test-task-123',
            'status': 'queued'
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        class DownloadRequest(BaseModel):
            collection_id: str
            destination: str

        agent = Agent(
            model='test',
            system_prompt='Download agent'
        )

        @agent.tool
        def download_collection(request: DownloadRequest) -> dict:
            """Download a collection"""
            import requests
            response = requests.post(
                'http://localhost:8765/download/bulk',
                json=request.model_dump()
            )
            return response.json()

        # Test download tool
        request = DownloadRequest(
            collection_id='test',
            destination='/tmp/test'
        )
        result = download_collection(request)

        assert 'task_id' in result
        assert result['status'] == 'queued'


class TestAgentWorkflows:
    """Test complete agent workflows"""

    @pytest.mark.asyncio
    @patch('requests.get')
    @patch('requests.post')
    async def test_discovery_and_download_workflow(self, mock_post, mock_get):
        """Test complete workflow: discover -> list -> download"""
        # Mock collection list
        mock_get_resp = Mock()
        mock_get_resp.json.return_value = [
            {
                'collection_id': 'doj_releases',
                'name': 'DOJ Releases',
                'document_count': 100
            }
        ]
        mock_get_resp.status_code = 200
        mock_get.return_value = mock_get_resp

        # Mock download response
        mock_post_resp = Mock()
        mock_post_resp.json.return_value = {
            'task_id': 'workflow-test',
            'status': 'queued'
        }
        mock_post_resp.status_code = 200
        mock_post.return_value = mock_post_resp

        # Create workflow agent
        agent = Agent(
            model='test',
            system_prompt='Workflow agent'
        )

        @agent.tool
        def discover_collections() -> list:
            """Discover collections"""
            import requests
            return requests.get('http://localhost:8765/collections').json()

        @agent.tool
        def initiate_download(collection_id: str) -> dict:
            """Start download"""
            import requests
            return requests.post(
                'http://localhost:8765/download/bulk',
                json={'collection_id': collection_id}
            ).json()

        # Execute workflow
        collections = discover_collections()
        assert len(collections) > 0

        result = initiate_download(collections[0]['collection_id'])
        assert 'task_id' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
