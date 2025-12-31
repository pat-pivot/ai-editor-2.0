"""
FreshRSS API Client for Ingestion Engine Sandbox

This client connects to the FreshRSS instance running on Render
and fetches articles using the Google Reader API.

Production Instance:
    URL: https://pivot-media-rss-feed.onrender.com
    API: https://pivot-media-rss-feed.onrender.com/api/greader.php

18 Active Feeds (Dec 30, 2025):
    - Direct RSS: Bloomberg, The Verge, The Atlantic, CNBC, VentureBeat, Semafor
    - AI-Specific RSS: TechCrunch AI, TechRepublic AI, MIT Tech Review, MIT News,
                       Science Daily, The Guardian, The Next Web
    - Native RSS: NYT AI (direct), WSJ Technology (Dow Jones)
    - Google News RSS: Reuters AI, Google News AI
    - Kill The Newsletter: AI Newsletters

Usage:
    from config.freshrss_client import FreshRSSClient

    client = FreshRSSClient()
    articles = client.get_articles(limit=100)
    feeds = client.list_feeds()
"""

import os
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

# EST timezone for all timestamps
EST = ZoneInfo("America/New_York")


# FreshRSS Configuration
FRESHRSS_URL = os.environ.get(
    "FRESHRSS_URL",
    "https://pivot-media-rss-feed.onrender.com"
)
FRESHRSS_AUTH = os.environ.get(
    "FRESHRSS_AUTH",
    "admin/d13c712f15c87f1d9aee574372ed7dffe7e5e880"
)
FRESHRSS_API = f"{FRESHRSS_URL}/api/greader.php"


# Source name mappings from stream ID to display name
# Updated Dec 30, 2025 - Added new AI-focused feeds, replaced general with AI-specific
STREAM_ID_TO_SOURCE = {
    "feed/3": "Bloomberg",
    "feed/8": "The Verge",
    "feed/10": "CNBC",
    "feed/11": "The Atlantic",
    "feed/16": "Google News AI",
    "feed/17": "AI Newsletters",
    "feed/23": "Reuters",
    "feed/27": "Semafor",
    "feed/28": "VentureBeat",
    # New feeds added Dec 30, 2025
    "feed/30": "The Next Web",
    "feed/31": "MIT Tech Review",
    "feed/32": "MIT News",
    "feed/33": "Science Daily",
    "feed/34": "The Guardian",
    "feed/35": "TechCrunch",  # AI-specific feed (replaced general)
    "feed/36": "TechRepublic",  # AI-specific feed (replaced general)
    "feed/37": "New York Times",  # Native RSS (replaced Google News)
    "feed/38": "WSJ",  # Dow Jones direct (replaced Google News)
}

# Domain to source name mappings for URL-based extraction
DOMAIN_TO_SOURCE = {
    "reuters.com": "Reuters",
    "cnbc.com": "CNBC",
    "theverge.com": "The Verge",
    "techcrunch.com": "TechCrunch",
    "wsj.com": "WSJ",
    "ft.com": "Financial Times",
    "bloomberg.com": "Bloomberg",
    "nytimes.com": "New York Times",
    "theatlantic.com": "The Atlantic",
    "semafor.com": "Semafor",
    "techrepublic.com": "TechRepublic",
    "venturebeat.com": "VentureBeat",
    "wired.com": "Wired",
    "arstechnica.com": "Ars Technica",
    "engadget.com": "Engadget",
    "zdnet.com": "ZDNet",
    "axios.com": "Axios",
    "politico.com": "Politico",
    "apnews.com": "AP News",
    "fortune.com": "Fortune",
    "fastcompany.com": "Fast Company",
    # New sources added Dec 30, 2025
    "thenextweb.com": "The Next Web",
    "technologyreview.com": "MIT Tech Review",
    "news.mit.edu": "MIT News",
    "sciencedaily.com": "Science Daily",
    "theguardian.com": "The Guardian",
}

# Newsletter domain mappings for Kill The Newsletter content extraction
# These newsletters are forwarded to Kill The Newsletter and need source extraction
NEWSLETTER_DOMAIN_TO_SOURCE = {
    "theaivalley.com": "AI Valley",
    "theaireport.ai": "The AI Report",
    "joinsuperhuman.ai": "Superhuman",
    "theneurondaily.com": "The Neuron",
    "superhuman.ai": "Superhuman",
    "bensbites.co": "Ben's Bites",
    "bensbites.beehiiv.com": "Ben's Bites",
    "readwrite.com": "ReadWrite AI",
    "aibreakfast.beehiiv.com": "AI Breakfast",
    "tldr.tech": "TLDR AI",
}


class FreshRSSClient:
    """
    Client for interacting with FreshRSS Google Reader API.

    Handles authentication, article fetching, and source extraction.
    """

    def __init__(self, url: str = None, auth: str = None):
        """
        Initialize the FreshRSS client.

        Args:
            url: FreshRSS instance URL (defaults to env or production URL)
            auth: Auth token (defaults to env or production token)
        """
        self.url = url or FRESHRSS_URL
        self.auth = auth or FRESHRSS_AUTH
        self.api = f"{self.url}/api/greader.php"
        self.headers = {
            "Authorization": f"GoogleLogin auth={self.auth}",
            "User-Agent": "Pivot5-FreshRSS-Client/1.0"
        }

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Make an authenticated request to FreshRSS API.

        Args:
            endpoint: API endpoint (relative to /api/greader.php)
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response or None if failed
        """
        try:
            url = f"{self.api}{endpoint}"
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=timeout
            )

            if response.status_code != 200:
                print(f"[FreshRSS] Error: HTTP {response.status_code} for {endpoint}")
                return None

            return response.json()

        except requests.exceptions.Timeout:
            print(f"[FreshRSS] Timeout fetching {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[FreshRSS] Request error: {e}")
            return None
        except ValueError as e:
            print(f"[FreshRSS] JSON parse error: {e}")
            return None

    def list_feeds(self) -> List[Dict[str, Any]]:
        """
        List all subscribed feeds.

        Returns:
            List of feed objects with id, title, url
        """
        data = self._make_request(
            "/reader/api/0/subscription/list",
            params={"output": "json"}
        )

        if not data or "subscriptions" not in data:
            return []

        return data["subscriptions"]

    def trigger_refresh(self, max_feeds: int = 50) -> bool:
        """
        Trigger FreshRSS to crawl/refresh all feeds.

        FreshRSS on Render free tier goes to sleep and stops crawling.
        This endpoint wakes it up and forces a feed refresh.

        Args:
            max_feeds: Maximum feeds to refresh per call (default 50)

        Returns:
            True if refresh was triggered successfully
        """
        try:
            # Use the actualize endpoint (from FreshRSS docs)
            # https://freshrss.github.io/FreshRSS/en/users/09_refreshing_feeds.html
            url = f"{self.url}/i/?c=feed&a=actualize&ajax=1&maxFeeds={max_feeds}"
            response = requests.get(url, timeout=30)

            if response.status_code == 200 and response.text.strip() == "OK":
                print(f"[FreshRSS] Triggered feed refresh (maxFeeds={max_feeds})")
                return True
            else:
                print(f"[FreshRSS] Refresh returned: {response.status_code} - {response.text[:50]}")
                return False

        except Exception as e:
            print(f"[FreshRSS] Failed to trigger refresh: {e}")
            return False

    def get_articles(
        self,
        limit: int = 100,
        feed_id: str = None,
        since_hours: int = 36,
        auto_refresh: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent articles from FreshRSS.

        Args:
            limit: Maximum number of articles to fetch
            feed_id: Optional specific feed ID (e.g., "feed/3")
            since_hours: Only include articles from the last N hours
            auto_refresh: Trigger FreshRSS to crawl feeds before fetching (default True)

        Returns:
            List of article dicts with normalized fields
        """
        # Trigger feed refresh to wake up FreshRSS and get fresh articles
        # This is critical because FreshRSS on Render free tier goes to sleep
        if auto_refresh:
            self.trigger_refresh()

        # Build endpoint
        if feed_id:
            endpoint = f"/reader/api/0/stream/contents/{feed_id}"
        else:
            endpoint = "/reader/api/0/stream/contents"

        # Fetch from API
        data = self._make_request(
            endpoint,
            params={"n": limit, "output": "json"}
        )

        if not data or "items" not in data:
            return []

        # Calculate cutoff time
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)

        # Process articles
        articles = []
        for item in data["items"]:
            article = self._parse_article(item)

            if not article:
                continue

            # Filter by BOTH crawl time AND publication time:
            # 1. crawl_dt: Must be within since_hours (default 24h) - prevents reprocessing
            # 2. published_dt: Must be within 72h - prevents week-old articles from flooding
            #
            # Why 72h for published? Articles can be crawled days after publication
            # (e.g., Google News, editorial delays). 72h allows 2-3 day old articles
            # that were just discovered, but blocks 7+ day old stale news.
            if article.get("crawl_dt"):
                if article["crawl_dt"] < cutoff:
                    continue

            # Published filter uses 72h window (3 days) regardless of since_hours param
            published_cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
            if article.get("published_dt"):
                if article["published_dt"] < published_cutoff:
                    continue

            articles.append(article)

        print(f"[FreshRSS] Fetched {len(articles)} articles (filtered from {len(data['items'])})")
        return articles

    def _parse_article(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a FreshRSS article item into normalized format.

        Args:
            item: Raw article item from API

        Returns:
            Normalized article dict or None if invalid
        """
        try:
            # Extract URL
            url = None
            if item.get("alternate"):
                url = item["alternate"][0].get("href")
            if not url:
                url = item.get("canonical", [{}])[0].get("href")

            if not url:
                return None

            # Extract title
            title = item.get("title", "").strip()
            if not title:
                return None

            # Extract publication timestamp (for reference/output)
            # Convert to EST for consistent timezone across pipeline
            published = item.get("published")
            published_dt = None
            if published:
                try:
                    # Parse as UTC then convert to EST
                    published_dt = datetime.fromtimestamp(published, tz=timezone.utc).astimezone(EST)
                except (ValueError, TypeError):
                    pass

            # Extract crawl timestamp (when FreshRSS discovered the article)
            # This is more reliable for filtering "recent" articles
            # Convert to EST for consistent timezone across pipeline
            crawl_ms = item.get("crawlTimeMsec")
            crawl_dt = None
            if crawl_ms:
                try:
                    # Parse as UTC then convert to EST
                    crawl_dt = datetime.fromtimestamp(int(crawl_ms) / 1000, tz=timezone.utc).astimezone(EST)
                except (ValueError, TypeError):
                    pass

            # Extract summary (needed early for newsletter source extraction)
            summary = ""
            if item.get("summary"):
                summary = item["summary"].get("content", "")
            elif item.get("content"):
                summary = item["content"].get("content", "")

            # Extract source from origin or URL
            source = None
            origin = item.get("origin", {})
            stream_id = origin.get("streamId", "")

            # Special handling for Kill The Newsletter (feed/17)
            # Extract actual newsletter name from content
            if stream_id == "feed/17":
                newsletter_source = self._extract_newsletter_source(summary)
                if newsletter_source:
                    source = newsletter_source
                else:
                    source = "AI Newsletter"  # Generic fallback
            # Try stream ID for other feeds
            elif stream_id in STREAM_ID_TO_SOURCE:
                source = STREAM_ID_TO_SOURCE[stream_id]
            # Try origin title
            elif origin.get("title"):
                source = origin["title"]
            # Fall back to URL extraction
            else:
                source = self._extract_source_from_url(url)

            return {
                "title": title,
                "url": url,
                "source_id": source or "Unknown",
                "published": published_dt.isoformat() if published_dt else None,
                "published_dt": published_dt,
                "crawl_dt": crawl_dt,  # When FreshRSS discovered the article
                "summary": summary[:500] if summary else None,  # Truncate summary
                "stream_id": stream_id,
            }

        except Exception as e:
            print(f"[FreshRSS] Error parsing article: {e}")
            return None

    def _extract_source_from_url(self, url: str) -> Optional[str]:
        """
        Extract source name from article URL.

        Args:
            url: Article URL

        Returns:
            Source name or None
        """
        if not url:
            return None

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Strip www. prefix
            if domain.startswith("www."):
                domain = domain[4:]

            # Try exact match
            if domain in DOMAIN_TO_SOURCE:
                return DOMAIN_TO_SOURCE[domain]

            # Try root domain
            parts = domain.split(".")
            if len(parts) >= 2:
                root_domain = ".".join(parts[-2:])
                if root_domain in DOMAIN_TO_SOURCE:
                    return DOMAIN_TO_SOURCE[root_domain]

            # Capitalize main domain as fallback
            if len(parts) >= 2:
                return parts[-2].capitalize()

            return None

        except Exception:
            return None

    def _extract_newsletter_source(self, content: str) -> Optional[str]:
        """
        Extract newsletter source name from content by finding known newsletter domains.

        Kill The Newsletter articles contain links to the original newsletter's website.
        We parse the content HTML/text to find these domain references.

        Args:
            content: Article summary or content HTML

        Returns:
            Newsletter source name if found, None otherwise
        """
        if not content:
            return None

        content_lower = content.lower()

        # Look for known newsletter domains in content
        for domain, source_name in NEWSLETTER_DOMAIN_TO_SOURCE.items():
            if domain in content_lower:
                return source_name

        return None

    def health_check(self) -> bool:
        """
        Check if FreshRSS API is accessible.

        Returns:
            True if API is reachable and authenticated
        """
        feeds = self.list_feeds()
        return len(feeds) > 0


# Module-level convenience functions
_client = None


def get_client() -> FreshRSSClient:
    """Get or create singleton FreshRSS client."""
    global _client
    if _client is None:
        _client = FreshRSSClient()
    return _client


def get_articles(limit: int = 100, since_hours: int = 24) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch articles.

    Args:
        limit: Maximum number of articles
        since_hours: Only include articles from last N hours

    Returns:
        List of article dicts
    """
    return get_client().get_articles(limit=limit, since_hours=since_hours)


def list_feeds() -> List[Dict[str, Any]]:
    """
    Convenience function to list feeds.

    Returns:
        List of feed dicts
    """
    return get_client().list_feeds()
