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
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from pyairtable import Api
from redis import Redis
from rq import Queue

# Import local utilities
from utils.pivot_id import generate_pivot_id
from config.freshrss_client import FreshRSSClient, get_articles


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
    limit: int = 100,
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
    print(f"[Ingest Sandbox] Starting at {datetime.utcnow().isoformat()}")
    print(f"[Ingest Sandbox] Debug mode: {debug}")
    print(f"[Ingest Sandbox] Target base: {AIRTABLE_AI_EDITOR_BASE_ID}")
    started_at = datetime.now(timezone.utc)

    results = {
        "started_at": started_at.isoformat(),
        "source": "FreshRSS",
        "articles_fetched": 0,
        "articles_ingested": 0,
        "articles_skipped_duplicate": 0,
        "articles_skipped_invalid": 0,
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
            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            return results

        if not articles:
            print("[Ingest Sandbox] No articles found, exiting")
            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            return results

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
                "date_ingested": datetime.now(timezone.utc).isoformat(),  # When we ingested
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

                # Enqueue AI Scoring with batch size matching ingested count
                ai_job = queue.enqueue(
                    run_ai_scoring_sandbox,
                    batch_size=min(results["articles_ingested"], 50),  # Cap at 50 per run
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

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
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
