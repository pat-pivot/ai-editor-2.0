"""
Newsletter Link Extraction Job (Standalone)

Extracts external news links from AI newsletters arriving via Kill The Newsletter
(FreshRSS feed/17) and creates records in the Articles table with provenance tracking.

This is a SEPARATE job from ingestion - triggered independently via the dashboard.

Documentation: docs/ai-ingestion-engine-step-0/Newsletter-Logic-Extraction-1-2-26.md
Created: January 2, 2026
"""

import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

# EST timezone for all timestamps
EST = ZoneInfo("America/New_York")


def build_gmail_search_url(subject: str, date_str: str) -> str:
    """
    Build a Gmail search URL to find the newsletter email.

    Args:
        subject: Email subject line
        date_str: Date string (ISO format or YYYY-MM-DD)

    Returns:
        Gmail search URL that will find the email
    """
    try:
        # Parse the date
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")

        # Format date for Gmail search: YYYY/MM/DD
        date_formatted = dt.strftime("%Y/%m/%d")

        # Build search query: subject:"exact subject" after:date before:date+1
        # Using exact subject match with quotes
        next_day = dt + timedelta(days=1)
        next_day_formatted = next_day.strftime("%Y/%m/%d")

        # Gmail search query
        search_query = f'subject:"{subject}" after:{date_formatted} before:{next_day_formatted}'

        # Encode for URL
        encoded_query = quote(search_query, safe='')

        return f"https://mail.google.com/mail/u/0/#search/{encoded_query}"
    except Exception as e:
        # Fallback to simple subject search
        encoded_subject = quote(f'subject:"{subject}"', safe='')
        return f"https://mail.google.com/mail/u/0/#search/{encoded_subject}"


def format_date_friendly(date_str: str) -> str:
    """
    Convert ISO date string to friendly format: "January 2, 2026 at 7:50am ET"

    Args:
        date_str: ISO format date string (e.g., "2026-01-02T07:50:00-05:00")

    Returns:
        Friendly formatted date string
    """
    try:
        # Parse the date string
        if isinstance(date_str, str):
            # Handle ISO format with timezone
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                # Just a date, no time
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                dt = dt.replace(tzinfo=EST)
        else:
            dt = date_str

        # Convert to EST if not already
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=EST)
        else:
            dt = dt.astimezone(EST)

        # Format: "January 2, 2026 at 7:50am ET"
        # %I = hour (12-hour), %M = minute, %p = AM/PM
        time_part = dt.strftime("%I:%M%p").lower().lstrip("0")
        date_part = dt.strftime("%B %-d, %Y")  # %-d for non-zero-padded day
        return f"{date_part} at {time_part} ET"
    except Exception as e:
        # Fallback to original string if parsing fails
        return date_str

from pyairtable import Api
from anthropic import Anthropic

# Google News URL decoding
from googlenewsdecoder import gnewsdecoder

# Import local utilities
from utils.pivot_id import generate_pivot_id
from config.freshrss_client import FreshRSSClient
from config.newsletter_extraction import (
    NEWSLETTER_EXTRACTION_CONFIG,
    SKIP_NEWSLETTERS,
    get_newsletter_config,
    should_skip_newsletter,
    is_blocked_domain as is_newsletter_blocked_domain,
    is_non_news_url
)

# Thread pool for blocking gnewsdecoder calls
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

# Domains to skip (stock speculation, low-quality sources)
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

        if domain.startswith("www."):
            domain = domain[4:]

        if domain in DOMAIN_TO_SOURCE:
            return DOMAIN_TO_SOURCE[domain]

        parts = domain.split(".")
        if len(parts) >= 2:
            root_domain = ".".join(parts[-2:])
            if root_domain in DOMAIN_TO_SOURCE:
                return DOMAIN_TO_SOURCE[root_domain]

        if len(parts) >= 2:
            main_name = parts[-2]
            return main_name.capitalize()

        return None
    except Exception:
        return None


async def resolve_google_news_url(url: str, retry_count: int = 0) -> tuple[str, Optional[str]]:
    """
    Resolve a Google News URL to the actual article URL.
    """
    if not url or "news.google.com" not in url:
        return url, None

    max_retries = 3
    print(f"[GNEWS DECODE] Attempting: {url[:80]}...")

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _google_news_executor,
            lambda: gnewsdecoder(url, interval=3.0)  # 3s delay - more conservative to avoid 429
        )

        if result.get("status") and result.get("decoded_url"):
            decoded_url = result["decoded_url"]
            source_name = extract_source_from_url(decoded_url)
            print(f"[GNEWS DECODE] ✅ SUCCESS: {url[:50]}...")
            return decoded_url, source_name
        else:
            error_msg = result.get("message", "Unknown error")
            if "429" in str(error_msg) or "rate" in str(error_msg).lower():
                if retry_count < max_retries:
                    backoff = 30 * (2 ** retry_count)  # 30s, 60s, 120s (more conservative)
                    print(f"[GNEWS DECODE] ⚠️ RATE LIMITED - waiting {backoff}s before retry...")
                    await asyncio.sleep(backoff)
                    return await resolve_google_news_url(url, retry_count + 1)
            print(f"[GNEWS DECODE] ❌ FAILED: {url[:60]}...")
            return url, "Google News"

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "rate" in error_str.lower():
            if retry_count < max_retries:
                backoff = 30 * (2 ** retry_count)  # 30s, 60s, 120s (more conservative)
                print(f"[GNEWS DECODE] ⚠️ RATE LIMITED - waiting {backoff}s before retry...")
                await asyncio.sleep(backoff)
                return await resolve_google_news_url(url, retry_count + 1)
        print(f"[GNEWS DECODE] ❌ EXCEPTION: {e}")
        return url, "Google News"


def detect_newsletter_domain(content: str) -> Optional[str]:
    """Detect which newsletter sent this content by looking for known domains."""
    if not content:
        return None

    content_lower = content.lower()

    for domain in NEWSLETTER_EXTRACTION_CONFIG.keys():
        if domain in content_lower:
            return domain

    for domain in SKIP_NEWSLETTERS:
        if domain in content_lower:
            return domain

    return None


async def extract_newsletter_links(
    html_content: str,
    newsletter_config: dict,
    newsletter_date: str
) -> List[dict]:
    """Use Claude Haiku to extract news links from newsletter HTML."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print(f"[Newsletter Extract] ERROR: ANTHROPIC_API_KEY not set")
        return []

    client = Anthropic(api_key=api_key)

    newsletter_name = newsletter_config['name']
    extract_sections = newsletter_config.get('extract_sections', [])
    ignore_sections = newsletter_config.get('ignore_sections', [])
    extract_all = newsletter_config.get('extract_all', False)

    section_instructions = ""
    if extract_sections:
        section_instructions = f"ONLY extract links from these sections: {', '.join(extract_sections)}"
    elif extract_all:
        section_instructions = "Extract ALL external news links from the newsletter"
    else:
        section_instructions = "Extract external news links"

    ignore_instructions = ""
    if ignore_sections:
        ignore_instructions = f"\nIGNORE these sections completely: {', '.join(ignore_sections)}"

    content_truncated = html_content[:15000]

    prompt = f"""You are parsing HTML to find URLs that link to external news articles.

Newsletter: {newsletter_name}

CRITICAL RULE - DO NOT HALLUCINATE:
You must ONLY return URLs that LITERALLY APPEAR in the HTML content below as href attributes.
DO NOT make up URLs. DO NOT generate plausible-looking URLs.
ONLY extract actual URLs from <a href="..."> tags in the HTML.

TASK:
{section_instructions}{ignore_instructions}

Parse the HTML and find <a href="..."> tags linking to news articles.

WHAT TO INCLUDE (only if URL exists in HTML):
- Links to news sites: Reuters, Bloomberg, TechCrunch, The Verge, CNBC, WSJ, NYT, etc.
- News articles about AI, technology, business, funding, product launches
- Any link that points to a NEWS STORY - use your reasoning to identify news articles even if the section headers differ from what you expect

BACKUP REASONING:
If no explicit section headers match, use your general understanding to identify news story links:
- News stories typically report on events, announcements, product launches, funding rounds, company news, research breakthroughs, regulatory developments
- They are hosted on known news domains OR third-party publication sites (not the newsletter's own domain)
- The anchor text often reads like a headline or describes a newsworthy event

WHAT TO SKIP:
- Newsletter's own website links
- Social media (twitter.com, linkedin.com/in/)
- Unsubscribe/preferences links
- Sponsor ads
- huggingface.co, github.com repos
- Product signup pages, docs, pricing
- Job postings

RETURN FORMAT (JSON array only):
[
  {{"url": "EXACT_URL_FROM_HTML", "headline": "anchor text or null", "source_hint": "publication name or null"}}
]

IMPORTANT: Every URL you return MUST be copy-pasted from an href attribute in the HTML below.
If you cannot find any valid news URLs in the HTML, return: []

HTML CONTENT:
{content_truncated}

Return ONLY the JSON array, nothing else."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        if response_text.startswith("```"):
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1)

        links = json.loads(response_text)

        if not isinstance(links, list):
            print(f"[Newsletter Extract] Unexpected response format: {type(links)}")
            return []

        filtered_links = []
        for link in links:
            url = link.get('url', '')
            if not url:
                continue

            if is_newsletter_blocked_domain(url):
                continue

            if is_non_news_url(url):
                continue

            filtered_links.append(link)

        print(f"[Newsletter Extract] Extracted {len(filtered_links)} links from {newsletter_name} (filtered from {len(links)} raw)")
        return filtered_links

    except json.JSONDecodeError as e:
        print(f"[Newsletter Extract] JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"[Newsletter Extract] Error calling Claude Haiku: {e}")
        return []


async def process_newsletter_article(
    article: dict,
    existing_pivot_ids: set
) -> List[dict]:
    """Process a newsletter article to extract and create records for external links."""
    records_to_create = []

    summary = article.get('summary', '')
    if not summary:
        print(f"[Newsletter Extract] No content in newsletter article, skipping")
        return records_to_create

    newsletter_domain = detect_newsletter_domain(summary)

    if not newsletter_domain:
        print(f"[Newsletter Extract] Could not detect newsletter domain, skipping")
        return records_to_create

    if should_skip_newsletter(newsletter_domain):
        print(f"[Newsletter Extract] Skipping newsletter (in skip list): {newsletter_domain}")
        return records_to_create

    config = get_newsletter_config(newsletter_domain)
    if not config:
        print(f"[Newsletter Extract] No extraction config for {newsletter_domain}, skipping")
        return records_to_create

    newsletter_name = config['name']
    newsletter_date = article.get('published', datetime.now(EST).strftime('%Y-%m-%d'))
    newsletter_subject = article.get('title', '')  # Email subject line for Gmail search

    print(f"[Newsletter Extract] Processing {newsletter_name} ({newsletter_domain})")

    extracted_links = await extract_newsletter_links(
        html_content=summary,
        newsletter_config=config,
        newsletter_date=newsletter_date
    )

    if not extracted_links:
        print(f"[Newsletter Extract] No links extracted from {newsletter_name}")
        return records_to_create

    for link_data in extracted_links:
        url = link_data.get('url', '')
        headline = link_data.get('headline', '')
        source_hint = link_data.get('source_hint', '')

        if not url:
            continue

        # Resolve Google News URLs if present
        if 'news.google.com' in url:
            try:
                resolved_url, resolved_source = await resolve_google_news_url(url)
                if resolved_url != url:
                    url = resolved_url
                if resolved_source and resolved_source != 'Google News':
                    source_hint = resolved_source
            except Exception as e:
                print(f"[Newsletter Extract] Failed to resolve Google News URL: {e}")

        if is_blocked_domain(url):
            continue

        if not source_hint or source_hint == 'Google News':
            source_hint = extract_source_from_url(url) or 'Unknown'

        pivot_id = generate_pivot_id(url, headline)
        if not pivot_id:
            continue

        if pivot_id in existing_pivot_ids:
            continue

        # Format date in friendly format: "January 2, 2026 at 7:50am ET"
        date_str = newsletter_date if isinstance(newsletter_date, str) else newsletter_date.strftime('%Y-%m-%d')
        friendly_date = format_date_friendly(date_str)

        # Build notes with friendly date and Gmail search link
        notes = f"Link derived from {newsletter_name} on {friendly_date}"
        if newsletter_subject:
            gmail_url = build_gmail_search_url(newsletter_subject, date_str)
            notes += f"\nFind in Gmail: {gmail_url}"

        record = {
            "pivot_id": pivot_id,
            "original_url": url,
            "source_name": source_hint,
            "headline": headline or f"Article from {source_hint}",
            "date_ingested": datetime.now(EST).isoformat(),
            "needs_ai": True,
            "fit_status": "pending",
            "notes": notes,
        }

        if article.get('published'):
            record["date_og_published"] = article["published"]

        records_to_create.append(record)
        existing_pivot_ids.add(pivot_id)

    print(f"[Newsletter Extract] Created {len(records_to_create)} records from {newsletter_name}")
    return records_to_create


# =============================================================================
# AIRTABLE CONFIGURATION
# =============================================================================

AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_AI_EDITOR_BASE_ID = os.environ.get(
    "AIRTABLE_AI_EDITOR_BASE_ID",
    "appglKSJZxmA9iHpl"
)
ARTICLES_TABLE_SANDBOX = os.environ.get(
    "AIRTABLE_ARTICLES_TABLE_SANDBOX",
    "Articles - All Ingested"
)


def newsletter_extract_sandbox(
    debug: bool = False,
    since_hours: int = 48  # Look back further for newsletters
) -> Dict[str, Any]:
    """
    Standalone newsletter extraction job.

    Fetches newsletter articles from FreshRSS (feed/17), extracts external
    news links using Claude Haiku, and creates records in Airtable.

    Args:
        debug: If True, limit processing for testing
        since_hours: How far back to look for newsletters

    Returns:
        Results dict with counts and timing
    """
    print(f"")
    print(f"{'='*60}")
    print(f"[NEWSLETTER EXTRACTION] Starting at {datetime.now(EST).isoformat()}")
    print(f"{'='*60}")
    print(f"Debug mode: {debug}")
    print(f"Looking back: {since_hours} hours")

    started_at = datetime.now(EST)

    results = {
        "started_at": started_at.isoformat(),
        "source": "FreshRSS Newsletter (feed/17)",
        "newsletter_articles_found": 0,
        "newsletters_processed": 0,
        "links_extracted": 0,
        "records_created": 0,
        "records_skipped_duplicate": 0,
        "records_skipped_blocked": 0,
        "errors": [],
        "newsletters_summary": {}
    }

    try:
        # Initialize Airtable
        if not AIRTABLE_API_KEY:
            raise ValueError("AIRTABLE_API_KEY environment variable not set")

        api = Api(AIRTABLE_API_KEY)
        table = api.table(AIRTABLE_AI_EDITOR_BASE_ID, ARTICLES_TABLE_SANDBOX)

        # Fetch articles from FreshRSS
        print(f"[Newsletter Extract] Fetching articles from FreshRSS...")

        try:
            client = FreshRSSClient()
            # Get all articles, we'll filter for feed/17 ourselves
            all_articles = client.get_articles(limit=500, since_hours=since_hours)

            # Filter for newsletter articles (feed/17)
            newsletter_articles = [
                a for a in all_articles
                if a.get("stream_id") == "feed/17"
            ]

            results["newsletter_articles_found"] = len(newsletter_articles)
            print(f"[Newsletter Extract] Found {len(newsletter_articles)} newsletter articles from feed/17")

        except Exception as e:
            error_msg = f"Failed to fetch from FreshRSS: {e}"
            print(f"[Newsletter Extract] {error_msg}")
            results["errors"].append(error_msg)
            results["completed_at"] = datetime.now(EST).isoformat()
            return results

        if not newsletter_articles:
            print("[Newsletter Extract] No newsletter articles found, exiting")
            results["completed_at"] = datetime.now(EST).isoformat()
            return results

        # Get existing pivot_ids for deduplication
        print("[Newsletter Extract] Fetching existing records for deduplication...")
        try:
            existing_records = table.all(fields=["pivot_id"])
            existing_pivot_ids = {
                r["fields"].get("pivot_id")
                for r in existing_records
                if r["fields"].get("pivot_id")
            }
            print(f"[Newsletter Extract] Found {len(existing_pivot_ids)} existing records")
        except Exception as e:
            print(f"[Newsletter Extract] Warning: Could not fetch existing records: {e}")
            existing_pivot_ids = set()

        # Process each newsletter article
        total_records_created = 0
        newsletters_summary = {}

        for newsletter_article in newsletter_articles:
            try:
                # Detect newsletter domain first to log which newsletter we're processing
                summary = newsletter_article.get('summary', '')
                newsletter_domain = detect_newsletter_domain(summary)

                if not newsletter_domain:
                    continue

                if should_skip_newsletter(newsletter_domain):
                    print(f"[Newsletter Extract] Skipping {newsletter_domain} (in skip list)")
                    continue

                config = get_newsletter_config(newsletter_domain)
                if not config:
                    continue

                newsletter_name = config['name']

                # Extract links using async function
                extracted_records = asyncio.run(
                    process_newsletter_article(newsletter_article, existing_pivot_ids)
                )

                results["newsletters_processed"] += 1

                # Create records in Airtable
                records_from_this_newsletter = 0
                for record in extracted_records:
                    try:
                        table.create(record)
                        total_records_created += 1
                        records_from_this_newsletter += 1
                        results["links_extracted"] += 1
                    except Exception as e:
                        error_msg = f"Error creating record: {str(e)}"
                        print(f"[Newsletter Extract] {error_msg}")
                        results["errors"].append(error_msg)

                # Track per-newsletter stats
                if newsletter_name not in newsletters_summary:
                    newsletters_summary[newsletter_name] = 0
                newsletters_summary[newsletter_name] += records_from_this_newsletter

            except Exception as e:
                error_msg = f"Error processing newsletter: {str(e)}"
                print(f"[Newsletter Extract] {error_msg}")
                results["errors"].append(error_msg)

        results["records_created"] = total_records_created
        results["newsletters_summary"] = newsletters_summary

        # Log final summary
        print(f"")
        print(f"{'='*60}")
        print(f"[NEWSLETTER EXTRACTION] Summary")
        print(f"{'='*60}")
        print(f"  Newsletter articles found:    {results['newsletter_articles_found']}")
        print(f"  Newsletters processed:        {results['newsletters_processed']}")
        print(f"  Links extracted:              {results['links_extracted']}")
        print(f"  Records created in Airtable:  {results['records_created']}")
        print(f"  Errors:                       {len(results['errors'])}")
        print(f"{'='*60}")

        if newsletters_summary:
            print(f"")
            print(f"[BREAKDOWN] Records by Newsletter:")
            for name, count in sorted(newsletters_summary.items(), key=lambda x: -x[1]):
                print(f"  {name}: {count}")
            print(f"")

    except Exception as e:
        error_msg = f"Newsletter extraction job failed: {str(e)}"
        print(f"[Newsletter Extract] {error_msg}")
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()

    results["completed_at"] = datetime.now(EST).isoformat()
    # Add 'processed' key for UI compatibility
    results["processed"] = results["records_created"]
    return results


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": newsletter_extract_sandbox,
    "trigger": "cron",
    "hour": 12,  # Noon UTC = 7 AM EST
    "minute": 0,
    "id": "newsletter_extract_sandbox",
    "replace_existing": True
}
