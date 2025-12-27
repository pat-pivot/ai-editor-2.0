"""
AI Scoring Job - Score articles using Claude Sonnet

Replaces the n8n 20-minute cron workflow (mgIuocpwH9kXvPjM).
Can run manually, on-demand, or chained after ingestion.

ARCHITECTURE:
  Step 0 (Ingest) → Articles table (needs_ai = true)
  AI Scoring → Updates Articles with scores (needs_ai = false)
              → Creates Newsletter Stories records (interest_score >= 15)

OUTPUT TABLES:
  1. Articles (tblGumae8KDpsrWvh) - ALL articles with scores
  2. Newsletter Stories (tblY78ziWp5yhiGXp) - BEST articles (interest_score >= 15)

Query: {needs_ai} = 1
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from pyairtable import Api
from anthropic import Anthropic

# Configuration
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appwSozYTkrsQWUXB")
ARTICLES_TABLE = os.environ.get("AIRTABLE_ARTICLES_TABLE", "tblGumae8KDpsrWvh")
NEWSLETTER_STORIES_TABLE = "tblY78ziWp5yhiGXp"  # Output for high-interest articles
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Interest score threshold for Newsletter Stories output
INTEREST_SCORE_THRESHOLD = 15

# Topic labels (18 fixed categories)
VALID_TOPICS = [
    "WORK", "EDUCATION", "INFRASTRUCTURE", "HEALTHCARE", "ENVIRONMENT",
    "FINANCE", "RETAIL", "ENTERTAINMENT", "MANUFACTURING", "SECURITY",
    "TRANSPORTATION", "AGRICULTURE", "LEGAL", "REAL_ESTATE", "ENERGY",
    "GOVERNMENT", "COMMUNICATION", "OTHER"
]

# Newsletter slugs for fit scoring
NEWSLETTERS = ["pivot_ai", "pivot_build", "pivot_invest"]


def build_scoring_prompt(article: Dict[str, Any]) -> str:
    """
    Build the Claude prompt for scoring an article.

    Args:
        article: Article record from Airtable

    Returns:
        Formatted prompt string
    """
    headline = article.get("headline") or article.get("title", "No headline")
    source = article.get("source_id", "Unknown")
    url = article.get("original_url", "")
    published = article.get("date_published", "")

    return f"""Analyze this news article and provide scoring for newsletter placement.

ARTICLE:
- Headline: {headline}
- Source: {source}
- URL: {url}
- Published: {published}

SCORING REQUIREMENTS:

1. **interest_score** (0-25): How important/interesting is this article?
   - 0-10: Low interest, generic news
   - 11-15: Moderate interest, worth noting
   - 16-20: High interest, should be considered for newsletter
   - 21-25: Exceptional, must-include story

2. **sentiment** (-10 to 10): Tone of the news
   - -10 to -5: Very negative (crisis, failure, scandal)
   - -4 to -1: Somewhat negative
   - 0: Neutral
   - 1 to 4: Somewhat positive
   - 5 to 10: Very positive (success, breakthrough, innovation)

3. **topic**: Classify into ONE of these categories:
   WORK, EDUCATION, INFRASTRUCTURE, HEALTHCARE, ENVIRONMENT,
   FINANCE, RETAIL, ENTERTAINMENT, MANUFACTURING, SECURITY,
   TRANSPORTATION, AGRICULTURE, LEGAL, REAL_ESTATE, ENERGY,
   GOVERNMENT, COMMUNICATION, OTHER

4. **tags**: Array of exactly 5 short descriptive tags

5. **newsletter_recommendations**: For each newsletter, provide a fit_score (0-25):
   - pivot_ai: AI and technology news
   - pivot_build: Business and construction
   - pivot_invest: Finance and investment

6. **primary_newsletter_slug**: Which newsletter is the best fit?

Return ONLY valid JSON (no markdown, no explanation):
{{
  "interest_score": <number 0-25>,
  "sentiment": <number -10 to 10>,
  "topic": "<one of the valid topics>",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "newsletter_recommendations": [
    {{"newsletter_slug": "pivot_ai", "fit_score": <0-25>}},
    {{"newsletter_slug": "pivot_build", "fit_score": <0-25>}},
    {{"newsletter_slug": "pivot_invest", "fit_score": <0-25>}}
  ],
  "primary_newsletter_slug": "<best fit newsletter>"
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
            max_tokens=1024,
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
        print(f"[AI Scoring] JSON parse error for article {article.get('id')}: {e}")
        return None
    except Exception as e:
        print(f"[AI Scoring] Error scoring article {article.get('id')}: {e}")
        return None


def run_ai_scoring(batch_size: int = 50) -> Dict[str, Any]:
    """
    Main AI Scoring job function.

    Queries articles with needs_ai = true, scores them with Claude,
    and updates the records.

    Args:
        batch_size: Max articles to process per run (default 50)

    Returns:
        Results dict with counts and timing
    """
    print(f"[AI Scoring] Starting job at {datetime.utcnow().isoformat()}")
    started_at = datetime.now(timezone.utc)

    results = {
        "started_at": started_at.isoformat(),
        "articles_queried": 0,
        "articles_scored": 0,
        "articles_failed": 0,
        "articles_skipped": 0,
        "high_interest_count": 0,  # interest_score >= 15
        "newsletter_stories_created": 0,  # Written to Newsletter Stories table
        "errors": []
    }

    try:
        # Initialize clients
        if not AIRTABLE_API_KEY:
            raise ValueError("AIRTABLE_API_KEY not set")
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set")

        airtable = Api(AIRTABLE_API_KEY)
        articles_table = airtable.table(AIRTABLE_BASE_ID, ARTICLES_TABLE)
        newsletter_stories_table = airtable.table(AIRTABLE_BASE_ID, NEWSLETTER_STORIES_TABLE)
        claude = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Query articles needing AI scoring
        print("[AI Scoring] Querying articles with needs_ai = true...")
        formula = "{needs_ai} = 1"
        articles = articles_table.all(formula=formula, max_records=batch_size)

        results["articles_queried"] = len(articles)
        print(f"[AI Scoring] Found {len(articles)} articles to score")

        if not articles:
            print("[AI Scoring] No articles need scoring, exiting")
            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            results["processed"] = 0
            return results

        # Score each article
        for record in articles:
            article_id = record["id"]
            fields = record["fields"]

            headline = fields.get('headline') or fields.get('title', 'Unknown')
            print(f"[AI Scoring] Scoring article: {headline[:50]}...")

            # Score with Claude
            scores = score_article(claude, fields)

            if not scores:
                results["articles_failed"] += 1
                continue

            # Prepare update record
            # Note: Only include fields that exist in the Articles table
            update_fields = {
                "needs_ai": False,  # Mark as scored
                "interest_score": scores.get("interest_score"),
                "sentiment": scores.get("sentiment"),
                "topic": scores.get("topic"),
                "tags": json.dumps(scores.get("tags", [])),
                "date_ai_scored": datetime.now(timezone.utc).isoformat(),
            }
            # Removed: primary_newsletter_slug (field doesn't exist in Airtable)
            # Removed: fit_score_{slug} loop (fields don't exist in Airtable)

            # Update Articles table record
            try:
                articles_table.update(article_id, update_fields)
                results["articles_scored"] += 1
                print(f"[AI Scoring] ✓ Scored: interest={scores.get('interest_score')}, topic={scores.get('topic')}")
            except Exception as e:
                error_msg = f"Failed to update article {article_id}: {e}"
                print(f"[AI Scoring] {error_msg}")
                results["errors"].append(error_msg)
                results["articles_failed"] += 1
                continue

            # Track high-interest articles and write to Newsletter Stories
            interest_score = scores.get("interest_score", 0)
            if interest_score >= INTEREST_SCORE_THRESHOLD:
                results["high_interest_count"] += 1

                # Create Newsletter Stories record for high-interest articles
                try:
                    newsletter_story = {
                        "pivotId": fields.get("pivot_Id"),
                        "core_url": fields.get("original_url"),
                        "source_id": fields.get("source_id", "Unknown"),
                        "date_og_published": fields.get("date_published"),
                        "interest_score": interest_score,
                        "sentiment": scores.get("sentiment"),
                        "topic": scores.get("topic"),
                        "tags": json.dumps(scores.get("tags", [])),
                        "fit_score": scores.get("newsletter_recommendations", [{}])[0].get("fit_score", 0),
                        "newsletter": scores.get("primary_newsletter_slug", "pivot_ai"),
                    }
                    # Remove None values
                    newsletter_story = {k: v for k, v in newsletter_story.items() if v is not None}

                    newsletter_stories_table.create(newsletter_story)
                    results["newsletter_stories_created"] += 1
                    print(f"[AI Scoring] ✅ Created Newsletter Story: {headline[:50]}... (score: {interest_score})")
                except Exception as e:
                    error_msg = f"Failed to create Newsletter Story for {article_id}: {e}"
                    print(f"[AI Scoring] {error_msg}")
                    results["errors"].append(error_msg)

        print(f"[AI Scoring] Complete: {results['articles_scored']} scored, {results['high_interest_count']} high-interest, {results['newsletter_stories_created']} Newsletter Stories created")

    except Exception as e:
        error_msg = f"AI Scoring job failed: {e}"
        print(f"[AI Scoring] {error_msg}")
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["processed"] = results["articles_scored"]
    return results


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": run_ai_scoring,
    "trigger": "interval",
    "minutes": 20,  # Match n8n behavior, or set higher
    "id": "ai_scoring",
    "replace_existing": True
}
