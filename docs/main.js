/* THE STREAMIC – main.js
   TVBEurope bento grid: first card large, all others horizontal (image-left/text-right)
   Targets: <main id="bentoGridLarge" class="bento-grid-large">
   Reads:   data/news.json  { featured_priority: [], items: [] }
*/
(() => {
  'use strict';

  // ── CONFIG ────────────────────────────────────────────────────────────────
  const NEWS_FILE       = 'data/news.json?v=' + Date.now();
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

    const imgUrl  = pickImage(item);
    const title   = item.title  || 'Untitled';
    const url     = item.link   || '#';
    const summary = truncate(item.summary || item.dek || item.teaser || '', SUMMARY_LIMIT);
    const source  = item.source || item.sourceName || '';

    // Image container
    const imgWrap = document.createElement('div');
    imgWrap.className = 'bento-image-container';
    imgWrap.appendChild(makeLazyImg(imgUrl, title));
    li.appendChild(imgWrap);

    // Content container
    const content = document.createElement('div');
    content.className = 'bento-content-container';

    const h3 = document.createElement('h3');
    const a  = document.createElement('a');
    a.href       = url;
    a.target     = '_blank';
    a.rel        = 'noopener noreferrer';
    a.textContent = title;
    h3.appendChild(a);
    content.appendChild(h3);

    if (summary) {
      const p  = document.createElement('p');
      p.textContent = summary;
      content.appendChild(p);
    }

    if (source) {
      const span  = document.createElement('span');
      span.className = 'source-credit';
      span.textContent = source;
      content.appendChild(span);
    }

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
    const r = await fetch(NEWS_FILE);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
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
