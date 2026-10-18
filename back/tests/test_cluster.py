import numpy as np
import pytest

from back.pipeline.cluster import nearest_event, update_centroid


def test_nearest_event_finds_similar_centroid() -> None:
    centroids = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    index = nearest_event(np.array([0.98, 0.2], dtype=np.float32), centroids, 0.85)
    assert index == 0


def test_nearest_event_returns_none_below_threshold() -> None:
    centroids = np.array([[1.0, 0.0]], dtype=np.float32)
    index = nearest_event(np.array([0.0, 1.0], dtype=np.float32), centroids, 0.85)
    assert index is None


def test_update_centroid_is_normalized() -> None:
    updated = update_centroid(
        np.array([1.0, 0.0], dtype=np.float32),
        1,
        np.array([0.0, 1.0], dtype=np.float32),
    )
    assert np.linalg.norm(updated) == pytest.approx(1.0)
