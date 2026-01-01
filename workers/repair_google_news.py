#!/usr/bin/env python3
"""
Repair Script: Fix Google News URLs in Airtable

Fixes records that have "Google News" as source_name with unresolved
redirect URLs (news.google.com/...). Uses aggressive rate limiting
to avoid getting blocked by Google.

SLOW AND CAREFUL:
- 5 second delay between each URL decode
- 60 second delay between batches of 10
- Processes records one at a time with immediate Airtable updates
- Exponential backoff on rate limit (429) errors

Usage:
    python workers/repair_google_news.py
"""

import os
import sys
import time
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Add workers directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Google News URL decoding - calls Google's batchexecute API
from googlenewsdecoder import gnewsdecoder

# Load environment variables
load_dotenv('.env.local')

# EST timezone
EST = ZoneInfo("America/New_York")

# Airtable config
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
AI_EDITOR_BASE_ID = os.environ.get('AI_EDITOR_BASE_ID', 'appglKSJZxmA9iHpl')
ARTICLES_TABLE_ID = 'tblMfRgSNSyoRIhx1'  # Articles All Ingested

import requests

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
    "theguardian.com": "The Guardian",
    "technologyreview.com": "MIT Tech Review",
    "news.mit.edu": "MIT News",
    "sciencedaily.com": "Science Daily",
    "barrons.com": "Barrons",
}


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


def decode_google_news_url(url: str, max_retries: int = 3) -> tuple:
    """
    Decode a Google News URL to the actual article URL.

    Uses gnewsdecoder with longer interval and exponential backoff on 429 errors.

    Returns:
        Tuple of (decoded_url, source_name, success)
    """
    if not url or "news.google.com" not in url:
        return url, None, False

    for attempt in range(max_retries):
        try:
            # Use longer interval to be gentler on Google's API
            result = gnewsdecoder(url, interval=2.0)

            if result.get("status") and result.get("decoded_url"):
                decoded_url = result["decoded_url"]
                source_name = extract_source_from_url(decoded_url)
                return decoded_url, source_name, True
            else:
                error_msg = result.get("message", "Unknown error")
                # Check for rate limit errors
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    wait_time = 30 * (2 ** attempt)  # 30s, 60s, 120s
                    print(f"    [RATE LIMIT] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                print(f"    [FAILED] {error_msg}")
                return url, None, False

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Too Many Requests" in error_str:
                wait_time = 30 * (2 ** attempt)
                print(f"    [RATE LIMIT] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            print(f"    [ERROR] {e}")
            return url, None, False

    print(f"    [FAILED] Max retries exceeded")
    return url, None, False


def fetch_broken_records():
    """Fetch all records with source_name = 'Google News' that have unresolved URLs."""
    print("\n[Repair] Fetching broken records from Airtable...")

    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }

    broken_records = []
    offset = None

    while True:
        url = f'https://api.airtable.com/v0/{AI_EDITOR_BASE_ID}/{ARTICLES_TABLE_ID}'
        params = {
            'filterByFormula': "AND({source_name} = 'Google News', FIND('news.google.com', {original_url}) > 0)",
            'pageSize': 100
        }
        if offset:
            params['offset'] = offset

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"[Repair] Error fetching records: {response.status_code}")
            print(response.text)
            break

        data = response.json()

        for record in data.get('records', []):
            broken_records.append({
                'id': record['id'],
                'original_url': record['fields'].get('original_url', ''),
                'headline': record['fields'].get('headline', 'No headline')[:50]
            })

        offset = data.get('offset')
        if not offset:
            break

    print(f"[Repair] Found {len(broken_records)} records needing repair")
    return broken_records


def update_airtable_record(record_id: str, new_url: str, source_name: str):
    """Update a single Airtable record with the decoded URL and source."""
    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }

    url = f'https://api.airtable.com/v0/{AI_EDITOR_BASE_ID}/{ARTICLES_TABLE_ID}/{record_id}'

    data = {
        'fields': {
            'original_url': new_url,
            'source_name': source_name
        }
    }

    response = requests.patch(url, headers=headers, json=data)
    return response.status_code == 200


def repair_google_news_job(limit: int = 50):
    """
    RQ-compatible job function to repair Google News URLs.

    Args:
        limit: Max records to process per run (default 50 to avoid timeouts)

    Returns:
        Dict with repair statistics
    """
    print("=" * 60)
    print("Google News URL Repair Job")
    print(f"Started at {datetime.now(EST).isoformat()}")
    print("=" * 60)

    # Fetch broken records
    broken_records = fetch_broken_records()

    if not broken_records:
        print("\n[Repair] No broken records found! All URLs are already resolved.")
        return {"status": "complete", "fixed": 0, "failed": 0, "remaining": 0}

    # Limit the number of records to process
    records_to_process = broken_records[:limit]
    remaining = len(broken_records) - len(records_to_process)

    # Stats
    fixed_count = 0
    failed_count = 0
    fixed_sources = []

    print(f"\n[Repair] Processing {len(records_to_process)} of {len(broken_records)} records...")
    print("[Repair] Using 5-second delay between URLs to avoid rate limiting")
    print("[Repair] Initial 30-second wait to let rate limits reset...\n")
    time.sleep(30)  # Shorter initial wait for RQ job

    for i, record in enumerate(records_to_process, 1):
        print(f"[{i}/{len(records_to_process)}] {record['headline']}...")

        # Decode the URL (with built-in interval and retry logic)
        decoded_url, source_name, success = decode_google_news_url(record['original_url'])

        if success and source_name:
            # Update Airtable immediately
            if update_airtable_record(record['id'], decoded_url, source_name):
                print(f"    [OK] -> {source_name}")
                fixed_count += 1
                fixed_sources.append(source_name)
            else:
                print(f"    [ERROR] Failed to update Airtable")
                failed_count += 1
        else:
            failed_count += 1

        # CRITICAL: 5-second delay between each URL to avoid rate limiting
        if i < len(records_to_process):
            time.sleep(5)

        # Extra 30-second pause every 10 records
        if i % 10 == 0 and i < len(records_to_process):
            print(f"\n[Repair] Batch pause (30 seconds) to avoid rate limiting...")
            time.sleep(30)
            print()

    print("\n" + "=" * 60)
    print(f"REPAIR JOB COMPLETE")
    print(f"  - Fixed: {fixed_count}")
    print(f"  - Failed: {failed_count}")
    print(f"  - Remaining: {remaining}")
    print("=" * 60)

    return {
        "status": "complete" if remaining == 0 else "partial",
        "fixed": fixed_count,
        "failed": failed_count,
        "remaining": remaining,
        "sources_fixed": list(set(fixed_sources))
    }


def main():
    """CLI entry point - runs full repair"""
    result = repair_google_news_job(limit=500)  # Process all when run directly
    print(f"\nResult: {result}")


if __name__ == '__main__':
    main()
