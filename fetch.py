#!/usr/bin/env python3
"""
The Streamic - RSS Aggregator (Cloudflare + Fast + Fail-safe)
- Fetches all feeds via Cloudflare Worker proxy
- Caps items/ feed (fast)
- Optional (capped) article-page fetch for OG/Twitter image (OFF by default to avoid stalls)
- Short timeouts to prevent hanging in CI
- Balanced categories, atomic write, validation
- Fail-safe: never publish a blank site, even if validation fails on a first run
"""

import json
import time
import re
import os
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from collections import defaultdict

# ------------------ SETTINGS ------------------

# Your Cloudflare Worker passthrough (XML)
WORKER_BASE = "https://broken-king-b4dc.itabmum.workers.dev/?url="  # change only if your Worker URL changes

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"
ARCHIVE_FILE = DATA_DIR / "archive.json"

# Total items to keep in news.json
MAX_NEWS_ITEMS = 300

# Min per category (balanced output)
MIN_PER_CATEGORY = 15

# Validation: categories that must be present (threshold below)
REQUIRED_CATEGORIES = {
    "newsroom", "playout", "infrastructure", "graphics", "cloud", "streaming", "audio-ai"
}
MIN_REQUIRED_EACH = 5

# --- Fast & Stable knobs ---
MAX_ITEMS_PER_FEED = 15      # parse at most N items per feed (fast)
FEED_FETCH_TIMEOUT = 12      # seconds per RSS fetch via Worker
ARTICLE_FETCH_TIMEOUT = 5    # seconds per article HTML fetch (for OG image)
MAX_ARTICLE_FETCHES = 0      # <-- 0 = OFF (safest). Later, set 4..8 if you want better thumbnails.

# Global counter for article fetches (do not edit)
ARTICLE_FETCH_COUNT = 0

# ------------------ FEED SOURCES ------------------
FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.newscaststudio.com/tag/news-production/feed/", "label": "NewscastStudio"},
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Tech"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"}
    ],
    "playout": [
        {"url": "https://www.inbroadcast.com/rss.xml", "label": "InBroadcast"},
        {"url": "https://www.tvtechnology.com/playout/rss.xml", "label": "TV Tech Playout"},
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://www.harmonicinc.com/insights/blog/rss.xml", "label": "Harmonic"},
    ],
    "infrastructure": [
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
        {"url": "https://www.thebroadcastbridge.com/rss/all", "label": "Broadcast Bridge"},
        {"url": "https://www.newscaststudio.com/category/broadcast-engineering/feed/", "label": "NewscastStudio Engineering"},
    ],
    "graphics": [
        {"url": "https://www.newscaststudio.com/tag/tv-news-graphics/feed/", "label": "NewscastStudio Graphics"},
        {"url": "https://www.vizrt.com/feed/", "label": "Vizrt News"},
        {"url": "https://motionographer.com/feed/", "label": "Motionographer"},
    ],
    "cloud": [
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media Blog"},
        {"url": "https://www.tvtechnology.com/cloud/rss.xml", "label": "TV Tech Cloud"},
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
    ],
    "streaming": [
        {"url": "https://www.tvtechnology.com/platform/streaming/rss.xml", "label": "TV Tech Streaming"},
        {"url": "https://www.tvtechnology.com/business/rss.xml", "label": "TV Tech Business"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"},
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
        {"url": "https://www.inbroadcast.com/rss.xml", "label": "InBroadcast"},
    ],
    "audio-ai": [
        {"url": "https://www.tvtechnology.com/production/rss.xml", "label": "TV Tech Production"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"},
        {"url": "https://www.newscaststudio.com/tag/audio/feed/", "label": "NewscastStudio Audio"},
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
    ]
}

# ------------------ HELPERS ------------------

class ImageScraper(HTMLParser):
    """Find first <img src=...> inside HTML content."""
    def __init__(self):
        super().__init__()
        self.image_url = None
    def handle_starttag(self, tag, attrs):
        if tag == "img" and not self.image_url:
            for a, v in attrs:
                if a == "src" and v and any(ext in v.lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
                    self.image_url = v

def try_extract_image_from_text(html_text: str) -> str:
    if not html_text:
        return ""
    m = re.search(r'(https?://[^\s"<>]+\.(?:jpg|jpeg|png|gif|webp))', html_text, re.IGNORECASE)
    return m.group(1) if m else ""

def fetch_url(url: str, timeout: int):
    """HTTP GET with UA and timeout; returns bytes or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        return None

def fetch_html(url: str, timeout: int) -> str:
    """Fetch article HTML (short timeout)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except:
        return ""

def get_og_twitter_image(html: str) -> str:
    """Extract og:image or twitter:image via regex (no DOM)."""
    if not html:
        return ""
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            u = m.group(1).strip()
            if u.startswith("http://") or u.startswith("https://"):
                return u
    return ""

def good_img_url(url: str) -> bool:
    if not url: return False
    u = url.strip()
    if u.startswith("//"): u = "https:" + u
    if not u.startswith(("http://","https://")): return False
    reject = ["1x1", "spacer", "blank", "pixel", "data:image", "avatar", "gravatar"]
    return not any(r in u.lower() for r in reject)

def get_best_image(item_xml) -> str:
    """
    1) RSS media:content / media:thumbnail / enclosure
    2) <img> inside description/content
    3) (CAPPED) article HTML for og:image / twitter:image
    """
    global ARTICLE_FETCH_COUNT

    candidates = []
    media_ns = "{http://search.yahoo.com/mrss/}"

    # media:content / media:thumbnail
    for elem in [item_xml.find(f"{media_ns}content"), item_xml.find(f"{media_ns}thumbnail")]:
        if elem is not None and elem.get("url"):
            candidates.append(elem.get("url"))

    # enclosure
    enc = item_xml.find("enclosure")
    if enc is not None and "image" in (enc.get("type", "") or "") and enc.get("url"):
        candidates.append(enc.get("url"))

    # description & content:encoded
    for tag_name in ["description", "{http://purl.org/rss/1.0/modules/content/}encoded"]:
        elem = item_xml.find(tag_name)
        if elem is not None and elem.text:
            parser = ImageScraper()
            try:
                parser.feed(elem.text)
            except Exception:
                pass
            if parser.image_url:
                candidates.append(parser.image_url)
            rx = try_extract_image_from_text(elem.text)
            if rx:
                candidates.append(rx)

    # pick first good
    for url in candidates:
        if good_img_url(url):
            return url.strip()

    # FINAL: article HTML (only a few per run; OFF by default)
    link_elem = item_xml.find("link")
    link_url = (link_elem.text or "").strip() if link_elem is not None and link_elem.text else ""
    if link_url and MAX_ARTICLE_FETCHES > 0 and ARTICLE_FETCH_COUNT < MAX_ARTICLE_FETCHES:
        ARTICLE_FETCH_COUNT += 1
        html = fetch_html(link_url, timeout=ARTICLE_FETCH_TIMEOUT)
        og = get_og_twitter_image(html)
        if good_img_url(og):
            return og

    return ""

def parse_rss_feed(xml_data: bytes, category: str, source_label: str):
    """Parse RSS XML into a list of items (capped)."""
    items = []
    if not xml_data:
        return items
    try:
        root = ET.fromstring(xml_data)
        count = 0
        for item in root.findall(".//item"):
            if count >= MAX_ITEMS_PER_FEED:
                break
            title_elem = item.find("title")
            link_elem = item.find("link")
            guid_elem = item.find("guid")

            title = unescape(title_elem.text).strip() if title_elem is not None and title_elem.text else "Untitled"
            link = (link_elem.text or "").strip() if link_elem is not None and link_elem.text else "#"
            guid = guid_elem.text if guid_elem is not None and guid_elem.text else link

            items.append({
                "guid": guid,
                "title": title,
                "link": link,
                "category": category,
                "image": get_best_image(item),
                "source": source_label,
                "timestamp": datetime.now().isoformat()
            })
            count += 1
        return items
    except Exception:
        return []

def balance_by_category(items: list, max_total: int, min_per_cat: int):
    """Guarantee min_per_cat items/category, then fill by global recency."""
    by_cat = defaultdict(list)
    for it in items:
        c = (it.get("category") or "").lower()
        by_cat[c].append(it)
    for c in by_cat:
        by_cat[c].sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    picked = []
    # baseline per category
    for c, arr in by_cat.items():
        picked.extend(arr[:min_per_cat])

    # remaining by recency
    remaining = []
    for c, arr in by_cat.items():
        remaining.extend(arr[min_per_cat:])
    remaining.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    remaining_slots = max_total - len(picked)
    if remaining_slots > 0:
        picked.extend(remaining[:remaining_slots])

    # dedupe by GUID
    seen, final = set(), []
    for it in picked:
        gid = it.get("guid")
        if gid and gid not in seen:
            seen.add(gid)
            final.append(it)
    return final[:max_total]

def atomic_write_json(path: Path, data: list):
    """Atomic write to avoid partial/corrupted files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile('w', delete=False, dir=str(path.parent), encoding='utf-8') as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp_name = tmp.name
    os.replace(tmp_name, str(path))

def validate_categories(items: list, required: set, min_each: int):
    """Return list of categories missing or below min_each."""
    counts = defaultdict(int)
    for it in items:
        c = (it.get("category") or "").lower()
        counts[c] += 1
    missing = [c for c in sorted(required) if counts.get(c, 0) < min_each]
    return missing, counts

# ------------------ WORKFLOW ------------------

def run_workflow():
    global ARTICLE_FETCH_COUNT
    ARTICLE_FETCH_COUNT = 0

    print("=" * 70)
    print(" THE STREAMIC — Cloudflare + Fast + Fail-safe ")
    print("=" * 70)

    DATA_DIR.mkdir(exist_ok=True)

    all_new_items = []
    per_feed_stats = []

    # 1) Fetch all feeds via Cloudflare Worker
    for category, feeds in FEED_SOURCES.items():
        print(f"\n▶ {category.upper()}\n" + "-" * 70)
        for fd in feeds:
            label = fd["label"]
            feed_url = fd["url"]
            proxy = (WORKER_BASE or "") + feed_url if WORKER_BASE else feed_url

            print(f"{label:40s}", end="", flush=True)
            xml = fetch_url(proxy, timeout=FEED_FETCH_TIMEOUT)
            if not xml:
                print(" ✗ failed")
                continue

            items = parse_rss_feed(xml, category, label)
            print(f" ✓ {len(items):2d} items (cap {MAX_ITEMS_PER_FEED})")
            all_new_items.extend(items)
            per_feed_stats.append((label, len(items)))
            time.sleep(0.05)  # brief pause

    # 2) Load existing for fallback/validation
    existing = []
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # 3) Merge, newest-first
    merged = all_new_items + existing
    merged.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 4) Balance categories
    final_list = balance_by_category(merged, max_total=MAX_NEWS_ITEMS, min_per_cat=MIN_PER_CATEGORY)

    # 5) Validate before publishing
    missing, counts = validate_categories(final_list, REQUIRED_CATEGORIES, MIN_REQUIRED_EACH)

    print("\nSUMMARY (post-balance):")
    for c in sorted(counts.keys()):
        print(f"  {c:16s}: {counts[c]:3d}")
    print(f"\nArticle fetch attempts (OG images): {ARTICLE_FETCH_COUNT}/{MAX_ARTICLE_FETCHES}")

    # ---- FAIL-SAFE ----
    # If validation failed and there's NO existing news.json, publish a usable file anyway
    if missing and not existing:
        print("\n⚠ Validation failed & no existing news.json; writing unbalanced dataset to avoid blank site.")
        atomic_write_json(NEWS_FILE, merged[:MAX_NEWS_ITEMS])
        print(f"✔ Saved {min(len(merged), MAX_NEWS_ITEMS)} items to {NEWS_FILE} (fail-safe)")
        print("=" * 70)
        return

    # If validation failed but we HAVE an existing file, keep existing (avoid regressions)
    if missing and existing:
        print("\n✗ Validation failed. Keeping existing news.json to avoid blank sections.")
        print("=" * 70)
        return

    # 6) Optional backup
    try:
        if NEWS_FILE.exists():
            old = []
            try:
                with open(NEWS_FILE, "r", encoding="utf-8") as f:
                    old = json.load(f)
            except Exception:
                pass
            if old:
                with open(ARCHIVE_FILE, "w", encoding="utf-8") as b:
                    json.dump(old, b, indent=2, ensure_ascii=False)
                print(f"\nBackup saved to {ARCHIVE_FILE}")
    except Exception as e:
        print("Backup skipped:", e)

    # 7) Atomic write
    atomic_write_json(NEWS_FILE, final_list)
    print(f"\n✔ Saved {len(final_list)} items to {NEWS_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    run_workflow()
