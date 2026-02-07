/* =========================================================
   THE STREAMIC - Main JavaScript
   - Smart image fallbacks
   - Tiered Bento Layout (12 Large, 8 List)
   - Dynamic Navigation Highlights
========================================================= */

(() => {
  const NEWS_FILE = 'data/news.json';
  
  const CATEGORY_FALLBACKS = {
    'newsroom': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80',
    'playout': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80',
    'infrastructure': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80',
    'graphics': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80',
    'cloud': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
    'streaming': 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80',
    'audio-ai': 'https://images.unsplash.com/photo-1557800636-894a64c1696f?w=800&q=80'
  };

  function renderLargeCard(item) {
    const fallback = CATEGORY_FALLBACKS[item.category] || CATEGORY_FALLBACKS['newsroom'];
    const displayImg = (item.image && item.image.startsWith('http')) ? item.image : fallback;

    const card = document.createElement('a');
    card.className = 'bento-card-large';
    card.href = item.link;
    card.target = '_blank';
    card.innerHTML = `
      <div class="card-image">
        <img src="${displayImg}" alt="News" onerror="this.src='${fallback}'">
      </div>
      <div class="card-body">
        <div class="card-meta">${item.source || 'BROADCAST HUB'}</div>
        <h3>${item.title}</h3>
      </div>
    `;
    return card;
  }

  function renderListItem(item) {
    const link = document.createElement('a');
    link.className = 'list-item';
    link.href = item.link;
    link.target = '_blank';
    link.innerHTML = `
      <h4>${item.title}</h4>
      <span class="card-meta">${item.source}</span>
    `;
    return link;
  }

  function loadCategoryPage(category) {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    
    if (!largeGrid) return;

    fetch(NEWS_FILE)
      .then(res => res.json())
      .then(data => {
        const filtered = data.filter(i => i.category === category);
        
        largeGrid.innerHTML = '';
        if (listGrid) listGrid.innerHTML = '';

        // Cards 1-12 go into the Bento Grid
        filtered.slice(0, 12).forEach(item => {
          largeGrid.appendChild(renderLargeCard(item));
        });

        // Cards 13-20 go into the List Grid
        if (listGrid && filtered.length > 12) {
          filtered.slice(12, 20).forEach(item => {
            listGrid.appendChild(renderListItem(item));
          });
        }
      })
      .catch(err => console.error("Could not load news:", err));
  }

  function init() {
    // 1. Highlight the current active link in navigation
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(link => {
      if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
      }
    });

    // 2. Load content based on body data-category
    const category = document.body.dataset.category;
    if (category) {
      loadCategoryPage(category);
    }
    
    // 3. Mobile Nav Toggle
    const toggle = document.querySelector('.nav-toggle');
    const nav = document.querySelector('.nav-links');
    if (toggle) {
      toggle.addEventListener('click', () => {
        nav.style.display = nav.style.display === 'flex' ? 'none' : 'flex';
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
