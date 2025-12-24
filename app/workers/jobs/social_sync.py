"""
Step 5: Social Syndication Job
Workflow ID: I8U8LgJVDsO8PeBJ
Schedule: 4:30 AM & 5:00 AM EST (0 9 30 * * 2-6 UTC, 0 10 0 * * 2-6 UTC)

Syndicates decorated stories to P5 Social Posts table for social media
publishing workflows.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient


def sync_social_posts() -> dict:
    """
    Step 5: Social Sync Cron Job - Main entry point

    Flow:
    1. Get decorated stories with image_status='generated' and no social_status
    2. For each story:
       a. Check if social post already exists (by source_record_id)
       b. If not, create P5 Social Post record
       c. Mark decoration as social_synced
    3. Return sync results

    Returns:
        {synced: int, skipped: int, errors: list}
    """
    print(f"[Step 5] Starting social sync at {datetime.utcnow().isoformat()}")

    # Initialize client
    airtable = AirtableClient()

    # Track results
    results = {
        "synced": 0,
        "skipped": 0,
        "already_exists": 0,
        "errors": []
    }

    try:
        # 1. Get decorated stories ready for social
        print("[Step 5] Fetching stories for social sync...")
        decorations = airtable.get_decorations_for_social(max_records=10)

        if not decorations:
            print("[Step 5] No stories need social sync")
            return results

        print(f"[Step 5] Found {len(decorations)} stories for social sync")

        # 2. Process each story
        for decoration in decorations:
            record_id = decoration.get('id', '')
            fields = decoration.get('fields', {})
            story_id = fields.get('storyID', 'unknown')

            print(f"[Step 5] Processing story: {story_id}")

            try:
                # 2a. Check if social post already exists
                existing = airtable.find_existing_social_post(record_id)

                if existing:
                    print(f"[Step 5] Social post already exists for {story_id}")
                    results["already_exists"] += 1

                    # Still mark as synced to avoid reprocessing
                    airtable.mark_social_synced(record_id)
                    continue

                # 2b. Build social post data
                social_post_data = _build_social_post(fields, record_id)

                if not social_post_data:
                    print(f"[Step 5] Insufficient data for {story_id}, skipping")
                    results["skipped"] += 1
                    continue

                # 2c. Create P5 Social Post record
                print(f"[Step 5] Creating social post for {story_id}...")
                social_record_id = airtable.create_social_post(social_post_data)

                print(f"[Step 5] Created social post: {social_record_id}")

                # 2d. Mark decoration as synced
                airtable.mark_social_synced(record_id)
                results["synced"] += 1

            except Exception as e:
                print(f"[Step 5] Error syncing {story_id}: {e}")
                results["errors"].append({
                    "storyId": story_id,
                    "error": str(e)
                })

        print(f"[Step 5] Social sync complete: {results}")
        return results

    except Exception as e:
        print(f"[Step 5] Fatal error: {e}")
        results["errors"].append({"fatal": str(e)})
        raise


def _build_social_post(decoration_fields: dict, source_record_id: str) -> Optional[dict]:
    """
    Build social post data from decoration fields.

    Required fields:
    - headline
    - At least one bullet point
    - image_url

    Returns:
        Social post data dict, or None if insufficient data
    """
    headline = decoration_fields.get('ai_headline', '')
    label = decoration_fields.get('label', 'AI NEWS')
    b1 = decoration_fields.get('ai_bullet_1', '')
    b2 = decoration_fields.get('ai_bullet_2', '')
    b3 = decoration_fields.get('ai_bullet_3', '')
    image_url = decoration_fields.get('image_url', '')
    original_url = decoration_fields.get('original_url', '')
    slot_order = decoration_fields.get('slot_order', 0)

    # Validate minimum required fields
    if not headline:
        return None

    if not any([b1, b2, b3]):
        return None

    # Build social post record
    return {
        "source_record_id": source_record_id,
        "headline": headline,
        "label": label,
        "b1": b1,
        "b2": b2,
        "b3": b3,
        "image_raw_url": image_url,
        "original_url": original_url,
        "publish_status": "ready",
        "Order": slot_order,
        "date_synced": datetime.utcnow().strftime('%Y-%m-%d'),
        "source": "ai_editor_2"
    }


def resync_story(decoration_record_id: str) -> dict:
    """
    Manually resync a single story to social.

    Args:
        decoration_record_id: Airtable decoration record ID

    Returns:
        {success: bool, social_record_id: str, error: str}
    """
    print(f"[Step 5] Manual resync for record: {decoration_record_id}")

    airtable = AirtableClient()

    try:
        # Get decoration record
        table = airtable._get_table(
            airtable.ai_editor_base_id,
            airtable.decoration_table_id
        )
        decoration = table.get(decoration_record_id)

        if not decoration:
            return {"success": False, "error": "Decoration not found"}

        fields = decoration.get('fields', {})

        # Check for existing
        existing = airtable.find_existing_social_post(decoration_record_id)
        if existing:
            return {
                "success": True,
                "social_record_id": existing.get('id'),
                "message": "Already exists"
            }

        # Build and create social post
        social_post_data = _build_social_post(fields, decoration_record_id)

        if not social_post_data:
            return {"success": False, "error": "Insufficient data for social post"}

        social_record_id = airtable.create_social_post(social_post_data)
        airtable.mark_social_synced(decoration_record_id)

        return {
            "success": True,
            "social_record_id": social_record_id
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_social_stats() -> dict:
    """
    Get social sync statistics.

    Returns:
        {total_posts: int, pending: int, published: int, by_date: dict}
    """
    airtable = AirtableClient()

    try:
        table = airtable._get_table(
            airtable.p5_social_base_id,
            airtable.p5_social_posts_table_id
        )

        # Get all posts
        records = table.all(
            fields=['publish_status', 'date_synced', 'headline']
        )

        stats = {
            "total_posts": len(records),
            "ready": 0,
            "published": 0,
            "pending": 0,
            "by_date": {}
        }

        for record in records:
            fields = record.get('fields', {})
            status = fields.get('publish_status', 'unknown')
            date = fields.get('date_synced', 'unknown')

            if status == 'ready':
                stats["ready"] += 1
            elif status == 'published':
                stats["published"] += 1
            else:
                stats["pending"] += 1

            if date not in stats["by_date"]:
                stats["by_date"][date] = 0
            stats["by_date"][date] += 1

        return stats

    except Exception as e:
        return {"error": str(e)}


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": sync_social_posts,
    "trigger": "cron",
    "hour": 9,   # 9 AM UTC = ~4 AM EST
    "minute": 30,
    "day_of_week": "tue-sat",
    "id": "step5_social_sync",
    "replace_existing": True
}


# Secondary schedule (5 AM EST)
JOB_CONFIG_2 = {
    "func": sync_social_posts,
    "trigger": "cron",
    "hour": 10,  # 10 AM UTC = 5 AM EST
    "minute": 0,
    "day_of_week": "tue-sat",
    "id": "step5_social_sync_2",
    "replace_existing": True
}
