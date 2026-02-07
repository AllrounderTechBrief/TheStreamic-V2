/* =========================================================
   THE STREAMIC - Main JavaScript (FIXED)
   - No category count in heading
   - Better fallback image handling
   - Tiered Bento Grid: Large cards (1-12), List cards (13-20)
========================================================= */

(() => {
  const NEWS_FILE = 'data/news.json';
  const ARCHIVE_FILE = 'data/archive.json';
  
  // Category-specific fallback images
  const CATEGORY_FALLBACKS = {
    'newsroom': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80',
    'playout': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80',
    'infrastructure': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80',
    'graphics': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80',
    'cloud': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
    'streaming': 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80',
    'audio-ai': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80'
  };
  
  /* ---------- Get Fallback Image for Category ---------- */
  function getFallbackImage(category) {
    return CATEGORY_FALLBACKS[category] || 'assets/fallback.jpg';
  }
  
  /* ---------- Render Large Bento Card (Items 1-12) ---------- */
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
    
    // Image
    const figure = document.createElement('figure');
    figure.className = 'card-image';
    const img = document.createElement('img');
    
    // Use category fallback if no image or invalid image
    const imageUrl = (item.image && !item.image.includes('fallback.jpg')) 
      ? item.image 
      : getFallbackImage(item.category);
    
    img.src = imageUrl;
    img.alt = item.title || 'Article image';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
      img.src = getFallbackImage(item.category);
    });
    figure.appendChild(img);
    article.appendChild(figure);
    
    // Body
    const body = document.createElement('div');
    body.className = 'card-body';
    
    const title = document.createElement('h3');
    title.textContent = item.title || 'Untitled';
    body.appendChild(title);
    
    // AI Summary (2 sentences max)
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
      tag.textContent = item.category.toUpperCase();
      meta.appendChild(tag);
    }
    
    body.appendChild(meta);
    article.appendChild(body);
    
    return article;
  }
  
  /* ---------- Render List Card (Items 13-20) ---------- */
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
    
    const imageUrl = (item.image && !item.image.includes('fallback.jpg')) 
      ? item.image 
      : getFallbackImage(item.category);
    
    img.src = imageUrl;
    img.alt = item.title || 'Article image';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
      img.src = getFallbackImage(item.category);
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
      tag.textContent = ` • ${item.category.toUpperCase()}`;
      meta.appendChild(tag);
    }
    
    body.appendChild(meta);
    article.appendChild(body);
    
    return article;
  }
  
  /* ---------- Load Homepage ---------- */
  function loadHomepage() {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    
    if (!largeGrid || !listGrid) return;
    
    fetch(NEWS_FILE)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch news');
        return res.json();
      })
      .then(items => {
        if (!Array.isArray(items) || items.length === 0) {
          largeGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #6e6e73; padding: 60px 20px;">No news available yet. Run the RSS workflow to populate content.</p>';
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
        
        // Hide "View More" if less than 20 items
        const viewMoreBtn = document.getElementById('viewMoreBtn');
        if (viewMoreBtn && items.length <= 20) {
          viewMoreBtn.style.display = 'none';
        }
      })
      .catch(err => {
        console.error('Failed to load news:', err);
        largeGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #6e6e73; padding: 60px 20px;">Failed to load content. Please run the RSS workflow first.</p>';
      });
  }
  
  /* ---------- Load Category Page ---------- */
  function loadCategoryPage(category) {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    
    if (!largeGrid || !listGrid) return;
    
    fetch(NEWS_FILE)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch news');
        return res.json();
      })
      .then(items => {
        if (!Array.isArray(items)) {
          throw new Error('Invalid data format');
        }
        
        // Filter by category
        const filtered = items.filter(item => 
          item.category === category
        );
        
        if (filtered.length === 0) {
          largeGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #6e6e73; padding: 60px 20px;">No articles in this category yet. Check back soon!</p>';
          return;
        }
        
        // First 12 in large format
        filtered.slice(0, 12).forEach(item => {
          largeGrid.appendChild(renderLargeCard(item));
        });
        
        // Rest in list format
        filtered.slice(12).forEach(item => {
          listGrid.appendChild(renderListCard(item));
        });
        
        // DO NOT ADD COUNT TO HEADING - REMOVED THIS CODE
        // const heading = document.querySelector('.category-heading');
        // if (heading) {
        //   heading.textContent += ` (${filtered.length})`;
        // }
      })
      .catch(err => {
        console.error('Failed to load category:', err);
        largeGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #6e6e73; padding: 60px 20px;">Failed to load content. Please run the RSS workflow first.</p>';
      });
  }
  
  /* ---------- Mobile Navigation ---------- */
  function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const links = document.querySelector('.nav-links');
    
    if (toggle && links) {
      toggle.addEventListener('click', () => {
        links.classList.toggle('active');
      });
    }
  }
  
  /* ---------- Initialize ---------- */
  if (document.readyState !== 'loading') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }
  
  function init() {
    initMobileNav();
    
    // Determine page type and load accordingly
    const body = document.body;
    
    if (body.classList.contains('homepage')) {
      loadHomepage();
    } else if (body.dataset.category) {
      loadCategoryPage(body.dataset.category);
    }
  }
  
  // Export for category pages
  window.loadCategory = loadCategoryPage;
})();
