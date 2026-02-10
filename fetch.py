#!/usr/bin/env python3
"""
The Streamic RSS Feed Aggregator
Fetches, parses, and aggregates broadcast technology news from multiple sources

Changes (2026-02-10):
- Added new vendor feeds (validated/HTTPS) and category mapping per request:
  • Streaming: Haivision, Telestream, Bitmovin
  • Infrastructure: Avid (Press Releases), Adobe (Developer Blog)
- Removed feeds per request: Dacast, OnTheFly, YoloLiv, TechCrunch, Engadget, WIRED
- Kept Cloudflare Worker in place for all other feeds; new/selected feeds bypass via DIRECT_FEEDS.
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
# Sources verified:
# - Haivision Blog page (WordPress; /feed is standard) [1](https://www.haivision.com/blog/)
# - Telestream Blog RSS feed endpoint (WordPress) [2](https://blog.telestream.com/feed/)
# - Bitmovin Blog (no native RSS exposed consistently; use OpenRSS over HTTPS) [3](https://bitmovin.com/blog/)[4](https://chesa.com/podcast/5-just-the-facts-mam/)
# - Avid Press Releases (Notified RSS endpoint) [5](https://api.client.notified.com/api/rss/publish/view/47032?type=press)
# - Adobe Developer Blog (OpenRSS wrapper of official developer blog) [6](https://blog.developer.adobe.com/)[4](https://chesa.com/podcast/5-just-the-facts-mam/)
DIRECT_FEEDS = [
    # Streaming category (keep)
    'https://www.streamingmediablog.com/feed',                 # Dan Rayburn / Streaming Media Blog
    'https://www.broadcastnow.co.uk/full-rss/',                # BroadcastNow full RSS

    # NEW Streaming vendor feeds
    'https://www.haivision.com/feed/',                         # Haivision blog feed [1](https://www.haivision.com/blog/)
    'https://blog.telestream.com/feed/',                       # Telestream blog feed [2](https://blog.telestream.com/feed/)
    'https://openrss.org/https://bitmovin.com/blog/',          # Bitmovin blog via OpenRSS [3](https://bitmovin.com/blog/)[4](https://chesa.com/podcast/5-just-the-facts-mam/)

    # Infrastructure - MAM/PAM & vendor platforms
    'https://api.client.notified.com/api/rss/publish/view/47032?type=press',  # Avid Press Releases RSS (Notified) [5](https://api.client.notified.com/api/rss/publish/view/47032?type=press)
    'https://openrss.org/https://blog.developer.adobe.com/',   # Adobe Developers Blog via OpenRSS [6](https://blog.developer.adobe.com/)[4](https://chesa.com/podcast/5-just-the-facts-mam/)

    # Existing Infrastructure feeds retained
    'https://chesa.com/feed',                                   # CHESA (MAM/PAM)
    'https://cloudinary.com/blog/feed',                         # Cloudinary (MAM/DAM)

    # Storage
    'https://www.studionetworksolutions.com/feed',              # SNS (storage/security)
    'https://openrss.org/https://scalelogicinc.com/blog/protecting-valuable-media-assets/',
    'https://openrss.org/https://qsan.io/solutions/media-production/',
    'https://openrss.org/https://www.keycodemedia.com/capabilities/media-shared-storage-cloud-storage/',

    # Production Ops
    'https://www.processexcellencenetwork.com/rss-feeds',

    # Legacy direct fetch kept
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

        # NEW: Avid (Press Releases) + Adobe Developers (Infrastructure)
        'https://api.client.notified.com/api/rss/publish/view/47032?type=press',   # Avid Press Releases [5](https://api.client.notified.com/api/rss/publish/view/47032?type=press)
        'https://openrss.org/https://blog.developer.adobe.com/',                   # Adobe Developers Blog (OpenRSS) [6](https://blog.developer.adobe.com/)[4](https://chesa.com/podcast/5-just-the-facts-mam/)

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

        # Core streaming sources (kept)
        'https://www.streamingmediablog.com/feed',
        'https://www.broadcastnow.co.uk/full-rss/',

        # NEW vendor streaming feeds (encode/low-latency/CDN)
        'https://www.haivision.com/feed/',                        # Haivision (SRT, low-latency) [1](https://www.haivision.com/blog/)
        'https://blog.telestream.com/feed/',                      # Telestream (Vantage, supply chain) [2](https://blog.telestream.com/feed/)
        'https://openrss.org/https://bitmovin.com/blog/'          # Bitmovin (HLS/DASH, player, compression) [3](https://bitmovin.com/blog/)[4](https://chesa.com/podcast/5-just-the-facts-mam/)
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
    """Check if feed should bypass Cloudflare Worker"""
    return feed_url in DIRECT_FEEDS

def fetch_feed_via_worker(feed_url):
    """Fetch feed through Cloudflare Worker"""
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
        print(f" ⚠ Worker error for {feed_url[:50]}: {e}")
        return None

def fetch_feed_direct(feed_url):
    """Fetch feed directly without worker"""
    try:
        response = requests.get(
            feed_url,
            timeout=FEED_FETCH_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; TheStreamic/1.0)'}
        )
        if response.status_code == 200:
