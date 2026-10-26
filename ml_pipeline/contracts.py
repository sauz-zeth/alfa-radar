"""Plain-data contracts shared by the worker and ML artifact adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class NormalizedPost:
    post_id: str
    source: str
    text: str
    title: str = ""
    url: str | None = None
    published_at: datetime | str | None = None
    labels: tuple[Mapping[str, Any], ...] = ()
    media: tuple[Mapping[str, Any], ...] = ()
    embedding: tuple[float, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, post: Mapping[str, Any]) -> NormalizedPost:
        """Convert an ORM-free mapping to the stable runtime input shape."""

        post_id = post.get("post_id", post.get("id"))
        if post_id is None:
            raise ValueError("post record requires id or post_id")

        labels = post.get("labels", post.get("predicted_labels", post.get("categories", ())))
        media = post.get("media", post.get("images", ()))
        embedding = post.get("embedding", ())
        text = post.get("text", "")
        if not isinstance(text, str):
            raise TypeError("post text must be a string")
        raw = post.get("raw") or {}
        if not isinstance(raw, Mapping):
            raise TypeError("post raw payload must be a mapping")

        return cls(
            post_id=str(post_id),
            source=str(post.get("source", post.get("source_name", post.get("channel", ""))) or ""),
            text=text,
            title=str(post.get("title") or ""),
            url=post.get("url"),
            published_at=post.get("published_at", post.get("date")),
            labels=tuple(item for item in labels or () if isinstance(item, Mapping)),
            media=tuple(item for item in media or () if isinstance(item, Mapping)),
            embedding=tuple(float(value) for value in embedding or ()),
            raw=dict(raw),
        )


@dataclass(frozen=True, slots=True)
class ClassificationDecision:
    status: str
    labels: tuple[Mapping[str, Any], ...] = ()
    text: str = ""
    embedding: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class ClusterEventPatch:
    cluster_key: str
    category_ids: tuple[int, ...] = ()
    source_posts: tuple[Mapping[str, Any], ...] = ()
    media: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class ProfileAnalysisResult:
    status: str
    importance: int = 0
    related: bool = False
    direct: bool = False
    fact: bool = False
    within_month: bool = False
    impact: str | None = None
    why: tuple[Mapping[str, Any], ...] = ()
    card_text: str | None = None
    key_facts: tuple[str, ...] = ()
    bank_position: str | None = None


class PostClassifier(Protocol):
    def predict(self, texts: Sequence[str]) -> Sequence[Mapping[str, Any]]: ...

    def embed(self, text: str) -> Sequence[float]: ...
