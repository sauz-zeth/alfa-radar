from back.db.models import BusinessProfile
from back.services.sources import (
    catalog,
    ensure_sources,
    sources_state,
    subscribe,
    unsubscribe_all,
)


def _profile() -> BusinessProfile:
    return BusinessProfile(
        entrepreneur_name="Иван",
        business_name="Тест",
        sources={},
        notifications={},
        search_history=[],
    )


def test_default_sources_are_recommended() -> None:
    profile = _profile()
    state = sources_state(profile)
    assert state.recommended_count == 15
    assert len(state.channels) == 15
    assert state.alfa_analytics is True
    assert ensure_sources(profile)["channels"]


def test_subscribe_by_handle_and_add_custom() -> None:
    profile = _profile()
    subscribe(profile, "@my_own_channel")
    assert any(item.handle == "@my_own_channel" for item in sources_state(profile).channels)
    custom = catalog(profile, "my_own").items
    assert custom and custom[0].kind == "custom"


def test_catalog_search() -> None:
    profile = _profile()
    result = catalog(profile, "металл")
    assert result.total >= 2
    assert all("металл" in f"{item.name} {item.topics}".lower() for item in result.items)


def test_unsubscribe_all_and_restore_by_resubscribe() -> None:
    profile = _profile()
    unsubscribe_all(profile)
    assert sources_state(profile).channels == []
    subscribe(profile, "metall-inside")
    assert len(sources_state(profile).channels) == 1
