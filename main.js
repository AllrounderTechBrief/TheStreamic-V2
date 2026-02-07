/* =========================================================
   THE STREAMIC - Main JavaScript
   Tiered Bento Grid: Large cards (1-12), List cards (13-20)
========================================================= */

(() => {
  const NEWS_FILE = 'data/news.json';
  const ARCHIVE_FILE = 'data/archive.json';
  
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
    img.src = item.image || 'assets/fallback.jpg';
    img.alt = item.title || 'Article image';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
      img.src = 'assets/fallback.jpg';
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
      tag.textContent = item.category;
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
    img.src = item.image || 'assets/fallback.jpg';
    img.alt = item.title || 'Article image';
    img.loading = 'lazy';
    img.addEventListener('error', () => {
      img.src = 'assets/fallback.jpg';
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
      tag.textContent = `• ${item.category}`;
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
      .then(res => res.json())
      .then(items => {
        if (!Array.isArray(items)) return;
        
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
      .catch(err => console.error('Failed to load news:', err));
  }
  
  /* ---------- Load Category Page ---------- */
  function loadCategoryPage(category) {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    
    if (!largeGrid || !listGrid) return;
    
    fetch(NEWS_FILE)
      .then(res => res.json())
      .then(items => {
        if (!Array.isArray(items)) return;
        
        // Filter by category
        const filtered = items.filter(item => 
          item.category === category
        );
        
        // First 12 in large format
        filtered.slice(0, 12).forEach(item => {
          largeGrid.appendChild(renderLargeCard(item));
        });
        
        // Rest in list format
        filtered.slice(12).forEach(item => {
          listGrid.appendChild(renderListCard(item));
        });
        
        // Show count
        const heading = document.querySelector('.category-heading');
        if (heading) {
          heading.textContent += ` (${filtered.length})`;
        }
      })
      .catch(err => console.error('Failed to load category:', err));
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
