#!/usr/bin/env python3
"""
72-Hour FreshRSS Backfill Script

Fetches articles from the past 72 hours and appends to Airtable
with proper deduplication (using pivot_id).

CRITICAL: Uses Google News URL resolution from ingest_sandbox.py
to decode news.google.com redirect URLs to actual article URLs.

NO SCORING - just raw article ingestion.

Usage:
    python workers/backfill_72h.py
"""

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

# EST timezone for consistency with main ingest
EST = ZoneInfo("America/New_York")
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Add workers directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.freshrss_client import FreshRSSClient
from utils.pivot_id import generate_pivot_id, normalize_url

# Google News URL decoding - calls Google's batchexecute API
from googlenewsdecoder import gnewsdecoder

# Load environment variables
load_dotenv('.env.local')

# Airtable config
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
AI_EDITOR_BASE_ID = os.environ.get('AI_EDITOR_BASE_ID', 'appglKSJZxmA9iHpl')
ARTICLES_TABLE_ID = 'tblMfRgSNSyoRIhx1'  # Articles All Ingested

import requests

# Thread pool for blocking gnewsdecoder calls (it makes HTTP requests)
_google_news_executor = ThreadPoolExecutor(max_workers=10)

# Source name mappings from domain to display name (from ingest_sandbox.py)
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
    "theguardian.com": "The Guardian",
    "technologyreview.com": "MIT Tech Review",
    "news.mit.edu": "MIT News",
    "sciencedaily.com": "Science Daily",
}

# Domains to skip during ingestion
BLOCKED_DOMAINS = [
    "yahoo.com",
    "finance.yahoo.com",
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


def extract_source_from_url(url: str):
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

        # Try matching root domain (e.g., "news.yahoo.com" -> "yahoo.com")
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


async def resolve_google_news_url(url: str):
    """
    Resolve a Google News URL to the actual article URL.

    Uses the googlenewsdecoder package which calls Google's batchexecute API.
    """
    # Only process Google News URLs
    if not url or "news.google.com" not in url:
        return url, None

    try:
        # Run blocking gnewsdecoder in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _google_news_executor,
            lambda: gnewsdecoder(url, interval=0.3)
        )

        if result.get("status") and result.get("decoded_url"):
            decoded_url = result["decoded_url"]
            source_name = extract_source_from_url(decoded_url)
            return decoded_url, source_name
        else:
            return url, "Google News"

    except Exception as e:
        print(f"[Backfill] Error decoding Google News URL: {e}")
        return url, "Google News"


async def resolve_article_urls(articles):
    """
    Resolve Google News redirect URLs to actual article URLs.
    Processes in batches with delays to avoid rate limiting.
    """
    google_news_articles = [
        (i, a) for i, a in enumerate(articles)
        if a.get("url") and "news.google.com" in a.get("url", "")
    ]

    if not google_news_articles:
        print("[Backfill] No Google News URLs to resolve")
        return articles, 0

    print(f"[Backfill] Resolving {len(google_news_articles)} Google News URLs...")

    # Process in batches of 10 with delays
    batch_size = 10
    resolved_count = 0

    for batch_start in range(0, len(google_news_articles), batch_size):
        batch = google_news_articles[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1
        total_batches = (len(google_news_articles) + batch_size - 1) // batch_size
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} URLs)...")

        tasks = [
            resolve_google_news_url(articles[idx]["url"])
            for idx, _ in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (idx, article), result in zip(batch, results):
            if isinstance(result, Exception):
                print(f"  Failed to resolve: {result}")
                continue

            resolved_url, source_name = result

            # Update article with resolved URL
            if resolved_url and resolved_url != article["url"]:
                articles[idx]["url"] = resolved_url
                resolved_count += 1

            # Update source_id if we got a better one from the resolved URL
            if source_name:
                articles[idx]["source_id"] = source_name

        # Delay between batches to avoid rate limiting
        if batch_start + batch_size < len(google_news_articles):
            await asyncio.sleep(1)

    print(f"[Backfill] Resolved {resolved_count} Google News URLs to actual sources")
    return articles, resolved_count


def fetch_existing_pivot_ids():
    """Fetch all existing pivot_ids from Airtable for deduplication."""
    print("\n[Airtable] Fetching existing pivot_ids for deduplication...")

    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }

    all_pivot_ids = set()
    offset = None

    while True:
        url = f'https://api.airtable.com/v0/{AI_EDITOR_BASE_ID}/{ARTICLES_TABLE_ID}'
        params = {'fields[]': 'pivot_id', 'pageSize': 100}
        if offset:
            params['offset'] = offset

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"[Airtable] Error fetching records: {response.status_code}")
            print(response.text)
            break

        data = response.json()

        for record in data.get('records', []):
            pivot_id = record.get('fields', {}).get('pivot_id')
            if pivot_id:
                all_pivot_ids.add(pivot_id)

        offset = data.get('offset')
        if not offset:
            break

    print(f"[Airtable] Found {len(all_pivot_ids)} existing pivot_ids")
    return all_pivot_ids


def append_to_airtable(articles):
    """Append articles to Airtable."""
    print(f"\n[Airtable] Appending {len(articles)} new articles...")

    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }

    url = f'https://api.airtable.com/v0/{AI_EDITOR_BASE_ID}/{ARTICLES_TABLE_ID}'

    # Airtable allows max 10 records per request
    batch_size = 10
    total_created = 0

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]

        records = []
        for article in batch:
            fields = {
                'pivot_id': article['pivot_id'],
                'original_url': article['url'],
                'headline': article['title'],
                'source_name': article.get('source_id', 'Unknown'),
                'date_ingested': datetime.now(EST).isoformat(),  # EST for consistency
                'needs_ai': True,  # Flag for AI Scoring job to pick up
                'fit_status': 'pending',  # Single select status
            }

            # Add date_og_published if available
            if article.get('published'):
                fields['date_og_published'] = article['published']

            records.append({'fields': fields})

        response = requests.post(url, headers=headers, json={'records': records})

        if response.status_code == 200:
            created = len(response.json().get('records', []))
            total_created += created
            print(f"  Batch {i // batch_size + 1}: Created {created} records")
        else:
            print(f"  Batch {i // batch_size + 1}: Error - {response.status_code}")
            print(f"  {response.text[:200]}")

    return total_created


def main():
    print("=" * 60)
    print("5-Day FreshRSS Backfill (with Google News URL Resolution)")
    print("=" * 60)

    # Step 1: Fetch articles from FreshRSS (5 days / 120 hours)
    print("\n[FreshRSS] Fetching articles from past 5 days...")
    client = FreshRSSClient()

    # Trigger refresh first
    client.trigger_refresh()

    # Fetch with 5-day window (120 hours) for extended backfill
    raw_articles = client.get_articles(limit=1000, since_hours=120, auto_refresh=False)
    print(f"[FreshRSS] Fetched {len(raw_articles)} articles")

    if not raw_articles:
        print("[FreshRSS] No articles found!")
        return

    # Step 2: Resolve Google News URLs to actual article URLs
    print("\n[Processing] Resolving Google News URLs...")
    raw_articles, resolved_count = asyncio.run(resolve_article_urls(raw_articles))
    print(f"[Processing] Resolved {resolved_count} Google News URLs")

    # Step 3: Filter out blocked domains
    articles_filtered = [
        a for a in raw_articles
        if not is_blocked_domain(a.get('url', ''))
    ]
    blocked_count = len(raw_articles) - len(articles_filtered)
    if blocked_count > 0:
        print(f"[Processing] Filtered out {blocked_count} blocked domain articles")

    # Step 3.5: CRITICAL - Filter by PUBLISHED date (not just crawl time!)
    # Extended to 5 days (120 hours) for backfill
    # This prevents old articles that were recently crawled from being imported
    publish_cutoff = datetime.now(timezone.utc) - timedelta(days=5)
    articles_recent = []
    old_article_count = 0
    for a in articles_filtered:
        pub_dt = a.get('published_dt')
        if pub_dt:
            # Make sure we're comparing timezone-aware datetimes
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            if pub_dt >= publish_cutoff:
                articles_recent.append(a)
            else:
                old_article_count += 1
        else:
            # Skip articles without a published date - we can't verify recency
            old_article_count += 1

    if old_article_count > 0:
        print(f"[Processing] Filtered out {old_article_count} articles with old/missing published dates")
        print(f"[Processing] Cutoff: {publish_cutoff.isoformat()} (5 days ago)")

    articles_filtered = articles_recent
    print(f"[Processing] {len(articles_filtered)} articles have recent published dates")

    # Step 4: Generate pivot_ids (AFTER URL resolution so we hash the resolved URL)
    print("\n[Processing] Generating pivot_ids...")
    for article in articles_filtered:
        url = article.get('url', '')
        article['pivot_id'] = generate_pivot_id(url=url)
        article['normalized_url'] = normalize_url(url)

    # Remove articles without pivot_id
    articles_with_id = [a for a in articles_filtered if a.get('pivot_id')]
    print(f"[Processing] {len(articles_with_id)} articles have valid pivot_ids")

    # Step 5: Fetch existing pivot_ids from Airtable
    existing_pivot_ids = fetch_existing_pivot_ids()

    # Step 6: Filter to only new articles
    new_articles = [
        a for a in articles_with_id
        if a.get('pivot_id') not in existing_pivot_ids
    ]

    duplicates = len(articles_with_id) - len(new_articles)
    print(f"\n[Deduplication] {duplicates} duplicates filtered out")
    print(f"[Deduplication] {len(new_articles)} new articles to append")

    if not new_articles:
        print("\n[Done] No new articles to append!")
        return

    # Step 7: Show sample of what we're adding
    print("\n[Preview] Sample of new articles:")
    for article in new_articles[:10]:
        source = article.get('source_id', 'Unknown')
        url_domain = urlparse(article.get('url', '')).netloc[:25]
        print(f"  - {source[:15]:15} | {url_domain:25} | {article['title'][:40]}")
    if len(new_articles) > 10:
        print(f"  ... and {len(new_articles) - 10} more")

    # Step 8: Append to Airtable
    created = append_to_airtable(new_articles)

    print("\n" + "=" * 60)
    print(f"COMPLETE: Created {created} new records in Airtable")
    print(f"  - Google News URLs resolved: {resolved_count}")
    print(f"  - Blocked domains filtered: {blocked_count}")
    print(f"  - Old/missing publish dates filtered: {old_article_count}")
    print(f"  - Duplicates filtered: {duplicates}")
    print("=" * 60)


if __name__ == '__main__':
    main()
