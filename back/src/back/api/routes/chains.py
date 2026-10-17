from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from back.api.deps import SessionDep
from back.db.models import Chain, ChainReport, ChainSubscriber, User
from back.schemas.api import ChainReportView, ChainView

router = APIRouter(prefix="/chains", tags=["chains"])


@router.get("", response_model=list[ChainView])
async def list_chains(
    session: SessionDep,
    user_id: Annotated[int, Query(...)],
) -> list[ChainView]:
    statement = (
        select(Chain, ChainSubscriber.id)
        .join(ChainSubscriber, ChainSubscriber.chain_id == Chain.id)
        .where(ChainSubscriber.user_id == user_id)
        .order_by(Chain.last_update.desc())
    )
    rows = (await session.execute(statement)).all()
    return [
        ChainView(
            chain_id=chain.id,
            summary=chain.summary,
            status=chain.status,
            last_update=chain.last_update,
            subscribed=subscriber_id is not None,
        )
        for chain, subscriber_id in rows
    ]


@router.post("/{chain_id}/subscribe", status_code=204)
async def subscribe(
    chain_id: int,
    session: SessionDep,
    user_id: Annotated[int, Query(...)],
) -> None:
    chain = await session.get(Chain, chain_id)
    user = await session.get(User, user_id)
    if chain is None or user is None:
        raise HTTPException(status_code=404, detail="Chain or user not found")
    existing = await session.scalar(
        select(ChainSubscriber).where(
            ChainSubscriber.chain_id == chain_id,
            ChainSubscriber.user_id == user_id,
        )
    )
    if existing is None:
        session.add(
            ChainSubscriber(
                chain_id=chain_id,
                user_id=user_id,
                company_id=user.company_id,
            )
        )
        await session.commit()


@router.delete("/{chain_id}/subscribe", status_code=204)
async def unsubscribe(
    chain_id: int,
    session: SessionDep,
    user_id: Annotated[int, Query(...)],
) -> None:
    subscription = await session.scalar(
        select(ChainSubscriber).where(
            ChainSubscriber.chain_id == chain_id,
            ChainSubscriber.user_id == user_id,
        )
    )
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await session.delete(subscription)
    await session.commit()


@router.get("/{chain_id}/reports", response_model=list[ChainReportView])
async def list_reports(
    chain_id: int,
    session: SessionDep,
    company_id: Annotated[int, Query(...)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ChainReportView]:
    rows = (
        await session.scalars(
            select(ChainReport)
            .where(
                ChainReport.chain_id == chain_id,
                ChainReport.company_id == company_id,
            )
            .order_by(ChainReport.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        ChainReportView(
            report_id=report.id,
            chain_id=report.chain_id,
            event_id=report.event_id,
            change=report.change,
            conclusions_changed=report.conclusions_changed,
            importance=report.importance,
            impact=report.impact,
            actions=report.actions or [],
            created_at=report.created_at,
        )
        for report in rows
    ]
