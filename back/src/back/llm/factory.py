import logging
from functools import lru_cache

from back.config import get_settings
from back.llm.base import BaseLLM
from back.llm.openai_compatible import OpenAICompatibleLLM
from back.llm.stub import StubLLM

logger = logging.getLogger(__name__)


@lru_cache
def get_llm() -> BaseLLM:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "openai":
        return OpenAICompatibleLLM(settings)
    if provider != "stub":
        logger.warning("Unknown LLM_PROVIDER=%s, falling back to stub", provider)
    return StubLLM()


def reset_llm_cache() -> None:
    get_llm.cache_clear()
