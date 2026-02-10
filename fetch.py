#!/usr/bin/env python3
"""
The Streamic RSS Feed Aggregator
Fetches, parses, and aggregates broadcast technology news from multiple sources
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

# Direct fetch domains (skip worker)
DIRECT_FETCH_DOMAINS = ['inbroadcast.com', 'imaginecommunications.com']

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
        'https://www.microsoft.com/en-us/security/blog/feed/'
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
        'https://www.tvtechnology.com/streaming/rss.xml'
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
    """Check if feed should bypass worker"""
    return any(domain in feed_url for domain in DIRECT_FETCH_DOMAINS)

def fetch_feed_via_worker(feed_url):
    """Fetch feed through Cloudflare Worker"""
    try:
        encoded_url = quote(feed_url, safe='')
        worker_url = f"{CLOUDFLARE_WORKER}?url={encoded_url}"
        
        response = requests.get(
            worker_url,
            timeout=FEED_FETCH_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; TheStreamic/1.0)'}
        )
        
        if response.status_code == 200:
            return feedparser.parse(response.content)
        return None
    except Exception as e:
        print(f"  ⚠ Worker fetch failed: {e}")
        return None

def fetch_feed_direct(feed_url):
    """Fetch feed directly"""
    try:
        response = requests.get(
            feed_url,
            timeout=FEED_FETCH_TIMEOUT,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*'
            }
        )
        
        if response.status_code == 200:
            return feedparser.parse(response.content)
        return None
    except Exception as e:
        print(f"  ⚠ Direct fetch failed: {e}")
        return None

def fetch_feed(feed_url, category):
    """Fetch feed with Worker + Direct fallback logic"""
    print(f"  Fetching {feed_url[:60]}...")
    
    if should_use_direct_fetch(feed_url):
        print(f"    → Direct fetch (bypassing worker)")
        feed = fetch_feed_direct(feed_url)
    else:
        print(f"    → Via worker")
        feed = fetch_feed_via_worker(feed_url)
        
        if not feed or not feed.entries:
            print(f"    → Worker failed, trying direct")
            feed = fetch_feed_direct(feed_url)
    
    if not feed or not feed.entries:
        print(f"    ✗ Failed")
        return []
    
    print(f"    ✓ Got {len(feed.entries)} entries")
    return feed.entries[:MAX_ITEMS_PER_FEED]

def parse_pubdate(entry):
    """Parse publication date from entry"""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except:
            pass
    
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        try:
            dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except:
            pass
    
    # Fallback to now
    return datetime.now(timezone.utc).isoformat()

def extract_image_from_entry(entry):
    """Extract image URL from feed entry"""
    # 1. media:content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if 'url' in media and media.get('medium') in [None, 'image']:
                return media['url']
    
    # 2. media:thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url')
    
    # 3. enclosure
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                return enc.get('href')
    
    # 4. <img> in description
    if hasattr(entry, 'summary'):
        img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', entry.summary)
        if img_match:
            img_url = img_match.group(1)
            # Skip obvious tracking pixels
            if not any(x in img_url.lower() for x in ['1x1', 'pixel', 'tracker', 'spacer']):
                return img_url
    
    return None

def extract_og_image(article_url, timeout=ARTICLE_FETCH_TIMEOUT):
    """Extract OG/Twitter image from article HTML using regex"""
    try:
        response = requests.get(
            article_url,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; TheStreamic/1.0)'}
        )
        
        if response.status_code != 200:
            return None
        
        html = response.text[:50000]  # First 50KB only
        
        # Try og:image
        og_match = re.search(r'<meta\s+property=["\'"]og:image["\'"][^>]+content=["\'"]([^"\']+)["\']', html, re.IGNORECASE)
        if og_match:
            return og_match.group(1)
        
        # Try twitter:image
        tw_match = re.search(r'<meta\s+name=["\'"]twitter:image["\'"][^>]+content=["\'"]([^"\']+)["\']', html, re.IGNORECASE)
        if tw_match:
            return tw_match.group(1)
        
        return None
    except:
        return None

def process_entries(entries, category, source_name):
    """Process feed entries into standardized items"""
    items = []
    
    for entry in entries:
        try:
            # Required fields
            title = entry.get('title', '').strip()
            link = entry.get('link', '').strip()
            guid = entry.get('id', link)
            
            if not title or not link:
                continue
            
            # Extract image
            image = extract_image_from_entry(entry)
            
            # Parse pubDate
            pub_date = parse_pubdate(entry)
            
            items.append({
                'title': title,
                'link': link,
                'guid': guid,
                'category': category,
                'source': source_name,
                'image': image,
                'pubDate': pub_date,
                'timestamp': int(time.time())
            })
            
        except Exception as e:
            print(f"    ⚠ Error processing entry: {e}")
            continue
    
    return items

def fetch_missing_images(items, max_fetches=MAX_ARTICLE_FETCHES):
    """Fetch OG images for items without images (limited)"""
    fetched_count = 0
    
    for item in items:
        if fetched_count >= max_fetches:
            break
        
        if not item.get('image'):
            print(f"    Fetching OG image for: {item['title'][:50]}...")
            og_image = extract_og_image(item['link'])
            if og_image:
                item['image'] = og_image
                print(f"      ✓ Found OG image")
                fetched_count += 1
    
    print(f"  ✓ Fetched {fetched_count} OG images")

def get_source_name(feed_url):
    """Extract source name from feed URL"""
    if 'newscaststudio' in feed_url:
        return 'Newscast Studio'
    elif 'tvtechnology' in feed_url:
        return 'TV Technology'
    elif 'broadcastbeat' in feed_url:
        return 'Broadcast Beat'
    elif 'svgeurope' in feed_url:
        return 'SVG Europe'
    elif 'inbroadcast' in feed_url:
        return 'InBroadcast'
    elif 'rossvideo' in feed_url:
        return 'Ross Video'
    elif 'harmonicinc' in feed_url:
        return 'Harmonic'
    elif 'evertz' in feed_url:
        return 'Evertz'
    elif 'imaginecommunications' in feed_url:
        return 'Imagine Communications'
    elif 'thebroadcastbridge' in feed_url or 'broadcastbridge' in feed_url:
        return 'The Broadcast Bridge'
    elif 'vizrt' in feed_url:
        return 'Vizrt'
    elif 'motionographer' in feed_url:
        return 'Motionographer'
    elif 'aws.amazon' in feed_url:
        return 'AWS'
    elif 'frame.io' in feed_url:
        return 'Frame.io'
    elif 'krebsonsecurity' in feed_url:
        return 'Krebs on Security'
    elif 'darkreading' in feed_url:
        return 'Dark Reading'
    elif 'bleepingcomputer' in feed_url:
        return 'BleepingComputer'
    elif 'securityweek' in feed_url:
        return 'SecurityWeek'
    elif 'feedburner.com/TheHackerNews' in feed_url:
        return 'The Hacker News'
    elif 'cloud.google.com' in feed_url:
        return 'Google Cloud'
    elif 'microsoft.com' in feed_url:
        return 'Microsoft Security'
    else:
        return 'Technology News'

def validate_news_data(items):
    """Validate that we have minimum items per category"""
    category_counts = {}
    
    for item in items:
        cat = item['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("\n📊 Category distribution:")
    for cat, count in sorted(category_counts.items()):
        status = "✓" if count >= MIN_REQUIRED_EACH else "⚠"
        print(f"  {status} {cat}: {count} items")
    
    # Check if any category is below minimum
    failed_categories = [cat for cat, count in category_counts.items() if count < MIN_REQUIRED_EACH]
    
    if failed_categories:
        print(f"\n⚠ Categories below minimum ({MIN_REQUIRED_EACH}): {', '.join(failed_categories)}")
        return False
    
    return True

def deduplicate_by_guid(items):
    """Remove duplicate articles by GUID"""
    seen_guids = set()
    unique_items = []
    
    for item in items:
        guid = item.get('guid', '')
        if guid and guid not in seen_guids:
            seen_guids.add(guid)
            unique_items.append(item)
    
    print(f"\n🔄 Deduplication: {len(items)} → {len(unique_items)} items (removed {len(items) - len(unique_items)} duplicates)")
    return unique_items

def balance_categories(all_items):
    """Balance items across categories"""
    # First, deduplicate by GUID
    all_items = deduplicate_by_guid(all_items)
    
    category_items = {}
    
    # Group by category
    for item in all_items:
        cat = item['category']
        if cat not in category_items:
            category_items[cat] = []
        category_items[cat].append(item)
    
    # Sort each category by pubDate (newest first)
    for cat in category_items:
        category_items[cat].sort(
            key=lambda x: x.get('pubDate', ''),
            reverse=True
        )
    
    # Take top items from each category
    balanced = []
    for cat, items in category_items.items():
        balanced.extend(items[:MIN_PER_CATEGORY])
    
    # Sort all by pubDate
    balanced.sort(key=lambda x: x.get('pubDate', ''), reverse=True)
    
    # Limit total
    return balanced[:MAX_NEWS_ITEMS]

def save_json_atomically(data, filepath):
    """Save JSON file atomically"""
    temp_file = filepath.with_suffix('.tmp')
    
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    temp_file.replace(filepath)

# ===== MAIN EXECUTION =====

def main():
    print("=" * 70)
    print("THE STREAMIC - RSS Feed Aggregator")
    print("=" * 70)
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    all_items = []
    
    # Fetch all feeds
    for category, feeds in FEED_GROUPS.items():
        print(f"\n📡 Category: {category.upper()}")
        category_items = []
        
        for feed_url in feeds:
            source_name = get_source_name(feed_url)
            entries = fetch_feed(feed_url, category)
            
            if entries:
                items = process_entries(entries, category, source_name)
                category_items.extend(items)
                print(f"    → Processed {len(items)} items from {source_name}")
        
        print(f"  ✓ Total for {category}: {len(category_items)} items")
        all_items.extend(category_items)
    
    print(f"\n📦 Total items collected: {len(all_items)}")
    
    # Fetch missing images (limited to MAX_ARTICLE_FETCHES)
    print(f"\n🖼 Fetching missing images (max {MAX_ARTICLE_FETCHES})...")
    fetch_missing_images(all_items)
    
    # Balance categories
    print("\n⚖ Balancing categories...")
    balanced_items = balance_categories(all_items)
    print(f"  ✓ Balanced to {len(balanced_items)} items")
    
    # Validate
    print("\n✅ Validating...")
    is_valid = validate_news_data(balanced_items)
    
    # Backup existing file
    if OUTPUT_FILE.exists():
        print(f"\n💾 Backing up to {ARCHIVE_FILE}...")
        with open(OUTPUT_FILE, 'r') as f:
            old_data = json.load(f)
        save_json_atomically(old_data, ARCHIVE_FILE)
    
    # Save strategy
    if is_valid or not OUTPUT_FILE.exists():
        # Save new data
        print(f"\n💾 Saving to {OUTPUT_FILE}...")
        save_json_atomically(balanced_items, OUTPUT_FILE)
        print(f"  ✓ Saved {len(balanced_items)} items")
    else:
        # Keep existing file if validation failed
        print("\n⚠ Validation failed - keeping existing file")
        if OUTPUT_FILE.exists():
            print("  ✓ Existing file preserved")
        else:
            # No existing file, save anyway
            print("  ⚠ No existing file - saving anyway with warnings")
            save_json_atomically(balanced_items, OUTPUT_FILE)
    
    print("\n" + "=" * 70)
    print("✅ AGGREGATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
