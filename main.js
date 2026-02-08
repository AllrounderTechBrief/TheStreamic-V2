/* THE STREAMIC - Final main.js (cache-busting + tolerant image check + diversity) */
(() => {
  // Always fetch the latest JSON (avoid CDN/browser cache issues)
  const NEWS_FILE = 'data/news.json?v=' + Date.now();

  const CATEGORY_FALLBACKS = {
    'newsroom': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80',
    'playout': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80',
    'infrastructure': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80',
    'graphics': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80',
    'cloud': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
    'streaming': 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80',
    'audio-ai': 'https://images.unsplash.com/photo-1557800636-894a64c1696f?w=800&q=80'
  };

  function getFallbackImage(category) {
    return CATEGORY_FALLBACKS[category] || CATEGORY_FALLBACKS['newsroom'];
  }

  // ✅ Tolerant image URL check (allow CDN links without extensions)
  function isValidImageUrl(url) {
    if (!url || typeof url !== 'string') return false;
    const u = url.trim().toLowerCase();
    if (!u.startsWith('http')) return false;
    const rejectPatterns = ['data:image', 'base64', '1x1', 'spacer', 'blank', 'pixel', 'fallback.jpg', 'avatar', 'gravatar'];
    if (rejectPatterns.some(p => u.includes(p))) return false;
    // Accept extension-less URLs (browser + onerror will handle bad ones)
    return true;
  }

  // (Optional) light cap so one source doesn't flood a page
  function capPerSource(items, perSource = 6) {
    const counts = new Map();
    const out = [];
    for (const it of items) {
      const src = (it.source || '').trim().toLowerCase();
      const c = counts.get(src) || 0;
      if (c < perSource) {
        out.push(it);
        counts.set(src, c + 1);
      }
    }
    return out;
  }

  function smartSort(items) {
    const withImages = items.filter(item => isValidImageUrl(item.image));
    const withoutImages = items.filter(item => !isValidImageUrl(item.image));
    const diversified = capPerSource(withImages, 6);
    console.log(`Smart Sort: ${withImages.length} with images, ${withoutImages.length} without`);
    return [...diversified, ...withoutImages];
  }

  function renderLargeCard(item) {
    const article = document.createElement('a');
    article.className = 'bento-card-large';
    article.href = item.link || '#';
    article.target = '_blank';
    article.rel = 'noopener noreferrer';

    const figure = document.createElement('figure');
    figure.className = 'card-image';
    const img = document.createElement('img');
    const imageUrl = isValidImageUrl(item.image) ? item.image : getFallbackImage(item.category);
    img.src = imageUrl;
    img.alt = item.title || 'Article image';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
      const fb = getFallbackImage(item.category);
      if (img.src !== fb) img.src = fb;
    });
    figure.appendChild(img);
    article.appendChild(figure);

    const body = document.createElement('div');
    body.className = 'card-body';
    const title = document.createElement('h3');
    title.textContent = item.title || 'Untitled';
    body.appendChild(title);

    const meta = document.createElement('div');
    meta.className = 'card-meta';
    const source = document.createElement('span');
    source.className = 'source';
    source.textContent = item.source || '';
    meta.appendChild(source);

    if (item.category) {
      const tag = document.createElement('span');
      tag.className = 'category-tag';
      tag.textContent = item.category.toUpperCase().replace('-', ' & ');
      meta.appendChild(tag);
    }

    body.appendChild(meta);
    article.appendChild(body);
    return article;
  }

  function renderListCard(item) {
    const article = document.createElement('a');
    article.className = 'list-card-horizontal';
    article.href = item.link || '#';
    article.target = '_blank';
    article.rel = 'noopener noreferrer';

    const figure = document.createElement('figure');
    figure.className = 'card-image';
    const img = document.createElement('img');
    const imageUrl = isValidImageUrl(item.image) ? item.image : getFallbackImage(item.category);
    img.src = imageUrl;
    img.alt = item.title || 'Article image';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
      const fb = getFallbackImage(item.category);
      if (img.src !== fb) img.src = fb;
    });
    figure.appendChild(img);
    article.appendChild(figure);

    const body = document.createElement('div');
    body.className = 'card-body';
    const title = document.createElement('h3');
    title.textContent = item.title || 'Untitled';
    body.appendChild(title);

    const meta = document.createElement('div');
    meta.className = 'card-meta';
    const source = document.createElement('span');
    source.textContent = item.source || '';
    meta.appendChild(source);

    if (item.category) {
      const tag = document.createElement('span');
      tag.textContent = ` • ${item.category.toUpperCase().replace('-', ' & ')}`;
      meta.appendChild(tag);
    }

    body.appendChild(meta);
    article.appendChild(body);
    return article;
  }

  function loadCategoryPage(category) {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    if (!largeGrid || !listGrid) return;

    let allItems = [];
    let displayedCount = 0;
    const ITEMS_PER_LOAD = 20;

    fetch(NEWS_FILE)
      .then(res => res.ok ? res.json() : Promise.reject(`HTTP ${res.status}`))
      .then(items => {
        if (!Array.isArray(items)) throw new Error('Invalid data');
        const cat = (category || '').trim().toLowerCase();
        // Flexible mapping for audio-ai
        let filteredItems = items.filter(it => {
          const c = (it.category || '').toLowerCase();
          if (cat === 'audio-ai') return c === 'audio-ai' || c === 'audio' || c === 'ai';
          return c === cat;
        });

        if (filteredItems.length === 0) {
          largeGrid.innerHTML = `<p class="empty-state">No articles yet. Run fetch.py to populate.</p>`;
          return;
        }

        allItems = smartSort(filteredItems);
        loadMoreItems();
        if (allItems.length > ITEMS_PER_LOAD) createLoadMoreButton();
      })
      .catch(err => {
        console.error('Load error:', err);
        largeGrid.innerHTML = '<p class="empty-state">Failed to load. Ensure fetch.py has run.</p>';
      });

    function loadMoreItems() {
      const next = allItems.slice(displayedCount, displayedCount + ITEMS_PER_LOAD);
      next.forEach((item, index) => {
        const absoluteIndex = displayedCount + index;
        if (absoluteIndex < 12) {
          largeGrid.appendChild(renderLargeCard(item));
        } else {
          listGrid.appendChild(renderListCard(item));
        }
      });
      displayedCount += next.length;
      const btn = document.getElementById('loadMoreBtn');
      if (btn && displayedCount >= allItems.length) btn.parentElement.style.display = 'none';
    }

    function createLoadMoreButton() {
      if (document.getElementById('loadMoreBtn')) return;
      const mainContent = document.querySelector('.category-content') || document.querySelector('main');
      if (!mainContent) return;

      const wrap = document.createElement('div');
      wrap.className = 'view-more-wrap';
      wrap.style.marginTop = '48px';

      const btn = document.createElement('button');
      btn.id = 'loadMoreBtn';
      btn.className = 'btn-view-more';
      btn.textContent = 'Load More';
      btn.addEventListener('click', () => loadMoreItems());

      wrap.appendChild(btn);
      mainContent.appendChild(wrap);
    }
  }

  function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const links = document.querySelector('.nav-links');
    if (!toggle || !links) return;

    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      links.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
      if (links.classList.contains('active') && !toggle.contains(e.target) && !links.contains(e.target)) {
        links.classList.remove('active');
      }
    });

    links.querySelectorAll('a').forEach(link => link.addEventListener('click', () => links.classList.remove('active')));
  }

  function init() {
    console.log('The Streamic - final main.js loaded');
    initMobileNav();
    const category = (document.body.dataset.category || '').trim().toLowerCase();
    if (category) loadCategoryPage(category);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for debugging
  window.loadCategory = loadCategoryPage;
})();
