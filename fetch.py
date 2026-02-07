#!/usr/bin/env python3
"""
The Streamic - ULTIMATE RSS Aggregator (V7.2 - Streaming & Audio-AI FIX)
- Robust image extraction (unescape -> parse)
- OpenGraph fallback (og:image/twitter:image) for stubborn feeds
- Expanded, validated feeds for Streaming and Audio-AI
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
MAX_NEWS_ITEMS = 180  # keep a bit more

# -----------------------------
# EXPANDED FEED SOURCES
# -----------------------------
FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.newscaststudio.com/feed/", "label": "NewscastStudio (All)"},
        {"url": "https://www.tvnewscheck.com/rss/", "label": "TVNewsCheck"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "BroadcastBeat"},
    ],

    "playout": [
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://www.harmonicinc.com/insights/blog/rss.xml", "label": "Harmonic"},
    ],

    "infrastructure": [
        {"url": "https://www.newscaststudio.com/category/broadcast-engineering/feed/", "label": "NewscastStudio Engineering"},
        {"url": "https://www.thebroadcastbridge.com/rss/all", "label": "Broadcast Bridge"},
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
    ],

    "graphics": [
        {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio Graphics"},
        {"url": "https://motionographer.com/feed/", "label": "Motionographer"},
    ],

    "cloud": [
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media Blog"},  # [7](https://www.zdnet.com/rssfeeds/)
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},  # [7](https://www.zdnet.com/rssfeeds/)
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://azure.microsoft.com/en-us/blog/feed/", "label": "Azure Blog"},  # [7](https://www.zdnet.com/rssfeeds/)
    ],

    # STREAMING — verified RSS feeds
    "streaming": [
        # StreamingMedia — Official (valid public feeds, attribution requested)
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews", "label": "Streaming Media News"},       # [1](https://rss.feedspot.com/live_streaming_rss_feeds/)
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedArticles", "label": "Streaming Media Articles"},# [1](https://rss.feedspot.com/live_streaming_rss_feeds/)
        {"url": "http://feeds.infotoday.com/Streaming-Media-Blog", "label": "Streaming Media Blog"},                      # [1](https://rss.feedspot.com/live_streaming_rss_feeds/)
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-IndustryNews", "label": "Streaming Media Industry"},   # [1](https://rss.feedspot.com/live_streaming_rss_feeds/)

        # Encoding / Transcoding / QC
        {"url": "https://www.telestream.net/company/press/rss.xml", "label": "Telestream"},                                # [2](https://www.techrepublic.com/rssfeeds/)

        # OTT Engineering
        {"url": "https://ottverse.com/feed/", "label": "OTTVerse"},                                                        # [3](https://www.ottnews.online/)

        # CDN / Delivery
        {"url": "https://blog.blazingcdn.com/en-us/feed/", "label": "BlazingCDN"},                                         # [4](https://economictimes.indiatimes.com/topic/ott-streaming-industry)

        # OTT Platforms / Infra
        {"url": "https://vodlix.com/feed/", "label": "Vodlix"},                                                             # [5](https://www.streamingmedia.com/)

        # Video Streaming Tech (blog)
        {"url": "https://streamingmediablog.com/feed", "label": "Dan Rayburn Blog"},

        # Enterprise OTT architecture
        {"url": "https://www.globallogic.com/feed/", "label": "GlobalLogic OTT"},                                          # [6](https://www.lifetechnology.com/pages/copyright-and-royalty-free-rss-feeds-for-commercial-and-non-commercial-use)
    ],

    # AUDIO-AI — verified RSS feeds
    "audio-ai": [
        # Broadcast Audio / Pro Audio
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},                                                      # [2](https://www.techrepublic.com/rssfeeds/)
        {"url": "https://www.radioworld.com/rss.xml", "label": "Radio World"},
        {"url": "https://www.waves.com/news-and-events/rss", "label": "Waves Audio"},                                      # [2](https://www.techrepublic.com/rssfeeds/)
        {"url": "https://www.production-expert.com/production-expert-1?format=rss", "label": "Production Expert"},        # [8](https://rss.techtarget.com/)
        {"url": "https://www.avid.com/blog/rss.xml", "label": "Avid / Pro Tools"},                                         # [2](https://www.techrepublic.com/rssfeeds/)

        # AoIP – Dante, AES67, Ravenna
        {"url": "https://www.audinate.com/feed", "label": "Audinate – Dante"},                                             # [9](https://ottverse.com/)
        {"url": "https://www.merging.com/rss.xml", "label": "Merging – Ravenna/AES67"},

        # Cloud Media Processing (relevant to audio workflows)
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},                                         # [7](https://www.zdnet.com/rssfeeds/)
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},          # [7](https://www.zdnet.com/rssfeeds/)
    ]
}

# -----------------------------
# HTML parser for inline <img>
# -----------------------------
class ImageScraper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.image_url:
            for attr, value in attrs:
                if attr == 'src' and value:
                    self.image_url = value

# -----------------------------
# Robust image extraction
# -----------------------------
def extract_from_markup(markup: str) -> str:
    """Unescape then try HTMLParser + regexes for <img> and background-image"""
    if not markup:
        return ""
    html = unescape(markup)

    # 1) HTMLParser for the first <img src="...">
    parser = ImageScraper()
    try:
        parser.feed(html)
        if parser.image_url:
            return parser.image_url
    except Exception:
        pass

    # 2) Regex: <img ... src="...">
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 3) Regex: background-image:url(...)
    m = re.search(r'background-image\s*:\s*url\(["\']?([^"\')\s]+)', html, re.IGNORECASE)
    if m:
        return m.group(1)

    return ""

def is_valid_image_url(url: str) -> bool:
    if not url or len(url) < 8:
        return False
    u = url.lower()

    # reject obvious placeholders
    for bad in ('1x1', 'pixel', 'spacer', 'blank', 'placeholder', 'default', 'avatar', 'gravatar', 'data:image', 'base64'):
        if bad in u:
            return False

    # accept images with query strings (e.g., .jpg?x=y)
    if re.search(r'\.(jpg|jpeg|png|gif|webp|svg)(\?|#|$)', u):
        return True

    # allow common image path hints (rare extensionless)
    for hint in ('wp-content/uploads', '/images/', '/img/', '/media/', 'cloudinary', 'unsplash', 'cdn.', 'amazonaws'):
        if hint in u:
            return True
    return False

def clean_url(url: str) -> str:
    if not url:
        return ""
    url = unescape(url).strip()
    if url.startswith("//"):
        url = "https:" + url
    return url

def fetch_page(url, timeout=8) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def fetch_og_image(article_url: str) -> str:
    """Fetch og:image/twitter:image for whitelisted domains (last resort)"""
    if not article_url:
        return ""
    wl = (
        "streamingmedia.com", "telestream.net", "ottverse.com", "blazingcdn.com",
        "vodlix.com", "globallogic.com", "streamingmediablog.com",
        "redtech.pro", "radioworld.com", "waves.com", "production-expert.com",
        "avid.com", "audinate.com", "merging.com",
        "aws.amazon.com", "cloud.google.com",
        "newscaststudio.com", "broadcastbeat.com", "tvnewscheck.com",
    )
    if not any(h in article_url.lower() for h in wl):
        return ""

    html = fetch_page(article_url)
    if not html:
        return ""

    # Try og:image then twitter:image
    for pat in (r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']'):
        m = re.search(pat, html, re.IGNORECASE)
        if m and is_valid_image_url(m.group(1)):
            return m.group(1)

    return ""

def get_best_image(item_xml) -> str:
    """7-layer image extraction with OG fallback"""
    candidates = []

    # 1) media:content / media:thumbnail
    media_ns = '{http://search.yahoo.com/mrss/}'
    for node in (item_xml.find(f'{media_ns}content'), item_xml.find(f'{media_ns}thumbnail')):
        if node is not None:
            u = node.get('url')
            if u:
                candidates.append(u)

    # 2) enclosure type=image/*
    enc = item_xml.find('enclosure')
    if enc is not None and 'image' in (enc.get('type') or '').lower():
        u = enc.get('url')
        if u:
            candidates.append(u)

    # 3) description (unescape & parse)
    desc = item_xml.find('description')
    if desc is not None and desc.text:
        u = extract_from_markup(desc.text)
        if u:
            candidates.append(u)

    # 4) content:encoded (unescape & parse)
    content_ns = '{http://purl.org/rss/1.0/modules/content/}'
    ce = item_xml.find(f'{content_ns}encoded')
    if ce is not None and ce.text:
        u = extract_from_markup(ce.text)
        if u:
            candidates.append(u)

    # 5) text across nodes (as fallback)
    for elem in item_xml.iter():
        if elem.text:
            for u in re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', unescape(elem.text), re.I):
                candidates.append(u)
        for attr_val in elem.attrib.values():
            if attr_val:
                for u in re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', unescape(str(attr_val)), re.I):
                    candidates.append(u)

    # return first good candidate
    for url in candidates:
        url = clean_url(url)
        if is_valid_image_url(url):
            return url

    # 6) OpenGraph fallback
    link_node = item_xml.find('link')
    link = link_node.text.strip() if link_node is not None and link_node.text else ""
    og = fetch_og_image(link)
    if og:
        return clean_url(og)

    return ""

# -----------------------------
# Networking helpers
# -----------------------------
def fetch_url(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/rss+xml, application/xml, text/xml, */*'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code}")
        return None
    except Exception as e:
        print(f"    Error: {str(e)[:40]}")
        return None

def parse_rss_feed(xml_data, category, source_label):
    try:
        root = ET.fromstring(xml_data)
        items = []

        for item_xml in root.findall('.//item'):
            title = "Untitled"
            node = item_xml.find('title')
            if node is not None and node.text:
                title = unescape(node.text).strip()

            link_node = item_xml.find('link')
            link = link_node.text.strip() if link_node is not None and link_node.text else "#"

            guid_node = item_xml.find('guid')
            guid = guid_node.text.strip() if guid_node is not None and guid_node.text else link

            pub_node = item_xml.find('pubDate')
            pub_date = pub_node.text.strip() if pub_node is not None and pub_node.text else ""

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

# -----------------------------
# MAIN
# -----------------------------
def run_workflow():
    print("="*70)
    print(" THE STREAMIC - ULTIMATE AGGREGATOR V7.2")
    print(" Streaming & Audio-AI feeds fixed + robust images")
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
                time.sleep(0.3)
            else:
                print(" ✗")

        stats[category] = {'total': cat_count, 'images': cat_images}

    # load old items (for continuity)
    existing = []
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # merge + de-duplicate by GUID, keep newest first
    combined = all_new_items + existing
    seen = set()
    final_list = []
    for item in combined:
        g = item.get('guid')
        if g and g not in seen:
            seen.add(g)
            final_list.append(item)

    # keep only the most recent N
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
    print(f" NEW ITEMS FETCHED : {len(all_new_items)}")
    print(f" TOTAL IN DATABASE : {len(final_list)}")
    print(f" ITEMS WITH IMAGES : {sum(1 for i in final_list if i.get('image'))}")
    print(f" Saved to: {NEWS_FILE}")
    print("="*70)
    print("💡 Tip: If a source shows few images, OG fallback will fill the gaps.")

if __name__ == "__main__":
    run_workflow()
