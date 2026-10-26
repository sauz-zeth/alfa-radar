"""Worker settings defaults: threshold 30, positive lease/batch/attempts, disabled default."""

from __future__ import annotations

from back.config import Settings


def test_feed_threshold_defaults_to_30() -> None:
    assert Settings().ml_feed_threshold == 30


def test_worker_defaults_are_positive_but_disabled() -> None:
    settings = Settings()
    assert settings.ml_worker_enabled is False
    assert settings.ml_worker_batch_size > 0
    assert settings.ml_worker_lease_seconds > 0
    assert settings.ml_worker_max_attempts > 0
    assert settings.ml_worker_poll_interval_seconds > 0
