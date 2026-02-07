#!/usr/bin/env python3
"""
The Streamic - Complete RSS Aggregator (V7.5)
- Streaming & Audio-AI robust:
  * RSS + Atom parsing
  * Unescape HTML before scanning for <img> / background-image
  * OpenGraph (og:image/twitter:image) fallback
  * Reject common placeholder/spinner images
  * Clear per-category summary
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

# -----------------------------
# Config
# -----------------------------
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"
MAX_NEWS_ITEMS = 180

# -----------------------------
# Feeds
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
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media Blog"},
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://azure.microsoft.com/en-us/blog/feed/", "label": "Azure Blog"},
    ],
    "streaming": [
        # StreamingMedia — Official public feeds
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews",     "label": "Streaming Media News"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedArticles", "label": "Streaming Media Articles"},
        {"url": "http://feeds.infotoday.com/Streaming-Media-Blog",                    "label": "Streaming Media Blog"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-IndustryNews",     "label": "Streaming Media Industry"},

        # Encoding / Transcoding / QC
        {"url": "https://www.telestream.net/company/press/rss.xml", "label": "Telestream"},

        # OTT Engineering
        {"url": "https://ottverse.com/feed/", "label": "OTTVerse"},

        # CDN / Delivery
        {"url": "https://blog.blazingcdn.com/en-us/feed/", "label": "BlazingCDN"},

        # OTT Platforms / Infra
        {"url": "https://vodlix.com/feed/", "label": "Vodlix"},

        # Streaming industry blog
        {"url": "https://streamingmediablog.com/feed", "label": "Dan Rayburn"},

        # Enterprise OTT architecture
        {"url": "https://www.globallogic.com/feed/", "label": "GlobalLogic OTT"},
    ],
    "audio-ai": [
        # Broadcast/Pro Audio
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},
        {"url": "https://www.radioworld.com/rss.xml", "label": "Radio World"},
        {"url": "https://www.waves.com/news-and-events/rss", "label": "Waves Audio"},
        {"url": "https://www.production-expert.com/production-expert-1?format=rss", "label": "Production Expert"},
        {"url": "https://www.avid.com/blog/rss.xml", "label": "Avid / Pro Tools"},

        # AoIP – Dante, AES67, Ravenna
        {"url": "https://www.audinate.com/feed", "label": "Audinate – Dante"},
        {"url": "https://www.merging.com/rss.xml", "label": "Merging – Ravenna/AES67"},

        # Cloud media (audio workflows overlap)
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media"},
    ],
}

# -----------------------------
# HTML helpers
# -----------------------------
class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and self.image_url is None:
            for k, v in attrs:
                if k == 'src' and v:
                    self.image_url = v

def _is_img_url(u):
    if not u or len(u) < 8:
        return False
    ul = u.lower()

    # reject obvious placeholders/pixels/spinners
    reject = (
        '1x1', 'pixel', 'spacer', 'blank', 'placeholder', 'default',
        'avatar', 'gravatar', 'data:image', 'base64', 'spinner.svg'
    )
    if any(b in ul for b in reject):
        return False

    # valid image ext (allow query/hash)
    if re.search(r'\.(jpg|jpeg|png|gif|webp|svg)(\?|#|$)', ul):
        return True

    # rare extensionless but image-like paths
    hints = ('wp-content/uploads', '/images/', '/img/', '/media/', 'cloudinary', 'unsplash', 'cdn.', 'amazonaws')
    if any(h in ul for h in hints):
        return True

    return False

def _clean(u):
    u = unescape(u or '').strip()
    if u.startswith('//'):
        u = 'https:' + u
    return u

def _extract_from_markup(markup):
    """Unescape markup then try HTMLParser + regex for <img> and background images."""
    if not markup:
        return ""
    html = unescape(markup)

    # 1) HTMLParser (first <img src=...>)
    p = ImgParser()
    try:
        p.feed(html)
        if _is_img_url(p.image_url):
            return _clean(p.image_url)
    except Exception:
        pass

    # 2) Regex: <img ... src="...">
    m = re.search(r'<img[^"\']+["\']', html, re.IGNORECASE)
    if m and _is_img_url(m.group(1)):
        return _clean(m.group(1))

    # 3) Regex: background-image:url(...)
    m = re.search(r'background-image\s*:\s*url\(["\']?([^"\')\s]+)', html, re.IGNORECASE)
    if m and _is_img_url(m.group(1)):
        return _clean(m.group(1))

    return ""

# -----------------------------
# Network helpers
# -----------------------------
def _fetch(url, timeout=20):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': USER_AGENT, 'Accept': 'application/rss+xml, application/xml, text/xml, */*'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"    ERR fetch: {str(e)[:60]}")
        return None

def _fetch_page(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,*/*'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception:
        return ""

def _fetch_og_image(article_url):
    """Fetch og:image/twitter:image for whitelisted domains (last resort)."""
    if not article_url:
        return ""
    wl = (
        "streamingmedia.com", "telestream.net", "ottverse.com", "blazingcdn.com", "vodlix.com",
        "globallogic.com", "streamingmediablog.com",
        "redtech.pro", "radioworld.com", "waves.com", "production-expert.com", "avid.com",
        "audinate.com", "merging.com", "aws.amazon.com", "cloud.google.com"
    )
    if not any(h in article_url.lower() for h in wl):
        return ""

    html = _fetch_page(article_url)
    if not html:
        return ""

    # Try <meta property="og:image" content="..."> then twitter:image
    patterns = (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    )
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m and _is_img_url(m.group(1)):
            return _clean(m.group(1))
    return ""

# -----------------------------
# Image extraction from feed item (RSS/Atom)
# -----------------------------
def get_best_image(item_xml):
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

    # description (RSS)
    desc = item_xml.find('description')
    if desc is not None and desc.text:
        u = _extract_from_markup(desc.text)
        if u:
            candidates.append(u)

    # content:encoded (RSS/WordPress)
    cns = '{http://purl.org/rss/1.0/modules/content/}'
    ce = item_xml.find(f'{cns}encoded')
    if ce is not None and ce.text:
        u = _extract_from_markup(ce.text)
        if u:
            candidates.append(u)

    # Atom: content/summary
    atom = '{http://www.w3.org/2005/Atom}'
    for t in ('content', 'summary'):
        node = item_xml.find(f'{atom}{t}')
        if node is not None and (node.text or node.get('type') == 'html'):
            u = _extract_from_markup(node.text or '')
            if u:
                candidates.append(u)

    # scan text/attribs for direct image URLs
    for elem in item_xml.iter():
        if elem.text:
            for u in re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', unescape(elem.text), re.I):
                candidates.append(u)
        for val in elem.attrib.values():
            for u in re.findall(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|svg)[^\s<>"\']*)', unescape(str(val)), re.I):
                candidates.append(u)

    # return first good candidate
    for u in candidates:
        u = _clean(u)
        if _is_img_url(u):
            return u

    # OpenGraph fallback
    link = (item_xml.findtext('link') or '').strip()
    if not link:
        # Atom link element
        atom_link = item_xml.find(f'{atom}link')
        if atom_link is not None and atom_link.get('href'):
            link = atom_link.get('href').strip()

    og = _fetch_og_image(link)
    if og:
        return og

    return ""

# -----------------------------
# Parse feed (RSS + Atom)
# -----------------------------
def parse_rss_or_atom(xml_data, category, source_label):
    try:
        root = ET.fromstring(xml_data)
        items = []

        # Prefer RSS <item>, fallback to Atom <entry>
        nodes = root.findall('.//item')
        is_atom = False
        if not nodes:
            is_atom = True
            atom_ns = '{http://www.w3.org/2005/Atom}'
            nodes = root.findall(f'.//{atom_ns}entry')

        for it in nodes:
            if not is_atom:
                title = unescape((it.findtext('title') or 'Untitled')).strip()
                link = (it.findtext('link') or '#').strip()
                guid = (it.findtext('guid') or link).strip()
            else:
                atom_ns = '{http://www.w3.org/2005/Atom}'
                title = unescape((it.findtext(f'{atom_ns}title') or 'Untitled')).strip()
                link_el = it.find(f'{atom_ns}link')
                link = (link_el.get('href') if link_el is not None and link_el.get('href') else '#').strip()
                guid = (it.findtext(f'{atom_ns}id') or link).strip()

            img = get_best_image(it)

            items.append({
                "guid": guid,
                "title": title,
                "link": link,
                "category": category,
                "image": img,
                "source": source_label,
                "timestamp": datetime.now().isoformat()
            })

        return items
    except ET.ParseError:
        return []
    except Exception:
        return []

# -----------------------------
# Main workflow
# -----------------------------
def run_workflow():
    print("=" * 70)
    print(" THE STREAMIC - Complete Aggregator (V7.5)")
    print(" Streaming & Audio-AI: RSS+Atom, proper HTML/OG image extraction")
    print("=" * 70)

    DATA_DIR.mkdir(exist_ok=True)
    all_new = []
    stats = {}

    for category, feeds in FEED_SOURCES.items():
        print(f"\n📂 {category.upper()}")
        print("-" * 70)
        c_total = 0
        c_imgs = 0

        for f in feeds:
            print(f"  {f['label']:<36}", end="")
            xml = _fetch(f['url'])
            if not xml:
                print(" ✗ fetch failed")
                continue

            items = parse_rss_or_atom(xml, category, f['label'])
            imgs = sum(1 for x in items if x.get('image'))

            c_total += len(items)
            c_imgs += imgs
            all_new.extend(items)

            print(f" ✓ {len(items):3d} items ({imgs:3d} imgs)")
            time.sleep(0.2)

        stats[category] = (c_total, c_imgs)

    # Merge with existing and de-duplicate by GUID (keep newest first)
    existing = []
    if NEWS_FILE.exists():
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except Exception:
            existing = []

    combined = all_new + existing
    seen = set()
    final = []
    for it in combined:
        g = it.get('guid')
        if g and g not in seen:
            seen.add(g)
            final.append(it)

    final = final[:MAX_NEWS_ITEMS]

    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(" SUMMARY")
    print("=" * 70)
    for cat in FEED_SOURCES:
        tot, img = stats.get(cat, (0, 0))
        pct = (img / tot * 100) if tot else 0
        print(f" {'✓' if tot else '✗'} {cat.upper():20s} : {tot:3d} items, {img:3d} imgs ({pct:.0f}%)")
    print("-" * 70)
    print(f" NEW ITEMS       : {len(all_new)}")
    print(f" Saved to        : {NEWS_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    run_workflow()
