#!/bin/bash

create_page() {
  local page="$1"
  local title="$2"
  local desc="$3"
  local meta_desc="$4"
  
cat > "${page}.html" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="${meta_desc}">
  <meta name="keywords" content="${page}, broadcast technology, media infrastructure, professional video">
  <meta name="author" content="The Streamic">
  <link rel="canonical" href="https://allroundertechbrief.github.io/TheStreamic-V2/${page}.html">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://allroundertechbrief.github.io/TheStreamic-V2/${page}.html">
  <meta property="og:title" content="${title} - The Streamic">
  <meta property="og:description" content="${meta_desc}">
  <title>${title} - The Streamic | Broadcast Technology News</title>
  <link rel="stylesheet" href="style.css">
</head>
<body data-category="${page}">
  
  <nav class="site-nav">
    <div class="nav-inner">
      <a href="index.html" class="nav-logo">THE STREAMIC</a>
      <button class="nav-toggle" aria-label="Toggle menu">☰</button>
      <ul class="nav-links">
        <li><a href="newsroom.html">NEWSROOM</a></li>
        <li><a href="playout.html">PLAYOUT</a></li>
        <li><a href="infrastructure.html">INFRASTRUCTURE</a></li>
        <li><a href="graphics.html">GRAPHICS</a></li>
        <li><a href="cloud.html">CLOUD</a></li>
        <li><a href="streaming.html">STREAMING</a></li>
        <li><a href="audio-ai.html">AUDIO & AI</a></li>
      </ul>
    </div>
  </nav>

  <header class="page-hero">
    <div class="hero-inner">
      <h1 class="category-heading">${title}</h1>
      <p>${desc}</p>
    </div>
  </header>

  <main class="category-content">
    <div id="bentoGridLarge" class="bento-grid-large"></div>
    <div id="listGrid" class="list-grid"></div>
  </main>

  <footer class="site-footer">
    <div class="footer-content">
      <div class="footer-grid">
        <div class="foot-col">
          <h4>About</h4>
          <p>An independent resource for systems architects and media technologists tracking the evolution of broadcast infrastructure.</p>
          <p class="footer-tagline">Real-time insights. Industry-leading coverage.</p>
        </div>
        
        <div class="foot-col">
          <h4>Categories</h4>
          <a href="newsroom.html">Newsroom</a>
          <a href="playout.html">Playout</a>
          <a href="infrastructure.html">Infrastructure</a>
          <a href="graphics.html">Graphics</a>
          <a href="cloud.html">Cloud</a>
          <a href="streaming.html">Streaming</a>
          <a href="audio-ai.html">Audio & AI</a>
        </div>
        
        <div class="foot-col">
          <h4>Resources</h4>
          <a href="about.html">About Us</a>
          <a href="contact.html">Contact</a>
          <a href="vlog.html">Video Blog</a>
          <a href="terms.html">Terms of Service</a>
          <a href="privacy.html">Privacy Policy</a>
          <a href="rss-policy.html">RSS Policy</a>
        </div>
        
        <div class="foot-col">
          <h4>Connect</h4>
          <a href="https://twitter.com/thestreamic" target="_blank" rel="noopener">Twitter</a>
          <a href="https://linkedin.com/company/thestreamic" target="_blank" rel="noopener">LinkedIn</a>
          <a href="https://github.com/AllrounderTechBrief/TheStreamic-V2" target="_blank" rel="noopener">GitHub</a>
          <a href="mailto:info@thestreamic.in">Email Us</a>
        </div>
      </div>
      
      <div class="footer-bottom">
        <p class="footer-note">© 2026 The Streamic. All rights reserved.</p>
        <p class="footer-tech">Powered by RSS aggregation & smart content curation</p>
      </div>
    </div>
  </footer>

  <script src="main.js"></script>
</body>
</html>
EOF
}

create_page "playout" "Playout" "Master control, channel automation, and playout systems" "Latest playout automation, master control, and channel management technology for broadcast operations."

create_page "infrastructure" "Infrastructure" "IP networking, ST 2110, NDI, switching, and broadcast infrastructure" "Broadcast infrastructure news covering ST 2110, NDI, IP networking, and professional video transport."

create_page "graphics" "Graphics" "Broadcast graphics, virtual sets, AR/VR, and motion graphics systems" "Real-time broadcast graphics, virtual production, AR/VR technology, and motion design innovations."

create_page "cloud" "Cloud" "Cloud production, remote workflows, and virtualized infrastructure" "Cloud-based production workflows, remote collaboration, and virtualized broadcast infrastructure."

create_page "streaming" "Streaming" "OTT platforms, streaming protocols, CDN, and video delivery" "Streaming media technology, OTT platforms, CDN solutions, and online video delivery systems."

create_page "audio-ai" "Audio & AI" "Audio technology, Dante/AES67, and AI/ML in broadcast" "Professional audio technology, AoIP systems (Dante/AES67), and AI/ML applications in broadcasting."

echo "✅ All category pages created with complete footer structure!"
