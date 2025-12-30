"""
FreshRSS API Client for Ingestion Engine Sandbox

This client connects to the FreshRSS instance running on Render
and fetches articles using the Google Reader API.

Production Instance:
    URL: https://pivot-media-rss-feed.onrender.com
    API: https://pivot-media-rss-feed.onrender.com/api/greader.php

14 Active Feeds (Dec 29, 2025):
    - Direct RSS: Bloomberg, The Verge, TechCrunch, The Atlantic, VentureBeat
    - Google News RSS: WSJ, CNBC, NYT, Semafor, TechRepublic, Reuters, AI News
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
STREAM_ID_TO_SOURCE = {
    "feed/3": "Bloomberg",
    "feed/6": "WSJ",
    "feed/7": "WSJ",
    "feed/8": "The Verge",
    "feed/9": "TechCrunch",
    "feed/10": "CNBC",
    "feed/11": "The Atlantic",
    "feed/12": "TechRepublic",
    "feed/13": "New York Times",
    "feed/16": "Google News AI",
    "feed/17": "AI Newsletters",
    "feed/18": "Reuters",
    "feed/27": "Semafor",
    "feed/28": "VentureBeat",
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

    def get_articles(
        self,
        limit: int = 100,
        feed_id: str = None,
        since_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent articles from FreshRSS.

        Args:
            limit: Maximum number of articles to fetch
            feed_id: Optional specific feed ID (e.g., "feed/3")
            since_hours: Only include articles from the last N hours

        Returns:
            List of article dicts with normalized fields
        """
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

            # Filter by publication date
            if article.get("published_dt"):
                if article["published_dt"] < cutoff:
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

            # Extract timestamp
            published = item.get("published")
            published_dt = None
            if published:
                try:
                    published_dt = datetime.fromtimestamp(published, tz=timezone.utc)
                except (ValueError, TypeError):
                    pass

            # Extract source from origin or URL
            source = None
            origin = item.get("origin", {})
            stream_id = origin.get("streamId", "")

            # Try stream ID first
            if stream_id in STREAM_ID_TO_SOURCE:
                source = STREAM_ID_TO_SOURCE[stream_id]
            # Try origin title
            elif origin.get("title"):
                source = origin["title"]
            # Fall back to URL extraction
            else:
                source = self._extract_source_from_url(url)

            # Extract summary
            summary = ""
            if item.get("summary"):
                summary = item["summary"].get("content", "")
            elif item.get("content"):
                summary = item["content"].get("content", "")

            return {
                "title": title,
                "url": url,
                "source_id": source or "Unknown",
                "published": published_dt.isoformat() if published_dt else None,
                "published_dt": published_dt,
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
