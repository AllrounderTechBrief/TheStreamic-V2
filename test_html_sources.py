"""
tests/test_html_sources.py
--------------------------
Lightweight smoke tests for scrapers/html_sources.py.

Design rules:
  - Tests NEVER hard-fail due to live site layout changes.
  - Tests skip automatically if beautifulsoup4 is not installed.
  - A "0 results" response from a live site is acceptable (not a failure).
  - A crash / exception IS a failure.

Run with:
    pytest tests/test_html_sources.py -v
"""

import pytest

# Skip entire module if dependencies are missing
pytest.importorskip("requests", reason="requests not installed")
pytest.importorskip("bs4", reason="beautifulsoup4 not installed")

from scrapers.html_sources import (
    fetch_tvbeurope_headlines,
    fetch_ncs_digital_headlines,
    _parse_anchors,
    _normalise_href,
)


# ─── Unit tests (no network) ──────────────────────────────────────────────────

def test_normalise_href_absolute():
    assert _normalise_href('https://example.com/page', 'https://base.com') == 'https://example.com/page'


def test_normalise_href_relative():
    result = _normalise_href('/news/article-1', 'https://www.tvbeurope.com')
    assert result == 'https://www.tvbeurope.com/news/article-1'


def test_normalise_href_empty():
    assert _normalise_href('', 'https://base.com') == ''


def test_parse_anchors_simple():
    html = """
    <html><body>
      <article>
        <h2><a href="/story/1">First Story</a></h2>
        <h2><a href="/story/2">Second Story</a></h2>
      </article>
    </body></html>
    """
    results = _parse_anchors(html, 'https://example.com', ['article h2 a'], limit=10)
    assert len(results) == 2
    assert results[0]['title'] == 'First Story'
    assert results[0]['link'] == 'https://example.com/story/1'
    assert results[0]['image'] is None


def test_parse_anchors_no_match_returns_empty():
    html = "<html><body><p>No headlines here</p></body></html>"
    results = _parse_anchors(html, 'https://example.com', ['article h2 a'], limit=10)
    assert results == []


def test_parse_anchors_respects_limit():
    links = ''.join(f'<h2><a href="/s/{i}">Story {i}</a></h2>' for i in range(20))
    html = f"<html><body>{links}</body></html>"
    results = _parse_anchors(html, 'https://example.com', ['h2 a'], limit=5)
    assert len(results) == 5


# ─── Integration smoke tests (live network) ───────────────────────────────────

def test_tvbeurope_returns_list():
    """Scraper must return a list; it's OK if the list is empty (site may block)."""
    results = fetch_tvbeurope_headlines(limit=5)
    assert isinstance(results, list), "Expected a list"
    for item in results:
        assert isinstance(item.get('title'), str) and item['title']
        assert isinstance(item.get('link'), str) and item['link'].startswith('http')
        assert item.get('source') == 'TVBEurope'
    if results:
        print(f"\n  ✓ TVBEurope sample: {results[0]['title'][:70]}")


def test_ncs_digital_returns_list():
    """Scraper must return a list; it's OK if the list is empty (site may block)."""
    results = fetch_ncs_digital_headlines(limit=5)
    assert isinstance(results, list), "Expected a list"
    for item in results:
        assert isinstance(item.get('title'), str) and item['title']
        assert isinstance(item.get('link'), str) and item['link'].startswith('http')
        assert item.get('source') == 'NCS Digital'
    if results:
        print(f"\n  ✓ NCS Digital sample: {results[0]['title'][:70]}")


def test_unreachable_url_does_not_raise():
    """Scrapers must never raise on bad URLs — always return []."""
    results = fetch_tvbeurope_headlines(
        url='https://thisdomaindoesnotexist.invalid/',
        limit=3,
    )
    assert results == []


def test_ncs_unreachable_url_does_not_raise():
    results = fetch_ncs_digital_headlines(
        url='https://thisdomaindoesnotexist.invalid/',
        limit=3,
    )
    assert results == []
