#!/usr/bin/env python3
"""
The Streamic – RSS Feed Aggregator (V4.1)
- Robust image extraction (media:content, media:thumbnail, enclosure, content:encoded, description)
- Accepts image URLs with query strings (?w=800&q=80)
- OpenGraph (og:image / twitter:image) fallback for stubborn feeds
- Clean, reliable feed set for each category
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

# -----------------------------
# CATEGORY RSS FEEDS
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
        {"url": "https://www.bitmovin.com/feed/", "label": "Bitmovin"},
        {"url": "https://www.wowza.com/blog/feed", "label": "Wowza"},
    ],
    "infrastructure": [
        {"url": "https://www.newscaststudio.com/category/broadcast-engineering/feed/", "label": "NewscastStudio Broadcast Engineering"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "BroadcastBeat"},
        {"url": "https://www.haivision.com/blog/feed/", "label": "Haivision Blog"},
        {"url": "https://www.darkreading.com/rss.xml", "label": "Dark Reading"},
        {"url": "https://www.csoonline.com/feed", "label": "CSO Online"},
    ],
    "graphics": [
        {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio Graphics"},
        {"url": "https://motionographer.com/feed/", "label": "Motionographer"},
        {"url": "https://www.creativebloq.com/feed", "label": "Creative Bloq"},
        {"url": "https://cgchannel.com/feed/", "label": "CG Channel"},
        {"url": "https://blog.adobe.com/en/feed", "label": "Adobe Blog"},
        {"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"},
        {"url": "https://chyron.com/feed/", "label": "Chyron"},
    ],
    "cloud": [
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
        {"url": "https://cloud.google.com/blog/products/media-entertainment/rss", "label": "Google Cloud Media & Entertainment"},
        {"url": "https://azure.microsoft.com/en-us/blog/feed/", "label": "Azure Blog"},
        {"url": "https://blog.frame.io/feed/", "label": "Frame.io"},
        {"url": "https://www.telestream.net/company/press/rss.xml", "label": "Telestream"},
    ],
    "streaming": [
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedNews", "label": "Streaming Media News"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-FeaturedArticles", "label": "Streaming Media Articles"},
        {"url": "http://feeds.infotoday.com/Streaming-Media-Blog", "label": "Streaming Media Blog"},
        {"url": "http://feeds.infotoday.com/StreamingMediaMagazine-IndustryNews", "label": "Streaming Media Industry"},
        {"url": "https://streamingmediablog.com/feed", "label": "Dan Rayburn Blog"},
    ],
    "audio-ai": [
        {"url": "https://www.redtech.pro/feed/", "label": "RedTech"},
        {"url": "https://www.audinate.com/feed", "label": "Audinate (Dante)"},
        {"url": "https://www.avid.com/blog/rss.xml", "label": "Avid"},
        {"url": "https://www.waves.com/news-and-events/rss", "label": "Waves Audio"},
    ],
}

# -----------------------------
# XML namespaces
# -----------------------------
NS = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


# -----------------------------
# Image extraction helpers
# -----------------------------
def get_best_image(item):
    """Try multiple strategies to find a real image URL."""
    # 1) media:content
    node = item.find("media:content", NS)
    if node is not None:
        u = node.get("url")
        if is_valid_image_url(u):
            return clean_url(u)

    # 2) media:thumbnail
    node = item.find("media:thumbnail", NS)
    if node is not None:
        u = node.get("url")
        if is_valid_image_url(u):
            return clean_url(u)

    # 3) enclosure type=image/*
    enc = item.find("enclosure")
    if enc is not None:
        et = (enc.get("type") or "").lower()
        if "image" in et:
            u = enc.get("url")
            if is_valid_image_url(u):
                return clean_url(u)

    # 4) content:encoded (HTML)
    ce = item.find("content:encoded", NS)
    if ce is not None and ce.text:
        u = extract_image_from_html(ce.text)
        if u:
            return clean_url(u)

    # 5) description (HTML)
    desc = item.findtext("description") or ""
    if desc:
        u = extract_image_from_html(desc)
        if u:
            return clean_url(u)

    # 6) OpenGraph fallback (as last resort)
    link = item.findtext("link") or ""
    og = fetch_og_image(link)
    if og:
        return clean_url(og)

    return ""


def extract_image_from_html(html):
    """Extract first valid image URL from HTML."""
    if not html:
        return None

    # <img ... src="...">
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m and is_valid_image_url(m.group(1)):
        return m.group(1)

    # background-image:url(...)
    m = re.search(r'background-image\s*:\s*url\(["\']?([^"\')\s]+)', html, re.IGNORECASE)
    if m and is_valid_image_url(m.group(1)):
        return m.group(1)

    return None


def is_valid_image_url(url):
    """Accepts images with query strings and common CDNs."""
    if not url or len(url) < 8:
        return False
    ul = url.lower()

    # Reject obvious placeholders/pixels
    for bad in ('1x1', 'pixel', 'spacer', 'blank', 'placeholder', 'default', 'avatar', 'gravatar', 'data:image', 'base64'):
        if bad in ul:
            return False

    # Accept real image extensions (with ? or # allowed)
    if re.search(r'\.(jpg|jpeg|png|gif|webp|svg)(\?|#|$)', ul):
        return True

    # Accept common image path patterns (rare cases without explicit extension)
    for hint in ('wp-content/uploads', '/images/', '/img/', '/media/', 'cloudinary', 'unsplash', 'cdn.', 'amazonaws'):
        if hint in ul:
            return True

    return False


def clean_url(url):
    if not url:
        return ""
    url = unescape(url).strip()
    if url.startswith("//"):
        url = "https:" + url
    return url


def fetch_og_image(article_url, timeout=7):
    """
    Fetch og:image / twitter:image from the article page.
    Whitelist domains to keep it fast and friendly.
    """
    if not article_url:
        return ""

    whitelist = (
        "streamingmedia.com",
        "newscaststudio.com",
        "broadcastbeat.com",
        "tvnewscheck.com",
        "creativebloq.com",
        "motionographer.com",
        "cgchannel.com",
        "haivision.com",
    )
    if not any(h in article_url.lower() for h in whitelist):
        return ""

    try:
        req = urllib.request.Request(
            article_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

    for pat in (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ):
        m = re.search(pat, html, re.IGNORECASE)
        if m and is_valid_image_url(m.group(1)):
            return m.group(1)

    return ""


# -----------------------------
# RSS fetching / aggregation
# -----------------------------
def fetch_feed(url, timeout=20):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f" ✗ {url} -> {e}")
        return None


def run():
    print("=" * 70)
    print(" THE STREAMIC – RSS AGGREGATOR (V4.1)")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_news = []
    stats = {}

    for category, sources in FEED_SOURCES.items():
        print(f"\n📂 {category.upper().replace('-', ' & ')}")
        print("-" * 70)
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
                items = root.findall(".//item")
                if not items:
                    print(" ✗ No items")
                    continue

                images_found = 0
                for it in items:
                    guid = it.findtext("guid") or it.findtext("link") or ""
                    if not guid:
                        continue

                    title = unescape((it.findtext("title") or "Untitled")).strip()
                    link = (it.findtext("link") or "").strip()
                    image = get_best_image(it)
                    if image:
                        images_found += 1

                    all_news.append(
                        {
                            "guid": guid,
                            "title": title,
                            "link": link,
                            "source": label,
                            "category": category,
                            "image": image,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    count += 1

                print(f" ✓ {len(items)} items ({images_found} with images)")

            except ET.ParseError:
                print(" ✗ XML parse error")
            except Exception as e:
                print(f" ✗ {str(e)[:50]}")

        stats[category] = count

    # de-duplicate by GUID
    unique = list({n["guid"]: n for n in all_news if n.get("guid")}.values())

    DATA_DIR.mkdir(exist_ok=True)
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(" SUMMARY")
    print("=" * 70)
    for cat in FEED_SOURCES.keys():
        c = stats.get(cat, 0)
        status = "✓" if c > 0 else "✗"
        print(f" {status} {cat.upper().replace('-', ' & '):20s} : {c:3d} items")
    print("-" * 70)
    print(f" TOTAL UNIQUE ITEMS: {len(unique)}")
    print(f" ITEMS WITH IMAGES: {sum(1 for n in unique if n.get('image'))}")
    print(f" Saved to: {NEWS_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    run()
