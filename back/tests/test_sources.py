from back.core.sources import (
    CHANNELS,
    RECOMMENDED_IDS,
    find_channel,
    parse_feed_url,
    rss_channel_id,
    rss_feed_urls,
    search_channels,
)


def test_recommended_are_subset_of_catalog() -> None:
    catalog_ids = {item.id for item in CHANNELS}
    assert set(RECOMMENDED_IDS) <= catalog_ids
    assert len(RECOMMENDED_IDS) == 15
    assert len(CHANNELS) == 193
    assert len(catalog_ids) == len(CHANNELS)


def test_find_channel_by_id_name_handle_and_feed_url() -> None:
    by_id = find_channel("rbc_news")
    by_name = find_channel("РБК. Новости. Главное")
    by_handle = find_channel("@rbc_news")
    assert by_id is not None and by_id.id == "rbc_news"
    assert by_name is not None and by_name.id == "rbc_news"
    assert by_handle is not None and by_handle.id == "rbc_news"


def test_rss_url_parsing() -> None:
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
    assert search_channels("") == list(CHANNELS)


def test_rss_feed_urls_default_to_40_unique_feeds() -> None:
    feeds = rss_feed_urls()
    assert len(feeds) == 40
    assert len(feeds) == len(set(feeds))
    assert all(feed.startswith("https://") for feed in feeds)
