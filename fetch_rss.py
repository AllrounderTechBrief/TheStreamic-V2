#!/usr/bin/env python3
import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import re
from html import unescape
from datetime import datetime
from pathlib import Path

# Configuration
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"

# Categorized Sources - Slugs must match HTML data-category exactly
FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"}
    ],
    "playout": [
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://imaginecommunications.com/feed/", "label": "Imagine"}
    ],
    "infrastructure": [
        {"url": "https://www.smpte.org/rss.xml", "label": "SMPTE"},
        {"url": "https://www.haivision.com/feed/", "label": "Haivision"}
    ],
    "graphics": [
        {"url": "https://www.vizrt.com/news/rss.xml", "label": "Vizrt"},
        {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio"}
    ],
    "cloud": [
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://www.adobe.com/video-audio.rss.xml", "label": "Adobe Cloud"}
    ],
    "streaming": [
        {"url": "https://www.streamingmedia.com/RSS/RSSFeed.aspx", "label": "Streaming Media"}
    ],
    "audio-ai": [
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"}
    ]
}

def get_best_image(item):
    """
    Advanced extraction to find the highest quality image available in the RSS item.
    """
    # 1. Try Media RSS Namespace (Common in pro tech feeds)
    namespaces = {'media': 'http://search.yahoo.com/mrss/'}
    media_content = item.find('media:content', namespaces)
    if media_content is not None:
        return media_content.get('url')
    
    media_thumbnail = item.find('media:thumbnail', namespaces)
    if media_thumbnail is not None:
        return media_thumbnail.get('url')

    # 2. Try Standard Enclosure (Podcasts/Blogs)
    enclosure = item.find('enclosure')
    if enclosure is not None and 'image' in (enclosure.get('type') or ''):
        return enclosure.get('url')

    # 3. Regex Fallback: Search the Description for <img> tags
    description = item.findtext('description') or ""
    img_match = re.search(r'<img [^>]*src="([^"]+)"', description)
    if img_match:
        return img_match.group(1)

    return ""

def fetch_feed(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except Exception as e:
        print(f"  ! Error fetching {url}: {e}")
        return None

def run():
    print(f"Starting Refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_news = []
    
    for category, sources in FEED_SOURCES.items():
        print(f"Processing Category: {category}")
        for source in sources:
            xml_data = fetch_feed(source['url'])
            if not xml_data: continue
            
            try:
                root = ET.fromstring(xml_data)
                items = root.findall('.//item')
                for i in items:
                    all_news.append({
                        "guid": i.findtext('guid') or i.findtext('link'),
                        "title": unescape(i.findtext('title') or "Untitled"),
                        "link": i.findtext('link'),
                        "source": source['label'],
                        "category": category,
                        "image": get_best_image(i),
                        "timestamp": datetime.now().isoformat()
                    })
                print(f"  → Found {len(items)} items from {source['label']}")
            except Exception as e:
                print(f"  ! Parse error for {source['label']}: {e}")

    # Deduplicate by GUID
    unique_news = {item['guid']: item for item in all_news}.values()
    
    # Save output
    DATA_DIR.mkdir(exist_ok=True)
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(unique_news), f, indent=2, ensure_ascii=False)
    
    print(f"Finished. Total unique items: {len(unique_news)}")

if __name__ == "__main__":
    run()
