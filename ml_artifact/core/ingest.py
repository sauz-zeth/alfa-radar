"""Collect RSS news for a rolling time window."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

from .image_utils import image_fingerprint

ROOT = Path(__file__).resolve().parent.parent
RSS_MD = ROOT / "RSS_ленты_для_новостной_аналитики_кейс_Альфа_Банка.md"
LINK_RE = re.compile(r"\[([^]]+)\]\((https?://[^)]+)\)")


def parse_sources(rss_path: Path = RSS_MD) -> list[dict[str, str]]:
    feeds = []
    for line in rss_path.read_text(encoding="utf-8").splitlines():
        links = LINK_RE.findall(line)
        if len(links) >= 2 and line.lstrip().startswith("|"):
            name, url = links[0][0], links[1][1]
            feeds.append({"name": name, "url": url})
    unique = {}
    for item in feeds:
        unique.setdefault(item["url"], item)
    return list(unique.values())


def parse_date(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    value = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return fallback
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


def stable_id(source: str, url: str) -> str:
    return hashlib.sha256(f"{source}\n{url}".encode()).hexdigest()[:24]


def download_image(url: str, directory: Path, stem: str, timeout: float = 20) -> dict | None:
    try:
        request = Request(url, headers={"User-Agent": "alfa-news-parser/1.0"})
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
        if not data or len(data) > 25 * 1024 * 1024:
            return None
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{stem}.bin"
        path.write_bytes(data)
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        sha, phash = image_fingerprint(path)
        suffix = ".jpg"
        with Image.open(path) as image:
            suffix = "." + (image.format or "JPEG").lower()
        final = path.with_suffix(suffix)
        if final != path:
            path.replace(final)
        return {"image_id": sha[:24], "path": str(final), "origin_url": url,
                "sha256": sha, "perceptual_hash": phash}
    except Exception:
        return None


def article_image_urls(entry: dict) -> list[str]:
    urls = []
    for key in ("media_content", "media_thumbnail", "enclosures", "links"):
        for item in entry.get(key, []) or []:
            if isinstance(item, dict):
                url = item.get("url") or item.get("href")
                kind = item.get("type", "")
                if url and (key != "links" or "image" in kind or "image" in url.lower()):
                    urls.append(url)
    html = " ".join(str(x.get("value", "")) for x in entry.get("content", []) if isinstance(x, dict))
    html += " " + str(entry.get("summary", ""))
    urls.extend(re.findall(r"<img[^>]+src=[\"']([^\"']+)", html, re.I))
    return list(dict.fromkeys(urls))


def og_image_url(url: str, timeout: float = 5) -> str | None:
    try:
        request = Request(url, headers={"User-Agent": "alfa-news-parser/1.0"})
        with urlopen(request, timeout=timeout) as response:
            html = response.read(2_000_000).decode("utf-8", "ignore")
        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I)
        if not match:
            match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
        return unescape(match.group(1)) if match else None
    except Exception:
        return None


def fetch_feed(url: str, timeout: float = 10, attempts: int = 1) -> bytes:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": "alfa-news-parser/1.0"})
            with urlopen(request, timeout=timeout) as response:
                return response.read(10_000_000)
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                continue
    raise RuntimeError(f"RSS fetch failed: {last_error}")


def fetch_rss(feed: dict, start: datetime, end: datetime, media_dir: Path) -> tuple[list[dict], str | None]:
    try:
        import feedparser
        parsed = feedparser.parse(fetch_feed(feed["url"]))
        rows = []
        source = re.sub(r"\s+", " ", unescape(feed["name"])).strip()
        slug = re.sub(r"[^\w.-]+", "_", source, flags=re.UNICODE).strip("_") or "rss"
        for entry in parsed.entries:
            now = datetime.now(UTC)
            stamp = entry.get("published") or entry.get("updated")
            if stamp:
                try:
                    from email.utils import parsedate_to_datetime
                    date = parsedate_to_datetime(stamp).astimezone(UTC)
                except Exception:
                    date = parse_date(stamp, now)
            else:
                date = now
            if not start <= date < end:
                continue
            url = entry.get("link") or feed["url"]
            text = re.sub(r"<[^>]+>", " ", entry.get("summary") or entry.get("description") or entry.get("title", ""))
            image_records = []
            image_urls = article_image_urls(entry)
            if not image_urls:
                page_image = og_image_url(url)
                if page_image:
                    image_urls.append(page_image)
            for index, image_url in enumerate(image_urls):
                image = download_image(image_url, media_dir / "rss" / slug, stable_id(source, url) + f"_{index}")
                if image:
                    image.update(source=source, post_id=stable_id(source, url))
                    image_records.append(image)
            rows.append({"post_id": stable_id(source, url), "source": source, "channel": source,
                         "date": date.isoformat(), "text": unescape(re.sub(r"\s+", " ", text)).strip(),
                         "url": url, "images": image_records})
        return rows, None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def fetch_rss_timed(feed: dict, start: datetime, end: datetime, media_dir: Path):
    started = time.perf_counter()
    rows, error = fetch_rss(feed, start, end, media_dir)
    return rows, error, time.perf_counter() - started


def ingest(output_dir: Path, start: datetime, end: datetime) -> dict:
    output_dir = output_dir.resolve()
    feeds = parse_sources()
    media_dir = output_dir / "media"
    raw_dir = output_dir / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows, errors = [], []
    output = raw_dir / "news.jsonl"
    print(f"[Ingest] окно {start.isoformat()} → {end.isoformat()}", flush=True)
    print(f"[RSS] источников: {len(feeds)}", flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_rss_timed, feed, start, end, media_dir): feed for feed in feeds}
        for index, future in enumerate(as_completed(futures), 1):
            feed = futures[future]
            try:
                feed_rows, error, elapsed = future.result()
            except Exception as exc:
                feed_rows, error, elapsed = [], f"{type(exc).__name__}: {exc}", 0
            rows.extend(feed_rows)
            if error:
                errors.append(f"rss:{feed['url']}: {error}")
                print(f"[RSS {index}/{len(feeds)}] {feed['name']} · ошибка: {error} · {elapsed:.1f} с", flush=True)
            else:
                print(f"[RSS {index}/{len(feeds)}] {feed['name']} · публикаций: {len(feed_rows)} · {elapsed:.1f} с", flush=True)
    rows.sort(key=lambda row: (row["date"], row["post_id"]))
    deduped = {row.get("post_id"): row for row in rows if row.get("post_id")}
    rows = list(deduped.values())
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    report = {"start": start.isoformat(), "end": end.isoformat(), "feeds": len(feeds),
              "posts": len(rows), "errors": errors, "media_dir": str(media_dir.resolve())}
    (output_dir / "ingest_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[Ingest] готово: {len(rows)} публикаций, ошибок: {len(errors)}", flush=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/news_run")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    end = parse_date(args.end, datetime.now(UTC))
    start = parse_date(args.start, end - timedelta(hours=48))
    report = ingest(args.output_dir, start, end)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
