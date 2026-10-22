from back.core.sources import CHANNELS, RECOMMENDED_IDS, find_channel, parse_handle, search_channels


def test_recommended_are_subset_of_catalog() -> None:
    catalog_ids = {item.id for item in CHANNELS}
    assert set(RECOMMENDED_IDS) <= catalog_ids
    assert len(RECOMMENDED_IDS) == 15


def test_parse_handle() -> None:
    assert parse_handle("@my_channel") == "@my_channel"
    assert parse_handle("https://t.me/my_channel") == "@my_channel"
    assert parse_handle("t.me/my_channel/") == "@my_channel"
    assert parse_handle("просто текст") is None


def test_find_channel_by_id_name_and_handle() -> None:
    by_id = find_channel("metall-inside")
    by_name = find_channel("Металл-Инсайд")
    by_handle = find_channel("@metall_inside")
    assert by_id is not None and by_id.id == "metall-inside"
    assert by_name is not None and by_name.id == "metall-inside"
    assert by_handle is not None and by_handle.id == "metall-inside"
    assert find_channel("@unknown_channel") is None


def test_catalog_search() -> None:
    result = search_channels("металл")
    assert len(result) >= 2
    assert any(item.id == "metall-inside" for item in result)
    assert search_channels("") == list(CHANNELS)
