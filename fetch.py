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

# Categorized Sources - Fixed to match HTML data-category exactly
FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Technology"},
        {"url": "https://www.broadcastingcable.com/feeds/all", "label": "Broadcasting & Cable"},
        {"url": "https://www.newscaststudio.com/feed/", "label": "NewscastStudio"}
    ],
    "playout": [
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://imaginecommunications.com/feed/", "label": "Imagine Communications"},
        {"url": "https://www.grassvalley.com/news-rss/", "label": "Grass Valley"}
    ],
    "infrastructure": [
        {"url": "https://www.smpte.org/rss.xml", "label": "SMPTE"},
        {"url": "https://www.haivision.com/feed/", "label": "Haivision"},
        {"url": "https://www.evertz.com/resources/news-and-events/rss", "label": "Evertz"}
    ],
    "graphics": [
        {"url": "https://www.vizrt.com/news/rss.xml", "label": "Vizrt"},
        {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio Graphics"},
        {"url": "https://www.chyronhego.com/feed/", "label": "ChyronHego"}
    ],
    "cloud": [
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
        {"url": "https://blog.google/products/google-cloud/rss/", "label": "Google Cloud"}
    ],
    "streaming": [
        {"url": "https://www.streamingmedia.com/RSS/RSSFeed.aspx", "label": "Streaming Media"},
        {"url": "https://www.wowza.com/blog/feed", "label": "Wowza"}
    ],
    "audio-ai": [
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},
        {"url": "https://www.audinate.com/feed", "label": "Audinate"}
    ]
}

def get_best_image(item):
    """
    Enhanced image extraction with multiple fallback strategies.
    Prioritizes higher quality images and handles various RSS formats.
    """
    # 1. Try Media RSS Namespace (Most common in professional feeds)
    namespaces = {
        'media': 'http://search.yahoo.com/mrss/',
        'content': 'http://purl.org/rss/1.0/modules/content/'
    }
    
    # Try media:content with url attribute
    media_content = item.find('media:content', namespaces)
    if media_content is not None:
        url = media_content.get('url')
        if url and is_valid_image_url(url):
            return url
    
    # Try media:thumbnail
    media_thumbnail = item.find('media:thumbnail', namespaces)
    if media_thumbnail is not None:
        url = media_thumbnail.get('url')
        if url and is_valid_image_url(url):
            return url
    
    # Try media:group > media:content
    media_group = item.find('media:group', namespaces)
    if media_group is not None:
        group_content = media_group.find('media:content', namespaces)
        if group_content is not None:
            url = group_content.get('url')
            if url and is_valid_image_url(url):
                return url

    # 2. Try Standard Enclosure
    enclosure = item.find('enclosure')
    if enclosure is not None:
        enclosure_type = enclosure.get('type', '')
        if 'image' in enclosure_type:
            url = enclosure.get('url')
            if url and is_valid_image_url(url):
                return url

    # 3. Try content:encoded namespace (WordPress style)
    content_encoded = item.find('content:encoded', namespaces)
    if content_encoded is not None and content_encoded.text:
        img_url = extract_image_from_html(content_encoded.text)
        if img_url:
            return img_url

    # 4. Regex Fallback: Search Description for <img> tags
    description = item.findtext('description') or ""
    if description:
        img_url = extract_image_from_html(description)
        if img_url:
            return img_url

    # 5. Look for og:image or other meta patterns in description
    og_match = re.search(r'og:image["\s]+content=["\']([^"\']+)', description)
    if og_match:
        url = og_match.group(1)
        if is_valid_image_url(url):
            return url

    return ""

def extract_image_from_html(html_content):
    """Extract first valid image URL from HTML content."""
    # Look for img src with various quote styles
    patterns = [
        r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^"\']*)?)["\']',
        r'<img[^>]+src=([^\s>]+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s>]*)?)',
    ]
    
    for pattern in patterns:
        img_match = re.search(pattern, html_content, re.IGNORECASE)
        if img_match:
            url = img_match.group(1)
            # Clean up URL
            url = url.split('?')[0] if '?' in url else url
            if is_valid_image_url(url):
                return url
    
    return None

def is_valid_image_url(url):
    """Check if URL is a valid image URL."""
    if not url:
        return False
    
    # Remove query parameters for extension check
    base_url = url.split('?')[0].lower()
    
    # Check for common image extensions
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    if not base_url.endswith(valid_extensions):
        # Some feeds have images without extensions but in image domains
        image_domains = ['unsplash.com', 'images.', 'img.', 'media.', 'cdn.']
        if not any(domain in url.lower() for domain in image_domains):
            return False
    
    # Reject tiny placeholder images
    if any(reject in url.lower() for reject in ['1x1', 'pixel', 'spacer', 'blank']):
        return False
    
    return True

def fetch_feed(url):
    """Fetch RSS feed with error handling."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        print(f"  ! HTTP Error {e.code} fetching {url}")
        return None
    except urllib.error.URLError as e:
        print(f"  ! URL Error fetching {url}: {e.reason}")
        return None
    except Exception as e:
        print(f"  ! Error fetching {url}: {e}")
        return None

def run():
    print(f"Starting Refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    all_news = []
    
    for category, sources in FEED_SOURCES.items():
        print(f"\nProcessing Category: {category.upper()}")
        print("-" * 40)
        for source in sources:
            print(f"  Fetching {source['label']}...", end=" ")
            xml_data = fetch_feed(source['url'])
            if not xml_data:
                print("FAILED")
                continue
            
            try:
                root = ET.fromstring(xml_data)
                items = root.findall('.//item')
                
                for i in items:
                    image_url = get_best_image(i)
                    
                    all_news.append({
                        "guid": i.findtext('guid') or i.findtext('link') or "",
                        "title": unescape(i.findtext('title') or "Untitled"),
                        "link": i.findtext('link') or "",
                        "source": source['label'],
                        "category": category,
                        "image": image_url,
                        "timestamp": datetime.now().isoformat()
                    })
                
                print(f"OK ({len(items)} items)")
                
            except ET.ParseError as e:
                print(f"PARSE ERROR: {e}")
            except Exception as e:
                print(f"ERROR: {e}")

    # Deduplicate by GUID
    unique_news = list({item['guid']: item for item in all_news if item['guid']}.values())
    
    # Save output
    DATA_DIR.mkdir(exist_ok=True)
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique_news, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"✓ Finished. Total unique items: {len(unique_news)}")
    print(f"✓ Saved to: {NEWS_FILE}")
    
    # Summary by category
    print("\nCategory Summary:")
    print("-" * 40)
    for category in FEED_SOURCES.keys():
        count = len([item for item in unique_news if item['category'] == category])
        print(f"  {category:20s}: {count:3d} items")

if __name__ == "__main__":
    run()
