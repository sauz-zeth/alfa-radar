from back.services.rss import parse_feed

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
