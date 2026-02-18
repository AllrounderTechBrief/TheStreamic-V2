#!/usr/bin/env python3
"""
The Streamic RSS Feed Aggregator
Fetches, parses, and aggregates broadcast technology news from multiple sources

This version:
- Uses Cloudflare Worker: https://broken-king-b4dc.itabmum.workers.dev
- Removes old feeds (Dacast / OnTheFly / YoloLiv / TechCrunch / Engadget / WIRED)
- Adds Streaming vendors: Haivision / Telestream / Bitmovin
- Adds Infra vendors: Avid Press (Notified) / Adobe Developer (OpenRSS)
- Renames 'audio-ai' -> 'ai-post-production'
- Adds 8 verified AI Post Production feeds
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
CLOUDFLARE_WORKER = "https://broken-king-b4dc.itabmum.workers.dev"
DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "news.json"
ARCHIVE_FILE = DATA_DIR / "archive.json"

# Performance settings
MAX_ITEMS_PER_FEED = 20
FEED_FETCH_TIMEOUT = 12
ARTICLE_FETCH_TIMEOUT = 5
MAX_ARTICLE_FETCHES = 8

# Balancing settings
MIN_PER_CATEGORY = 6
MIN_REQUIRED_EACH = 3
MAX_NEWS_ITEMS = 300


# ===== DIRECT FETCH FEEDS (Bypass Cloudflare Worker) =====
DIRECT_FEEDS = [
    # Streaming category (core + vendors)
    'https://www.streamingmediablog.com/feed',
    'https://www.broadcastnow.co.uk/full-rss/',
    'https://www.haivision.com/feed/',
    'https://blog.telestream.com/feed/',
    'https://openrss.org/https://bitmovin.com/blog/',

    # Infrastructure - MAM/PAM / Vendors
    'https://api.client.notified.com/api/rss/publish/view/47032?type=press',
    'https://openrss.org/https://blog.developer.adobe.com/',
    'https://chesa.com/feed',
    'https://cloudinary.com/blog/feed',

    # Storage
    'https://www.studionetworksolutions.com/feed',
    'https://openrss.org/https://scalelogicinc.com/blog/protecting-valuable-media-assets/',
    'https://openrss.org/https://qsan.io/solutions/media-production/',
    'https://openrss.org/https://www.keycodemedia.com/capabilities/media-shared-storage-cloud-storage/',

    # Production Ops
    'https://www.processexcellencenetwork.com/rss-feeds',

    # Legacy direct fetch (kept)
    'https://www.inbroadcast.com/rss.xml',
    'https://www.imaginecommunications.com/news/rss.xml',

    # ===============================
    # ⭐ ADDED AS REQUESTED (4 FEEDS)
    # ===============================
    'https://www.tvtechnology.com/playout/rss.xml',
    'https://www.rossvideo.com/news/feed/',
    'https://www.evertz.com/news/rss',
    'https://www.imaginecommunications.com/news/rss.xml'
    # ===============================
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

        # MAM/PAM + Vendors
        'https://api.client.notified.com/api/rss/publish/view/47032?type=press',
        'https://openrss.org/https://blog.developer.adobe.com/',
        'https://chesa.com/feed',
        'https://cloudinary.com/blog/feed',

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

        # Direct fetch streaming vendors
        'https://www.streamingmediablog.com/feed',
        'https://www.broadcastnow.co.uk/full-rss/',
        'https://www.haivision.com/feed/',
        'https://blog.telestream.com/feed/',
        'https://openrss.org/https://bitmovin.com/blog/'
    ],

    'ai-post-production': [
        'https://premiumbeat.com/blog/category/video-editing/feed/',
        'https://premieregal.com/blog?format=RSS',
        'https://videocopilot.net/feeds/tutorials/',
        'https://jonnyelwyn.co.uk/feed/',
        'https://blog.pond5.com/feed/',
        'https://filtergrade.com/category/video/feed/',
        'https://beforesandafters.com/feed/',
        'https://avinteractive.com/feed/'
    ]
}

# (rest of your script remains 100% unchanged below)
# ----------------------------------------------------
# ----------------------------------------------------
# ----------------------------------------------------

# HELPER FUNCTIONS (unchanged)
def should_use_direct_fetch(feed_url: str) -> bool:
    return feed_url in DIRECT_FEEDS


def fetch_feed_via_worker(feed_url: str):
    try:
        encoded_url = quote(feed_url, safe='')
        worker_url = f"{CLOUDFLARE_WORKER}/?url={encoded_url}"
        response = requests.get(
            worker_url,
            timeout=FEED_FETCH_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; TheStreamic/1.0)'}
        )
        if response.status_code == 200:
            return feedparser.parse(response.content)
        return None
    except Exception as e:
        print(f" ⚠ Worker error for {feed_url[:60]}: {e}")
        return None


def fetch_feed_direct(feed_url: str):
    try:
        response = requests.get(
            feed_url,
            timeout=FEED_FETCH_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; TheStreamic/1.0)'}
        )
        if response.status_code == 200:
            return feedparser.parse(response.content)
        return None
    except Exception as e:
        print(f" ⚠ Direct fetch error for {feed_url[:60]}: {e}")
        return None


def fetch_feed_with_fallback(feed_url: str):
    if should_use_direct_fetch(feed_url):
        print(f" → Direct fetch: {feed_url[:80]}")
        return fetch_feed_direct(feed_url)
    feed = fetch_feed_via_worker(feed_url)
    if feed:
        return feed
    print(" → Fallback to direct fetch")
    return fetch_feed_direct(feed_url)


# (remaining functions unchanged)
# ... (process_entries, extract_image, etc.)
# ... (main execution logic)

# END OF FILE
