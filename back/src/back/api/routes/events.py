from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from back.api.deps import SessionDep
from back.db.models import Event, EventAnalysis
from back.schemas.api import EventDetail

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: int,
    session: SessionDep,
    company_id: Annotated[int, Query(...)],
) -> EventDetail:
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    analysis = await session.scalar(
        select(EventAnalysis).where(
            EventAnalysis.event_id == event_id,
            EventAnalysis.company_id == company_id,
        )
    )
    return EventDetail(
        event_id=event.id,
        title=event.title,
        why=analysis.why if analysis else None,
        impact=analysis.impact if analysis else None,
        importance=analysis.importance if analysis else None,
        materiality=analysis.materiality if analysis else None,
        certainty=analysis.certainty if analysis else None,
        horizon=analysis.horizon if analysis else None,
        t0=event.t0,
        n_src=event.n_src,
        categories=event.categories or {},
        mentions=analysis.mentions if analysis and analysis.mentions else [],
    )
