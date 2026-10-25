from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.config import get_settings
from back.db.models import Channel, Post, ProfileChannel
from back.db.session import get_session
from back.schemas.common import Page
from back.schemas.ingest import (
    IngestChannelList,
    IngestChannelOut,
    IngestPostOut,
    IngestPostRequest,
    IngestPostTrace,
)
from back.services.pipeline import ingest_from_profile

router = APIRouter(prefix="/ingest", tags=["ingest"])


async def require_ingest_token(
    x_ingest_token: Annotated[str | None, Header(alias="X-Ingest-Token")] = None,
) -> None:
    expected = get_settings().ingest_token
    if expected and x_ingest_token != expected:
        raise HTTPException(status_code=401, detail="Недействительный сервисный токен")


@router.get(
    "/channels", response_model=IngestChannelList, dependencies=[Depends(require_ingest_token)]
)
async def list_ingest_channels(
    session: AsyncSession = Depends(get_session),
) -> IngestChannelList:
    subscribers = func.count(ProfileChannel.profile_id)
    rows = (
        await session.execute(
            select(
                Channel.id,
                Channel.name,
                Channel.handle,
                subscribers.label("subscribers"),
            )
            .join(ProfileChannel, ProfileChannel.channel_id == Channel.id)
            .where(
                Channel.is_active.is_(True),
                Channel.handle.is_not(None),
                Channel.handle != "",
            )
            .group_by(Channel.id, Channel.name, Channel.handle)
            .order_by(subscribers.desc(), Channel.name)
        )
    ).all()
    return IngestChannelList(
        items=[
            IngestChannelOut(
                id=row.id,
                name=row.name,
                handle=row.handle,
                subscribers=row.subscribers,
            )
            for row in rows
        ]
    )


@router.post("/posts", response_model=IngestPostOut, dependencies=[Depends(require_ingest_token)])
async def ingest_post(
    payload: IngestPostRequest,
    session: AsyncSession = Depends(get_session),
) -> IngestPostOut:
    try:
        post = await ingest_from_profile(
            session, payload.model_dump(mode="json"), payload.profile_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Профиль не найден") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestPostOut.model_validate(post)


@router.get(
    "/posts", response_model=Page[IngestPostOut], dependencies=[Depends(require_ingest_token)]
)
async def list_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> Page[IngestPostOut]:
    total = (await session.execute(select(func.count()).select_from(Post))).scalar_one()
    rows = list(
        (
            await session.execute(
                select(Post).order_by(Post.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars()
    )
    return Page[IngestPostOut](
        items=[IngestPostOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/posts/{post_id}",
    response_model=IngestPostTrace,
    dependencies=[Depends(require_ingest_token)],
)
async def get_post_trace(
    post_id: UUID, session: AsyncSession = Depends(get_session)
) -> IngestPostTrace:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Пост не найден")
    return IngestPostTrace.model_validate(post)
