# 🚀 DEPLOYMENT GUIDE

## Pre-Deployment Checklist

Before uploading to your server, verify:

### 1. Files Present ✅
```bash
# Check all required files exist
ls -la *.html
ls -la main.js
ls -la style.css
ls -la data/news.json
```

### 2. Quick Verification
```bash
# Run this to verify all changes
grep -r "main.js?v=20260208" *.html | wc -l
# Should show: 8 (number of HTML files with main.js)

grep "FEATURED" featured.html
# Should show: Multiple matches

grep "CLOUD PRODUCTION" cloud.html
# Should show: Multiple matches
```

---

## Deployment Steps

### Option 1: Full Site Upload (Recommended)
1. **Backup Current Site**
   ```bash
   # On your server, backup first
   cp -r /var/www/html /var/www/html.backup.$(date +%Y%m%d)
   ```

2. **Upload All Files**
   - Upload entire `TheStreamic-V2-FINAL` folder
   - Replace all existing files
   - Verify permissions: `chmod 644 *.html *.js *.css`

3. **Clear Server Cache** (if applicable)
   ```bash
   # Apache
   sudo service apache2 reload
   
   # Nginx
   sudo service nginx reload
   ```

### Option 2: Update Only Changed Files
Upload these files only:
- ✅ `featured.html` (NEW)
- ✅ `index.html`
- ✅ `main.js`
- ✅ `cloud.html`
- ✅ All other HTML files (for navigation updates)

---

## Post-Deployment Testing

### 1. Homepage Test
```
Visit: https://yoursite.com/
Expected: Auto-redirects to featured.html
Result: Should show all articles (not empty)
```

### 2. Featured Page Test
```
Visit: https://yoursite.com/featured.html
Expected: Displays all 260+ articles
Check: Navigation shows "FEATURED" (not "NEWSROOM")
```

### 3. Cloud Production Test
```
Visit: https://yoursite.com/cloud.html
Expected: Navigation shows "CLOUD PRODUCTION"
Expected: Page title shows "Cloud Production"
Expected: Articles load correctly
```

### 4. Cache-Busting Test
```
Open DevTools (F12)
Go to Network tab
Reload page
Check: main.js loads as "main.js?v=20260208"
```

### 5. Fallback Image Test
```
1. Open any category page
2. Scroll through articles
3. Check images load (or use fallbacks)
4. DevTools should show WebP format images
```

### 6. Mobile Navigation Test
```
1. Resize browser to mobile width (< 768px)
2. Click hamburger menu (☰)
3. Verify navigation opens
4. Check all links work
5. Navigation should close on link click
```

---

## Troubleshooting

### Problem: Featured page shows "No articles"
**Solution:**
- Check `data/news.json` exists and has content
- Run `fetch.py` to populate articles
- Check file permissions
- Verify JSON is valid

### Problem: Old navigation still showing
**Solution:**
- Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
- Clear browser cache
- Check HTML files uploaded correctly
- Verify no CDN cache blocking updates

### Problem: Images not loading
**Solution:**
- Check `assets/fallback.jpg` exists
- Verify image URLs in news.json
- Check network tab for 404 errors
- Ensure WebP format supported

### Problem: main.js old version loading
**Solution:**
- Verify `?v=20260208` in all HTML script tags
- Clear CDN cache if using one
- Check server cache (Apache/Nginx)
- Hard refresh browser

---

## Verification Commands

### On Server:
```bash
# Check featured.html exists
ls -la featured.html

# Verify main.js has cache-busting
grep "main.js?v=" featured.html

# Check navigation updated
grep "FEATURED" featured.html
grep "CLOUD PRODUCTION" cloud.html

# Verify data exists
ls -la data/news.json
wc -l data/news.json  # Should show ~3000+ lines
```

### In Browser Console:
```javascript
// Check if featured category works
window.loadCategory('featured');

// Check data loading
fetch('data/news.json?v=' + Date.now())
  .then(r => r.json())
  .then(d => console.log('Articles:', d.length));
```

---

## Performance Checks

### Page Load Speed
```
Target: < 3 seconds for initial load
Target: < 1 second for category switch
```

### Image Loading
```
Target: Images visible within 1-2 seconds
Fallback: Should show within 3 seconds if primary fails
```

### Mobile Performance
```
Target: Smooth scrolling
Target: Navigation opens without delay
```

---

## Rollback Plan (If Needed)

### Quick Rollback:
```bash
# If you backed up (recommended)
rm -rf /var/www/html/*
cp -r /var/www/html.backup.YYYYMMDD/* /var/www/html/
sudo service apache2 reload
```

### Selective Rollback:
1. Keep new `featured.html`
2. Restore old `index.html` if needed
3. Restore old `main.js` if issues occur
4. Keep navigation changes (they're improvements)

---

## Success Criteria

Site is successfully deployed when:

- ✅ Homepage redirects to featured.html
- ✅ Featured page shows all articles (260+)
- ✅ Navigation shows "FEATURED" and "CLOUD PRODUCTION"
- ✅ All category pages load correctly
- ✅ Images load (or fallbacks show)
- ✅ Cache-busting works (no old JS)
- ✅ Mobile navigation functions
- ✅ No console errors

---

## Monitoring

### First 24 Hours:
- Monitor server logs for errors
- Check analytics for traffic patterns
- Watch for 404 errors on featured.html
- Verify users can navigate between pages

### First Week:
- Monitor fallback image usage
- Track category page views
- Check mobile vs desktop usage
- Gather user feedback

---

## Support

### If Issues Arise:
1. Check browser console for errors
2. Verify files uploaded correctly
3. Check server error logs
4. Test in different browsers
5. Verify cache is cleared

### Contact:
- Check documentation in IMPLEMENTATION_REPORT.md
- Review BEFORE_AFTER.md for comparison
- See QUICK_CHANGES.md for summary

---

## Final Deployment Command

```bash
# Complete deployment (example)
cd /path/to/TheStreamic-V2-FINAL
rsync -avz --exclude='.git' . user@yourserver:/var/www/html/
ssh user@yourserver 'sudo service apache2 reload'
```

---

## ✅ READY TO DEPLOY!

All files prepared and verified. Site is production-ready!

**Version:** 2.0 (Cache-busted)
**Date:** February 8, 2026
**Status:** PRODUCTION READY ✅
