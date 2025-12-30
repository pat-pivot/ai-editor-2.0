"""
AI Scoring Sandbox - Simplified Single-Newsletter Scoring

Scores articles using Claude Sonnet for the pivot_ai newsletter only.
This is the SANDBOX version - writes to new tables, doesn't affect production.

SANDBOX ARCHITECTURE:
  Query: 'Articles - All Ingested' where needs_ai = true
  Output: Updates Articles + Creates 'Newsletter Selects' for interest_score >= 15

DIFFERENCES FROM PRODUCTION (ai_scoring.py):
  1. Target Base: AI Editor 2.0 (appglKSJZxmA9iHpl) instead of Pivot Media Master
  2. Single Newsletter: Only pivot_ai (removed pivot_build, pivot_invest)
  3. Simplified Prompt: No multi-newsletter recommendations
  4. Fields: Uses fit_status single-select instead of multiple newsletter fields
  5. Firecrawl: Extracts article content for high-interest articles

Output Tables:
  1. 'Articles - All Ingested' - ALL articles with scores
  2. 'Newsletter Selects' - HIGH-INTEREST articles (interest_score >= 15)

Query: {needs_ai} = 1
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from pyairtable import Api
from anthropic import Anthropic
from firecrawl import FirecrawlApp


# Airtable configuration for AI Editor 2.0 base (SANDBOX)
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_AI_EDITOR_BASE_ID = os.environ.get(
    "AIRTABLE_AI_EDITOR_BASE_ID",
    "appglKSJZxmA9iHpl"  # AI Editor 2.0 base
)
ARTICLES_TABLE_SANDBOX = os.environ.get(
    "AIRTABLE_ARTICLES_TABLE_SANDBOX",
    "Articles - All Ingested"
)
NEWSLETTER_SELECTS_TABLE = os.environ.get(
    "AIRTABLE_NEWSLETTER_SELECTS_TABLE",
    "Newsletter Selects"
)

# Anthropic configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Firecrawl configuration
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")

# Interest score threshold for Newsletter Selects output
INTEREST_SCORE_THRESHOLD = 15

# Topic labels (18 fixed categories)
VALID_TOPICS = [
    "WORK", "EDUCATION", "INFRASTRUCTURE", "HEALTHCARE", "ENVIRONMENT",
    "FINANCE", "RETAIL", "ENTERTAINMENT", "MANUFACTURING", "SECURITY",
    "TRANSPORTATION", "AGRICULTURE", "LEGAL", "REAL_ESTATE", "ENERGY",
    "GOVERNMENT", "COMMUNICATION", "OTHER"
]


def extract_article_content(url: str) -> Optional[str]:
    """
    Extract article content using Firecrawl API (SDK v2).

    Returns markdown content from the article, or None if extraction fails.

    SITE COMPATIBILITY (tested 12/29/25):
      ✅ WORKS: WSJ, Bloomberg (partial), VentureBeat, TechCrunch, The Atlantic,
                The Verge, Reuters, CNBC, Semafor
      ❌ BLOCKED: NYT - WebsiteNotSupportedError (requires Firecrawl Enterprise)

    Args:
        url: The article URL to extract content from

    Returns:
        Markdown content string or None if failed
    """
    if not FIRECRAWL_API_KEY:
        print("[AI Scoring Sandbox] FIRECRAWL_API_KEY not set, skipping extraction")
        return None

    # Skip known blocked sites
    blocked_domains = ["nytimes.com", "nyt.com"]
    if any(domain in url.lower() for domain in blocked_domains):
        print(f"[AI Scoring Sandbox] Skipping blocked site (NYT): {url[:50]}")
        return None

    try:
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        # SDK v2 uses keyword arguments directly, not a dict
        # Note: Cookies via headers not currently supported in SDK v2
        result = app.scrape(
            url,
            formats=["markdown"],
            only_main_content=True,  # Exclude nav, footer, ads
        )

        # SDK v2 returns object with .markdown attribute (not dict)
        if result and result.markdown:
            content = result.markdown
            print(f"[AI Scoring Sandbox] Extracted {len(content)} chars from {url[:50]}...")
            return content
        else:
            print(f"[AI Scoring Sandbox] No content extracted from {url[:50]}")
            return None

    except Exception as e:
        error_str = str(e)
        # Handle common error types gracefully
        if "WebsiteNotSupportedError" in error_str or "Website Not Supported" in error_str:
            print(f"[AI Scoring Sandbox] Site blocked by Firecrawl policy: {url[:50]}")
        else:
            print(f"[AI Scoring Sandbox] Firecrawl extraction failed for {url[:50]}: {e}")
        return None


def build_scoring_prompt(article: Dict[str, Any]) -> str:
    """
    Build simplified Claude prompt for single-newsletter scoring.

    Removed multi-newsletter logic - focuses only on pivot_ai.

    Args:
        article: Article record from Airtable

    Returns:
        Formatted prompt string
    """
    headline = article.get("headline") or article.get("title", "No headline")
    source = article.get("source_id", "Unknown")
    url = article.get("original_url", "")
    published = article.get("date_og_published", "")

    return f"""Analyze this news article for the Pivot AI newsletter.

ARTICLE:
- Headline: {headline}
- Source: {source}
- URL: {url}
- Published: {published}

SCORING REQUIREMENTS:

1. **interest_score** (0-25): How newsworthy is this for AI/tech professionals?
   - 0-10: Low interest, generic news, not relevant to AI/tech
   - 11-15: Moderate interest, tangentially related to AI/tech
   - 16-20: High interest, directly relevant to AI/tech industry
   - 21-25: Exceptional, breaking news or major development

2. **sentiment** (-10 to 10): Tone of the news
   - -10 to -5: Very negative (crisis, failure, scandal)
   - -4 to -1: Somewhat negative
   - 0: Neutral
   - 1 to 4: Somewhat positive
   - 5 to 10: Very positive (breakthrough, innovation, success)

3. **topic**: Classify into ONE of these categories:
   WORK, EDUCATION, INFRASTRUCTURE, HEALTHCARE, ENVIRONMENT,
   FINANCE, RETAIL, ENTERTAINMENT, MANUFACTURING, SECURITY,
   TRANSPORTATION, AGRICULTURE, LEGAL, REAL_ESTATE, ENERGY,
   GOVERNMENT, COMMUNICATION, OTHER

4. **tags**: Array of exactly 5 short descriptive tags

Return ONLY valid JSON (no markdown, no explanation):
{{
  "interest_score": <number 0-25>,
  "sentiment": <number -10 to 10>,
  "topic": "<one of the valid topics>",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""


def score_article(client: Anthropic, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Score a single article using Claude Sonnet.

    Args:
        client: Anthropic client
        article: Article record from Airtable

    Returns:
        Scoring results dict or None if failed
    """
    prompt = build_scoring_prompt(article)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,  # Reduced since simpler output
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse JSON response
        content = response.content[0].text.strip()

        # Handle potential markdown code block wrapping
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        # Validate required fields
        if not isinstance(result.get("interest_score"), (int, float)):
            raise ValueError("Missing or invalid interest_score")
        if result.get("topic") not in VALID_TOPICS:
            result["topic"] = "OTHER"

        return result

    except json.JSONDecodeError as e:
        print(f"[AI Scoring Sandbox] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[AI Scoring Sandbox] Error scoring article: {e}")
        return None


def run_ai_scoring_sandbox(batch_size: int = 50) -> Dict[str, Any]:
    """
    Main sandbox AI Scoring job function.

    Queries articles with needs_ai = true, scores them with Claude,
    and updates the records. Simplified for single newsletter (pivot_ai).

    Args:
        batch_size: Max articles to process per run (default 50)

    Returns:
        Results dict with counts and timing
    """
    print(f"[AI Scoring Sandbox] Starting at {datetime.utcnow().isoformat()}")
    print(f"[AI Scoring Sandbox] Target base: {AIRTABLE_AI_EDITOR_BASE_ID}")
    started_at = datetime.now(timezone.utc)

    results = {
        "started_at": started_at.isoformat(),
        "articles_queried": 0,
        "articles_scored": 0,
        "articles_failed": 0,
        "high_interest_count": 0,
        "newsletter_selects_created": 0,
        "articles_extracted": 0,
        "extraction_failures": 0,
        "errors": []
    }

    try:
        # Initialize clients
        if not AIRTABLE_API_KEY:
            raise ValueError("AIRTABLE_API_KEY not set")
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set")

        airtable = Api(AIRTABLE_API_KEY)
        articles_table = airtable.table(AIRTABLE_AI_EDITOR_BASE_ID, ARTICLES_TABLE_SANDBOX)
        newsletter_selects_table = airtable.table(AIRTABLE_AI_EDITOR_BASE_ID, NEWSLETTER_SELECTS_TABLE)
        claude = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Query articles needing AI scoring
        print("[AI Scoring Sandbox] Querying articles with needs_ai = true...")
        formula = "{needs_ai} = 1"
        articles = articles_table.all(formula=formula, max_records=batch_size)

        results["articles_queried"] = len(articles)
        print(f"[AI Scoring Sandbox] Found {len(articles)} articles to score")

        if not articles:
            print("[AI Scoring Sandbox] No articles need scoring, exiting")
            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            results["processed"] = 0
            return results

        # Score each article
        for record in articles:
            article_id = record["id"]
            fields = record["fields"]

            headline = fields.get('headline') or fields.get('title', 'Unknown')
            print(f"[AI Scoring Sandbox] Scoring: {headline[:50]}...")

            # Score with Claude
            scores = score_article(claude, fields)

            if not scores:
                results["articles_failed"] += 1
                continue

            interest_score = scores.get("interest_score", 0)

            # Determine fit_status based on interest score
            if interest_score >= INTEREST_SCORE_THRESHOLD:
                fit_status = "newsletter_fit"
            else:
                fit_status = "skipped_low_score"

            # Prepare update for Articles table
            update_fields = {
                "needs_ai": False,
                "date_scored": datetime.now(timezone.utc).isoformat(),
                "interest_score": interest_score,
                "fit_status": fit_status,
            }

            # Update Articles table record
            try:
                articles_table.update(article_id, update_fields)
                results["articles_scored"] += 1
                print(f"[AI Scoring Sandbox] Scored: interest={interest_score}, fit_status={fit_status}")
            except Exception as e:
                error_msg = f"Failed to update article {article_id}: {e}"
                print(f"[AI Scoring Sandbox] {error_msg}")
                results["errors"].append(error_msg)
                results["articles_failed"] += 1
                continue

            # Create Newsletter Selects for high-interest articles
            if interest_score >= INTEREST_SCORE_THRESHOLD:
                results["high_interest_count"] += 1

                try:
                    # Extract article content using Firecrawl
                    article_url = fields.get("original_url")
                    raw_content = None
                    if article_url:
                        raw_content = extract_article_content(article_url)
                        if raw_content:
                            results["articles_extracted"] += 1
                        else:
                            results["extraction_failures"] += 1

                    # NOTE: storyId is NOT set here - it will be generated later
                    # in the decoration step from the AI-generated headline
                    newsletter_select = {
                        "pivot_id": fields.get("pivot_id"),
                        "core_url": article_url,
                        "source_name": fields.get("source_name", "Unknown"),
                        "date_ai_process": datetime.now(timezone.utc).isoformat(),
                        "date_og_published": fields.get("date_og_published"),
                        "original_headline": headline,  # Original headline for reference
                        "raw": raw_content,  # Extracted article content from Firecrawl
                        "ai_complete": False,  # Will be set to True after full decoration
                        "topic": scores.get("topic", "OTHER"),
                        "interest_score": interest_score,
                        "sentiment": scores.get("sentiment", 0),
                    }

                    # Remove None values
                    newsletter_select = {k: v for k, v in newsletter_select.items() if v is not None}

                    newsletter_selects_table.create(newsletter_select)
                    results["newsletter_selects_created"] += 1
                    extracted_msg = f" (extracted {len(raw_content)} chars)" if raw_content else " (no extraction)"
                    print(f"[AI Scoring Sandbox] Created Newsletter Select: interest={interest_score}{extracted_msg}")

                except Exception as e:
                    error_msg = f"Failed to create Newsletter Select for {article_id}: {e}"
                    print(f"[AI Scoring Sandbox] {error_msg}")
                    results["errors"].append(error_msg)

        print(f"[AI Scoring Sandbox] Complete:")
        print(f"  - Articles scored: {results['articles_scored']}")
        print(f"  - High-interest: {results['high_interest_count']}")
        print(f"  - Newsletter Selects created: {results['newsletter_selects_created']}")
        print(f"  - Articles extracted: {results['articles_extracted']}")
        print(f"  - Extraction failures: {results['extraction_failures']}")
        print(f"  - Failed: {results['articles_failed']}")

    except Exception as e:
        error_msg = f"AI Scoring job failed: {e}"
        print(f"[AI Scoring Sandbox] {error_msg}")
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["processed"] = results["articles_scored"]
    return results


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": run_ai_scoring_sandbox,
    "trigger": "interval",
    "minutes": 30,  # Run every 30 minutes
    "id": "ai_scoring_sandbox",
    "replace_existing": True
}
