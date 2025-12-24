"""
Step 2: Slot Selection Job
Workflow ID: SZmPztKNEmisG3Zf
Schedule: 11:55 PM EST (0 4 * * 2-6 UTC)

5 sequential Claude agent calls select one story per slot, tracking
previously selected companies/sources/IDs to enforce diversity rules.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.claude import ClaudeClient


# Slot-specific freshness windows (in days)
SLOT_FRESHNESS = {
    1: 1,   # 0-24 hours
    2: 2,   # 24-48 hours
    3: 7,   # 0-7 days
    4: 2,   # 0-48 hours
    5: 7,   # 0-7 days
}


def select_slots() -> dict:
    """
    Step 2: Slot Selection Cron Job - Main entry point

    Flow:
    1. Get yesterday's issue for diversity rules
    2. For each slot (1-5):
       a. Get pre-filter candidates for that slot
       b. Filter out already selected storyIDs
       c. Call Claude agent with cumulative state
       d. Track selected story, company, source
    3. Generate subject line from 5 headlines
    4. Write to Selected Slots table

    Returns:
        {slots_filled: int, subject_line: str, record_id: str, errors: list}
    """
    print(f"[Step 2] Starting slot selection at {datetime.utcnow().isoformat()}")

    # Initialize clients
    airtable = AirtableClient()
    claude = ClaudeClient()

    # Track results
    results = {
        "slots_filled": 0,
        "subject_line": "",
        "record_id": "",
        "errors": []
    }

    try:
        # 1. Get yesterday's issue for diversity rules
        print("[Step 2] Fetching yesterday's issue...")
        yesterday_issue = airtable.get_yesterday_issue()
        yesterday_data = _extract_yesterday_data(yesterday_issue)
        print(f"[Step 2] Yesterday's headlines: {len(yesterday_data['headlines'])}")

        # 2. Initialize cumulative state for tracking across slots
        cumulative_state = {
            "selectedToday": [],       # storyIDs selected today
            "selectedCompanies": [],   # companies featured today
            "selectedSources": []      # sources used today (count for max 2)
        }

        # 3. Build today's issue data
        today_date = datetime.utcnow().strftime('%Y-%m-%d')
        issue_date_label = f"Pivot 5 - {datetime.utcnow().strftime('%b %d')}"

        issue_data = {
            "issue_date": issue_date_label,
            "status": "pending"
        }

        headlines = []

        # 4. Process each slot sequentially
        for slot in range(1, 6):
            print(f"[Step 2] Processing Slot {slot}...")

            try:
                # Get pre-filter candidates for this slot
                freshness_days = SLOT_FRESHNESS.get(slot, 7)
                candidates = airtable.get_prefilter_candidates(slot, freshness_days)
                print(f"[Step 2] Slot {slot}: Found {len(candidates)} candidates")

                if not candidates:
                    results["errors"].append({
                        "slot": slot,
                        "error": "No candidates available"
                    })
                    continue

                # Filter out already selected stories
                available_candidates = [
                    c for c in candidates
                    if c.get('fields', {}).get('storyID') not in cumulative_state["selectedToday"]
                ]

                if not available_candidates:
                    results["errors"].append({
                        "slot": slot,
                        "error": "All candidates already selected"
                    })
                    continue

                print(f"[Step 2] Slot {slot}: {len(available_candidates)} available after filtering")

                # Call Claude agent for slot selection
                selection = claude.select_slot(
                    slot=slot,
                    candidates=available_candidates,
                    yesterday_data=yesterday_data,
                    cumulative_state=cumulative_state
                )

                if "error" in selection:
                    results["errors"].append({
                        "slot": slot,
                        "error": selection.get("error")
                    })
                    continue

                # Extract selection results
                selected_story_id = selection.get("selected_storyId", "")
                selected_pivot_id = selection.get("selected_pivotId", "")
                selected_headline = selection.get("selected_headline", "")
                company = selection.get("company")
                source_id = selection.get("source_id", "")

                print(f"[Step 2] Slot {slot} selected: {selected_headline[:50]}...")

                # Update cumulative state
                if selected_story_id:
                    cumulative_state["selectedToday"].append(selected_story_id)
                if company:
                    cumulative_state["selectedCompanies"].append(company)
                if source_id:
                    cumulative_state["selectedSources"].append(source_id)

                # Add to issue data
                issue_data[f"slot_{slot}_headline"] = selected_headline
                issue_data[f"slot_{slot}_storyId"] = selected_story_id
                issue_data[f"slot_{slot}_pivotId"] = selected_pivot_id
                issue_data[f"slot_{slot}_source"] = source_id

                if company:
                    issue_data[f"slot_{slot}_company"] = company

                headlines.append(selected_headline)
                results["slots_filled"] += 1

            except Exception as e:
                print(f"[Step 2] Error processing Slot {slot}: {e}")
                results["errors"].append({
                    "slot": slot,
                    "error": str(e)
                })

        # 5. Generate subject line from headlines
        if headlines:
            print("[Step 2] Generating subject line...")
            try:
                subject_line = claude.generate_subject_line(headlines)
                issue_data["subject_line"] = subject_line
                results["subject_line"] = subject_line
                print(f"[Step 2] Subject line: {subject_line}")
            except Exception as e:
                print(f"[Step 2] Error generating subject line: {e}")
                results["errors"].append({
                    "step": "subject_line",
                    "error": str(e)
                })

        # 6. Write to Selected Slots table
        if results["slots_filled"] > 0:
            print("[Step 2] Writing to Selected Slots table...")
            try:
                record_id = airtable.write_selected_slots(issue_data)
                results["record_id"] = record_id
                print(f"[Step 2] Created record: {record_id}")
            except Exception as e:
                print(f"[Step 2] Error writing selected slots: {e}")
                results["errors"].append({
                    "step": "write_slots",
                    "error": str(e)
                })

        print(f"[Step 2] Slot selection complete: {results}")
        return results

    except Exception as e:
        print(f"[Step 2] Fatal error: {e}")
        results["errors"].append({"fatal": str(e)})
        raise


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


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": select_slots,
    "trigger": "cron",
    "hour": 4,  # 4 AM UTC = 11:55 PM EST (approximately)
    "minute": 55,
    "day_of_week": "tue-sat",  # Mon-Fri in EST
    "id": "step2_slot_selection",
    "replace_existing": True
}
