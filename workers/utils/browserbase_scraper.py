"""
Browserbase News Scraper for AI Editor 2.0

Handles paywalled news sites where Firecrawl fails:
- WSJ (Wall Street Journal)
- Bloomberg
- New York Times
- MSN

Uses Browserbase cloud browser infrastructure with:
- Advanced Stealth Mode for anti-bot evasion
- Persistent authentication contexts
- Proxy rotation for IP diversity

Environment Variables Required:
    BROWSERBASE_API_KEY: API key from Browserbase dashboard

Optional (for authenticated scraping):
    BROWSERBASE_PROJECT_ID: Project ID (optional, uses default)
    WSJ_EMAIL, WSJ_PASSWORD: WSJ subscription credentials
    NYT_EMAIL, NYT_PASSWORD: NYT subscription credentials
    BLOOMBERG_EMAIL, BLOOMBERG_PASSWORD: Bloomberg credentials
"""

import os
import json
import random
from typing import Optional, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from playwright.sync_api import sync_playwright
    from browserbase import Browserbase
    from html2text import html2text
    BROWSERBASE_AVAILABLE = True
except ImportError:
    BROWSERBASE_AVAILABLE = False

EST = ZoneInfo("America/New_York")


class BrowserbaseNewsScraper:
    """Scraper for paywalled news sites using Browserbase."""

    # Context IDs stored per-site for session persistence
    CONTEXT_FILE = "/tmp/browserbase_contexts.json"

    # Site-specific configurations for content extraction
    SITE_CONFIGS = {
        "wsj.com": {
            "login_url": "https://accounts.wsj.com/login",
            "username_selector": 'input[name="username"]',
            "password_selector": 'input[name="password"]',
            "submit_selector": 'button[type="submit"]',
            "article_selectors": [
                "article",
                '[class*="article-content"]',
                '[class*="story-body"]',
                ".wsj-snippet-body",
            ],
            "env_user": "WSJ_EMAIL",
            "env_pass": "WSJ_PASSWORD"
        },
        "nytimes.com": {
            "login_url": "https://myaccount.nytimes.com/auth/login",
            "username_selector": 'input[name="email"]',
            "password_selector": 'input[name="password"]',
            "submit_selector": 'button[type="submit"]',
            "article_selectors": [
                # Primary NYT selectors (based on current site structure)
                'article#story div.StoryBodyCompanionColumn',
                'section[name="articleBody"]',
                '[data-testid="article-body"]',
                "article#story",
                "article",
            ],
            "env_user": "NYT_EMAIL",
            "env_pass": "NYT_PASSWORD"
        },
        "bloomberg.com": {
            "login_url": "https://login.bloomberg.com/",
            "username_selector": 'input[name="email"]',
            "password_selector": 'input[name="password"]',
            "submit_selector": 'button[type="submit"]',
            "article_selectors": [
                ".body-content",
                "article",
                '[class*="article-body"]',
            ],
            "env_user": "BLOOMBERG_EMAIL",
            "env_pass": "BLOOMBERG_PASSWORD"
        },
        "msn.com": {
            "login_url": None,  # No login required for MSN
            "article_selectors": [
                "article",
                '[class*="article-body"]',
                ".content-body",
                "main",
            ],
        }
    }

    def __init__(self):
        """Initialize Browserbase client."""
        if not BROWSERBASE_AVAILABLE:
            raise ImportError(
                "Browserbase dependencies not installed. "
                "Run: pip install browserbase playwright html2text"
            )

        api_key = os.environ.get("BROWSERBASE_API_KEY")
        if not api_key:
            raise ValueError("BROWSERBASE_API_KEY environment variable not set")

        self.project_id = os.environ.get("BROWSERBASE_PROJECT_ID")
        if not self.project_id:
            raise ValueError("BROWSERBASE_PROJECT_ID environment variable not set (required by SDK v1.4+)")

        self.bb = Browserbase(api_key=api_key)
        self.contexts = self._load_contexts()

    def _load_contexts(self) -> Dict[str, str]:
        """Load saved context IDs from file."""
        try:
            if os.path.exists(self.CONTEXT_FILE):
                with open(self.CONTEXT_FILE, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[Browserbase] Warning: Could not load contexts: {e}")
        return {}

    def _save_contexts(self):
        """Save context IDs to file."""
        try:
            with open(self.CONTEXT_FILE, "w") as f:
                json.dump(self.contexts, f)
        except Exception as e:
            print(f"[Browserbase] Warning: Could not save contexts: {e}")

    def _get_site_key(self, url: str) -> Optional[str]:
        """Extract site key from URL."""
        for site in self.SITE_CONFIGS:
            if site in url.lower():
                return site
        return None

    def _create_session(self, site_key: Optional[str] = None) -> object:
        """Create a Browserbase session with proper settings per documentation."""
        session_settings = {
            "project_id": self.project_id,  # Required by SDK v1.4+
            "browser_settings": {
                "solve_captchas": True,  # Auto-solve CAPTCHAs
                "block_ads": True,  # Faster page loads
                "viewport": {"width": 1920, "height": 1080},
            },
            # Proxies with US geolocation (correct format per docs)
            "proxies": [{
                "type": "browserbase",
                "geolocation": {
                    "country": "US",
                    "state": "NY",
                    "city": "New York"
                }
            }],
        }

        # Use authenticated context if available for this site
        if site_key and site_key in self.contexts:
            session_settings["browser_settings"]["context"] = {
                "id": self.contexts[site_key],
                "persist": True
            }
            print(f"[Browserbase] Using cached auth context for {site_key}")

        return self.bb.sessions.create(**session_settings)

    def authenticate(self, site_key: str) -> str:
        """
        Perform login and save context for a site.

        Args:
            site_key: Site domain (e.g., "wsj.com")

        Returns:
            Context ID for reuse
        """
        if site_key not in self.SITE_CONFIGS:
            raise ValueError(f"Unknown site: {site_key}")

        config = self.SITE_CONFIGS[site_key]
        if not config.get("login_url"):
            raise ValueError(f"Site {site_key} does not require authentication")

        # Create new context (project_id required by SDK v1.4+)
        context = self.bb.contexts.create(project_id=self.project_id)

        session_settings = {
            "project_id": self.project_id,  # Required by SDK v1.4+
            "browser_settings": {
                "context": {"id": context.id, "persist": True},
                "solve_captchas": True,
                "block_ads": True,
                "viewport": {"width": 1920, "height": 1080},
            },
            "proxies": [{
                "type": "browserbase",
                "geolocation": {"country": "US"}
            }]
        }

        session = self.bb.sessions.create(**session_settings)

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(session.connect_url)
            ctx = browser.contexts[0]
            page = ctx.pages[0]

            try:
                # Navigate to login
                print(f"[Browserbase] Navigating to {config['login_url']}")
                page.goto(config["login_url"])
                page.wait_for_load_state("networkidle")

                # Fill credentials
                username = os.environ.get(config.get("env_user", ""))
                password = os.environ.get(config.get("env_pass", ""))

                if not username or not password:
                    raise ValueError(f"Missing credentials for {site_key}")

                page.fill(config["username_selector"], username)
                page.fill(config["password_selector"], password)
                page.click(config["submit_selector"])

                # Wait for redirect after login
                page.wait_for_timeout(5000)

                print(f"[Browserbase] Authenticated with {site_key}")
                print(f"[Browserbase] Session replay: https://browserbase.com/sessions/{session.id}")

            finally:
                browser.close()

        # Save context for future use
        self.contexts[site_key] = context.id
        self._save_contexts()

        return context.id

    def scrape(self, url: str) -> Dict:
        """
        Scrape an article using Browserbase.

        Uses cached authentication context if available.
        Tries multiple selectors to extract article content.

        Args:
            url: Article URL to scrape

        Returns:
            Dict with keys:
                - success: bool
                - title: str (article title)
                - content: str (markdown content)
                - url: str (original URL)
                - site: str (site key)
                - full_content: bool (True if content > 2000 chars)
                - content_length: int
                - session_replay: str (Browserbase session replay URL)
                - error: str (if success=False)
        """
        site_key = self._get_site_key(url)
        start_time = datetime.now(EST)

        try:
            session = self._create_session(site_key)
            print(f"[Browserbase] Session created: {session.id}")

            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(session.connect_url)
                ctx = browser.contexts[0]
                page = ctx.pages[0]

                try:
                    # Navigate to article (use domcontentloaded, not networkidle - more reliable)
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)

                    # Wait for page to stabilize and content to load
                    page.wait_for_timeout(5000)

                    # Human-like delay and scroll (helps avoid detection, loads content before paywall)
                    page.wait_for_timeout(random.randint(2000, 4000))
                    page.evaluate("window.scrollBy(0, window.innerHeight / 2)")
                    page.wait_for_timeout(random.randint(1000, 2000))

                    # Get title
                    title = "Unknown Title"
                    try:
                        title_element = page.locator("h1").first
                        if title_element:
                            title = title_element.text_content() or "Unknown Title"
                    except Exception:
                        pass

                    # Get article content using site-specific selectors
                    config = self.SITE_CONFIGS.get(site_key, {})
                    selectors = config.get("article_selectors", ["article", "main", "body"])

                    content = None
                    html_content = None

                    for selector in selectors:
                        try:
                            element = page.locator(selector).first
                            if element:
                                html_content = element.inner_html()
                                if html_content and len(html_content) > 200:
                                    content = html2text(html_content)
                                    if len(content) > 500:
                                        break
                        except Exception:
                            continue

                    # Fallback to body if no content found
                    if not content or len(content) < 200:
                        try:
                            html_content = page.locator("body").inner_html()
                            content = html2text(html_content)
                        except Exception:
                            content = ""

                    # Check if we got full content (rough heuristic)
                    content_length = len(content) if content else 0
                    is_full_content = content_length > 2000

                    duration = (datetime.now(EST) - start_time).total_seconds()
                    print(f"[Browserbase] Extracted {content_length} chars in {duration:.1f}s")

                    return {
                        "success": True,
                        "title": title.strip() if title else "Unknown Title",
                        "content": content or "",
                        "url": url,
                        "site": site_key or "unknown",
                        "full_content": is_full_content,
                        "content_length": content_length,
                        "session_replay": f"https://browserbase.com/sessions/{session.id}",
                        "duration_seconds": duration
                    }

                except Exception as e:
                    duration = (datetime.now(EST) - start_time).total_seconds()
                    return {
                        "success": False,
                        "error": str(e),
                        "url": url,
                        "site": site_key or "unknown",
                        "session_replay": f"https://browserbase.com/sessions/{session.id}",
                        "duration_seconds": duration
                    }
                finally:
                    browser.close()

        except Exception as e:
            duration = (datetime.now(EST) - start_time).total_seconds()
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "site": site_key or "unknown",
                "session_replay": None,
                "duration_seconds": duration
            }

    def is_available(self) -> bool:
        """Check if Browserbase is configured and available."""
        try:
            api_key = os.environ.get("BROWSERBASE_API_KEY")
            return bool(api_key and BROWSERBASE_AVAILABLE)
        except Exception:
            return False


# Convenience function for one-off scrapes
def scrape_with_browserbase(url: str) -> Dict:
    """
    Convenience function to scrape a single URL with Browserbase.

    Args:
        url: Article URL to scrape

    Returns:
        Scrape result dict (see BrowserbaseNewsScraper.scrape)
    """
    scraper = BrowserbaseNewsScraper()
    return scraper.scrape(url)


# Test function
if __name__ == "__main__":
    # Test basic scraping
    scraper = BrowserbaseNewsScraper()

    test_url = "https://www.wsj.com/tech/ai/openai-microsoft-apple-ai-partnership-challenges-2025-f6b4e123"
    print(f"Testing scrape for: {test_url}")

    result = scraper.scrape(test_url)
    print(json.dumps({
        "success": result["success"],
        "title": result.get("title", "")[:50],
        "content_length": result.get("content_length", 0),
        "full_content": result.get("full_content", False),
        "session_replay": result.get("session_replay")
    }, indent=2))
