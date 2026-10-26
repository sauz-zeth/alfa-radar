from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
from ml_pipeline import worker
from ml_pipeline.contracts import ClassificationDecision, NormalizedPost


class Session:
    def __init__(self, event=None):
        self.event = event
        self.added = []

    async def get(self, model, key):
        return self.event if self.event and self.event.id == key else None

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if not getattr(item, "id", None):
                item.id = uuid4()


class Repo:
    def __init__(self, events, members):
        self.events, self.members = events, members
        self.session = Session()
        self.locks = []

    async def lock_cluster(self, key):
        self.locks.append(key)

    async def candidate_events(self, since):
        return self.events

    async def event_member_posts(self, event_ids, since):
        return self.members


class Reranker:
    def __init__(self, logits):
        self.logits = logits

    def rank(self, text, candidates, batch_size):
        return np.asarray(self.logits[: len(candidates)], dtype=np.float32)


def test_old_cluster_is_not_a_candidate_even_if_repository_returns_it():
    now = datetime.now(UTC)
    event = SimpleNamespace(
        id=uuid4(),
        chain_key="existing-key",
        source_posts=[],
        media=[],
        category_ids=[],
        published_at=now - timedelta(days=2),
    )
    member = SimpleNamespace(
        id=uuid4(),
        news_event_id=event.id,
        source_name="other",
        published_at=now - timedelta(days=2),
        embedding=[1.0, 0.0],
        text="old text",
    )
    repo = Repo([(event, now - timedelta(days=2))], [member])
    post = SimpleNamespace(
        id=uuid4(),
        source_name="new",
        published_at=now,
        media=[],
        url=None,
        text="a" * 60,
        categories=[],
        embedding=[],
    )
    normalized = NormalizedPost(str(post.id), "new", "a" * 60, published_at=now)
    decision = ClassificationDecision(
        "accepted", labels=({"label": "cat", "score": 0.9},), text="a" * 60, embedding=(1.0, 0.0)
    )
    result, _key = asyncio.run(
        worker._cluster(repo, post, normalized, decision, Reranker([2.0]), {"cat": 1})
    )
    assert result is repo.session.added[0]
    assert result is not event


def test_matched_cluster_keeps_its_chain_key():
    now = datetime.now(UTC)
    event = SimpleNamespace(
        id=uuid4(),
        chain_key="stable-cluster",
        source_posts=[],
        media=[],
        category_ids=[],
        published_at=now - timedelta(minutes=20),
    )
    member = SimpleNamespace(
        id=uuid4(),
        news_event_id=event.id,
        source_name="other",
        published_at=now - timedelta(minutes=20),
        embedding=[1.0, 0.0],
        text="similar text",
    )
    repo = Repo([(event, now - timedelta(minutes=20))], [member])
    post = SimpleNamespace(
        id=uuid4(),
        source_name="new",
        published_at=now,
        media=[],
        url=None,
        text="similar text",
        categories=[],
        embedding=[],
    )
    normalized = NormalizedPost(str(post.id), "new", "similar text", published_at=now)
    decision = ClassificationDecision(
        "accepted",
        labels=({"label": "cat", "score": 0.9},),
        text="similar text",
        embedding=(1.0, 0.0),
    )
    result, key = asyncio.run(
        worker._cluster(repo, post, normalized, decision, Reranker([2.0]), {"cat": 1})
    )
    assert result is event
    assert key == "stable-cluster"
