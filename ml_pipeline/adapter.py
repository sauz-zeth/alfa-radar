"""ORM-free mapping adapter; classification behavior lives with Task 5."""

from collections.abc import Mapping
from typing import Any

from .contracts import (
    ClassificationDecision,
    ClusterEventPatch,
    NormalizedPost,
    PostClassifier,
)


def normalize_post(post: Mapping[str, Any]) -> NormalizedPost:
    return NormalizedPost.from_record(post)


def classify_post(post: NormalizedPost, classifier: PostClassifier) -> ClassificationDecision:
    text = " ".join(post.text.split())[:1200]
    if len(text) < 40:
        return ClassificationDecision("ignored", text=text)
    rows = list(classifier.predict([text]))
    labels: list[Mapping[str, Any]] = []
    for row in rows:  # real classifiers nest hits under row["labels"]
        if not isinstance(row, Mapping):
            continue
        inner = row.get("labels")
        if isinstance(inner, list):
            labels.extend(item for item in inner if isinstance(item, Mapping))
        else:
            labels.append(row)

    def _trash(label: object) -> bool:
        lab = str(label).strip().lower()
        return (
            any(part in {"реклама", "мусор"} for part in lab.split("/"))
            or "реклама" in lab
            or "мусор" in lab
        )

    if not labels or any(_trash(row.get("label", "")) for row in labels):
        return ClassificationDecision("ignored", labels=labels, text=text)
    embedding = tuple(float(value) for value in classifier.embed(text))
    norm = sum(value * value for value in embedding) ** 0.5
    if norm:
        embedding = tuple(value / norm for value in embedding)
    return ClassificationDecision("accepted", labels=labels, text=text, embedding=embedding)


def merge_cluster_event(
    existing: Mapping[str, Any] | None, post: NormalizedPost, cluster_key: str
) -> ClusterEventPatch:
    current = existing or {}
    labels: dict[int, float] = {}
    raw_labels = [*(current.get("category_ids") or ()), *(post.labels or ())]
    for raw in raw_labels:
        if isinstance(raw, Mapping):
            key, score = raw.get("id", raw.get("category_id")), raw.get("score", 0)
        else:
            key, score = raw, 1
        try:
            labels[int(key)] = max(labels.get(int(key), 0), float(score))
        except (TypeError, ValueError):
            continue
    source = {
        "post_id": post.post_id,
        "source": post.source,
        "text": post.text,
        "url": post.url,
        "date": str(post.published_at or ""),
        "media": list(post.media),
        "labels": list(post.labels),
    }
    sources = [*current.get("source_posts", ())]
    if not any(
        str(item.get("post_id")) == post.post_id for item in sources if isinstance(item, Mapping)
    ):
        sources.append(source)
    media = [*current.get("media", ())]
    for item in post.media:
        if any(
            item.get(key) and item.get(key) == old.get(key)
            for old in media
            for key in ("image_id", "sha256", "perceptual_hash")
        ):
            continue
        if len(media) >= 4:
            break
        media.append(dict(item))
    return ClusterEventPatch(cluster_key, tuple(labels), tuple(sources), tuple(media))
