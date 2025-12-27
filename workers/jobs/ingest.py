"""
Step 0: RSS Ingestion Job

Fetches articles from RSS feeds and creates records in Airtable.
This is Step 0 of the newsletter pipeline - raw ingestion to Articles table.

ARCHITECTURE (ONE-CLICK PIPELINE):
  Step 0a (Ingest) → Articles table (raw RSS data, needs_ai=true)
  Step 0b (AI Scoring) → Updates Articles (needs_ai=false) + Creates Newsletter Stories

  ONE CLICK triggers both steps automatically in sequence.

Target Table: Articles (tblGumae8KDpsrWvh) in Pivot Media Master base
Output Table: Newsletter Stories (tblY78ziWp5yhiGXp) for high-interest articles
"""

import asyncio
import aiohttp
import feedparser
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from pyairtable import Api
from urllib.parse import urlparse
from redis import Redis
from rq import Queue

# Import local utilities
from utils.pivot_id import generate_pivot_id
from config.rss_feeds import get_feeds


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


async def resolve_google_news_url(
    session: aiohttp.ClientSession,
    url: str
) -> tuple[str, Optional[str]]:
    """
    Resolve a Google News redirect URL to the actual article URL.

    Google News RSS feeds contain URLs like:
    https://news.google.com/rss/articles/...

    This follows the redirect to get the real article URL.

    Args:
        session: aiohttp client session
        url: Potentially a Google News redirect URL

    Returns:
        Tuple of (resolved_url, extracted_source_name)
    """
    # Only process Google News URLs
    if not url or "news.google.com" not in url:
        return url, None

    try:
        # Follow redirects to get the final URL
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=10),
            allow_redirects=True,
            headers={"User-Agent": "Pivot5-NewsBot/1.0"}
        ) as response:
            final_url = str(response.url)

            # Extract source from the resolved URL
            source_name = extract_source_from_url(final_url)

            print(f"[Ingest] Resolved Google News URL: {url[:60]}... -> {final_url[:60]}... (source: {source_name})")
            return final_url, source_name

    except Exception as e:
        print(f"[Ingest] Failed to resolve Google News URL: {e}")
        return url, None


# Airtable configuration
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appwSozYTkrsQWUXB")  # Pivot Media Master
ARTICLES_TABLE = os.environ.get(
    "AIRTABLE_ARTICLES_TABLE",
    "tblGumae8KDpsrWvh"  # Articles table - raw ingestion target
)

# Redis configuration for job chaining
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')


async def fetch_feed(
    session: aiohttp.ClientSession,
    feed: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Fetch and parse a single RSS feed.

    Args:
        session: aiohttp client session
        feed: Feed configuration dict with name, url, source_id

    Returns:
        List of parsed article dicts
    """
    try:
        async with session.get(
            feed["url"],
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Pivot5-NewsBot/1.0"}
        ) as response:
            if response.status != 200:
                print(f"[Ingest] Error fetching {feed['name']}: HTTP {response.status}")
                return []

            content = await response.text()
            parsed = feedparser.parse(content)

            articles = []
            for entry in parsed.entries:
                # Extract image URL from various RSS formats
                image_url = None
                if hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url')
                elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get('url')
                elif hasattr(entry, 'enclosures') and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get('type', '').startswith('image/'):
                            image_url = enc.get('href') or enc.get('url')
                            break

                # Extract categories/tags
                categories = []
                if hasattr(entry, 'tags'):
                    categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]

                articles.append({
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", "").strip(),
                    "pubDate": entry.get("published", ""),
                    "categories": ", ".join(categories) if categories else None,
                    "image_url": image_url,
                    "source_id": feed["source_id"],
                    "feed_name": feed["name"]
                })

            print(f"[Ingest] Fetched {len(articles)} articles from {feed['name']}")
            return articles

    except asyncio.TimeoutError:
        print(f"[Ingest] Timeout fetching {feed['name']}")
        return []
    except Exception as e:
        print(f"[Ingest] Error fetching {feed['name']}: {e}")
        return []


async def resolve_article_urls(
    session: aiohttp.ClientSession,
    articles: List[Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], int]:
    """
    Resolve Google News redirect URLs to actual article URLs.

    For articles with Google News URLs, follows the redirect to get the
    real article URL and extracts the actual source name.

    Args:
        session: aiohttp client session
        articles: List of article dicts

    Returns:
        Tuple of (articles with resolved URLs and updated source_ids, count of resolved URLs)
    """
    google_news_articles = [
        (i, a) for i, a in enumerate(articles)
        if a.get("link") and "news.google.com" in a.get("link", "")
    ]

    if not google_news_articles:
        return articles, 0  # Return tuple to match expected return type

    print(f"[Ingest] Resolving {len(google_news_articles)} Google News URLs...")

    # Process in batches of 20 to avoid overwhelming servers
    batch_size = 20
    resolved_count = 0

    for batch_start in range(0, len(google_news_articles), batch_size):
        batch = google_news_articles[batch_start:batch_start + batch_size]
        tasks = [
            resolve_google_news_url(session, articles[idx]["link"])
            for idx, _ in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (idx, article), result in zip(batch, results):
            if isinstance(result, Exception):
                print(f"[Ingest] Failed to resolve URL for article: {result}")
                continue

            resolved_url, source_name = result

            # Update article with resolved URL
            if resolved_url and resolved_url != article["link"]:
                articles[idx]["link"] = resolved_url
                resolved_count += 1

            # Update source_id if we got a better one from the resolved URL
            if source_name:
                articles[idx]["source_id"] = source_name

    print(f"[Ingest] Resolved {resolved_count} Google News URLs to actual sources")
    return articles, resolved_count


async def fetch_all_feeds(feeds: List[Dict[str, str]]) -> tuple[List[Dict[str, Any]], int]:
    """
    Fetch all RSS feeds in parallel and resolve Google News URLs.

    Args:
        feeds: List of feed configs

    Returns:
        Tuple of (flattened list of all articles, count of resolved Google News URLs)
    """
    print(f"[Ingest] Fetching {len(feeds)} RSS feeds in parallel...")

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results, filtering out exceptions
        all_articles = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[Ingest] Feed {feeds[i]['name']} failed: {result}")
            elif isinstance(result, list):
                all_articles.extend(result)

        # Resolve Google News redirect URLs to get actual article URLs and sources
        all_articles, resolved_count = await resolve_article_urls(session, all_articles)

        return all_articles, resolved_count


def ingest_articles(debug: bool = False) -> Dict[str, Any]:
    """
    Main ingestion job function.

    Fetches all RSS feeds, deduplicates against existing records,
    and creates new records in Airtable.

    Args:
        debug: If True, only fetch from DEBUG_FEEDS (single feed for testing)

    Returns:
        Results dict with counts and timing
    """
    print(f"[Ingest] Starting ingestion job at {datetime.utcnow().isoformat()}")
    print(f"[Ingest] Debug mode: {debug}")
    started_at = datetime.now(timezone.utc)

    results = {
        "started_at": started_at.isoformat(),
        "feeds_count": 0,
        "articles_found": 0,
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
        table = api.table(AIRTABLE_BASE_ID, ARTICLES_TABLE)

        # Select feeds based on debug mode
        feeds = get_feeds(debug=debug)
        results["feeds_count"] = len(feeds)
        print(f"[Ingest] Using {len(feeds)} feeds")

        # Fetch all articles from RSS feeds (includes Google News URL resolution)
        articles, google_news_resolved = asyncio.run(fetch_all_feeds(feeds))
        results["articles_found"] = len(articles)
        results["google_news_resolved"] = google_news_resolved
        print(f"[Ingest] Found {len(articles)} total articles")

        if not articles:
            print("[Ingest] No articles found, exiting")
            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            return results

        # Get existing pivot_Ids from Airtable for deduplication
        # Note: Articles table uses "pivot_Id" (with underscore) as the key
        print("[Ingest] Fetching existing pivot_Ids for deduplication...")
        try:
            existing_records = table.all(fields=["pivot_Id"])
            existing_pivot_ids = {
                r["fields"].get("pivot_Id")
                for r in existing_records
                if r["fields"].get("pivot_Id")
            }
            print(f"[Ingest] Found {len(existing_pivot_ids)} existing records")
        except Exception as e:
            print(f"[Ingest] Warning: Could not fetch existing records: {e}")
            existing_pivot_ids = set()

        # Process and create new records
        for article in articles:
            # Skip if no URL and no title
            if not article["link"] and not article["title"]:
                results["articles_skipped_invalid"] += 1
                continue

            # Generate pivotId
            pivot_id = generate_pivot_id(article["link"], article["title"])
            if not pivot_id:
                results["articles_skipped_invalid"] += 1
                continue

            # Check for duplicates
            if pivot_id in existing_pivot_ids:
                results["articles_skipped_duplicate"] += 1
                continue

            # Prepare Airtable record
            # Fields based on Articles table schema (matching n8n Ingestion Engine)
            # Note: We don't have markdown since we're RSS-only (no Firecrawl)
            record = {
                "pivot_Id": pivot_id,  # Primary deduplication key
                "original_url": article["link"],  # Source URL
                "source_id": article["source_id"],  # Publication name
                "date_ingested": datetime.now(timezone.utc).isoformat(),  # When we ingested
                "needs_ai": True,  # Flag for AI Scoring job to pick up
            }

            # Add optional fields if present
            if article["pubDate"]:
                record["date_published"] = article["pubDate"]

            # Note: We don't have markdown content since we're RSS-only
            # The n8n workflow uses Firecrawl to get markdown, but we're
            # deliberately skipping that step for this implementation.
            # Pre-Filter (Step 1) will need to work with minimal data.

            # Remove None values (Airtable doesn't like them)
            record = {k: v for k, v in record.items() if v is not None}

            try:
                table.create(record)
                existing_pivot_ids.add(pivot_id)  # Prevent duplicates within batch
                results["articles_ingested"] += 1
            except Exception as e:
                error_msg = f"Error creating record for {pivot_id}: {str(e)}"
                print(f"[Ingest] {error_msg}")
                results["errors"].append(error_msg)

        print(f"[Ingest] Ingestion complete:")
        print(f"  - Feeds fetched: {results['feeds_count']}")
        print(f"  - Articles found: {results['articles_found']}")
        print(f"  - Google News URLs resolved: {results['google_news_resolved']}")
        print(f"  - Articles ingested: {results['articles_ingested']}")
        print(f"  - Duplicates skipped: {results['articles_skipped_duplicate']}")
        print(f"  - Invalid skipped: {results['articles_skipped_invalid']}")
        print(f"  - Errors: {len(results['errors'])}")

        # AUTOMATIC CHAINING: Trigger AI Scoring if we ingested any articles
        if results["articles_ingested"] > 0:
            print(f"[Ingest] Chaining AI Scoring job for {results['articles_ingested']} new articles...")
            try:
                from jobs.ai_scoring import run_ai_scoring

                redis_conn = Redis.from_url(REDIS_URL)
                queue = Queue('default', connection=redis_conn)

                # Enqueue AI Scoring with batch size matching ingested count
                ai_job = queue.enqueue(
                    run_ai_scoring,
                    batch_size=min(results["articles_ingested"], 100),  # Cap at 100 per run
                    job_timeout='60m'  # AI scoring takes longer
                )

                results["ai_scoring_job_id"] = ai_job.id
                print(f"[Ingest] ✓ AI Scoring job enqueued: {ai_job.id}")

            except Exception as e:
                error_msg = f"Failed to chain AI Scoring job: {str(e)}"
                print(f"[Ingest] {error_msg}")
                results["errors"].append(error_msg)
        else:
            print("[Ingest] No new articles ingested, skipping AI Scoring")

    except Exception as e:
        error_msg = f"Ingestion job failed: {str(e)}"
        print(f"[Ingest] {error_msg}")
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    # Add 'processed' key for UI compatibility (UI looks for processed || total_written)
    results["processed"] = results["articles_ingested"]
    return results


# Job configuration for RQ scheduler (if we want to schedule this)
JOB_CONFIG = {
    "func": ingest_articles,
    "trigger": "cron",
    "hour": 20,  # 8 PM UTC = 3 PM EST
    "minute": 0,
    "id": "step0_ingest",
    "replace_existing": True
}
