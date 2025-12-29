"""
AI Scoring Job - Score articles AND create decorated Newsletter Stories

REPLACES n8n workflows entirely. This Python job handles:
1. Scoring articles (interest_score, sentiment, topic, tags)
2. Creating fully-decorated Newsletter Stories (ai_headline, ai_dek, bullets, image_prompt)

ARCHITECTURE:
  Step 0 (Ingest) → Articles table (needs_ai = true)
  AI Scoring → Updates Articles with scores (needs_ai = false)
              → Creates DECORATED Newsletter Stories (interest_score >= 15)

OUTPUT TABLES:
  1. Articles (tblGumae8KDpsrWvh) - ALL articles with scores
  2. Newsletter Stories (tblY78ziWp5yhiGXp) - DECORATED high-interest articles

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
NEWSLETTER_STORIES_TABLE = "tblY78ziWp5yhiGXp"  # Newsletter Stories in Pivot Media Master
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
    """
    source = article.get("source_id", "Unknown")
    url = article.get("original_url", "")
    published = article.get("date_published", "")

    return f"""Analyze this news article and provide scoring for newsletter placement.

ARTICLE:
- Source: {source}
- URL: {url}
- Published: {published}

IMPORTANT: Extract the article topic and headline from the URL path. The URL contains slug text that reveals the article subject.

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


def build_decoration_prompt(article: Dict[str, Any], scores: Dict[str, Any]) -> str:
    """
    Build the Claude prompt for decorating a high-interest article.
    Generates ai_headline, ai_dek, 3 bullets with bolding, and image_prompt.
    """
    source = article.get("source_id", "Unknown")
    url = article.get("original_url", "")
    topic = scores.get("topic", "OTHER")

    return f"""You are decorating a news article for an AI-focused newsletter. Generate compelling content.

ARTICLE:
- Source: {source}
- URL: {url}
- Topic: {topic}

IMPORTANT: Extract the article's topic and key information from the URL path. The URL slug reveals the article subject.

GENERATE THE FOLLOWING:

1. **ai_headline**: Rewrite the headline to be more compelling and newsletter-appropriate.
   - 8-15 words
   - Active voice
   - No clickbait but engaging
   - Focus on the key insight or development

2. **ai_dek**: A 1-2 sentence summary that hooks the reader.
   - Explain why this matters
   - 25-40 words
   - Complement the headline, don't repeat it

3. **ai_bullet_1**, **ai_bullet_2**, **ai_bullet_3**: Three bullet points with key insights.
   - Each bullet should be 1-2 sentences
   - Include **bold text** around the key phrase or statistic in each bullet
   - Focus on actionable insights, not just restating facts
   - Each bullet should add new information

4. **image_prompt**: A prompt for generating an illustration.
   - Describe a professional, minimalist tech illustration
   - Include style guidance (colors, composition)
   - 20-40 words

Return ONLY valid JSON (no markdown, no explanation):
{{
  "ai_headline": "<rewritten headline>",
  "ai_dek": "<1-2 sentence summary>",
  "ai_bullet_1": "<bullet with **bold** key phrase>",
  "ai_bullet_2": "<bullet with **bold** key phrase>",
  "ai_bullet_3": "<bullet with **bold** key phrase>",
  "image_prompt": "<image generation prompt>"
}}"""


def score_article(client: Anthropic, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Score a single article using Claude Sonnet.
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
        print(f"[AI Scoring] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[AI Scoring] Error scoring article: {e}")
        return None


def decorate_article(client: Anthropic, article: Dict[str, Any], scores: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate full decoration for a high-interest article.
    Returns ai_headline, ai_dek, bullets, and image_prompt.
    """
    prompt = build_decoration_prompt(article, scores)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            temperature=0.5,  # Slightly more creative for decoration
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.content[0].text.strip()

        # Handle potential markdown code block wrapping
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        # Validate required fields
        required_fields = ["ai_headline", "ai_dek", "ai_bullet_1", "ai_bullet_2", "ai_bullet_3"]
        for field in required_fields:
            if not result.get(field):
                raise ValueError(f"Missing required field: {field}")

        return result

    except json.JSONDecodeError as e:
        print(f"[AI Scoring] Decoration JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[AI Scoring] Error decorating article: {e}")
        return None


def run_ai_scoring(batch_size: int = 150) -> Dict[str, Any]:
    """
    Main AI Scoring job function.

    Queries articles with needs_ai = true, scores them with Claude,
    updates Articles table, and creates decorated Newsletter Stories.

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
        "newsletter_stories_created": 0,
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

        # Query articles needing AI scoring (TODAY only to avoid re-scoring old articles)
        print("[AI Scoring] Querying articles with needs_ai = true (today only)...")
        formula = "AND({needs_ai} = 1, IS_SAME({date_ingested}, TODAY(), 'day'))"
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
            pivot_id = fields.get("pivot_Id", "")

            # Articles table doesn't have headline - use URL slug for logging
            url = fields.get('original_url', '')
            url_slug = url.split('/')[-1][:50] if url else 'Unknown'
            print(f"[AI Scoring] Scoring: {url_slug}...")

            # Score with Claude
            scores = score_article(claude, fields)

            if not scores:
                results["articles_failed"] += 1
                results["errors"].append(f"Failed to score: {url_slug}")
                continue

            # Get the best newsletter fit score
            newsletter_recs = scores.get("newsletter_recommendations", [])
            best_fit_score = 0
            for rec in newsletter_recs:
                if rec.get("fit_score", 0) > best_fit_score:
                    best_fit_score = rec.get("fit_score", 0)

            # Format tags as comma-separated string
            tags_list = scores.get("tags", [])
            tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else str(tags_list)

            # Determine decoration_status based on interest score
            interest_score = scores.get("interest_score", 0)
            decoration_status = "completed" if interest_score >= INTEREST_SCORE_THRESHOLD else "skipped_low_score"

            # Update Articles table
            update_fields = {
                "needs_ai": False,
                "interest_score": interest_score,
                "sentiment": scores.get("sentiment"),
                "topic": scores.get("topic"),
                "tags": tags_str,
                "newsletter": scores.get("primary_newsletter_slug", "pivot_ai"),
                "fit_score": best_fit_score,
                "date_scored": datetime.now(timezone.utc).isoformat(),
                "decoration_status": decoration_status,
            }

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

            # For high-interest articles, generate decoration and create Newsletter Story
            if interest_score >= INTEREST_SCORE_THRESHOLD:
                print(f"[AI Scoring] ⭐ High-interest (score={interest_score}), generating decoration...")

                # Generate decoration
                decoration = decorate_article(claude, fields, scores)

                if not decoration:
                    error_msg = f"Failed to decorate high-interest article: {url_slug}"
                    print(f"[AI Scoring] {error_msg}")
                    results["errors"].append(error_msg)
                    continue

                # Create Newsletter Story record with FULL decoration
                newsletter_story = {
                    # Core identifiers
                    "id": article_id,  # Required unique identifier for Newsletter Stories
                    "pivotId": pivot_id,
                    "storyID": article_id,  # Link to Articles record
                    "core_url": fields.get("original_url", ""),
                    "date_og_published": fields.get("date_published", datetime.now(timezone.utc).isoformat()),

                    # Scores from AI Scoring
                    "interest_score": interest_score,
                    "sentiment": scores.get("sentiment"),
                    "topic": scores.get("topic"),
                    "tags": tags_str,
                    "fit_score": best_fit_score,
                    "newsletter": scores.get("primary_newsletter_slug", "pivot_ai"),

                    # Decoration from Claude
                    "ai_headline": decoration.get("ai_headline", url_slug),
                    "ai_dek": decoration.get("ai_dek", ""),
                    "ai_bullet_1": decoration.get("ai_bullet_1", ""),
                    "ai_bullet_2": decoration.get("ai_bullet_2", ""),
                    "ai_bullet_3": decoration.get("ai_bullet_3", ""),
                    "image_prompt": decoration.get("image_prompt", ""),

                    # Status fields
                    "ai_complete": True,
                    "image_status": "pending",
                    "date_ai_processed": datetime.now(timezone.utc).isoformat(),
                }

                try:
                    created = newsletter_stories_table.create(newsletter_story)
                    results["newsletter_stories_created"] += 1
                    print(f"[AI Scoring] ✅ Created Newsletter Story: {decoration.get('ai_headline', url_slug)[:50]}...")
                except Exception as e:
                    error_msg = f"Failed to create Newsletter Story for {pivot_id}: {e}"
                    print(f"[AI Scoring] {error_msg}")
                    results["errors"].append(error_msg)

        print(f"[AI Scoring] Complete: {results['articles_scored']} scored, {results['newsletter_stories_created']} Newsletter Stories created")

    except Exception as e:
        error_msg = f"AI Scoring job failed: {e}"
        print(f"[AI Scoring] {error_msg}")
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()

    # ALWAYS check for remaining articles and auto-requeue (even after errors)
    try:
        # Re-initialize Airtable client if needed
        if not AIRTABLE_API_KEY:
            print("[AI Scoring] Cannot check remaining: AIRTABLE_API_KEY not set")
        else:
            airtable = Api(AIRTABLE_API_KEY)
            articles_table = airtable.table(AIRTABLE_BASE_ID, ARTICLES_TABLE)

            # Only check for remaining articles from TODAY
            today_formula = "AND({needs_ai} = 1, IS_SAME({date_ingested}, TODAY(), 'day'))"
            remaining = articles_table.all(formula=today_formula, max_records=1)
            if remaining:
                remaining_count = len(articles_table.all(formula=today_formula, max_records=500))
                print(f"[AI Scoring] 🔄 {remaining_count} more articles remaining, auto-requeueing...")
                results["remaining_articles"] = remaining_count
                results["requeued"] = True

                # Re-queue another AI Scoring job
                from rq import Queue
                from redis import Redis

                redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
                redis_conn = Redis.from_url(redis_url)
                queue = Queue("default", connection=redis_conn)
                queue.enqueue(run_ai_scoring, batch_size=batch_size)
                print(f"[AI Scoring] ✅ Requeued next batch")
            else:
                print(f"[AI Scoring] ✅ All articles processed, no more remaining")
                results["remaining_articles"] = 0
                results["requeued"] = False
    except Exception as requeue_error:
        print(f"[AI Scoring] ⚠️ Auto-requeue failed: {requeue_error}")
        results["requeue_error"] = str(requeue_error)

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["processed"] = results["articles_scored"]
    return results


# Job configuration for RQ scheduler
# DISABLED: User wants manual control only, not automatic scheduling
# JOB_CONFIG = {
#     "func": run_ai_scoring,
#     "trigger": "interval",
#     "minutes": 20,
#     "id": "ai_scoring",
#     "replace_existing": True
# }
