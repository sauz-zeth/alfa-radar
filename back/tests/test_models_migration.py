from __future__ import annotations

import importlib.util
from pathlib import Path

from back.db.models import EventAnalysis, NewsEvent, Post, ProfileEventScore


def test_runtime_columns_and_defaults() -> None:
    assert NewsEvent.__table__.c.media.default.arg.__name__ == "list"
    assert Post.__table__.c.media.default.arg.__name__ == "list"
    assert Post.__table__.c.attempt_count.default.arg == 0
    assert Post.__table__.c.lease_until.nullable
    assert Post.__table__.c.last_error.nullable
    assert EventAnalysis.__table__.c.status.default.arg == "weak"
    assert EventAnalysis.__table__.c.independent_source_count.default.arg == 0
    assert ProfileEventScore.__table__.c.importance.default.arg == 0
    assert ProfileEventScore.__table__.c.status.default.arg == "weak"
    for name in (
        "related",
        "direct",
        "fact",
        "within_month",
        "why",
        "card_text",
        "key_facts",
        "bank_position",
    ):
        assert name in EventAnalysis.__table__.c


def test_migration_has_reversible_operations() -> None:
    path = Path(__file__).parents[1] / "migrations/versions/new_ml_feed_runtime_fields.py"
    spec = importlib.util.spec_from_file_location("new_ml_feed_runtime_fields", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "new_ml_feed_runtime_fields"
    assert module.down_revision == "e5c6d7e8f9a0"
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    names = module.upgrade.__code__.co_names
    assert "profile_event_scores" in names or "create_table" in names
