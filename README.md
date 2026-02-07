# The Streamic - Broadcast Technology News Hub

Apple Bento-style news aggregator for broadcast technology professionals.

## 🎯 Features

- **Tiered Bento Grid Layout**: Large cards (1-12) + horizontal list cards (13-20)
- **Category-Specific RSS Feeds**: Each category gets targeted industry sources
- **GUID Deduplication**: Prevents duplicate articles
- **Auto-Archiving**: Moves items older than 30 days or beyond 100 items to archive
- **6-Hour Updates**: GitHub Actions fetches new content every 6 hours
- **Editor's Desk**: Original commentary and analysis (gold border)
- **Static Site**: Pure HTML/CSS/JS, no database required

## 📂 Structure

```
streamic-v2/
├── index.html           # Homepage with Bento grid
├── newsroom.html        # Category pages (7 total)
├── vlog.html            # Editor's Desk
├── fetch_rss.py         # RSS aggregator with archiving
├── main.js              # Tiered card rendering
├── style.css            # Apple Bento design system
├── data/
│   ├── news.json        # Current items (max 100)
│   └── archive.json     # Archived items
├── content/editor/      # Markdown vlog posts
└── .github/workflows/
    └── update.yml       # 6-hour automation
```

## 🚀 Deployment

1. Create GitHub repository
2. Upload all files
3. Enable GitHub Pages (Settings → Pages → main branch)
4. Run "Update RSS Feeds" action manually to populate initial content
5. Site live at `https://username.github.io/repo-name/`

## 📧 Configuration

**Update email address:** Search and replace `siteidea6@gmail.com` with your email in:
- contact.html
- All legal pages (privacy.html, terms.html, etc.)

## 🎨 Categories

- **Newsroom**: Dalet, Avid, newsroom systems
- **Playout**: Ross, Imagine, master control
- **Infrastructure**: SMPTE, networking, security
- **Graphics**: Vizrt, virtual sets, AR
- **Cloud**: Frame.io, Adobe, cloud workflows
- **Streaming**: AWS, CDN, OTT platforms  
- **Audio & AI**: Dante, AI/ML in broadcast

## 🔄 How It Works

1. `fetch_rss.py` runs every 6 hours via GitHub Actions
2. Fetches category-specific RSS feeds
3. Tags items by category, deduplicates by GUID
4. Archives items >30 days or beyond 100-item cap
5. Saves to `data/news.json` and `data/archive.json`
6. Frontend renders tiered Bento grid from JSON

## 💰 Cost

**FREE** - GitHub Pages + GitHub Actions (within free tier limits)

## 📄 License

Website code © 2026 The Streamic. Aggregated content belongs to respective publishers.

---

Contact: siteidea6@gmail.com
