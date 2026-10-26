"""Small, dependency-light image fingerprinting helpers."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

# Источники, чьи изображения сохраняются, но не добавляются в cluster.images.
# Имена указываются в нормализованном виде: "интерфакс", "rbc_news".
CLUSTER_IMAGE_EXCLUDED_SOURCES: set[str] = {
    "агентство нефтегазовой информации",
    "взгляд",
    "интерфакс",
    "кошелек onliner",
    "независимая газета",
    "право ру",
    "прайм",
    "профиль",
    "российская газета",
    "утро ру",
    "учительская газета",
    "хабр лучшее за неделю",
    "advertology.ru",
    "alta.ru",
    "bfm.ru",
    "drom.ru",
    "new retail",
    "open net",
    "regnum",
    "rt на русском",
}


def normalize_image_source(value: str) -> str:
    value = str(value or "").strip().lower().replace("ё", "е")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("_", " ").replace("-", " ").replace("—", " ").replace("–", " ")
    value = re.sub(r"\s+", " ", value).strip().lstrip("@").split("/", 1)[0]
    return value


def image_source_is_excluded(value: str, excluded: set[str] | None = None) -> bool:
    """Match display names and directory-style aliases used by the RSS catalogue."""
    source = normalize_image_source(value)
    aliases = {normalize_image_source(item) for item in
               (CLUSTER_IMAGE_EXCLUDED_SOURCES if excluded is None else excluded)}
    return any(source == alias or source.startswith(alias + " ") for alias in aliases)


def image_fingerprint(path: Path) -> tuple[str, str]:
    """Return SHA-256 and a compact perceptual hash for an image file."""
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    try:
        from PIL import Image
        import imagehash

        with Image.open(path) as image:
            phash = str(imagehash.phash(image.convert("RGB")))
    except Exception:
        # A broken or unsupported image is still safely deduplicated by bytes.
        phash = sha[:16]
    return sha, phash


def same_image(left: dict, right: dict, max_distance: int = 8) -> bool:
    if left.get("sha256") and left.get("sha256") == right.get("sha256"):
        return True
    a, b = left.get("perceptual_hash"), right.get("perceptual_hash")
    if not a or not b or len(a) != len(b):
        return False
    try:
        return sum(x != y for x, y in zip(bin(int(a, 16))[2:].zfill(len(a) * 4),
                                          bin(int(b, 16))[2:].zfill(len(b) * 4))) <= max_distance
    except ValueError:
        return False
