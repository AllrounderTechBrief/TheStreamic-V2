import json, time, urllib.request, xml.etree.ElementTree as ET
from html import unescape
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"

# Unified Category Slugs (Must match HTML data-category)
FEED_SOURCES = {
    "newsroom": [{"url": "https://www.dalet.com/feed/", "label": "Dalet"}, {"url": "https://www.avid.com/press-center/rss", "label": "Avid"}],
    "playout": [{"url": "https://www.rossvideo.com/news/feed/", "label": "Ross Video"}, {"url": "https://imaginecommunications.com/feed/", "label": "Imagine"}],
    "infrastructure": [{"url": "https://www.smpte.org/rss.xml", "label": "SMPTE"}, {"url": "https://www.haivision.com/feed/", "label": "Haivision"}],
    "graphics": [{"url": "https://www.vizrt.com/news/rss.xml", "label": "Vizrt"}, {"url": "https://www.newscaststudio.com/category/graphics/feed/", "label": "NewscastStudio"}],
    "cloud": [{"url": "https://blog.frame.io/feed/", "label": "Frame.io"}, {"url": "https://www.adobe.com/video-audio.rss.xml", "label": "Adobe Cloud"}],
    "streaming": [{"url": "https://www.streamingmedia.com/RSS/RSSFeed.aspx", "label": "Streaming Media"}],
    "audio-ai": [{"url": "https://www.redtech.pro/feed/", "label": "RedTech"}]
}

def get_img(item):
    for node in item.findall('.//{http://search.yahoo.com/mrss/}content'):
        if 'url' in node.attrib: return node.attrib['url']
    for node in item.findall('.//enclosure'):
        if 'url' in node.attrib: return node.attrib['url']
    return ""

def run():
    out = []
    for cat, srcs in FEED_SOURCES.items():
        for s in srcs:
            try:
                req = urllib.request.Request(s['url'], headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as r:
                    root = ET.fromstring(r.read())
                    for i in root.findall('.//item'):
                        out.append({
                            "guid": i.findtext('guid') or i.findtext('link'),
                            "title": unescape(i.findtext('title')),
                            "link": i.findtext('link'),
                            "source": s['label'],
                            "category": cat,
                            "image": get_img(i),
                            "timestamp": datetime.now().isoformat()
                        })
            except: continue
    unique = {v['guid']: v for v in out}.values()
    DATA_DIR.mkdir(exist_ok=True)
    with open(NEWS_FILE, 'w') as f: json.dump(list(unique), f, indent=2)

if __name__ == "__main__": run()
