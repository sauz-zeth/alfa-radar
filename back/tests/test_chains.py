from datetime import UTC, datetime, timedelta

import numpy as np

from back.pipeline.chains.candidates import find_candidates
from back.pipeline.chains.notify import push_text, should_push


def test_candidates_require_threshold_and_newer_event() -> None:
    now = datetime(2026, 10, 18, 12, tzinfo=UTC)
    vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    candidates = find_candidates(
        np.array([1.0, 0.0], dtype=np.float32),
        vectors,
        chain_ids=[10, 20],
        last_updates=[now - timedelta(hours=1), now + timedelta(hours=1)],
        t0=now,
        threshold=0.75,
    )
    assert candidates == [10]


def test_candidates_are_limited_to_top_three() -> None:
    now = datetime(2026, 10, 18, 12, tzinfo=UTC)
    vectors = np.eye(5, dtype=np.float32)
    candidates = find_candidates(
        np.eye(5, dtype=np.float32)[0],
        vectors,
        chain_ids=[1, 2, 3, 4, 5],
        last_updates=[now - timedelta(hours=1)] * 5,
        t0=now,
        threshold=0.0,
        top_k=3,
    )
    assert len(candidates) == 3


def test_push_only_for_significant_updates() -> None:
    assert should_push(True, 10.0, pushes_today=0)
    assert should_push(False, 50.0, pushes_today=0)
    assert not should_push(False, 49.0, pushes_today=0)
    assert not should_push(True, 100.0, pushes_today=3)


def test_push_text() -> None:
    assert push_text("ЦБ повысил ставку", "Решение принято") == (
        "Обновление: ЦБ повысил ставку. Решение принято"
    )
