from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import and_, select

from back.api.deps import SessionDep
from back.db.models import Event, EventAnalysis, FeedItem, User
from back.schemas.api import FeedCard

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=list[FeedCard])
async def get_feed(
    session: SessionDep,
    user_id: Annotated[int, Query(...)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[FeedCard]:
    statement = (
        select(Event, EventAnalysis)
        .join(FeedItem, FeedItem.event_id == Event.id)
        .join(User, User.id == FeedItem.user_id)
        .outerjoin(
            EventAnalysis,
            and_(
                EventAnalysis.event_id == Event.id,
                EventAnalysis.company_id == User.company_id,
            ),
        )
        .where(FeedItem.user_id == user_id, FeedItem.seen.is_(False))
        .order_by(FeedItem.rank.desc())
        .limit(limit)
    )
    rows = (await session.execute(statement)).all()
    return [
        FeedCard(
            event_id=event.id,
            title=event.title,
            why=analysis.why if analysis else "",
            impact=analysis.impact if analysis else "",
            importance=analysis.importance if analysis else 0.0,
            t0=event.t0,
            n_src=event.n_src,
            main_category=event.main_category,
        )
        for event, analysis in rows
    ]
