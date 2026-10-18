from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import SessionDep
from back.config import settings
from back.db.models import CategoryCounter, Event, FeedItem, Swipe
from back.schemas.api import SwipeRequest
from back.services.feedback import swipe_effect

router = APIRouter(prefix="/swipes", tags=["swipes"])


@router.post("", status_code=204)
async def create_swipe(
    payload: SwipeRequest,
    session: SessionDep,
) -> None:
    event = await session.get(Event, payload.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    session.add(
        Swipe(
            user_id=payload.user_id,
            event_id=payload.event_id,
            direction=payload.direction,
            reason=payload.reason,
        )
    )
    effect = swipe_effect(
        event.categories or {},
        settings.category_thresholds,
        payload.direction,
        payload.reason,
    )
    for category, delta in effect.likes.items():
        await _increment(session, payload.user_id, category, likes=delta)
    for category, delta in effect.dislikes.items():
        await _increment(session, payload.user_id, category, dislikes=delta)

    feed_item = await session.scalar(
        select(FeedItem).where(
            FeedItem.user_id == payload.user_id,
            FeedItem.event_id == payload.event_id,
        )
    )
    if feed_item is not None:
        feed_item.seen = True
    await session.commit()


async def _increment(
    session: AsyncSession,
    user_id: int,
    category: str,
    likes: float = 0.0,
    dislikes: float = 0.0,
) -> None:
    counter = await session.scalar(
        select(CategoryCounter).where(
            CategoryCounter.user_id == user_id,
            CategoryCounter.category == category,
        )
    )
    if counter is None:
        session.add(
            CategoryCounter(
                user_id=user_id,
                category=category,
                likes=likes,
                dislikes=dislikes,
            )
        )
        return
    counter.likes += likes
    counter.dislikes += dislikes
