"""
Step 0.6: Browserbase Retry for Paywalled Sites

Runs AFTER Firecrawl extraction in AI Scoring (Step 0.5).
Finds articles from problematic sources with missing/truncated content.
Re-extracts using Browserbase with authenticated sessions.

Pipeline Position:
    Step 0:   Ingest (Google News RSS)
    Step 0a:  Direct Feed Ingest
    Step 0.5: AI Scoring (Firecrawl extracts articles)
    Step 0.6: BROWSERBASE RETRY <-- THIS JOB
    Step 0b:  Newsletter Extraction
    Step 1:   Pre-Filter (5 slots with Gemini)

Target Sources:
    - WSJ (Wall Street Journal)
    - Bloomberg
    - New York Times (NYT)
    - MSN

Airtable Table:
    Newsletter Selects (tblKhICCdWnyuqgry) in AI Editor 2.0 base

Environment Variables:
    BROWSERBASE_API_KEY: Required for scraping
    BROWSERBASE_PROJECT_ID: Optional project ID
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List

EST = ZoneInfo("America/New_York")

# Sites that need Browserbase retry (case-insensitive matching)
BROWSERBASE_SOURCES = [
    "WSJ",
    "Wall Street Journal",
    "Bloomberg",
    "New York Times",
    "NYT",
    "MSN",
]

# Minimum content length - below this is considered failed/truncated
MIN_CONTENT_LENGTH = 500


def browserbase_retry() -> Dict:
    """
    Query Newsletter Selects for failed extractions and retry with Browserbase.

    Finds articles where:
    - source_name matches a paywalled source (WSJ, Bloomberg, NYT, MSN)
    - raw field is empty OR has less than MIN_CONTENT_LENGTH characters
    - Was processed today (date_ai_process)

    Returns:
        Dict with keys:
            - status: "completed" | "skipped" | "no_records"
            - retried: int (total articles attempted)
            - success: int (successful extractions)
            - failed: int (failed extractions)
            - details: List[Dict] (per-article results)
    """
    job_start = datetime.now(EST)
    print(f"[Browserbase Retry] Starting at {job_start.strftime('%I:%M %p ET')}")

    # Check if Browserbase is configured
    if not os.environ.get("BROWSERBASE_API_KEY"):
        print("[Browserbase Retry] BROWSERBASE_API_KEY not set, skipping")
        return {
            "status": "skipped",
            "reason": "BROWSERBASE_API_KEY not configured",
            "retried": 0,
            "success": 0,
            "failed": 0
        }

    # Import dependencies (lazy load to avoid import errors)
    try:
        from utils.browserbase_scraper import BrowserbaseNewsScraper
        from utils.airtable import AirtableClient
    except ImportError as e:
        print(f"[Browserbase Retry] Import error: {e}")
        return {
            "status": "skipped",
            "reason": f"Import error: {e}",
            "retried": 0,
            "success": 0,
            "failed": 0
        }

    # Initialize Airtable client for Newsletter Selects
    airtable = AirtableClient()

    # Build filter formula for articles needing retry:
    # - source_name in BROWSERBASE_SOURCES
    # - raw is empty OR length < MIN_CONTENT_LENGTH
    # - processed today (date_ai_process)
    source_conditions = ", ".join([f"{{source_name}}='{s}'" for s in BROWSERBASE_SOURCES])
    formula = (
        f"AND("
        f"OR({source_conditions}), "
        f"OR({{raw}}='', LEN({{raw}})<{MIN_CONTENT_LENGTH}), "
        f"IS_SAME({{date_ai_process}}, TODAY(), 'day')"
        f")"
    )

    print(f"[Browserbase Retry] Query formula: {formula[:100]}...")

    # Query Newsletter Selects table
    try:
        records = airtable.get_newsletter_selects_by_formula(formula)
        print(f"[Browserbase Retry] Found {len(records)} articles needing retry")
    except Exception as e:
        print(f"[Browserbase Retry] Airtable query failed: {e}")
        return {
            "status": "failed",
            "reason": f"Airtable query failed: {e}",
            "retried": 0,
            "success": 0,
            "failed": 0
        }

    if not records:
        duration = (datetime.now(EST) - job_start).total_seconds()
        print(f"[Browserbase Retry] No articles need retry, completed in {duration:.1f}s")
        return {
            "status": "no_records",
            "retried": 0,
            "success": 0,
            "failed": 0,
            "duration_seconds": duration
        }

    # Initialize Browserbase scraper
    try:
        scraper = BrowserbaseNewsScraper()
    except Exception as e:
        print(f"[Browserbase Retry] Scraper init failed: {e}")
        return {
            "status": "failed",
            "reason": f"Scraper init failed: {e}",
            "retried": 0,
            "success": 0,
            "failed": 0
        }

    # Track results
    results = {
        "status": "completed",
        "retried": 0,
        "success": 0,
        "failed": 0,
        "details": []
    }

    # Process each article
    for record in records:
        fields = record.get("fields", {})
        record_id = record.get("id")
        url = fields.get("core_url")
        source = fields.get("source_name", "Unknown")
        pivot_id = fields.get("pivotId", "")

        if not url:
            print(f"[Browserbase Retry] Skipping record {record_id}: no core_url")
            continue

        print(f"[Browserbase Retry] Extracting: {source} - {url[:60]}...")

        try:
            # Scrape with Browserbase
            scrape_result = scraper.scrape(url)

            if scrape_result.get("success") and scrape_result.get("content_length", 0) >= MIN_CONTENT_LENGTH:
                # Update Airtable with new content
                update_fields = {
                    "raw": scrape_result["content"],
                    "browserbase_extracted": True,
                    "browserbase_session": scrape_result.get("session_replay", ""),
                }

                try:
                    airtable.update_newsletter_select(record_id, update_fields)
                    results["success"] += 1
                    print(f"[Browserbase Retry] Success: {scrape_result['content_length']} chars extracted")
                except Exception as e:
                    print(f"[Browserbase Retry] Airtable update failed: {e}")
                    results["failed"] += 1
            else:
                results["failed"] += 1
                error_msg = scrape_result.get("error", "Content too short or empty")
                print(f"[Browserbase Retry] Failed: {error_msg}")

            # Track details
            results["details"].append({
                "record_id": record_id,
                "pivot_id": pivot_id,
                "url": url,
                "source": source,
                "success": scrape_result.get("success", False) and scrape_result.get("content_length", 0) >= MIN_CONTENT_LENGTH,
                "content_length": scrape_result.get("content_length", 0),
                "session_replay": scrape_result.get("session_replay"),
                "error": scrape_result.get("error")
            })

        except Exception as e:
            results["failed"] += 1
            print(f"[Browserbase Retry] Exception: {e}")
            results["details"].append({
                "record_id": record_id,
                "pivot_id": pivot_id,
                "url": url,
                "source": source,
                "success": False,
                "error": str(e)
            })

        results["retried"] += 1

    # Calculate duration
    duration = (datetime.now(EST) - job_start).total_seconds()
    results["duration_seconds"] = duration

    print(f"[Browserbase Retry] Complete: {results['success']}/{results['retried']} succeeded in {duration:.1f}s")
    return results


# Export for individual slot testing (matches prefilter.py pattern)
def browserbase_retry_job() -> Dict:
    """Wrapper for RQ job queue compatibility."""
    return browserbase_retry()


# Main entry point for direct execution
if __name__ == "__main__":
    import json
    result = browserbase_retry()
    print(json.dumps(result, indent=2, default=str))
