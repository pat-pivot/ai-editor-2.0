"""
Step 1: Pre-Filter Job
Workflow ID: VoSZu0MIJAw1IuLL
Schedule: 9:00 PM EST (0 2 * * 2-6 UTC)

Filters candidate articles into 5 newsletter slots based on freshness,
source credibility, and content relevance using Gemini AI.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.gemini import GeminiClient


def prefilter_stories() -> dict:
    """
    Step 1: Pre-Filter Cron Job - Main entry point

    Flow:
    1. Get fresh stories from Newsletter Stories (last 7 days)
    2. Get queued stories from AI Editor base
    3. Merge story sources
    4. Get source credibility scores
    5. Get yesterday's issue for diversity
    6. For each story: call Gemini for slot eligibility
    7. Write eligible stories to Pre-Filter Log (one record per slot)

    Returns:
        {processed: int, eligible: int, written: int, errors: list}
    """
    print(f"[Step 1] Starting pre-filter job at {datetime.utcnow().isoformat()}")

    # Initialize clients
    airtable = AirtableClient()
    gemini = GeminiClient()

    # Track results
    results = {
        "processed": 0,
        "eligible": 0,
        "written": 0,
        "skipped": 0,
        "errors": []
    }

    try:
        # 1. Get fresh stories from Newsletter Stories table
        print("[Step 1] Fetching fresh stories...")
        fresh_stories = airtable.get_fresh_stories(days=7, max_records=100)
        print(f"[Step 1] Found {len(fresh_stories)} fresh stories")

        # 2. Get queued stories (manual priority)
        print("[Step 1] Fetching queued stories...")
        queued_stories = airtable.get_queued_stories()
        print(f"[Step 1] Found {len(queued_stories)} queued stories")

        # 3. Merge story sources (queued have priority)
        all_stories = _merge_stories(fresh_stories, queued_stories)
        print(f"[Step 1] Total stories to process: {len(all_stories)}")

        # 4. Get source credibility lookup
        print("[Step 1] Building source credibility lookup...")
        source_lookup = airtable.build_source_lookup()
        print(f"[Step 1] Loaded {len(source_lookup)} source scores")

        # 5. Get yesterday's issue for diversity rules
        print("[Step 1] Fetching yesterday's issue...")
        yesterday_issue = airtable.get_yesterday_issue()
        yesterday_data = _extract_yesterday_data(yesterday_issue)
        print(f"[Step 1] Yesterday's headlines: {len(yesterday_data['headlines'])}")

        # 6. Get article details for source lookup
        pivot_ids = [s.get('fields', {}).get('pivotId') for s in all_stories if s.get('fields', {}).get('pivotId')]
        articles_lookup = airtable.get_articles_batch(pivot_ids)
        print(f"[Step 1] Loaded {len(articles_lookup)} article details")

        # 7. Process each story through Gemini pre-filter
        prefilter_records = []

        for story in all_stories:
            results["processed"] += 1
            fields = story.get('fields', {})

            try:
                # Get article details
                pivot_id = fields.get('pivotId', '')
                article = articles_lookup.get(pivot_id, {})
                article_fields = article.get('fields', {}) if article else {}

                # Build story data for Gemini
                source_id = article_fields.get('source_id', '')
                source_score = source_lookup.get(source_id.lower(), 3)

                # Skip low-credibility sources
                if source_score < 2:
                    results["skipped"] += 1
                    continue

                story_data = {
                    "storyId": fields.get('storyID', ''),
                    "pivotId": pivot_id,
                    "headline": fields.get('ai_headline', ''),
                    "dek": fields.get('ai_dek', ''),
                    "topic": fields.get('topic', ''),
                    "source": source_id,
                    "hoursAgo": _calculate_hours_ago(fields.get('date_og_published', '')),
                    "originalUrl": article_fields.get('original_url', '')
                }

                # Call Gemini for slot eligibility
                eligibility = gemini.prefilter_story(
                    story_data,
                    yesterday_data['headlines'],
                    source_score
                )

                eligible_slots = eligibility.get('eligible_slots', [])

                if not eligible_slots:
                    results["skipped"] += 1
                    continue

                results["eligible"] += 1

                # Create one pre-filter log record per eligible slot
                for slot in eligible_slots:
                    record = {
                        "storyID": story_data["storyId"],
                        "pivotId": story_data["pivotId"],
                        "headline": story_data["headline"],
                        "original_url": story_data["originalUrl"],
                        "source_id": source_id,
                        "date_og_published": fields.get('date_og_published', ''),
                        "date_prefiltered": datetime.utcnow().strftime('%Y-%m-%d'),
                        "slot": slot
                    }
                    prefilter_records.append(record)

            except Exception as e:
                results["errors"].append({
                    "storyId": fields.get('storyID', 'unknown'),
                    "error": str(e)
                })
                print(f"[Step 1] Error processing story {fields.get('storyID', 'unknown')}: {e}")

        # 8. Batch write to Pre-Filter Log
        if prefilter_records:
            print(f"[Step 1] Writing {len(prefilter_records)} pre-filter records...")
            record_ids = airtable.write_prefilter_log_batch(prefilter_records)
            results["written"] = len(record_ids)
            print(f"[Step 1] Successfully wrote {len(record_ids)} records")

        print(f"[Step 1] Pre-filter complete: {results}")
        return results

    except Exception as e:
        print(f"[Step 1] Fatal error: {e}")
        results["errors"].append({"fatal": str(e)})
        raise


def _merge_stories(fresh: List[dict], queued: List[dict]) -> List[dict]:
    """
    Merge fresh stories with queued stories.
    Queued stories take priority and are added first.
    Deduplicate by storyID.
    """
    seen_ids = set()
    merged = []

    # Add queued stories first (priority)
    for story in queued:
        story_id = story.get('fields', {}).get('storyID')
        if story_id and story_id not in seen_ids:
            seen_ids.add(story_id)
            merged.append(story)

    # Add fresh stories
    for story in fresh:
        story_id = story.get('fields', {}).get('storyID')
        if story_id and story_id not in seen_ids:
            seen_ids.add(story_id)
            merged.append(story)

    return merged


def _extract_yesterday_data(issue: Optional[dict]) -> dict:
    """
    Extract headlines, storyIds, pivotIds from yesterday's issue
    for diversity rule enforcement.
    """
    data = {
        "headlines": [],
        "storyIds": [],
        "pivotIds": [],
        "slot1Company": None
    }

    if not issue:
        return data

    fields = issue.get('fields', {})

    for i in range(1, 6):
        headline = fields.get(f'slot_{i}_headline', '')
        story_id = fields.get(f'slot_{i}_storyId', '')
        pivot_id = fields.get(f'slot_{i}_pivotId', '')

        if headline:
            data["headlines"].append(headline)
        if story_id:
            data["storyIds"].append(story_id)
        if pivot_id:
            data["pivotIds"].append(pivot_id)

    # Slot 1 company for two-day rotation rule
    data["slot1Company"] = fields.get('slot_1_company')

    return data


def _calculate_hours_ago(date_str: str) -> int:
    """Calculate hours since publication"""
    if not date_str:
        return 999

    try:
        # Handle various date formats
        for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d']:
            try:
                published = datetime.strptime(date_str, fmt)
                delta = datetime.utcnow() - published
                return int(delta.total_seconds() / 3600)
            except ValueError:
                continue
        return 999
    except Exception:
        return 999


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": prefilter_stories,
    "trigger": "cron",
    "hour": 2,  # 2 AM UTC = 9 PM EST
    "minute": 0,
    "day_of_week": "tue-sat",  # Mon-Fri in EST (Tue-Sat in UTC)
    "id": "step1_prefilter",
    "replace_existing": True
}
