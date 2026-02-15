"""Job posting scraper with support for Indeed, LinkedIn, and local HTML files."""

import gzip
import http.cookiejar
import json
import platform
import random
import re
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser
from pathlib import Path

COOKIES_FILE = Path(__file__).parent / "cookies.txt"

_CHROME_VER = "133"
_UA_LIST = [
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CHROME_VER}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CHROME_VER}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CHROME_VER}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
]


class _ScriptCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self._depth = 0
        self._type = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._depth = 1
            self._type = dict(attrs).get("type")
            self._buf = []
        elif self._depth:
            self._depth += 1

    def handle_data(self, data):
        if self._depth:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._depth:
            self.scripts.append((self._type, "".join(self._buf).strip()))
            self._depth = 0


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "li"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("p", "li", "ul", "ol"):
            self._parts.append("\n")

    def handle_data(self, data):
        self._parts.append(data)

    def text(self):
        return "\n".join(ln.strip() for ln in "".join(self._parts).splitlines() if ln.strip())


class _MetaExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            d = dict(attrs)
            key = d.get("property") or d.get("name")
            if key and d.get("content"):
                self.meta[key] = d["content"]


class _IndeedExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = self.company = self.description = ""
        self._title_d = self._company_d = self._desc_d = 0
        self._t_buf, self._c_buf, self._d_buf = [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self._title_d:
            self._title_d += 1
        if self._company_d:
            self._company_d += 1
        if self._desc_d:
            self._desc_d += 1

        if not self._title_d and tag == "h1":
            self._title_d = 1
        if not self._company_d and self._is_company(a):
            self._company_d = 1
        if not self._desc_d and self._is_desc(a):
            self._desc_d = 1
        if self._desc_d and tag in ("br", "p", "li"):
            self._d_buf.append("\n")

        cn = a.get("data-company-name") or a.get("data-companyname")
        if cn and any(c.isalpha() for c in cn):
            self._c_buf.append(cn)

    def handle_endtag(self, tag):
        if self._desc_d and tag in ("p", "li", "ul", "ol"):
            self._d_buf.append("\n")
        if self._title_d:
            self._title_d -= 1
        if self._company_d:
            self._company_d -= 1
        if self._desc_d:
            self._desc_d -= 1

    def handle_data(self, data):
        if self._title_d:
            self._t_buf.append(data)
        if self._company_d:
            self._c_buf.append(data)
        if self._desc_d:
            self._d_buf.append(data)

    def finalize(self):
        self.title = " ".join("".join(self._t_buf).split()).strip()
        self.company = " ".join("".join(self._c_buf).split()).strip()
        self.description = "\n".join(ln.strip() for ln in "".join(self._d_buf).splitlines() if ln.strip())

    @staticmethod
    def _is_company(a):
        if "data-company-name" in a or "data-companyname" in a:
            return True
        tid = (a.get("data-testid") or "").lower()
        if "company" in tid and "name" in tid:
            return True
        cls = (a.get("class") or "").lower()
        return "companyname" in cls or "company-name" in cls

    @staticmethod
    def _is_desc(a):
        if a.get("id") == "jobDescriptionText":
            return True
        tid = a.get("data-testid") or ""
        if tid in ("jobDescriptionText", "job-description"):
            return True
        return "jobDescriptionText" in (a.get("class") or "")


def _strip_html(html):
    ext = _TextExtractor()
    ext.feed(html or "")
    return ext.text()


def _load_cookies():
    if not COOKIES_FILE.exists():
        return None
    try:
        jar = http.cookiejar.MozillaCookieJar(str(COOKIES_FILE))
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar
    except Exception:
        return None


def _headers(ua=None):
    if ua is None:
        ua = random.choice(_UA_LIST)

    # Determine platform from UA
    if "Macintosh" in ua:
        plat = '"macOS"'
    elif "Linux" in ua:
        plat = '"Linux"'
    else:
        plat = '"Windows"'

    # Determine Sec-Ch-Ua based on browser
    if "Firefox" in ua:
        sec_ch_ua = None  # Firefox doesn't send Sec-Ch-Ua
    elif "Safari" in ua and "Chrome" not in ua:
        sec_ch_ua = None  # Safari doesn't send Sec-Ch-Ua
    else:
        sec_ch_ua = f'"Not(A:Brand";v="99", "Google Chrome";v="{_CHROME_VER}", "Chromium";v="{_CHROME_VER}"'

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": plat,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

    if sec_ch_ua:
        headers["Sec-Ch-Ua"] = sec_ch_ua

    return headers


def _decompress(data, encoding):
    if encoding == "gzip":
        return gzip.decompress(data)
    if encoding == "deflate":
        try:
            return zlib.decompress(data)
        except zlib.error:
            return zlib.decompress(data, -zlib.MAX_WBITS)
    if encoding == "br":
        try:
            import brotli

            return brotli.decompress(data)
        except ImportError:
            pass
    return data


def _create_ssl_context():
    """Create SSL context, handling macOS certificate issues."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _http_get(url, jar=None):
    handlers = [urllib.request.HTTPCookieProcessor(jar or http.cookiejar.CookieJar())]

    # Add SSL context handler for macOS certificate issues
    ssl_context = _create_ssl_context()
    handlers.append(urllib.request.HTTPSHandler(context=ssl_context))

    opener = urllib.request.build_opener(*handlers)
    hdrs = _headers()
    parsed = urllib.parse.urlparse(url)
    hdrs["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"

    req = urllib.request.Request(url, headers=hdrs)
    with opener.open(req, timeout=30) as resp:
        data = resp.read()
        enc = resp.headers.get("Content-Encoding", "").lower()
        try:
            data = _decompress(data, enc)
        except Exception:
            pass
        return data.decode("utf-8", errors="replace")


def _curl_get(url, cookie_file=None):
    """Fallback to curl which often bypasses blocks that urllib can't."""
    cmd = [
        "curl",
        "-s",
        "-L",
        "--compressed",
        "-H",
        f"User-Agent: {random.choice(_UA_LIST)}",
        "-H",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H",
        "Accept-Language: en-US,en;q=0.9",
        "-H",
        "Accept-Encoding: gzip, deflate, br",
        "-H",
        "Cache-Control: max-age=0",
        "-H",
        "Upgrade-Insecure-Requests: 1",
        "--max-time",
        "30",
    ]

    if cookie_file and Path(cookie_file).exists():
        cmd.extend(["-b", str(cookie_file)])

    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode == 0:
        return result.stdout
    raise RuntimeError(f"curl failed: {result.stderr}")


def _playwright_get(url):
    """Use Playwright as ultimate fallback for JavaScript-heavy sites."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(_UA_LIST),
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # Load cookies if available
        if COOKIES_FILE.exists():
            import json

            cookies_text = COOKIES_FILE.read_text()
            # Simple parsing for Netscape format
            cookies = []
            for line in cookies_text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        cookies.append(
                            {
                                "name": parts[5],
                                "value": parts[6],
                                "domain": parts[0],
                                "path": parts[2],
                            }
                        )
            if cookies:
                context.add_cookies(cookies)

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Wait for job content to load
            page.wait_for_selector("body", timeout=10000)
            html = page.content()
            browser.close()
            return html
        except Exception as e:
            browser.close()
            raise RuntimeError(f"Playwright failed: {e}")


def _local_path(value):
    if value.lower().startswith("file://"):
        parsed = urllib.parse.urlparse(value)
        path = parsed.path or ""
        if parsed.netloc and parsed.netloc not in ("", "localhost"):
            path = f"//{parsed.netloc}{path}"
        p = Path(urllib.request.url2pathname(path))
        return p if p.exists() else None
    p = Path(value).expanduser()
    return p if p.exists() else None


def fetch_html(url):
    lp = _local_path(url)
    if lp:
        return lp.read_text(encoding="utf-8", errors="replace")

    jar = _load_cookies()
    is_linkedin = "linkedin.com" in url.lower()
    is_indeed = "indeed.com" in url.lower() or "indeed.ca" in url.lower()

    # Warn if cookies are missing for LinkedIn
    if is_linkedin and jar is None:
        print("Warning: No cookies.txt found. LinkedIn may block the request.")
        print("Consider exporting cookies from your browser (see error message for details).\n")

    errors = []

    # Method 1: Try urllib with retries
    for attempt in range(2):
        try:
            if attempt:
                # Add jitter to avoid pattern detection
                time.sleep(1 + random.random())
            return _http_get(url, jar)
        except urllib.error.HTTPError as e:
            if e.code not in (403, 429, 999):
                raise
            errors.append(f"urllib attempt {attempt + 1}: HTTP {e.code}")
            if attempt == 1:
                if e.code == 999 and is_linkedin:
                    print("urllib blocked, trying curl fallback...")
                elif e.code == 403 and is_indeed:
                    raise ValueError("Indeed blocked (403). Refresh cookies or save page as HTML.") from e

    # Method 2: Try curl as fallback
    try:
        print("Attempting curl fallback...")
        return _curl_get(url, COOKIES_FILE if COOKIES_FILE.exists() else None)
    except Exception as e:
        errors.append(f"curl: {e}")

    # Method 3: Try Playwright as last resort
    if is_linkedin:
        try:
            print("Attempting Playwright (headless browser)...")
            return _playwright_get(url)
        except RuntimeError as e:
            if "not installed" in str(e):
                errors.append("playwright: not installed")
            else:
                errors.append(f"playwright: {e}")

    # If we get here, all methods failed
    if is_linkedin:
        raise ValueError(
            "LinkedIn blocked (999).\n\n"
            "All methods failed. Try one of these solutions:\n\n"
            "OPTION 1 - Export Cookies (Easiest):\n"
            "1. Install 'Get cookies.txt LOCALLY' browser extension\n"
            "2. Go to linkedin.com and log in\n"
            "3. Export cookies to cookies.txt in this directory\n\n"
            "OPTION 2 - Use Playwright (Most Robust):\n"
            "Run: pip install playwright && playwright install\n"
            "Then retry - it will use a real browser automatically\n\n"
            "OPTION 3 - Save as HTML:\n"
            "Open the job page and press Ctrl+S (Cmd+S) to save as HTML,\n"
            "then provide the file path instead of the URL\n\n"
            f"Errors: {', '.join(errors)}"
        )
    raise RuntimeError(f"Failed to fetch HTML: {', '.join(errors)}")


def _extract_json_ld(html):
    col = _ScriptCollector()
    col.feed(html)
    for typ, content in col.scripts:
        if typ and typ.lower() != "application/ld+json":
            continue
        try:
            yield json.loads(content)
        except json.JSONDecodeError:
            pass


def _find_job_posting(data):
    if isinstance(data, dict):
        jt = data.get("@type")
        if jt == "JobPosting" or (isinstance(jt, list) and "JobPosting" in jt):
            return data
        for v in data.values():
            if found := _find_job_posting(v):
                return found
    elif isinstance(data, list):
        for item in data:
            if found := _find_job_posting(item):
                return found
    return None


def _normalize_ld(job):
    title = job.get("title") or job.get("name") or ""
    org = job.get("hiringOrganization")
    company = ""
    if isinstance(org, dict):
        company = org.get("name", "")
    elif isinstance(org, list):
        for o in org:
            if isinstance(o, dict) and o.get("name"):
                company = o["name"]
                break
    desc = _strip_html(job.get("description", ""))
    return {
        "title": title.strip(),
        "company": company.strip(),
        "description": desc.strip(),
    }


def parse_json_ld(html):
    for payload in _extract_json_ld(html):
        if job := _find_job_posting(payload):
            return _normalize_ld(job)
    return None


def parse_linkedin(html):
    meta = _MetaExtractor()
    meta.feed(html)

    og = meta.meta.get("og:title", "")
    title = company = ""

    # Try multiple patterns for extracting company and title from og:title
    # Pattern 1: "Company hiring Title in Location"
    if m := re.match(r"^(.+?)\s+hiring\s+(.+?)\s+in\s+", og):
        company, title = m.group(1).strip(), m.group(2).strip()
    # Pattern 2: "Title at Company | LinkedIn"
    elif m := re.search(r"^(.+?)\s+at\s+(.+?)\s*\|?\s*LinkedIn", og, re.I):
        title, company = m.group(1).strip(), m.group(2).strip()
    # Pattern 3: Just clean up "Title | LinkedIn"
    else:
        title = re.sub(r"\s*\|\s*LinkedIn\s*$", "", og).strip()

    desc = ""
    # Try multiple patterns for description extraction
    # Pattern 1: LinkedIn's job description container
    if m := re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", html, re.DOTALL | re.I):
        desc = _strip_html(m.group(1))
    # Pattern 2: Alternative description containers (LinkedIn changes these frequently)
    if not desc:
        for pattern in [
            r"description__text[^>]*>(.*?)</div>",
            r"job-details-jobs-unified-description__text[^>]*>(.*?)</div>",
            r"job-description[^>]*>(.*?)</div>",
            r'data-testid="job-description"[^>]*>(.*?)</div>',
        ]:
            if m := re.search(pattern, html, re.DOTALL | re.I):
                desc = _strip_html(m.group(1))
                if desc:
                    break
    # Fallback to meta description
    desc = desc or meta.meta.get("og:description", "") or meta.meta.get("description", "")

    # Extract company if not already found
    if not company:
        # Try multiple patterns for company extraction
        for pattern in [
            r"topcard__org-name-link[^>]*>([^<]+)</a>",
            r"top-card-layout__entity-info[^>]*>([^<]+)</a>",
            r'class="[^"]*topcard[^"]*"[^>]*>\s*<a[^>]*>([^<]+)</a>',
            r'"companyName":\s*"([^"]+)"',
            r'"hiringOrganization":\s*\{[^}]*"name":\s*"([^"]+)"',
            r"top-card-layout__card[^>]*>.*?<a[^>]*>([^<]+)</a>",
            r'class="[^"]*company[^"]*"[^>]*>([^<]+)</',
            r'@type":\s*"Organization"[^}]*"name":\s*"([^"]+)"',
            r'<div[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</div>',
            r'<span[^>]*class="[^"]*company[^"]*"[^>]*>([^<]+)</span>',
        ]:
            if m := re.search(pattern, html, re.DOTALL | re.I):
                company = " ".join(m.group(1).split())
                if company:
                    break

    if title or company or desc:
        return {
            "title": title.strip(),
            "company": company.strip(),
            "description": desc.strip(),
        }
    return None


def parse_indeed(html):
    ext = _IndeedExtractor()
    ext.feed(html)
    ext.finalize()

    if not ext.title or not ext.company:
        meta = _MetaExtractor()
        meta.feed(html)
        ext.title = ext.title or " ".join((meta.meta.get("og:title") or "").split())

    if not ext.description:
        meta = _MetaExtractor()
        meta.feed(html)
        ext.description = "\n".join(
            ln.strip() for ln in (meta.meta.get("og:description") or "").splitlines() if ln.strip()
        )

    if ext.title or ext.company or ext.description:
        return {
            "title": ext.title,
            "company": ext.company,
            "description": ext.description,
        }
    return None


def _is_auth_wall(html):
    lower = html.lower()
    return any(
        s in lower
        for s in (
            "sign in to view",
            "join now to see",
            "authwall",
            '"isloggedin":false',
            "login to view",
            "sign in to see",
            "join to view",
            "sign in or register",
            "log in to view",
        )
    )


def _parse_linkedin_embedded_json(html):
    """Parse LinkedIn's embedded JSON data which often contains job info."""
    # Look for JSON data in <code> tags with specific patterns
    patterns = [
        r'<code[^>]*>\s*(\{.*?"@type":\s*"JobPosting".*?\})\s*</code>',
        r'<code[^>]*>\s*(\{.*?"jobPosting".*?\})\s*</code>',
        r'data-testid="json-ld-script"[^>]*>(\{.*?\})</script>',
        r"<script[^>]*>window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*</script>",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, html, re.DOTALL | re.I):
            try:
                data = json.loads(match.group(1))
                if job := _find_job_posting(data):
                    return _normalize_ld(job)
            except (json.JSONDecodeError, AttributeError):
                continue
    return None


def scrape_job(url):
    is_linkedin = "linkedin.com" in url.lower()
    html = fetch_html(url)

    job = parse_json_ld(html)
    if not job and is_linkedin:
        job = parse_linkedin(html)
        # Try embedded JSON as additional fallback for LinkedIn
        if not job:
            job = _parse_linkedin_embedded_json(html)
    if not job:
        job = parse_indeed(html)

    if not job:
        lower = html.lower()
        if "captcha" in lower or "verify you are a human" in lower:
            raise ValueError("Blocked by CAPTCHA. Save page as HTML and pass file path.")
        if is_linkedin and _is_auth_wall(html):
            raise ValueError("LinkedIn auth wall. Export cookies or save page as HTML.")
        raise ValueError("No job data found. Try saving page as HTML.")

    return job
