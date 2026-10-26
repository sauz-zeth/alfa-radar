from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from starlette.datastructures import Headers

from back.config import get_settings
from back.db.models import Post
from back.db.session import get_session
from back.main import app
from back.services.media import save_post_media

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\x0dIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.asyncio
async def test_save_post_media_writes_metadata_and_dimensions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    get_settings.cache_clear()
    file = UploadFile(
        file=io.BytesIO(PNG_1X1),
        filename="photo.png",
        headers=Headers({"content-type": "image/png"}),
    )

    result = await save_post_media([file], "Telegram channel", uuid4())

    assert len(result) == 1
    item = result[0]
    assert item["source"] == "Telegram channel"
    assert item["width"] == 1
    assert item["height"] == 1
    assert item["sha256"]
    assert item["perceptual_hash"]
    assert (tmp_path / item["path"]).is_file()


class _Session:
    def __init__(self) -> None:
        self.post: Post | None = None

    def add(self, value: Post) -> None:
        self.post = value

    async def flush(self) -> None:
        assert self.post is not None
        if self.post.id is None:
            self.post.id = UUID(str(uuid4()))
        self.post.created_at = datetime.now(UTC)
        self.post.status_updated_at = datetime.now(UTC)
        self.post.attempt_count = 0

    async def commit(self) -> None:
        return None

    async def refresh(self, value: Post) -> None:
        return None


@pytest.mark.asyncio
async def test_multipart_ingest_returns_received_and_keeps_broken_image(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    get_settings.cache_clear()
    session = _Session()

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/ingest/posts",
                files=[
                    (
                        "images",
                        ("broken.png", b"not an image", "image/png"),
                    )
                ],
                data={
                    "payload": json.dumps(
                        {
                            "text": "Текст новости сохраняется даже при битой картинке.",
                            "source_name": "RSS",
                            "profile_id": str(uuid4()),
                            "images": [
                                {
                                    "url": "https://example.test/news/photo.png",
                                    "filename": "broken.png",
                                    "content_type": "image/png",
                                }
                            ],
                        }
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "received"
    assert body["stage"] == "received"
    assert body["media"][0]["error"]
    assert body["media"][0]["origin_url"] == "https://example.test/news/photo.png"
    assert session.post is not None
    assert session.post.raw["profile_id"]
