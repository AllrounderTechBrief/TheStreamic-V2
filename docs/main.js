/* THE STREAMIC – main.js
   TVBEurope bento grid: first card large, all others horizontal (image-left/text-right)
   Targets: <main id="bentoGridLarge" class="bento-grid-large">
   Reads:   data/news.json  { featured_priority: [], items: [] }
*/
(() => {
  'use strict';

  // ── CONFIG ────────────────────────────────────────────────────────────────
  // news.json lives in docs/data/ (served by GitHub Pages)
  // On root-served fallback it's at data/news.json from root
  const _bust = Date.now();
  const NEWS_FILE = 'data/news.json?v=' + _bust;
  const ITEMS_PER_BATCH = 12;
  const SUMMARY_LIMIT   = 1800;  // chars — keeps layout stable if Groq over-generates

  const CAT_FALLBACKS = {
    featured:           'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80&fm=webp',
    newsroom:           'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80&fm=webp',
    playout:            'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80&fm=webp',
    infrastructure:     'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80&fm=webp',
    graphics:           'https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=800&q=80&fm=webp',
    cloud:              'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80&fm=webp',
    'cloud-production': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80&fm=webp',
    streaming:          'https://images.unsplash.com/photo-1499364615650-ec38552f4f34?w=800&q=80&fm=webp',
    'ai-post-production':'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=800&q=80&fm=webp',
  };

  // ── STATE ─────────────────────────────────────────────────────────────────
  let allItems      = [];
  let displayedCount = 0;
  let observer      = null;

  // ── UTILS ─────────────────────────────────────────────────────────────────
  function fallback(cat) {
    const c = (cat || '').toLowerCase().trim();
    return CAT_FALLBACKS[c] || CAT_FALLBACKS.featured;
  }

  function isValidUrl(url) {
    const u = (url || '').trim().toLowerCase();
    return u.startsWith('http://') || u.startsWith('https://');
  }

  function pickImage(item) {
    return isValidUrl(item.image) ? item.image : fallback(item.category);
  }

  function truncate(str, max) {
    if (!str) return '';
    str = str.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    return str.length > max ? str.substring(0, max).replace(/\s+\S*$/, '') + '…' : str;
  }

  function setupLazyObserver() {
    if (!('IntersectionObserver' in window)) return null;
    return new IntersectionObserver((entries, obs) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const img = e.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            obs.unobserve(img);
          }
        }
      });
    }, { rootMargin: '60px', threshold: 0.01 });
  }

  function makeLazyImg(url, alt) {
    const img = document.createElement('img');
    img.alt = alt || '';
    img.className = 'ts-card-img';
    if (observer) {
      img.dataset.src = url;
      img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
      img.classList.add('lazy');
      observer.observe(img);
    } else {
      img.src = url;
      img.loading = 'lazy';
    }
    return img;
  }

  // ── CARD BUILDER ──────────────────────────────────────────────────────────
  /**
   * createCardHtml — returns an <li class="bento-grid-item"> element.
   * Identical structure for every card; CSS :first-child handles the big one.
   *
   * Inner structure (spec-compliant):
   *   <div class="bento-image-container"><img …></div>
   *   <div class="bento-content-container">
   *     <h3><a href="…">…</a></h3>
   *     <p>…</p>
   *     <span class="source-credit">…</span>
   *   </div>
   */
  function createCardHtml(item) {
    const li = document.createElement('li');
    li.className = 'bento-grid-item';

    // Resolve item fields — fetch.py uses 'link' or 'url'
    const imgUrl = pickImage(item);
    const title  = (item.title  || 'Untitled').trim();
    const url    = (item.link || item.url || '#').trim();
    const source = (item.source || item.sourceName || item.sourceLabel || '').trim();

    // Summary: prefer Groq-generated card_summary; fall back to RSS teaser
    const rawSummary = item.card_summary || item.summary || item.dek
                     || item.teaser || item.description || '';
    const summary = truncate(rawSummary, SUMMARY_LIMIT);

    // ── Image container ──────────────────────────────────────────────────────
    const imgWrap = document.createElement('div');
    imgWrap.className = 'bento-image-container';
    const imgLink = document.createElement('a');
    imgLink.href   = url;
    imgLink.target = '_blank';
    imgLink.rel    = 'noopener noreferrer nofollow';
    imgLink.setAttribute('aria-label', title);
    imgLink.appendChild(makeLazyImg(imgUrl, title));
    imgWrap.appendChild(imgLink);
    li.appendChild(imgWrap);

    // ── Content container ────────────────────────────────────────────────────
    const content = document.createElement('div');
    content.className = 'bento-content-container';

    // Title — clickable, opens source in new tab
    const h3 = document.createElement('h3');
    h3.className = 'ts-card-title';
    const titleLink = document.createElement('a');
    titleLink.href   = url;
    titleLink.target = '_blank';
    titleLink.rel    = 'noopener noreferrer nofollow';
    titleLink.textContent = title;
    h3.appendChild(titleLink);
    content.appendChild(h3);

    // Summary paragraph
    if (summary) {
      const p = document.createElement('p');
      p.className = 'ts-card-summary';
      p.textContent = summary;
      content.appendChild(p);
    }

    // Footer: source credit + Read Full Story link
    const footer = document.createElement('div');
    footer.className = 'ts-card-footer';

    if (source) {
      const srcSpan = document.createElement('span');
      srcSpan.className = 'ts-source source-credit';
      srcSpan.textContent = source;
      footer.appendChild(srcSpan);
    }

    if (url && url !== '#') {
      const readLink = document.createElement('a');
      readLink.href      = url;
      readLink.target    = '_blank';
      readLink.rel       = 'noopener noreferrer nofollow';
      readLink.className = 'ts-read-more';
      readLink.textContent = 'Read Full Story →';
      footer.appendChild(readLink);
    }

    content.appendChild(footer);
    li.appendChild(content);
    return li;
  }

  // ── RENDER BATCH ─────────────────────────────────────────────────────────
  function renderNextBatch() {
    const grid = document.getElementById('bentoGridLarge');
    if (!grid) return;

    const slice = allItems.slice(displayedCount, displayedCount + ITEMS_PER_BATCH);
    if (slice.length === 0) { hideLoadMore(); return; }

    const schedule = window.requestIdleCallback || (cb => setTimeout(cb, 50));
    schedule(() => {
      const frag = document.createDocumentFragment();
      slice.forEach(item => frag.appendChild(createCardHtml(item)));
      grid.appendChild(frag);
      displayedCount += slice.length;

      const btn = document.getElementById('loadMoreBtn');
      if (btn && displayedCount >= allItems.length) {
        btn.parentElement.style.display = 'none';
      }
    });
  }

  // ── LOAD MORE ────────────────────────────────────────────────────────────
  function createLoadMoreBtn() {
    if (document.getElementById('loadMoreBtn')) return;
    const container = document.querySelector('.category-content') || document.querySelector('main');
    if (!container) return;
    const wrap = document.createElement('div');
    wrap.style.cssText = 'margin:48px auto;text-align:center;';
    const btn  = document.createElement('button');
    btn.id = 'loadMoreBtn';
    btn.className = 'btn-view-more';
    btn.textContent = 'Load More';
    btn.addEventListener('click', () => renderNextBatch());
    wrap.appendChild(btn);
    container.appendChild(wrap);
  }

  function hideLoadMore() {
    const btn = document.getElementById('loadMoreBtn');
    if (btn && btn.parentElement) btn.parentElement.style.display = 'none';
  }

  // ── DATA LOADING ─────────────────────────────────────────────────────────
  async function loadJson() {
    // Try current-directory first (docs/data/ served as /data/)
    let r = await fetch(NEWS_FILE).catch(() => null);
    if (!r || !r.ok) {
      // Fallback: explicit path for root-served Pages
      r = await fetch('/data/news.json?v=' + Date.now()).catch(() => null);
    }
    if (!r || !r.ok) throw new Error('news.json not reachable');
    const raw = await r.json();

    // Normalise: accept flat list, {items,featured_priority}, or {category:[...]} dict
    if (Array.isArray(raw)) {
      // flat list from fetch.py
      const featured = raw.filter(it => (it.category||'').toLowerCase() === 'featured').slice(0,6);
      const rest     = raw.filter(it => (it.category||'').toLowerCase() !== 'featured');
      return { featured_priority: featured, items: rest };
    }
    if (raw.items !== undefined || raw.featured_priority !== undefined) {
      return raw;  // already normalised
    }
    // dict-of-categories: flatten
    const flat = [];
    Object.entries(raw).forEach(([cat, list]) => {
      (list || []).forEach(it => { flat.push({ ...it, category: it.category || cat }); });
    });
    flat.sort((a,b) => (b.pubDate||b.published||'').localeCompare(a.pubDate||a.published||''));
    return { featured_priority: flat.slice(0,6), items: flat.slice(6) };
  }

  function filterByCategory(items, cat) {
    const c = cat.toLowerCase().trim();
    return items.filter(it => (it.category || '').toLowerCase().trim() === c);
  }

  function interleaveBySource(items) {
    const bySource = {};
    items.forEach(it => {
      const s = it.source || 'unknown';
      if (!bySource[s]) bySource[s] = [];
      bySource[s].push(it);
    });
    const groups = Object.values(bySource);
    const out = [];
    let i = 0;
    while (out.length < items.length) {
      let added = false;
      groups.forEach(g => {
        if (i < g.length) { out.push(g[i]); added = true; }
      });
      if (!added) break;
      i++;
    }
    return out;
  }

  // ── PAGE LOADER ───────────────────────────────────────────────────────────
  function loadPage(category) {
    const grid = document.getElementById('bentoGridLarge');
    if (!grid) return;   // page doesn't have the bento grid; skip

    grid.innerHTML = '<p class="empty-state" style="padding:40px;color:#86868b;">Loading…</p>';
    allItems      = [];
    displayedCount = 0;

    loadJson()
      .then(data => {
        const { items = [], featured_priority = [] } = data;
        const cat = (category || '').trim().toLowerCase();
        let filtered;

        if (!cat || cat === 'featured') {
          const priorityIds = new Set(featured_priority.map(it => it.guid || it.link));
          const rest        = items.filter(it => !priorityIds.has(it.guid || it.link));
          filtered = [...featured_priority, ...rest];
        } else {
          filtered = filterByCategory(items, cat);
        }

        // Only keep items with real URLs
        filtered = filtered.filter(it => isValidUrl(it.link));

        if (filtered.length === 0) {
          grid.innerHTML = '<p class="empty-state" style="padding:40px;color:#86868b;">No articles yet. Check back soon!</p>';
          return;
        }

        allItems = (cat === 'featured' || !cat) ? filtered : interleaveBySource(filtered);
        grid.innerHTML = '';
        renderNextBatch();
        if (allItems.length > ITEMS_PER_BATCH) createLoadMoreBtn();
      })
      .catch(err => {
        console.error('[Streamic] load error:', err);
        grid.innerHTML = '<p class="empty-state" style="padding:40px;color:#e0003c;">Failed to load articles.</p>';
      });
  }

  // ── MOBILE NAV ────────────────────────────────────────────────────────────
  function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const links  = document.querySelector('.nav-links');
    if (!toggle || !links) return;
    toggle.addEventListener('click', e => {
      e.stopPropagation();
      links.classList.toggle('active');
      links.classList.toggle('nav-open');
    });
    document.addEventListener('click', e => {
      if (!links.contains(e.target) && !toggle.contains(e.target)) {
        links.classList.remove('active', 'nav-open');
      }
    });
    links.querySelectorAll('a').forEach(a =>
      a.addEventListener('click', () => links.classList.remove('active', 'nav-open'))
    );
  }

  // ── INIT ──────────────────────────────────────────────────────────────────
  function init() {
    observer = setupLazyObserver();
    initMobileNav();

    // Detect current category from <body data-category="..."> or URL
    const bodyCategory = document.body.dataset.category || '';
    const pathMatch    = window.location.pathname.match(/\/([^/]+)\.html$/);
    const pathCategory = pathMatch ? pathMatch[1].replace('.html', '') : '';
    const category     = bodyCategory || pathCategory || 'featured';

    // Only run on pages that have the bento grid
    if (document.getElementById('bentoGridLarge')) {
      loadPage(category);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
