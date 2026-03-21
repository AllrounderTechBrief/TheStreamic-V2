"""
scripts/generate_originals.py
Read data/news.json + data/images.json.
Generate up to 3 original 700-900 word articles per category using
fully deterministic templates — no LLM, no scraped text.
Write data/generated_articles.json.
"""
import hashlib, json, os, re
from datetime import datetime, timezone
from slugify import slugify

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NEWS_F   = os.path.join(ROOT, "data", "news.json")
IMAGES_F = os.path.join(ROOT, "data", "images.json")
OUTPUT_F = os.path.join(ROOT, "data", "generated_articles.json")
ARTICLES_PER_CATEGORY = 3
SITE_URL = os.environ.get("SITE_BASE_URL", "https://www.thestreamic.in")

CAT_META = {
    "featured":           {"label":"Featured",            "icon":"⭐",  "color":"#1d1d1f","page":"featured.html"},
    "streaming":          {"label":"Streaming",           "icon":"📡",  "color":"#0071e3","page":"streaming.html"},
    "cloud":              {"label":"Cloud Production",    "icon":"☁️",  "color":"#5856d6","page":"cloud.html"},
    "graphics":           {"label":"Graphics",            "icon":"🎨",  "color":"#FF9500","page":"graphics.html"},
    "playout":            {"label":"Playout",             "icon":"▶️",  "color":"#34C759","page":"playout.html"},
    "infrastructure":     {"label":"Infrastructure",      "icon":"🏗️",  "color":"#8E8E93","page":"infrastructure.html"},
    "ai-post-production": {"label":"AI & Post-Production","icon":"🎬",  "color":"#FF2D55","page":"ai-post-production.html"},
    "newsroom":           {"label":"Newsroom",            "icon":"📰",  "color":"#D4AF37","page":"newsroom.html"},
}
CAT_IMAGES = {
    "featured":           "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=900&auto=format&fit=crop",
    "streaming":          "https://images.unsplash.com/photo-1616401784845-180882ba9ba8?w=900&auto=format&fit=crop",
    "cloud":              "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=900&auto=format&fit=crop",
    "graphics":           "https://images.unsplash.com/photo-1547658719-da2b51169166?w=900&auto=format&fit=crop",
    "playout":            "https://images.unsplash.com/photo-1612420696760-0a0f34d3e7d0?w=900&auto=format&fit=crop",
    "infrastructure":     "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=900&auto=format&fit=crop",
    "ai-post-production": "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=900&auto=format&fit=crop",
    "newsroom":           "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=900&auto=format&fit=crop",
}

# ---------------------------------------------------------------------------
# Body templates — ~830 words each, all original prose, no feed text reused
# ---------------------------------------------------------------------------
T = {}

T["streaming"] = """<p>The streaming technology landscape continues to evolve at pace, driven by broadcaster demand for lower latency, higher resilience, and more flexible delivery architectures. As OTT audiences grow globally, the engineering decisions made today — codec selection, CDN strategy, origin architecture — will define competitive advantage for years ahead. Understanding the forces shaping this space is essential for anyone involved in video delivery infrastructure, from platform engineers to operations managers overseeing live event delivery at scale.</p>

<h2>The Shifting Architecture of Video Delivery</h2>
<p>Modern streaming pipelines increasingly separate ingest, packaging, and delivery into discrete, independently scalable layers. This decoupled approach allows operators to upgrade individual components — swapping an encoder, changing a packaging format, or onboarding a new CDN partner — without disrupting the entire chain. The adoption of CMAF (Common Media Application Format) has been a significant enabler, providing a single-origin media format compatible with both HLS and DASH players, reducing storage duplication and simplifying origin management across large content libraries with diverse device requirements.</p>

<p>Codec evolution continues to shape streaming infrastructure decisions. AV1 is gaining traction as a royalty-free alternative to HEVC for high-efficiency delivery, particularly for platforms with the compute resources to support its more demanding encoding requirements. LCEVC (Low Complexity Enhancement Video Coding) offers a different approach, using an enhancement layer above a base codec to improve perceived quality at equivalent bitrates, with relatively modest encoder complexity overhead making it appealing for live streaming applications where latency and processing cost are primary constraints on codec selection.</p>

<h2>Why This Matters to Broadcast Engineers</h2>
<p>For broadcast engineers, the transition from traditional satellite and cable delivery to IP-based streaming represents the most significant workflow transformation in a generation. The operational demands are different: instead of managing physical transmission infrastructure, teams are now responsible for cloud configurations, API integrations, and real-time monitoring dashboards. The skills required have broadened considerably, requiring familiarity with Kubernetes, object storage, and observability platforms alongside traditional broadcast expertise in signal quality and redundancy design. Engineering teams that invest in developing this cross-domain competency will be significantly better positioned to manage the increasingly complex delivery environments their organisations depend upon for revenue and audience reach.</p>

<h2>Key Trends Shaping the Sector</h2>
<ul>
<li><strong>Low-latency live streaming:</strong> WebRTC and LL-HLS protocols are enabling sub-three-second glass-to-glass latency for live sports and news, closing the gap with traditional broadcast and unlocking new interactive viewing experiences for connected audiences across all device types and screen sizes.</li>
<li><strong>Per-title encoding optimisation:</strong> Machine learning models now analyse each piece of content to determine optimal encoding parameters per shot type, reducing bitrate requirements by up to thirty percent without perceptible quality loss, with direct impact on CDN delivery costs and storage requirements at scale across large libraries.</li>
<li><strong>Edge computing integration:</strong> Moving transcoding and packaging workloads to CDN edge nodes reduces origin load and improves responsiveness for regional audiences, particularly during high-concurrency live events where centralised infrastructure faces extreme peak demand and latency requirements are most stringent for viewer experience quality.</li>
<li><strong>Sustainability metrics:</strong> Leading streaming platforms are publishing carbon-per-stream figures and implementing bitrate caps and quality-adaptive algorithms specifically designed to reduce network energy consumption while maintaining the audience satisfaction scores their advertising and subscription models depend upon for commercial performance.</li>
</ul>

<h2>Practical Implications for Operations Teams</h2>
<p>Operations teams managing streaming infrastructure should prioritise investment in end-to-end monitoring that spans origin, CDN, and client player. Visibility gaps between these layers are the leading cause of slow incident response times during live events where audiences and commercial partners have low tolerance for quality failures. Synthetic monitoring — simulated stream requests from geographically distributed probes — provides early warning of delivery issues before real viewer impact is detected. Pair this with real-user monitoring (RUM) data to correlate infrastructure metrics with actual rebuffering rates and quality scores, creating an actionable picture of delivery health that bridges the gap between infrastructure telemetry and audience experience measurement in operational environments.</p>

<p>Multi-CDN orchestration is increasingly a standard practice for high-value live content, with intelligent routing directing viewer requests to the best-performing CDN in real time based on availability, performance, and cost parameters. Implementing this capability requires investment in orchestration platforms and in the operational processes to manage CDN relationships and performance measurement, but delivers measurable resilience improvements for events where streaming interruption has significant commercial or reputational consequences for the broadcasting organisation.</p>

<h2>Looking Ahead</h2>
<p>The next eighteen months will see continued consolidation among streaming technology vendors, with platform players acquiring point-solution providers to offer more integrated stacks that reduce the integration burden on broadcast technology teams. Broadcasters evaluating their technology partnerships should assess vendor roadmaps for AI-assisted quality control, multi-CDN orchestration capabilities, and support for emerging standards. The organisations that invest in flexible, standards-based architectures today, avoiding vendor lock-in where possible and maintaining internal expertise in core platform components, will be best positioned to adopt advances as they mature and to negotiate effectively with technology partners from a position of genuine technical understanding and operational confidence."""

T["cloud"] = """<p>Cloud production has moved from an experimental model to operational mainstream within broadcast. What was once considered viable only for non-live, low-priority workflows is now routinely handling live sports, breaking news, and high-profile entertainment production across major broadcast organisations globally. The economics are compelling, but realising the full benefit requires deliberate architecture decisions and a clear understanding of where cloud adds genuine value and where it introduces complexity that must be managed carefully by engineering and operations teams with appropriate skills and processes in place.</p>

<h2>The Anatomy of a Cloud Production Workflow</h2>
<p>A fully cloud-native production workflow typically comprises four layers: contribution (getting camera feeds to cloud), processing (vision mixing, graphics, audio mixing, commentary), distribution (encoding and delivery), and coordination (rundown management, communications, remote access). Each layer can be sourced independently, allowing broadcasters to transition incrementally rather than undertaking a single high-risk cutover. Many organisations begin with cloud-based replay and highlights processing, where latency tolerance is higher, before extending to live switching environments where the performance and resilience requirements are more demanding and where production staff confidence in the technology is equally important to technical performance.</p>

<p>The contribution layer — reliably getting high-quality video signals from field locations to cloud processing environments — remains one of the most technically challenging aspects of cloud production. SRT (Secure Reliable Transport) and RIST (Reliable Internet Stream Transport) protocols have significantly improved the reliability of contribution over public internet paths, with forward error correction and automatic retransmission mechanisms designed specifically for the characteristics of internet-based media transport. Understanding the behaviour and configuration of these protocols under different network conditions is now essential knowledge for broadcast engineers designing cloud production workflows for live events in varied location environments.</p>

<h2>Remote and At-Home Production Economics</h2>
<p>The financial case for remote and at-home production (REMI) via cloud rests on reducing travel, accommodation, and on-site technical staff costs for events. For a broadcaster covering fifty events annually across multiple geographies, the saving in production travel alone can justify significant cloud infrastructure investment over a multi-year period. Beyond cost, cloud production enables smaller editorial teams to handle more events simultaneously, with centralised technical operations supporting multiple remote productions from a single facility — a model increasingly adopted by regional sports broadcasters seeking to expand their event coverage without proportional increases in technical headcount or capital investment in portable production equipment.</p>

<h2>Critical Factors for Cloud Production Success</h2>
<ul>
<li><strong>Network resilience:</strong> Cloud production is only as reliable as the connectivity linking field sites to cloud infrastructure. Dual-path designs using bonded cellular alongside fibre or satellite provide the redundancy required for live broadcast confidence, particularly for events in locations where fixed-line connectivity is unreliable or unavailable and where transmission failures have significant commercial consequences.</li>
<li><strong>Latency management:</strong> Round-trip latency between a remote presenter and a cloud production environment must be managed carefully across the entire production team. Talkback systems, interruptible fold-back, and programme return all have different latency tolerances that must be understood before going live to avoid communication breakdowns during complex live productions.</li>
<li><strong>Security architecture:</strong> Cloud production surfaces that were previously air-gapped are now reachable via the public internet. Zero-trust network architecture, multi-factor authentication, and role-based access control are non-negotiable requirements for production environments handling live broadcast signals of significant commercial value and editorial sensitivity.</li>
<li><strong>Vendor lock-in risk:</strong> Proprietary cloud production platforms can create dependency on a single supplier whose pricing and roadmap decisions the broadcaster cannot influence. Evaluating vendors against open standards support provides a hedge against future migration costs and preserves the organisation's technology independence.</li>
</ul>

<h2>What Engineering Teams Need Now</h2>
<p>Engineering teams adopting cloud production should invest in staff development alongside infrastructure. Cloud platform skills — particularly in AWS Media Services, Azure Media, or equivalent — are now as important as traditional broadcast signal processing knowledge for engineers responsible for live production infrastructure. Pair technical upskilling with process change: cloud production requires tighter pre-production planning, documented runbooks for failover scenarios, and clear escalation paths when issues arise mid-transmission without an on-site technical team able to respond physically to equipment failures or connectivity problems during live events.</p>

<h2>The Road Ahead</h2>
<p>The maturation of cloud production technology will accelerate over the next two years as major cloud providers deepen their broadcast-specific tooling and as software-defined production platforms gain track record at scale across the industry. Broadcasters that have built genuine internal cloud production capability — staff who understand both the technology and the operational disciplines required — will gain increasing competitive advantage in content velocity: the ability to get compelling content to air faster, at lower cost, from more locations than was previously possible with production models dependent on physical technical infrastructure at every event venue and production location.</p>"""

T["graphics"] = """<p>Broadcast graphics technology is undergoing a period of rapid change, driven by the convergence of real-time game engines, IP-connected studio infrastructure, and growing audience expectation for visually sophisticated on-screen presentation. Graphics teams that once operated largely independently now work within tightly integrated production workflows where their output must synchronise precisely with automated data feeds, augmented reality tracking systems, and cloud-based distribution platforms. The skillset required of broadcast graphics professionals has expanded significantly, and the technical demands on the infrastructure supporting graphics production have grown accordingly across every type of broadcast environment.</p>

<h2>Real-Time Engines Enter Broadcast Production</h2>
<p>Unreal Engine and similar real-time rendering platforms have established a firm foothold in broadcast graphics. Their ability to render photorealistic virtual environments at broadcast frame rates, combined with support for IP-based control protocols, makes them genuinely viable for live studio and virtual set applications at scale. The learning curve for graphics operators transitioning from traditional CG tools is real, but vendors are investing in broadcast-specific workflow abstractions that reduce dependency on deep game development knowledge for day-to-day operation, making these powerful platforms accessible to a broader range of production teams and budget levels than was previously the case in broadcast graphics technology.</p>

<p>The shift toward real-time rendering also changes the economics of graphics production significantly. Traditional CG workflows required substantial pre-rendering time, limiting the ability to update graphics in response to breaking developments during live coverage or to adapt quickly to last-minute editorial changes. Real-time engines eliminate this constraint, enabling graphics to be updated or entirely regenerated within seconds, fundamentally changing what is achievable in live broadcast environments and opening new creative possibilities for productions that previously relied on static pre-rendered graphic packages prepared hours or days before transmission.</p>

<h2>Data-Driven Graphics and Live Integration</h2>
<p>Modern broadcast graphics are rarely designed in isolation from data. Sports statistics, election results, financial market data, and weather feeds are all consumed in real time and rendered dynamically through graphics templates. The infrastructure connecting data sources to graphics engines — APIs, message queues, data normalisation layers — is now a critical part of the graphics technology stack. Failures in this pipeline result in missing or incorrect on-screen data, with immediate audience-facing consequences in live broadcast environments where accuracy and timeliness are fundamental editorial values that audiences and regulators both expect and demand.</p>

<h2>Technology Trends Driving Design Decisions</h2>
<ul>
<li><strong>IP-based graphics control:</strong> Migration from serial and proprietary control protocols to IP-based interfaces enables tighter integration with automation systems and remote operation, reducing the number of people required on the studio floor during live production and enabling centralised graphics control across multiple simultaneous productions from a single technical hub facility.</li>
<li><strong>Augmented reality at scale:</strong> AR graphics have expanded beyond major events into regular sports and news programming, supported by declining costs for camera tracking hardware and improvements in rendering performance at broadcast frame rates across a wider range of production budgets and facility configurations than was previously practical.</li>
<li><strong>Cloud rendering pipelines:</strong> Pre-rendered and semi-real-time graphics elements are increasingly processed in cloud environments, with finished assets delivered to on-premises playout systems, allowing graphics-intensive productions to access compute resources on demand without equivalent capital investment in on-premises hardware that would otherwise sit underutilised between productions.</li>
<li><strong>Automated template systems:</strong> News and sports graphics increasingly use template-driven systems that generate consistent, brand-compliant outputs from structured data inputs, reducing manual graphic design work under deadline pressure and enabling non-specialist operators to produce on-air graphics in time-pressured breaking news environments where speed and consistency are the primary requirements.</li>
</ul>

<h2>Operational Considerations for Graphics Teams</h2>
<p>Graphics operators and supervisors working in these environments need a broader technical understanding than was traditionally required of broadcast graphics professionals. Network fundamentals, data feed troubleshooting, and an understanding of render pipeline dependencies are now part of the operational skill set alongside the design and animation expertise that has always been central to broadcast graphics work. Teams should document their data integration points rigorously — knowing exactly which data source feeds which on-screen element is essential for rapid fault resolution when live broadcasts encounter issues with incorrect or missing graphic content under the unforgiving time pressure of live transmission.</p>

<h2>Future Directions</h2>
<p>AI-assisted graphics generation, where machine learning models automatically create data visualisations from raw inputs or suggest design variations based on brand guidelines, is an emerging capability that will reduce time-to-air for complex graphic sequences while maintaining creative quality and brand consistency. The graphics vendors investing in this capability now are building a meaningful competitive advantage as broadcast organisations look for ways to increase content output without proportional increases in creative and technical resource, particularly in the context of expanding multi-platform content demands that require consistent high-quality graphic presentation across linear and digital distribution channels simultaneously.</p>"""

T["playout"] = """<p>Playout remains the final, non-negotiable link in the broadcast chain — the point at which all upstream production effort is converted into a transmitted signal that reaches audiences. The technology underpinning playout has transformed dramatically over the past decade, moving from dedicated proprietary hardware to software-defined systems running on commodity servers, and increasingly to cloud-hosted environments that offer new levels of flexibility and cost efficiency. This evolution brings significant operational advantages, but also introduces new disciplines that broadcast engineers and operations teams must master to maintain the reliability and compliance standards that broadcast transmission demands from every transmission event.</p>

<h2>Software-Defined Playout: The New Normal</h2>
<p>Channel-in-a-box solutions, which consolidate multiple playout functions — graphics, audio processing, branding, clip playback — into a single software platform, are now the dominant deployment model for new channel launches and technology refreshes across the broadcast industry. Mature software playout platforms provide feature parity with the dedicated hardware they replace, with the additional benefit of software-update-driven capability growth rather than hardware replacement cycles that required significant capital expenditure and operational disruption. The shift also enables virtualisation, allowing playout channels to run as instances on shared infrastructure with significant capital and operational cost benefits, particularly for multi-channel operators managing large numbers of linear channels with different programming and technical format requirements.</p>

<p>The migration from hardware to software playout has also changed the maintenance and reliability model for broadcast operations. Instead of hardware spares inventories and engineer callouts for physical fault resolution, software playout demands expertise in virtualisation platforms, storage performance management, and network configuration. Mean time to recovery for software-defined systems is often faster than hardware equivalents when properly designed and monitored, but the failure modes are different and require different diagnostic skills from operations teams accustomed to traditional broadcast hardware troubleshooting in live transmission environments.</p>

<h2>Cloud Playout: Deployment Models and Trade-offs</h2>
<p>Cloud playout has moved from proof-of-concept to production deployment across a growing number of channels, particularly for linear channels with lower resilience requirements and for pop-up or seasonal channel operations where the ability to spin up capacity on demand provides significant operational flexibility and capital cost advantages. The trade-offs remain real: cloud playout introduces dependency on internet connectivity for distribution, adds latency considerations for graphics and live events, and requires operators to develop cloud platform skills. For the right use cases, the operational flexibility and reduced capital commitment are compelling arguments that justify the transition investment and operational change management required.</p>

<h2>Automation and Scheduling Advances</h2>
<ul>
<li><strong>AI-driven scheduling:</strong> Machine learning models are being applied to traffic scheduling to optimise advertising placement, minimise repeat adjacencies, and automate compliance checks that previously required manual review by scheduling staff, improving both operational efficiency and regulatory compliance consistency across large channel portfolios with complex scheduling requirements.</li>
<li><strong>Integrated MAM and playout workflows:</strong> Tighter integration between media asset management systems and playout automation reduces manual media movement, with content automatically transferred to nearline storage and prepared for transmission based on confirmed schedule data, eliminating a significant source of operator error and last-minute preparation issues.</li>
<li><strong>Disaster recovery via cloud:</strong> Cloud-hosted disaster recovery environments for on-premises playout systems provide cost-effective resilience, with secondary channels maintained in cloud infrastructure that can be activated within minutes of a primary system failure, significantly reducing the capital cost of maintaining fully redundant on-premises playout systems for all channels in a portfolio.</li>
<li><strong>Monitoring and compliance automation:</strong> Automated loudness correction, closed caption validation, and content rating verification are increasingly embedded within the playout chain, reducing the burden on compliance teams while ensuring regulatory requirements are met consistently across all channels and output formats without reliance on manual review processes.</li>
</ul>

<h2>Operational Readiness for Modern Playout</h2>
<p>Broadcast operations teams managing software and cloud playout environments require updated incident response processes appropriate to the technology they operate. Traditional broadcast fault isolation — tracing a signal path through physical hardware — translates to log analysis, container health monitoring, and network packet inspection in virtualised environments. Investing in training and in observability tooling that surfaces meaningful alerts without overwhelming operators with noise is as important as the playout technology itself for maintaining operational confidence during the time-pressured incidents that live broadcast transmission inevitably encounters across any sufficiently complex multi-channel operation.</p>

<h2>What Comes Next</h2>
<p>The convergence of playout, distribution, and streaming operations into unified transmission platforms will accelerate over the coming years as the industry moves beyond treating linear and streaming as separate technical domains requiring separate operational teams. Broadcasters operating both linear and streaming channels will benefit from single platforms that manage scheduling, graphics, and delivery across all output types, reducing operational overhead and enabling consistent brand presentation regardless of the viewer's chosen platform. Vendors competing in this unified transmission space are investing heavily, and the competitive pressure will drive rapid feature advancement that creates real opportunities for broadcast operators to simplify their technology stacks while expanding their distribution reach and audience accessibility.</p>"""

T["infrastructure"] = """<p>Broadcast infrastructure is in the midst of its most fundamental transition since the move from analogue to digital — the migration from SDI-based signal routing to IP-connected architectures based on SMPTE ST 2110 and related standards. This shift promises unprecedented flexibility in facility design, the ability to share infrastructure across multiple productions, and simpler integration with cloud environments and remote production workflows. It also demands new engineering competencies, more rigorous network design disciplines, and a rethinking of resilience architectures that served the broadcast industry reliably for decades. For broadcast engineers navigating this transition, understanding both the technical and operational dimensions of IP infrastructure is essential for successful deployment and ongoing operation.</p>

<h2>The SMPTE ST 2110 Infrastructure Model</h2>
<p>SMPTE ST 2110 defines a suite of standards for transporting media — video, audio, ancillary data — as separate, synchronised IP streams over standard Ethernet infrastructure. The architecture enables any device on the network to send or receive any signal, subject to network capacity and NMOS (Networked Media Open Specifications) registration and discovery protocols. In practice, this replaces dedicated point-to-point coaxial and fibre routing with a managed network fabric, with all the operational benefits and complexity that entails for engineering teams accustomed to the deterministic and physically traceable behaviour of traditional SDI signal routing in broadcast facilities.</p>

<p>Precision Time Protocol (PTP) synchronisation is the foundation of ST 2110 infrastructure reliability, providing the sub-microsecond timing accuracy required to synchronise media streams across the network. Getting PTP right — selecting appropriate grandmaster clocks, configuring network switch support correctly, and monitoring timing health continuously — is one of the most technically demanding aspects of IP broadcast facility design. Engineering teams that invest in deep PTP expertise early in their IP infrastructure journey will avoid a significant proportion of the synchronisation-related issues that have complicated deployments that underestimated the importance of timing infrastructure design and ongoing monitoring.</p>

<h2>Network Design as Broadcast Engineering</h2>
<p>For broadcast facilities adopting IP infrastructure, the network is no longer a passive carrier — it is a critical active component in the production signal chain. Spine-leaf network architectures, precision time protocol synchronisation, and quality-of-service configuration are now core broadcast engineering responsibilities. Teams need to work closely with IT networking specialists, or develop these skills internally, to design and operate infrastructure that meets broadcast reliability and latency requirements while leveraging standard data networking technology available from the broad IT vendor ecosystem at competitive prices and with extensive industry support resources.</p>

<h2>Infrastructure Trends Broadcast Engineers Must Track</h2>
<ul>
<li><strong>Software-defined networking in broadcast:</strong> SDN controllers that manage network topology and routing rules programmatically are enabling dynamic infrastructure reconfiguration to support changing production requirements without manual intervention, particularly valuable for facilities supporting multiple simultaneous productions with different routing and bandwidth requirements across shared network infrastructure.</li>
<li><strong>Shared infrastructure models:</strong> IP architecture enables multiple productions or broadcasters to share common network and compute infrastructure, amortising capital costs across more users and enabling flexible resource allocation based on current production schedules rather than requiring peak-capacity dedicated hardware for every production environment in the facility.</li>
<li><strong>Hybrid SDI and IP facilities:</strong> Most major facility upgrades involve a transitional period with SDI and IP infrastructure coexisting, connected via gateway devices. Managing this hybrid environment — signal path documentation, fault isolation across technology boundaries — is a practical challenge that many engineering teams are navigating in live production environments right now as upgrades proceed incrementally.</li>
<li><strong>Cybersecurity in production networks:</strong> The convergence of broadcast and IT networks eliminates the traditional air gap that protected broadcast infrastructure from external threats. Network segmentation, device authentication, and continuous security monitoring are essential disciplines for any IP-connected broadcast facility operating in an environment of increasing cyber threat activity targeting media and entertainment organisations globally.</li>
</ul>

<h2>Skills and Team Structure for IP Infrastructure</h2>
<p>Broadcast facilities managing IP infrastructure increasingly require engineers with both broadcast domain knowledge and data networking expertise in a combination that is genuinely rare in the available talent market. Recruitment is challenging, making internal development programmes essential for most organisations. Structured cross-training between broadcast engineering and IT networking teams, supported by vendor-led certification programmes, is the most effective path to building the competency required to operate complex ST 2110 environments confidently under the demands of live production schedules where infrastructure failures have immediate on-air consequences and limited tolerance for extended troubleshooting periods.</p>

<h2>The Next Phase of Infrastructure Evolution</h2>
<p>As ST 2110 adoption matures and the installed base of IP-capable devices grows, attention is shifting to the operational tooling layer: monitoring systems that understand broadcast signal quality metrics alongside network performance indicators, orchestration platforms that automate resource allocation across shared infrastructure, and integration with cloud environments for elastic capacity during peak demand periods. The facilities that invest in this tooling alongside their core IP infrastructure deployment will derive the greatest operational benefit from their technology transition investment and will be best positioned to extend their capabilities as the ecosystem continues to develop and as new production workflows emerge that depend on the flexibility that IP infrastructure uniquely provides.</p>"""

T["ai-post-production"] = """<p>Artificial intelligence is reshaping post-production workflows across the broadcast industry, automating tasks that once consumed significant time from skilled editors, colourists, and technical operators. From automated speech-to-text transcription enabling searchable media archives to AI-assisted colour grade matching across episodic content, the applications are diverse and growing rapidly in their capability and reliability. For post-production professionals, understanding where AI genuinely accelerates workflow and where it requires careful human oversight is essential for effective adoption that delivers real productivity improvements without compromising the editorial and technical quality standards that define broadcast output quality.</p>

<h2>Where AI Delivers Real Post-Production Value</h2>
<p>The clearest current AI applications in post-production are in tasks that are repetitive, rules-based, or pattern-recognition-intensive. Automated loudness normalisation, speech transcription for metadata generation, face recognition for talent tagging, and scene detection for rough-cut assembly all fall into this category. These applications reduce manual processing time substantially — in some deployments by sixty to eighty percent for specific workflow steps — freeing editorial staff to focus on creative and editorial judgement tasks where human skill and experience remains irreplaceable by automated systems. The business case for these applications is straightforward and the technology is production-proven at scale across major broadcast and streaming organisations with large content volumes and demanding operational timelines.</p>

<p>Quality control automation represents one of the highest-value AI applications in post-production operations at scale. Manual QC of large content volumes is expensive, time-consuming, and subject to human fatigue-related errors that automated systems do not experience. AI-powered QC systems detect audio sync issues, video artefacts, caption compliance failures, and aspect ratio problems consistently across entire libraries, at speeds that make previously impractical QC coverage achievable within normal production timelines. The key operational requirement is configuring sensitivity thresholds appropriately for the content type and destination platform, which requires experienced QC professionals working alongside the AI systems rather than being entirely replaced by them in the quality assurance process.</p>

<h2>AI-Assisted Editing and Content Discovery</h2>
<p>More sophisticated AI applications in post-production include content-based search that enables operators to find specific moments within large media archives using natural language queries rather than manual browsing through timecoded logs and clip descriptions. These systems use a combination of speech recognition, visual analysis, and metadata indexing to make large archives genuinely searchable in ways that transform the economics of archive content exploitation for news and sports broadcasters with deep libraries that have historically been underutilised due to the prohibitive time cost of manual content discovery workflows.</p>

<h2>Key AI Capabilities Transforming the Sector</h2>
<ul>
<li><strong>Automated quality control:</strong> AI-powered QC systems can analyse video and audio at scale, detecting artefacts, audio sync issues, and compliance failures far faster than manual review, with configurable sensitivity thresholds that balance detection completeness against false-positive rates in operational deployment across diverse content types and delivery destinations.</li>
<li><strong>Intelligent highlight generation:</strong> Sports broadcast platforms are deploying AI that identifies key moments in near-real time, automatically generating highlight packages that can be published across digital and social platforms within minutes of the live event conclusion, significantly extending the commercial value of live sports rights for broadcasters and platform operators.</li>
<li><strong>Localisation workflow automation:</strong> AI translation and dubbing tools are accelerating content localisation, enabling broadcasters and streaming platforms to prepare international versions in hours rather than days, expanding the economic case for multi-territory distribution of content that would previously have been too expensive to localise comprehensively for all available markets.</li>
<li><strong>Generative production tools:</strong> Generative AI is beginning to enter production tool suites for tasks such as background removal, object removal, and synthetic voiceover generation for promotional content — capabilities that will become more prevalent as quality improves and the creative and legal frameworks for their use in broadcast production are established by the industry.</li>
</ul>

<h2>Responsible AI Adoption in Post-Production</h2>
<p>Broadcast organisations adopting AI in post-production workflows need governance frameworks that address accuracy requirements, editorial oversight responsibilities, and the handling of AI-generated output in content that reaches audiences. Automated systems can make errors — a misidentified face in a news archive, an incorrect transcription used as broadcast subtitles — with reputational and potentially legal consequences that make human review checkpoints at appropriate stages of AI-assisted workflows essential components of a responsible implementation, not optional additions that can be removed to maximise throughput efficiency in high-volume content operations.</p>

<h2>The Post-Production AI Horizon</h2>
<p>The pace of AI capability development in the post-production space will continue to accelerate significantly over the coming years. Organisations that build internal AI literacy — staff who understand what these tools can and cannot do reliably, and how to configure, evaluate, and improve them effectively in operational contexts — will be better positioned to adopt advances quickly and maintain competitive content production capability. The technology is not a destination but an ongoing capability evolution that will reward continuous learning and experimental adoption alongside the careful operational governance that maintains the editorial and technical quality standards audiences expect from professional broadcast content at every stage of the production and delivery chain.</p>"""

T["newsroom"] = """<p>The modern broadcast newsroom operates in an environment of intense competitive pressure, with audiences consuming news across linear television, streaming platforms, social media, and digital publications simultaneously and expecting consistent quality and speed across every channel. Technology plays a central role in enabling newsroom teams to gather, process, and distribute content at the speed this multi-platform reality demands. The newsroom computer system, once primarily a rundown management and scripting tool, has evolved into the integration hub connecting editorial workflow with production, graphics, audio, and digital distribution systems in ways that fundamentally change the operational model of contemporary broadcast news production and the skills required from news production staff.</p>

<h2>The Integrated Newsroom Technology Stack</h2>
<p>Contemporary NRCS platforms integrate with a wide ecosystem of connected systems: wire services for automated story ingest, social media monitoring tools for early-breaking story detection, MAM systems for video search and editing, graphics engines for template-driven packaging, and audience analytics platforms that inform editorial decisions about story prioritisation and treatment. The value of this integration lies in reducing the manual steps between a developing story and an on-air package — every automated handoff between systems reduces the time from editorial decision to transmission, a critical advantage in breaking news scenarios where speed directly affects audience reach, competitive positioning, and the commercial performance of news programming for advertisers and platform partners.</p>

<p>The transition from dedicated hardware control surfaces to software-based production interfaces, accelerated by the operational learnings of remote production periods, has made newsroom production more flexible but also more dependent on reliable network infrastructure within the facility and to external contribution points. Engineering teams supporting newsroom technology must now maintain both the traditional broadcast signal infrastructure and the IP network that supports NRCS platforms, software-based graphics engines, and cloud-connected services — a significantly expanded operational responsibility that requires updated skills, monitoring approaches, and incident response processes compared to traditional broadcast facility engineering roles.</p>

<h2>Remote and Mobile Journalism Infrastructure</h2>
<p>The infrastructure supporting remote journalism has improved dramatically, enabling correspondents and contributing reporters to file broadcast-quality video from locations that would have required satellite uplink equipment and specialist technical crew a decade ago. Bonded cellular encoders, cloud-based editing platforms accessible from any connected device, and IP-based contribution to centralised production facilities have democratised live broadcast capability significantly. News organisations are expanding geographic coverage without proportional increases in technical crew, reshaping the economics of field journalism and enabling coverage of stories in locations that would previously have been financially inaccessible for organisations outside the largest global news broadcasters.</p>

<h2>Technology Priorities Reshaping Newsroom Operations</h2>
<ul>
<li><strong>Automated content ingest and tagging:</strong> AI-powered systems that automatically ingest, transcribe, and tag incoming video content — including agency feeds, user-generated contributions, and archive material — dramatically reduce the time researchers and editors spend locating relevant material under deadline pressure during major breaking news events where speed of content assembly is critical.</li>
<li><strong>Multi-platform publishing workflows:</strong> Newsroom systems that publish simultaneously to linear broadcast, streaming platforms, and social media from a single editorial workflow reduce the operational overhead of multi-platform distribution while maintaining editorial consistency and rights management compliance across all output channels from a single editorial decision point.</li>
<li><strong>Virtual and remote production:</strong> Cloud-based studio environments and virtual set infrastructure are enabling news organisations to produce compelling broadcast-quality output from facilities that would not have supported television production under traditional technology constraints, significantly reducing the capital cost of establishing new broadcast news operations or expanding existing ones into new geographic markets.</li>
<li><strong>Audience verification workflows:</strong> The volume of user-generated content reaching newsrooms has driven investment in geolocation tools, metadata analysis platforms, and AI-assisted visual verification systems that support editorial teams in assessing the authenticity and provenance of submitted material before it is used in broadcast output where accuracy and verification standards are fundamental editorial and legal obligations.</li>
</ul>

<h2>People and Process Alongside Technology</h2>
<p>Technology investment in newsroom systems delivers its full value only when accompanied by process redesign and structured staff development programmes. NRCS implementations that replicate existing workflows digitally, without rethinking the editorial and production process around new capabilities, consistently underperform against the potential of the technology investment. The most successful newsroom technology programmes pair technical deployment with detailed workflow analysis, structured change management, and training that helps editorial and production staff use new systems effectively under the time pressure of live news broadcasting where operational hesitation has immediate on-air consequences.</p>

<h2>The Newsroom of Tomorrow</h2>
<p>The newsroom technology trajectory points toward increased automation of routine production tasks — standard graphics generation, social media clipping, highlights packaging — that will allow editorial teams to concentrate scarce journalistic resources on original reporting and the editorial judgement that defines the value of professional broadcast news to audiences. Organisations that invest thoughtfully in this automation layer, while maintaining the human editorial oversight that audiences trust and regulatory frameworks require, will be well positioned for the competitive and economic challenges ahead in broadcast news as audience fragmentation continues and the cost pressure on news production intensifies across the global broadcast industry.</p>"""

T["featured"] = """<p>Broadcast technology is evolving across every dimension simultaneously — production workflows are moving to cloud infrastructure, IP-based signal routing is replacing legacy SDI architectures, artificial intelligence is entering post-production and operations at pace, and streaming delivery is challenging traditional linear broadcast for audience attention and advertising investment. For professionals working in this industry, staying oriented amid this breadth of change while delivering reliable, high-quality content to audiences is the defining operational challenge of the current era in broadcast and media technology across every type of organisation from global networks to regional broadcasters.</p>

<h2>The Technology Transformation Reshaping Broadcasting</h2>
<p>The common thread running through broadcast technology transformation is the adoption of standards and architectures from the wider IT and internet industry. Ethernet-based media transport, cloud computing, software-defined systems, and AI capabilities built on large-scale data processing are all technologies that originated outside the broadcast domain. Their adoption within broadcasting brings significant capability and cost benefits while also requiring the industry to develop new skill sets, new operational disciplines, and new relationships with technology partners from adjacent sectors who may not fully understand the specific reliability, latency, and quality requirements that broadcast transmission demands from every piece of infrastructure in the signal chain.</p>

<p>The pace of technology change creates a genuine challenge for broadcast organisations in making effective investment decisions across a wide range of competing priorities and vendor claims. Technologies that appear transformative when announced at trade shows can take years to reach production readiness, while others mature faster than anticipated. Building internal technical capability to evaluate emerging technologies critically — rather than relying solely on vendor assessments and marketing materials — is increasingly a competitive advantage for organisations that need to allocate technology investment budgets strategically across infrastructure, production tools, and distribution platforms simultaneously.</p>

<h2>Convergence of IT and Broadcast Operations</h2>
<p>The convergence of broadcast engineering and IT operations is visible in every area of the technology stack and cannot be reversed as the industry's infrastructure becomes more deeply IP-connected. Network engineers now configure the infrastructure that carries live programme signals. Cloud architects design the environments where content is stored, processed, and distributed globally. Cybersecurity professionals — a discipline absent from most broadcast facilities a decade ago — are now integral to the safe operation of IP-connected production environments. This convergence is irreversible, and the organisations that have invested in building genuinely cross-disciplinary teams are deriving measurable operational advantage from the resulting combination of broadcast domain knowledge and modern IT capability that serves them across every area of technology investment and operations.</p>

<h2>Industry Priorities Across the Broadcast Sector</h2>
<ul>
<li><strong>Sustainability and energy efficiency:</strong> Broadcast organisations face increasing pressure from regulators, advertisers, and their own sustainability commitments to reduce the energy consumption of production and distribution infrastructure, driving investment in more efficient encoders, virtualised systems, and optimised streaming delivery networks that reduce the carbon footprint of content delivery at scale.</li>
<li><strong>Audience fragmentation response:</strong> Linear television audiences are declining across most demographics while streaming consumption grows, forcing broadcasters to operate across more platforms with more content at lower per-unit cost — a fundamental challenge to traditional production economics that requires both technology innovation and business model adaptation from organisations at all scales.</li>
<li><strong>Standards-based interoperability:</strong> As broadcast technology ecosystems become more complex, the value of open standards — SMPTE ST 2110, NMOS, SRT, CMAF — in enabling interoperability between vendors and reducing integration costs is increasingly recognised across the sector, driving active participation in standards bodies by both broadcasters and technology suppliers who recognise the market benefit of a healthy, interoperable ecosystem.</li>
<li><strong>Talent and skills pipeline:</strong> The broadcast industry faces a significant skills gap as experienced engineers retire and the competencies required for modern technology environments extend well beyond the talent pools from which the industry has traditionally recruited, requiring new approaches to education partnerships, recruitment strategies, and internal career development programmes.</li>
</ul>

<h2>What Broadcast Professionals Need to Focus On</h2>
<p>Broadcast professionals navigating this environment benefit most from developing a clear framework for evaluating technology change — distinguishing between innovations that will materially improve their organisation's production capability or economics and those that represent incremental evolution insufficient to justify the disruption and investment cost of adoption. Engagement with industry bodies including SMPTE, IBC, and SVG, and with the vendor community through events and technical working groups, provides the most reliable signal about which technologies are approaching production maturity and which remain at earlier stages that require patience before operational deployment can be recommended with confidence to technology decision-makers.</p>

<h2>A Sector in Motion</h2>
<p>The broadcast technology sector is characterised by genuine excitement alongside real operational complexity that demands respect from every organisation planning to adopt new capabilities. The capabilities available to production teams, facility operators, and distributors today — real-time cloud production, AI-assisted editorial workflows, ultra-low-latency streaming, IP-based facility infrastructure — were aspirational only a few years ago. The organisations that adopt these capabilities thoughtfully, with appropriate investment in training, process design, and operational governance, are building durable competitive advantage in a rapidly evolving media landscape where technical capability increasingly determines the ability to deliver content that meets both audience expectations and the commercial objectives that sustain the investment in high-quality broadcast production and distribution infrastructure.</p>"""

T["fallback"] = T["featured"]

BODY_TEMPLATES = T

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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
    return (f"An independent editorial overview of the technology forces reshaping "
            f"{label.lower()} for broadcast engineers and media operations professionals.")

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
    from bs4 import BeautifulSoup
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    return len(text.split())

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _topic_image(title, cat_slug, seed=''):
    """Unique, topic-relevant Unsplash image per article (CC0)."""
    import hashlib as _hl
    _used = getattr(_topic_image, '_used', set()); _topic_image._used = _used
    tl = title.lower()
    pools = [
        (['smpte','ip routing','nmos','infrastructure','network','fiber'],['photo-1558494949-ef010cbdcc31','photo-1545987796-200677ee1011','photo-1451187580459-43490279c0fa','photo-1544197150-b99a580bb7a8']),
        (['artificial intelligence','ai-powered','machine learning','neural','generative ai','automation'],['photo-1677442135703-1787eea5ce01','photo-1620712943543-bcc4688e7485','photo-1655635643532-fa9ba2648cbe','photo-1635070041078-e363dbe005cb']),
        (['broadcast camera','cinema camera','camera','lens','4k','8k'],['photo-1516035069371-29a1b244cc32','photo-1574717024653-61fd2cf4d44d','photo-1605116868827-a9e8b3028b99','photo-1551269901-5c2d5b2e3b24']),
        (['cloud','aws','azure','saas','data center'],['photo-1531297484001-80022131f5a1','photo-1488229297570-58520851e868','photo-1573164713988-8665fc963095','photo-1580584126903-c17d41830450']),
        (['streaming','ott','vod','hls','low latency'],['photo-1616401784845-180882ba9ba8','photo-1611532736597-de2d4265fba3','photo-1593642632559-0c6d3fc62b89','photo-1574717025058-97e3af4ef9b5']),
        (['encoder','encoding','transcod','codec','hevc','av1'],['photo-1574717024653-61fd2cf4d44d','photo-1504384308090-c894fdcc538d','photo-1518770660439-4636190af475','photo-1560472354-b33ff0c44a43']),
        (['graphics','motion graphics','virtual set','ar','augmented reality'],['photo-1504639725590-34d0984388bd','photo-1547658719-da2b51169166','photo-1518770660439-4636190af475','photo-1561736778-92e52a7769ef']),
        (['playout','master control','automation','channel in a box','on-air'],['photo-1478737270239-2f02b77fc618','photo-1590602847861-f357a9332bbc','photo-1612420696760-0a0f34d3e7d0','photo-1525059696034-4967a8e1dca2']),
        (['newsroom','nrcs','news production','journalist','reporter'],['photo-1504711434969-e33886168f5c','photo-1493863641943-9b68992a8d07','photo-1585829365295-ab7cd400c167','photo-1557804506-669a67965ba0']),
        (['post-production','editing','nle','davinci','premiere','media composer'],['photo-1572044162444-ad60f128bdea','photo-1605106702734-205df224ecce','photo-1574717025058-97e3af4ef9b5','photo-1489875347897-49f64b51c1f8']),
        (['audio','mixer','console','lawo','calrec','dolby'],['photo-1511379938547-c1f69419868d','photo-1598520106830-8c45c2035460','photo-1471478331149-c72f17e33c73','photo-1520523839897-bd0b52f945a0']),
        (['wireless','5g','satellite','uplink','rf'],['photo-1526374965328-7f61d4dc18c5','photo-1581092583537-20d51b4b4f1b','photo-1598520106830-8c45c2035460','photo-1605196560547-b2f7281b7355']),
    ]
    cat_pools = {'streaming':['photo-1616401784845-180882ba9ba8','photo-1611532736597-de2d4265fba3','photo-1574717025058-97e3af4ef9b5'],'cloud':['photo-1531297484001-80022131f5a1','photo-1488229297570-58520851e868','photo-1573164713988-8665fc963095'],'ai-post-production':['photo-1677442135703-1787eea5ce01','photo-1620712943543-bcc4688e7485','photo-1572044162444-ad60f128bdea'],'graphics':['photo-1504639725590-34d0984388bd','photo-1547658719-da2b51169166','photo-1518770660439-4636190af475'],'playout':['photo-1478737270239-2f02b77fc618','photo-1590602847861-f357a9332bbc','photo-1612420696760-0a0f34d3e7d0'],'infrastructure':['photo-1558494949-ef010cbdcc31','photo-1545987796-200677ee1011','photo-1451187580459-43490279c0fa'],'newsroom':['photo-1504711434969-e33886168f5c','photo-1493863641943-9b68992a8d07','photo-1585829365295-ab7cd400c167'],'featured':['photo-1598488035139-bdbb2231ce04','photo-1530026405186-ed1f139313f8','photo-1574717024653-61fd2cf4d44d']}
    for kws, pids in pools:
        if any(kw in tl for kw in kws):
            for pid in pids:
                if pid not in _used: _used.add(pid); return f'https://images.unsplash.com/{pid}?w=800&auto=format&fit=crop'
    pool = cat_pools.get(cat_slug, cat_pools['featured'])
    for pid in pool:
        if pid not in _used: _used.add(pid); return f'https://images.unsplash.com/{pid}?w=800&auto=format&fit=crop'
    all_pids = [p for _,ps in pools for p in ps]
    idx = int(_hl.md5((seed+title).encode()).hexdigest(),16) % len(all_pids)
    _used.add(all_pids[idx]); return f'https://images.unsplash.com/{all_pids[idx]}?w=800&auto=format&fit=crop'

def main():
    with open(NEWS_F, "r", encoding="utf-8") as f:
        news = json.load(f)
    with open(IMAGES_F, "r", encoding="utf-8") as f:
        images_list = json.load(f)

    images_by_slug = {img["slug"]: img for img in images_list}
    images_by_cat  = {img.get("category", ""): img for img in images_list}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    articles = []

    for category, items in news.items():
        if not items:
            print(f"  ⚠  No news items for {category}, skipping.")
            continue
        cat_meta = CAT_META.get(category, {"label": category.title(), "icon": "📺", "color": "#333", "page": f"{category}.html"})
        body_html = BODY_TEMPLATES.get(category, BODY_TEMPLATES["fallback"])
        count = min(ARTICLES_PER_CATEGORY, len(items))
        for i in range(count):
            feed_item = items[i]
            slug = make_slug(category, i)
            img_obj = images_by_slug.get(slug) or images_by_cat.get(category)
            image_url     = img_obj["image_url"] if img_obj else CAT_IMAGES.get(category, CAT_IMAGES["featured"])
            image_credit  = img_obj.get("credit", "Unsplash — free to use under the Unsplash License") if img_obj else "Unsplash — free to use under the Unsplash License"
            image_license = img_obj.get("license", "Unsplash License") if img_obj else "Unsplash License"
            image_lic_url = img_obj.get("license_url", "https://unsplash.com/license") if img_obj else "https://unsplash.com/license"
            wc = word_count(body_html)
            # Carry the RSS guid through so build.py can write a legacy
            # rss-<guid>.html alias alongside the slug file.
            item_guid = feed_item.get("guid", "")
            legacy_slug = f"rss-{item_guid[:16]}" if item_guid and len(item_guid) == 16 else None
            # Use RSS teaser as the card summary — real content, not generic text
            rss_teaser = (feed_item.get("teaser") or "").strip()
            card_summary = rss_teaser[:200] if rss_teaser else build_meta(category, i)
            # Use unique topic-relevant image per article
            unique_img = _topic_image(build_title(category, i), category, slug)
            articles.append({
                "category": category, "cat_label": cat_meta["label"],
                "cat_icon": cat_meta["icon"], "cat_color": cat_meta["color"],
                "cat_page": cat_meta["page"], "title": build_title(category, i),
                "slug": slug,
                "guid": item_guid,
                "legacy_slug": legacy_slug,
                "dek": build_dek(category),
                "meta_description": card_summary,
                "body_html": body_html.strip(), "word_count": wc,
                "source_url": feed_item["url"], "source_domain": feed_item["source"],
                "published": today, "image_url": unique_img,
                "image_credit": "Unsplash — free to use under the Unsplash License",
                "image_license": "Unsplash License",
                "image_license_url": "https://unsplash.com/license",
            })
        print(f"  {category}: {count} articles ({word_count(body_html)} words)")

    if not articles:
        raise SystemExit("ERROR: No articles generated — aborting.")
    os.makedirs(os.path.dirname(OUTPUT_F), exist_ok=True)
    with open(OUTPUT_F, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    print(f"\n✓ {len(articles)} articles → data/generated_articles.json")

if __name__ == "__main__":
    main()
