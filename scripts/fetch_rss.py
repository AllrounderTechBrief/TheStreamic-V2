"""
scripts/fetch_rss.py
====================
Reads data/feeds.json, fetches each feed with feedparser, and writes
metadata-only records to data/news.json.

Rules:
- Stores ONLY: guid, title, url, published, teaser[:280]
- NO body text, NO images from feeds (copyright safety)
- Deduplicates by url per category, keeps max 40 per category
- Encoding: UTF-8 without BOM
"""

import json
import os
import re
import time
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
from bs4 import BeautifulSoup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FEEDS_F = os.path.join(ROOT, "data", "feeds.json")
NEWS_F  = os.path.join(ROOT, "data", "news.json")

MAX_PER_CAT = 80
FETCH_TIMEOUT = 20


def clean_html(raw: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    # Remove common RSS boilerplate suffixes
    text = re.sub(
        r"\s*(appeared first on|the post .{0,80}|read more\.?|\[…\]|\[…\])\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def parse_published(entry) -> str:
    """Return ISO-8601 date string from entry, fallback to today."""
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        try:
            return datetime(*t[:6], tzinfo=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def entry_guid(entry) -> str:
    """Stable unique ID for an entry."""
    raw = entry.get("id") or entry.get("link") or entry.get("title") or ""
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def fetch_category(category: str, urls: list) -> list:
    """Fetch all feeds for one category; return deduped list of dicts."""
    seen_urls: set = set()
    items: list = []

    for feed_url in urls:
        try:
            feed = feedparser.parse(feed_url, request_headers={"User-Agent": "TheStreamicBot/1.0"})
        except Exception as exc:
            print(f"  ⚠  {feed_url[:60]} → {exc}")
            continue

        source_host = urlparse(feed_url).netloc.lstrip("www.")

        for entry in feed.entries[:50]:
            url = (entry.get("link") or "").strip()
            if not url or url in seen_urls:
                continue

            title = clean_html(entry.get("title") or "")
            if not title:
                continue

            # Teaser: prefer summary, fall back to description — metadata only
            raw_sum = (
                entry.get("summary")
                or entry.get("description")
                or ""
            )
            teaser = clean_html(raw_sum)[:280]

            items.append(
                {
                    "guid":      entry_guid(entry),
                    "category":  category,
                    "title":     title,
                    "url":       url,
                    "source":    source_host,
                    "published": parse_published(entry),
                    "teaser":    teaser,
                }
            )
            seen_urls.add(url)

        time.sleep(0.3)  # polite crawl delay

    # Sort newest first; keep cap
    items.sort(key=lambda x: x["published"], reverse=True)
    return items[:MAX_PER_CAT]


def main():
    with open(FEEDS_F, "r", encoding="utf-8") as f:
        feeds: dict = json.load(f)

    news: dict = {}
    total = 0

    for category, urls in feeds.items():
        print(f"Fetching: {category} ({len(urls)} feeds)")
        items = fetch_category(category, urls)
        news[category] = items
        total += len(items)
        print(f"  → {len(items)} items")

    os.makedirs(os.path.dirname(NEWS_F), exist_ok=True)
    with open(NEWS_F, "w", encoding="utf-8") as f:
        json.dump(news, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Wrote {total} items across {len(news)} categories → data/news.json")


if __name__ == "__main__":
    main()
