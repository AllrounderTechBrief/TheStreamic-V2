#!/usr/bin/env python3
"""
The Streamic - Complete RSS Aggregator (V7.5)
- Streaming & Audio-AI robust:
  * RSS + Atom parsing
  * Unescape HTML before scanning for <img> / background-image
  * OpenGraph (og:image/twitter:image) fallback
  * Reject common placeholder/spinner images
  * Clear per-category summary
"""

import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
import re

# -----------------------------
# Config
# -----------------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"
MAX_NEWS_ITEMS = 180

# -----------------------------
# Feeds
# -----------------------------
FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.newscaststudio.com/feed/", "label": "NewscastStudio (All)"},
        {"url": "https://www.tvnewscheck.com/rss/", "label": "TVNewsCheck"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "BroadcastBeat"},
    ],
    "playout": [
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://www.harmonicinc.com/insights/blog/rss.xml", "label": "Harmonic"},
    ],
    "infrastructure": [
        {"url": "https://www.newscaststudio.com/category/broadcast-engineering/feed/", "label": "NewscastStudio Engineering"},
        {"url": "https://www.thebroadcastbridge.com/rss/all", "label": "Broadcast Bridge"},
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
    ],
    "graphics": [
        {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio Graphics"},
        {"url": "https://motionographer.com/feed/", "label": "Motionographer"},
    ],
    "cloud": [
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media Blog"},
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://azure.microsoft.com/en-us/blog/feed/", "label": "Azure Blog"},
    ],
    "streaming": [
        # StreamingMedia — Official public feeds
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews",     "label": "Streaming Media News"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedArticles", "label": "Streaming Media Articles"},
        {"url": "http://feeds.infotoday.com/Streaming-Media-Blog",                    "label": "Streaming Media Blog"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-IndustryNews",     "label": "Streaming Media Industry"},

        # Encoding / Transcoding / QC
        {"url": "https://www.telestream.net/company/press/rss.xml", "label": "Telestream"},

        # OTT Engineering
        {"url": "https://ottverse.com/feed/", "label": "OTTVerse"},

        # CDN / Delivery
        {"url": "https://blog.blazingcdn.com/en-us/feed/", "label": "BlazingCDN"},

        # OTT Platforms / Infra
        {"url": "https://vodlix.com/feed/", "label": "Vodlix"},

        # Streaming industry blog
        {"url": "https://streamingmediablog.com/feed", "label": "Dan Rayburn"},

        # Enterprise OTT architecture
        {"url": "https://www.globallogic.com/feed/", "label": "GlobalLogic OTT"},
    ],
    "audio-ai": [
        # Broadcast/Pro Audio
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},
        {"url": "https://www.radioworld.com/rss.xml", "label": "Radio World"},
        {"url": "https://www.waves.com/news-and-events/rss", "label": "Waves Audio"},
        {"url": "https://www.production-expert.com/production-expert-1?format=rss", "label": "Production Expert"},
        {"url": "https://www.avid.com/blog/rss.xml", "label": "Avid / Pro Tools"},

        # AoIP – Dante, AES67, Ravenna
        {"url": "https://www.audinate.com/feed", "label": "Audinate – Dante"},
        {"url": "https://www.merging.com/rss.xml", "label": "Merging – Ravenna/AES67"},

        # Cloud media (audio workflows overlap)
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},
    ],
}

# -----------------------------
# HTML helpers
# -----------------------------
class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and self.image_url is None:
            for k, v in attrs:
                if k == 'src' and v:
                    self.image_url = v

def _is_img_url(u):
    if not u or len(u) < 8:
        return False
    ul = u.lower()

    # reject obvious placeholders/pixels/spinners
    reject = (
        '1x1', 'pixel', 'spacer', 'blank', 'placeholder', 'default',
        'avatar', 'gravatar', 'data:image', 'base64', 'spinner.svg'
    )
    if any(b in ul for b in reject):
        return False

    # valid image ext (allow query/hash)
