"""
Codex Agent
Specialized agent for safe code generation, explanation, test synthesis and refactoring suggestions.
"""

import asyncio
from datetime import datetime
from typing import Any


class CodexAgent:
    """A lightweight Codex-style agent that provides code generation and explanation utilities.

    Note: This implementation intentionally does not call any remote code execution APIs or run
    generated code. It provides deterministic, testable scaffolding suitable for unit tests and
    integration with the multi-agent orchestrator.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.history: list[dict[str, Any]] = []

    async def generate_code(
        self, prompt: str, language: str = "python", max_tokens: int = 256
    ) -> dict[str, Any]:
        """Generate code for a prompt.

        Returns a dictionary with generated `code` (string) and `metadata`.
        The method simulates generation and is deterministic for tests.
        """
        request_id = f"gen_{datetime.now().timestamp()}"
        await asyncio.sleep(0.01)

        # Deterministic sample generation for tests
        code = f"# Generated {language} code for prompt: {prompt}\n# (Simulated output)\n" + (
            "def generated_function():\n    return 'ok'\n"
        )

        result = {
            "request_id": request_id,
            "language": language,
            "code": code,
            "meta": {"max_tokens": max_tokens, "temperature": self.config.get("temperature", 0.0)},
            "timestamp": datetime.now().isoformat(),
        }

        self.history.append(result)
        return result

    async def explain_code(self, code: str, level: str = "high") -> dict[str, Any]:
        """Return a short explanation of the provided code.

        The explanation is simulated and safe.
        """
        request_id = f"explain_{datetime.now().timestamp()}"
        await asyncio.sleep(0.005)

        explanation = {
            "summary": f"This {level}-level explanation says the code defines a function and returns a constant.",
            "advice": ["Add docstrings", "Add input validation"],
        }

        result = {
            "request_id": request_id,
            "explanation": explanation,
            "timestamp": datetime.now().isoformat(),
        }
        self.history.append(result)
        return result

    async def suggest_tests(self, code: str) -> dict[str, Any]:
        """Suggest unit tests for the given code.

        Returns a dict with `tests` which is a list of suggested test snippets (strings).
        """
        request_id = f"test_{datetime.now().timestamp()}"
        await asyncio.sleep(0.005)

        tests = ["def test_generated_function():\n    assert generated_function() == 'ok'\n"]

        result = {"request_id": request_id, "tests": tests, "timestamp": datetime.now().isoformat()}
        self.history.append(result)
        return result

    async def build_openai_request(
        self,
        prompt: str,
        model: str | None = None,
        functions: list | None = None,
        temperature: float | None = None,
    ) -> dict:
        """Return the kwargs that would be sent to OpenAI for function-calling flow.

        This helper is intentionally non-destructive and does not perform network calls. It is
        designed to be used by tests and by orchestration code that will perform the actual request
        (if allowed by configuration).
        """
        model = model or self.config.get("model", "gpt-4o-mini")
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "functions": functions or OPENAI_FUNCTIONS,
            "temperature": float(
                temperature if temperature is not None else self.config.get("temperature", 0.0)
            ),
        }

    async def call_openai(self, prompt: str, allow_live: bool = False, **kwargs) -> dict:
        """Attempt to call OpenAI if allowed. By default, this method returns the prepared request payload.

        - If `allow_live` is True and the environment contains `OPENAI_API_KEY`, the method will
          attempt to import `openai` and perform a call. If `allow_live` is False (default), the
          method only returns the payload for safe inspection and testing.
        """
        payload = await self.build_openai_request(prompt, **kwargs)

        if not allow_live:
            return {"live": False, "payload": payload}

        # Live call requested — verify environment and availability
        api_key = __import__("os").environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set; cannot perform live OpenAI calls")

        try:
            import openai as _openai
        except Exception as e:
            raise RuntimeError("openai package is not available in the environment") from e

        _openai.api_key = api_key
        # Note: For safety we perform a synchronous call only if explicitly requested.
        # Using ChatCompletion for function calling
        response = _openai.ChatCompletion.create(**payload)
        return {"live": True, "response": response}


# OpenAI-compatible function definitions for tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_code",
            "description": "Generate code for a given prompt and language",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "language": {"type": "string", "default": "python"},
                    "max_tokens": {"type": "integer", "default": 256},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_code",
            "description": "Return a human-readable explanation for supplied code",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "level": {"type": "string", "default": "high"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_tests",
            "description": "Generate suggested unit tests for provided code",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
]

# OpenAI-friendly function list (for function-calling compatibility)
OPENAI_FUNCTIONS = [f["function"] for f in TOOLS]

# Agent metadata
AGENT_INFO = {
    "name": "Codex Agent",
    "description": "Agent providing deterministic code generation, explanation, and test suggestions (no remote execution by default).",
    "version": "0.1.0",
    "capabilities": ["code_generation", "explain_code", "generate_tests"],
    "tools": TOOLS,
    "openai_compatible": True,
    "function_calling": True,
}


# Safe OpenAI helper: builds request payload and optionally performs a live call
async def build_openai_request(
    self,
    prompt: str,
    model: str | None = None,
    functions: list | None = None,
    temperature: float | None = None,
) -> dict:
    """Return the kwargs that would be sent to OpenAI for function-calling flow.

    This helper is intentionally non-destructive and does not perform network calls. It is
    designed to be used by tests and by orchestration code that will perform the actual request
    (if allowed by configuration).
    """
    model = model or self.config.get("model", "gpt-4o-mini")
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "functions": functions or OPENAI_FUNCTIONS,
        "temperature": float(
            temperature if temperature is not None else self.config.get("temperature", 0.0)
        ),
    }


async def call_openai(self, prompt: str, allow_live: bool = False, **kwargs) -> dict:
    """Attempt to call OpenAI if allowed. By default, this method returns the prepared request payload.

    - If `allow_live` is True and the environment contains `OPENAI_API_KEY`, the method will
      attempt to import `openai` and perform a call. If `allow_live` is False (default), the
      method only returns the payload for safe inspection and testing.
    """
    payload = await self.build_openai_request(prompt, **kwargs)

    if not allow_live:
        return {"live": False, "payload": payload}

    # Live call requested — verify environment and availability
    api_key = __import__("os").environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot perform live OpenAI calls")

    try:
        import openai as _openai
    except Exception as e:
        raise RuntimeError("openai package is not available in the environment") from e

    _openai.api_key = api_key
    # Note: For safety we perform a synchronous call only if explicitly requested.
    # Using ChatCompletion for function calling
    response = _openai.ChatCompletion.create(**payload)
    return {"live": True, "response": response}

    async def build_openai_request(
        self,
        prompt: str,
        model: str | None = None,
        functions: list | None = None,
        temperature: float | None = None,
    ) -> dict:
        return await build_openai_request(
            self, prompt, model=model, functions=functions, temperature=temperature
        )

    async def call_openai(self, prompt: str, allow_live: bool = False, **kwargs) -> dict:
        return await call_openai(self, prompt, allow_live=allow_live, **kwargs)


if __name__ == "__main__":
    import asyncio

    agent = CodexAgent()

    async def main():
        gen = await agent.generate_code("Write a function that returns sum of list")
        print(gen["code"])
        expl = await agent.explain_code(gen["code"])
        print(expl["explanation"]["summary"])
        tests = await agent.suggest_tests(gen["code"])
        print(tests["tests"])

    asyncio.run(main())
