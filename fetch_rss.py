#!/usr/bin/env python3 catagory
"""
The Streamic RSS Aggregator
- Category-based feed tagging
- GUID-based deduplication
- Automatic archiving (30 days / 100 items cap)
- AI summary placeholder support
"""

import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html import unescape
from datetime import datetime, timedelta
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; StreamicBot/1.0)"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"
ARCHIVE_FILE = DATA_DIR / "archive.json"
MAX_NEWS_ITEMS = 100
ARCHIVE_DAYS = 30

# ========== CATEGORY-SPECIFIC RSS SOURCES ==========

FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
    ],
    "playout": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
    ],
    "infrastructure": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.sportsvideo.org/feed/", "label": "Sports Video Group"},
    ],
    "graphics": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.sportsvideo.org/feed/", "label": "Sports Video Group"},
    ],
    "cloud": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
    ],
    "streaming": [
        {"url": "https://www.streamingmedia.com/RSS/RSSFeed.aspx", "label": "Streaming Media"},
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
    ],
    "audio-ai": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.prosoundnetwork.com/feed", "label": "Pro Sound Network"},
    ]
}

def fetch_url(url, timeout=20):
    """Fetch URL with error handling"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception as e:
        print(f"  ✗ Error fetching {url}: {e}")
        return None

def extract_text(node, path, default=""):
    """Safely extract text from XML element"""
    el = node.find(path)
    return (el.text or "").strip() if el is not None and el.text else default

def extract_image(item):
    """Extract image URL from RSS item"""
    # Try media:thumbnail
    media_ns = "{http://search.yahoo.com/mrss/}"
    thumb = item.find(f"{media_ns}thumbnail")
    if thumb is not None and thumb.get("url"):
        return thumb.get("url")
    
    # Try media:content
    content = item.find(f"{media_ns}content")
    if content is not None and content.get("url"):
        if content.get("type", "").startswith("image/"):
            return content.get("url")
    
    # Try enclosure
    enc = item.find("enclosure")
    if enc is not None and enc.get("type", "").startswith("image/"):
        return enc.get("url")
    
    # Parse description for img tags
    desc = extract_text(item, "description", "")
    if desc:
        desc = unescape(desc)
        idx = desc.lower().find("<img ")
        if idx != -1:
            src_idx = desc.lower().find("src=", idx)
            if src_idx != -1:
                quote = desc[src_idx+4:src_idx+5]
                if quote in "\"'":
                    end_idx = desc.find(quote, src_idx+5)
                    if end_idx != -1:
                        return desc[src_idx+5:end_idx]
    
    return ""

def extract_guid(item):
    """Extract unique identifier (GUID or link)"""
    guid_elem = item.find("guid")
    if guid_elem is not None and guid_elem.text:
        return guid_elem.text.strip()
    
    link = extract_text(item, "link", "")
    return link if link else str(time.time())

def parse_rss_feed(xml_data, category):
    """Parse RSS/Atom feed and tag with category"""
    items = []
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return items

    # RSS 2.0
    channel = root.find("channel")
    if channel is not None:
        source_title = extract_text(channel, "title", "Source")
        for item in channel.findall("item"):
            items.append({
                "guid": extract_guid(item),
                "title": extract_text(item, "title", "Untitled"),
                "link": extract_text(item, "link", ""),
                "source": source_title,
                "image": extract_image(item),
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "summary": ""  # Placeholder for AI summary
            })
    
    # Atom feeds
    atom_ns = "{http://www.w3.org/2005/Atom}"
    if root.tag == f"{atom_ns}feed":
        source_title = extract_text(root, f"{atom_ns}title", "Source")
        for entry in root.findall(f"{atom_ns}entry"):
            link_elem = entry.find(f"{atom_ns}link[@rel='alternate']")
            if link_elem is None:
                link_elem = entry.find(f"{atom_ns}link")
            link = link_elem.get("href", "") if link_elem is not None else ""
            
            items.append({
                "guid": extract_text(entry, f"{atom_ns}id", link),
                "title": extract_text(entry, f"{atom_ns}title", "Untitled"),
                "link": link,
                "source": source_title,
                "image": "",
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "summary": ""
            })
    
    return items

def load_existing_news():
    """Load existing news items"""
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def load_archive():
    """Load archive items"""
    if ARCHIVE_FILE.exists():
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_json(filepath, data):
    """Save data to JSON file"""
    DATA_DIR.mkdir(exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def archive_old_items(items):
    """Move items older than ARCHIVE_DAYS or beyond MAX_NEWS_ITEMS to archive"""
    cutoff_date = datetime.now() - timedelta(days=ARCHIVE_DAYS)
    
    # Sort by timestamp (newest first)
    items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Items to keep in news
    news_items = []
    # Items to archive
    to_archive = []
    
    for item in items:
        try:
            item_date = datetime.fromisoformat(item.get('timestamp', ''))
            is_old = item_date < cutoff_date
        except:
            is_old = False
        
        # Archive if old OR beyond capacity
        if is_old or len(news_items) >= MAX_NEWS_ITEMS:
            to_archive.append(item)
        else:
            news_items.append(item)
    
    # Load existing archive and merge
    if to_archive:
        existing_archive = load_archive()
        existing_guids = {item['guid'] for item in existing_archive}
        
        # Only add new items to archive
        for item in to_archive:
            if item['guid'] not in existing_guids:
                existing_archive.append(item)
        
        save_json(ARCHIVE_FILE, existing_archive)
        print(f"  → Archived {len(to_archive)} items")
    
    return news_items

def fetch_all_feeds():
    """Fetch and aggregate all RSS feeds"""
    print("=" * 70)
    print("THE STREAMIC - RSS Aggregator")
    print("=" * 70 + "\n")
    
    all_items = []
    existing_news = load_existing_news()
    existing_guids = {item['guid'] for item in existing_news}
    
    # Fetch from all category sources
    for category, sources in FEED_SOURCES.items():
        print(f"\n📁 Category: {category.upper()}")
        print("-" * 70)
        
        for source in sources:
            url = source['url']
            label = source.get('label', url)
            
            print(f"  Fetching: {label}")
            xml_data = fetch_url(url)
            
            if xml_data:
                items = parse_rss_feed(xml_data, category)
                
                # Override source label if provided
                if label:
                    for item in items:
                        item['source'] = label
                
                # Only add new items (GUID deduplication)
                new_items = [item for item in items if item['guid'] not in existing_guids]
                all_items.extend(new_items)
                
                print(f"  → Found {len(items)} items ({len(new_items)} new)")
                time.sleep(0.5)  # Be polite to servers
    
    # Merge with existing items
    merged_items = existing_news + all_items
    
    # Remove duplicates by GUID (keep most recent)
    seen_guids = set()
    unique_items = []
    for item in merged_items:
        if item['guid'] not in seen_guids:
            seen_guids.add(item['guid'])
            unique_items.append(item)
    
    # Archive old items and limit to MAX_NEWS_ITEMS
    final_items = archive_old_items(unique_items)
    
    # Save to news.json
    save_json(NEWS_FILE, final_items)
    
    print("\n" + "=" * 70)
    print(f"✓ Complete!")
    print(f"  News items: {len(final_items)}")
    print(f"  New items added: {len(all_items)}")
    archive_count = len(load_archive())
    print(f"  Archive items: {archive_count}")
    print("=" * 70)

if __name__ == "__main__":
    fetch_all_feeds()
