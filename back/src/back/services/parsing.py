"""Tolerant normalisation of raw incoming posts."""

import html
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from back.services.ml import normalize

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_TITLE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%d %B %Y",
)

MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


@dataclass(frozen=True)
class ParsedPost:
    title: str
    text: str
    source_name: str
    url: str | None
    published_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "text": self.text,
            "source_name": self.source_name,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
        }


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = _TAG_RE.sub(" ", text)
    text = text.replace("\u00a0", " ")
    return _SPACE_RE.sub(" ", text).strip()


def _derive_title(text: str) -> str:
    first = _TITLE_SPLIT_RE.split(text, maxsplit=1)[0].strip()
    candidate = first or text
    if len(candidate) <= 120:
        return candidate
    return candidate[:117].rstrip() + "..."


def _parse_human_date(text: str) -> datetime | None:
    match = re.search(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})", text.lower())
    if not match:
        return None
    month = MONTHS.get(match.group(2))
    if not month:
        return None
    try:
        return datetime(int(match.group(3)), month, int(match.group(1)), tzinfo=UTC)
    except ValueError:
        return None


def parse_published_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if value is None:
        return datetime.now(UTC)
    raw = str(value).strip()
    if not raw:
        return datetime.now(UTC)
    candidate = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    human = _parse_human_date(raw)
    if human is not None:
        return human
    return datetime.now(UTC)


def parse_post(payload: dict[str, Any]) -> ParsedPost:
    text = clean_text(payload.get("text") or payload.get("content") or payload.get("body"))
    title = clean_text(payload.get("title") or payload.get("headline"))
    if not text:
        text = title
    if not title:
        title = _derive_title(text)
    source = clean_text(
        payload.get("source")
        or payload.get("source_name")
        or payload.get("channel")
        or payload.get("author")
    )
    url = clean_text(payload.get("url") or payload.get("link")) or None
    published_at = parse_published_at(payload.get("published_at") or payload.get("date"))
    if not text:
        raise ValueError("post text is empty after cleanup")
    return ParsedPost(
        title=title[:512],
        text=text,
        source_name=(source or "Неизвестный источник")[:128],
        url=url[:1024] if url else None,
        published_at=published_at,
    )


def text_key(text: str) -> str:
    return normalize(text)[:500]
