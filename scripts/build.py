"""
scripts/build.py  —  The Streamic site builder (zero-LLM edition)
Reads data/generated_articles.json, writes all docs/ output.
No Groq, no paid APIs, no external calls during build.
"""

import json, os, shutil
from datetime import datetime, timezone

ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTICLES_F = os.path.join(ROOT, "data", "generated_articles.json")
DOCS       = os.path.join(ROOT, "docs")
ARTS_D     = os.path.join(DOCS, "articles")
BASE_URL   = os.environ.get("SITE_BASE_URL", "https://www.thestreamic.in").rstrip("/")
PAGE_SIZE           = 24    # cards per category page
SHOW_SOURCE_ON_CARD = False # hide external source labels for AdSense review

CAT_META = {
    "featured":           {"label":"Featured",            "icon":"⭐", "color":"#1d1d1f","page":"featured.html"},
    "streaming":          {"label":"Streaming",           "icon":"📡", "color":"#0071e3","page":"streaming.html"},
    "cloud":              {"label":"Cloud Production",    "icon":"☁️", "color":"#5856d6","page":"cloud.html"},
    "graphics":           {"label":"Graphics",            "icon":"🎨", "color":"#FF9500","page":"graphics.html"},
    "playout":            {"label":"Playout",             "icon":"▶️", "color":"#34C759","page":"playout.html"},
    "infrastructure":     {"label":"Infrastructure",      "icon":"🏗️", "color":"#8E8E93","page":"infrastructure.html"},
    "ai-post-production": {"label":"AI & Post-Production","icon":"🎬", "color":"#FF2D55","page":"ai-post-production.html"},
    "newsroom":           {"label":"Newsroom",            "icon":"📰", "color":"#D4AF37","page":"newsroom.html"},
}
GA_TAG     = "G-0VSHDN3ZR6"
ADS_ID     = "ca-pub-8033069131874524"
AUTHOR     = "The Streamic Editorial Team"

CAT_DESC = {
    "featured":           "Independent broadcast and streaming technology journalism. Original analysis and expert commentary for media professionals.",
    "streaming":          "OTT platforms, video encoding, CDN infrastructure, live streaming workflows, and streaming technology innovation coverage.",
    "cloud":              "Cloud-native broadcast production, remote workflows, REMI architecture, and cloud playout technology for media operations.",
    "graphics":           "Real-time graphics, virtual sets, motion design, data-driven visuals, and broadcast graphics technology developments.",
    "playout":            "Channel playout, master control, broadcast automation, channel-in-a-box, and transmission technology for broadcast operations.",
    "infrastructure":     "SMPTE ST 2110, IP routing, network infrastructure, storage systems, and broadcast facility technology.",
    "ai-post-production": "AI-driven editing tools, automated QC, intelligent MAM, colour grading, and post-production technology advances.",
    "newsroom":           "NRCS systems, remote journalism technology, newsroom workflow automation, and news production infrastructure.",
}
CAT_H2 = {
    "featured": "&#11088; Featured Stories",
    "streaming": "&#128225; Latest Streaming Technology",
    "cloud": "&#9729;&#65039; Cloud Production News",
    "graphics": "&#127912; Graphics Technology",
    "playout": "&#9654;&#65039; Playout &amp; Automation",
    "infrastructure": "&#127959;&#65039; Infrastructure &amp; IP",
    "ai-post-production": "&#127916; AI &amp; Post-Production",
    "newsroom": "&#128240; Newsroom Technology",
}



# ── Groq summary loader (data/summaries/<slug>.json → applied during build) ──
_SUMMARIES_CACHE: dict = {}

def _load_summary(slug: str) -> dict:
    """Load Groq-generated summary if it exists; returns empty dict otherwise."""
    if slug in _SUMMARIES_CACHE:
        return _SUMMARIES_CACHE[slug]
    path = os.path.join(ROOT, "data", "summaries", f"{slug}.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as _f:
                data = json.load(_f)
                _SUMMARIES_CACHE[slug] = data
                return data
        except Exception:
            pass
    _SUMMARIES_CACHE[slug] = {}
    return {}

def enrich_with_summary(a: dict) -> dict:
    """Return enriched article dict with Groq summary applied if available."""
    s = _load_summary(a.get("slug", ""))
    if not s:
        return a
    enriched = dict(a)
    if s.get("card_summary"):
        enriched["card_summary"] = s["card_summary"]
    if s.get("body_html"):
        enriched["body_html"]    = s["body_html"]
    if s.get("word_count"):
        enriched["word_count"]   = s["word_count"]
    return enriched


def e(s): return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
def d(iso):
    try: return datetime.strptime(iso,"%Y-%m-%d").strftime("%B %d, %Y")
    except: return iso
def w(path, txt):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",encoding="utf-8") as f: f.write(txt)

def read_time(wc):
    mins = max(1, round(wc / 200))
    return f"{mins} min read"

# ── Topic-relevant Unsplash image pool (CC0 / Unsplash License) ──────────
_IMG_USED: set = set()
_KEYWORD_POOLS = [
    (['smpte','ip routing','nmos','infrastructure','network','fiber','ethernet','rack'],
     ['photo-1558494949-ef010cbdcc31','photo-1545987796-200677ee1011','photo-1451187580459-43490279c0fa',
      'photo-1544197150-b99a580bb7a8','photo-1558618666-fcd25c85cd64']),
    (['artificial intelligence','ai-powered','machine learning','neural','generative ai','automation'],
     ['photo-1677442135703-1787eea5ce01','photo-1620712943543-bcc4688e7485','photo-1655635643532-fa9ba2648cbe',
      'photo-1635070041078-e363dbe005cb','photo-1655635949212-1d8f4f103ea1']),
    (['broadcast camera','cinema camera','camera','lens','4k','8k','sensor'],
     ['photo-1516035069371-29a1b244cc32','photo-1574717024653-61fd2cf4d44d','photo-1605116868827-a9e8b3028b99',
      'photo-1551269901-5c2d5b2e3b24','photo-1567095761054-7003afd47020']),
    (['cloud production','cloud storage','cloud','aws','azure','saas','data center'],
     ['photo-1531297484001-80022131f5a1','photo-1488229297570-58520851e868',
      'photo-1573164713988-8665fc963095','photo-1580584126903-c17d41830450','photo-1544197150-b99a580bb7a8']),
    (['streaming','ott','vod','hls','low latency','delivery','cdn'],
     ['photo-1616401784845-180882ba9ba8','photo-1611532736597-de2d4265fba3',
      'photo-1593642632559-0c6d3fc62b89','photo-1574717025058-97e3af4ef9b5','photo-1492619375914-88005aa9e8fb']),
    (['encoder','encoding','transcod','codec','hevc','av1','mpeg'],
     ['photo-1574717024653-61fd2cf4d44d','photo-1504384308090-c894fdcc538d',
      'photo-1518770660439-4636190af475','photo-1560472354-b33ff0c44a43','photo-1598488035139-bdbb2231ce04']),
    (['graphics','motion graphics','virtual set','ar','augmented reality','lower third'],
     ['photo-1504639725590-34d0984388bd','photo-1547658719-da2b51169166','photo-1518770660439-4636190af475',
      'photo-1561736778-92e52a7769ef','photo-1634153821015-5a2cc1b70bba']),
    (['playout','master control','automation','channel in a box','ciab','on-air','transmission'],
     ['photo-1478737270239-2f02b77fc618','photo-1590602847861-f357a9332bbc','photo-1612420696760-0a0f34d3e7d0',
      'photo-1525059696034-4967a8e1dca2','photo-1461749280684-dccba630e2f6']),
    (['newsroom','nrcs','news production','journalist','reporter','anchor'],
     ['photo-1504711434969-e33886168f5c','photo-1493863641943-9b68992a8d07','photo-1585829365295-ab7cd400c167',
      'photo-1557804506-669a67965ba0','photo-1432821596592-e2c18b78144f']),
    (['post-production','editing','nle','davinci','premiere','media composer','avid'],
     ['photo-1572044162444-ad60f128bdea','photo-1605106702734-205df224ecce',
      'photo-1574717025058-97e3af4ef9b5','photo-1489875347897-49f64b51c1f8','photo-1605116868827-a9e8b3028b99']),
    (['audio','mixer','console','lawo','calrec','dolby','spatial audio'],
     ['photo-1511379938547-c1f69419868d','photo-1598520106830-8c45c2035460',
      'photo-1471478331149-c72f17e33c73','photo-1520523839897-bd0b52f945a0','photo-1516321165247-4aa89a48be55']),
    (['wireless','5g','satellite','uplink','rf','cellular'],
     ['photo-1526374965328-7f61d4dc18c5','photo-1581092583537-20d51b4b4f1b',
      'photo-1598520106830-8c45c2035460','photo-1605196560547-b2f7281b7355','photo-1558618666-fcd25c85cd64']),
    (['storage','nas','archive','lto','mam','media asset'],
     ['photo-1560472354-b33ff0c44a43','photo-1497366216548-37526070297c',
      'photo-1465343161283-c1959138ddaa','photo-1504384308090-c894fdcc538d','photo-1620714223084-8fcacc2386f7']),
    (['live event','live sports','ob van','outside broadcast','stadium','esports'],
     ['photo-1560272564-c83b66b1ad12','photo-1471295253337-3ceaaedca402',
      'photo-1492619375914-88005aa9e8fb','photo-1540747913346-19212a4a3bdf','photo-1574629810360-7efbbe195018']),
    (['nab show','nab 2026','ibc show','ibc 2026','trade show','expo'],
     ['photo-1540575467063-178a50c2df87','photo-1568992687947-868a62a9f521',
      'photo-1505373877841-8d25f7d46678','photo-1497366754035-f200968a6e72','photo-1492619375914-88005aa9e8fb']),
    (['appoints','appoint','ceo','chief','vp ','director','joins','funding','investment'],
     ['photo-1507679799987-c73779587ccf','photo-1553877522-43269d4ea984','photo-1573496359142-b8d87734a5a2',
      'photo-1560250097-0b93528c311a','photo-1600880292203-757bb62b4baf']),
]
_CAT_IMG_POOLS = {
    'streaming':         ['photo-1616401784845-180882ba9ba8','photo-1611532736597-de2d4265fba3',
                          'photo-1574717025058-97e3af4ef9b5','photo-1492619375914-88005aa9e8fb',
                          'photo-1593642632559-0c6d3fc62b89','photo-1520523839897-bd0b52f945a0'],
    'cloud':             ['photo-1531297484001-80022131f5a1','photo-1488229297570-58520851e868',
                          'photo-1573164713988-8665fc963095','photo-1580584126903-c17d41830450',
                          'photo-1544197150-b99a580bb7a8','photo-1451187580459-43490279c0fa'],
    'ai-post-production':['photo-1677442135703-1787eea5ce01','photo-1620712943543-bcc4688e7485',
                          'photo-1572044162444-ad60f128bdea','photo-1605106702734-205df224ecce',
                          'photo-1574717025058-97e3af4ef9b5','photo-1655635643532-fa9ba2648cbe'],
    'graphics':          ['photo-1504639725590-34d0984388bd','photo-1547658719-da2b51169166',
                          'photo-1518770660439-4636190af475','photo-1561736778-92e52a7769ef',
                          'photo-1634153821015-5a2cc1b70bba','photo-1593642632559-0c6d3fc62b89'],
    'playout':           ['photo-1478737270239-2f02b77fc618','photo-1590602847861-f357a9332bbc',
                          'photo-1612420696760-0a0f34d3e7d0','photo-1525059696034-4967a8e1dca2',
                          'photo-1461749280684-dccba630e2f6','photo-1526374965328-7f61d4dc18c5'],
    'infrastructure':    ['photo-1558494949-ef010cbdcc31','photo-1545987796-200677ee1011',
                          'photo-1451187580459-43490279c0fa','photo-1558618666-fcd25c85cd64',
                          'photo-1544197150-b99a580bb7a8','photo-1504384308090-c894fdcc538d'],
    'newsroom':          ['photo-1504711434969-e33886168f5c','photo-1493863641943-9b68992a8d07',
                          'photo-1585829365295-ab7cd400c167','photo-1557804506-669a67965ba0',
                          'photo-1432821596592-e2c18b78144f','photo-1503428593586-e225b39bddfe'],
    'featured':          ['photo-1598488035139-bdbb2231ce04','photo-1530026405186-ed1f139313f8',
                          'photo-1574717024653-61fd2cf4d44d','photo-1516321165247-4aa89a48be55',
                          'photo-1525059696034-4967a8e1dca2','photo-1490645935967-10de6ba17061'],
}

def topic_image(title: str, cat_slug: str, seed: str = '') -> str:
    """Return a unique, topic-relevant Unsplash URL (CC0 / Unsplash License)."""
    import hashlib as _hl
    tl = title.lower()
    for kws, pids in _KEYWORD_POOLS:
        if any(kw in tl for kw in kws):
            for pid in pids:
                if pid not in _IMG_USED:
                    _IMG_USED.add(pid); return f'https://images.unsplash.com/{pid}?w=800&auto=format&fit=crop'
    pool = _CAT_IMG_POOLS.get(cat_slug, _CAT_IMG_POOLS['featured'])
    for pid in pool:
        if pid not in _IMG_USED:
            _IMG_USED.add(pid); return f'https://images.unsplash.com/{pid}?w=800&auto=format&fit=crop'
    all_pids = [p for _,ps in _KEYWORD_POOLS for p in ps]
    idx = int(_hl.md5((seed+title).encode()).hexdigest(), 16) % len(all_pids)
    pid = all_pids[idx]; _IMG_USED.add(pid)
    return f'https://images.unsplash.com/{pid}?w=800&auto=format&fit=crop'



CONSENT = f"""<script>
    window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
    gtag('consent','default',{{'analytics_storage':'denied','ad_storage':'denied','ad_user_data':'denied','ad_personalization':'denied','wait_for_update':500}});
  </script>
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_TAG}"></script>
  <script>gtag('js',new Date());gtag('config','{GA_TAG}');</script>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS_ID}" crossorigin="anonymous"></script>"""


# ── GDPR Cookie Consent Banner ──────────────────────────────────────────────
_COOKIE_BANNER = '''
<div id="ts-cookie-banner" style="display:none;position:fixed;bottom:0;left:0;right:0;z-index:99999;
  background:#1d1d1f;color:#fff;padding:16px 24px;
  box-shadow:0 -4px 20px rgba(0,0,0,.3);font-size:13px;line-height:1.5;">
  <div style="max-width:1400px;margin:0 auto;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
    <div style="flex:1;min-width:260px;">
      <strong style="font-size:14px;">We use cookies</strong>
      <p style="margin:4px 0 0;color:rgba(255,255,255,.7);">
        We use analytics and advertising cookies to improve your experience.
        <a href="/privacy.html" style="color:#FFD700;">Privacy Policy</a>
      </p>
    </div>
    <div style="display:flex;gap:10px;flex-shrink:0;">
      <button onclick="tsCC(false)"
        style="padding:9px 20px;border-radius:8px;border:1px solid rgba(255,255,255,.3);
        background:transparent;color:#fff;font-size:13px;font-weight:600;cursor:pointer;">
        Reject optional</button>
      <button onclick="tsCC(true)"
        style="padding:9px 20px;border-radius:8px;border:none;
        background:#FFD700;color:#000;font-size:13px;font-weight:700;cursor:pointer;">
        Accept all</button>
    </div>
  </div>
</div>
<script>
(function(){
  var K="ts_cc",s=localStorage.getItem(K),b=document.getElementById("ts-cookie-banner");
  if(!s&&b){b.style.display="block";}
  window.tsCC=function(ok){
    localStorage.setItem(K,ok?"granted":"denied");
    if(b)b.style.display="none";
    if(typeof gtag!="undefined"){
      gtag("consent","update",{analytics_storage:ok?"granted":"denied",
        ad_storage:ok?"granted":"denied",ad_user_data:ok?"granted":"denied",
        ad_personalization:ok?"granted":"denied"});
    }
  };
  if(s==="granted"&&typeof gtag!="undefined"){
    gtag("consent","update",{analytics_storage:"granted",ad_storage:"granted",
      ad_user_data:"granted",ad_personalization:"granted"});
  }
})();
</script>
'''

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@300;400;600;700&display=swap" rel="stylesheet">'


def head(title, desc, canon, css_rel, og_img=""):
    og = f'  <meta property="og:image" content="{e(og_img)}">\n' if og_img else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  {CONSENT}
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}">
  <meta name="robots" content="index, follow">
  <meta name="author" content="{AUTHOR}">
  <link rel="canonical" href="{e(canon)}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="The Streamic">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:url" content="{e(canon)}">
{og}  <meta name="twitter:card" content="summary_large_image">
  {FONTS}
  <link rel="stylesheet" href="{css_rel}">
</head>
{_COOKIE_BANNER}"""


def nav(active="", base=""):
    pages = [
        ("featured.html","FEATURED"),("infrastructure.html","INFRASTRUCTURE"),
        ("graphics.html","GRAPHICS"),("cloud.html","CLOUD PRODUCTION"),
        ("streaming.html","STREAMING"),("ai-post-production.html","AI &amp; POST-PRODUCTION"),
        ("playout.html","PLAYOUT"),("newsroom.html","NEWSROOM"),("howto.html","HOW-TO"),
    ]
    lis = "".join(
        '        <li><a href="' + base + h + '"' + (' class="active"' if h==active else '') + '>' + lbl + '</a></li>\n'
        for h,lbl in pages)
    return f"""  <nav class="site-nav">
    <div class="nav-inner">
      <a href="{base}featured.html" class="nav-logo-container">
        <img src="{base}assets/logo.png" alt="The Streamic Logo" class="nav-logo-image"
             onload="this.closest('.nav-logo-container').classList.add('logo-loaded')">
        <span class="nav-logo">THE STREAMIC</span>
      </a>
      <button class="nav-toggle" aria-label="Toggle menu">&#9776;</button>
      <ul class="nav-links">
{lis}      </ul>
      <div class="header-subscribe"><a href="{base}vlog.html" class="editors-desk-link">Editor's Desk</a></div>
    </div>
  </nav>"""


def footer(base=""):
    yr = datetime.now(timezone.utc).year
    return f"""  <footer class="site-footer">
    <div class="footer-inner">
      <div>
        <div class="footer-brand">THE STREAMIC</div>
        <p>An independent broadcast and streaming technology publication. Covering streaming, cloud production, AI post-production, graphics, playout, infrastructure, and newsroom technology.</p>
      </div>
      <div class="footer-col">
        <h4>Categories</h4>
        <a href="{base}featured.html">Featured</a><a href="{base}streaming.html">Streaming</a>
        <a href="{base}cloud.html">Cloud Production</a><a href="{base}ai-post-production.html">AI &amp; Post-Production</a>
        <a href="{base}graphics.html">Graphics</a><a href="{base}playout.html">Playout</a>
        <a href="{base}infrastructure.html">Infrastructure</a><a href="{base}newsroom.html">Newsroom</a>
      </div>
      <div class="footer-col">
        <h4>Site Info</h4>
        <a href="{base}about.html">About</a><a href="{base}contact.html">Contact</a>
        <a href="{base}vlog.html">Editor's Desk</a><a href="{base}privacy.html">Privacy Policy</a>
        <a href="{base}terms.html">Terms of Use</a>
      </div>
    </div>
    <div class="footer-bottom">
      <span>&copy; {yr} The Streamic &mdash; thestreamic.in. All rights reserved.</span>
      <span>Independent broadcast technology journalism. Trademarks belong to their respective owners.</span>
    </div>
  </footer>
  <script>(function(){{var t=document.querySelector('.nav-toggle'),n=document.querySelector('.nav-links');if(!t||!n)return;t.addEventListener('click',function(){{n.classList.toggle('nav-open');}});}})();</script>"""



def horiz_card(a, base=""):
    """
    TVBEurope-style single featured card:
    image left (~38%), text right — compact, editorial.
    Only used for the #1 article on each category page.
    """
    href     = f"{base}articles/{a['slug']}.html"
    fallback = f"{base}assets/fallback.jpg"
    img_url  = e(a.get("image_url",""))
    title    = e(a.get("title",""))
    cat_col  = a.get("cat_color","#0071e3")
    cat_icon = a.get("cat_icon","")
    cat_label= e(a.get("cat_label",""))
    date_str = d(a.get("published",""))
    rt       = read_time(a.get("word_count",600))
    summary  = e((a.get("card_summary") or a.get("dek") or a.get("meta_description",""))[:280])

    img_html = f'''<a href="{href}" class="hc-img-link" tabindex="-1" aria-hidden="true">
      <img src="{img_url}" alt="{title}" loading="lazy"
           onerror="this.src=\'{fallback}\'">
    </a>''' if img_url else f'''<a href="{href}" class="hc-img-link hc-img-placeholder">
      <span>The Streamic</span></a>'''

    return f"""  <article class="hc-article">
    {img_html}
    <div class="hc-body">
      <div class="hc-meta-row">
        <a class="hc-badge" href="{base}{a.get('cat_page','featured.html')}" style="background:{cat_col};" tabindex="-1">{cat_icon} {cat_label}</a>
        <span class="hc-date">{date_str}</span>
      </div>
      <h2 class="hc-title"><a href="{href}">{title}</a></h2>
      <p class="hc-summary">{summary}</p>
      <div class="hc-footer">
        <a href="{href}" class="hc-read">Read full article &rarr;</a>
        <span class="hc-rt">{rt}</span>
      </div>
    </div>
  </article>"""


def card(a, base="", num=0):
    """
    TheTechBrief-style card:
    [image with number badge] / [badge • cat name] / [title] /
    [summary] / [KEY INSIGHT box] / [Read link | date]
    """
    href     = f"{base}articles/{a['slug']}.html"
    fallback = f"{base}assets/fallback.jpg"
    img_url  = e(a.get("image_url", ""))
    title    = e(a.get("title", ""))
    cat_col  = a.get("cat_color", "#0071e3")
    cat_icon = a.get("cat_icon", "")
    cat_label= e(a.get("cat_label", ""))
    date_str = d(a.get("published", ""))
    rt       = read_time(a.get("word_count", 600))
    # Prefer card_summary; fallback to dek / meta_description
    summary  = e((a.get("card_summary") or a.get("dek") or a.get("meta_description",""))[:300])
    # Key insight: first 100 chars of summary as pull-quote
    insight  = e((a.get("card_summary") or a.get("dek") or a.get("meta_description",""))[:120])
    num_html = f'<span class="ts-card-num">{num:02d}</span>' if num else ""

    if img_url:
        img_html = f'''<div class="ts-card-img-wrap">
        <img src="{img_url}" alt="{title}" loading="lazy"
             onerror="this.src=\'{fallback}\'">
        {num_html}
      </div>'''
    else:
        img_html = f'''<div class="ts-card-img-wrap ts-card-img-placeholder">
        {num_html}
        <span>The Streamic</span>
      </div>'''

    return f"""      <article class="ts-card">
        <a href="{href}" style="text-decoration:none;color:inherit;">
          {img_html}
        </a>
        <div class="ts-card-body">
          <div class="ts-card-meta">
            <span class="ts-card-badge" style="background:{cat_col};">{cat_icon} {cat_label}</span>
            <span class="ts-card-cat-name">{cat_label}</span>
          </div>
          <div class="ts-card-title"><a href="{href}">{title}</a></div>
          <div class="ts-card-summary">{summary}</div>
          <div class="ts-card-insight">
            <span class="ts-card-insight-label">Key Insight</span>
            {insight}
          </div>
          <div class="ts-card-footer">
            <a href="{href}" class="ts-card-read">Read full article
              <svg viewBox="0 0 12 12"><path d="M1 6h10M6 1l5 5-5 5"/></svg>
            </a>
            <span class="ts-card-date">{date_str}</span>
          </div>
        </div>
      </article>"""


def article_page(a):
    slug    = a["slug"]
    url     = f"{BASE_URL}/articles/{slug}.html"
    wc      = a.get("word_count", 800)
    rm      = max(1, round(wc/200))
    color   = a["cat_color"]
    schema  = json.dumps({
        "@context":"https://schema.org","@type":"NewsArticle",
        "headline":a["title"],"description":a["meta_description"],
        "image":a["image_url"],"datePublished":a["published"],"dateModified":a["published"],
        "author":{"@type":"Organization","name":AUTHOR},
        "publisher":{"@type":"Organization","name":"The Streamic","url":BASE_URL,
                     "logo":{"@type":"ImageObject","url":f"{BASE_URL}/assets/logo.png"}},
        "mainEntityOfPage":url,"articleSection":a["cat_label"],"wordCount":wc,
    }, indent=2)
    return f"""{head(e(a['title'])+" | The Streamic", a['meta_description'], url, "../style.css", a['image_url'])}
<body>
{nav(a['cat_page'], base="../")}
  <main>
    <div style="max-width:760px;margin:0 auto;padding:40px 24px 80px;">
      <div style="font-size:13px;color:#86868b;margin-bottom:10px;">
        <a href="../featured.html" style="color:#86868b;text-decoration:none;">Home</a> &rsaquo;
        <a href="../{a['cat_page']}" style="color:{color};font-weight:600;text-decoration:none;">{e(a['cat_label'])}</a>
      </div>
      <a href="../{a['cat_page']}" style="display:inline-block;background:{color};color:#fff;padding:4px 14px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:14px;text-decoration:none;">{a['cat_icon']} {e(a['cat_label'])}</a>
      <h1 style="font-family:Montserrat,sans-serif;font-size:clamp(22px,4vw,36px);font-weight:700;line-height:1.2;margin-bottom:10px;color:#1d1d1f;">{e(a['title'])}</h1>
      <p style="font-size:17px;color:#424245;line-height:1.6;margin-bottom:16px;">{e(a['dek'])}</p>
      <div style="font-size:13px;color:#86868b;margin-bottom:24px;padding-bottom:14px;border-bottom:1px solid #d2d2d7;display:flex;gap:14px;flex-wrap:wrap;">
        <span>By <strong style="color:#1d1d1f;">{AUTHOR}</strong></span>
        <span><time datetime="{a['published']}">{d(a['published'])}</time></span>
        <span>{wc} words &middot; {rm} min read</span>
      </div>
      <figure style="margin:0 0 28px 0;">
        <img src="{e(a['image_url'])}" alt="{e(a['title'])}" loading="eager"
             style="width:100%;max-height:420px;object-fit:cover;border-radius:12px;display:block;">
        <figcaption style="font-size:11px;color:#86868b;margin-top:6px;text-align:center;">
          {e(a['image_credit'])} &mdash;
          <a href="{e(a['image_license_url'])}" rel="nofollow noopener" target="_blank" style="color:#86868b;">{e(a['image_license'])}</a>
        </figcaption>
      </figure>
      <div style="margin:0 0 24px 0;">
        <ins class="adsbygoogle" style="display:block" data-ad-client="{ADS_ID}" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>
        <script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script>
      </div>
      <div style="font-size:16px;line-height:1.78;color:#1d1d1f;">
        {a['body_html']}
      </div>
      <div style="margin:24px 0 0 0;">
        <ins class="adsbygoogle" style="display:block" data-ad-client="{ADS_ID}" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>
        <script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script>
      </div>
      <div style="margin-top:32px;padding:14px 18px;background:#f5f5f7;border-radius:8px;font-size:13px;color:#86868b;">
        <strong style="color:#1d1d1f;">Editorial Note:</strong>
        Original commentary by The Streamic on broadcast and streaming technology.
        <a href="../about.html" style="color:{color};margin-left:6px;">About The Streamic &#8594;</a>
      </div>
      <div style="border-top:1px solid #d2d2d7;margin-top:40px;padding-top:20px;">
        <h3 style="font-family:Montserrat,sans-serif;font-size:17px;font-weight:700;margin-bottom:12px;">Continue Reading</h3>
        <a href="../{a['cat_page']}" style="display:block;padding:8px 0;border-bottom:1px solid #f5f5f7;color:{color};font-size:14px;text-decoration:none;">{a['cat_icon']} All {e(a['cat_label'])} Coverage</a>
        <a href="../featured.html" style="display:block;padding:8px 0;color:{color};font-size:14px;text-decoration:none;">&#11088; Featured Stories</a>
      </div>
    </div>
  </main>
  <script type="application/ld+json">{schema}</script>
{footer(base="../")}
</body>
</html>"""


def _load_rss_stubs(cat_slug: str) -> list:
    """Load existing rss-*.html stubs for a category to populate card grid."""
    import re as _re, os as _os
    BADGE_COLORS = {
        'streaming':'#0071e3','cloud':'#5856d6','ai-post-production':'#FF2D55',
        'graphics':'#FF9500','playout':'#34C759','infrastructure':'#8E8E93',
        'newsroom':'#D4AF37','featured':'#1d1d1f'
    }
    BADGE_ICONS = {
        'streaming':'📡','cloud':'☁️','ai-post-production':'🎬',
        'graphics':'🎨','playout':'▶️','infrastructure':'🏗️',
        'newsroom':'📰','featured':'⭐'
    }
    docs_arts = _os.path.join(DOCS, "articles")
    if not _os.path.isdir(docs_arts): return []
    stubs = []
    for fname in sorted(_os.listdir(docs_arts)):
        if not fname.startswith("rss-") or not fname.endswith(".html"): continue
        try:
            with open(_os.path.join(docs_arts, fname), encoding="utf-8") as _f:
                html = _f.read()
        except Exception: continue
        # category check
        cat_m = _re.search(r'href="\.\./([^.]+)\.html" style="color', html)
        if not cat_m or cat_m.group(1) != cat_slug: continue
        # title
        tm = _re.search(r'<title>([^|<]+)', html)
        title = tm.group(1).strip() if tm else fname
        if "Broadcast Technology Update" in title: continue  # skip generic stubs
        # summary — use meta description (real RSS teaser was stored there)
        dm = _re.search(r'<meta name="description" content="([^"]+)"', html)
        summary = dm.group(1) if dm else ""
        # image — already Unsplash from previous builds
        im = _re.search(r'<meta property="og:image" content="([^"]+)"', html)
        image = im.group(1) if im else ""
        if not image or "thestreamic" in image: continue
        # date
        dtm = _re.search(r'<time datetime="([^"]+)"', html)
        pub = dtm.group(1)[:10] if dtm else "2026-03-01"
        wc_m = _re.search(r'(\d+) words', html[:2000])
        wc = int(wc_m.group(1)) if wc_m else 250
        stubs.append({
            "cat_label": cat_slug.replace("-"," ").title(),  # icon added by card() separately
            "cat_color": BADGE_COLORS.get(cat_slug,"#0071e3"),
            "cat_icon":  BADGE_ICONS.get(cat_slug,"📡"),
            "category":  cat_slug,
            "title":     title,
            "slug":      fname[:-5],      # rss-xxxx (no .html)
            "legacy_slug": fname[:-5],
            "meta_description": summary,
            "image_url": image,
            "word_count": wc,
            "source_domain": "",
            "published": pub,
        })
    return stubs

def _pagination_html(cat, page, total_pages, base=""):
    """Generate prev/next pagination links."""
    links = []
    if page > 0:
        prev_file = f"{cat}.html" if page == 1 else f"{cat}-p{page}.html"
        links.append(f'<a href="{base}{prev_file}" class="pag-link">&larr; Newer</a>')
    else:
        links.append('<span class="pag-link pag-disabled">&larr; Newer</span>')
    links.append(f'<span class="pag-info">Page {page+1} of {total_pages}</span>')
    if page < total_pages - 1:
        next_file = f"{cat}-p{page+2}.html"
        links.append(f'<a href="{base}{next_file}" class="pag-link">Older &rarr;</a>')
    else:
        links.append('<span class="pag-link pag-disabled">Older &rarr;</span>')
    return f'<div class="pag-bar">{"&nbsp;".join(links)}</div>'


def category_page(cat, arts):
    """Build category page(s) with pagination at PAGE_SIZE cards each."""
    # Merge generated articles + RSS stubs
    all_arts = list(arts)
    stub_slugs = {a["slug"] for a in all_arts}
    for stub in _load_rss_stubs(cat):
        if stub["slug"] not in stub_slugs:
            all_arts.append(stub)
            stub_slugs.add(stub["slug"])
    all_arts.sort(key=lambda a: a["published"], reverse=True)

    cm = CAT_META.get(cat, {})
    title_base = f"{cm.get('label', cat.title())} — The Streamic" if cm else f"{cat.title()} — The Streamic"
    desc  = CAT_DESC.get(cat, "Broadcast technology coverage from The Streamic.")
    h2    = CAT_H2.get(cat, cat.title())

    total = len(all_arts)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    pages_html = []

    for page in range(total_pages):
        slice_arts = all_arts[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        # First article: TVBEurope-style magazine card; rest: numbered grid
        first  = slice_arts[:1]
        rest   = slice_arts[1:]
        horiz_html = horiz_card(first[0]) if first else ""
        grid_html  = "\n".join(card(a, num=i+2) for i, a in enumerate(rest))
        if rest:
            cards_html = f'<div class="hc-featured-wrap">{horiz_html}</div>\n<div class="news-grid">{grid_html}</div>'
        else:
            cards_html = f'<div class="hc-featured-wrap">{horiz_html}</div>'
        pag = _pagination_html(cat, page, total_pages) if total_pages > 1 else ""
        out_html = f"""{head(title_base, desc, f"{BASE_URL}/{cat}.html", "style.css")}
<body>
{nav(f"{cat}.html")}
  <main>
    <div class="page-wrap">
      <div class="page-section">
        <div class="section-hdr"><h2>{h2}</h2></div>
{cards_html}
        {pag}
      </div>
    </div>
  </main>
{footer()}
</body>
</html>"""
        pages_html.append((page, out_html))
    return pages_html  # list of (page_num, html)


def index_page(arts):
    """Full homepage — no redirect. Hero + category strips + latest grid."""
    latest  = sorted(arts, key=lambda a: a["published"], reverse=True)[:18]
    title   = "The Streamic — Independent Broadcast & Streaming Technology News"
    desc    = ("Expert analysis and original editorial on streaming, cloud production, "
               "AI post-production, graphics, playout, infrastructure, and newsroom technology.")
    canon   = f"{BASE_URL}/index.html"

    # Build one featured hero card from the most-recent article
    hero_a  = latest[0] if latest else None
    hero_html = ""
    if hero_a:
        hero_html = f"""  <section class="ts-hero">
    <div class="ts-hero-inner">
      <div class="ts-hero-img-wrap">
        <img src="{e(hero_a['image_url'])}" alt="{e(hero_a['title'])}" loading="eager">
        <span class="nc-pill" style="background:{hero_a['cat_color']};">{hero_a['cat_icon']} {e(hero_a['cat_label'])}</span>
      </div>
      <div class="ts-hero-body">
        <p class="ts-hero-eyebrow">Editor's Pick &mdash; {d(hero_a['published'])}</p>
        <h2 class="ts-hero-title"><a href="articles/{hero_a['slug']}.html">{e(hero_a['title'])}</a></h2>
        <p class="ts-hero-dek">{e((hero_a.get('dek') or hero_a['meta_description'])[:220])}</p>
        <div class="ts-hero-footer">
          <span>&#128337; {read_time(hero_a.get('word_count',600))}</span>
          <a href="articles/{hero_a['slug']}.html" class="ts-hero-cta">Read full article &#8594;</a>
        </div>
      </div>
    </div>
  </section>"""

    # Category nav pills row
    cats = [
        ("streaming.html",          "📡 Streaming"),
        ("cloud.html",              "☁️ Cloud"),
        ("graphics.html",           "🎨 Graphics"),
        ("playout.html",            "▶️ Playout"),
        ("infrastructure.html",     "🏗️ Infrastructure"),
        ("ai-post-production.html", "🎬 AI & Post"),
        ("newsroom.html",           "📰 Newsroom"),
    ]
    cat_pills = "".join(
        f'<a href="{pg}" class="ts-cat-pill">{lbl}</a>' for pg, lbl in cats)

    # Latest grid — skip hero article so no duplicate
    grid_arts = [a for a in latest if a is not hero_a][:17]
    cards_html = "\n".join(card(a, num=i+1) for i, a in enumerate(grid_arts))

    return f"""{head(title, desc, canon, "style.css")}
<body>
{nav("index.html" if True else "")}
  {hero_html}
  <div class="ts-catbar">
    <div class="ts-catbar-inner">{cat_pills}</div>
  </div>
  <main>
    <div class="page-wrap">
      <div class="page-section">
        <div class="section-hdr">
          <h2>&#128240; Latest Broadcast &amp; Streaming News</h2>
          <span class="ts-updated">Updated every 6 hours</span>
        </div>
{cards_html}
      </div>
    </div>
  </main>
{footer()}
</body>
</html>"""


def sitemap(arts):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    statics = [
        ("index.html","daily","1.0"),("featured.html","daily","0.95"),
        ("streaming.html","daily","0.9"),("cloud.html","daily","0.9"),
        ("graphics.html","daily","0.9"),("playout.html","daily","0.9"),
        ("infrastructure.html","daily","0.9"),("ai-post-production.html","daily","0.9"),
        ("newsroom.html","daily","0.9"),("howto.html","weekly","0.8"),
        ("about.html","monthly","0.6"),("contact.html","monthly","0.5"),("privacy.html","yearly","0.3"),
    ]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for pg,fr,pr in statics:
        lines.append(f"  <url><loc>{BASE_URL}/{pg}</loc><lastmod>{today}</lastmod><changefreq>{fr}</changefreq><priority>{pr}</priority></url>")
    for a in arts:
        lines.append(f"  <url><loc>{BASE_URL}/articles/{a['slug']}.html</loc><lastmod>{a['published']}</lastmod><changefreq>monthly</changefreq><priority>0.75</priority></url>")
        # Also include legacy rss-* URL in sitemap so Google can find it
        if a.get("legacy_slug"):
            lines.append(f"  <url><loc>{BASE_URL}/articles/{a['legacy_slug']}.html</loc><lastmod>{a['published']}</lastmod><changefreq>monthly</changefreq><priority>0.65</priority></url>")
    lines.append("</urlset>")
    return "\n".join(lines)



def home_with_hero(feat_arts: list, all_arts: list) -> str:
    """Build homepage with hero + category pill bar + latest grid."""
    hero = feat_arts[0] if feat_arts else (all_arts[0] if all_arts else None)
    grid_arts = [a for a in all_arts if a is not hero][:23]

    title = "Featured — The Streamic | Broadcast & Streaming Technology News"
    desc  = ("Featured broadcast and streaming technology coverage. Expert analysis, "
             "original editorial, and breaking news for media professionals.")
    base  = BASE_URL

    hero_html = ""
    if hero:
        hr   = read_time(hero.get("word_count", 600))
        himg = e(hero.get("image_url", ""))
        hlink = f"articles/{hero['slug']}.html"
        hero_html = f"""  <section class="ts-hero">
    <div class="ts-hero-inner">
      <div class="ts-hero-img-wrap">
        <img src="{himg}" alt="{e(hero['title'])}" loading="eager"
             onerror="this.src='assets/fallback.jpg'">
        <span class="nc-pill" style="background:{hero['cat_color']};">{hero['cat_icon']} {e(hero.get('cat_label',''))}</span>
      </div>
      <div class="ts-hero-body">
        <p class="ts-hero-eyebrow">Editor's Pick &mdash; {d(hero['published'])}</p>
        <h2 class="ts-hero-title"><a href="{hlink}">{e(hero['title'])}</a></h2>
        <p class="ts-hero-dek">{e((hero.get('card_summary') or hero.get('dek') or '')[:160])}</p>
        <div class="ts-hero-footer">
          <span>&#128337; {hr}</span>
          <a href="{hlink}" class="ts-hero-cta">Read full article &#8594;</a>
        </div>
      </div>
    </div>
  </section>"""

    cats_bar = [
        ("streaming.html","📡 Streaming"),("cloud.html","☁️ Cloud"),
        ("graphics.html","🎨 Graphics"),("playout.html","▶️ Playout"),
        ("infrastructure.html","🏗️ Infrastructure"),
        ("ai-post-production.html","🎬 AI & Post"),("newsroom.html","📰 Newsroom"),
    ]
    pills = "".join(f'<a href="{pg}" class="ts-cat-pill">{lb}</a>' for pg, lb in cats_bar)
    catbar = f"""  <div class="ts-catbar">
    <div class="ts-catbar-inner">{pills}
      <span class="ts-updated">Updated every 6 hours</span>
    </div>
  </div>"""

    cards_html = "\n".join(card(a, num=i+1) for i, a in enumerate(grid_arts))

    return f"""{head(title, desc, f"{base}/featured.html", "style.css")}
<body>
{nav("featured.html")}
{hero_html}
{catbar}
  <main>
    <div class="page-wrap">
      <div class="page-section">
        <div class="section-hdr">
          <h2>&#128240; Latest Broadcast &amp; Streaming News</h2>
          <span class="ts-updated">Updated every 6 hours</span>
        </div>
{cards_html}
      </div>
    </div>
  </main>
{footer()}
</body>
</html>"""

def main():
    with open(ARTICLES_F, "r", encoding="utf-8") as f:
        arts = json.load(f)
    if not arts:
        raise SystemExit("ERROR: No articles — aborting build.")

    os.makedirs(ARTS_D, exist_ok=True)

    # Load how many summaries are available
    summaries_dir = os.path.join(ROOT, "data", "summaries")
    sum_count = len(os.listdir(summaries_dir)) if os.path.isdir(summaries_dir) else 0
    if sum_count: print(f"  ✓ {sum_count} Groq summaries loaded from data/summaries/")

    written = 0
    for a in arts:
        a = enrich_with_summary(a)   # apply Groq summary if available
        html = article_page(a)
        # 1. Canonical slug file
        w(os.path.join(ARTS_D, f"{a['slug']}.html"), html)
        written += 1
        # 2. Legacy rss-<hex>.html alias so old "Read" links keep working
        legacy = a.get("legacy_slug")
        if legacy and legacy != a["slug"]:
            w(os.path.join(ARTS_D, f"{legacy}.html"), html)
            written += 1
    print(f"  \u2713 {written} article files ({len(arts)} articles + legacy aliases)")

    by_cat = {}
    for a in arts: by_cat.setdefault(a["category"], []).append(a)
    cat_file_count = 0
    for cat, ca in by_cat.items():
        pages = category_page(cat, ca)
        for page_num, page_html in pages:
            fname = f"{cat}.html" if page_num == 0 else f"{cat}-p{page_num+1}.html"
            w(os.path.join(DOCS, fname), page_html)
            cat_file_count += 1
    print(f"  ✓ {len(by_cat)} categories, {cat_file_count} page files (paginated at {PAGE_SIZE} cards)")

    # Build featured.html WITH hero (overwrites the plain grid version from category loop)
    feat_arts = by_cat.get("featured", [])
    all_for_home = sorted(arts, key=lambda a: a["published"], reverse=True)
    w(os.path.join(DOCS, "featured.html"), home_with_hero(feat_arts or all_for_home, all_for_home))
    w(os.path.join(DOCS, "index.html"),    home_with_hero(feat_arts or all_for_home, all_for_home))
    print("  ✓ featured.html + index.html (with hero)")

    w(os.path.join(DOCS, "sitemap.xml"), sitemap(arts))
    w(os.path.join(DOCS, "robots.txt"), f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")
    print("  ✓ sitemap.xml + robots.txt")

    for fname in ("style.css", "main.js"):
        src_f = os.path.join(ROOT, fname)
        if os.path.isfile(src_f):
            shutil.copy2(src_f, os.path.join(DOCS, fname))
            print(f"  ✓ {fname} copied to docs/")

    # ── Mirror key pages to repo root so Pages works from either root OR /docs ──
    # GitHub Pages can serve from root or /docs — mirror ensures both work.
    _root_mirror = ["index.html", "featured.html", "streaming.html", "cloud.html",
                    "graphics.html", "playout.html", "infrastructure.html",
                    "ai-post-production.html", "newsroom.html", "howto.html",
                    "about.html", "contact.html", "privacy.html", "terms.html",
                    "vlog.html", "sitemap.xml", "robots.txt"]
    for fname in _root_mirror:
        src_f = os.path.join(DOCS, fname)
        dst_f = os.path.join(ROOT, fname)
        if os.path.isfile(src_f):
            shutil.copy2(src_f, dst_f)
    # Mirror style.css and main.js to root (prefer site/ source, skip if same file)
    for fname in ("style.css", "main.js"):
        src_f = os.path.join(ROOT, "site", fname)
        dst_f = os.path.join(ROOT, fname)
        if os.path.isfile(src_f) and src_f != dst_f:
            shutil.copy2(src_f, dst_f)
    # Ensure CNAME and .nojekyll exist at root
    for f, content in [("CNAME", "thestreamic.in"), (".nojekyll", "")]:
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            with open(p, "w") as _f: _f.write(content)
    # Mirror articles/ to root/articles/ so links work if Pages serves from root
    root_arts = os.path.join(ROOT, "articles")
    os.makedirs(root_arts, exist_ok=True)
    docs_arts = os.path.join(DOCS, "articles")
    mirror_count = 0
    if os.path.isdir(docs_arts):
        for art_fname in os.listdir(docs_arts):
            if art_fname.endswith(".html"):
                shutil.copy2(os.path.join(docs_arts, art_fname), os.path.join(root_arts, art_fname))
                mirror_count += 1
    print(f"  ✓ Key pages + {mirror_count} articles mirrored to repo root (works from / or /docs)")

    print(f"\n✓ Build complete: {len(arts)} articles, {len(by_cat)} categories.")

if __name__ == "__main__":
    main()
