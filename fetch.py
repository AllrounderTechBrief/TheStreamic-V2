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

# ===== DIRECT FETCH FEEDS (Bypass Cloudflare Worker) =====
DIRECT_FEEDS = [
    # Streaming category
    'https://www.streamingmediablog.com/feed',
    'https://www.dacast.com/feed',
    'https://onthefly.stream/blog/feed',
    'https://yololiv.com/blog/feed',
    'https://techcrunch.com/feed',
    'https://www.engadget.com/rss.xml',
    'https://www.wired.com/feed/rss',
    'https://www.broadcastnow.co.uk/full-rss/',
    # Infrastructure category - MAM/PAM
    'https://chesa.com/feed',
    'https://cloudinary.com/blog/feed',
    # Infrastructure category - Storage
    'https://www.studionetworksolutions.com/feed',
    'https://openrss.org/https://scalelogicinc.com/blog/protecting-valuable-media-assets/',
    'https://openrss.org/https://qsan.io/solutions/media-production/',
    'https://openrss.org/https://www.keycodemedia.com/capabilities/media-shared-storage-cloud-storage/',
    # Infrastructure category - Production Ops
    'https://www.processexcellencenetwork.com/rss-feeds',
    # Legacy direct fetch
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
        # Direct fetch streaming feeds
        'https://www.streamingmediablog.com/feed',
        'https://www.dacast.com/feed',
        'https://onthefly.stream/blog/feed',
        'https://yololiv.com/blog/feed',
        'https://techcrunch.com/feed',
        'https://www.engadget.com/rss.xml',
        'https://www.wired.com/feed/rss',
        'https://www.broadcastnow.co.uk/full-rss/'
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
        print(f"  ⚠ Worker error for {feed_url[:50]}: {e}")
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
            return feedparser.parse(response.content)
        return None
    except Exception as e:
        print(f"  ⚠ Direct fetch error for {feed_url[:50]}: {e}")
        return None

def fetch_feed_with_fallback(feed_url):
    """Fetch feed with worker or direct based on configuration"""
    if should_use_direct_fetch(feed_url):
        print(f"  → Direct fetch: {feed_url[:60]}")
        feed = fetch_feed_direct(feed_url)
        if feed:
            return feed
        print(f"  ⚠ Direct fetch failed")
        return None
    else:
        feed = fetch_feed_via_worker(feed_url)
        if feed:
            return feed
        print(f"  → Fallback to direct fetch")
        return fetch_feed_direct(feed_url)

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
    
    # 4. Extract from description/summary HTML
    description = entry.get('description', '') or entry.get('summary', '')
    if description:
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', description, re.IGNORECASE)
        if img_match:
            img_url = img_match.group(1)
            if not any(x in img_url.lower() for x in ['1x1', 'pixel', 'tracker', 'spacer']):
                return img_url
    
    # 5. Try lower quality image parameters if available
    if hasattr(entry, 'media_content'):
        for media in entry.media_content:
            url = media.get('url', '')
            if url and ('w=' in url or 'width=' in url):
                # Try reducing quality parameters
                low_quality_url = re.sub(r'(w|width)=\d+', r'\1=400', url)
                low_quality_url = re.sub(r'(h|height)=\d+', r'\1=300', low_quality_url)
                low_quality_url = re.sub(r'(q|quality)=\d+', r'\1=60', low_quality_url)
                return low_quality_url
    
    return None

def extract_og_image(article_url, timeout=ARTICLE_FETCH_TIMEOUT):
    """Extract OG/Twitter image from article HTML"""
    try:
        response = requests.get(
            article_url,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; TheStreamic/1.0)'}
        )
        
        if response.status_code != 200:
            return None
        
        html = response.text[:50000]
        
        # Try og:image
        og_match = re.search(r'<meta\s+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_match:
            img_url = og_match.group(1)
            # Try lower quality version
            if 'w=' in img_url or 'width=' in img_url:
                img_url = re.sub(r'(w|width)=\d+', r'\1=400', img_url)
                img_url = re.sub(r'(h|height)=\d+', r'\1=300', img_url)
            return img_url
        
        # Try twitter:image
        tw_match = re.search(r'<meta\s+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if tw_match:
            img_url = tw_match.group(1)
            if 'w=' in img_url or 'width=' in img_url:
                img_url = re.sub(r'(w|width)=\d+', r'\1=400', img_url)
                img_url = re.sub(r'(h|height)=\d+', r'\1=300', img_url)
            return img_url
        
        return None
    except:
        return None

def process_entries(entries, category, source_name):
    """Process feed entries into standardized items"""
    items = []
    article_fetch_count = 0
    
    for entry in entries:
        try:
            title = entry.get('title', '').strip()
            link = entry.get('link', '').strip()
            guid = entry.get('id', link)
            
            if not title or not link:
                continue
            
            # Extract image
            image = extract_image_from_entry(entry)
            
            # If no image, try OG image (limited attempts)
            if not image and article_fetch_count < MAX_ARTICLE_FETCHES:
                image = extract_og_image(link)
                article_fetch_count += 1
            
            # Parse pubDate
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                except:
                    pass
            
            if not pub_date and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                try:
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
                except:
                    pass
            
            if not pub_date:
                pub_date = datetime.now(timezone.utc).isoformat()
            
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
            print(f"  ⚠ Error processing entry: {e}")
            continue
    
    return items

def get_source_name(feed_url):
    """Extract human-readable source name from feed URL"""
    if 'newscaststudio' in feed_url:
        return 'NewscastStudio'
    elif 'tvtechnology' in feed_url:
        return 'TV Technology'
    elif 'broadcastbeat' in feed_url:
        return 'BroadcastBeat'
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
    elif 'broadcastbridge' in feed_url or 'thebroadcastbridge' in feed_url:
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
    elif 'streamingmediablog' in feed_url:
        return 'Streaming Media Blog'
    elif 'dacast' in feed_url:
        return 'Dacast'
    elif 'onthefly.stream' in feed_url:
        return 'OnTheFly'
    elif 'yololiv' in feed_url:
        return 'YoloLiv'
    elif 'techcrunch' in feed_url:
        return 'TechCrunch'
    elif 'engadget' in feed_url:
        return 'Engadget'
    elif 'wired.com' in feed_url:
        return 'WIRED'
    elif 'broadcastnow' in feed_url:
        return 'Broadcast Now'
    elif 'chesa.com' in feed_url:
        return 'Chesa'
    elif 'cloudinary' in feed_url:
        return 'Cloudinary'
    elif 'studionetworksolutions' in feed_url:
        return 'Studio Network Solutions'
    elif 'scalelogicinc' in feed_url:
        return 'ScaleLogic'
    elif 'qsan.io' in feed_url:
        return 'QSAN'
    elif 'keycodemedia' in feed_url:
        return 'Keycode Media'
    elif 'processexcellencenetwork' in feed_url:
        return 'Process Excellence Network'
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
    all_items = deduplicate_by_guid(all_items)
    
    category_items = {}
    
    for item in all_items:
        cat = item['category']
        if cat not in category_items:
            category_items[cat] = []
        category_items[cat].append(item)
    
    for cat in category_items:
        category_items[cat].sort(
            key=lambda x: x.get('pubDate', ''),
            reverse=True
        )
    
    balanced = []
    for cat, items in category_items.items():
        balanced.extend(items[:MIN_PER_CATEGORY])
    
    balanced.sort(key=lambda x: x.get('pubDate', ''), reverse=True)
    
    return balanced[:MAX_NEWS_ITEMS]

def save_json_atomically(data, filepath):
    """Save JSON file atomically"""
    temp_file = filepath.with_suffix('.tmp')
    
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    temp_file.replace(filepath)

def main():
    """Main aggregation function"""
    print("🚀 Starting The Streamic RSS Aggregator\n")
    
    DATA_DIR.mkdir(exist_ok=True)
    
    all_items = []
    
    for category, feed_urls in FEED_GROUPS.items():
        print(f"\n📰 Processing {category.upper()} ({len(feed_urls)} feeds)")
        
        for feed_url in feed_urls:
            try:
                feed = fetch_feed_with_fallback(feed_url)
                
                if not feed or not feed.entries:
                    print(f"  ⚠ No entries from {feed_url[:60]}")
                    continue
                
                entries = feed.entries[:MAX_ITEMS_PER_FEED]
                source_name = get_source_name(feed_url)
                
                items = process_entries(entries, category, source_name)
                all_items.extend(items)
                
                print(f"  ✓ {source_name}: {len(items)} items")
                
            except Exception as e:
                print(f"  ✗ Error with {feed_url[:60]}: {e}")
                continue
    
    print(f"\n📦 Total items collected: {len(all_items)}")
    
    if not all_items:
        print("❌ No items collected. Exiting.")
        return
    
    balanced_items = balance_categories(all_items)
    
    print(f"⚖️  Balanced to: {len(balanced_items)} items")
    
    validation_passed = validate_news_data(balanced_items)
    
    if OUTPUT_FILE.exists():
        if validation_passed:
            if ARCHIVE_FILE.exists():
                ARCHIVE_FILE.unlink()
            OUTPUT_FILE.rename(ARCHIVE_FILE)
            print(f"\n💾 Backed up existing data to {ARCHIVE_FILE}")
        else:
            print(f"\n⚠️  Validation failed. Keeping existing {OUTPUT_FILE}")
            return
    else:
        if not validation_passed:
            print("\n⚠️  Validation failed but no existing file. Saving anyway.")
    
    save_json_atomically(balanced_items, OUTPUT_FILE)
    
    print(f"✅ Saved {len(balanced_items)} items to {OUTPUT_FILE}")
    print("\n🎉 Aggregation complete!")

if __name__ == "__main__":
    main()
