import pytest

from back.config import get_settings
from back.llm.factory import reset_llm_cache


@pytest.fixture(autouse=True)
def _deterministic_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("LLM_AGENT_ENABLED", "false")
    monkeypatch.setenv("LLM_ML_ENABLED", "false")
    get_settings.cache_clear()
    reset_llm_cache()
    yield
    get_settings.cache_clear()
    reset_llm_cache()
