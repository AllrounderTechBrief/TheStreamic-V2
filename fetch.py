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
MIN_PER_CATEGORY = 18
MIN_REQUIRED_EACH = 3
MAX_NEWS_ITEMS = 300
MAX_ITEMS_PER_SOURCE = 8  # Prevent any single source from dominating the feed

# ===== DIRECT FETCH FEEDS (Bypass Cloudflare Worker) =====
DIRECT_FEEDS = [
    # Streaming - broadcast-focused (direct fetch)
    'https://www.streamingmediablog.com/feed',
    'https://www.dacast.com/feed',
    'https://onthefly.stream/blog/feed',
    'https://yololiv.com/blog/feed',
    'https://www.broadcastnow.co.uk/full-rss/',
    'https://www.haivision.com/blog/feed/',
    'https://bitmovin.com/blog/feed/',
    'https://www.akamai.com/blog/feed.xml',
    'https://www.limelight.com/resources/blog/feed/',
    'https://www.fastly.com/blog/feed',
    # Playout & broadcast vendors (direct fetch)
    'https://www.grassvalley.com/news/rss/',
    'https://www.pebble.tv/feed/',
    'https://www.playboxtechnology.com/feed/',
    # Infrastructure - MAM/PAM/Storage
    'https://chesa.com/feed',
    'https://cloudinary.com/blog/feed',
    'https://www.studionetworksolutions.com/feed',
    'https://www.signiant.com/blog/feed/',
    'https://openrss.org/https://scalelogicinc.com/blog/protecting-valuable-media-assets/',
    'https://openrss.org/https://qsan.io/solutions/media-production/',
    'https://openrss.org/https://www.keycodemedia.com/capabilities/media-shared-storage-cloud-storage/',
    # AI & Post-Production (direct fetch)
    'https://www.provideocoalition.com/feed/',
    'https://nofilmschool.com/rss',
    'https://www.newsshooter.com/feed/',
    'https://www.bhphotovideo.com/explora/feed',
    # General tech - LOW PRIORITY, capped
    'https://techcrunch.com/feed',
    'https://www.engadget.com/rss.xml',
    'https://www.wired.com/feed/rss',
    # Legacy direct fetch
    'https://www.inbroadcast.com/rss.xml',
    'https://www.imaginecommunications.com/news/rss.xml',
    # Industry news (direct fetch)
    'https://www.tvbeurope.com/feed/',
    'https://www.digitaltvnews.net/?feed=rss2',
    'https://www.digitaltveurope.com/feed/',
    'https://www.rapidtvnews.com/feed/',
    'https://www.sportsvideo.org/feed/',
]

# ===== LOW PRIORITY FEEDS (general tech, shown last, capped at fewer items) =====
LOW_PRIORITY_FEEDS = [
    'https://techcrunch.com/feed',
    'https://www.engadget.com/rss.xml',
    'https://www.wired.com/feed/rss',
]
MAX_ITEMS_LOW_PRIORITY = 3  # Max items from any low-priority general tech feed

# ===== FEED GROUPS =====
FEED_GROUPS = {
    'newsroom': [
        # Core broadcast news outlets
        'https://www.newscaststudio.com/feed/',
        'https://www.tvtechnology.com/news/rss.xml',
        'https://www.broadcastbeat.com/feed/',
        'https://www.svgeurope.org/feed/',
        'https://www.sportsvideo.org/feed/',
        # Global broadcast industry news
        'https://www.tvbeurope.com/feed/',
        'https://www.digitaltvnews.net/?feed=rss2',
        'https://www.digitaltveurope.com/feed/',
        'https://www.rapidtvnews.com/feed/',
        'https://www.broadcastnow.co.uk/full-rss/',
        # Trade press
        'https://www.thebroadcastbridge.com/rss/news',
        'https://www.ibc.org/rss',
        'https://www.nab.org/nabpubs/news/rss.xml',
    ],
    'playout': [
        # Established broadcast vendors
        'https://www.inbroadcast.com/rss.xml',
        'https://www.tvtechnology.com/playout/rss.xml',
        'https://www.rossvideo.com/news/feed/',
        'https://www.harmonicinc.com/insights/blog/rss.xml',
        'https://www.evertz.com/news/rss',
        'https://www.imaginecommunications.com/news/rss.xml',
        # Additional playout vendors
        'https://www.grassvalley.com/news/rss/',
        'https://www.pebble.tv/feed/',
        'https://www.playboxtechnology.com/feed/',
        # Broadcast bridge playout coverage
        'https://www.thebroadcastbridge.com/rss/playout',
        'https://www.tvtechnology.com/production/rss.xml',
        # Scheduling & automation
        'https://www.newscaststudio.com/category/channel-in-a-box/feed/',
    ],
    'infrastructure': [
        # Core broadcast infrastructure
        'https://www.thebroadcastbridge.com/rss/infrastructure',
        'https://www.tvtechnology.com/infrastructure/rss.xml',
        # IP & networking for broadcast
        'https://www.thebroadcastbridge.com/rss/ip-network',
        'https://www.tvtechnology.com/networking/rss.xml',
        # MAM/PAM - Media Asset Management
        'https://chesa.com/feed',
        'https://cloudinary.com/blog/feed',
        'https://www.signiant.com/blog/feed/',
        # Storage for media
        'https://www.studionetworksolutions.com/feed',
        'https://openrss.org/https://scalelogicinc.com/blog/protecting-valuable-media-assets/',
        'https://openrss.org/https://qsan.io/solutions/media-production/',
        'https://openrss.org/https://www.keycodemedia.com/capabilities/media-shared-storage-cloud-storage/',
        # Broadcast monitoring & test
        'https://www.thebroadcastbridge.com/rss/test-measurement',
        'https://www.tvtechnology.com/test-measurement/rss.xml',
    ],
    'graphics': [
        # Core broadcast graphics
        'https://www.thebroadcastbridge.com/rss/graphics',
        'https://www.tvtechnology.com/graphics/rss.xml',
        # Vendors - capped by MAX_ITEMS_PER_SOURCE
        'https://www.vizrt.com/news/rss',
        'https://routing.vizrt.com/rss',
        # Motion graphics & design
        'https://motionographer.com/feed/',
        'https://www.cgchannel.com/feed/',
        'https://realtimevfx.com/latest.rss',
        # Virtual studios & AR
        'https://www.newscaststudio.com/category/virtual-set/feed/',
        'https://www.broadcastbeat.com/category/graphics/feed/',
        # Sports graphics
        'https://www.svgeurope.org/feed/',
        'https://www.sportsvideo.org/feed/',
    ],
    'cloud': [
        # Broadcast-specific cloud coverage
        'https://www.thebroadcastbridge.com/rss/cloud',
        'https://www.tvtechnology.com/cloud/rss.xml',
        # Cloud vendor media blogs
        'https://aws.amazon.com/blogs/media/feed/',
        'https://azure.microsoft.com/en-us/blog/topics/media/feed/',
        'https://cloud.google.com/blog/topics/media-entertainment/rss/',
        # CDN & delivery
        'https://www.akamai.com/blog/feed.xml',
        'https://www.fastly.com/blog/feed',
        # Workflow & collaboration
        'https://blog.frame.io/feed/',
        'https://bitmovin.com/blog/feed/',
        # Broadcast cloud news
        'https://www.thebroadcastbridge.com/rss/remote-production',
        'https://www.tvtechnology.com/remote-production/rss.xml',
    ],
    'streaming': [
        # === PRIMARY: Core broadcast & professional streaming ===
        'https://www.thebroadcastbridge.com/rss/streaming',
        'https://www.tvtechnology.com/streaming/rss.xml',
        'https://www.streamingmediablog.com/feed',
        'https://www.broadcastnow.co.uk/full-rss/',
        'https://www.haivision.com/blog/feed/',
        'https://bitmovin.com/blog/feed/',
        # OTT & video delivery
        'https://www.thebroadcastbridge.com/rss/ott',
        'https://www.tvtechnology.com/ott/rss.xml',
        # Live streaming platforms
        'https://www.dacast.com/feed',
        'https://onthefly.stream/blog/feed',
        'https://yololiv.com/blog/feed',
        # CDN / delivery
        'https://www.akamai.com/blog/feed.xml',
        # Industry trade coverage
        'https://www.tvbeurope.com/feed/',
        'https://www.rapidtvnews.com/feed/',
        # === LOW PRIORITY: General tech (capped at MAX_ITEMS_LOW_PRIORITY each) ===
        'https://techcrunch.com/feed',
        'https://www.engadget.com/rss.xml',
        'https://www.wired.com/feed/rss',
    ],
    'ai-post-production': [
        # === PRIMARY: Broadcast AI & editing ===
        'https://www.thebroadcastbridge.com/rss/ai',
        'https://www.tvtechnology.com/ai/rss.xml',
        'https://www.thebroadcastbridge.com/rss/audio',
        'https://www.tvtechnology.com/audio/rss.xml',
        # Post-production specialist press
        'https://motionographer.com/feed/',
        'https://blog.frame.io/feed/',
        'https://www.provideocoalition.com/feed/',
        'https://nofilmschool.com/rss',
        'https://www.newsshooter.com/feed/',
        'https://www.bhphotovideo.com/explora/feed',
        # Editing & colour
        'https://www.broadcastbeat.com/category/post-production/feed/',
        'https://www.tvtechnology.com/post-production/rss.xml',
        'https://www.thebroadcastbridge.com/rss/post-production',
        # AI tools coverage
        'https://www.thebroadcastbridge.com/rss/machine-learning',
        'https://www.tvbeurope.com/feed/',
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

def process_entries(entries, category, source_name, feed_url=''):
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
                'timestamp': int(time.time()),
                '_low_priority': feed_url in LOW_PRIORITY_FEEDS
            })
            
        except Exception as e:
            print(f"  ⚠ Error processing entry: {e}")
            continue
    
    return items

def get_source_name(feed_url):
    """Extract human-readable source name from feed URL"""
    # Broadcast & trade press
    if 'newscaststudio' in feed_url:
        return 'NewscastStudio'
    elif 'tvtechnology' in feed_url:
        return 'TV Technology'
    elif 'broadcastbeat' in feed_url:
        return 'BroadcastBeat'
    elif 'svgeurope' in feed_url:
        return 'SVG Europe'
    elif 'sportsvideo' in feed_url:
        return 'Sports Video Group'
    elif 'tvbeurope' in feed_url:
        return 'TVBEurope'
    elif 'digitaltvnews' in feed_url:
        return 'Digital TV News'
    elif 'digitaltveurope' in feed_url:
        return 'Digital TV Europe'
    elif 'rapidtvnews' in feed_url:
        return 'Rapid TV News'
    elif 'ibc.org' in feed_url:
        return 'IBC'
    elif 'nab.org' in feed_url:
        return 'NAB'
    elif 'broadcastnow' in feed_url:
        return 'Broadcast Now'
    elif 'broadcastbridge' in feed_url or 'thebroadcastbridge' in feed_url:
        return 'The Broadcast Bridge'
    # Playout & broadcast vendors
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
    elif 'grassvalley' in feed_url:
        return 'Grass Valley'
    elif 'pebble.tv' in feed_url:
        return 'Pebble'
    elif 'playboxtechnology' in feed_url:
        return 'PlayBox Technology'
    # Graphics vendors
    elif 'vizrt' in feed_url:
        return 'Vizrt'
    elif 'motionographer' in feed_url:
        return 'Motionographer'
    elif 'cgchannel' in feed_url:
        return 'CG Channel'
    elif 'realtimevfx' in feed_url:
        return 'RealtimeVFX'
    # Cloud & delivery
    elif 'aws.amazon' in feed_url and 'media' in feed_url:
        return 'AWS Media'
    elif 'aws.amazon' in feed_url:
        return 'AWS'
    elif 'azure.microsoft' in feed_url:
        return 'Azure Media'
    elif 'cloud.google.com' in feed_url and 'media' in feed_url:
        return 'Google Cloud Media'
    elif 'cloud.google.com' in feed_url:
        return 'Google Cloud'
    elif 'akamai' in feed_url:
        return 'Akamai'
    elif 'fastly' in feed_url:
        return 'Fastly'
    elif 'limelight' in feed_url:
        return 'Limelight'
    elif 'bitmovin' in feed_url:
        return 'Bitmovin'
    elif 'frame.io' in feed_url:
        return 'Frame.io'
    # MAM/PAM & workflow
    elif 'signiant' in feed_url:
        return 'Signiant'
    elif 'chesa.com' in feed_url:
        return 'Chesa'
    elif 'cloudinary' in feed_url:
        return 'Cloudinary'
    # Storage
    elif 'studionetworksolutions' in feed_url:
        return 'Studio Network Solutions'
    elif 'scalelogicinc' in feed_url:
        return 'ScaleLogic'
    elif 'qsan.io' in feed_url:
        return 'QSAN'
    elif 'keycodemedia' in feed_url:
        return 'Keycode Media'
    # Streaming vendors
    elif 'haivision' in feed_url:
        return 'Haivision'
    elif 'streamingmediablog' in feed_url:
        return 'Streaming Media Blog'
    elif 'dacast' in feed_url:
        return 'Dacast'
    elif 'onthefly.stream' in feed_url:
        return 'OnTheFly'
    elif 'yololiv' in feed_url:
        return 'YoloLiv'
    # AI & post-production
    elif 'provideocoalition' in feed_url:
        return 'Pro Video Coalition'
    elif 'nofilmschool' in feed_url:
        return 'No Film School'
    elif 'newsshooter' in feed_url:
        return 'Newsshooter'
    elif 'bhphotovideo' in feed_url:
        return 'B&H Explora'
    # Low priority general tech
    elif 'techcrunch' in feed_url:
        return 'TechCrunch'
    elif 'engadget' in feed_url:
        return 'Engadget'
    elif 'wired.com' in feed_url:
        return 'WIRED'
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
    """Balance items across categories, with per-source cap to prevent domination"""
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
        # Apply per-source cap within each category
        source_counts = {}
        capped_items = []
        for item in items:
            src = item.get('source', '')
            limit = MAX_ITEMS_LOW_PRIORITY if item.get('_low_priority') else MAX_ITEMS_PER_SOURCE
            src_count = source_counts.get(src, 0)
            if src_count < limit:
                capped_items.append(item)
                source_counts[src] = src_count + 1
        balanced.extend(capped_items[:MIN_PER_CATEGORY])
    
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
                
                items = process_entries(entries, category, source_name, feed_url)
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
