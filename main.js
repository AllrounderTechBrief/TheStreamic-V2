/**
 * THE STREAMIC - Optimized main.js with Worker Integration
 * 
 * INSTALLATION:
 * 1. Replace your existing main.js with this file
 * 2. Keep all HTML files unchanged (this maintains compatibility)
 * 3. Deploy to GitHub Pages
 * 
 * FEATURES:
 * - Integrates with Cloudflare Worker for guaranteed thumbnails
 * - Batched incremental rendering (responsive UI)
 * - Lazy image loading with IntersectionObserver
 * - Maintains existing renderLargeCard/renderListCard functions
 * - Works with existing CSS and HTML structure
 * 
 * CHANGES FROM ORIGINAL:
 * - Uses Cloudflare Worker instead of local news.json
 * - Adds incremental rendering for smooth performance
 * - Implements lazy image loading
 * - More tolerant image URL validation
 * - Better error handling
 */

(() => {
  // ==========================================================================
  // CONFIGURATION
  // ==========================================================================
  
  const WORKER = 'https://broken-king-b4dc.itabmum.workers.dev';
  
  const FEEDS = [
    'https://www.newscaststudio.com/tag/news-production/feed/',
    'https://www.tvtechnology.com/rss.xml',
    'https://www.broadcastbeat.com/feed/',
    'https://www.svgeurope.org/feed/',
    'https://www.inbroadcast.com/feed/',
    'https://www.thebroadcastbridge.com/rss.xml'
  ];
  
  const PER_FEED_LIMIT = 10;
  const ITEMS_PER_BATCH = 12;
  
  const CATEGORY_FALLBACKS = {
    'featured': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80&fm=webp',
    'playout': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80&fm=webp',
    'infrastructure': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80&fm=webp',
    'graphics': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80&fm=webp',
    'cloud-production': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80&fm=webp',
    'streaming': 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80&fm=webp',
    'audio-ai': 'https://images.unsplash.com/photo-1589903308904-1010c2294adc?w=800&q=80&fm=webp'
  };

  // ==========================================================================
  // GLOBAL STATE
  // ==========================================================================
  
  let imageObserver = null;
  let allItems = [];
  let displayedCount = 0;
  const ITEMS_PER_LOAD = 20;

  // ==========================================================================
  // UTILITIES
  // ==========================================================================

  function getFallbackImage(category) {
    const cat = (category || '').toLowerCase().trim();
    if (cat === 'cloud') return CATEGORY_FALLBACKS['cloud-production'];
    if (cat === 'newsroom') return CATEGORY_FALLBACKS['featured'];
    return CATEGORY_FALLBACKS[cat] || CATEGORY_FALLBACKS['featured'];
  }

  /**
   * Tolerant image URL validation
   * Accepts CDN URLs without extensions
   */
  function isValidImageUrl(url) {
    if (!url || typeof url !== 'string') return false;
    const u = url.trim().toLowerCase();
    
    // Must be HTTP/HTTPS
    if (!u.startsWith('http')) return false;
    
    // Reject obvious tracking pixels
    const rejectPatterns = ['1x1', 'spacer', 'blank', 'pixel'];
    if (rejectPatterns.some(p => u.includes(p))) return false;
    
    // Accept everything else (browser will handle failures via onerror)
    return true;
  }

  /**
   * Setup lazy image loading with IntersectionObserver
   */
  function setupImageObserver() {
    if (!('IntersectionObserver' in window)) {
      console.log('IntersectionObserver not available, using native lazy loading');
      return null;
    }
    
    return new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          const src = img.dataset.src;
          
          if (src) {
            img.src = src;
            img.classList.remove('lazy');
            observer.unobserve(img);
          }
        }
      });
    }, {
      rootMargin: '50px',
      threshold: 0.01
    });
  }

  /**
   * Create image element with lazy loading
   */
  function createLazyImage(imageUrl, alt, category) {
    const img = document.createElement('img');
    img.alt = alt || 'Article image';
    
    const validUrl = isValidImageUrl(imageUrl) ? imageUrl : getFallbackImage(category);
    
    if (imageObserver) {
      // Use IntersectionObserver for lazy loading
      img.dataset.src = validUrl;
      img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
      img.classList.add('lazy');
      imageObserver.observe(img);
    } else {
      // Fallback to native lazy loading
      img.src = validUrl;
      img.loading = 'lazy';
    }
    
    // Error fallback
    img.addEventListener('error', () => {
      const fallback = getFallbackImage(category);
      if (img.src !== fallback) {
        img.src = fallback;
      }
    });
    
    return img;
  }

  // ==========================================================================
  // RENDERING FUNCTIONS (keeping original structure)
  // ==========================================================================

  function renderLargeCard(item) {
    const article = document.createElement('a');
    article.className = 'bento-card-large';
    article.href = item.link || '#';
    article.target = '_blank';
    article.rel = 'noopener noreferrer';

    const figure = document.createElement('figure');
    figure.className = 'card-image';
    
    // Use lazy loading
    const img = createLazyImage(item.thumbnail_url || item.image, item.title, item.category);
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
    
    // Use lazy loading
    const img = createLazyImage(item.thumbnail_url || item.image, item.title, item.category);
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

  // ==========================================================================
  // FEED LOADING WITH WORKER
  // ==========================================================================

  async function fetchFeed(feedUrl) {
    const workerUrl = `${WORKER}?url=${encodeURIComponent(feedUrl)}&format=json&limit=${PER_FEED_LIMIT}`;
    
    try {
      const response = await fetch(workerUrl);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!Array.isArray(data)) {
        throw new Error('Invalid response format');
      }
      
      return data;
      
    } catch (error) {
      console.error(`Failed to fetch ${feedUrl}:`, error);
      throw error;
    }
  }

  async function loadAllFeeds(category) {
    console.log(`Loading feeds for category: ${category || 'all'}`);
    
    try {
      // Fetch all feeds in parallel
      const feedPromises = FEEDS.map(feedUrl => fetchFeed(feedUrl));
      const results = await Promise.allSettled(feedPromises);
      
      // Collect successful results
      const items = [];
      results.forEach((result, index) => {
        if (result.status === 'fulfilled' && Array.isArray(result.value)) {
          items.push(...result.value);
          console.log(`✓ Feed ${index + 1}: ${result.value.length} items`);
        } else {
          console.warn(`✗ Feed ${index + 1} failed:`, result.reason);
        }
      });
      
      if (items.length === 0) {
        throw new Error('No articles loaded from any feed');
      }
      
      // Filter by category if needed
      let filteredItems;
      const cat = (category || '').trim().toLowerCase();
      
      if (cat === 'featured' || !cat) {
        // Featured shows ALL articles
        filteredItems = items;
      } else if (cat === 'audio-ai') {
        // Audio-AI: Only audio and AI content
        filteredItems = items.filter(it => {
          const c = (it.category || '').toLowerCase();
          return c === 'audio-ai' || c === 'audio' || c === 'ai';
        });
      } else if (cat === 'cloud-production' || cat === 'cloud') {
        // Cloud Production
        filteredItems = items.filter(it => {
          const c = (it.category || '').toLowerCase();
          return c === 'cloud' || c === 'cloud-production';
        });
      } else {
        // Standard category filtering
        filteredItems = items.filter(it => {
          const c = (it.category || '').toLowerCase();
          return c === cat;
        });
      }
      
      // Sort by date (newest first)
      return filteredItems.sort((a, b) => {
        const dateA = new Date(a.pubDate);
        const dateB = new Date(b.pubDate);
        return dateB - dateA;
      });
      
    } catch (error) {
      console.error('Failed to load feeds:', error);
      throw error;
    }
  }

  // ==========================================================================
  // INCREMENTAL RENDERING
  // ==========================================================================

  function renderNextBatch() {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    
    if (!largeGrid || !listGrid) return;
    
    const nextItems = allItems.slice(displayedCount, displayedCount + ITEMS_PER_BATCH);
    
    if (nextItems.length === 0) {
      hideLoadMoreButton();
      return;
    }
    
    // Use requestIdleCallback for smooth rendering
    const scheduleRender = window.requestIdleCallback || 
      ((cb) => setTimeout(cb, 50));
    
    scheduleRender(() => {
      // Use DocumentFragment for efficient DOM manipulation
      const largeFragment = document.createDocumentFragment();
      const listFragment = document.createDocumentFragment();
      
      nextItems.forEach((item, index) => {
        const absoluteIndex = displayedCount + index;
        
        if (absoluteIndex < 12) {
          largeFragment.appendChild(renderLargeCard(item));
        } else {
          listFragment.appendChild(renderListCard(item));
        }
      });
      
      // Single append per grid
      largeGrid.appendChild(largeFragment);
      listGrid.appendChild(listFragment);
      
      displayedCount += nextItems.length;
      
      // Show/hide load more button
      const btn = document.getElementById('loadMoreBtn');
      if (btn) {
        if (displayedCount >= allItems.length) {
          btn.parentElement.style.display = 'none';
        }
      }
      
      console.log(`Rendered ${displayedCount} / ${allItems.length} articles`);
    });
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
    btn.addEventListener('click', () => renderNextBatch());

    wrap.appendChild(btn);
    mainContent.appendChild(wrap);
  }

  function hideLoadMoreButton() {
    const btn = document.getElementById('loadMoreBtn');
    if (btn && btn.parentElement) {
      btn.parentElement.style.display = 'none';
    }
  }

  // ==========================================================================
  // CATEGORY PAGE LOADER
  // ==========================================================================

  function loadCategoryPage(category) {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    
    if (!largeGrid || !listGrid) return;
    
    // Show loading state
    largeGrid.innerHTML = '<p class="empty-state">Loading articles...</p>';
    listGrid.innerHTML = '';
    
    // Reset state
    allItems = [];
    displayedCount = 0;
    
    // Load feeds
    loadAllFeeds(category)
      .then(items => {
        if (items.length === 0) {
          largeGrid.innerHTML = '<p class="empty-state">No articles found for this category.</p>';
          return;
        }
        
        allItems = items;
        largeGrid.innerHTML = '';
        
        // Render first batch
        renderNextBatch();
        
        // Setup load more button if needed
        if (allItems.length > ITEMS_PER_BATCH) {
          createLoadMoreButton();
        }
      })
      .catch(error => {
        console.error('Load error:', error);
        largeGrid.innerHTML = '<p class="empty-state">Failed to load articles. Please try again later.</p>';
      });
  }

  // ==========================================================================
  // MOBILE NAVIGATION
  // ==========================================================================

  function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const links = document.querySelector('.nav-links');
    
    if (!toggle || !links) return;

    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      links.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
      if (links.classList.contains('active') && 
          !toggle.contains(e.target) && 
          !links.contains(e.target)) {
        links.classList.remove('active');
      }
    });

    links.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => links.classList.remove('active'));
    });
  }

  // ==========================================================================
  // INITIALIZATION
  // ==========================================================================

  function init() {
    console.log('The Streamic - Optimized main.js loaded');
    
    // Setup lazy image observer
    imageObserver = setupImageObserver();
    
    // Setup mobile navigation
    initMobileNav();
    
    // Load category page if on a category page
    const category = (document.body.dataset.category || '').trim().toLowerCase();
    if (category) {
      loadCategoryPage(category);
    }
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for debugging
  window.loadCategory = loadCategoryPage;
  window.theStreamicDebug = {
    reload: () => loadCategoryPage(document.body.dataset.category),
    getItems: () => allItems,
    getDisplayed: () => displayedCount,
    renderMore: renderNextBatch
  };
})();
