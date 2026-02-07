#!/usr/bin/env python3
"""
The Streamic - ULTIMATE RSS Aggregator (V7 - BEST OF BOTH)
Combines: Your visual-rich feed sources + Ultra-aggressive image extraction
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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"
MAX_NEWS_ITEMS = 120

# YOUR VISUAL-RICH FEED SOURCES (from your research!)
FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.newscaststudio.com/tag/news-production/feed/", "label": "NewscastStudio"},
        {"url": "https://www.tvtechnology.com/rss.xml", "label": "TV Tech"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"}
    ],
    "playout": [
        {"url": "https://www.inbroadcast.com/rss.xml", "label": "InBroadcast"},
        {"url": "https://www.tvtechnology.com/playout/rss.xml", "label": "TV Tech Playout"},
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://www.harmonicinc.com/insights/blog/rss.xml", "label": "Harmonic"},
    ],
    "infrastructure": [
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
        {"url": "https://www.thebroadcastbridge.com/rss/all", "label": "Broadcast Bridge"},
        {"url": "https://www.newscaststudio.com/category/broadcast-engineering/feed/", "label": "NewscastStudio Engineering"},
    ],
    "graphics": [
        {"url": "https://www.newscaststudio.com/tag/tv-news-graphics/feed/", "label": "NewscastStudio Graphics"},
        {"url": "https://www.vizrt.com/feed/", "label": "Vizrt News"},
        {"url": "https://motionographer.com/feed/", "label": "Motionographer"},
    ],
    "cloud": [
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media Blog"},
        {"url": "https://www.tvtechnology.com/cloud/rss.xml", "label": "TV Tech Cloud"},
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
    ],
    "streaming": [
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews", "label": "Streaming Media"},
        {"url": "https://www.haivision.com/blog/feed/", "label": "Haivision Blog"},
        {"url": "https://streamingmediablog.com/feed", "label": "Dan Rayburn"},
    ],
    "audio-ai": [
        {"url": "https://www.radioworld.com/rss.xml", "label": "Radio World"},
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech AI"},
        {"url": "https://www.audinate.com/feed", "label": "Audinate"},
    ]
}

# YOUR HTML PARSER (for description scraping)
class ImageScraper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None
    
    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.image_url:
            for attr, value in attrs:
                if attr == 'src' and value:
                    # Validate it's a real image URL
                    if any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        self.image_url = value

# MY ULTRA-AGGRESSIVE IMAGE EXTRACTION
def get_best_image(item_xml):
    """
    ULTIMATE IMAGE EXTRACTION - Combines both approaches!
    """
    candidates = []
    
    # METHOD 1: Standard media:content namespace
    media_ns = '{http://search.yahoo.com/mrss/}'
    media_content = item_xml.find(f'{media_ns}content')
    if media_content is not None:
        url = media_content.get('url')
        if url:
            candidates.append(url)
    
    # METHOD 2: media:thumbnail
    media_thumbnail = item_xml.find(f'{media_ns}thumbnail')
    if media_thumbnail is not None:
        url = media_thumbnail.get('url')
        if url:
            candidates.append(url)
    
    # METHOD 3: Standard enclosure
    enclosure = item_xml.find('enclosure')
    if enclosure is not None:
        enc_type = enclosure.get('type', '')
        if 'image' in enc_type:
            url = enclosure.get('url')
            if url:
                candidates.append(url)
    
    # METHOD 4: YOUR HTML PARSER (for description)
    desc = item_xml.find('description')
    if desc is not None and desc.text:
        parser = ImageScraper()
        try:
            parser.feed(desc.text)
            if parser.image_url:
                candidates.append(parser.image_url)
        except:
            pass
    
    # METHOD 5: MY REGEX EXTRACTION (for description)
    if desc is not None and desc.text:
        # Look for any img src
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', desc.text, re.I)
        candidates.extend(img_matches)
        
        # Look for direct image URLs
        url_matches = re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', desc.text, re.I)
        candidates.extend(url_matches)
    
    # METHOD 6: content:encoded (WordPress)
    content_ns = '{http://purl.org/rss/1.0/modules/content/}'
    content_encoded = item_xml.find(f'{content_ns}encoded')
    if content_encoded is not None and content_encoded.text:
        # HTML parser
        parser2 = ImageScraper()
        try:
            parser2.feed(content_encoded.text)
            if parser2.image_url:
                candidates.append(parser2.image_url)
        except:
            pass
        
        # Regex extraction
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content_encoded.text, re.I)
        candidates.extend(img_matches)
        url_matches = re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', content_encoded.text, re.I)
        candidates.extend(url_matches)
    
    # METHOD 7: Check ALL elements and attributes (aggressive)
    for elem in item_xml.iter():
        # Check element text
        if elem.text:
            urls = re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', elem.text, re.I)
            candidates.extend(urls)
        
        # Check all attributes
        for attr_val in elem.attrib.values():
            if attr_val:
                urls = re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', str(attr_val), re.I)
                candidates.extend(urls)
    
    # FILTER AND VALIDATE
    for url in candidates:
        url = url.strip()
        
        # Clean URL
        if url.startswith('//'):
            url = 'https:' + url
        
        # Reject junk
        if any(bad in url.lower() for bad in ['1x1', 'spacer', 'blank', 'pixel', 'data:image', 'avatar', 'gravatar']):
            continue
        
        # Must be http
        if not url.startswith('http'):
            continue
        
        # Must have image extension or keywords
        if not (re.search(r'\.(jpg|jpeg|png|gif|webp|svg)', url, re.I) or 
                any(kw in url.lower() for kw in ['image', 'media', 'photo', 'wp-content'])):
            continue
        
        # Return first valid image
        return url
    
    return ""

def fetch_url(url, timeout=15):
    """Fetch with proper error handling"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code}")
        return None
    except Exception as e:
        print(f"    Error: {str(e)[:40]}")
        return None

def parse_rss_feed(xml_data, category, source_label):
    """Parse RSS feed with extensive error handling"""
    try:
        root = ET.fromstring(xml_data)
        items = []
        
        for item_xml in root.findall('.//item'):
            # Extract fields
            title_elem = item_xml.find('title')
            title = unescape(title_elem.text).strip() if title_elem is not None and title_elem.text else "Untitled"
            
            link_elem = item_xml.find('link')
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else "#"
            
            guid_elem = item_xml.find('guid')
            guid = guid_elem.text if guid_elem is not None and guid_elem.text else link
            
            pub_date_elem = item_xml.find('pubDate')
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""
            
            # ULTIMATE IMAGE EXTRACTION
            image = get_best_image(item_xml)
            
            items.append({
                "guid": guid,
                "title": title,
                "link": link,
                "date": pub_date,
                "category": category,
                "image": image,
                "source": source_label,
                "timestamp": datetime.now().isoformat()
            })
        
        return items
    except ET.ParseError as e:
        print(f"    Parse error: {e}")
        return []
    except Exception as e:
        print(f"    Error: {str(e)[:40]}")
        return []

def run_workflow():
    print("="*70)
    print(" THE STREAMIC - ULTIMATE RSS AGGREGATOR")
    print(" Combining: Visual-rich feeds + Ultra-aggressive extraction")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    DATA_DIR.mkdir(exist_ok=True)
    
    all_new_items = []
    stats = {}
    
    for category, feeds in FEED_SOURCES.items():
        print(f"\n📂 {category.upper().replace('-', ' & ')}")
        print("-"*70)
        
        cat_count = 0
        cat_images = 0
        
        for feed in feeds:
            label = feed['label']
            url = feed['url']
            
            print(f"  {label:30s}", end="", flush=True)
            
            xml_data = fetch_url(url)
            if xml_data:
                items = parse_rss_feed(xml_data, category, label)
                
                # Count images
                imgs = sum(1 for item in items if item['image'])
                cat_images += imgs
                cat_count += len(items)
                
                all_new_items.extend(items)
                print(f" ✓ {len(items)} items ({imgs} imgs)")
                
                time.sleep(0.5)  # Be nice to servers
            else:
                print(" ✗ Failed")
        
        stats[category] = {'total': cat_count, 'images': cat_images}
    
    # Load existing news for deduplication
    existing = []
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            existing = []
    
    # Merge and deduplicate (prioritize new items)
    combined = all_new_items + existing
    seen_guids = set()
    final_list = []
    
    for item in combined:
        guid = item.get('guid')
        if guid and guid not in seen_guids:
            seen_guids.add(guid)
            final_list.append(item)
    
    # Limit to MAX_NEWS_ITEMS
    final_list = final_list[:MAX_NEWS_ITEMS]
    
    # Save
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    
    total_imgs = 0
    for cat in FEED_SOURCES.keys():
        s = stats.get(cat, {'total': 0, 'images': 0})
        total_imgs += s['images']
        pct = (s['images'] / s['total'] * 100) if s['total'] > 0 else 0
        status = "✓" if s['total'] > 0 else "✗"
        print(f" {status} {cat.upper().replace('-', ' & '):20s} : {s['total']:3d} items, {s['images']:3d} imgs ({pct:.0f}%)")
    
    print("-"*70)
    print(f" NEW ITEMS FETCHED: {len(all_new_items)}")
    print(f" TOTAL IN DATABASE: {len(final_list)}")
    print(f" ITEMS WITH IMAGES: {sum(1 for item in final_list if item.get('image'))}")
    print(f" Saved to: {NEWS_FILE}")
    print("="*70)
    
    # Show which categories have best image coverage
    if total_imgs > 0:
        print("\n💡 IMAGE COVERAGE BY CATEGORY:")
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]['images'], reverse=True)
        for cat, s in sorted_stats[:3]:
            pct = (s['images'] / s['total'] * 100) if s['total'] > 0 else 0
            print(f"   🏆 {cat.upper():20s} : {pct:.0f}% image coverage")

if __name__ == "__main__":
    run_workflow()
