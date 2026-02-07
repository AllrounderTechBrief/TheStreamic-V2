#!/usr/bin/env python3
"""The Streamic - RSS Aggregator V8 - FIXED with Working Feeds"""
import json, time, urllib.request, urllib.error, xml.etree.ElementTree as ET
from html import unescape, parser as HTMLParser_module
from datetime import datetime
from pathlib import Path
import re

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATA_DIR, NEWS_FILE, MAX_NEWS_ITEMS = Path("data"), Path("data/news.json"), 150

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
    
    # FIXED STREAMING FEEDS - Using more reliable sources
    "streaming": [
        # Use TV Technology streaming section (more reliable)
        {"url": "https://www.tvtechnology.com/platform/streaming/rss.xml", "label": "TV Tech Streaming"},
        {"url": "https://www.tvtechnology.com/business/rss.xml", "label": "TV Tech Business"},
        # Broadcast Beat covers streaming
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"},
        # SVG Europe covers OTT/streaming
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
        # InBroadcast covers streaming
        {"url": "https://www.inbroadcast.com/rss.xml", "label": "InBroadcast"},
    ],
    
    # FIXED AUDIO-AI FEEDS - Using more reliable sources
    "audio-ai": [
        # TV Technology audio section
        {"url": "https://www.tvtechnology.com/production/rss.xml", "label": "TV Tech Production"},
        # Broadcast Beat covers audio
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"},
        # NewscastStudio covers audio tech
        {"url": "https://www.newscaststudio.com/tag/audio/feed/", "label": "NewscastStudio Audio"},
        # SVG Europe covers audio
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
        # AWS Media includes AI/ML
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
    ]
}

class ImageScraper(HTMLParser_module.HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None
    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.image_url:
            for attr, value in attrs:
                if attr == 'src' and value and any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    self.image_url = value

def get_best_image(item_xml):
    candidates = []
    media_ns = '{http://search.yahoo.com/mrss/}'
    for elem in [item_xml.find(f'{media_ns}content'), item_xml.find(f'{media_ns}thumbnail')]:
        if elem is not None and elem.get('url'): candidates.append(elem.get('url'))
    enc = item_xml.find('enclosure')
    if enc is not None and 'image' in enc.get('type', '') and enc.get('url'): candidates.append(enc.get('url'))
    for tag_name in ['description', '{http://purl.org/rss/1.0/modules/content/}encoded']:
        elem = item_xml.find(tag_name)
        if elem is not None and elem.text:
            parser = ImageScraper()
            try: parser.feed(elem.text)
            except: pass
            if parser.image_url: candidates.append(parser.image_url)
            candidates.extend(re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', elem.text, re.I))
            candidates.extend(re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', elem.text, re.I))
    for url in candidates:
        url = url.strip()
        if url.startswith('//'): url = 'https:' + url
        if any(bad in url.lower() for bad in ['1x1', 'spacer', 'blank', 'pixel', 'data:image', 'avatar', 'gravatar']): continue
        if url.startswith('http') and (re.search(r'\.(jpg|jpeg|png|gif|webp|svg)', url, re.I) or any(kw in url.lower() for kw in ['image', 'media', 'photo', 'wp-content'])):
            return url
    return ""

def fetch_url(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        print(f" ✗ HTTP {e.code}")
        return None
    except urllib.error.URLError as e:
        print(f" ✗ URL Error")
        return None
    except Exception as e:
        print(f" ✗ Error")
        return None

def parse_rss_feed(xml_data, category, source_label):
    try:
        root, items = ET.fromstring(xml_data), []
        for item_xml in root.findall('.//item'):
            title_elem, link_elem, guid_elem = item_xml.find('title'), item_xml.find('link'), item_xml.find('guid')
            items.append({
                "guid": guid_elem.text if guid_elem is not None and guid_elem.text else (link_elem.text if link_elem is not None else ""),
                "title": unescape(title_elem.text).strip() if title_elem is not None and title_elem.text else "Untitled",
                "link": link_elem.text.strip() if link_elem is not None and link_elem.text else "#",
                "category": category,
                "image": get_best_image(item_xml),
                "source": source_label,
                "timestamp": datetime.now().isoformat()
            })
        return items
    except:
        return []

def run_workflow():
    print("="*70)
    print(" THE STREAMIC V8 - FIXED FEEDS")
    print("="*70)
    DATA_DIR.mkdir(exist_ok=True)
    all_new_items, stats = [], {}
    
    for category, feeds in FEED_SOURCES.items():
        print(f"\n📂 {category.upper().replace('-', ' & ')}")
        print("-"*70)
        cat_count, cat_images = 0, 0
        
        for feed in feeds:
            print(f"  {feed['label']:40s}", end="", flush=True)
            xml_data = fetch_url(feed['url'])
            if xml_data:
                items = parse_rss_feed(xml_data, category, feed['label'])
                if items:
                    imgs = sum(1 for item in items if item['image'])
                    cat_images, cat_count = cat_images + imgs, cat_count + len(items)
                    all_new_items.extend(items)
                    print(f" ✓ {len(items):2d} items ({imgs:2d} imgs)")
                    time.sleep(0.3)
                else:
                    print(" ✗ No items")
        
        stats[category] = {'total': cat_count, 'images': cat_images}
    
    existing = []
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f: existing = json.load(f)
        except: pass
    
    final_list = list({(item.get('guid') or ""): item for item in (all_new_items + existing) if item.get('guid')}.values())[:MAX_NEWS_ITEMS]
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    for cat in FEED_SOURCES.keys():
        s = stats.get(cat, {'total': 0, 'images': 0})
        pct = (s['images'] / s['total'] * 100) if s['total'] > 0 else 0
        print(f" {'✓' if s['total'] > 0 else '✗'} {cat.upper().replace('-', ' & '):20s} : {s['total']:3d} items, {s['images']:3d} imgs ({pct:.0f}%)")
    
    print("-"*70)
    print(f" NEW ITEMS: {len(all_new_items)}")
    print(f" TOTAL: {len(final_list)}")
    print(f" WITH IMAGES: {sum(1 for item in final_list if item.get('image'))}")
    print("="*70)

if __name__ == "__main__":
    run_workflow()
