import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

spec = importlib.util.spec_from_file_location(
    "watch_pipeline", Path(__file__).parents[1] / "scripts" / "watch_pipeline.py"
)
watch_pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch_pipeline)


def test_format_post_shows_text_categories_cluster_and_profile_status():
    event_id = uuid4()
    post = SimpleNamespace(
        id=uuid4(),
        source_name="Тестовый источник",
        title="Тестовая новость",
        text="Текст новости",
        url="https://example.com/news",
        published_at=datetime(2026, 10, 26, tzinfo=UTC),
        status="clustered",
        stage="clustered",
        categories=[1],
        cluster_key="cluster-123",
        news_event_id=event_id,
        similarity=0.91,
        importance=72,
        last_error=None,
    )

    output = watch_pipeline.format_post(
        post, {1: "Экономика"}, [{"profile_id": "profile-1", "status": "strong"}]
    )

    assert "Текст новости" in output
    assert "Экономика" in output
    assert "cluster-123" in output
    assert str(event_id) in output
    assert "profile-1" in output
    assert "strong" in output
