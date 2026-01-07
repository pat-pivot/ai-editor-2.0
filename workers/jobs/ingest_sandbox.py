"""
Step 0 Sandbox: FreshRSS-Based Ingestion Job

Fetches articles from FreshRSS and creates records in AI Editor 2.0 Airtable.
This is the SANDBOX version - writes to new tables, doesn't affect production.

SANDBOX ARCHITECTURE:
  FreshRSS → Full-Stack App → AI Editor 2.0 Base (appglKSJZxmA9iHpl)

  Step 0a (Ingest) → 'Articles - All Ingested' table (needs_ai=true)
  Step 0b (AI Scoring) → Updates Articles + Creates 'Newsletter Selects'

DIFFERENCES FROM PRODUCTION (ingest.py):
  1. Data Source: FreshRSS API instead of RSS.app feeds
  2. Target Base: AI Editor 2.0 (appglKSJZxmA9iHpl) instead of Pivot Media Master
  3. Fields: Simplified schema with fit_status single-select
  4. Newsletter: Single newsletter (pivot_ai) instead of 3

Target Table: 'Articles - All Ingested' in AI Editor 2.0 base
"""

import os
import re
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

# EST timezone for all timestamps
EST = ZoneInfo("America/New_York")

from pyairtable import Api
from anthropic import Anthropic

# Google News URL decoding - calls Google's batchexecute API
from googlenewsdecoder import gnewsdecoder

# Import local utilities
from utils.pivot_id import generate_pivot_id
from config.freshrss_client import FreshRSSClient, get_articles

# Thread pool for blocking gnewsdecoder calls (it makes HTTP requests)
_google_news_executor = ThreadPoolExecutor(max_workers=10)

# Source name mappings from domain to display name
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
    """
    Extract source name from a URL by matching against known domains.

    Args:
        url: Article URL

    Returns:
        Source name if found, None otherwise
    """
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

        # Try matching root domain (e.g., "news.yahoo.com" -> "yahoo.com")
        parts = domain.split(".")
        if len(parts) >= 2:
            root_domain = ".".join(parts[-2:])
            if root_domain in DOMAIN_TO_SOURCE:
                return DOMAIN_TO_SOURCE[root_domain]

        # Fallback: capitalize the main domain name
        # e.g., "techrepublic.com" -> "Techrepublic"
        if len(parts) >= 2:
            main_name = parts[-2]
            return main_name.capitalize()

        return None
    except Exception:
        return None


async def resolve_google_news_url(url: str, retry_count: int = 0) -> tuple[str, Optional[str]]:
    """
    Resolve a Google News URL to the actual article URL.

    Uses the googlenewsdecoder package which calls Google's batchexecute API.
    This is the ONLY reliable way to decode modern Google News URLs.

    RATE LIMITING: Uses AGGRESSIVE timing to avoid Google 429 errors:
      - 3.0s interval in gnewsdecoder (increased from 2.0s)
      - 5s between each URL decode (matching repair_google_news.py)
      - Up to 3 retries with exponential backoff (30s, 60s, 120s)

    Args:
        url: Google News article URL
        retry_count: Current retry attempt (0-2)

    Returns:
        Tuple of (resolved_url, extracted_source_name)
    """
    # Only process Google News URLs
    if not url or "news.google.com" not in url:
        return url, None

    max_retries = 3

    # Log each decode attempt
    print(f"[GNEWS DECODE] Attempting: {url[:80]}...")

    try:
        # Run blocking gnewsdecoder in thread pool
        # The gnewsdecoder package makes HTTP calls to Google's batchexecute API
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _google_news_executor,
            lambda: gnewsdecoder(url, interval=3.0)  # 3s delay - more conservative to avoid 429
        )

        if result.get("status") and result.get("decoded_url"):
            decoded_url = result["decoded_url"]
            source_name = extract_source_from_url(decoded_url)
            print(f"[GNEWS DECODE] ✅ SUCCESS: {url[:50]}...")
            print(f"[GNEWS DECODE]    → Resolved to: {decoded_url}")
            print(f"[GNEWS DECODE]    → Source extracted: {source_name}")
            return decoded_url, source_name
        else:
            error_msg = result.get("message", "Unknown error")
            error_str = str(error_msg).lower()

            # Check for retryable errors (rate limiting, timeouts, connection issues)
            is_retryable = any(x in error_str for x in [
                "429", "rate", "timeout", "connection", "network",
                "temporary", "unavailable", "overloaded", "503", "502"
            ])

            if is_retryable and retry_count < max_retries:
                backoff = 30 * (2 ** retry_count)  # 30s, 60s, 120s
                print(f"[GNEWS DECODE] ⚠️ RETRYABLE ERROR - waiting {backoff}s before retry {retry_count + 1}/{max_retries}...")
                print(f"[GNEWS DECODE]    → Error was: {error_msg}")
                await asyncio.sleep(backoff)
                return await resolve_google_news_url(url, retry_count + 1)

            print(f"[GNEWS DECODE] ❌ FAILED: {url[:60]}...")
            print(f"[GNEWS DECODE]    → Error: {error_msg}")
            print(f"[GNEWS DECODE]    → Retries exhausted: {retry_count >= max_retries}")
            return url, "Google News"

    except Exception as e:
        error_str = str(e).lower()

        # Check for retryable exceptions (rate limiting, timeouts, connection issues)
        is_retryable = any(x in error_str for x in [
            "429", "rate", "timeout", "connection", "network",
            "temporary", "unavailable", "overloaded", "503", "502",
            "reset", "refused", "eof", "ssl"
        ])

        if is_retryable and retry_count < max_retries:
            backoff = 30 * (2 ** retry_count)  # 30s, 60s, 120s
            print(f"[GNEWS DECODE] ⚠️ RETRYABLE EXCEPTION - waiting {backoff}s before retry {retry_count + 1}/{max_retries}...")
            print(f"[GNEWS DECODE]    → Exception was: {e}")
            await asyncio.sleep(backoff)
            return await resolve_google_news_url(url, retry_count + 1)

        print(f"[GNEWS DECODE] ❌ EXCEPTION: {url[:60]}...")
        print(f"[GNEWS DECODE]    → Error: {e}")
        print(f"[GNEWS DECODE]    → Retries exhausted: {retry_count >= max_retries}")
        return url, "Google News"


async def resolve_article_urls(articles: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    """
    Resolve Google News redirect URLs to actual article URLs.

    Uses the googlenewsdecoder package which calls Google's batchexecute API.
    Processes in small batches with CONSERVATIVE delays to avoid rate limiting.

    RATE LIMITING STRATEGY (learned from repair_google_news.py):
      - Small batch size (5 URLs per batch)
      - Sequential processing within batches (not parallel) to avoid hammering Google
      - 5 second delay between batches
      - 2 second delay between individual URLs within a batch

    Args:
        articles: List of article dicts from FreshRSS

    Returns:
        Tuple of (articles with resolved URLs and updated source_ids, count of resolved URLs)
    """
    google_news_articles = [
        (i, a) for i, a in enumerate(articles)
        if a.get("url") and "news.google.com" in a.get("url", "")
    ]

    if not google_news_articles:
        return articles, 0

    print(f"[Ingest Sandbox] Resolving {len(google_news_articles)} Google News URLs using googlenewsdecoder...")
    print(f"[Ingest Sandbox] Using conservative rate limiting (3s interval, 5s between URLs, 15s between batches)")

    # CONSERVATIVE rate limiting to avoid Google 429 errors
    # Based on repair_google_news.py which uses even more conservative timing
    batch_size = 5  # Reduced from 10
    resolved_count = 0
    failed_count = 0

    for batch_start in range(0, len(google_news_articles), batch_size):
        batch = google_news_articles[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1
        total_batches = (len(google_news_articles) + batch_size - 1) // batch_size
        print(f"[Ingest Sandbox] Processing batch {batch_num}/{total_batches} ({len(batch)} URLs)...")

        # Process URLs SEQUENTIALLY within batch to avoid hammering Google
        for idx, article in batch:
            url = articles[idx]["url"]

            # CRITICAL: Store original Google News URL for deduplication
            # This prevents duplicates when resolution fails inconsistently
            articles[idx]["gnews_url"] = url

            try:
                resolved_url, source_name = await resolve_google_news_url(url)

                # Update article with resolved URL
                if resolved_url and resolved_url != url:
                    articles[idx]["url"] = resolved_url
                    resolved_count += 1

                # Update source_id if we got a better one from the resolved URL
                if source_name and source_name != "Google News":
                    articles[idx]["source_id"] = source_name
                elif source_name == "Google News":
                    failed_count += 1

            except Exception as e:
                print(f"[Ingest Sandbox] Failed to resolve URL: {e}")
                failed_count += 1

            # 5 second delay between individual URLs (matching repair_google_news.py)
            await asyncio.sleep(5)

        # 15 second delay between batches to avoid rate limiting
        if batch_start + batch_size < len(google_news_articles):
            print(f"[Ingest Sandbox] Batch complete, waiting 15s before next batch...")
            await asyncio.sleep(15)

    # Log detailed summary
    print(f"")
    print(f"{'='*60}")
    print(f"[GNEWS DECODE] SUMMARY")
    print(f"{'='*60}")
    print(f"  Total Google News URLs: {len(google_news_articles)}")
    print(f"  Successfully decoded:   {resolved_count}")
    print(f"  Failed/Unresolved:      {failed_count}")
    success_rate = (resolved_count / len(google_news_articles) * 100) if google_news_articles else 0
    print(f"  Success rate:           {success_rate:.1f}%")
    print(f"{'='*60}")
    print(f"")
    return articles, resolved_count


# =============================================================================
# AIRTABLE CONFIGURATION
# =============================================================================

# Airtable configuration for AI Editor 2.0 base (SANDBOX)
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_AI_EDITOR_BASE_ID = os.environ.get(
    "AIRTABLE_AI_EDITOR_BASE_ID",
    "appglKSJZxmA9iHpl"  # AI Editor 2.0 base
)
ARTICLES_TABLE_SANDBOX = os.environ.get(
    "AIRTABLE_ARTICLES_TABLE_SANDBOX",
    "Articles - All Ingested"  # Use table name if ID not set
)



def ingest_articles_sandbox(
    debug: bool = False,
    limit: int = 1000,  # Increased to get all articles before filtering
    since_hours: int = 24
) -> Dict[str, Any]:
    """
    Main sandbox ingestion job function.

    Fetches articles from FreshRSS, deduplicates against existing records,
    and creates new records in AI Editor 2.0 Airtable.

    Args:
        debug: If True, only fetch 10 articles for testing
        limit: Maximum number of articles to fetch from FreshRSS
        since_hours: Only include articles from last N hours

    Returns:
        Results dict with counts and timing
    """
    print(f"[Ingest Sandbox] Starting at {datetime.now(EST).isoformat()}")
    print(f"[Ingest Sandbox] Debug mode: {debug}")
    print(f"[Ingest Sandbox] Target base: {AIRTABLE_AI_EDITOR_BASE_ID}")
    started_at = datetime.now(EST)

    results = {
        "started_at": started_at.isoformat(),
        "source": "FreshRSS",
        "articles_fetched": 0,
        "articles_ingested": 0,
        "articles_skipped_duplicate": 0,
        "articles_skipped_invalid": 0,
        "articles_skipped_blocked": 0,
        "google_news_resolved": 0,
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
        print(f"[Ingest Sandbox] Fetching articles from FreshRSS (limit={fetch_limit}, since_hours={since_hours})...")

        try:
            client = FreshRSSClient()
            articles = client.get_articles(limit=fetch_limit, since_hours=since_hours)
            results["articles_fetched"] = len(articles)
            print(f"[Ingest Sandbox] Fetched {len(articles)} articles from FreshRSS")

            # Log source breakdown from FreshRSS
            print(f"")
            print(f"{'='*60}")
            print(f"[SOURCE BREAKDOWN] Articles by Source (from FreshRSS)")
            print(f"{'='*60}")
            source_counts = {}
            google_news_count = 0
            direct_feed_count = 0
            for article in articles:
                source = article.get("source_id", "Unknown")
                url = article.get("url", "")
                source_counts[source] = source_counts.get(source, 0) + 1
                if "news.google.com" in url:
                    google_news_count += 1
                else:
                    direct_feed_count += 1

            # Sort by count descending
            for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
                print(f"  {source}: {count}")
            print(f"{'='*60}")
            print(f"  TOTAL: {len(articles)} articles")
            print(f"  - Google News URLs (need decoding): {google_news_count}")
            print(f"  - Direct feed URLs: {direct_feed_count}")
            print(f"{'='*60}")
            print(f"")

        except Exception as e:
            error_msg = f"Failed to fetch from FreshRSS: {e}"
            print(f"[Ingest Sandbox] {error_msg}")
            results["errors"].append(error_msg)
            results["completed_at"] = datetime.now(EST).isoformat()
            return results

        if not articles:
            print("[Ingest Sandbox] No articles found, exiting")
            results["completed_at"] = datetime.now(EST).isoformat()
            return results

        # Resolve Google News URLs to get actual article URLs and sources
        # This decodes news.google.com redirect URLs to their real destinations
        try:
            articles, google_news_resolved = asyncio.run(resolve_article_urls(articles))
            results["google_news_resolved"] = google_news_resolved

            # Log POST-RESOLUTION source breakdown
            print(f"")
            print(f"{'='*60}")
            print(f"[SOURCE BREAKDOWN] After Google News URL Resolution")
            print(f"{'='*60}")
            post_resolution_sources = {}
            still_google_news = 0
            for article in articles:
                source = article.get("source_id", "Unknown")
                url = article.get("url", "")
                post_resolution_sources[source] = post_resolution_sources.get(source, 0) + 1
                if "news.google.com" in url:
                    still_google_news += 1

            # Sort by count descending
            for source, count in sorted(post_resolution_sources.items(), key=lambda x: -x[1]):
                marker = " ⚠️ (unresolved)" if source == "Google News" else ""
                print(f"  {source}: {count}{marker}")
            print(f"{'='*60}")
            if still_google_news > 0:
                print(f"  ⚠️ WARNING: {still_google_news} URLs still point to news.google.com")
            else:
                print(f"  ✅ All Google News URLs successfully resolved!")
            print(f"{'='*60}")
            print(f"")

            # Store source breakdown in results for dashboard visibility
            results["source_breakdown"] = post_resolution_sources

        except Exception as e:
            print(f"[Ingest Sandbox] Warning: URL resolution failed: {e}")
            # Continue with unresolved URLs rather than failing entirely

        # Get existing pivot_ids AND gnews_urls from Airtable for deduplication
        # CRITICAL: We check BOTH to prevent duplicates when Google News decoding fails inconsistently
        print("[Ingest Sandbox] Fetching existing records for deduplication...")
        try:
            existing_records = table.all(fields=["pivot_id", "gnews_url"])
            existing_pivot_ids = {
                r["fields"].get("pivot_id")
                for r in existing_records
                if r["fields"].get("pivot_id")
            }
            # Also track existing Google News URLs for deduplication
            existing_gnews_urls = {
                r["fields"].get("gnews_url")
                for r in existing_records
                if r["fields"].get("gnews_url")
            }
            print(f"[Ingest Sandbox] Found {len(existing_pivot_ids)} existing records, {len(existing_gnews_urls)} Google News URLs")
        except Exception as e:
            print(f"[Ingest Sandbox] Warning: Could not fetch existing records: {e}")
            existing_pivot_ids = set()
            existing_gnews_urls = set()

        # Process and create new records
        # Track sources of successfully ingested articles
        ingested_sources = {}

        for article in articles:
            url = article.get("url")
            title = article.get("title")

            # Skip if no URL and no title
            if not url and not title:
                results["articles_skipped_invalid"] += 1
                continue

            # Skip blocked domains (Yahoo Finance, etc.)
            if is_blocked_domain(url):
                results["articles_skipped_blocked"] += 1
                continue

            # Generate pivot_id
            pivot_id = generate_pivot_id(url, title)
            if not pivot_id:
                results["articles_skipped_invalid"] += 1
                continue

            # Check for duplicates - BOTH pivot_id AND gnews_url
            # This prevents duplicates when Google News decoding fails inconsistently
            # (same article gets different pivot_ids when resolution fails vs succeeds)
            gnews_url = article.get("gnews_url")  # Original Google News URL if present

            if pivot_id in existing_pivot_ids:
                results["articles_skipped_duplicate"] += 1
                continue

            # Also check if this Google News URL was already ingested
            # This catches cases where decoding failed previously but succeeds now
            if gnews_url and gnews_url in existing_gnews_urls:
                print(f"[Ingest Sandbox] Skipping duplicate (gnews_url match): {gnews_url[:80]}...")
                results["articles_skipped_duplicate"] += 1
                continue

            # Prepare Airtable record
            # Fields based on new 'Articles - All Ingested' schema
            # NOTE: storyId is NOT generated here - it will be created later
            # in the decoration step from the AI-generated headline
            record = {
                "pivot_id": pivot_id,                    # Primary deduplication key (hash)
                "original_url": url,                     # Source URL (resolved if Google News)
                "source_name": article.get("source_id", "Unknown"),  # Publication name
                "headline": title,                       # Original article title
                "date_ingested": datetime.now(EST).isoformat(),  # When we ingested (EST)
                "needs_ai": True,                        # Flag for AI Scoring job
                "fit_status": "pending",                 # Single select status
            }

            # Store Google News URL for deduplication (only if this came from Google News)
            if gnews_url:
                record["gnews_url"] = gnews_url

            # Add optional fields if present
            if article.get("published"):
                record["date_og_published"] = article["published"]

            # Remove None values (Airtable doesn't like them)
            record = {k: v for k, v in record.items() if v is not None}

            try:
                table.create(record)
                existing_pivot_ids.add(pivot_id)  # Prevent duplicates within batch
                if gnews_url:
                    existing_gnews_urls.add(gnews_url)  # Also track gnews_url for batch dedup
                results["articles_ingested"] += 1

                # Track source for ingested articles summary
                source_name = record.get("source_name", "Unknown")
                ingested_sources[source_name] = ingested_sources.get(source_name, 0) + 1
            except Exception as e:
                error_msg = f"Error creating record for {pivot_id}: {str(e)}"
                print(f"[Ingest Sandbox] {error_msg}")
                results["errors"].append(error_msg)

        # Store ingested sources in results for dashboard visibility
        results["ingested_sources"] = ingested_sources

        # Log final summary
        print(f"")
        print(f"{'='*60}")
        print(f"[INGESTION COMPLETE] Final Summary")
        print(f"{'='*60}")
        print(f"  Articles fetched from FreshRSS: {results['articles_fetched']}")
        print(f"  Google News URLs decoded:       {results['google_news_resolved']}")
        print(f"  Articles ingested to Airtable:  {results['articles_ingested']}")
        print(f"  Skipped (duplicates):           {results['articles_skipped_duplicate']}")
        print(f"  Skipped (invalid):              {results['articles_skipped_invalid']}")
        print(f"  Skipped (blocked domains):      {results['articles_skipped_blocked']}")
        print(f"  Errors:                         {len(results['errors'])}")
        print(f"{'='*60}")

        # Log ingested sources breakdown
        if results.get("ingested_sources"):
            print(f"")
            print(f"[INGESTED] Articles by Source (what went into Airtable):")
            for source, count in sorted(results["ingested_sources"].items(), key=lambda x: -x[1]):
                print(f"  {source}: {count}")
            print(f"")

        # NOTE: AI Scoring is now triggered SEPARATELY via the dashboard
        # (removed automatic chaining to allow manual control)
        if results["articles_ingested"] > 0:
            print(f"[Ingest Sandbox] {results['articles_ingested']} articles need AI scoring - trigger via dashboard")

    except Exception as e:
        error_msg = f"Ingestion job failed: {str(e)}"
        print(f"[Ingest Sandbox] {error_msg}")
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()

    results["completed_at"] = datetime.now(EST).isoformat()
    # Add 'processed' key for UI compatibility
    results["processed"] = results["articles_ingested"]
    return results


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": ingest_articles_sandbox,
    "trigger": "cron",
    "hour": 20,  # 8 PM UTC = 3 PM EST
    "minute": 0,
    "id": "step0_ingest_sandbox",
    "replace_existing": True
}
