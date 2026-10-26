"""Persist ingest media and collect small, JSON-safe image metadata."""

from __future__ import annotations

import hashlib
import io
import mimetypes
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from fastapi import UploadFile

from back.config import get_settings

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def _image_metadata(data: bytes) -> tuple[str, int, int]:
    import imagehash
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        image.load()
        return str(imagehash.phash(image.convert("RGB"))), image.width, image.height


def _safe_filename(filename: str | None, index: int) -> str:
    name = Path(filename or f"image-{index}").name
    name = _SAFE_NAME.sub("_", name).strip("._")
    return name or f"image-{index}"


async def save_post_media(
    files: Sequence[UploadFile], source_name: str, post_id: UUID
) -> list[dict[str, Any]]:
    """Save each upload independently; a bad image becomes an error entry."""

    root = get_settings().media_root
    post_root = root / "posts" / str(post_id)
    post_root.mkdir(parents=True, exist_ok=True)
    result: list[dict[str, Any]] = []
    for index, file in enumerate(files):
        filename = _safe_filename(file.filename, index)
        relative = Path("posts") / str(post_id) / f"{index}-{filename}"
        target = root / relative
        entry: dict[str, Any] = {
            "image_id": f"{post_id}:{index}",
            "path": relative.as_posix(),
            "origin_url": file.filename,
            "filename": file.filename,
            "source": source_name,
            "content_type": file.content_type,
        }
        try:
            data = await file.read()
            if not data:
                raise ValueError("empty image")
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["perceptual_hash"], entry["width"], entry["height"] = _image_metadata(data)
            temporary = target.with_name(f".{target.name}.tmp")
            temporary.write_bytes(data)
            temporary.replace(target)
        except Exception as exc:  # one broken file must not reject its post
            entry["error"] = str(exc) or exc.__class__.__name__
        result.append(entry)
    return result


async def save_remote_post_media(
    urls: Sequence[str], source_name: str, post_id: UUID, client: httpx.AsyncClient
) -> list[dict[str, Any]]:
    """Download RSS images into the same media store used by uploaded post images."""
    root = get_settings().media_root
    post_root = root / "posts" / str(post_id)
    post_root.mkdir(parents=True, exist_ok=True)
    result: list[dict[str, Any]] = []
    for index, url in enumerate(dict.fromkeys(urls)):
        entry: dict[str, Any] = {
            "image_id": f"{post_id}:{index}",
            "path": (Path("posts") / str(post_id) / f"{index}.img").as_posix(),
            "origin_url": url,
            "source": source_name,
        }
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.content
            if not data or len(data) > 25 * 1024 * 1024:
                raise ValueError("empty image or image exceeds 25 MiB")
            phash, width, height = _image_metadata(data)
            content_type = response.headers.get("content-type", "").split(";", 1)[0]
            suffix = mimetypes.guess_extension(content_type) or Path(httpx.URL(url).path).suffix
            suffix = suffix if suffix and len(suffix) <= 8 else ".img"
            entry["path"] = (Path("posts") / str(post_id) / f"{index}{suffix}").as_posix()
            entry.update(
                sha256=hashlib.sha256(data).hexdigest(),
                perceptual_hash=phash,
                width=width,
                height=height,
                content_type=response.headers.get("content-type"),
            )
            target = root / entry["path"]
            temporary = target.with_name(f".{target.name}.tmp")
            temporary.write_bytes(data)
            temporary.replace(target)
        except Exception as exc:
            entry["error"] = str(exc) or exc.__class__.__name__
        result.append(entry)
    return result
