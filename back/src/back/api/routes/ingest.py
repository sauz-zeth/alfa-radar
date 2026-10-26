import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.config import get_settings
from back.db.models import Channel, Post
from back.db.session import get_session
from back.schemas.common import Page
from back.schemas.ingest import (
    IngestPostOut,
    IngestPostRequest,
    IngestPostTrace,
    IngestAvatarOut,
)
from back.services.avatars import MAX_AVATAR_BYTES, save_avatar
from back.services.media import save_post_media
from back.services.parsing import parse_post

router = APIRouter(prefix="/ingest", tags=["ingest"])


async def require_ingest_token(
    x_ingest_token: Annotated[str | None, Header(alias="X-Ingest-Token")] = None,
) -> None:
    expected = get_settings().ingest_token
    if expected and x_ingest_token != expected:
        raise HTTPException(status_code=401, detail="Недействительный сервисный токен")


@router.put(
    "/channels/{channel_id}/avatar",
    response_model=IngestAvatarOut,
    dependencies=[Depends(require_ingest_token)],
)
async def upload_channel_avatar(
    channel_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> IngestAvatarOut:
    channel = await session.get(Channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Канал не найден")
    data = await request.body()
    if not data:
        raise HTTPException(status_code=422, detail="Пустой файл аватарки")
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Файл аватарки больше 2 МБ")
    try:
        avatar_url = save_avatar(channel_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    channel.meta = {**(channel.meta or {}), "avatar_url": avatar_url}
    await session.commit()
    return IngestAvatarOut(avatar_url=avatar_url)


@router.post("/posts", response_model=IngestPostOut, dependencies=[Depends(require_ingest_token)])
async def ingest_post(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> IngestPostOut:
    content_type = request.headers.get("content-type", "")
    files: list[UploadFile] = []
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        raw_payload: Any = next(
            (form.get(name) for name in ("payload", "json", "data") if form.get(name)), None
        )
        for name, value in form.multi_items():
            is_upload = hasattr(value, "filename") and hasattr(value, "read")
            if name in {"images", "image"} and is_upload:
                files.append(value)  # type: ignore[arg-type]
        if raw_payload is None:
            raw_payload = {
                name: value
                for name, value in form.multi_items()
                if name not in {"images", "image"} and not hasattr(value, "filename")
            }
        if isinstance(raw_payload, str):
            try:
                raw_payload = json.loads(raw_payload)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail="Некорректный JSON payload") from exc
    else:
        try:
            raw_payload = await request.json()
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Некорректный JSON payload") from exc
    try:
        payload = IngestPostRequest.model_validate(raw_payload)
        parsed = parse_post(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    raw = payload.model_dump(mode="json")
    post = Post(
        source_name=parsed.source_name,
        title=parsed.title,
        text=parsed.text,
        url=parsed.url,
        published_at=parsed.published_at,
        raw=raw,
        parsed=parsed.as_dict(),
        categories=[],
        embedding=[],
        decision_trace=[{"stage": "parse", **parsed.as_dict()}],
        media=[],
        attempt_count=0,
        status="received",
        stage="received",
    )
    session.add(post)
    await session.flush()
    try:
        post.media = await save_post_media(files, parsed.source_name, post.id)
        origins = raw.get("images")
        if isinstance(origins, list):
            for index, item in enumerate(post.media):
                if index >= len(origins) or not isinstance(origins[index], dict):
                    continue
                metadata = origins[index]
                for key in ("origin_url", "url", "filename", "content_type"):
                    if metadata.get(key):
                        item[key if key != "url" else "origin_url"] = metadata[key]
    except Exception:  # media helper is per-file tolerant; keep text ingestion available
        post.media = []
    await session.commit()
    await session.refresh(post)
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
