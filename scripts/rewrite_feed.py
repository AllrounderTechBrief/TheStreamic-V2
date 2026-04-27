"""
scripts/rewrite_feed.py
=======================

RSS metadata -> Streamic-style original editorial article records.

Input:
  data/news.json

Supported input formats:
  1) Flat list:
     [{"title": "...", "url": "...", "source": "...", "teaser": "..."}]

  2) Dict of categories:
     {"streaming": [{...}], "cloud": [{...}]}

  3) Client format:
     {"featured_priority": [...], "items": [...]}

Output:
  data/generated_articles.json

Rules:
  - RSS title + teaser are used as seed/context only.
  - No full-page scraping.
  - No LLM.
  - No external network calls.
  - Original deterministic editorial prose.
  - AdSense safer: stronger analysis, practical workflow value, less feed-like output.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone


# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NEWS_F = os.path.join(ROOT, "data", "news.json")
POOLS_F = os.path.join(ROOT, "data", "image_pools.json")
OUTPUT_F = os.path.join(ROOT, "data", "generated_articles.json")

ITEMS_PER_CAT = int(os.environ.get("ITEMS_PER_CAT", "36"))
MAX_TOTAL_KEPT = int(os.environ.get("MAX_TOTAL_KEPT", "400"))
CARD_WORDS = int(os.environ.get("CARD_WORDS", "90"))


# ── Category metadata ────────────────────────────────────────────────────────
CAT_META = {
    "featured": {"label": "Featured", "icon": "⭐", "color": "#1d1d1f", "page": "featured.html"},
    "streaming": {"label": "Streaming", "icon": "📡", "color": "#0071e3", "page": "streaming.html"},
    "cloud": {"label": "Cloud Production", "icon": "☁️", "color": "#5856d6", "page": "cloud.html"},
    "graphics": {"label": "Graphics", "icon": "🎨", "color": "#FF9500", "page": "graphics.html"},
    "playout": {"label": "Playout", "icon": "▶️", "color": "#34C759", "page": "playout.html"},
    "infrastructure": {"label": "Infrastructure", "icon": "🏗️", "color": "#8E8E93", "page": "infrastructure.html"},
    "ai-post-production": {"label": "AI & Post-Production", "icon": "🎬", "color": "#FF2D55", "page": "ai-post-production.html"},
    "newsroom": {"label": "Newsroom", "icon": "📰", "color": "#D4AF37", "page": "newsroom.html"},
}

CATEGORY_KEYWORDS = {
    "streaming": [
        "streaming", "ott", "cdn", "hls", "dash", "cmaf", "abr", "codec", "encoder",
        "encoding", "transcode", "vod", "video delivery", "latency", "av1", "hevc",
    ],
    "cloud": [
        "cloud", "remote production", "remi", "aws", "azure", "virtualized", "virtualised",
        "saas", "cloud production", "cloud playout", "data center", "datacenter",
    ],
    "graphics": [
        "graphics", "virtual production", "unreal", "vizrt", "ar", "xr", "augmented",
        "virtual set", "render", "motion graphics",
    ],
    "playout": [
        "playout", "automation", "master control", "mcr", "channel-in-a-box",
        "channel in a box", "transmission", "on-air", "schedule",
    ],
    "infrastructure": [
        "smpte", "st 2110", "2110", "nmos", "ptp", "sdn", "ip routing", "broadcast ip",
        "infrastructure", "storage", "network", "switch", "fiber", "fibre", "sdi",
    ],
    "ai-post-production": [
        "ai", "artificial intelligence", "machine learning", "post-production",
        "post production", "editing", "avid", "media composer", "davinci", "premiere",
        "mam", "pam", "metadata", "qc", "quality control", "archive", "transcription",
    ],
    "newsroom": [
        "newsroom", "nrcs", "inews", "journalist", "news production", "rundown",
        "editorial workflow", "wire service", "breaking news",
    ],
}

CAT_CONTEXT = {
    "streaming": "streaming delivery, CDN behaviour, player compatibility, encoding strategy, and incident response",
    "cloud": "cloud production, REMI reliability, latency management, access control, and cost visibility",
    "graphics": "real-time graphics, template control, data-feed accuracy, virtual sets, and on-air execution",
    "playout": "playout automation, schedule integrity, compliance, disaster recovery, and master control operations",
    "infrastructure": "IP infrastructure, timing, routing, storage, interoperability, observability, and support ownership",
    "ai-post-production": "AI-assisted post-production, metadata trust, archive search, automated QC, and editorial review",
    "newsroom": "NRCS integration, newsroom automation, rundown speed, verified media handling, and multi-platform publishing",
    "featured": "broadcast engineering, media operations, streaming workflows, and infrastructure decision-making",
}


# ── Boilerplate stripper ─────────────────────────────────────────────────────
_BOILERPLATE = re.compile(
    r"\b(today announced|is pleased to announce|proud to introduce|"
    r"we are excited|leading provider of|industry-leading|state-of-the-art|"
    r"cutting-edge|revolutionary|game-changing|best-in-class|world-class|"
    r"seamless|transformative|next-generation)\b",
    re.IGNORECASE,
)


def clean(text):
    """Clean RSS text safely."""
    if text is None:
        return ""
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = _BOILERPLATE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sents(text):
    text = clean(text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def domain_from_url(url):
    url = clean(url)
    m = re.search(r"https?://([^/]+)", url)
    if not m:
        return ""
    return m.group(1).lower().replace("www.", "")


def detect_category(item):
    """Detect Streamic category from item fields."""
    existing = clean(item.get("category") or item.get("cat") or "").lower()
    existing = existing.replace("_", "-").replace(" ", "-")
    if existing in CAT_META:
        return existing

    haystack = " ".join([
        clean(item.get("title")),
        clean(item.get("teaser")),
        clean(item.get("summary")),
        clean(item.get("description")),
        clean(item.get("source")),
        clean(item.get("url")),
    ]).lower()

    best_cat = "featured"
    best_score = 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in haystack)
        if score > best_score:
            best_cat = cat
            best_score = score
    return best_cat


def normalise_news(raw):
    """
    Return dict:
      {category: [item, item]}
    Works for flat list, dict-of-categories, and {"featured_priority": [], "items": []}.
    """
    by_cat = {cat: [] for cat in CAT_META}

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                by_cat.setdefault(detect_category(item), []).append(item)
        return by_cat

    if isinstance(raw, dict):
        if "items" in raw or "featured_priority" in raw:
            merged = []
            if isinstance(raw.get("featured_priority"), list):
                merged.extend(raw.get("featured_priority", []))
            if isinstance(raw.get("items"), list):
                merged.extend(raw.get("items", []))
            for item in merged:
                if isinstance(item, dict):
                    by_cat.setdefault(detect_category(item), []).append(item)
            return by_cat

        for cat, items in raw.items():
            if not isinstance(items, list):
                continue
            cat_slug = cat if cat in CAT_META else detect_category({"category": cat})
            by_cat.setdefault(cat_slug, [])
            for item in items:
                if isinstance(item, dict):
                    item.setdefault("category", cat_slug)
                    by_cat[cat_slug].append(item)
        return by_cat

    raise SystemExit(f"ERROR: Unsupported data/news.json format: {type(raw).__name__}")


def load_pools():
    """Load image pools. Fall back to safe built-in pools if file is missing."""
    default = {
        "cat_pools": {
            "featured": ["photo-1598488035139-bdbb2231ce04", "photo-1574717024653-61fd2cf4d44d"],
            "streaming": ["photo-1616401784845-180882ba9ba8", "photo-1574717025058-97e3af4ef9b5"],
            "cloud": ["photo-1544197150-b99a580bb7a8", "photo-1531297484001-80022131f5a1"],
            "graphics": ["photo-1547658719-da2b51169166", "photo-1504639725590-34d0984388bd"],
            "playout": ["photo-1612420696760-0a0f34d3e7d0", "photo-1478737270239-2f02b77fc618"],
            "infrastructure": ["photo-1486312338219-ce68d2c6f44d", "photo-1558494949-ef010cbdcc31"],
            "ai-post-production": ["photo-1677442135703-1787eea5ce01", "photo-1572044162444-ad60f128bdea"],
            "newsroom": ["photo-1504711434969-e33886168f5c", "photo-1585829365295-ab7cd400c167"],
        }
    }

    if not os.path.exists(POOLS_F):
        return default

    try:
        with open(POOLS_F, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("cat_pools"), dict):
            return data
    except Exception:
        pass

    return default


def unique_picks(pool, seed, count):
    if not pool:
        return []
    indexed = list(range(len(pool)))
    indexed.sort(key=lambda i: int(hashlib.md5(f"{seed}:{i}".encode()).hexdigest(), 16))
    return [pool[indexed[i % len(pool)]] for i in range(count)]


PARAS = {
    "context": [
        "The useful question is not whether the announcement sounds modern, but whether it can survive the realities of broadcast operations.",
        "Most media technology changes become valuable only when they reduce operational friction without weakening control, visibility, or reliability.",
        "The broadcast sector is moving quickly, but engineering teams still need technology that behaves predictably under deadline pressure.",
        "A strong workflow improvement is not measured by a feature list; it is measured by how clearly it helps operators, engineers, and editorial teams do their work.",
        "The gap between a product claim and a production-ready workflow is where most broadcast technology decisions succeed or fail.",
        "For media organisations, every new system must be judged against integration effort, support ownership, and failure behaviour.",
        "Technology adoption in broadcast rarely fails because the idea is weak; it fails when operational details are underestimated.",
        "Engineering teams should treat this as a signal to review workflow assumptions rather than as a reason to chase the newest platform immediately.",
    ],
    "development": [
        "The development matters because it points to a wider shift in how media systems are being designed, integrated, and supported.",
        "The strongest value will come where the technology removes manual handling and improves confidence in the chain.",
        "The practical impact depends on how well it connects with existing systems rather than how impressive it looks in isolation.",
        "For facilities with mixed legacy and modern infrastructure, transition planning is as important as the headline capability.",
        "If the workflow touches production, publishing, or transmission, observability and rollback paths need to be defined before deployment.",
        "The real test is whether the system reduces pressure during live or deadline-driven operations, not whether it performs well in a controlled demonstration.",
        "Teams should look for evidence of interoperability, operational transparency, and clear vendor support before treating the move as mature.",
        "This kind of change is most useful when it supports existing professional judgement instead of replacing it with another opaque layer.",
    ],
    "operations": [
        "Operations teams should begin with a limited workflow test using real media, real users, and realistic failure scenarios.",
        "The first review should cover permissions, monitoring, metadata behaviour, storage paths, network dependencies, and support escalation.",
        "Training should not be treated as an afterthought because adoption often fails when the interface changes faster than the operating culture.",
        "A system that saves time for one team but creates manual checking for another has not truly simplified the workflow.",
        "Change control should include measurable success criteria such as reduced handoffs, faster retrieval, lower incident count, or clearer fault isolation.",
        "The support model matters because blurred ownership between vendor, IT, engineering, and operations can increase downtime.",
        "Baseline metrics should be captured before rollout so the organisation can prove whether the new workflow actually improves performance.",
        "The safest deployments are staged, documented, reversible, and monitored from the beginning.",
    ],
    "outlook": [
        "The broader direction is clear: broadcast workflows are becoming more software-defined, data-aware, and connected across production and delivery.",
        "Vendors that expose open interfaces and respect operational realities will be better placed than platforms that rely only on closed ecosystems.",
        "The next phase of adoption will reward teams that combine engineering discipline with editorial and operational understanding.",
        "The organisations that benefit most will be those that test carefully, document lessons, and avoid treating every announcement as a finished solution.",
        "The value is real, but only when deployment planning is grounded in the day-to-day reality of media operations.",
        "For The Streamic, this is less a standalone story and more a sign of how media technology is moving toward integrated, accountable workflows.",
    ],
}


def make_slug(title, pub_date, cat=""):
    date_part = (pub_date or "2026-01-01")[:10]
    cat_part = re.sub(r"[^\w]+", "-", (cat or "").lower()).strip("-")[:18]
    title_part = re.sub(r"[^\w\s-]", "", (title or "").lower())
    title_part = re.sub(r"[\s_]+", "-", title_part).strip("-")
    if not title_part:
        title_part = "streamic-analysis"
    prefix = f"{date_part}-{cat_part}-" if cat_part else f"{date_part}-"
    return f"{prefix}{title_part[:80 - len(prefix)]}".strip("-")


def editorial_title(title, cat):
    title = clean(title)
    if not title:
        return f"{CAT_META.get(cat, CAT_META['featured'])['label']} Workflow Reality Check"

    low = title.lower()
    if any(x in low for x in ["launch", "unveil", "introduc", "announce"]):
        return f"What {title} Could Mean for Broadcast Operations"
    if any(x in low for x in ["partner", "collaborat", "integrat"]):
        return f"Why {title} Matters Beyond the Partnership Headline"
    if any(x in low for x in ["ai", "artificial intelligence", "automation"]):
        return f"{title}: The Real Workflow Question for Media Teams"
    if cat == "streaming":
        return f"{title}: The Delivery Infrastructure Angle"
    if cat == "infrastructure":
        return f"{title}: The Engineering Reality Check"
    return f"{title}: What Media Technology Teams Should Take From It"


def build_card_summary(title, teaser, cat, target_words=CARD_WORDS):
    label = CAT_META.get(cat, CAT_META["featured"])["label"].lower()
    base = clean(teaser) or clean(title)

    sentence = (
        f"The Streamic looks at this {label} development through an operational lens: "
        f"what may change in real workflows, where the integration risk sits, and why engineers should read beyond the headline."
    )

    if base:
        sentence += f" The source signal points to {base[:160]}."

    words = sentence.split()
    return " ".join(words[:target_words])


def build_article_body(title, teaser, slug, cat="featured"):
    clean_title = clean(title)
    clean_teaser = clean(teaser)
    ctx = CAT_CONTEXT.get(cat, CAT_CONTEXT["featured"])

    lead = (
        f"<p><strong>The Streamic view:</strong> {clean_title} should be read as an operational signal, not just an industry headline. "
        f"For broadcast and media teams, the important question is how this affects {ctx}.</p>"
    )

    source_context = ""
    if clean_teaser:
        source_context = (
            f"<p>The public summary suggests: “{clean_teaser[:220]}”. "
            f"That gives useful context, but it does not answer the engineering question: whether the workflow becomes easier to operate, easier to monitor, and safer to support.</p>"
        )
    else:
        source_context = (
            "<p>The available RSS metadata gives the headline signal, but the value for readers comes from interpreting what the development may mean in production environments.</p>"
        )

    ctx_pick = unique_picks(PARAS["context"], f"{slug}:ctx", 3)
    dev_pick = unique_picks(PARAS["development"], f"{slug}:dev", 4)
    ops_pick = unique_picks(PARAS["operations"], f"{slug}:ops", 5)
    out_pick = unique_picks(PARAS["outlook"], f"{slug}:out", 3)

    body = [
        lead,
        source_context,
        "<h2>Why this matters beyond the headline</h2>",
        f"<p>{ctx_pick[0]} {ctx_pick[1]}</p>",
        f"<p>{ctx_pick[2]} In this case, the value should be measured against practical broadcast requirements rather than announcement language.</p>",
        "<h2>The operational angle</h2>",
        f"<p>{dev_pick[0]} {dev_pick[1]}</p>",
        f"<p>{dev_pick[2]} {dev_pick[3]}</p>",
        "<h2>What teams should check</h2>",
        "<ul>",
        f"<li><strong>Integration:</strong> {ops_pick[0]}</li>",
        f"<li><strong>Visibility:</strong> {ops_pick[1]}</li>",
        f"<li><strong>Training:</strong> {ops_pick[2]}</li>",
        f"<li><strong>Ownership:</strong> {ops_pick[3]}</li>",
        f"<li><strong>Measurement:</strong> {ops_pick[4]}</li>",
        "</ul>",
        "<h2>The hidden risk</h2>",
        "<p>The hidden risk is partial success. A tool can work in a demonstration, handle a clean workflow, and still create friction when mixed media, legacy systems, deadline pressure, or unclear support boundaries appear. That is why engineering validation should include real operators, real assets, and real failure scenarios.</p>",
        "<h2>The Streamic assessment</h2>",
        f"<p>{out_pick[0]} {out_pick[1]}</p>",
        f"<p>{out_pick[2]} The practical takeaway is to separate the announcement from the deployment reality. If the change improves reliability, reduces manual handling, and gives teams better operational clarity, it deserves attention. If it only adds another layer, it may create more noise than value.</p>",
    ]

    html = "\n".join(body)
    wc = len(re.sub(r"<[^>]+>", " ", html).split())
    return html, wc


def pick_image(cat, slug, pools):
    cat_pools = pools.get("cat_pools", {})
    pool = cat_pools.get(cat) or cat_pools.get("featured") or []
    if not pool:
        pool = ["photo-1598488035139-bdbb2231ce04"]

    idx = int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(pool)
    photo_id = pool[idx]

    return {
        "image_url": f"https://images.unsplash.com/{photo_id}?w=900&auto=format&fit=crop&q=80",
        "image_credit": "Photo: Unsplash — free to use under the Unsplash License",
        "image_license": "Unsplash License",
        "image_license_url": "https://unsplash.com/license",
    }


def load_existing():
    if not os.path.exists(OUTPUT_F):
        return []
    try:
        with open(OUTPUT_F, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def item_key(item):
    return clean(item.get("url")) or clean(item.get("link")) or clean(item.get("guid")) or clean(item.get("title")).lower()


def main():
    print("=== rewrite_feed.py ===")

    if not os.path.exists(NEWS_F):
        raise SystemExit(f"ERROR: Missing {NEWS_F}")

    with open(NEWS_F, "r", encoding="utf-8") as f:
        raw_news = json.load(f)

    pools = load_pools()
    news_by_cat = normalise_news(raw_news)

    existing = load_existing()
    existing_slugs = {a.get("slug") for a in existing if isinstance(a, dict) and a.get("slug")}
    existing_keys = {a.get("source_url") for a in existing if isinstance(a, dict) and a.get("source_url")}

    new_articles = []
    seen_input = set()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for cat, items in news_by_cat.items():
        if not items:
            print(f"  {cat}: 0 items")
            continue

        cm = CAT_META.get(cat, {
            "label": cat.title(),
            "icon": "📡",
            "color": "#0071e3",
            "page": f"{cat}.html",
        })

        count = 0

        for item in items[:ITEMS_PER_CAT]:
            if not isinstance(item, dict):
                continue

            title_raw = clean(item.get("title"))
            if not title_raw:
                continue

            key = item_key(item)
            if key and key in seen_input:
                continue
            seen_input.add(key)

            src_url = clean(item.get("url") or item.get("link"))
            if src_url and src_url in existing_keys:
                continue

            teaser = clean(item.get("teaser") or item.get("summary") or item.get("description"))
            pub = clean(item.get("published") or item.get("pubDate") or today)[:10] or today
            src_dom = clean(item.get("source")) or domain_from_url(src_url)

            title = editorial_title(title_raw, cat)
            slug = make_slug(title, pub, cat)

            # Avoid slug collision.
            if slug in existing_slugs:
                suffix = hashlib.md5((src_url or title).encode()).hexdigest()[:6]
                slug = f"{slug[:72]}-{suffix}"
            if slug in existing_slugs:
                continue

            card_summary = build_card_summary(title_raw, teaser, cat)
            body_html, word_count = build_article_body(title_raw, teaser, slug, cat)
            image_meta = pick_image(cat, slug, pools)

            guid = clean(item.get("guid"))
            if not guid:
                guid = hashlib.md5((src_url or slug).encode()).hexdigest()[:16]

            new_articles.append({
                "category": cat,
                "cat_label": cm["label"],
                "cat_icon": cm["icon"],
                "cat_color": cm["color"],
                "cat_page": cm["page"],
                "title": title,
                "slug": slug,
                "guid": guid,
                "legacy_slug": f"rss-{guid[:16]}" if guid else None,
                "dek": card_summary,
                "meta_description": card_summary[:200],
                "card_summary": card_summary,
                "body_html": body_html,
                "word_count": word_count,
                "source_url": src_url,
                "source_domain": src_dom,
                "published": pub,
                "editorial": True,
                "type_label": "STREAMIC ANALYSIS",
                **image_meta,
            })

            existing_slugs.add(slug)
            if src_url:
                existing_keys.add(src_url)
            count += 1

        print(f"  {cat}: {count} new articles")

    merged = new_articles + existing
    merged.sort(key=lambda a: clean(a.get("published")), reverse=True)
    merged = merged[:MAX_TOTAL_KEPT]

    os.makedirs(os.path.dirname(OUTPUT_F), exist_ok=True)
    with open(OUTPUT_F, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"\n✓ generated_articles.json: {len(merged)} total ({len(new_articles)} new)")


if __name__ == "__main__":
    main()
