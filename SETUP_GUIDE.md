# Quick Setup & Testing Guide

## 🚀 Installation

1. **Place all files in your web root:**
   ```
   your-project/
   ├── index.html
   ├── newsroom.html
   ├── playout.html
   ├── infrastructure.html
   ├── graphics.html
   ├── cloud.html
   ├── streaming.html
   ├── audio-ai.html
   ├── style.css
   ├── main.js
   ├── fetch.py
   └── data/
       └── news.json (will be created)
   ```

2. **Fetch RSS feeds:**
   ```bash
   python3 fetch.py
   ```

3. **Open in browser:**
   ```
   index.html
   ```

## ✅ Testing Checklist

### 1. Homepage (index.html)
- [ ] No hero section visible
- [ ] Shows grid of cards from all categories
- [ ] First 12 cards are large bento cards
- [ ] Items 13-20 are horizontal list cards
- [ ] Images load (real images preferred, fallbacks if needed)
- [ ] "View More" link appears at bottom

### 2. Navigation
- [ ] Navigation shows: NEWSROOM | PLAYOUT | INFRASTRUCTURE | GRAPHICS | CLOUD | STREAMING | AUDIO & AI
- [ ] No "HOME" link in navigation
- [ ] All category links work
- [ ] Mobile menu toggle works (< 1024px width)
- [ ] Active page highlighted in nav

### 3. Newsroom Category Page
- [ ] Hero section visible with "Newsroom" title
- [ ] Shows only newsroom category items
- [ ] First 12 items in large grid
- [ ] Items 13-20 in list format
- [ ] "Load More" button appears if >20 items
- [ ] Clicking "Load More" loads next 20 items
- [ ] Button disappears when all items shown

### 4. Playout Category Page
- [ ] Shows content (not empty)
- [ ] RSS feeds working (Ross Video, Imagine, Grass Valley)
- [ ] Images display correctly
- [ ] Load More works if >20 items

### 5. Infrastructure Category Page
- [ ] Shows content (not empty)
- [ ] RSS feeds working (SMPTE, Haivision, Evertz)
- [ ] Images display correctly
- [ ] Load More works if >20 items

### 6. Audio & AI Category Page
- [ ] Correct URL: audio-ai.html (not audio&ai)
- [ ] data-category="audio-ai" in HTML
- [ ] Shows content from RedTech and Audinate
- [ ] Fallback images work
- [ ] Category tag shows "AUDIO & AI"

### 7. Image Quality
- [ ] Real images from RSS feeds display when available
- [ ] Fallback images only show when RSS has no image
- [ ] No broken image icons
- [ ] Images maintain aspect ratio in cards
- [ ] Hover effects work (scale on large cards, slide on list cards)

### 8. Responsive Design
- [ ] Desktop (>1024px): 3-column grid
- [ ] Tablet (641-1024px): 2-column grid
- [ ] Mobile (<640px): 1-column grid
- [ ] Mobile navigation works
- [ ] Touch interactions smooth

## 🐛 Troubleshooting

### No content showing
```bash
# Check if news.json exists and has data
cat data/news.json | head -20

# Re-fetch feeds
python3 fetch.py
```

### Images not loading
1. Check browser console for errors
2. Verify RSS feeds have images: look at data/news.json
3. Check that fallback images are accessible
4. Ensure no CORS issues

### "Load More" not working
1. Check browser console for JavaScript errors
2. Verify category has >20 items: 
   ```bash
   cat data/news.json | grep '"category": "newsroom"' | wc -l
   ```
3. Make sure main.js is loaded

### Category shows wrong data
1. Verify data-category attribute in HTML matches category in fetch.py
2. Check that news.json has items with correct category values
3. Ensure no typos in category names (e.g., "audio-ai" not "audio&ai")

## 📊 Expected RSS Feed Results

After running `fetch.py`, you should see approximately:

```
Category Summary:
  newsroom            : 40-60 items
  playout             : 15-30 items
  infrastructure      : 10-25 items
  graphics            : 20-35 items
  cloud               : 15-30 items
  streaming           : 10-20 items
  audio-ai            : 8-15 items
```

If any category shows 0 items, check:
1. RSS feed URLs are accessible
2. No network issues
3. Feed format is valid XML/RSS

## 🔧 Manual Testing Steps

1. **Clear browser cache**
2. **Run fetch.py:**
   ```bash
   python3 fetch.py
   ```
3. **Open homepage:** Verify no hero, mixed categories
4. **Click Newsroom:** Verify hero, filtered content, Load More
5. **Click Playout:** Verify content exists (was previously empty)
6. **Click Infrastructure:** Verify content exists (was previously empty)
7. **Click Audio & AI:** Verify correct URL and content
8. **Test mobile:** Resize to <640px, test navigation
9. **Check images:** Verify real images > fallback images ratio is high

## ✨ Success Criteria

All bugs fixed when:
- ✅ Homepage has no hero section
- ✅ Navigation doesn't include "HOME"
- ✅ Newsroom shows unique content (not same as homepage)
- ✅ Load More works on category pages with >20 items
- ✅ "audio-ai" category works (not "audio&ai")
- ✅ Playout and Infrastructure show content
- ✅ Images extracted from RSS feeds (not just fallbacks)
- ✅ Category pages show Load More button when needed

## 📝 Notes

- Data refreshes each time you run fetch.py
- Images cached by browser - clear cache to test image changes
- Load More state doesn't persist across page reloads
- RSS feeds update at different intervals (check source sites)

---
**Need help?** Check BUGFIX_REPORT.md for detailed technical documentation.
