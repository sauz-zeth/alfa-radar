import httpx
import pytest

from back.services.rss import fetch_feed, parse_feed

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Деловые новости</title>
  <item>
    <title>ЦБ повысил ставку</title>
    <description><![CDATA[<p>Ставка выросла до <b>21%</b>.</p>]]></description>
    <link>https://example.com/news/rate</link>
    <pubDate>Tue, 21 Oct 2025 09:30:00 GMT</pubDate>
  </item>
</channel></rss>
"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Минфин</title>
  <entry>
    <title>Пошлина на металлопрокат</title>
    <summary>Ставка 7% с 1 ноября.</summary>
    <link rel="alternate" href="https://example.com/atom/duty"/>
    <updated>2025-10-20T12:00:00Z</updated>
  </entry>
</feed>
"""


def test_parse_rss_channel() -> None:
    items = parse_feed(RSS, "https://example.com/rss")
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "ЦБ повысил ставку"
    assert item["text"] == "Ставка выросла до 21% ."
    assert item["source"] == "Деловые новости"
    assert item["url"] == "https://example.com/news/rate"
    assert item["published_at"].startswith("2025-10-21T09:30:00")


def test_parse_atom_entry() -> None:
    items = parse_feed(ATOM, "https://example.com/atom")
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "Пошлина на металлопрокат"
    assert item["source"] == "Минфин"
    assert item["url"] == "https://example.com/atom/duty"
    assert item["published_at"].startswith("2025-10-20T12:00:00")


@pytest.mark.parametrize("body", ["", "not xml", "<rss>"])
def test_parse_feed_reports_invalid_or_empty_xml(body: str) -> None:
    with pytest.raises(ValueError, match="Invalid or empty RSS/Atom XML"):
        parse_feed(body, "https://example.com/rss")


def test_rss_extracts_image_enclosure_thumbnail_and_content_image() -> None:
    xml = '''<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><title>Feed</title><item>
      <title>News</title><description>&lt;img src="/inline.jpg"&gt;</description>
      <enclosure url="/photo.jpg" type="image/jpeg"/>
      <enclosure url="/audio.mp3" type="audio/mpeg"/>
      <media:thumbnail url="/thumb.jpg"/>
      <media:content url="/media.jpg" type="image/jpeg"/>
    </item></channel></rss>'''
    item = parse_feed(xml, "https://example.com/rss")[0]
    assert item["images"] == ["/photo.jpg", "/thumb.jpg", "/media.jpg", "/inline.jpg"]


@pytest.mark.asyncio
async def test_fetch_feed_uses_open_graph_when_item_has_no_image() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rss":
            return httpx.Response(200, text=RSS)
        return httpx.Response(200, text='<meta content="/cover.jpg" property="og:image">')

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        items = await fetch_feed("https://example.com/rss", client)
    assert items[0]["images"] == ["https://example.com/cover.jpg"]


@pytest.mark.asyncio
async def test_fetch_feed_keeps_item_when_open_graph_page_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rss":
            return httpx.Response(200, text=RSS)
        raise httpx.ConnectError("offline", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        items = await fetch_feed("https://example.com/rss", client)
    assert items[0]["title"] == "ЦБ повысил ставку"
    assert items[0]["images"] == []


@pytest.mark.asyncio
async def test_ingest_feed_logs_ingested_and_duplicate_counts(caplog, monkeypatch) -> None:
    from unittest.mock import AsyncMock

    from back.services import rss

    session = AsyncMock()
    session.scalar.return_value = None
    monkeypatch.setattr(rss, "fetch_feed", AsyncMock(return_value=[{"url": None}]))
    monkeypatch.setattr(rss, "parse_post", lambda _: _parsed_post())
    monkeypatch.setattr(rss, "save_remote_post_media", AsyncMock(return_value=[]))
    session.flush = AsyncMock()
    session.add = lambda _: None
    with caplog.at_level("INFO", logger="back.services.rss"):
        assert await rss.ingest_feed(session, "https://example.com/rss") == (1, 0)
    assert "rss ingest" in caplog.text
    assert "ingested=1" in caplog.text


@pytest.mark.asyncio
async def test_ingest_feed_filters_to_since_and_logs_added_news(caplog, monkeypatch) -> None:
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock

    from back.services import rss

    session = AsyncMock()
    session.scalar.return_value = None
    monkeypatch.setattr(
        rss,
        "fetch_feed",
        AsyncMock(
            return_value=[
                {"url": "https://example.com/old", "published_at": "2025-10-20T00:00:00+00:00"},
                {"url": "https://example.com/new", "published_at": "2025-10-21T00:00:00+00:00"},
            ]
        ),
    )
    monkeypatch.setattr(rss, "parse_post", lambda _: _parsed_post())
    monkeypatch.setattr(rss, "save_remote_post_media", AsyncMock(return_value=[]))
    session.flush = AsyncMock()
    session.add = lambda _: None
    with caplog.at_level("INFO", logger="back.services.rss"):
        assert await rss.ingest_feed(
            session, "https://example.com/rss", since=datetime(2025, 10, 21, tzinfo=UTC)
        ) == (1, 0)
    assert "rss queued" in caplog.text


@pytest.mark.asyncio
async def test_ingest_feed_can_queue_existing_url_when_deduplication_disabled(monkeypatch) -> None:
    from unittest.mock import AsyncMock

    from back.services import rss

    session = AsyncMock()
    monkeypatch.setattr(rss, "parse_post", lambda _: _parsed_post())
    monkeypatch.setattr(rss, "save_remote_post_media", AsyncMock(return_value=[]))
    session.flush = AsyncMock()
    session.add = lambda _: None
    monkeypatch.setattr(
        rss,
        "fetch_feed",
        AsyncMock(return_value=[{"url": "https://example.com/already-seen"}]),
    )

    assert await rss.ingest_feed(
        session, "https://example.com/rss", skip_existing=False
    ) == (1, 0)
    session.scalar.assert_not_awaited()


def _parsed_post():
    from datetime import UTC, datetime
    from types import SimpleNamespace

    return SimpleNamespace(
        source_name="RSS",
        title="title",
        text="text",
        url=None,
        published_at=datetime(2025, 10, 21, tzinfo=UTC),
        as_dict=lambda: {},
    )
