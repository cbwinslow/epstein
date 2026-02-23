import pytest

from integrations.lang.langchain_adapter import LangChainAdapter


def test_langchain_adapter_run_monkeypatched(monkeypatch):
    # Monkeypatch a minimal langchain module
    class Dummy:
        pass

    monkeypatch.setitem(__import__("sys").modules, "langchain", Dummy())

    a = LangChainAdapter(model="test")
    res = a.run("Hello", {"k": "v"})
    assert res["model"] == "test"
    assert res["prompt"] == "Hello"
    assert "Echo: Hello" in res["result"]


def test_langchain_adapter_missing():
    # Ensure adapter errors when langchain is not installed
    import sys
    sys.modules.pop("langchain", None)
    a = LangChainAdapter()
    with pytest.raises(RuntimeError):
        a.run("hi")
