"""
scrapers/html_sources.py
------------------------
Optional HTML headline scrapers for sources without RSS feeds.
Used ONLY when ENABLE_HTML_SCRAPERS = True in fetch.py.

Rules:
  - Extracts titles + links ONLY (no article bodies, no paywall bypass).
  - Summaries are generated in fetch.py from the headline text — copyright safe.
  - All network calls use timeouts and try/except; failures return empty lists.
  - Uses beautifulsoup4 (must be installed — see requirements.txt).
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

# Optional imports — scrapers degrade gracefully if bs4 not installed
try:
    import requests
    from bs4 import BeautifulSoup
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (compatible; TheStreamic/1.0; '
        '+https://thestreamic.com)'
    )
}
_TIMEOUT = 10  # seconds


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _check_deps() -> bool:
    if not _DEPS_AVAILABLE:
        print(" ⚠ HTML scrapers require 'requests' and 'beautifulsoup4'. "
              "Run: pip install beautifulsoup4")
    return _DEPS_AVAILABLE


def _fetch_html(url: str) -> Optional[str]:
    """GET a page and return its text, or None on any error."""
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
        if resp.status_code == 200:
            return resp.text
        print(f" ⚠ HTTP {resp.status_code} for {url}")
    except Exception as exc:
        print(f" ⚠ Fetch error for {url[:80]}: {exc}")
    return None


def _normalise_href(href: str, base: str) -> str:
    """
    Resolve relative URLs against base.
    Returns empty string for anything that isn't a real http(s) URL —
    catches about:blank, javascript:, bare #anchors, and empty hrefs.
    """
    href = (href or '').strip()
    if not href or href.startswith('#'):
        return ''
    if href.lower().startswith('javascript'):
        return ''
    resolved = href if href.startswith('http') else urljoin(base, href)
    # Final guard — about:blank, data:, etc. are rejected here
    if not resolved.startswith('http'):
        return ''
    return resolved


def _parse_anchors(
    html: str,
    base_url: str,
    selectors: list[str],
    limit: int,
) -> list[dict]:
    """
    Try CSS selectors in order; return items from the first one that yields
    real article links. Filters out nav labels, about:blank, and homepage links.
    """
    soup = BeautifulSoup(html, 'html.parser')
    now_iso = datetime.now(timezone.utc).isoformat()
    base_norm = base_url.rstrip('/')

    for selector in selectors:
        anchors = soup.select(selector)
        results = []
        for anchor in anchors[:limit * 3]:  # oversample so filtering doesn't starve results
            title = anchor.get_text(strip=True)
            href = _normalise_href(anchor.get('href', ''), base_url)

            # Must have a valid http(s) link that isn't the homepage itself
            if not href or href.rstrip('/') == base_norm:
                continue
            # Title must be long enough to be a real headline (skips "News", nav labels)
            if len(title) < 12:
                continue
            # Skip short all-caps navigation labels like "BROADCAST NEWS"
            if title.isupper() and len(title) < 40:
                continue

            results.append({
                'title': title,
                'link': href,
                'guid': href,
                'image': None,
                'pubDate': now_iso,
            })
            if len(results) >= limit:
                break

        if results:
            return results

    return []


# ─── Public scraper functions ─────────────────────────────────────────────────

def fetch_tvbeurope_headlines(
    url: str = 'https://www.tvbeurope.com/',
    limit: int = 10,
) -> list[dict]:
    """
    Scrape up to `limit` article headlines from TVBEurope.
    Returns a list of dicts with keys: title, link, guid, image, pubDate, source.
    Returns [] on any failure without raising.
    """
    if not _check_deps():
        return []

    html = _fetch_html(url)
    if not html:
        return []

    # Ordered from most-specific to most-generic — first hit wins
    selectors = [
        'h2.article-title a',
        'h3.article-title a',
        'h2.entry-title a',
        'h3.entry-title a',
        'article h2 a',
        'article h3 a',
        '.post-title a',
        'h2 a',
        'h3 a',
    ]

    items = _parse_anchors(html, url, selectors, limit)

    for item in items:
        item['source'] = 'TVBEurope'

    print(f" → TVBEurope: found {len(items)} headlines")
    return items


def fetch_ncs_digital_headlines(
    url: str = 'https://digital.newscaststudio.com/',
    limit: int = 10,
) -> list[dict]:
    """
    Scrape up to `limit` article headlines from NewscastStudio Digital.
    Returns a list of dicts with keys: title, link, guid, image, pubDate, source.
    Returns [] on any failure without raising.
    """
    if not _check_deps():
        return []

    html = _fetch_html(url)
    if not html:
        return []

    selectors = [
        'h2.entry-title a',
        'h3.entry-title a',
        'h2.article-title a',
        'h3.article-title a',
        'article h2 a',
        'article h3 a',
        '.post-title a',
        'h2 a',
        'h3 a',
    ]

    items = _parse_anchors(html, url, selectors, limit)

    for item in items:
        item['source'] = 'NCS Digital'

    print(f" → NCS Digital: found {len(items)} headlines")
    return items
