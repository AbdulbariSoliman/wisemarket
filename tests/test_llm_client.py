"""LLM client: current Groq models, reasoning headroom, empty answers trigger the fallback."""
from types import SimpleNamespace

import pytest

from backend.services import llm_client as llm


def _fake_completion(content, seen):
    def completion(**kwargs):
        seen.append(kwargs)
        msg = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    return completion


def test_default_models_are_not_the_shut_down_llama_models():
    for model in (llm.INTENT_MODEL, llm.REFINER_MODEL, llm.FALLBACK_MODEL):
        assert "llama-3.1-8b-instant" not in model and "llama-3.3-70b-versatile" not in model


def test_reasoning_models_get_headroom_and_low_effort(monkeypatch):
    seen = []
    monkeypatch.setattr(llm.litellm, "completion", _fake_completion("ok", seen))
    assert llm._call("groq/openai/gpt-oss-20b", [], max_tokens=20) == "ok"
    assert seen[0]["max_tokens"] == 20 + llm.REASONING_HEADROOM
    assert seen[0]["extra_body"] == {"reasoning_effort": "low"}


def test_empty_answer_raises_so_the_fallback_runs(monkeypatch):
    monkeypatch.setattr(llm.litellm, "completion", _fake_completion("", []))
    with pytest.raises(RuntimeError):
        llm._call("groq/openai/gpt-oss-120b", [], max_tokens=20)
