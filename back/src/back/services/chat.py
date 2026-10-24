import logging
from collections.abc import AsyncIterator
from typing import Any

from back.config import get_settings
from back.db.models import BusinessCategory, BusinessProfile, Counterparty, NewsEvent
from back.llm.factory import get_llm
from back.llm.prompts import CHAT_SYSTEM, chat_prompt
from back.services.agent import chat_context

logger = logging.getLogger(__name__)


async def answer_question(
    profile: BusinessProfile,
    event: NewsEvent,
    business_categories: list[BusinessCategory],
    counterparties: list[Counterparty],
    report: dict[str, Any] | None,
    question: str,
) -> str | None:
    if not get_settings().llm_agent_enabled:
        return None
    context = chat_context(profile, event, business_categories, counterparties, report)
    try:
        answer = await get_llm().complete_text(
            system=CHAT_SYSTEM,
            user=chat_prompt(context, question),
            temperature=0.2,
        )
    except Exception:
        logger.exception("Chat LLM failed, leaving the question waiting")
        return None
    cleaned = answer.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
    return cleaned or None


async def stream_answer(context: dict[str, Any], question: str) -> AsyncIterator[str]:
    if not get_settings().llm_agent_enabled:
        return
    try:
        async for chunk in get_llm().stream_text(
            system=CHAT_SYSTEM,
            user=chat_prompt(context, question),
            temperature=0.2,
        ):
            yield chunk
    except Exception:
        logger.exception("Chat LLM stream failed, leaving the question waiting")
