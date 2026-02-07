#!/usr/bin/env python3
"""
The Streamic RSS Aggregator - FIXED VERSION
- Professional broadcast tech RSS feeds (no Hall of Fame headshots)
- Category-based feed tagging
- GUID-based deduplication
- Automatic archiving (30 days / 100 items cap)
- Enhanced image extraction
"""

import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser
from datetime import datetime, timedelta
from pathlib import Path
import re

USER_AGENT = "Mozilla/5.0 (compatible; StreamicBot/1.0)"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"
ARCHIVE_FILE = DATA_DIR / "archive.json"
MAX_NEWS_ITEMS = 100
ARCHIVE_DAYS = 30

# ========== PROFESSIONAL RSS SOURCES (NO HALL OF FAME) ==========

FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
        {"url": "https://www.sportsvideo.org/feed/", "label": "Sports Video Group"},
    ],
    "playout": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
        {"url": "https://www.ibc.org/rss", "label": "IBC"},
    ],
    "infrastructure": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.sportsvideo.org/feed/", "label": "Sports Video Group"},
        {"url": "https://www.ibc.org/rss", "label": "IBC"},
    ],
    "graphics": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.sportsvideo.org/feed/", "label": "Sports Video Group"},
        {"url": "https://www.newscaststudio.com/feed/", "label": "NewscastStudio"},
    ],
    "cloud": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
        {"url": "https://www.streamingmedia.com/RSS/RSSFeed.aspx", "label": "Streaming Media"},
    ],
    "streaming": [
        {"url": "https://www.streamingmedia.com/RSS/RSSFeed.aspx", "label": "Streaming Media"},
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
    ],
    "audio-ai": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.sportsvideo.org/feed/", "label": "Sports Video Group"},
        {"url": "https://www.prosoundnetwork.com/feed", "label": "Pro Sound Network"},
    ]
}

# Category-specific fallback images (high quality Unsplash)
CATEGORY_FALLBACKS = {
    "newsroom": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80",
    "playout": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80",
    "infrastructure": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80",
    "graphics": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80",
    "cloud": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80",
    "streaming": "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80",
    "audio-ai": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80"
}

class ImageExtractor(HTMLParser):
    """Enhanced HTML parser to extract images from descriptions"""
    def __init__(self):
        super().__init__()
        self.images = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            attrs_dict = dict(attrs)
            if 'src' in attrs_dict:
                src = attrs_dict['src']
                # Filter out tracking pixels, small images, and person photos
                if (src and 
                    not any(x in src.lower() for x in ['1x1', 'pixel', 'tracker', 'headshot', 'portrait', 'person']) and
                    not src.endswith('.gif')):
                    self.images.append(src)

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

def extract_image(item, category="newsroom"):
    """Extract image URL from RSS item with enhanced detection"""
    # Try media:thumbnail
    media_ns = "{http://search.yahoo.com/mrss/}"
    thumb = item.find(f"{media_ns}thumbnail")
    if thumb is not None and thumb.get("url"):
        url = thumb.get("url")
        if is_valid_image(url):
            return url
    
    # Try media:content
    for content in item.findall(f"{media_ns}content"):
        url = content.get("url", "")
        if url and content.get("medium") == "image" and is_valid_image(url):
            return url
    
    # Try enclosure
    enc = item.find("enclosure")
    if enc is not None:
        url = enc.get("url", "")
        if url and enc.get("type", "").startswith("image/") and is_valid_image(url):
            return url
    
    # Parse content:encoded for images
    content_encoded = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
    if content_encoded is not None and content_encoded.text:
        img_url = extract_image_from_html(content_encoded.text)
        if img_url and is_valid_image(img_url):
            return img_url
    
    # Parse description for images
    desc = extract_text(item, "description", "")
    if desc:
        img_url = extract_image_from_html(desc)
        if img_url and is_valid_image(img_url):
            return img_url
    
    # Return category-specific fallback
    return CATEGORY_FALLBACKS.get(category, "assets/fallback.jpg")

def extract_image_from_html(html_content):
    """Extract first valid image from HTML content"""
    parser = ImageExtractor()
    try:
        parser.feed(unescape(html_content))
        if parser.images:
            return parser.images[0]
    except:
        pass
    return None

def is_valid_image(url):
    """Check if image URL is valid (not a person photo or tracking pixel)"""
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Reject tracking pixels and tiny images
    if any(x in url_lower for x in ['1x1', 'pixel', 'tracker', 'beacon']):
        return False
    
    # Reject person/headshot photos
    if any(x in url_lower for x in ['headshot', 'portrait', 'person', 'face', 'avatar', 'profile']):
        return False
    
    # Reject gifs (often logos or tracking)
    if url_lower.endswith('.gif'):
        return False
    
    # Accept valid image extensions
    if any(url_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
        return True
    
    return False

def extract_guid(item):
    """Extract unique identifier (GUID or link)"""
    guid_elem = item.find("guid")
    if guid_elem is not None and guid_elem.text:
        return guid_elem.text.strip()
    
    link = extract_text(item, "link", "")
    return link if link else f"temp-{time.time()}"

def extract_description(item):
    """Extract and clean description for summary"""
    # Try content:encoded first
    content = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
    if content is not None and content.text:
        text = content.text
    else:
        text = extract_text(item, "description", "")
    
    if text:
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', unescape(text))
        # Clean whitespace
        text = ' '.join(text.split())
        # Limit to 2 sentences (approximately)
        sentences = re.split(r'[.!?]+\s+', text)
        summary = '. '.join(sentences[:2])
        if summary and not summary.endswith('.'):
            summary += '.'
        return summary[:200]  # Max 200 chars
    
    return ""

def parse_rss_feed(xml_data, category):
    """Parse RSS/Atom feed and tag with category"""
    items = []
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"  ✗ Parse error: {e}")
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
                "image": extract_image(item, category),
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "summary": extract_description(item)
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
            
            # Get summary from Atom
            summary_elem = entry.find(f"{atom_ns}summary")
            summary = ""
            if summary_elem is not None and summary_elem.text:
                summary = re.sub(r'<[^>]+>', '', summary_elem.text)[:200]
            
            items.append({
                "guid": extract_text(entry, f"{atom_ns}id", link),
                "title": extract_text(entry, f"{atom_ns}title", "Untitled"),
                "link": link,
                "source": source_title,
                "image": CATEGORY_FALLBACKS.get(category, "assets/fallback.jpg"),
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "summary": summary
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
    print("THE STREAMIC - RSS Aggregator (FIXED)")
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
