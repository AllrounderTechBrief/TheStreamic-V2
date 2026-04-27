"""
scripts/generate_originals.py
The Streamic original article generator — deterministic, zero-LLM edition.

Reads:
  - data/news.json
  - data/images.json, optional

Supports news.json as:
  1) Flat list:
     [{"title": "...", "url": "...", "source": "...", "teaser": "..."}]

  2) Dict of categories:
     {"streaming": [{...}], "cloud": [{...}]}

  3) Client format:
     {"featured_priority": [...], "items": [...]}

Writes:
  - data/generated_articles.json

No LLM.
No scraping.
No external network calls.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone

try:
    from slugify import slugify
except Exception:
    def slugify(value):
        value = (value or "").lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = re.sub(r"-+", "-", value).strip("-")
        return value or "streamic-article"


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NEWS_F = os.path.join(ROOT, "data", "news.json")
IMAGES_F = os.path.join(ROOT, "data", "images.json")
OUTPUT_F = os.path.join(ROOT, "data", "generated_articles.json")

ARTICLES_PER_CATEGORY = int(os.environ.get("ARTICLES_PER_CATEGORY", "3"))
SITE_URL = os.environ.get("SITE_BASE_URL", "https://www.thestreamic.in").rstrip("/")
AUTHOR_NAME = "The Streamic Editorial Team"

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

CAT_IMAGES = {
    "featured": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=900&auto=format&fit=crop",
    "streaming": "https://images.unsplash.com/photo-1616401784845-180882ba9ba8?w=900&auto=format&fit=crop",
    "cloud": "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=900&auto=format&fit=crop",
    "graphics": "https://images.unsplash.com/photo-1547658719-da2b51169166?w=900&auto=format&fit=crop",
    "playout": "https://images.unsplash.com/photo-1612420696760-0a0f34d3e7d0?w=900&auto=format&fit=crop",
    "infrastructure": "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=900&auto=format&fit=crop",
    "ai-post-production": "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=900&auto=format&fit=crop",
    "newsroom": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=900&auto=format&fit=crop",
}

CATEGORY_KEYWORDS = {
    "streaming": ["streaming", "ott", "cdn", "hls", "dash", "cmaf", "abr", "codec", "encoding", "encoder", "transcode", "vod", "live stream", "latency", "av1", "hevc", "mpeg", "video delivery"],
    "cloud": ["cloud", "remote production", "remi", "aws", "azure", "virtualized", "virtualised", "saas", "datacenter", "data center", "cloud playout", "cloud production"],
    "graphics": ["graphics", "virtual production", "unreal", "vizrt", "ar", "xr", "augmented", "virtual set", "motion graphics", "render"],
    "playout": ["playout", "automation", "master control", "mcr", "channel-in-a-box", "channel in a box", "transmission", "on-air", "scheduling"],
    "infrastructure": ["smpte", "st 2110", "2110", "nmos", "ptp", "sdn", "ip routing", "broadcast ip", "infrastructure", "storage", "nexis", "network", "switch", "fiber", "fibre", "sdi"],
    "ai-post-production": ["ai", "artificial intelligence", "machine learning", "post-production", "post production", "editing", "media composer", "avid", "davinci", "premiere", "mam", "pam", "metadata", "qc", "quality control", "transcription", "archive"],
    "newsroom": ["newsroom", "nrcs", "inews", "journalist", "news production", "rundown", "editorial workflow", "wire service", "news"],
}


def clean_text(value):
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def domain_from_url(url):
    url = clean_text(url)
    if not url:
        return ""
    m = re.search(r"https?://([^/]+)", url)
    if not m:
        return ""
    return m.group(1).lower().replace("www.", "")


def detect_category(item):
    existing = clean_text(item.get("category") or item.get("cat") or "").lower()
    existing = existing.replace("_", "-").replace(" ", "-")
    if existing in CAT_META:
        return existing

    haystack = " ".join([
        clean_text(item.get("title")),
        clean_text(item.get("teaser")),
        clean_text(item.get("summary")),
        clean_text(item.get("description")),
        clean_text(item.get("source")),
        clean_text(item.get("url")),
    ]).lower()

    best_cat = "featured"
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in haystack)
        if score > best_score:
            best_cat = cat
            best_score = score
    return best_cat


def normalise_items(raw):
    out = []

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                out.append((detect_category(item), item))
        return out

    if isinstance(raw, dict):
        if "items" in raw or "featured_priority" in raw:
            merged = []
            if isinstance(raw.get("featured_priority"), list):
                merged.extend(raw.get("featured_priority", []))
            if isinstance(raw.get("items"), list):
                merged.extend(raw.get("items", []))
            for item in merged:
                if isinstance(item, dict):
                    out.append((detect_category(item), item))
            return out

        for cat, items in raw.items():
            if not isinstance(items, list):
                continue
            cat_slug = cat if cat in CAT_META else detect_category({"category": cat})
            for item in items:
                if isinstance(item, dict):
                    item.setdefault("category", cat_slug)
                    out.append((cat_slug, item))
        return out

    raise SystemExit(f"ERROR: Unsupported data/news.json format: {type(raw).__name__}")


def load_images():
    if not os.path.exists(IMAGES_F):
        return {}, {}

    try:
        with open(IMAGES_F, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}, {}

    if isinstance(raw, list):
        images = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        images = [x for x in raw.values() if isinstance(x, dict)]
    else:
        images = []

    by_slug = {img.get("slug"): img for img in images if img.get("slug")}
    by_cat = {img.get("category"): img for img in images if img.get("category")}
    return by_slug, by_cat


def topic_image(category, slug, images_by_slug, images_by_cat):
    img_obj = images_by_slug.get(slug) or images_by_cat.get(category)
    if img_obj:
        return {
            "image_url": img_obj.get("image_url") or CAT_IMAGES.get(category, CAT_IMAGES["featured"]),
            "image_credit": img_obj.get("credit", "Unsplash — free to use under the Unsplash License"),
            "image_license": img_obj.get("license", "Unsplash License"),
            "image_license_url": img_obj.get("license_url", "https://unsplash.com/license"),
        }

    return {
        "image_url": CAT_IMAGES.get(category, CAT_IMAGES["featured"]),
        "image_credit": "Unsplash — free to use under the Unsplash License",
        "image_license": "Unsplash License",
        "image_license_url": "https://unsplash.com/license",
    }


def source_name(item):
    return clean_text(item.get("source")) or domain_from_url(clean_text(item.get("url"))) or "Industry source"


def item_teaser(item):
    teaser = clean_text(item.get("teaser")) or clean_text(item.get("summary")) or clean_text(item.get("description"))
    return teaser[:240]


def make_stable_slug(item, category, index):
    title = clean_text(item.get("title")) or f"{category} broadcast technology analysis"
    base = slugify(title)[:80].strip("-") or f"{category}-broadcast-technology-analysis"
    seed = clean_text(item.get("url")) or clean_text(item.get("guid")) or f"{category}-{index}-{title}"
    suffix = hashlib.md5(seed.encode("utf-8")).hexdigest()[:6]
    return f"{base}-{suffix}"


def editorial_title(item, category):
    raw_title = clean_text(item.get("title"))
    label = CAT_META.get(category, CAT_META["featured"])["label"]

    if not raw_title:
        return f"What {label} Teams Should Watch Next"

    low = raw_title.lower()

    if any(x in low for x in ["launch", "unveil", "introduc", "announce"]):
        return f"What {raw_title} Could Mean for Broadcast Operations"

    if any(x in low for x in ["partner", "collaborat", "integrat"]):
        return f"Why {raw_title} Matters Beyond the Partnership Headline"

    if any(x in low for x in ["ai", "artificial intelligence", "automation"]):
        return f"{raw_title}: The Real Workflow Question for Media Teams"

    if category == "streaming":
        return f"{raw_title}: The Delivery Infrastructure Angle"

    if category == "infrastructure":
        return f"{raw_title}: The Broadcast Engineering Reality Check"

    if category == "ai-post-production":
        return f"{raw_title}: Practical Impact on Post-Production Workflows"

    return f"{raw_title}: What Broadcast Professionals Should Take From It"


def build_card_summary(item, category):
    label = CAT_META.get(category, CAT_META["featured"])["label"].lower()
    return (
        f"The Streamic looks at this {label} development from an operations perspective: "
        f"what it may change, where the practical limits sit, and why engineering teams should read beyond the headline."
    )


def build_meta_description(title, category):
    label = CAT_META.get(category, CAT_META["featured"])["label"]
    return (
        f"Independent Streamic analysis of {title[:90]} for broadcast engineers, "
        f"media operations teams, and {label.lower()} decision-makers."
    )[:155]


def build_body_html(item, category, title):
    label = CAT_META.get(category, CAT_META["featured"])["label"]
    raw_title = clean_text(item.get("title")) or title
    src = source_name(item)
    teaser = item_teaser(item)

    category_focus = {
        "streaming": "streaming delivery chains, origin performance, CDN behaviour, player compatibility, bitrate strategy, monitoring, and incident response",
        "cloud": "cloud contribution, REMI reliability, remote access, latency management, cost visibility, failover planning, and operator confidence",
        "graphics": "template control, real-time render reliability, data-feed accuracy, operator workflow, virtual set integration, and brand-safe on-air execution",
        "playout": "automation reliability, schedule integrity, asset readiness, disaster recovery, compliance handling, and master control escalation paths",
        "infrastructure": "network design, timing, storage, routing, interoperability, cyber risk, observability, and the operational shift from SDI thinking to IP systems",
        "ai-post-production": "metadata trust, MAM/PAM integration, editorial search, automated QC, version handling, review checkpoints, and human oversight",
        "newsroom": "NRCS integration, rundown speed, verified media handling, archive search, graphics handoff, remote journalism, and multi-platform publishing",
        "featured": "broadcast infrastructure, production workflows, streaming operations, post-production systems, newsroom technology, and engineering decision-making",
    }.get(category, "media technology operations, workflow impact, integration risk, and engineering decision-making")

    source_context = (
        f"<p>The public source signal comes from {src}. The Streamic is using it as a starting point for independent analysis, not as copy to be republished. "
        f"The useful question is how this development affects real broadcast, post-production, streaming, and newsroom operations once it leaves the announcement layer and enters production planning.</p>"
    )

    if teaser:
        source_context += (
            f"<p>The available summary suggests the topic is connected to “{teaser[:160]}”. "
            f"That context is useful, but the operational value depends on integration, supportability, and whether the workflow can be trusted under pressure.</p>"
        )

    return f"""
<p><strong>The Streamic view:</strong> {raw_title} is useful only if it is read through the reality of broadcast operations, not just the announcement headline. In media technology, the gap between a vendor claim and a dependable workflow is where engineering judgement matters most.</p>

{source_context}

<h2>Why this matters beyond the announcement</h2>
<p>In a working media environment, technology value is not measured by how modern the language sounds. It is measured by whether operators can trust it during a deadline, whether engineers can monitor it under pressure, and whether the system fits into the existing chain without creating hidden support debt. That is why this {label.lower()} development should be judged against the practical needs of {category_focus}.</p>

<p>For broadcast and streaming teams, the strongest signal is rarely the headline itself. The stronger signal is what the move says about where vendors believe operational pressure is building. If the update is about automation, the real question is not whether automation exists, but whether it reduces repetitive effort without weakening editorial control. If the update is about cloud or IP, the question is not whether the architecture is flexible, but whether teams can operate it safely when something fails.</p>

<h2>The operational question</h2>
<p>The first question for engineers is simple: where does this sit in the chain? A tool that touches ingest, metadata, editing, playout, streaming delivery, or archive search has a different risk profile from a tool that only improves reporting or visualisation. The closer a system sits to transmission, publishing, or editorial decision-making, the more important observability, rollback, permissions, and support ownership become.</p>

<p>Many announcements sound strong because they describe a final outcome: faster production, smarter search, lower latency, improved efficiency, or better collaboration. In practice, those outcomes depend on integration details. Authentication, storage permissions, metadata mapping, API reliability, network paths, file naming, project locking, audio/video sync, subtitle handling, and monitoring dashboards decide whether the promise becomes useful in a real facility.</p>

<h2>What engineering teams should check</h2>
<ul>
<li><strong>Integration depth:</strong> Does the product integrate with existing MAM, PAM, NRCS, automation, storage, and delivery systems, or does it create another island that staff must manually bridge?</li>
<li><strong>Failure behaviour:</strong> What happens when a service is slow, unavailable, or returns incomplete metadata? A workflow is only production-ready when failure modes are visible and recoverable.</li>
<li><strong>Operator trust:</strong> Does the system make work clearer for editors, producers, operators, or engineers, or does it add another interface that must be checked under deadline pressure?</li>
<li><strong>Standards and portability:</strong> Are outputs based on open standards and clear metadata structures, or does the broadcaster become dependent on one vendor’s interpretation of the workflow?</li>
<li><strong>Support ownership:</strong> When something breaks, is the issue owned by engineering, IT, operations, the vendor, or a cloud provider? Blurred ownership increases downtime.</li>
</ul>

<h2>The hidden risk</h2>
<p>The hidden risk is not that the technology fails completely. The more common risk is partial success. A system may work well in a demo, handle simple files, or support a controlled test workflow, while still becoming fragile when applied to mixed codecs, older projects, multilingual metadata, live publishing deadlines, or multi-site operations. This is especially important in broadcast environments where legacy systems and modern platforms often coexist for years.</p>

<p>That is why The Streamic would treat this kind of development as a planning signal rather than a final answer. It may point in the right direction, but the production decision should come after a controlled workflow test, clear ownership mapping, and a review of how the system behaves when real operational constraints appear.</p>

<h2>Practical takeaway</h2>
<p>The practical takeaway is to separate the announcement from the deployment reality. If the technology improves a real bottleneck, reduces manual handling, and gives teams better visibility, it deserves attention. If it only adds another layer without simplifying the chain, it may create more operational noise than value.</p>

<p>For media organisations, the winning approach is not to chase every new platform or feature. It is to build a disciplined evaluation model: define the workflow problem, test with real operational material, measure time saved, monitor failure cases, and decide whether the change improves reliability as well as speed. That is the difference between technology adoption and technology accumulation.</p>

<h2>The Streamic assessment</h2>
<p>{title} should be viewed as part of a wider industry movement toward more software-defined, data-aware, and workflow-connected media operations. The opportunity is real, but the value depends on execution. Broadcast teams should look for evidence of interoperability, transparent monitoring, clear support paths, and measurable operational improvement before treating any announcement as a production-ready solution.</p>
""".strip()


def word_count(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return len(text.split()) if text else 0


def dedupe_articles(items):
    seen = set()
    out = []
    for cat, item in items:
        key = clean_text(item.get("url")) or clean_text(item.get("guid")) or clean_text(item.get("title")).lower()
        if not key:
            key = hashlib.md5(json.dumps(item, sort_keys=True).encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append((cat, item))
    return out


def main():
    if not os.path.exists(NEWS_F):
        raise SystemExit(f"ERROR: Missing {NEWS_F}")

    with open(NEWS_F, "r", encoding="utf-8") as f:
        raw_news = json.load(f)

    images_by_slug, images_by_cat = load_images()

    pairs = dedupe_articles(normalise_items(raw_news))
    if not pairs:
        raise SystemExit("ERROR: No valid news items found in data/news.json")

    by_cat = {}
    for cat, item in pairs:
        by_cat.setdefault(cat, []).append(item)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    articles = []

    for category in CAT_META.keys():
        items = by_cat.get(category, [])
        if not items:
            continue

        count = min(ARTICLES_PER_CATEGORY, len(items))
        meta = CAT_META[category]

        for i, item in enumerate(items[:count]):
            title = editorial_title(item, category)
            slug = make_stable_slug(item, category, i)
            body = build_body_html(item, category, title)
            image_meta = topic_image(category, slug, images_by_slug, images_by_cat)

            item_guid = clean_text(item.get("guid"))
            if not item_guid:
                item_guid = hashlib.md5((clean_text(item.get("url")) or slug).encode("utf-8")).hexdigest()[:16]

            published = clean_text(item.get("published"))[:10] or clean_text(item.get("pubDate"))[:10] or today
            card_summary = build_card_summary(item, category)

            articles.append({
                "category": category,
                "cat_label": meta["label"],
                "cat_icon": meta["icon"],
                "cat_color": meta["color"],
                "cat_page": meta["page"],
                "title": title,
                "slug": slug,
                "guid": item_guid,
                "legacy_slug": f"rss-{item_guid[:16]}" if item_guid else None,
                "dek": card_summary,
                "card_summary": card_summary,
                "meta_description": build_meta_description(title, category),
                "body_html": body,
                "word_count": word_count(body),
                "source_url": clean_text(item.get("url") or item.get("link")),
                "source_domain": source_name(item),
                "published": published,
                "image_url": image_meta["image_url"],
                "image_credit": image_meta["image_credit"],
                "image_license": image_meta["image_license"],
                "image_license_url": image_meta["image_license_url"],
                "editorial": True,
                "type_label": "STREAMIC ANALYSIS",
                "author": AUTHOR_NAME,
            })

        print(f"  ✓ {category}: {count} original analysis articles")

    if not articles:
        raise SystemExit("ERROR: No articles generated — check data/news.json categories and fields.")

    os.makedirs(os.path.dirname(OUTPUT_F), exist_ok=True)
    with open(OUTPUT_F, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(articles)} original articles written to data/generated_articles.json")


if __name__ == "__main__":
    main()
