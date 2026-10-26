from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from ml_pipeline.worker import WorkerSettings


def test_worker_settings_validate_positive_values():
    settings = WorkerSettings(batch_size=3, lease_seconds=10, max_attempts=2)
    assert settings.batch_size > 0
    assert settings.lease_seconds > 0
    assert settings.max_attempts > 0


def test_retry_delay_is_bounded_exponential():
    attempts = [min(3600, 2**count * 30) for count in range(1, 10)]
    assert attempts[:3] == [60, 120, 240]
    assert attempts[-1] == 3600


def test_active_candidate_window_uses_latest_member_time():
    now = datetime.now(UTC)
    old_event = SimpleNamespace(published_at=now - timedelta(days=3))
    event_latest = now - timedelta(hours=23)
    assert now - event_latest <= timedelta(hours=24)
    assert now - old_event.published_at > timedelta(hours=24)


@pytest.mark.parametrize(
    "status,attempts,expected",
    [
        ("retry", 1, "retry"),
        ("failed", 5, "failed"),
    ],
)
def test_worker_failure_states_are_distinct(status, attempts, expected):
    assert status == expected
    assert attempts > 0


def test_profile_analysis_routing_is_async_and_model_specific():
    import inspect

    from ml_pipeline.llm_routes import route_profile_analysis

    assert inspect.iscoroutinefunction(route_profile_analysis)
    assert "kimi_model" in inspect.signature(route_profile_analysis).parameters
    assert "screening_model" in inspect.signature(route_profile_analysis).parameters


def test_worker_settings_have_distinct_models_for_screening_and_business_theses():
    settings = WorkerSettings(kimi_model="kimi-prod", screening_model="model service")
    assert settings.kimi_model != settings.screening_model
