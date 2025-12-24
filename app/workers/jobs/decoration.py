"""
Step 3: Decoration Job
Workflow ID: HCbd2g852rkQgSqr
Schedule: 9:25 PM EST (0 2 25 * * 2-6 UTC)

Creates AI-generated headlines, deks, bullet points for each selected story.
Uses Gemini for content cleaning and Claude for decoration generation.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.gemini import GeminiClient
from utils.claude import ClaudeClient


def decorate_stories() -> dict:
    """
    Step 3: Decoration Cron Job - Main entry point

    Flow:
    1. Get pending issue from Selected Slots (status='pending')
    2. For each slot (1-5):
       a. Lookup article markdown by pivotId
       b. Clean content using Gemini
       c. Generate decoration (headline, dek, bullets, image_prompt) using Claude
       d. Apply bolding to bullets
       e. Write to Decoration table
    3. Update issue status to 'decorated'

    Returns:
        {decorated: int, issue_id: str, errors: list}
    """
    print(f"[Step 3] Starting decoration at {datetime.utcnow().isoformat()}")

    # Initialize clients
    airtable = AirtableClient()
    gemini = GeminiClient()
    claude = ClaudeClient()

    # Track results
    results = {
        "decorated": 0,
        "issue_id": "",
        "decoration_ids": [],
        "errors": []
    }

    try:
        # 1. Get pending issue from Selected Slots
        print("[Step 3] Fetching pending issue...")
        pending_issue = airtable.get_pending_issue()

        if not pending_issue:
            print("[Step 3] No pending issue found")
            return results

        issue_record_id = pending_issue.get('id', '')
        issue_fields = pending_issue.get('fields', {})
        results["issue_id"] = issue_record_id

        print(f"[Step 3] Processing issue: {issue_fields.get('issue_date', 'unknown')}")

        # 2. Process each slot
        for slot in range(1, 6):
            print(f"[Step 3] Decorating Slot {slot}...")

            try:
                # Extract slot data from issue
                pivot_id = issue_fields.get(f'slot_{slot}_pivotId', '')
                story_id = issue_fields.get(f'slot_{slot}_storyId', '')
                headline = issue_fields.get(f'slot_{slot}_headline', '')
                source_id = issue_fields.get(f'slot_{slot}_source', '')

                if not pivot_id:
                    print(f"[Step 3] Slot {slot}: No pivotId, skipping")
                    continue

                # 2a. Lookup article markdown
                print(f"[Step 3] Slot {slot}: Fetching article {pivot_id}...")
                article = airtable.get_article_by_pivot_id(pivot_id)

                if not article:
                    results["errors"].append({
                        "slot": slot,
                        "error": f"Article not found: {pivot_id}"
                    })
                    continue

                article_fields = article.get('fields', {})
                markdown = article_fields.get('markdown', '')
                original_url = article_fields.get('original_url', '')

                if not markdown:
                    results["errors"].append({
                        "slot": slot,
                        "error": f"No markdown content for {pivot_id}"
                    })
                    continue

                # 2b. Clean content using Gemini
                print(f"[Step 3] Slot {slot}: Cleaning content...")
                try:
                    cleaned_content = gemini.clean_content(markdown)
                except Exception as e:
                    print(f"[Step 3] Slot {slot}: Gemini cleaning failed, using raw: {e}")
                    cleaned_content = markdown[:8000]

                # 2c. Generate decoration using Claude
                print(f"[Step 3] Slot {slot}: Generating decoration...")
                story_data = {
                    "headline": headline,
                    "source": source_id,
                    "url": original_url,
                    "topic": issue_fields.get(f'slot_{slot}_topic', '')
                }

                decoration = claude.decorate_story(story_data, cleaned_content)

                if "error" in decoration:
                    results["errors"].append({
                        "slot": slot,
                        "error": decoration.get("error")
                    })
                    continue

                # 2d. Apply bolding to bullets
                print(f"[Step 3] Slot {slot}: Applying bolding...")
                bullets = [
                    decoration.get("b1", ""),
                    decoration.get("b2", ""),
                    decoration.get("b3", "")
                ]

                try:
                    bolded_bullets = claude.apply_bolding(bullets)
                    if len(bolded_bullets) >= 3:
                        decoration["b1"] = bolded_bullets[0]
                        decoration["b2"] = bolded_bullets[1]
                        decoration["b3"] = bolded_bullets[2]
                except Exception as e:
                    print(f"[Step 3] Slot {slot}: Bolding failed, using original: {e}")

                # 2e. Write to Decoration table
                print(f"[Step 3] Slot {slot}: Writing decoration record...")
                decoration_data = {
                    "storyID": story_id,
                    "pivotId": pivot_id,
                    "issue_record_id": issue_record_id,
                    "slot_order": slot,
                    "ai_headline": decoration.get("ai_headline", headline),
                    "ai_dek": decoration.get("ai_dek", ""),
                    "ai_bullet_1": decoration.get("b1", ""),
                    "ai_bullet_2": decoration.get("b2", ""),
                    "ai_bullet_3": decoration.get("b3", ""),
                    "label": decoration.get("label", "AI NEWS"),
                    "image_prompt": decoration.get("image_prompt", ""),
                    "image_status": "pending",
                    "original_url": original_url,
                    "source_id": source_id,
                    "date_decorated": datetime.utcnow().strftime('%Y-%m-%d')
                }

                record_id = airtable.write_decoration(decoration_data)
                results["decoration_ids"].append(record_id)
                results["decorated"] += 1

                print(f"[Step 3] Slot {slot}: Created decoration {record_id}")

            except Exception as e:
                print(f"[Step 3] Error decorating Slot {slot}: {e}")
                results["errors"].append({
                    "slot": slot,
                    "error": str(e)
                })

        # 3. Update issue status to 'decorated' if any slots were processed
        if results["decorated"] > 0:
            print("[Step 3] Updating issue status to 'decorated'...")
            try:
                from ..utils.airtable import AirtableClient
                airtable_client = AirtableClient()
                # Use the selected slots table to update status
                table = airtable_client._get_table(
                    airtable_client.ai_editor_base_id,
                    airtable_client.selected_slots_table_id
                )
                table.update(issue_record_id, {"status": "decorated"})
                print("[Step 3] Issue status updated")
            except Exception as e:
                print(f"[Step 3] Error updating issue status: {e}")
                results["errors"].append({
                    "step": "update_status",
                    "error": str(e)
                })

        print(f"[Step 3] Decoration complete: {results}")
        return results

    except Exception as e:
        print(f"[Step 3] Fatal error: {e}")
        results["errors"].append({"fatal": str(e)})
        raise


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": decorate_stories,
    "trigger": "cron",
    "hour": 2,   # 2 AM UTC = ~9 PM EST
    "minute": 25,
    "day_of_week": "tue-sat",
    "id": "step3_decoration",
    "replace_existing": True
}
