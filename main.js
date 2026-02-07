/* ==================================================================
   THE STREAMIC - Main JavaScript (V3.1 - FIXES)
   - Homepage removed (index redirects to newsroom)
   - Category loader hardened (trim/lowercase)
   - Image handling: better acceptance of querystring images
   - Tiered Bento Grid: Large cards (1-12), List cards (13+)
================================================================== */

(() => {
  const NEWS_FILE = 'data/news.json';

  // Category-specific fallback images
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

  // Accepts images that include an extension even with params, or a known CDN path pattern.
  function isValidImageUrl(url) {
    if (!url || url.trim() === '' || url.includes('fallback.jpg')) return false;

    const rejectPatterns = ['1x1', 'pixel', 'spacer', 'blank', 'placeholder', 'default', 'avatar', 'gravatar', 'data:image', 'base64'];
    const u = url.toLowerCase();
    if (rejectPatterns.some(p => u.includes(p))) return false;

    const hasExt = /\.(jpg|jpeg|png|gif|webp|svg)(\?|#|$)/i.test(u);
    if (hasExt) return true;

    // Some WP/CDN paths hide extension but still serve images (rare). Allow common image/CDN hints.
    const indicators = ['wp-content/uploads', 'images/', '/img/', '/media/', 'cloudinary', 'unsplash', 'cdn.'];
    return indicators.some(h => u.includes(h));
  }

  function renderLargeCard(item) {
    const article = document.createElement('a');
    article.className = 'bento-card-large';
    article.href = item.link || '#';
    article.target = '_blank';
    article.rel = 'noopener noreferrer';

    if (item.isVlog) article.classList.add('vlog-card');

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

    if (item.summary) {
      const summary = document.createElement('p');
      summary.className = 'card-summary';
      summary.textContent = item.summary;
      body.appendChild(summary);
    }

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
    if (!largeGrid || !listGrid) {
      console.error('Grid containers not found');
      return;
    }

    let allItems = [];
    let displayedCount = 0;
    const ITEMS_PER_LOAD = 20;

    fetch(NEWS_FILE)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch news`);
        return res.json();
      })
      .then(items => {
        if (!Array.isArray(items)) throw new Error('Invalid data format');

        const cat = (category || '').toString().trim().toLowerCase();
        allItems = items.filter(it => (it.category || '').toLowerCase() === cat);

        if (allItems.length === 0) {
          largeGrid.innerHTML = `<p class="empty-state">No articles in this category yet. Run fetch.py to populate content.</p>`;
          return;
        }

        loadMoreItems();

        if (allItems.length > ITEMS_PER_LOAD) {
          createLoadMoreButton();
        }
      })
      .catch(err => {
        console.error('Failed to load category:', err);
        largeGrid.innerHTML = '<p class="empty-state">Failed to load content. Please ensure fetch.py has been run and data/news.json exists.</p>';
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
      if (btn && displayedCount >= allItems.length) {
        btn.parentElement.style.display = 'none';
      }
    }

    function createLoadMoreButton() {
      if (document.getElementById('loadMoreBtn')) return;
      const mainContent = document.querySelector('.category-content') || document.querySelector('main');

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
    initMobileNav();

    const body = document.body;
    const category = (body.dataset.category || '').trim().toLowerCase();
    if (category) {
      loadCategoryPage(category);
    } else {
      // There is no homepage anymore (index redirects)
      console.warn('No category detected. If this is intentional, ensure body[data-category] is set.');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.loadCategory = loadCategoryPage;
})();
``
