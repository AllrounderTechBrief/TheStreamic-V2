#!/usr/bin/env python3
"""
The Streamic - RSS Aggregator V8 (Balanced Version)
Ensures ALL categories (including streaming & audio-ai) always appear.
"""
import json, time, urllib.request, urllib.error, xml.etree.ElementTree as ET
from html import unescape, parser as HTMLParser_module
from datetime import datetime
from pathlib import Path
import re
from collections import defaultdict

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

DATA_DIR = Path("data")
NEWS_FILE = Path("data/news.json")

# ⭐⭐ Increase total capacity
MAX_NEWS_ITEMS = 300

# ⭐⭐ FEEDS (unchanged)
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
        {"url": "https://www.tvtechnology.com/platform/streaming/rss.xml", "label": "TV Tech Streaming"},
        {"url": "https://www.tvtechnology.com/business/rss.xml", "label": "TV Tech Business"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"},
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
        {"url": "https://www.inbroadcast.com/rss.xml", "label": "InBroadcast"},
    ],
    "audio-ai": [
        {"url": "https://www.tvtechnology.com/production/rss.xml", "label": "TV Tech Production"},
        {"url": "https://www.broadcastbeat.com/feed/", "label": "Broadcast Beat"},
        {"url": "https://www.newscaststudio.com/tag/audio/feed/", "label": "NewscastStudio Audio"},
        {"url": "https://www.svgeurope.org/feed/", "label": "SVG Europe"},
        {"url": "https://aws.amazon.com/blogs/media/feed/", "label": "AWS Media"},
    ]
}

# ========= IMAGE SCRAPER ==========
class ImageScraper(HTMLParser_module.HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_url = None
    def handle_starttag(self, tag, attrs):
        if tag == "img" and not self.image_url:
            for a, v in attrs:
                if a == "src" and v and any(ext in v.lower() for ext in [".jpg",".jpeg",".png",".gif",".webp"]):
                    self.image_url = v

# ========= GET IMAGE =============
def get_best_image(item_xml):
    candidates = []
    media_ns = "{http://search.yahoo.com/mrss/}"

    # <media:content> & <media:thumbnail>
    for elem in [item_xml.find(f"{media_ns}content"), item_xml.find(f"{media_ns}thumbnail")]:
        if elem is not None and elem.get("url"):
            candidates.append(elem.get("url"))

    # enclosure
    enc = item_xml.find("enclosure")
    if enc is not None and "image" in enc.get("type","") and enc.get("url"):
        candidates.append(enc.get("url"))

    # description scraping
    for t in ["description", "{http://purl.org/rss/1.0/modules/content/}encoded"]:
        elem = item_xml.find(t)
        if elem is not None and elem.text:
            parser = ImageScraper()
            try: parser.feed(elem.text)
            except: pass
            if parser.image_url: 
                candidates.append(parser.image_url)

    # final filtering
    for url in candidates:
        if not url: continue
        u = url.strip()
        if u.startswith("//"): u = "https:" + u
        if u.startswith("http") and any(ext in u.lower() for ext in [".jpg",".jpeg",".png",".gif",".webp"]):
            return u
    return ""

# ========= FETCH URL ============
def fetch_url(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except:
        return None

# ========= PARSE FEED ============
def parse_rss_feed(xml_data, category, source_label):
    items = []
    try:
        root = ET.fromstring(xml_data)
        for x in root.findall(".//item"):
            title_elem = x.find("title")
            link_elem = x.find("link")
            guid_elem = x.find("guid")

            items.append({
                "guid": guid_elem.text if guid_elem is not None and guid_elem.text else (link_elem.text if link_elem is not None else ""),
                "title": unescape(title_elem.text).strip() if title_elem is not None and title_elem.text else "Untitled",
                "link": link_elem.text.strip() if link_elem is not None and link_elem.text else "#",
                "category": category,
                "image": get_best_image(x),
                "source": source_label,
                "timestamp": datetime.now().isoformat()
            })
        return items
    except:
        return []

# ========= CATEGORY BALANCER ============
def balance_by_category(items, max_total=300, min_per_cat=15):
    by_cat = defaultdict(list)

    # group
    for it in items:
        by_cat[it.get("category","").lower()].append(it)

    # newest first per category
    for c in by_cat:
        by_cat[c].sort(key=lambda x: x.get("timestamp",""), reverse=True)

    picked = []

    # guarantee baseline
    for c, arr in by_cat.items():
        picked.extend(arr[:min_per_cat])

    # fill remaining globally
    remaining = []
    for c, arr in by_cat.items():
        remaining.extend(arr[min_per_cat:])
    remaining.sort(key=lambda x: x.get("timestamp",""), reverse=True)

    remaining_slots = max_total - len(picked)
    if remaining_slots > 0:
        picked.extend(remaining[:remaining_slots])

    # dedupe final
    seen = set()
    final = []
    for it in picked:
        gid = it.get("guid")
        if gid and gid not in seen:
            seen.add(gid)
            final.append(it)

    return final[:max_total]

# ========= MAIN WORKFLOW ============
def run_workflow():
    print("="*70)
    print(" THE STREAMIC — BALANCED FEEDS MODE")
    print("="*70)

    DATA_DIR.mkdir(exist_ok=True)

    all_items = []

    for category, feeds in FEED_SOURCES.items():
        print(f"\n▶ {category.upper()}\n" + "-"*70)

        for fd in feeds:
            print(f"{fd['label']:40s}", end="")
            xml = fetch_url(fd["url"])
            if xml:
                items = parse_rss_feed(xml, category, fd["label"])
                print(f" ✓ {len(items)} items")
                all_items.extend(items)
            else:
                print(" ✗ failed")
            time.sleep(0.2)

    # Load existing
    existing = []
    if NEWS_FILE.exists():
        try:
            existing = json.load(open(NEWS_FILE, "r", encoding="utf-8"))
        except:
            existing = []

    # Merge, sort newest
    merged = all_items + existing
    merged.sort(key=lambda x: x.get("timestamp",""), reverse=True)

    # Balance categories
    final_list = balance_by_category(merged, max_total=MAX_NEWS_ITEMS, min_per_cat=15)

    # Save
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=2, ensure_ascii=False)

    print("\nSaved balanced news.json with", len(final_list), "items")
    print("="*70)

if __name__ == "__main__":
    run_workflow()
