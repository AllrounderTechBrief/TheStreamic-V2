#!/usr/bin/env python3
"""
The Streamic - ULTIMATE RSS Aggregator (V7.1 - EXPANDED FEEDS)
Now with comprehensive Streaming and Audio-AI feed sources!
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
MAX_NEWS_ITEMS = 150  # Increased for more content

# EXPANDED FEED SOURCES - Now with comprehensive Streaming & Audio-AI!
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
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},
        {"url": "https://azure.microsoft.com/en-us/blog/feed/", "label": "Azure Blog"},
    ],
    
    # EXPANDED STREAMING - Your comprehensive list!
    "streaming": [
        # StreamingMedia — Official feeds
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews", "label": "Streaming Media News"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedArticles", "label": "Streaming Media Articles"},
        {"url": "http://feeds.infotoday.com/Streaming-Media-Blog", "label": "Streaming Media Blog"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-IndustryNews", "label": "Streaming Media Industry"},
        
        # Professional Tools / Encoding
        {"url": "https://www.telestream.net/company/press/rss.xml", "label": "Telestream"},
        {"url": "https://www.haivision.com/blog/feed/", "label": "Haivision Blog"},
        
        # OTT Engineering
        {"url": "https://ottverse.com/feed/", "label": "OTTVerse"},
        
        # CDN / Delivery
        {"url": "https://blog.blazingcdn.com/en-us/feed/", "label": "BlazingCDN"},
        
        # OTT Platforms
        {"url": "https://vodlix.com/feed/", "label": "Vodlix"},
        
        # Video Streaming Tech
        {"url": "https://streamingmediablog.com/feed", "label": "Dan Rayburn Blog"},
        
        # Enterprise OTT
        {"url": "https://www.globallogic.com/feed/", "label": "GlobalLogic OTT"},
        
        # Streaming Consulting
        {"url": "https://bmps.tech/feed/", "label": "BMPS Technology"},
    ],
    
    # EXPANDED AUDIO-AI - Your comprehensive list!
    "audio-ai": [
        # Broadcast Audio
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},
        {"url": "https://www.radioworld.com/rss.xml", "label": "Radio World"},
        {"url": "https://www.waves.com/news-and-events/rss", "label": "Waves Audio"},
        {"url": "https://www.production-expert.com/production-expert-1?format=rss", "label": "Production Expert"},
        {"url": "https://www.avid.com/blog/rss.xml", "label": "Avid / Pro Tools"},
        
        # AoIP – Dante, AES67, Ravenna
        {"url": "https://www.audinate.com/feed", "label": "Audinate – Dante"},
        {"url": "https://www.merging.com/rss.xml", "label": "Merging – Ravenna/AES67"},
        
        # Cloud Media Processing (relevant to audio workflows)
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},
    ]
}

# HTML PARSER for description scraping
class ImageScraper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None
    
    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.image_url:
            for attr, value in attrs:
                if attr == 'src' and value:
                    if any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        self.image_url = value

# ULTRA-AGGRESSIVE IMAGE EXTRACTION (7 layers)
def get_best_image(item_xml):
    """Ultimate image extraction combining all methods"""
    candidates = []
    
    # Layer 1: Standard media:content
    media_ns = '{http://search.yahoo.com/mrss/}'
    for elem in [item_xml.find(f'{media_ns}content'), item_xml.find(f'{media_ns}thumbnail')]:
        if elem is not None:
            url = elem.get('url')
            if url:
                candidates.append(url)
    
    # Layer 2: Standard enclosure
    enclosure = item_xml.find('enclosure')
    if enclosure is not None and 'image' in enclosure.get('type', ''):
        url = enclosure.get('url')
        if url:
            candidates.append(url)
    
    # Layer 3: HTML Parser on description
    desc = item_xml.find('description')
    if desc is not None and desc.text:
        parser = ImageScraper()
        try:
            parser.feed(desc.text)
            if parser.image_url:
                candidates.append(parser.image_url)
        except:
            pass
    
    # Layer 4: Regex on description
    if desc is not None and desc.text:
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', desc.text, re.I)
        candidates.extend(img_matches)
        url_matches = re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', desc.text, re.I)
        candidates.extend(url_matches)
    
    # Layer 5: content:encoded (WordPress)
    content_ns = '{http://purl.org/rss/1.0/modules/content/}'
    content_encoded = item_xml.find(f'{content_ns}encoded')
    if content_encoded is not None and content_encoded.text:
        parser2 = ImageScraper()
        try:
            parser2.feed(content_encoded.text)
            if parser2.image_url:
                candidates.append(parser2.image_url)
        except:
            pass
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content_encoded.text, re.I)
        candidates.extend(img_matches)
        url_matches = re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', content_encoded.text, re.I)
        candidates.extend(url_matches)
    
    # Layer 6 & 7: Check all elements/attributes
    for elem in item_xml.iter():
        if elem.text:
            urls = re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', elem.text, re.I)
            candidates.extend(urls)
        for attr_val in elem.attrib.values():
            if attr_val:
                urls = re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', str(attr_val), re.I)
                candidates.extend(urls)
    
    # Filter and validate
    for url in candidates:
        url = url.strip()
        if url.startswith('//'):
            url = 'https:' + url
        if any(bad in url.lower() for bad in ['1x1', 'spacer', 'blank', 'pixel', 'data:image', 'avatar', 'gravatar']):
            continue
        if not url.startswith('http'):
            continue
        if not (re.search(r'\.(jpg|jpeg|png|gif|webp|svg)', url, re.I) or 
                any(kw in url.lower() for kw in ['image', 'media', 'photo', 'wp-content'])):
            continue
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
    """Parse RSS feed"""
    try:
        root = ET.fromstring(xml_data)
        items = []
        
        for item_xml in root.findall('.//item'):
            title_elem = item_xml.find('title')
            title = unescape(title_elem.text).strip() if title_elem is not None and title_elem.text else "Untitled"
            
            link_elem = item_xml.find('link')
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else "#"
            
            guid_elem = item_xml.find('guid')
            guid = guid_elem.text if guid_elem is not None and guid_elem.text else link
            
            pub_date_elem = item_xml.find('pubDate')
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""
            
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
    except ET.ParseError:
        return []
    except Exception:
        return []

def run_workflow():
    print("="*70)
    print(" THE STREAMIC - ULTIMATE AGGREGATOR V7.1")
    print(" NOW WITH EXPANDED STREAMING & AUDIO-AI FEEDS!")
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
            
            print(f"  {label:35s}", end="", flush=True)
            
            xml_data = fetch_url(url)
            if xml_data:
                items = parse_rss_feed(xml_data, category, label)
                imgs = sum(1 for item in items if item['image'])
                cat_images += imgs
                cat_count += len(items)
                all_new_items.extend(items)
                print(f" ✓ {len(items)} items ({imgs} imgs)")
                time.sleep(0.5)
            else:
                print(" ✗")
        
        stats[category] = {'total': cat_count, 'images': cat_images}
    
    # Load existing for deduplication
    existing = []
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            existing = []
    
    # Merge and deduplicate
    combined = all_new_items + existing
    seen_guids = set()
    final_list = []
    
    for item in combined:
        guid = item.get('guid')
        if guid and guid not in seen_guids:
            seen_guids.add(guid)
            final_list.append(item)
    
    final_list = final_list[:MAX_NEWS_ITEMS]
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    
    for cat in FEED_SOURCES.keys():
        s = stats.get(cat, {'total': 0, 'images': 0})
        pct = (s['images'] / s['total'] * 100) if s['total'] > 0 else 0
        status = "✓" if s['total'] > 0 else "✗"
        print(f" {status} {cat.upper().replace('-', ' & '):20s} : {s['total']:3d} items, {s['images']:3d} imgs ({pct:.0f}%)")
    
    print("-"*70)
    print(f" NEW ITEMS FETCHED: {len(all_new_items)}")
    print(f" TOTAL IN DATABASE: {len(final_list)}")
    print(f" ITEMS WITH IMAGES: {sum(1 for item in final_list if item.get('image'))}")
    print(f" Saved to: {NEWS_FILE}")
    print("="*70)
    print("\n💡 Streaming & Audio-AI now have comprehensive feed coverage!")

if __name__ == "__main__":
    run_workflow()
