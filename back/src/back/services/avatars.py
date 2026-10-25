import re
from pathlib import Path

AVATAR_DIR = Path(__file__).resolve().parent.parent / "static" / "avatars"
MAX_AVATAR_BYTES = 2 * 1024 * 1024

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


def _image_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_avatar(channel_id: str, data: bytes) -> str:
    extension = _image_extension(data)
    if extension is None:
        raise ValueError("Поддерживаются только JPEG, PNG и WebP")
    name = _SAFE_NAME.sub("_", channel_id).strip("_") or "channel"
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    path = AVATAR_DIR / f"{name}.{extension}"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return f"/static/avatars/{path.name}"
