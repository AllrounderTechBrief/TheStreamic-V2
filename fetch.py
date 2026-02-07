#!/usr/bin/env python3
"""
The Streamic - Complete RSS Aggregator (V7.3)
- FIX for streaming & audio-ai categories:
  * Unescape HTML before parsing <img>
  * OpenGraph (og:image/twitter:image) fallback for stubborn feeds
  * Clearer logging to spot zero-item feeds
"""
import json, time, urllib.request, urllib.error, xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
import re

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"
MAX_NEWS_ITEMS = 180

FEED_SOURCES = {
    "newsroom": [
        {"url": "https://www.newscaststudio.com/feed/", "label": "NewscastStudio (All)"},
        {"url": "https://www.tvnewscheck.com/rss/", "label": "TVNewsCheck"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "BroadcastBeat"}
    ],
    "playout": [
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://www.harmonicinc.com/insights/blog/rss.xml", "label": "Harmonic"}
    ],
    "infrastructure": [
        {"url": "https://www.newscaststudio.com/category/broadcast-engineering/feed/", "label": "NewscastStudio Engineering"},
        {"url": "https://www.thebroadcastbridge.com/rss/all", "label": "Broadcast Bridge"},
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"}
    ],
    "graphics": [
        {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio Graphics"},
        {"url": "https://motionographer.com/feed/", "label": "Motionographer"}
    ],
    "cloud": [
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media Blog"},                # AWS Media RSS [2](https://www.zdnet.com/rssfeeds/)
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"}, # GCP Media M&E RSS [2](https://www.zdnet.com/rssfeeds/)
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://azure.microsoft.com/en-us/blog/feed/", "label": "Azure Blog"}                 # Azure blog RSS [2](https://www.zdnet.com/rssfeeds/)
    ],
    "streaming": [
        # StreamingMedia — Official public feeds
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews",      "label": "Streaming Media News"},       # [1](https://rss.feedspot.com/live_streaming_rss_feeds/)
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedArticles",  "label": "Streaming Media Articles"},   # [1](https://rss.feedspot.com/live_streaming_rss_feeds/)
        {"url": "http://feeds.infotoday.com/Streaming-Media-Blog",                     "label": "Streaming Media Blog"},       # [1](https://rss.feedspot.com/live_streaming_rss_feeds/)
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-IndustryNews",      "label": "Streaming Media Industry"},   # [1](https://rss.feedspot.com/live_streaming_rss_feeds/)

        {"url": "https://www.telestream.net/company/press/rss.xml", "label": "Telestream"},                                  # [3](https://www.techrepublic.com/rssfeeds/)
        {"url": "https://ottverse.com/feed/", "label": "OTTVerse"},                                                          # [4](https://www.ottnews.online/)
        {"url": "https://blog.blazingcdn.com/en-us/feed/", "label": "BlazingCDN"},                                           # [5](https://economictimes.indiatimes.com/topic/ott-streaming-industry)
        {"url": "https://vodlix.com/feed/", "label": "Vodlix"},                                                               # [6](https://www.streamingmedia.com/)
        {"url": "https://streamingmediablog.com/feed", "label": "Dan Rayburn"},
        {"url": "https://www.globallogic.com/feed/", "label": "GlobalLogic OTT"}                                             # [7](https://www.lifetechnology.com/pages/copyright-and-royalty-free-rss-feeds-for-commercial-and-non-commercial-use)
    ],
    "audio-ai": [
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},                                                        # [3](https://www.techrepublic.com/rssfeeds/)
        {"url": "https://www.radioworld.com/rss.xml", "label": "Radio World"},
        {"url": "https://www.waves.com/news-and-events/rss", "label": "Waves Audio"},                                        # [3](https://www.techrepublic.com/rssfeeds/)
        {"url": "https://www.production-expert.com/production-expert-1?format=rss", "label": "Production Expert"},          # [8](https://rss.techtarget.com/)
        {"url": "https://www.avid.com/blog/rss.xml", "label": "Avid / Pro Tools"},                                           # [3](https://www.techrepublic.com/rssfeeds/)
        {"url": "https://www.audinate.com/feed", "label": "Audinate – Dante"},                                               # [9](https://ottverse.com/)
        {"url": "https://www.merging.com/rss.xml", "label": "Merging – Ravenna/AES67"},
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},                                           # [2](https://www.zdnet.com/rssfeeds/)
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"}             # [2](https://www.zdnet.com/rssfeeds/)
    ]
}

# ----------------- HTML parsing helpers -----------------
class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None
    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.image_url:
            for k, v in attrs:
                if k == 'src' and v:
                    self.image_url = v

def _is_img_url(u: str) -> bool:
    if not u or len(u) < 8: return False
    ul = u.lower()
    for bad in ('1x1','pixel','spacer','blank','placeholder','default','avatar','gravatar','data:image','base64'):
        if bad in ul: return False
    if re.search(r'\.(jpg|jpeg|png|gif|webp|svg)(\?|#|$)', ul): return True
    for hint in ('wp-content/uploads','/images/','/img/','/media/','cloudinary','unsplash','cdn.','amazonaws'):
        if hint in ul: return True
    return False

def _clean(u: str) -> str:
    u = unescape(u or '').strip()
    if u.startswith('//'): u = 'https:' + u
    return u

def _extract_from_markup(markup: str) -> str:
    if not markup: return ""
    html = unescape(markup)

    # HTMLParser
    p = ImgParser()
    try:
        p.feed(html)
        if _is_img_url(p.image_url): return _clean(p.image_url)
    except Exception:
        pass

    # Regex <img ... src="...">
    m = re.search(r'<img[^"\']+["\']', html, re.IGNORECASE)
    if m and _is_img_url(m.group(1)): return _clean(m.group(1))

    # background-image:url(...)
    m = re.search(r'background-image\s*:\s*url\(["\']?([^"\')\s]+)', html, re.IGNORECASE)
    if m and _is_img_url(m.group(1)): return _clean(m.group(1))

    return ""

def _fetch(url: str, timeout=20) -> bytes | None:
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': USER_AGENT, 'Accept': 'application/rss+xml, application/xml, text/xml, */*'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"    ERR {str(e)[:60]}")
        return None

def _fetch_page(url: str, timeout=8) -> str:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,*/*'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception:
        return ""

def _fetch_og_image(article_url: str) -> str:
    """Fetch og:image/twitter:image for whitelisted domains (last resort)."""
    if not article_url: return ""
    wl = (
        "streamingmedia.com","telestream.net","ottverse.com","blazingcdn.com","vodlix.com",
        "globallogic.com","streamingmediablog.com",
        "redtech.pro","radioworld.com","waves.com","production-expert.com","avid.com",
        "audinate.com","merging.com","aws.amazon.com","cloud.google.com"
    )
    if not any(h in article_url.lower() for h in wl): return ""
    html = _fetch_page(article_url)
    if not html: return ""
    # try og:image then twitter:image
    for pat in (r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']'):
        m = re.search(pat, html, re.IGNORECASE)
        if m and _is_img_url(m.group(1)):
            return _clean(m.group(1))
    return ""

def get_best_image(item_xml) -> str:
    candidates = []

    # media:content / media:thumbnail
    mns = '{http://search.yahoo.com/mrss/}'
    for node in (item_xml.find(f'{mns}content'), item_xml.find(f'{mns}thumbnail')):
        if node is not None and node.get('url'):
            candidates.append(node.get('url'))

    # enclosure type=image/*
    enc = item_xml.find('enclosure')
    if enc is not None and 'image' in (enc.get('type') or '').lower() and enc.get('url'):
        candidates.append(enc.get('url'))

    # description
    desc = item_xml.find('description')
    if desc is not None and desc.text:
        u = _extract_from_markup(desc.text)
        if u: candidates.append(u)

    # content:encoded
    cns = '{http://purl.org/rss/1.0/modules/content/}'
    ce = item_xml.find(f'{cns}encoded')
    if ce is not None and ce.text:
        u = _extract_from_markup(ce.text)
        if u: candidates.append(u)

    # scan text/attribs for direct image URLs
    for elem in item_xml.iter():
        if elem.text:
            for u in re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', unescape(elem.text), re.I):
                candidates.append(u)
        for val in elem.attrib.values():
            for u in re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', unescape(str(val)), re.I):
                candidates.append(u)

    for u in candidates:
        u = _clean(u)
        if _is_img_url(u):
            return u

    # OpenGraph fallback
    link = (item_xml.findtext('link') or '').strip()
    og = _fetch_og_image(link)
    if og: return og

    return ""

def parse_rss_feed(xml_data: bytes, category: str, source_label: str):
    try:
        root = ET.fromstring(xml_data)
        items = []
        for it in root.findall('.//item'):
            title = unescape((it.findtext('title') or 'Untitled')).strip()
            link  = (it.findtext('link') or '#').strip()
            guid  = (it.findtext('guid') or link).strip()
            img   = get_best_image(it)

            items.append({
                "guid": guid, "title": title, "link": link,
                "category": category, "image": img, "source": source_label,
                "timestamp": datetime.now().isoformat()
            })
        return items
    except ET.ParseError:
        return []
    except Exception:
        return []

def run_workflow():
    print("="*70)
    print(" THE STREAMIC - Complete Aggregator (V7.3)")
    print(" Fixes for STREAMING and AUDIO-AI categories")
    print("="*70)

    DATA_DIR.mkdir(exist_ok=True)
    all_new, stats = [], {}

    for category, feeds in FEED_SOURCES.items():
        print(f"\n📂 {category.upper()}")
        print("-"*70)
        c_total = c_imgs = 0

        for f in feeds:
            print(f"  {f['label']:<36}", end="")
            xml = _fetch(f['url'])
            if not xml:
                print(" ✗ fetch failed")
                continue
            items = parse_rss_feed(xml, category, f['label'])
            imgs  = sum(1 for x in items if x.get('image'))
            c_total += len(items); c_imgs += imgs
            all_new.extend(items)
            print(f" ✓ {len(items):3d} items ({imgs:3d} imgs)")
            time.sleep(0.25)

        stats[category] = (c_total, c_imgs)

    # Merge with existing and de-duplicate by GUID (keep newest first)
    existing = []
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except Exception:
            pass

    combined = all_new + existing
    seen, final = set(), []
    for it in combined:
        g = it.get('guid')
        if g and g not in seen:
            seen.add(g); final.append(it)

    final = final[:MAX_NEWS_ITEMS]
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    for cat in FEED_SOURCES:
        tot, img = stats.get(cat, (0,0))
        pct = (img/tot*100) if tot else 0
        print(f" {'✓' if tot else '✗'} {cat.upper():20s} : {tot:3d} items, {img:3d} imgs ({pct:.0f}%)")
    print("-"*70)
    print(f" NEW ITEMS       : {len(all_new)}")
    print(f" TOTAL IN DB     : {len(final)}")
    print(f" ITEMS w/ IMAGES : {sum(1 for x in final if x.get('image'))}")
    print(f" Saved to        : {NEWS_FILE}")
    print("="*70)

if __name__ == "__main__":
    run_workflow()
