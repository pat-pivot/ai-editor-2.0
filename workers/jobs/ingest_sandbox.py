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
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

# EST timezone for all timestamps
EST = ZoneInfo("America/New_York")

from pyairtable import Api
from redis import Redis
from rq import Queue

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


async def resolve_google_news_url(url: str) -> tuple[str, Optional[str]]:
    """
    Resolve a Google News URL to the actual article URL.

    Uses the googlenewsdecoder package which calls Google's batchexecute API.
    This is the ONLY reliable way to decode modern Google News URLs.

    Args:
        url: Google News article URL

    Returns:
        Tuple of (resolved_url, extracted_source_name)
    """
    # Only process Google News URLs
    if not url or "news.google.com" not in url:
        return url, None

    try:
        # Run blocking gnewsdecoder in thread pool
        # The gnewsdecoder package makes HTTP calls to Google's batchexecute API
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _google_news_executor,
            lambda: gnewsdecoder(url, interval=0.3)  # 0.3s delay between retries
        )

        if result.get("status") and result.get("decoded_url"):
            decoded_url = result["decoded_url"]
            source_name = extract_source_from_url(decoded_url)
            print(f"[Ingest Sandbox] Decoded Google News URL: {url[:50]}... -> {decoded_url[:60]}... (source: {source_name})")
            return decoded_url, source_name
        else:
            print(f"[Ingest Sandbox] Could not decode Google News URL: {url[:60]}...")
            return url, "Google News"

    except Exception as e:
        print(f"[Ingest Sandbox] Error decoding Google News URL: {e}")
        return url, "Google News"


async def resolve_article_urls(articles: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    """
    Resolve Google News redirect URLs to actual article URLs.

    Uses the googlenewsdecoder package which calls Google's batchexecute API.
    Processes in small batches with delays to avoid rate limiting.

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

    # Process in smaller batches with delays to avoid Google rate limiting
    batch_size = 10
    resolved_count = 0

    for batch_start in range(0, len(google_news_articles), batch_size):
        batch = google_news_articles[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1
        total_batches = (len(google_news_articles) + batch_size - 1) // batch_size
        print(f"[Ingest Sandbox] Processing batch {batch_num}/{total_batches} ({len(batch)} URLs)...")

        tasks = [
            resolve_google_news_url(articles[idx]["url"])
            for idx, _ in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (idx, article), result in zip(batch, results):
            if isinstance(result, Exception):
                print(f"[Ingest Sandbox] Failed to resolve URL for article: {result}")
                continue

            resolved_url, source_name = result

            # Update article with resolved URL
            if resolved_url and resolved_url != article["url"]:
                articles[idx]["url"] = resolved_url
                resolved_count += 1

            # Update source_id if we got a better one from the resolved URL
            if source_name:
                articles[idx]["source_id"] = source_name

        # Add delay between batches to avoid rate limiting
        if batch_start + batch_size < len(google_news_articles):
            await asyncio.sleep(1)

    print(f"[Ingest Sandbox] Resolved {resolved_count} Google News URLs to actual sources")
    return articles, resolved_count


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

# Redis configuration for job chaining
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')


def ingest_articles_sandbox(
    debug: bool = False,
    limit: int = 1000,  # Increased to get all articles before filtering
    since_hours: int = 36
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
        except Exception as e:
            print(f"[Ingest Sandbox] Warning: URL resolution failed: {e}")
            # Continue with unresolved URLs rather than failing entirely

        # Get existing pivot_ids from Airtable for deduplication
        print("[Ingest Sandbox] Fetching existing records for deduplication...")
        try:
            existing_records = table.all(fields=["pivot_id"])
            existing_pivot_ids = {
                r["fields"].get("pivot_id")
                for r in existing_records
                if r["fields"].get("pivot_id")
            }
            print(f"[Ingest Sandbox] Found {len(existing_pivot_ids)} existing records")
        except Exception as e:
            print(f"[Ingest Sandbox] Warning: Could not fetch existing records: {e}")
            existing_pivot_ids = set()

        # Process and create new records
        for article in articles:
            url = article.get("url")
            title = article.get("title")

            # Skip if no URL and no title
            if not url and not title:
                results["articles_skipped_invalid"] += 1
                continue

            # Generate pivot_id
            pivot_id = generate_pivot_id(url, title)
            if not pivot_id:
                results["articles_skipped_invalid"] += 1
                continue

            # Check for duplicates
            if pivot_id in existing_pivot_ids:
                results["articles_skipped_duplicate"] += 1
                continue

            # Prepare Airtable record
            # Fields based on new 'Articles - All Ingested' schema
            # NOTE: storyId is NOT generated here - it will be created later
            # in the decoration step from the AI-generated headline
            record = {
                "pivot_id": pivot_id,                    # Primary deduplication key (hash)
                "original_url": url,                     # Source URL
                "source_name": article.get("source_id", "Unknown"),  # Publication name
                "headline": title,                       # Original article title
                "date_ingested": datetime.now(EST).isoformat(),  # When we ingested (EST)
                "needs_ai": True,                        # Flag for AI Scoring job
                "fit_status": "pending",                 # Single select status
            }

            # Add optional fields if present
            if article.get("published"):
                record["date_og_published"] = article["published"]

            # Remove None values (Airtable doesn't like them)
            record = {k: v for k, v in record.items() if v is not None}

            try:
                table.create(record)
                existing_pivot_ids.add(pivot_id)  # Prevent duplicates within batch
                results["articles_ingested"] += 1
            except Exception as e:
                error_msg = f"Error creating record for {pivot_id}: {str(e)}"
                print(f"[Ingest Sandbox] {error_msg}")
                results["errors"].append(error_msg)

        print(f"[Ingest Sandbox] Ingestion complete:")
        print(f"  - Articles fetched: {results['articles_fetched']}")
        print(f"  - Google News URLs resolved: {results['google_news_resolved']}")
        print(f"  - Articles ingested: {results['articles_ingested']}")
        print(f"  - Skipped (duplicates): {results['articles_skipped_duplicate']}")
        print(f"  - Skipped (invalid): {results['articles_skipped_invalid']}")
        print(f"  - Errors: {len(results['errors'])}")

        # AUTOMATIC CHAINING: Trigger AI Scoring if we ingested any articles
        if results["articles_ingested"] > 0:
            print(f"[Ingest Sandbox] Chaining AI Scoring job for {results['articles_ingested']} new articles...")
            try:
                from jobs.ai_scoring_sandbox import run_ai_scoring_sandbox

                redis_conn = Redis.from_url(REDIS_URL)
                queue = Queue('default', connection=redis_conn)

                # Enqueue AI Scoring - no cap, process all ingested articles
                ai_job = queue.enqueue(
                    run_ai_scoring_sandbox,
                    batch_size=results["articles_ingested"],
                    job_timeout='60m'
                )

                results["ai_scoring_job_id"] = ai_job.id
                print(f"[Ingest Sandbox] AI Scoring job enqueued: {ai_job.id}")

            except Exception as e:
                error_msg = f"Failed to chain AI Scoring job: {str(e)}"
                print(f"[Ingest Sandbox] {error_msg}")
                results["errors"].append(error_msg)
        else:
            print("[Ingest Sandbox] No new articles ingested, skipping AI Scoring")

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
