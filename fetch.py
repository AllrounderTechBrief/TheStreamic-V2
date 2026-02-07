#!/usr/bin/env python3
"""
The Streamic - RSS Feed Aggregator (V3 - FULLY FIXED)
Fetches broadcast technology news from multiple RSS sources
"""
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
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"

# ============================================================================
# CATEGORY RSS FEEDS - FULLY WORKING SOURCES
# ============================================================================

FEED_SOURCES = {
    # -------- NEWSROOM --------
    "newsroom": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
        {"url": "https://www.newscaststudio.com/feed/", "label": "NewscastStudio"},
        {"url": "https://www.tvnewscheck.com/rss/", "label": "TV NewsCheck"},
    ],
    
    # -------- PLAYOUT --------
    "playout": [
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://imaginecommunications.com/feed/", "label": "Imagine Communications"},
        {"url": "https://www.grassvalley.com/news-rss/", "label": "Grass Valley"},
        {"url": "https://www.harmonicinc.com/insights/blog/rss.xml", "label": "Harmonic"},
    ],
    
    # -------- INFRASTRUCTURE --------
    "infrastructure": [
        # Broadcast infrastructure / engineering
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"},
        {"url": "https://www.smpte.org/rss.xml", "label": "SMPTE"},
        {"url": "https://www.haivision.com/feed/", "label": "Haivision"},
        # IP Networking
        {"url": "https://www.evertz.com/resources/news-and-events/rss", "label": "Evertz"},
        {"url": "https://www.cisco.com/c/en/us/about/press-room.rss", "label": "Cisco"},
        # Cybersecurity for broadcast
        {"url": "https://www.darkreading.com/rss.xml", "label": "Dark Reading"},
        {"url": "https://www.csoonline.com/feed", "label": "CSO Online"},
    ],
    
    # -------- GRAPHICS --------
    "graphics": [
        # Broadcast graphics / industry news
        {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio Graphics"},
        {"url": "https://www.tvnewscheck.com/rss/", "label": "TV NewsCheck"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"},
        # Motion design / 3D / VFX
        {"url": "https://motionographer.com/feed/", "label": "Motionographer"},
        {"url": "https://www.creativebloq.com/feed", "label": "Creative Bloq"},
        {"url": "https://cgchannel.com/feed/", "label": "CG Channel"},
        # Adobe / Creative Cloud
        {"url": "https://blog.adobe.com/en/feed", "label": "Adobe Blog"},
        # Broadcast graphics vendors
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://chyron.com/feed/", "label": "Chyron"},
        {"url": "https://www.vizrt.com/news/rss.xml", "label": "Vizrt"},
    ],
    
    # -------- CLOUD --------
    "cloud": [
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},
        {"url": "https://azure.microsoft.com/en-us/blog/feed/", "label": "Azure"},
        {"url": "https://www.adobe.com/creativecloud/business/teams.rss", "label": "Adobe Creative Cloud"},
        {"url": "https://www.telestream.net/company/press/rss.xml", "label": "Telestream"},
    ],
    
    # -------- STREAMING --------
    "streaming": [
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews", "label": "Streaming Media News"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedArticles", "label": "Streaming Media Articles"},
        {"url": "http://feeds.infotoday.com/Streaming-Media-Blog", "label": "Streaming Media Blog"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-IndustryNews", "label": "Streaming Media Industry"},
        {"url": "https://streamingmediablog.com/feed", "label": "Streaming Media Blog"},
        {"url": "https://www.wowza.com/blog/feed", "label": "Wowza"},
        {"url": "https://www.bitmovin.com/feed/", "label": "Bitmovin"},
    ],
    
    # -------- AUDIO & AI --------
    "audio-ai": [
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},
        {"url": "https://www.audinate.com/feed", "label": "Audinate"},
        {"url": "https://www.waves.com/news-and-events/rss", "label": "Waves Audio"},
        {"url": "https://www.avid.com/blog/rss.xml", "label": "Avid"},
    ]
}

# ============================================================================
# IMAGE EXTRACTION - ENHANCED MULTI-LAYER STRATEGY
# ============================================================================

def get_best_image(item):
    """
    Enhanced 7-layer image extraction strategy.
    Returns the first valid image URL found, or empty string.
    """
    namespaces = {
        'media': 'http://search.yahoo.com/mrss/',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'enclosure': 'http://purl.oclc.org/net/rss_2.0/enc#'
    }
    
    # Layer 1: Media RSS namespace - media:content
    media_content = item.find('media:content', namespaces)
    if media_content is not None:
        url = media_content.get('url')
        if url and is_valid_image_url(url):
            return clean_url(url)
    
    # Layer 2: Media RSS namespace - media:thumbnail
    media_thumbnail = item.find('media:thumbnail', namespaces)
    if media_thumbnail is not None:
        url = media_thumbnail.get('url')
        if url and is_valid_image_url(url):
            return clean_url(url)
    
    # Layer 3: Media group (some feeds nest content)
    media_group = item.find('media:group', namespaces)
    if media_group is not None:
        group_content = media_group.find('media:content', namespaces)
        if group_content is not None:
            url = group_content.get('url')
            if url and is_valid_image_url(url):
                return clean_url(url)
    
    # Layer 4: Standard enclosure tag
    enclosure = item.find('enclosure')
    if enclosure is not None:
        enc_type = (enclosure.get('type') or '').lower()
        if 'image' in enc_type:
            url = enclosure.get('url')
            if url and is_valid_image_url(url):
                return clean_url(url)
    
    # Layer 5: content:encoded (WordPress style)
    content_encoded = item.find('content:encoded', namespaces)
    if content_encoded is not None and content_encoded.text:
        img_url = extract_image_from_html(content_encoded.text)
        if img_url:
            return clean_url(img_url)
    
    # Layer 6: Description field HTML parsing
    description = item.findtext('description') or ""
    if description:
        img_url = extract_image_from_html(description)
        if img_url:
            return clean_url(img_url)
    
    # Layer 7: Look for og:image or twitter:image in description
    if description:
        og_patterns = [
            r'og:image["\s]+content=["\']([^"\']+)',
            r'twitter:image["\s]+content=["\']([^"\']+)',
        ]
        for pattern in og_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                url = match.group(1)
                if is_valid_image_url(url):
                    return clean_url(url)
    
    return ""

def extract_image_from_html(html_content):
    """Extract first valid image from HTML content."""
    if not html_content:
        return None
    
    # Try multiple regex patterns
    patterns = [
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+src=([^\s>]+)',
        r'background-image:\s*url\(["\']?([^"\')\s]+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        for url in matches:
            # Clean up URL
            url = url.strip()
            if is_valid_image_url(url):
                return url
    
    return None

def is_valid_image_url(url):
    """Validate if URL is likely a real image."""
    if not url or len(url) < 10:
        return False
    
    url_lower = url.lower()
    
    # Reject obvious placeholders
    reject_patterns = [
        '1x1', 'pixel', 'spacer', 'blank', 'transparent',
        'placeholder', 'default', 'avatar', 'gravatar',
        '/s/', 'data:image', 'base64'
    ]
    if any(pattern in url_lower for pattern in reject_patterns):
        return False
    
    # Accept if has image extension
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
    url_base = url.split('?')[0].lower()
    if url_base.endswith(image_extensions):
        return True
    
    # Accept if URL contains image-related domains/paths
    image_indicators = [
        'image', 'img', 'photo', 'picture', 'media',
        'uploads', 'content', 'cdn', 'cloudinary',
        'unsplash', 'pexels', 'pixabay'
    ]
    if any(indicator in url_lower for indicator in image_indicators):
        # But must look like an image file
        if any(ext[1:] in url_lower for ext in image_extensions):
            return True
    
    return False

def clean_url(url):
    """Clean and normalize URL."""
    if not url:
        return ""
    
    # Remove HTML entities
    url = unescape(url)
    
    # Strip whitespace
    url = url.strip()
    
    # Ensure proper protocol
    if url.startswith('//'):
        url = 'https:' + url
    
    return url

# ============================================================================
# RSS FETCHING
# ============================================================================

def fetch_feed(url, timeout=20):
    """Fetch RSS feed with error handling."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': USER_AGENT,
                'Accept': 'application/rss+xml, application/xml, text/xml, */*'
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        print(f"      ✗ HTTP {e.code}")
        return None
    except urllib.error.URLError as e:
        print(f"      ✗ Network error: {e.reason}")
        return None
    except Exception as e:
        print(f"      ✗ Error: {str(e)[:50]}")
        return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run():
    """Main function to fetch and aggregate RSS feeds."""
    print("=" * 70)
    print("  THE STREAMIC - RSS FEED AGGREGATOR (V3)")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    all_news = []
    stats = {}
    
    for category, sources in FEED_SOURCES.items():
        print(f"\n📂 {category.upper().replace('-', ' & ')}")
        print("-" * 70)
        
        category_count = 0
        
        for source in sources:
            label = source['label']
            url = source['url']
            
            print(f"   Fetching: {label:30s} ", end='', flush=True)
            
            xml_data = fetch_feed(url)
            if not xml_data:
                continue
            
            try:
                root = ET.fromstring(xml_data)
                items = root.findall('.//item')
                
                if not items:
                    print("✗ No items")
                    continue
                
                for item in items:
                    guid = item.findtext('guid') or item.findtext('link') or ""
                    if not guid:
                        continue
                    
                    title = item.findtext('title') or "Untitled"
                    title = unescape(title).strip()
                    
                    link = item.findtext('link') or ""
                    
                    image = get_best_image(item)
                    
                    all_news.append({
                        "guid": guid,
                        "title": title,
                        "link": link,
                        "source": label,
                        "category": category,
                        "image": image,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    category_count += 1
                
                print(f"✓ {len(items)} items")
                
            except ET.ParseError as e:
                print(f"✗ XML parse error")
            except Exception as e:
                print(f"✗ {str(e)[:30]}")
        
        stats[category] = category_count
    
    # Deduplicate by GUID
    unique_news = list({item['guid']: item for item in all_news if item['guid']}.values())
    
    # Save to JSON
    DATA_DIR.mkdir(exist_ok=True)
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique_news, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for category in FEED_SOURCES.keys():
        count = stats.get(category, 0)
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {category.upper().replace('-', ' & '):20s} : {count:3d} items")
    
    print("-" * 70)
    print(f"  TOTAL UNIQUE ITEMS: {len(unique_news)}")
    print(f"  Saved to: {NEWS_FILE}")
    print("=" * 70)
    
    # Check for empty categories
    empty_categories = [cat for cat, count in stats.items() if count == 0]
    if empty_categories:
        print("\n⚠️  WARNING: Empty categories detected!")
        for cat in empty_categories:
            print(f"     - {cat}")
        print("     Check RSS feed URLs or network connectivity.\n")

if __name__ == "__main__":
    run()
