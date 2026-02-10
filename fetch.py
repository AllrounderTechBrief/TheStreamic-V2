#!/usr/bin/env python3
"""
The Streamic RSS Feed Aggregator
Fetches, parses, and aggregates broadcast technology news from multiple sources

Changes (2026-02-10):
- Added new vendor feeds (validated/HTTPS) and category mapping per request:
  • Streaming: Haivision, Telestream, Bitmovin
  • Infrastructure: Avid Press Releases, Adobe Developer Blog
- Removed feeds: Dacast, OnTheFly, YoloLiv, TechCrunch, Engadget, Wired
- Fixed indentation errors in extract_image_from_entry()
- Kept Cloudflare Worker for all non-direct feeds
"""

import feedparser
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote
import requests
from pathlib import Path

# ===== CONFIGURATION =====
CLOUDFLARE_WORKER = "https://rss-proxy.prerak-mehta.workers.dev"
DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "news.json"
ARCHIVE_FILE = DATA_DIR / "archive.json"

# Performance settings
MAX_ITEMS_PER_FEED = 20
FEED_FETCH_TIMEOUT = 12
ARTICLE_FETCH_TIMEOUT = 5
MAX_ARTICLE_FETCHES = 8

# Balancing settings
MIN_PER_CATEGORY = 18
MIN_REQUIRED_EACH = 3
MAX_NEWS_ITEMS = 300

# ===== DIRECT FETCH FEEDS (Bypass Cloudflare Worker) =====
DIRECT_FEEDS = [
    # Streaming (kept)
    'https://www.streamingmediablog.com/feed',
    'https://www.broadcastnow.co.uk/full-rss/',

    # NEW Streaming vendors
    'https://www.haivision.com/feed/',
    'https://blog.telestream.com/feed/',
    'https://openrss.org/https://bitmovin.com/blog/',

    # Infrastructure – Avid + Adobe
    'https://api.client.notified.com/api/rss/publish/view/47032?type=press',
    'https://openrss.org/https://blog.developer.adobe.com/',

    # Existing MAM/PAM
    'https://chesa.com/feed',
    'https://cloudinary.com/blog/feed',

    # Existing Storage
    'https://www.studionetworksolutions.com/feed',
    'https://openrss.org/https://scalelogicinc.com/blog/protecting-valuable-media-assets/',
    'https://openrss.org/https://qsan.io/solutions/media-production/',
    'https://openrss.org/https://www.keycodemedia.com/capabilities/media-shared-storage-cloud-storage/',

    # Production Ops
    'https://www.processexcellencenetwork.com/rss-feeds',

    # Legacy direct feeds
    'https://www.inbroadcast.com/rss.xml',
    'https://www.imaginecommunications.com/news/rss.xml'
]

# ===== FEED GROUPS =====
FEED_GROUPS = {
    'newsroom': [
        'https://www.newscaststudio.com/feed/',
        'https://www.tvtechnology.com/news/rss.xml',
        'https://www.broadcastbeat.com/feed/',
        'https://www.svgeurope.org/feed/'
    ],

    'playout': [
        'https://www.inbroadcast.com/rss.xml',
        'https://www.tvtechnology.com/playout/rss.xml',
        'https://www.rossvideo.com/news/feed/',
        'https://www.harmonicinc.com/insights/blog/rss.xml',
        'https://www.evertz.com/news/rss',
        'https://www.imaginecommunications.com/news/rss.xml'
    ],

    'infrastructure': [
        'https://www.thebroadcastbridge.com/rss/infrastructure',
        'https://www.tvtechnology.com/infrastructure/rss.xml',
        'https://www.broadcastbridge.com/rss/security',
        'https://www.tvtechnology.com/security/rss.xml',
        'https://aws.amazon.com/security/blog/feed/',
        'https://krebsonsecurity.com/feed/',
        'https://www.darkreading.com/rss.xml',
        'https://www.bleepingcomputer.com/feed/',
        'https://www.securityweek.com/feed/',
        'https://feeds.feedburner.com/TheHackerNews',
        'https://cloud.google.com/blog/topics/security/rss/',
        'https://www.microsoft.com/en-us/security/blog/feed/',

        # MAM/PAM
        'https://chesa.com/feed',
        'https://cloudinary.com/blog/feed',

        # NEW Avid (Press Releases)
        'https://api.client.notified.com/api/rss/publish/view/47032?type=press',

        # NEW Adobe Developer Blog
        'https://openrss.org/https://blog.developer.adobe.com/',

        # Storage
        'https://www.studionetworksolutions.com/feed',
        'https://openrss.org/https://scalelogicinc.com/blog/protecting-valuable-media-assets/',
        'https://openrss.org/https://qsan.io/solutions/media-production/',
        'https://openrss.org/https://www.keycodemedia.com/capabilities/media-shared-storage-cloud-storage/',

        # Production Ops
        'https://www.processexcellencenetwork.com/rss-feeds'
    ],

    'graphics': [
        'https://www.thebroadcastbridge.com/rss/graphics',
        'https://www.tvtechnology.com/graphics/rss.xml',
        'https://www.vizrt.com/news/rss',
        'https://routing.vizrt.com/rss',
        'https://motionographer.com/feed/'
    ],

    'cloud': [
        'https://www.thebroadcastbridge.com/rss/cloud',
        'https://www.tvtechnology.com/cloud/rss.xml',
        'https://aws.amazon.com/blogs/media/feed/',
        'https://blog.frame.io/feed/'
    ],

    'streaming': [
        'https://www.thebroadcastbridge.com/rss/streaming',
        'https://www.tvtechnology.com/streaming/rss.xml',

        # Streaming core
        'https://www.streamingmediablog.com/feed',
        'https://www.broadcastnow.co.uk/full-rss/',

        # NEW streaming tech vendors
        'https://www.haivision.com/feed/',
        'https://blog.telestream.com/feed/',
        'https://openrss.org/https://bitmovin.com/blog/'
    ],

    'audio-ai': [
        'https://www.thebroadcastbridge.com/rss/audio',
        'https://www.tvtechnology.com/audio/rss.xml',
        'https://www.thebroadcastbridge.com/rss/ai',
        'https://www.tvtechnology.com/ai/rss.xml'
    ]
}

# ===== HELPER FUNCTIONS =====
def should_use_direct_fetch(feed_url):
    return feed_url in DIRECT_FEEDS

def fetch_feed_via_worker(feed_url):
    try:
        encoded = quote(feed_url, safe='')
        url = f"{CLOUDFLARE_WORKER}/?url={encoded}"
        r = requests.get(url, timeout=FEED_FETCH_TIMEOUT, headers={'User-Agent':'Mozilla/5.0'})
        if r.status_code == 200:
            return feedparser.parse(r.content)
        return None
    except Exception as e:
        print(f" ⚠ Worker error: {feed_url} → {e}")
        return None

def fetch_feed_direct(feed_url):
    try:
        r = requests.get(feed_url, timeout=FEED_FETCH_TIMEOUT, headers={'User-Agent':'Mozilla/5.0'})
        if r.status_code == 200:
            return feedparser.parse(r.content)
        return None
    except Exception as e:
        print(f" ⚠ Direct error: {feed_url} → {e}")
        return None

def fetch_feed_with_fallback(feed_url):
    if should_use_direct_fetch(feed_url):
        print(f" → Direct fetch: {feed_url}")
        feed = fetch_feed_direct(feed_url)
        return feed
    feed = fetch_feed_via_worker(feed_url)
    if feed:
        return feed
    return fetch_feed_direct(feed_url)

# ===== FIXED VERSION OF extract_image_from_entry() =====
def extract_image_from_entry(entry):
    """Extract image URL with multiple fallback strategies"""

    # 1. media:content
    if hasattr(entry, 'media_content'):
        for media in entry.media_content:
            if media.get('url'):
                return media['url']

    # 2. media:thumbnail
    if hasattr(entry, 'media_thumbnail'):
        for thumb in entry.media_thumbnail:
            if thumb.get('url'):
                return thumb['url']

    # 3. enclosure
    if hasattr(entry, 'enclosures'):
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                return enc.get('href') or enc.get('url')

    # 4. parse from description HTML
    desc = entry.get('description', '') or entry.get('summary', '')
    if desc:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc, re.IGNORECASE)
        if match:
            img = match.group(1)
            if not any(bad in img.lower() for bad in ['1x1','pixel','tracker','spacer']):
                return img

    # 5. Try reduced-quality variant if needed
    if hasattr(entry, 'media_content'):
        for media in entry.media_content:
            url = media.get('url', '')
            if url and ('w=' in url or 'width=' in url):
                url = re.sub(r'(w|width)=\d+', r'\1=400', url)
                url = re.sub(r'(h|height)=\d+', r'\1=300', url)
                url = re.sub(r'(q|quality)=\d+', r'\1=60', url)
                return url

    return None

def extract_og_image(article_url, timeout=ARTICLE_FETCH_TIMEOUT):
    try:
        r = requests.get(article_url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            return None
        html = r.text[:50000]

        # og:image
        og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og:
            return og.group(1)

        # twitter:image
        tw = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if tw:
            return tw.group(1)

        return None
    except:
        return None

def process_entries(entries, category, source_name):
    items = []
    fetch_count = 0

    for entry in entries:
        try:
            title = entry.get('title', '').strip()
            link = entry.get('link', '').strip()
            guid = entry.get('id', link)
            if not title or not link:
                continue

            image = extract_image_from_entry(entry)
            if not image and fetch_count < MAX_ARTICLE_FETCHES:
                image = extract_og_image(link)
                fetch_count += 1

            pub = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                except:
                    pass
            if not pub:
                pub = datetime.now(timezone.utc).isoformat()

            items.append({
                'title': title,
                'link': link,
                'guid': guid,
                'category': category,
                'source': source_name,
                'image': image,
                'pubDate': pub,
                'timestamp': int(time.time())
            })
        except Exception as e:
            print(f" ⚠ Entry error: {e}")
            continue

    return items

def get_source_name(url):
    u = url.lower()

    # Streaming
    if 'streamingmediablog' in u: return 'Streaming Media Blog'
    if 'broadcastnow' in u: return 'Broadcast Now'
    if 'haivision' in u: return 'Haivision'
    if 'telestream' in u: return 'Telestream'
    if 'bitmovin' in u: return 'Bitmovin'

    # Infra
    if 'chesa' in u: return 'Chesa'
    if 'cloudinary' in u: return 'Cloudinary'
    if 'studionetworksolutions' in u: return 'Studio Network Solutions'
    if 'scalelogicinc' in u: return 'ScaleLogic'
    if 'qsan.io' in u: return 'QSAN'
    if 'keycodemedia' in u: return 'Keycode Media'
    if 'processexcellencenetwork' in u: return 'Process Excellence Network'
    if 'api.client.notified.com' in u and 'type=press' in u: return 'Avid Press Room'
    if 'developer.adobe.com' in u: return 'Adobe Developer Blog'

    # Others fallback
    return "Technology News"

def validate_news_data(items):
    counts = {}
    for i in items:
        counts[i['category']] = counts.get(i['category'], 0) + 1

    print("\n📊 Category distribution:")
    for cat, count in counts.items():
        mark = "✓" if count >= MIN_REQUIRED_EACH else "⚠"
        print(f" {mark} {cat}: {count}")

    return all(count >= MIN_REQUIRED_EACH for count in counts.values())

def dedupe(items):
    seen = set()
    out = []
    for i in items:
        g = i.get('guid', '')
        if g not in seen:
            seen.add(g)
            out.append(i)
    return out

def balance_categories(items):
    items = dedupe(items)
    grouped = {}
    for i in items:
        grouped.setdefault(i['category'], []).append(i)

    for cat in grouped:
        grouped[cat].sort(key=lambda x: x['pubDate'], reverse=True)

    final = []
    for cat, group_items in grouped.items():
        final.extend(group_items[:MIN_PER_CATEGORY])

    final.sort(key=lambda x: x['pubDate'], reverse=True)
    return final[:MAX_NEWS_ITEMS]

def save_json(data, file):
    tmp = file.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(file)

def main():
    print("🚀 Starting aggregator\n")
    DATA_DIR.mkdir(exist_ok=True)

    all_items = []

    for cat, urls in FEED_GROUPS.items():
        print(f"\n📰 {cat.upper()} ({len(urls)} feeds)")
        for url in urls:
            feed = fetch_feed_with_fallback(url)
            if not feed or not feed.entries:
                print(f" ⚠ No entries: {url}")
                continue
            src = get_source_name(url)
            entries = feed.entries[:MAX_ITEMS_PER_FEED]
            processed = process_entries(entries, cat, src)
            print(f" ✓ {src}: {len(processed)}")
            all_items.extend(processed)

    print(f"\nCollected: {len(all_items)}")
    if not all_items:
        print("❌ No items. Stop.")
        return

    balanced = balance_categories(all_items)
    print(f"Balanced: {len(balanced)} items")

    valid = validate_news_data(balanced)

    if OUTPUT_FILE.exists():
        if valid:
            if ARCHIVE_FILE.exists(): ARCHIVE_FILE.unlink()
            OUTPUT_FILE.rename(ARCHIVE_FILE)
        else:
            print("⚠ Validation failed. Keeping previous file.")
            return

    save_json(balanced, OUTPUT_FILE)
    print(f"Saved: {OUTPUT_FILE}")
    print("\n🎉 Done")

if __name__ == "__main__":
    main()
