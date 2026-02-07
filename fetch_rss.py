#!/usr/bin/env python3
"""
The Streamic – RSS Feed Aggregator (V3.2)
- Stronger image extraction (media:content, media:thumbnail, content:encoded)
- Cleaned/verified feed list for Infrastructure, Graphics, Streaming, etc.
"""

import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import re
from html import unescape
from datetime import datetime
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"

# --------------------------------------------------------------------------------------
# CATEGORY RSS FEEDS  (verified high-signal sources)
# --------------------------------------------------------------------------------------
FEED_SOURCES = {
    # NEWSROOM – keep broad industry news if you use a newsroom page
    "newsroom": [
        {"url": "https://www.newscaststudio.com/category/industry-feed/feed/", "label": "NewscastStudio Industry"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "BroadcastBeat"},
        # Optional: TVTechnology site-wide feed (works on most Future sites; comment out if 404)
        {"url": "https://www.tvtechnology.com/.rss", "label": "TV Technology"},
    ],

    # PLAYOUT – vendor/platform updates
    "playout": [
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://www.harmonicinc.com/insights/blog/rss.xml", "label": "Harmonic"},
        {"url": "https://www.bitmovin.com/feed/", "label": "Bitmovin"},
        {"url": "https://www.wowza.com/blog/feed", "label": "Wowza"},
    ],

    # INFRASTRUCTURE – broadcast engineering, IP networking (ST 2110/NDI), plus security
    "infrastructure": [
        # Broadcast engineering (images in RSS)
        {"url": "https://www.newscaststudio.com/category/broadcast-engineering/feed/", "label": "NewscastStudio Broadcast Engineering"},  # [1](https://www.newscaststudio.com/category/broadcast-engineering/)
        {"url": "https://www.broadcastbeat.com/feed/", "label": "BroadcastBeat"},  # [2](https://rss.feedspot.com/live_streaming_rss_feeds/)
        # IP networking / vendor news
        {"url": "https://newsroom.cisco.com/c/r/newsroom/en/us/rss-feeds.html?rss=Enterprise%20Networking", "label": "Cisco – Enterprise Networking"},  # [3](https://newsroom.cisco.com/rss-feeds)
        {"url": "https://newsroom.cisco.com/c/r/newsroom/en/us/rss-feeds.html?rss=Security", "label": "Cisco – Security"},  # [3](https://newsroom.cisco.com/rss-feeds)
        {"url": "https://www.haivision.com/blog/feed/", "label": "Haivision Blog"},  # [4](https://www.haivision.com/blog/)
        # Security publications relevant to infra uptime
        {"url": "https://www.darkreading.com/rss.xml", "label": "Dark Reading"},  # [5](https://engineering.einnews.com/all_rss)
        {"url": "https://www.csoonline.com/feed", "label": "CSO Online"},  # [5](https://engineering.einnews.com/all_rss)
    ],

    # GRAPHICS – broadcast graphics, motion design, vendors (these feeds expose images)
    "graphics": [
        {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio Graphics"},  # [6](https://www.newscaststudio.com/)
        {"url": "https://motionographer.com/feed/", "label": "Motionographer"},
        {"url": "https://www.creativebloq.com/feed", "label": "Creative Bloq"},
        {"url": "https://cgchannel.com/feed/", "label": "CG Channel"},
        {"url": "https://blog.adobe.com/en/feed", "label": "Adobe Blog"},
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://chyron.com/feed/", "label": "Chyron"},
    ],

    # CLOUD – vendor media blogs that publish images in RSS
    "cloud": [
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media & Entertainment"},
        {"url": "https://azure.microsoft.com/en-us/blog/feed/", "label": "Azure Blog"},
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://www.telestream.net/company/press/rss.xml", "label": "Telestream"},
    ],

    # STREAMING – StreamingMedia.com family (explicitly offers public RSS) 
    "streaming": [
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews", "label": "Streaming Media News"},       # [7](http://www.shook-usa.com/News_and_Information/Broadcast_News_Feed.html)
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedArticles", "label": "Streaming Media Articles"}, # [7](http://www.shook-usa.com/News_and_Information/Broadcast_News_Feed.html)
        {"url": "http://feeds.infotoday.com/Streaming-Media-Blog", "label": "Streaming Media Blog"},                      # [7](http://www.shook-usa.com/News_and_Information/Broadcast_News_Feed.html)
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-IndustryNews", "label": "Streaming Media Industry"},   # [7](http://www.shook-usa.com/News_and_Information/Broadcast_News_Feed.html)
        {"url": "https://streamingmediablog.com/feed", "label": "Dan Rayburn Blog"},
    ],

    # AUDIO & AI – audio transport (Dante) + pro audio vendors
    "audio-ai": [
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},
        {"url": "https://www.audinate.com/feed", "label": "Audinate (Dante)"},
        {"url": "https://www.avid.com/blog/rss.xml", "label": "Avid"},
        {"url": "https://www.waves.com/news-and-events/rss", "label": "Waves Audio"},
    ],
}

# --------------------------------------------------------------------------------------
# IMAGE EXTRACTION
# --------------------------------------------------------------------------------------
NS = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}

def get_best_image(item):
    # media:content
    mc = item.find('media:content', NS)
    if mc is not None:
        u = mc.get('url')
        if is_valid_image_url(u): return clean_url(u)

    # media:thumbnail
    mt = item.find('media:thumbnail', NS)
    if mt is not None:
        u = mt.get('url')
        if is_valid_image_url(u): return clean_url(u)

    # enclosure type="image/*"
    enc = item.find('enclosure')
    if enc is not None:
        et = (enc.get('type') or '').lower()
        if 'image' in et:
            u = enc.get('url')
            if is_valid_image_url(u): return clean_url(u)

    # content:encoded (HTML)
    ce = item.find('content:encoded', NS)
    if ce is not None and ce.text:
        u = extract_image_from_html(ce.text)
        if u: return clean_url(u)

    # description (HTML)
    desc = item.findtext('description') or ""
    if desc:
        u = extract_image_from_html(desc)
        if u: return clean_url(u)

    return ""

def extract_image_from_html(html):
    if not html:
        return None
    # first <img src="...">
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m and is_valid_image_url(m.group(1)):
        return m.group(1)
    # background-image:url(...)
    m = re.search(r'background-image\s*:\s*url\(["\']?([^"\')\s]+)', html, re.IGNORECASE)
    if m and is_valid_image_url(m.group(1)):
        return m.group(1)
    return None

def is_valid_image_url(url):
    if not url or len(url) < 8:
        return False
    ul = url.lower()
    for bad in ['1x1', 'pixel', 'spacer', 'blank', 'placeholder', 'default', 'avatar', 'gravatar', 'data:image', 'base64']:
        if bad in ul:
            return False
    # accept if looks like an image path (with params allowed)
    return re.search(r'\.(jpg|jpeg|png|gif|webp|svg)(\?|#|$)', ul) is not None

def clean_url(url):
    if not url:
        return ""
    url = unescape(url).strip()
    if url.startswith('//'):
        url = 'https:' + url
    return url

# --------------------------------------------------------------------------------------
# FETCHING / AGGREGATION
# --------------------------------------------------------------------------------------
def fetch_feed(url, timeout=20):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rss+xml, application/xml, text/xml, */*"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f" ✗ {url} -> {e}")
        return None

def run():
    print("="*70)
    print(" THE STREAMIC - RSS FEED AGGREGATOR (V3.2)")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_news = []
    stats = {}

    for category, sources in FEED_SOURCES.items():
        print(f"\n📂 {category.upper().replace('-', ' & ')}")
        print("-"*70)
        count = 0

        for src in sources:
            label = src["label"]
            url = src["url"]
            print(f" Fetching: {label:40s}", end="", flush=True)

            xml_bytes = fetch_feed(url)
            if not xml_bytes:
                print(" ✗")
                continue

            try:
                root = ET.fromstring(xml_bytes)
                items = root.findall('.//item')
                if not items:
                    print(" ✗ No items")
                    continue

                print(f" ✓ {len(items)} items")
                for it in items:
                    guid = it.findtext('guid') or it.findtext('link') or ""
                    if not guid:
                        continue

                    title = unescape((it.findtext('title') or "Untitled")).strip()
                    link = (it.findtext('link') or "").strip()
                    image = get_best_image(it)

                    all_news.append({
                        "guid": guid,
                        "title": title,
                        "link": link,
                        "source": label,
                        "category": category,
                        "image": image,
                        "timestamp": datetime.now().isoformat()
                    })
                    count += 1

            except ET.ParseError:
                print(" ✗ XML parse error")
            except Exception as e:
                print(f" ✗ {str(e)[:50]}")

        stats[category] = count

    # De-duplicate by GUID
    unique = list({n["guid"]: n for n in all_news if n.get("guid")}.values())

    DATA_DIR.mkdir(exist_ok=True)
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    for cat in FEED_SOURCES.keys():
        c = stats.get(cat, 0)
        status = "✓" if c > 0 else "✗"
        print(f" {status} {cat.upper().replace('-', ' & '):20s} : {c:3d} items")
    print("-"*70)
    print(f" TOTAL UNIQUE ITEMS: {len(unique)}")
    print(f" Saved to: {NEWS_FILE}")
    print("="*70)

if __name__ == "__main__":
    run()
