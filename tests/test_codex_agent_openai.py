import pytest
import os
import asyncio

from agents.codex_agent import CodexAgent, OPENAI_FUNCTIONS


@pytest.mark.asyncio
async def test_build_openai_request_contains_functions():
    agent = CodexAgent(config={"temperature": 0.0})
    payload = await agent.build_openai_request("Create a function to add numbers")
    assert "functions" in payload
    assert isinstance(payload["functions"], list)
    # Ensure our function schema includes generate_code
    assert any(f["name"] == "generate_code" for f in payload["functions"])


@pytest.mark.asyncio
async def test_call_openai_returns_payload_when_live_not_allowed():
    agent = CodexAgent(config={"temperature": 0.0})
    result = await agent.call_openai("Make a sum function", allow_live=False)
    assert result["live"] is False
    assert "payload" in result


@pytest.mark.asyncio
async def test_call_openai_requires_api_key_for_live():
    # Ensure OPENAI_API_KEY is unset for this test
    os.environ.pop("OPENAI_API_KEY", None)
    agent = CodexAgent(config={"temperature": 0.0})
    with pytest.raises(RuntimeError):
        await agent.call_openai("Make a sum function", allow_live=True)
