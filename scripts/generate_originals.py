"""
scripts/generate_originals.py
Read data/news.json + data/images.json.
Generate up to 3 original 700-900 word articles per category using
fully deterministic templates — no LLM, no scraped text.
Write data/generated_articles.json.

Fixes included:
- Supports news.json as either a dict of categories or a flat list of items.
- Supports images.json as either a list or dict.
- Avoids AttributeError: 'list' object has no attribute 'items'.
- Avoids KeyError when feed items are missing url/source/guid/teaser.
- Removes duplicate broken output block.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone

try:
    from slugify import slugify
except ImportError:  # Safe fallback if python-slugify is unavailable
    def slugify(value):
        value = str(value).lower().strip()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        return value.strip("-")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NEWS_F = os.path.join(ROOT, "data", "news.json")
IMAGES_F = os.path.join(ROOT, "data", "images.json")
OUTPUT_F = os.path.join(ROOT, "data", "generated_articles.json")
ARTICLES_PER_CATEGORY = 3
SITE_URL = os.environ.get("SITE_BASE_URL", "https://www.thestreamic.in")

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

BODY_TEMPLATES = {
    "streaming": """<p>The streaming technology landscape continues to evolve at pace, driven by broadcaster demand for lower latency, higher resilience, and more flexible delivery architectures. As OTT audiences grow globally, the engineering decisions made today — codec selection, CDN strategy, origin architecture, player compatibility, and monitoring design — will define competitive advantage for years ahead. Understanding these forces is essential for anyone involved in video delivery infrastructure, from platform engineers to operations managers overseeing live event delivery at scale.</p>
<h2>The Shifting Architecture of Video Delivery</h2>
<p>Modern streaming pipelines increasingly separate ingest, packaging, and delivery into discrete, independently scalable layers. This decoupled approach allows operators to upgrade individual components — swapping an encoder, changing a packaging format, or onboarding a new CDN partner — without disrupting the entire chain. The adoption of CMAF has been a significant enabler, providing a single-origin media format compatible with both HLS and DASH players, reducing storage duplication and simplifying origin management across large content libraries.</p>
<p>Codec evolution continues to shape streaming infrastructure decisions. AV1 is gaining traction as a royalty-free alternative to HEVC for high-efficiency delivery, particularly for platforms with the compute resources to support its more demanding encoding requirements. LCEVC offers a different approach, using an enhancement layer above a base codec to improve perceived quality at equivalent bitrates, with relatively modest encoder complexity overhead.</p>
<h2>Why This Matters to Broadcast Engineers</h2>
<p>For broadcast engineers, the transition from traditional satellite and cable delivery to IP-based streaming represents the most significant workflow transformation in a generation. The operational demands are different: instead of managing only physical transmission infrastructure, teams are now responsible for cloud configurations, API integrations, player telemetry, observability dashboards, and incident response across several suppliers.</p>
<h2>Key Trends Shaping the Sector</h2>
<ul><li><strong>Low-latency live streaming:</strong> WebRTC and LL-HLS are closing the gap with traditional broadcast and enabling interactive viewing experiences.</li><li><strong>Per-title encoding optimisation:</strong> Content-aware encoding reduces delivery cost while preserving perceived quality.</li><li><strong>Edge computing integration:</strong> Moving packaging and processing closer to viewers improves resilience during peak events.</li><li><strong>Sustainability metrics:</strong> Platforms are beginning to measure energy and network impact per stream.</li></ul>
<h2>Practical Implications for Operations Teams</h2>
<p>Operations teams should prioritise end-to-end monitoring that spans origin, CDN, and client player. Visibility gaps between these layers are the leading cause of slow incident response during live events. Synthetic monitoring provides early warning, while real-user monitoring connects infrastructure behaviour with viewer experience. Multi-CDN orchestration is increasingly standard for high-value live content, but it requires clear performance measurement, cost controls, and operational runbooks.</p>
<h2>Looking Ahead</h2>
<p>The strongest streaming architectures will be flexible, standards-based, and operationally observable. Broadcasters that avoid unnecessary lock-in and maintain internal expertise in core delivery components will be best positioned to adopt advances as they mature.</p>""",

    "cloud": """<p>Cloud production has moved from experimental model to operational mainstream within broadcast. What was once considered viable only for non-live or lower-priority workflows is now routinely used for live sports, breaking news, and entertainment production. The economics are compelling, but realising the full benefit requires deliberate architecture decisions and a clear understanding of where cloud adds genuine value and where it introduces operational complexity.</p>
<h2>The Anatomy of a Cloud Production Workflow</h2>
<p>A cloud production workflow usually includes contribution, processing, distribution, and coordination. Contribution gets camera feeds into cloud environments. Processing handles switching, audio, graphics, replay, and monitoring. Distribution prepares outputs for broadcast and streaming. Coordination includes rundown management, comms, remote access, and operator control.</p>
<p>SRT and RIST have improved the reliability of contribution over managed and public networks, but engineering discipline still matters. Bandwidth headroom, latency budgets, jitter tolerance, and failover design must be validated before live operation. Cloud production does not remove engineering complexity; it moves much of it into software, networking, and orchestration.</p>
<h2>Remote and At-Home Production Economics</h2>
<p>The business case for REMI and cloud production often begins with reduced travel, accommodation, and equipment movement. A broadcaster covering many events across several locations can centralise more production functions while keeping smaller teams on site. Beyond cost, the larger strategic benefit is content velocity: the ability to cover more events with the same technical base.</p>
<h2>Critical Factors for Cloud Production Success</h2>
<ul><li><strong>Network resilience:</strong> Dual-path connectivity remains essential for live confidence.</li><li><strong>Latency management:</strong> Talkback, programme return, and presenter interaction each have different tolerances.</li><li><strong>Security architecture:</strong> MFA, role-based access, and zero-trust principles are non-negotiable.</li><li><strong>Vendor lock-in:</strong> Open standards support protects long-term operational flexibility.</li></ul>
<h2>What Engineering Teams Need Now</h2>
<p>Engineering teams adopting cloud production need cloud platform skills alongside broadcast signal knowledge. Runbooks, rehearsals, monitoring, and escalation paths are as important as the platform itself. The best results come when technical training is paired with workflow redesign.</p>
<h2>The Road Ahead</h2>
<p>Cloud production will continue to mature as major suppliers add broadcast-specific tooling and as software-defined production platforms gain operational history. Teams that build genuine internal capability will gain a lasting advantage.</p>""",

    "graphics": """<p>Broadcast graphics technology is changing quickly as real-time engines, IP-connected studio infrastructure, and data-driven presentation converge. Graphics teams that once operated as a separate creative function now work inside tightly integrated production workflows where output must synchronise with live data, camera tracking, automation systems, and multi-platform delivery requirements.</p>
<h2>Real-Time Engines Enter Broadcast Production</h2>
<p>Unreal Engine and similar rendering platforms have become practical for live studios, virtual sets, and augmented reality presentation. Their value is not only visual quality but flexibility: scenes can be updated quickly, graphics can react to live inputs, and production teams can create looks that previously required expensive pre-rendered packages.</p>
<p>This shift changes team requirements. Operators need creative skill, but they also need to understand tracking, render performance, data feeds, network control, and failover planning. A beautiful graphic that cannot be trusted in a live programme chain is not broadcast-ready.</p>
<h2>Data-Driven Graphics and Live Integration</h2>
<p>Modern graphics are rarely static. Sports statistics, election results, weather feeds, financial data, and social inputs all pass through APIs or structured data layers before reaching on-air templates. When that pipeline fails, the visible result is missing or incorrect information, so graphics infrastructure must be monitored like any other critical production system.</p>
<h2>Technology Trends Driving Design Decisions</h2>
<ul><li><strong>IP-based control:</strong> Enables centralised and remote graphics operation.</li><li><strong>Augmented reality:</strong> Wider use is being enabled by cheaper tracking and stronger GPUs.</li><li><strong>Cloud rendering:</strong> Burst compute supports graphics-heavy campaigns without permanent hardware investment.</li><li><strong>Template automation:</strong> Structured templates help non-specialist teams produce consistent output under deadline pressure.</li></ul>
<h2>Operational Considerations</h2>
<p>Teams should document every data source, template dependency, tracking input, and render output. Clear dependency maps reduce troubleshooting time during live issues. The most reliable graphics operations combine design ambition with engineering discipline.</p>
<h2>Future Directions</h2>
<p>AI-assisted graphics generation will speed up variation, localisation, and visualisation, but human judgement remains essential for accuracy, editorial tone, and brand consistency. Broadcast graphics will continue moving toward real-time, data-aware, and operationally integrated systems.</p>""",

    "playout": """<p>Playout remains the final, non-negotiable link in the broadcast chain — the point where upstream production work becomes a transmitted service. The technology has moved from dedicated hardware toward software-defined systems, virtualised infrastructure, and cloud-hosted models. This brings flexibility, but it also changes the fault model that operations teams must understand.</p>
<h2>Software-Defined Playout</h2>
<p>Channel-in-a-box platforms consolidate graphics, audio processing, branding, clip playback, automation, and scheduling interfaces into software. For multi-channel operators, this reduces hardware dependency and simplifies channel launch workflows. The gain is real, but the new operational requirement is competence in servers, storage, virtualisation, logging, and network behaviour.</p>
<h2>Cloud Playout</h2>
<p>Cloud playout is useful for pop-up channels, regional feeds, disaster recovery, and lower-complexity linear services. For premium live channels, design must account for connectivity, latency, compliance monitoring, and operational control. Cloud is not automatically cheaper; it is more flexible when used for the right workload.</p>
<h2>Automation and Scheduling Advances</h2>
<ul><li><strong>Integrated MAM workflows:</strong> Reduce manual media movement before transmission.</li><li><strong>Compliance automation:</strong> Loudness, caption, and rating checks reduce repetitive manual work.</li><li><strong>Disaster recovery:</strong> Cloud standby channels can reduce duplicated hardware cost.</li><li><strong>Scheduling intelligence:</strong> Automation can support traffic and continuity decisions, but still needs human oversight.</li></ul>
<h2>Operational Readiness</h2>
<p>Modern playout incidents often require log analysis, API checks, container health review, storage validation, and network inspection. Traditional signal tracing still matters, but it is now only part of the diagnostic toolkit. Monitoring must surface meaningful alerts rather than overwhelming operators with noise.</p>
<h2>What Comes Next</h2>
<p>Playout, streaming distribution, and compliance monitoring are converging into unified transmission platforms. Broadcasters that manage linear and digital outputs together will reduce duplication and improve consistency across services.</p>""",

    "infrastructure": """<p>Broadcast infrastructure is undergoing its most significant change since the move from analogue to digital. The migration from SDI routing to IP-connected architectures based on SMPTE ST 2110 promises flexibility, scalability, and better integration with cloud and remote production workflows. It also demands stronger networking discipline and deeper operational monitoring.</p>
<h2>The SMPTE ST 2110 Model</h2>
<p>ST 2110 transports video, audio, and ancillary data as separate synchronised IP streams over Ethernet. Instead of fixed point-to-point routing, facilities move toward a managed network fabric where senders and receivers are discovered, registered, and connected through orchestration. This is powerful, but it changes troubleshooting from physical signal tracing to network and timing analysis.</p>
<p>Precision Time Protocol is the foundation. Grandmaster selection, boundary clock behaviour, switch configuration, and timing health must be carefully designed and continuously monitored. Many difficult IP broadcast issues are ultimately timing issues.</p>
<h2>Network Design as Broadcast Engineering</h2>
<p>The production network is no longer a passive carrier. It is part of the signal chain. Spine-leaf topology, multicast design, QoS, bandwidth reservation, redundancy, and cybersecurity all become broadcast engineering concerns. The strongest teams combine broadcast domain knowledge with IT networking expertise.</p>
<h2>Infrastructure Trends</h2>
<ul><li><strong>Software-defined networking:</strong> Allows dynamic routing for changing production needs.</li><li><strong>Hybrid SDI/IP facilities:</strong> Most real-world migrations require long transition periods.</li><li><strong>Shared infrastructure:</strong> IP enables more flexible resource allocation across productions.</li><li><strong>Cybersecurity:</strong> Connected production networks must be segmented, monitored, and controlled.</li></ul>
<h2>Skills and Team Structure</h2>
<p>Facilities need engineers who understand both signal integrity and packet networks. Cross-training between broadcast and IT teams is not optional; it is the practical path to reliable operation.</p>
<h2>The Next Phase</h2>
<p>The next advantage will come from tooling: monitoring systems that connect network metrics to media quality, orchestration platforms that reduce manual routing, and operational dashboards that make IP infrastructure understandable during live pressure.</p>""",

    "ai-post-production": """<p>Artificial intelligence is reshaping post-production workflows by automating tasks that once consumed significant time from editors, colourists, assistants, and technical operators. The useful question is not whether AI is impressive in a demo. The useful question is where it improves real workflows without weakening editorial judgement, technical quality, or operator trust.</p>
<h2>Where AI Delivers Real Value</h2>
<p>The strongest current applications are repetitive or pattern-recognition tasks: speech-to-text transcription, scene detection, face recognition, QC checks, loudness validation, object detection, and rough metadata generation. These tools reduce manual effort, but their output must be reviewed when it affects editorial meaning, compliance, rights, or delivery quality.</p>
<p>Quality control automation is particularly valuable at scale. AI-powered QC can detect video artefacts, audio issues, caption problems, and format mismatches faster than manual review. The operational challenge is threshold tuning: too sensitive and operators ignore false positives; too relaxed and real faults pass through.</p>
<h2>AI-Assisted Editing and Discovery</h2>
<p>Searchable archives are one of the most practical AI use cases for broadcasters. Speech recognition, visual analysis, and metadata indexing can help teams find material that would otherwise remain hidden in large libraries. In real operations, the key measure is not number of tags; it is whether users can reliably retrieve the right content under deadline pressure.</p>
<h2>Capabilities Transforming the Sector</h2>
<ul><li><strong>Automated QC:</strong> Speeds up repetitive technical review.</li><li><strong>Highlight generation:</strong> Supports rapid sports and social publishing.</li><li><strong>Localisation:</strong> Accelerates translation, captioning, and dubbing workflows.</li><li><strong>Generative tools:</strong> Assist background removal, cleanup, and promo creation.</li></ul>
<h2>Responsible Adoption</h2>
<p>AI systems can make confident mistakes. A misidentified face, wrong subtitle, or incorrect metadata field can create editorial and legal risk. Human review checkpoints are therefore part of responsible workflow design, not a sign that automation failed.</p>
<h2>The AI Horizon</h2>
<p>Post-production teams that build AI literacy will benefit most. The winning organisations will know what to automate, what to supervise, and what must remain a human editorial decision.</p>""",

    "newsroom": """<p>The modern broadcast newsroom operates under intense pressure to publish across linear television, streaming, social platforms, and digital channels with speed and consistency. Technology now sits at the centre of this operation. The newsroom computer system has evolved from scripting and rundown tool into the integration hub connecting editorial decisions with production, graphics, archive, automation, and digital publishing.</p>
<h2>The Integrated Newsroom Stack</h2>
<p>Contemporary NRCS platforms connect wire ingest, social monitoring, MAM search, video editing, graphics templates, studio automation, and audience analytics. The value is speed: fewer manual handoffs between a developing story and an on-air or online package. But integration also increases dependency. When one system fails, the operational impact can spread quickly.</p>
<p>Engineering teams supporting newsrooms must understand both broadcast systems and IP-based software platforms. The facility network, authentication, cloud services, storage, and APIs are now part of the newsroom production chain.</p>
<h2>Remote and Mobile Journalism</h2>
<p>Bonded cellular, lightweight encoders, cloud editing, and IP contribution have changed field reporting. Journalists can file usable video from locations that once required specialist transmission resources. This expands coverage but increases the need for clear verification, metadata, rights, and quality processes.</p>
<h2>Technology Priorities</h2>
<ul><li><strong>Automated ingest:</strong> Reduces time spent preparing incoming material.</li><li><strong>Multi-platform publishing:</strong> Sends content to several outputs from one editorial workflow.</li><li><strong>Virtual production:</strong> Lowers the cost of visually rich news presentation.</li><li><strong>Verification tools:</strong> Help assess user-generated material before broadcast use.</li></ul>
<h2>People and Process</h2>
<p>Newsroom technology only delivers value when workflows are redesigned around it. Recreating old processes inside new tools usually underperforms. Training, documentation, and rehearsal matter because newsroom staff operate under deadline pressure.</p>
<h2>The Newsroom of Tomorrow</h2>
<p>The next newsroom will automate routine production tasks while preserving human editorial judgement. The strongest organisations will use technology to increase speed without weakening trust.</p>""",

    "featured": """<p>Broadcast technology is evolving across every dimension at once: production workflows are moving to cloud infrastructure, IP-based routing is replacing legacy SDI architectures, artificial intelligence is entering post-production and operations, and streaming delivery is challenging traditional linear models. For media professionals, the challenge is not simply tracking new tools. It is understanding which changes genuinely improve reliability, efficiency, and audience delivery.</p>
<h2>The Transformation Reshaping Broadcasting</h2>
<p>The common thread is the adoption of standards and architectures from the wider IT and internet industry. Ethernet media transport, cloud computing, software-defined systems, and AI capabilities are now part of broadcast strategy. Their adoption brings capability and cost benefits, but also requires new skills, stronger cybersecurity, and more structured operational monitoring.</p>
<p>Technology change creates an evaluation challenge. Trade-show announcements can look transformative long before they are ready for production. Broadcast organisations need internal technical capability to separate useful maturity from vendor momentum.</p>
<h2>Convergence of IT and Broadcast Operations</h2>
<p>The convergence of broadcast engineering and IT operations is visible everywhere. Network engineers configure live media infrastructure. Cloud architects design processing and distribution environments. Cybersecurity teams protect production networks. This convergence is now permanent.</p>
<h2>Industry Priorities</h2>
<ul><li><strong>Sustainability:</strong> More efficient encoding, virtualised systems, and optimised delivery reduce energy impact.</li><li><strong>Audience fragmentation:</strong> Broadcasters must produce more outputs with tighter resources.</li><li><strong>Interoperability:</strong> ST 2110, NMOS, SRT, CMAF, and related standards reduce integration risk.</li><li><strong>Skills pipeline:</strong> Modern broadcast requires hybrid engineering capability.</li></ul>
<h2>What Professionals Need to Focus On</h2>
<p>The most valuable skill is judgement: knowing which technologies improve operations and which add unnecessary complexity. Engagement with standards bodies, vendor briefings, and real-world testing helps teams make stronger decisions.</p>
<h2>A Sector in Motion</h2>
<p>The organisations that adopt new capabilities thoughtfully, with training and governance, will build durable advantage. Technical capability increasingly determines how quickly and reliably broadcasters can serve audiences across platforms.</p>""",
}

BODY_TEMPLATES["fallback"] = BODY_TEMPLATES["featured"]


def build_title(category, index):
    label = CAT_META.get(category, {}).get("label", category.title())
    prefixes = [
        f"How {label} Technology Is Evolving in 2026",
        f"The State of {label}: What Broadcast Professionals Need to Know",
        f"Inside the {label} Revolution: Key Trends and Practical Implications",
    ]
    return prefixes[index % len(prefixes)]


def build_dek(category):
    label = CAT_META.get(category, {}).get("label", category.title())
    return (
        f"An independent editorial overview of the technology forces reshaping "
        f"{label.lower()} for broadcast engineers and media operations professionals."
    )


def build_meta(category, index):
    label = CAT_META.get(category, {}).get("label", category.title())
    metas = [
        f"Explore the key trends, architecture decisions, and operational priorities shaping {label.lower()} technology in broadcast and streaming in 2026.",
        f"The Streamic's editorial analysis of {label.lower()} technology: what broadcast engineers and operations teams need to know right now.",
        f"Independent coverage of {label.lower()} technology developments, workflow implications, and emerging standards for broadcast professionals.",
    ]
    return metas[index % len(metas)]


def make_slug(category, index):
    labels = [
        f"{category}-technology-trends-broadcast-2026",
        f"{category}-workflow-insights-broadcast-professionals",
        f"{category}-infrastructure-and-operations-guide-2026",
    ]
    return slugify(labels[index % len(labels)])


def word_count(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return len(text.split()) if text else 0


def _topic_image(title, cat_slug, seed=""):
    """Return a deterministic, topic-relevant Unsplash image per article."""
    used = getattr(_topic_image, "_used", set())
    _topic_image._used = used

    tl = (title or "").lower()
    pools = [
        (["smpte", "ip routing", "nmos", "infrastructure", "network", "fiber"], ["photo-1558494949-ef010cbdcc31", "photo-1545987796-200677ee1011", "photo-1451187580459-43490279c0fa", "photo-1544197150-b99a580bb7a8"]),
        (["artificial intelligence", "ai-powered", "machine learning", "neural", "generative ai", "automation"], ["photo-1677442135703-1787eea5ce01", "photo-1620712943543-bcc4688e7485", "photo-1655635643532-fa9ba2648cbe", "photo-1635070041078-e363dbe005cb"]),
        (["cloud", "aws", "azure", "saas", "data center"], ["photo-1531297484001-80022131f5a1", "photo-1488229297570-58520851e868", "photo-1573164713988-8665fc963095", "photo-1580584126903-c17d41830450"]),
        (["streaming", "ott", "vod", "hls", "low latency"], ["photo-1616401784845-180882ba9ba8", "photo-1611532736597-de2d4265fba3", "photo-1593642632559-0c6d3fc62b89", "photo-1574717025058-97e3af4ef9b5"]),
        (["graphics", "motion graphics", "virtual set", "ar", "augmented reality"], ["photo-1504639725590-34d0984388bd", "photo-1547658719-da2b51169166", "photo-1518770660439-4636190af475", "photo-1561736778-92e52a7769ef"]),
        (["playout", "master control", "automation", "channel in a box", "on-air"], ["photo-1478737270239-2f02b77fc618", "photo-1590602847861-f357a9332bbc", "photo-1612420696760-0a0f34d3e7d0", "photo-1525059696034-4967a8e1dca2"]),
        (["newsroom", "nrcs", "news production", "journalist", "reporter"], ["photo-1504711434969-e33886168f5c", "photo-1493863641943-9b68992a8d07", "photo-1585829365295-ab7cd400c167", "photo-1557804506-669a67965ba0"]),
        (["post-production", "editing", "nle", "davinci", "premiere", "media composer"], ["photo-1572044162444-ad60f128bdea", "photo-1605106702734-205df224ecce", "photo-1574717025058-97e3af4ef9b5", "photo-1489875347897-49f64b51c1f8"]),
    ]

    cat_pools = {
        "streaming": ["photo-1616401784845-180882ba9ba8", "photo-1611532736597-de2d4265fba3", "photo-1574717025058-97e3af4ef9b5"],
        "cloud": ["photo-1531297484001-80022131f5a1", "photo-1488229297570-58520851e868", "photo-1573164713988-8665fc963095"],
        "ai-post-production": ["photo-1677442135703-1787eea5ce01", "photo-1620712943543-bcc4688e7485", "photo-1572044162444-ad60f128bdea"],
        "graphics": ["photo-1504639725590-34d0984388bd", "photo-1547658719-da2b51169166", "photo-1518770660439-4636190af475"],
        "playout": ["photo-1478737270239-2f02b77fc618", "photo-1590602847861-f357a9332bbc", "photo-1612420696760-0a0f34d3e7d0"],
        "infrastructure": ["photo-1558494949-ef010cbdcc31", "photo-1545987796-200677ee1011", "photo-1451187580459-43490279c0fa"],
        "newsroom": ["photo-1504711434969-e33886168f5c", "photo-1493863641943-9b68992a8d07", "photo-1585829365295-ab7cd400c167"],
        "featured": ["photo-1598488035139-bdbb2231ce04", "photo-1530026405186-ed1f139313f8", "photo-1574717024653-61fd2cf4d44d"],
    }

    for keywords, pids in pools:
        if any(keyword in tl for keyword in keywords):
            for pid in pids:
                if pid not in used:
                    used.add(pid)
                    return f"https://images.unsplash.com/{pid}?w=800&auto=format&fit=crop"

    pool = cat_pools.get(cat_slug, cat_pools["featured"])
    for pid in pool:
        if pid not in used:
            used.add(pid)
            return f"https://images.unsplash.com/{pid}?w=800&auto=format&fit=crop"

    all_pids = [pid for _, pids in pools for pid in pids]
    idx = int(hashlib.md5((seed + title).encode("utf-8")).hexdigest(), 16) % len(all_pids)
    pid = all_pids[idx]
    used.add(pid)
    return f"https://images.unsplash.com/{pid}?w=800&auto=format&fit=crop"


def _load_json(path, default):
    if not os.path.exists(path):
        print(f"  ⚠  Missing {os.path.relpath(path, ROOT)}; using empty fallback.")
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalise_images(images_raw):
    if isinstance(images_raw, list):
        return [img for img in images_raw if isinstance(img, dict)]
    if isinstance(images_raw, dict):
        values = images_raw.values()
        return [img for img in values if isinstance(img, dict)]
    return []


def _normalise_news(news_raw):
    """
    Return iterable pairs: [(category, items)].
    Supports:
    - {"streaming": [{...}], "cloud": [{...}]}
    - [{...}, {...}]
    """
    if isinstance(news_raw, dict):
        return list(news_raw.items())
    if isinstance(news_raw, list):
        return [("featured", news_raw)]
    raise SystemExit(f"ERROR: Unsupported news.json format: {type(news_raw).__name__}")


def main():
    news_raw = _load_json(NEWS_F, [])
    images_raw = _load_json(IMAGES_F, [])

    images_list = _normalise_images(images_raw)
    images_by_slug = {img.get("slug"): img for img in images_list if img.get("slug")}
    images_by_cat = {img.get("category", ""): img for img in images_list if img.get("category")}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    articles = []

    for category, items in _normalise_news(news_raw):
        if not isinstance(items, list):
            print(f"  ⚠  Skipping {category}: expected list, got {type(items).__name__}")
            continue

        if not items:
            print(f"  ⚠  No news items for {category}, skipping.")
            continue

        cat_meta = CAT_META.get(
            category,
            {"label": category.title(), "icon": "📺", "color": "#333", "page": f"{category}.html"},
        )
        body_html = BODY_TEMPLATES.get(category, BODY_TEMPLATES["fallback"])
        count = min(ARTICLES_PER_CATEGORY, len(items))

        generated_for_category = 0
        for i in range(count):
            feed_item = items[i]
            if not isinstance(feed_item, dict):
                print(f"  ⚠  Skipping invalid item in {category}: not an object")
                continue

            title = build_title(category, i)
            slug = make_slug(category, i)
            img_obj = images_by_slug.get(slug) or images_by_cat.get(category)

            item_guid = str(feed_item.get("guid", "") or "")
            legacy_slug = f"rss-{item_guid[:16]}" if item_guid and len(item_guid) >= 16 else None

            rss_teaser = (
                feed_item.get("teaser")
                or feed_item.get("summary")
                or feed_item.get("description")
                or ""
            ).strip()
            card_summary = rss_teaser[:200] if rss_teaser else build_meta(category, i)

            image_url = _topic_image(title, category, slug)

            articles.append(
                {
                    "category": category,
                    "cat_label": cat_meta["label"],
                    "cat_icon": cat_meta["icon"],
                    "cat_color": cat_meta["color"],
                    "cat_page": cat_meta["page"],
                    "title": title,
                    "slug": slug,
                    "guid": item_guid,
                    "legacy_slug": legacy_slug,
                    "dek": build_dek(category),
                    "meta_description": card_summary,
                    "body_html": body_html.strip(),
                    "word_count": word_count(body_html),
                    "source_url": feed_item.get("url", ""),
                    "source_domain": feed_item.get("source", ""),
                    "published": today,
                    "image_url": image_url,
                    "image_credit": img_obj.get("credit", "Unsplash — free to use under the Unsplash License") if img_obj else "Unsplash — free to use under the Unsplash License",
                    "image_license": img_obj.get("license", "Unsplash License") if img_obj else "Unsplash License",
                    "image_license_url": img_obj.get("license_url", "https://unsplash.com/license") if img_obj else "https://unsplash.com/license",
                }
            )
            generated_for_category += 1

        print(f"  {category}: {generated_for_category} articles ({word_count(body_html)} words each template)")

    if not articles:
        raise SystemExit("ERROR: No articles generated — aborting.")

    os.makedirs(os.path.dirname(OUTPUT_F), exist_ok=True)
    with open(OUTPUT_F, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(articles)} articles → data/generated_articles.json")


if __name__ == "__main__":
    main()
