# LinkedIn Job Scraper - Robust Solutions

## Problem
LinkedIn has sophisticated bot detection and blocks automated scraping attempts with HTTP 999 errors.

## Solutions (in order of reliability)

### Option 1: Browser Bookmarklet (Easiest - No Setup Required)

Create a bookmark in your browser with this JavaScript code:

```javascript
javascript:(function(){
  const title = document.querySelector('h1')?.innerText?.trim() || '';
  const company = document.querySelector('[data-testid="job-title"]')?.innerText?.trim() || 
                  document.querySelector('.topcard__org-name-link')?.innerText?.trim() ||
                  document.querySelector('.job-details-jobs-unified-top-card__company-name')?.innerText?.trim() || '';
  const description = document.querySelector('.show-more-less-html__markup')?.innerText?.trim() || 
                      document.querySelector('.description__text')?.innerText?.trim() ||
                      document.querySelector('[data-testid="job-description"]')?.innerText?.trim() || '';
  
  const data = {title, company, description, url: window.location.href};
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `job-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  alert('Job data downloaded! Run: python3 job_tool.py job-xxx.json');
})();
```

**How to use:**
1. Create a new bookmark in your browser
2. Paste the JavaScript code above as the URL
3. Go to any LinkedIn job posting
4. Click the bookmark - it will download a JSON file
5. Run: `python3 job_tool.py <path-to-downloaded-json>`

---

### Option 2: Playwright (Most Robust - Requires Installation)

This uses a real headless browser that LinkedIn can't easily detect.

**Install:**
```bash
pip install playwright
playwright install chromium
```

**The scraper will automatically use Playwright when urllib fails.**

---

### Option 3: Export Cookies (Medium Complexity)

1. Install the "Get cookies.txt LOCALLY" extension for your browser
2. Go to linkedin.com and log in to your account
3. Click the extension and export cookies
4. Save as `cookies.txt` in the crack_ats directory
5. Run the scraper normally

---

### Option 4: Save as HTML (Manual but Always Works)

1. Open the LinkedIn job posting in your browser
2. Press Ctrl+S (Cmd+S on Mac) to save the page
3. Run: `python3 job_tool.py <path-to-saved-html-file>`

---

## What the Scraper Now Does (Multi-Layered Approach)

The updated scraper tries multiple methods automatically:

1. **urllib with stealth headers** - Random User-Agent, realistic browser headers
2. **curl fallback** - Often bypasses blocks that urllib can't
3. **Playwright** - Real headless browser (if installed)
4. **Clear error messages** - Tells you exactly what to do next

## Technical Improvements Made

- User-Agent rotation (Chrome, Firefox, Safari on Windows/Mac/Linux)
- Random request delays to avoid pattern detection
- Enhanced browser fingerprinting headers
- curl as fallback method
- Playwright integration for JavaScript-heavy sites
- Better error messages with actionable solutions
