
import pytest

from agents.codex_agent import AGENT_INFO, TOOLS, CodexAgent


@pytest.fixture
def agent():
    return CodexAgent(config={"temperature": 0.0})


@pytest.mark.asyncio
async def test_generate_code(agent):
    resp = await agent.generate_code("create a function that returns 1", language="python")
    assert "code" in resp
    assert "request_id" in resp
    assert isinstance(resp["code"], str)


@pytest.mark.asyncio
async def test_explain_code(agent):
    code = "def generated_function():\n    return 'ok'\n"
    resp = await agent.explain_code(code)
    assert "explanation" in resp
    assert "summary" in resp["explanation"]


@pytest.mark.asyncio
async def test_suggest_tests(agent):
    code = "def generated_function():\n    return 'ok'\n"
    resp = await agent.suggest_tests(code)
    assert "tests" in resp
    assert isinstance(resp["tests"], list)
    assert any("test_generated_function" in t or "generated_function" in t for t in resp["tests"])


def test_agent_metadata_present():
    assert AGENT_INFO["name"] == "Codex Agent"
    assert "generate_code" in [t["function"]["name"] for t in TOOLS]
