from back.core.sources import CHANNELS, RECOMMENDED_IDS, find_channel, parse_handle, search_channels


def test_recommended_are_subset_of_catalog() -> None:
    catalog_ids = {item.id for item in CHANNELS}
    assert set(RECOMMENDED_IDS) <= catalog_ids
    assert len(RECOMMENDED_IDS) == 15
    assert len(CHANNELS) == 93
    assert len(catalog_ids) == len(CHANNELS)


def test_parse_handle() -> None:
    assert parse_handle("@my_channel") == "@my_channel"
    assert parse_handle("https://t.me/my_channel") == "@my_channel"
    assert parse_handle("t.me/my_channel/") == "@my_channel"
    assert parse_handle("просто текст") is None


def test_find_channel_by_id_name_and_handle() -> None:
    by_id = find_channel("rbc_news")
    by_name = find_channel("РБК. Новости. Главное")
    by_handle = find_channel("@rbc_news")
    assert by_id is not None and by_id.id == "rbc_news"
    assert by_name is not None and by_name.id == "rbc_news"
    assert by_handle is not None and by_handle.id == "rbc_news"
    assert find_channel("@unknown_channel") is None


def test_catalog_search() -> None:
    result = search_channels("металл")
    assert len(result) >= 2
    assert any(item.id in {"metals_mining", "prometallinfo"} for item in result)
    assert search_channels("") == list(CHANNELS)
