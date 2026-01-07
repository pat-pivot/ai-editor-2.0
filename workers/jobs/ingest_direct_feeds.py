"""
Direct Feed Ingestion - ONLY non-Google News URLs

This is a SEPARATE extraction process that runs AFTER Google News decoding.
It ingests articles from direct RSS feeds (Reuters, TechCrunch, etc.)
that do NOT come through Google News.

Why separate?
- Google News decoding is slow (5s per URL + rate limiting)
- Direct feeds don't need decoding
- Running together caused direct feeds to be skipped

Target Table: 'Articles - All Ingested' in AI Editor 2.0 base
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from pyairtable import Api

from utils.pivot_id import generate_pivot_id
from config.freshrss_client import FreshRSSClient

# EST timezone for all timestamps
EST = ZoneInfo("America/New_York")

# Environment variables
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_AI_EDITOR_BASE_ID = os.environ.get("AI_EDITOR_BASE_ID", "appglKSJZxmA9iHpl")
ARTICLES_TABLE_SANDBOX = os.environ.get("AIRTABLE_ARTICLES_TABLE_SANDBOX", "Articles - All Ingested")

# Source name mappings from domain to display name (same as ingest_sandbox.py)
DOMAIN_TO_SOURCE = {
    "reuters.com": "Reuters",
    "cnbc.com": "CNBC",
    "theverge.com": "The Verge",
    "techcrunch.com": "TechCrunch",
    "yahoo.com": "Yahoo Finance",
    "finance.yahoo.com": "Yahoo Finance",
    "wsj.com": "WSJ",
    "ft.com": "Financial Times",
    "bloomberg.com": "Bloomberg",
    "nytimes.com": "New York Times",
    "washingtonpost.com": "Washington Post",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "cnn.com": "CNN",
    "forbes.com": "Forbes",
    "businessinsider.com": "Business Insider",
    "wired.com": "Wired",
    "arstechnica.com": "Ars Technica",
    "engadget.com": "Engadget",
    "venturebeat.com": "VentureBeat",
    "zdnet.com": "ZDNet",
    "techrepublic.com": "TechRepublic",
    "theatlantic.com": "The Atlantic",
    "semafor.com": "Semafor",
    "axios.com": "Axios",
    "politico.com": "Politico",
    "apnews.com": "AP News",
    "marketwatch.com": "MarketWatch",
    "fortune.com": "Fortune",
    "inc.com": "Inc.",
    "fastcompany.com": "Fast Company",
    "hbr.org": "Harvard Business Review",
    "thehill.com": "The Hill",
    "foxbusiness.com": "Fox Business",
    "theregister.com": "The Register",
    "thenextweb.com": "The Next Web",
    "gizmodo.com": "Gizmodo",
}

# Domains to skip during ingestion (stock speculation, low-quality sources)
BLOCKED_DOMAINS = [
    "yahoo.com",
    "finance.yahoo.com",
    "barrons.com",
]


def is_blocked_domain(url: str) -> bool:
    """Check if URL is from a blocked domain."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return any(blocked in domain for blocked in BLOCKED_DOMAINS)
    except Exception:
        return False


def extract_source_from_url(url: str) -> Optional[str]:
    """Extract source name from a URL by matching against known domains."""
    if not url:
        return None

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]

        # Try exact match first
        if domain in DOMAIN_TO_SOURCE:
            return DOMAIN_TO_SOURCE[domain]

        # Try matching root domain
        parts = domain.split(".")
        if len(parts) >= 2:
            root_domain = ".".join(parts[-2:])
            if root_domain in DOMAIN_TO_SOURCE:
                return DOMAIN_TO_SOURCE[root_domain]

        # Fallback: capitalize the main domain name
        if len(parts) >= 2:
            main_name = parts[-2]
            return main_name.capitalize()

        return None
    except Exception:
        return None


def ingest_direct_feeds(
    limit: int = 500,
    since_hours: int = 24,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Ingest ONLY direct feed articles (non-Google News).

    This runs SEPARATELY from Google News ingestion.
    It ONLY processes URLs that are NOT from news.google.com.

    Args:
        limit: Maximum number of articles to fetch from FreshRSS
        since_hours: Only include articles from last N hours
        debug: If True, only fetch 10 articles for testing

    Returns:
        Results dict with counts and timing
    """
    print(f"")
    print(f"{'='*60}")
    print(f"[DIRECT FEED INGEST] Starting at {datetime.now(EST).isoformat()}")
    print(f"{'='*60}")
    print(f"[DIRECT FEED INGEST] This job ONLY processes non-Google News URLs")
    print(f"[DIRECT FEED INGEST] Google News URLs are handled by ingest_sandbox.py")
    print(f"")

    started_at = datetime.now(EST)
    results = {
        "started_at": started_at.isoformat(),
        "source": "FreshRSS-DirectFeeds",
        "articles_fetched": 0,
        "direct_feeds_found": 0,
        "google_news_skipped": 0,
        "articles_ingested": 0,
        "articles_skipped_duplicate": 0,
        "articles_skipped_invalid": 0,
        "articles_skipped_blocked": 0,
        "errors": []
    }

    try:
        # Initialize Airtable
        if not AIRTABLE_API_KEY:
            raise ValueError("AIRTABLE_API_KEY environment variable not set")

        api = Api(AIRTABLE_API_KEY)
        table = api.table(AIRTABLE_AI_EDITOR_BASE_ID, ARTICLES_TABLE_SANDBOX)

        # Fetch articles from FreshRSS
        fetch_limit = 10 if debug else limit
        print(f"[DIRECT FEED INGEST] Fetching articles from FreshRSS (limit={fetch_limit}, since_hours={since_hours})...")

        try:
            client = FreshRSSClient()
            articles = client.get_articles(limit=fetch_limit, since_hours=since_hours)
            results["articles_fetched"] = len(articles)
            print(f"[DIRECT FEED INGEST] Fetched {len(articles)} total articles from FreshRSS")
        except Exception as e:
            error_msg = f"Failed to fetch from FreshRSS: {e}"
            print(f"[DIRECT FEED INGEST] {error_msg}")
            results["errors"].append(error_msg)
            results["completed_at"] = datetime.now(EST).isoformat()
            return results

        if not articles:
            print("[DIRECT FEED INGEST] No articles found, exiting")
            results["completed_at"] = datetime.now(EST).isoformat()
            return results

        # FILTER: Only keep NON-Google News URLs
        direct_feed_articles = []
        for article in articles:
            url = article.get("url", "")
            if "news.google.com" in url:
                results["google_news_skipped"] += 1
            else:
                direct_feed_articles.append(article)

        results["direct_feeds_found"] = len(direct_feed_articles)

        print(f"[DIRECT FEED INGEST] Found {len(direct_feed_articles)} direct feed articles")
        print(f"[DIRECT FEED INGEST] Skipped {results['google_news_skipped']} Google News URLs")

        if not direct_feed_articles:
            print(f"[DIRECT FEED INGEST] No direct feeds to process, exiting")
            results["completed_at"] = datetime.now(EST).isoformat()
            return results

        # Log source breakdown
        print(f"")
        print(f"{'='*60}")
        print(f"[SOURCE BREAKDOWN] Direct Feed Articles by Source")
        print(f"{'='*60}")
        source_counts = {}
        for article in direct_feed_articles:
            source = article.get("source_id", "Unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            print(f"  {source}: {count}")
        print(f"{'='*60}")
        print(f"")

        results["source_breakdown"] = source_counts

        # Get existing pivot_ids for deduplication
        print("[DIRECT FEED INGEST] Fetching existing records for deduplication...")
        try:
            existing_records = table.all(fields=["pivot_id"])
            existing_pivot_ids = {
                r["fields"].get("pivot_id")
                for r in existing_records
                if r["fields"].get("pivot_id")
            }
            print(f"[DIRECT FEED INGEST] Found {len(existing_pivot_ids)} existing records")
        except Exception as e:
            print(f"[DIRECT FEED INGEST] Warning: Could not fetch existing records: {e}")
            existing_pivot_ids = set()

        # Process and create records
        ingested_sources = {}
        duplicate_samples = []  # Track sample duplicates for debugging
        MAX_DUPLICATE_SAMPLES = 10  # Log first N duplicates for verification

        for article in direct_feed_articles:
            url = article.get("url")
            title = article.get("title")

            # Skip if no URL and no title
            if not url and not title:
                results["articles_skipped_invalid"] += 1
                continue

            # Skip blocked domains
            if is_blocked_domain(url):
                results["articles_skipped_blocked"] += 1
                continue

            # Generate pivot_id
            pivot_id = generate_pivot_id(url, title)
            if not pivot_id:
                results["articles_skipped_invalid"] += 1
                continue

            # Check for duplicates
            if pivot_id in existing_pivot_ids:
                results["articles_skipped_duplicate"] += 1
                # Log sample duplicates for verification
                if len(duplicate_samples) < MAX_DUPLICATE_SAMPLES:
                    duplicate_samples.append({
                        "pivot_id": pivot_id,
                        "url": url[:100] if url else None,
                        "title": title[:50] if title else None
                    })
                continue

            # Extract source name from URL
            source_name = extract_source_from_url(url)
            if not source_name:
                source_name = article.get("source_id", "Unknown")

            # Create record - NOTE: NO gnews_url field (this is a direct feed)
            record = {
                "pivot_id": pivot_id,
                "original_url": url,
                "source_name": source_name,
                "headline": title,
                "date_ingested": datetime.now(EST).isoformat(),
                "needs_ai": True,
                "fit_status": "pending",
            }

            # Add published date if available
            if article.get("published"):
                record["date_og_published"] = article["published"]

            # Remove None values
            record = {k: v for k, v in record.items() if v is not None}

            try:
                table.create(record)
                existing_pivot_ids.add(pivot_id)
                results["articles_ingested"] += 1

                # Track source for summary
                ingested_sources[source_name] = ingested_sources.get(source_name, 0) + 1

                if results["articles_ingested"] % 10 == 0:
                    print(f"[DIRECT FEED INGEST] Progress: {results['articles_ingested']} articles ingested")

            except Exception as e:
                error_msg = f"Error creating record for {pivot_id}: {str(e)}"
                print(f"[DIRECT FEED INGEST] {error_msg}")
                results["errors"].append(error_msg)

        # Summary
        print(f"")
        print(f"{'='*60}")
        print(f"[DIRECT FEED INGEST] COMPLETE")
        print(f"{'='*60}")
        print(f"  Direct feeds found:    {results['direct_feeds_found']}")
        print(f"  Articles ingested:     {results['articles_ingested']}")
        print(f"  Skipped (duplicates):  {results['articles_skipped_duplicate']}")
        print(f"  Skipped (invalid):     {results['articles_skipped_invalid']}")
        print(f"  Skipped (blocked):     {results['articles_skipped_blocked']}")
        print(f"  Google News skipped:   {results['google_news_skipped']}")
        print(f"{'='*60}")

        if ingested_sources:
            print(f"")
            print(f"[DIRECT FEED INGEST] Ingested by source:")
            for source, count in sorted(ingested_sources.items(), key=lambda x: -x[1]):
                print(f"  {source}: {count}")

        results["ingested_sources"] = ingested_sources

        # Log sample duplicates for verification
        if duplicate_samples:
            print(f"")
            print(f"{'='*60}")
            print(f"[DUPLICATE VERIFICATION] Sample duplicates (first {len(duplicate_samples)}):")
            print(f"{'='*60}")
            for i, dup in enumerate(duplicate_samples, 1):
                print(f"  {i}. pivot_id: {dup['pivot_id']}")
                print(f"     URL: {dup['url']}")
                print(f"     Title: {dup['title']}")
                print(f"")
            print(f"[DUPLICATE VERIFICATION] Use these pivot_ids to verify in Airtable")
            print(f"{'='*60}")

    except Exception as e:
        error_msg = f"Direct feed ingestion failed: {str(e)}"
        print(f"[DIRECT FEED INGEST] {error_msg}")
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()

    results["completed_at"] = datetime.now(EST).isoformat()
    results["processed"] = results["articles_ingested"]
    return results


# Alias for RQ compatibility
def run_direct_feed_ingest(**kwargs) -> Dict[str, Any]:
    """Wrapper function for RQ job queue."""
    return ingest_direct_feeds(**kwargs)
