/* ==================================================================
   THE STREAMIC - Main JavaScript (V3 - FULLY FIXED)
   - Removed HOME from navigation
   - Added Load More functionality  
   - Fixed audio-ai category naming
   - Enhanced image handling with proper fallbacks
   - Tiered Bento Grid: Large cards (1-12), List cards (13+)
================================================================== */

(() => {
  const NEWS_FILE = 'data/news.json';
  
  // Category-specific fallback images - FIXED audio-ai
  const CATEGORY_FALLBACKS = {
    'newsroom': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80',
    'playout': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80',
    'infrastructure': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80',
    'graphics': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80',
    'cloud': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
    'streaming': 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80',
    'audio-ai': 'https://images.unsplash.com/photo-1557800636-894a64c1696f?w=800&q=80'
  };
  
  /* --------- Get Fallback Image --------- */
  function getFallbackImage(category) {
    return CATEGORY_FALLBACKS[category] || CATEGORY_FALLBACKS['newsroom'];
  }
  
  /* --------- Validate Image URL --------- */
  function isValidImageUrl(url) {
    if (!url || url.trim() === '' || url.includes('fallback.jpg')) {
      return false;
    }
    
    // Reject placeholders and tiny images
    const rejectPatterns = ['1x1', 'pixel', 'spacer', 'blank', 'placeholder', 'default'];
    const urlLower = url.toLowerCase();
    
    if (rejectPatterns.some(pattern => urlLower.includes(pattern))) {
      return false;
    }
    
    return true;
  }
  
  /* --------- Render Large Bento Card (Items 1-12) --------- */
  function renderLargeCard(item) {
    const article = document.createElement('a');
    article.className = 'bento-card-large';
    article.href = item.link || '#';
    article.target = '_blank';
    article.rel = 'noopener noreferrer';
    
    // Add vlog styling if applicable
    if (item.isVlog) {
      article.classList.add('vlog-card');
    }
    
    // Image container
    const figure = document.createElement('figure');
    figure.className = 'card-image';
    const img = document.createElement('img');
    
    // Determine image URL
    const imageUrl = isValidImageUrl(item.image) 
      ? item.image 
      : getFallbackImage(item.category);
    
    img.src = imageUrl;
    img.alt = item.title || 'Article image';
    img.loading = 'lazy';
    
    // Error handler
    img.addEventListener('error', () => {
      if (img.src !== getFallbackImage(item.category)) {
        img.src = getFallbackImage(item.category);
      }
    });
    
    figure.appendChild(img);
    article.appendChild(figure);
    
    // Body
    const body = document.createElement('div');
    body.className = 'card-body';
    
    const title = document.createElement('h3');
    title.textContent = item.title || 'Untitled';
    body.appendChild(title);
    
    // AI Summary if available
    if (item.summary) {
      const summary = document.createElement('p');
      summary.className = 'card-summary';
      summary.textContent = item.summary;
      body.appendChild(summary);
    }
    
    // Meta info
    const meta = document.createElement('div');
    meta.className = 'card-meta';
    
    const source = document.createElement('span');
    source.className = 'source';
    source.textContent = item.source || '';
    meta.appendChild(source);
    
    if (item.category) {
      const tag = document.createElement('span');
      tag.className = 'category-tag';
      // Display "AUDIO & AI" instead of "AUDIO-AI"
      tag.textContent = item.category.toUpperCase().replace('-', ' & ');
      meta.appendChild(tag);
    }
    
    body.appendChild(meta);
    article.appendChild(body);
    
    return article;
  }
  
  /* --------- Render List Card (Items 13+) --------- */
  function renderListCard(item) {
    const article = document.createElement('a');
    article.className = 'list-card-horizontal';
    article.href = item.link || '#';
    article.target = '_blank';
    article.rel = 'noopener noreferrer';
    
    // Image
    const figure = document.createElement('figure');
    figure.className = 'card-image';
    const img = document.createElement('img');
    
    const imageUrl = isValidImageUrl(item.image) 
      ? item.image 
      : getFallbackImage(item.category);
    
    img.src = imageUrl;
    img.alt = item.title || 'Article image';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
      if (img.src !== getFallbackImage(item.category)) {
        img.src = getFallbackImage(item.category);
      }
    });
    figure.appendChild(img);
    article.appendChild(figure);
    
    // Body
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
  
  /* --------- Load Homepage (NO HERO) --------- */
  function loadHomepage() {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    
    if (!largeGrid || !listGrid) {
      console.error('Grid containers not found');
      return;
    }
    
    fetch(NEWS_FILE)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch news`);
        return res.json();
      })
      .then(items => {
        if (!Array.isArray(items) || items.length === 0) {
          largeGrid.innerHTML = '<p class="empty-state">No news available. Run fetch.py to populate content.</p>';
          return;
        }
        
        // First 12 items in large bento grid
        items.slice(0, 12).forEach(item => {
          largeGrid.appendChild(renderLargeCard(item));
        });
        
        // Items 13-20 in list format
        items.slice(12, 20).forEach(item => {
          listGrid.appendChild(renderListCard(item));
        });
        
        // Hide View More if less than 20 items
        const viewMoreBtn = document.querySelector('.view-more-wrap');
        if (viewMoreBtn && items.length <= 20) {
          viewMoreBtn.style.display = 'none';
        }
      })
      .catch(err => {
        console.error('Failed to load news:', err);
        largeGrid.innerHTML = '<p class="empty-state">Failed to load content. Please ensure fetch.py has been run and data/news.json exists.</p>';
      });
  }
  
  /* --------- Load Category Page with Load More --------- */
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
        if (!Array.isArray(items)) {
          throw new Error('Invalid data format');
        }
        
        // Filter by category
        allItems = items.filter(item => item.category === category);
        
        if (allItems.length === 0) {
          largeGrid.innerHTML = `<p class="empty-state">No articles in this category yet. Run fetch.py to populate content.</p>`;
          return;
        }
        
        // Initial load
        loadMoreItems();
        
        // Add Load More button if needed
        if (allItems.length > ITEMS_PER_LOAD) {
          createLoadMoreButton();
        }
      })
      .catch(err => {
        console.error('Failed to load category:', err);
        largeGrid.innerHTML = '<p class="empty-state">Failed to load content. Please ensure fetch.py has been run and data/news.json exists.</p>';
      });
    
    function loadMoreItems() {
      const nextBatch = allItems.slice(displayedCount, displayedCount + ITEMS_PER_LOAD);
      
      nextBatch.forEach((item, index) => {
        const absoluteIndex = displayedCount + index;
        
        // First 12 go to large grid, rest to list grid
        if (absoluteIndex < 12) {
          largeGrid.appendChild(renderLargeCard(item));
        } else {
          listGrid.appendChild(renderListCard(item));
        }
      });
      
      displayedCount += nextBatch.length;
      
      // Hide load more button if all items displayed
      const loadMoreBtn = document.getElementById('loadMoreBtn');
      if (loadMoreBtn && displayedCount >= allItems.length) {
        loadMoreBtn.parentElement.style.display = 'none';
      }
    }
    
    function createLoadMoreButton() {
      // Check if button already exists
      if (document.getElementById('loadMoreBtn')) {
        return;
      }
      
      const mainContent = document.querySelector('.category-content') || document.querySelector('main');
      
      const btnWrap = document.createElement('div');
      btnWrap.className = 'view-more-wrap';
      btnWrap.style.marginTop = '48px';
      
      const loadMoreBtn = document.createElement('button');
      loadMoreBtn.id = 'loadMoreBtn';
      loadMoreBtn.className = 'btn-view-more';
      loadMoreBtn.textContent = 'Load More';
      
      loadMoreBtn.addEventListener('click', () => {
        loadMoreItems();
      });
      
      btnWrap.appendChild(loadMoreBtn);
      mainContent.appendChild(btnWrap);
    }
  }
  
  /* --------- Mobile Navigation --------- */
  function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const links = document.querySelector('.nav-links');
    
    if (!toggle || !links) return;
    
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      links.classList.toggle('active');
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (links.classList.contains('active')) {
        if (!toggle.contains(e.target) && !links.contains(e.target)) {
          links.classList.remove('active');
        }
      }
    });
    
    // Close menu when clicking a link
    links.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        links.classList.remove('active');
      });
    });
  }
  
  /* --------- Initialize --------- */
  function init() {
    console.log('The Streamic V3 - Initializing...');
    
    initMobileNav();
    
    // Determine page type and load accordingly
    const body = document.body;
    
    if (body.classList.contains('homepage')) {
      console.log('Loading homepage...');
      loadHomepage();
    } else if (body.dataset.category) {
      console.log(`Loading category: ${body.dataset.category}`);
      loadCategoryPage(body.dataset.category);
    } else {
      console.warn('Unknown page type');
    }
  }
  
  // Run when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  // Export for external use if needed
  window.loadCategory = loadCategoryPage;
  
})();
