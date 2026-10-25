from back.core.sources import (
    CHANNELS,
    RECOMMENDED_IDS,
    find_channel,
    parse_feed_url,
    parse_handle,
    rss_channel_id,
    search_channels,
)


def test_recommended_are_subset_of_catalog() -> None:
    catalog_ids = {item.id for item in CHANNELS}
    assert set(RECOMMENDED_IDS) <= catalog_ids
    assert len(RECOMMENDED_IDS) == 15
    assert len(CHANNELS) == 193
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


def test_rss_and_handle_parsing() -> None:
    assert parse_feed_url("https://vz.ru/rss.xml") == "https://vz.ru/rss.xml"
    assert parse_feed_url("https://t.me/rbc_news") is None
    assert parse_feed_url("@rbc_news") is None
    assert parse_feed_url("просто текст") is None
    assert parse_feed_url("http://localhost:8000/feed") is None
    assert parse_feed_url("http://127.0.0.1/feed") is None
    rss = find_channel("https://vz.ru/rss.xml")
    assert rss is not None and rss.feed_url == "https://vz.ru/rss.xml"
    assert rss.id == rss_channel_id("https://vz.ru/rss.xml")


def test_catalog_search() -> None:
    result = search_channels("металл")
    assert len(result) >= 2
    assert any(item.id in {"metals_mining", "prometallinfo"} for item in result)
    assert search_channels("") == list(CHANNELS)
