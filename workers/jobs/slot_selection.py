"""
Step 2: Slot Selection Job
Workflow ID: SZmPztKNEmisG3Zf
Schedule: 11:55 PM EST (0 4 * * 2-6 UTC)

5 sequential Claude agent calls select one story per slot, tracking
previously selected companies/sources/IDs to enforce diversity rules.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.claude import ClaudeClient

# EST timezone (UTC-5) for newsletter scheduling
# Newsletter is for US East Coast readers, so all date calculations must use EST
EST = timezone(timedelta(hours=-5))


# Base slot-specific freshness windows (in days)
# These are extended on weekends (see get_slot_freshness)
BASE_SLOT_FRESHNESS = {
    1: 1,   # 0-24 hours (72h on weekends)
    2: 2,   # 24-48 hours (72h on weekends)
    3: 7,   # 0-7 days
    4: 2,   # 0-48 hours (72h on weekends)
    5: 7,   # 0-7 days
}

# 14-day lookback for duplicate checking (matches n8n workflow)
DUPLICATE_LOOKBACK_DAYS = 14


def get_next_issue_date() -> tuple[str, str]:
    """
    Calculate the next newsletter issue date with weekend skipping.

    CRITICAL: Uses EST timezone, not UTC!
    Newsletter schedule is based on US East Coast time.
    Job runs at ~9:25 PM EST = ~2:25 AM UTC next day.

    n8n Logic:
    - Newsletter runs Tue-Sat for Mon-Fri issues
    - Friday run → Monday issue (skip weekend)
    - Saturday run → Monday issue (skip weekend)
    - Otherwise → next day

    Returns:
        Tuple of (issue_date_iso, issue_date_label)
        e.g., ('2025-01-02', 'Pivot 5 - Jan 02')
    """
    # FIXED 1/2/26: Use EST, not UTC. Job runs at 9:25 PM EST.
    # Using UTC caused Friday calculation when it was still Thursday EST.
    now = datetime.now(EST)
    weekday = now.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

    print(f"[Step 2] Date calculation: EST now = {now.strftime('%Y-%m-%d %H:%M %Z')}, weekday = {weekday}")

    # Calculate next issue date based on day of week
    if weekday == 4:  # Friday -> Monday (skip Sat/Sun)
        next_issue = now + timedelta(days=3)
    elif weekday == 5:  # Saturday -> Monday (skip Sun)
        next_issue = now + timedelta(days=2)
    else:
        next_issue = now + timedelta(days=1)

    issue_date_iso = next_issue.strftime('%Y-%m-%d')
    issue_date_label = f"Pivot 5 - {next_issue.strftime('%b %d')}"

    return issue_date_iso, issue_date_label


def get_slot_freshness(slot: int) -> int:
    """
    Get freshness window for a slot, extended on weekends.

    n8n Logic:
    - On Sunday/Monday runs, extend freshness to 72 hours (3 days) for slots 1, 2, 4
    - This accounts for weekend gap when no newsletters are sent

    Args:
        slot: Slot number (1-5)

    Returns:
        Freshness window in days
    """
    base_freshness = BASE_SLOT_FRESHNESS.get(slot, 7)

    # Check if it's a weekend (Sunday=6 or Monday=0) - use EST, not UTC
    weekday = datetime.now(EST).weekday()
    is_weekend_run = weekday in (6, 0)  # Sunday or Monday

    # Extend to 72 hours (3 days) for slots with short freshness on weekends
    if is_weekend_run and base_freshness <= 2:
        return 3  # 72 hours

    return base_freshness


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
        # 1. Get recent issues for diversity rules (14-day lookback)
        print(f"[Step 2] Fetching recent issues (last {DUPLICATE_LOOKBACK_DAYS} days)...")
        recent_issues = airtable.get_recent_sent_issues(DUPLICATE_LOOKBACK_DAYS)

        # 1b. Get decorated stories for semantic deduplication (added 1/7/26)
        print(f"[Step 2] Fetching decorated stories for semantic deduplication...")
        decorated_stories = airtable.get_recent_decorated_stories(DUPLICATE_LOOKBACK_DAYS)
        print(f"[Step 2] Found {len(decorated_stories)} decorated stories for semantic context")

        # Pass decorated_stories to extraction function for semantic context
        recent_data = _extract_recent_issues_data(recent_issues, decorated_stories)
        print(f"[Step 2] Recent issues found: {len(recent_issues)}, total storyIds: {len(recent_data['storyIds'])}, story_summaries: {len(recent_data.get('story_summaries', []))}")

        # 2. Initialize cumulative state for tracking across slots
        # Updated 12/31/25: selectedSources is now a dict with counts per n8n audit
        cumulative_state = {
            "selectedToday": [],       # storyIDs selected today
            "selectedCompanies": [],   # companies featured today
            "selectedSources": {}      # sources used today {source: count} for max 2 rule
        }

        # NOTE: Source credibility lookup removed 1/1/26
        # Credibility guidance is now baked into Claude system prompts in the database

        # 3. Build today's issue data using proper next-issue calculation
        issue_date_iso, issue_date_label = get_next_issue_date()
        print(f"[Step 2] Next issue date: {issue_date_label}")

        issue_data = {
            "issue_date": issue_date_iso,  # ISO format for Airtable date field
            "issue_id": issue_date_label,  # Human-readable label e.g. "Pivot 5 - Dec 31"
            "status": "pending"
        }

        headlines = []

        # 4. Process each slot sequentially
        for slot in range(1, 6):
            print(f"[Step 2] Processing Slot {slot}...")

            try:
                # Get pre-filter candidates for this slot (with weekend extension)
                freshness_days = get_slot_freshness(slot)
                candidates = airtable.get_prefilter_candidates(slot, freshness_days)
                print(f"[Step 2] Slot {slot}: Found {len(candidates)} candidates")

                if not candidates:
                    results["errors"].append({
                        "slot": slot,
                        "error": "No candidates available"
                    })
                    continue

                # Filter out already selected stories AND stories from 14-day lookback
                # FIXED 1/2/26: Also check headlines and pivotIds, not just storyIDs
                # Same article can get re-ingested with new storyID, causing duplicates
                recent_story_ids = set(recent_data.get('storyIds', []))
                recent_headlines = set(h.lower().strip() for h in recent_data.get('headlines', []) if h)
                recent_pivot_ids = set(recent_data.get('pivotIds', []))
                selected_today = set(cumulative_state["selectedToday"])
                excluded_ids = recent_story_ids | selected_today

                def is_duplicate(candidate):
                    """Check if candidate matches any recently used story by ID, headline, or pivotId"""
                    fields = candidate.get('fields', {})
                    story_id = fields.get('storyID', '')
                    headline = (fields.get('headline', '') or '').lower().strip()
                    pivot_id = fields.get('pivotId', '')

                    # Check storyID
                    if story_id in excluded_ids:
                        return True
                    # Check headline (case-insensitive)
                    if headline and headline in recent_headlines:
                        return True
                    # Check pivotId
                    if pivot_id and pivot_id in recent_pivot_ids:
                        return True
                    return False

                available_candidates = [
                    c for c in candidates
                    if not is_duplicate(c)
                ]

                # Log how many were filtered
                filtered_count = len(candidates) - len(available_candidates)
                if filtered_count > 0:
                    print(f"[Step 2] Slot {slot}: Filtered out {filtered_count} duplicates (by storyID/headline/pivotId)")

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
                    recent_data=recent_data,
                    cumulative_state=cumulative_state
                )

                if "error" in selection:
                    results["errors"].append({
                        "slot": slot,
                        "error": selection.get("error")
                    })
                    continue

                # Extract selection results (field names match n8n prompt output)
                selected_story_id = selection.get("selected_id", "")
                selected_headline = selection.get("selected_headline", "")
                company = selection.get("selected_company")  # n8n uses selected_company
                source_id = selection.get("selected_source", "")  # n8n uses selected_source

                # Look up pivotId from candidates (not returned by Claude, but we have it)
                # FIX 1/7/26: Claude sometimes returns truncated/invalid storyIDs
                # Added headline-based fallback when storyID lookup fails
                selected_pivot_id = ""
                matched_candidate = None
                candidate_story_ids = [c.get('fields', {}).get('storyID') for c in available_candidates]
                print(f"[Step 2] Slot {slot}: Looking for storyID '{selected_story_id}' in {len(available_candidates)} candidates")

                # Step 1: Try exact storyID match
                for c in available_candidates:
                    candidate_sid = c.get('fields', {}).get('storyID')
                    if candidate_sid == selected_story_id:
                        matched_candidate = c
                        selected_pivot_id = c.get('fields', {}).get('pivotId', '')
                        print(f"[Step 2] Slot {slot}: MATCH by storyID - pivotId='{selected_pivot_id}'")
                        break

                # Step 2: FALLBACK - Try headline match if storyID lookup failed
                if not matched_candidate and selected_headline:
                    print(f"[Step 2] Slot {slot}: storyID '{selected_story_id}' not found, trying headline match...")
                    selected_headline_lower = selected_headline.lower().strip()
                    for c in available_candidates:
                        candidate_headline = (c.get('fields', {}).get('headline', '') or '').lower().strip()
                        if candidate_headline == selected_headline_lower:
                            matched_candidate = c
                            # CORRECT the storyID to the actual valid one
                            selected_story_id = c.get('fields', {}).get('storyID', '')
                            selected_pivot_id = c.get('fields', {}).get('pivotId', '')
                            print(f"[Step 2] Slot {slot}: MATCH by headline - corrected storyID='{selected_story_id}', pivotId='{selected_pivot_id}'")
                            break

                if not matched_candidate:
                    print(f"[Step 2] Slot {slot}: WARNING - No match by storyID or headline!")
                    print(f"[Step 2] Slot {slot}: Claude returned storyID='{selected_story_id}', headline='{selected_headline[:80]}...'")
                    print(f"[Step 2] Slot {slot}: Candidate storyIDs: {candidate_story_ids[:10]}...")  # First 10

                print(f"[Step 2] Slot {slot} selected: {selected_headline[:50]}...")

                # Update cumulative state
                if selected_story_id:
                    cumulative_state["selectedToday"].append(selected_story_id)
                if company:
                    cumulative_state["selectedCompanies"].append(company)
                if source_id:
                    # Track source counts in dict (n8n format: {"TechCrunch": 1, "Bloomberg": 1})
                    cumulative_state["selectedSources"][source_id] = \
                        cumulative_state["selectedSources"].get(source_id, 0) + 1

                # Add to issue data (only fields that exist in Airtable Selected Slots table)
                issue_data[f"slot_{slot}_headline"] = selected_headline
                issue_data[f"slot_{slot}_storyId"] = selected_story_id
                issue_data[f"slot_{slot}_pivotId"] = selected_pivot_id
                # Note: slot_{n}_source and slot_{n}_company fields don't exist in Airtable

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


def _extract_recent_issues_data(issues: List[dict], decorated_stories: List[dict] = None) -> dict:
    """
    Extract headlines, storyIds, pivotIds from recent issues (14-day lookback)
    for diversity rule enforcement.

    Updated 12/30/25: Changed from single-day to 14-day lookback to match n8n workflow.
    This prevents the same story from appearing in the newsletter within a 2-week window.

    Updated 1/7/26: Now includes semantic context from decorated stories for Claude comparison.
    This enables semantic deduplication to catch same news events with different headlines/IDs.
    """
    data = {
        "headlines": [],
        "storyIds": [],
        "pivotIds": [],
        "slot1Headline": None,  # Yesterday's Slot 1 headline for two-day company rotation
        "story_summaries": [],   # For semantic deduplication
        "slot_history": {1: [], 2: [], 3: [], 4: [], 5: []}  # NEW: Slot-specific history
    }

    if not issues:
        # Still process decorated_stories even if no issues
        if decorated_stories:
            for story in decorated_stories[:30]:  # Limit to most recent 30
                fields = story.get('fields', {})
                summary = {
                    "headline": fields.get('headline', ''),
                    "bullets": [
                        fields.get('b1', ''),
                        fields.get('b2', ''),
                        fields.get('b3', '')
                    ],
                    "dek": fields.get('ai_dek', ''),
                    "label": fields.get('label', ''),  # FIXED 1/7/26: 'company' doesn't exist, use 'label'
                    "storyId": fields.get('story_id', '')  # Newsletter Issue Stories uses snake_case
                }
                # Add ALL stories with headlines (bullets optional for semantic dedup)
                if summary["headline"]:
                    data["story_summaries"].append(summary)
        return data

    for idx, issue in enumerate(issues):
        fields = issue.get('fields', {})
        issue_date = fields.get('issue_date', 'unknown')

        for i in range(1, 6):
            headline = fields.get(f'slot_{i}_headline', '')
            story_id = fields.get(f'slot_{i}_storyId', '')
            pivot_id = fields.get(f'slot_{i}_pivotId', '')

            if headline:
                data["headlines"].append(headline)
                # NEW: Build slot-specific history (each slot sees its own past selections)
                # This helps Claude avoid selecting same story for same slot
                data["slot_history"][i].append({
                    "headline": headline,
                    "storyId": story_id,
                    "date": issue_date
                })
            if story_id:
                data["storyIds"].append(story_id)
            if pivot_id:
                data["pivotIds"].append(pivot_id)

        # Get Slot 1 headline from most recent issue for two-day company rotation
        # Claude will infer the company name from the headline (e.g., "Nvidia Eyes $3B..." → Nvidia)
        if idx == 0:
            data["slot1Headline"] = fields.get('slot_1_headline')

    # Log slot history counts
    for slot_num in range(1, 6):
        print(f"[Step 2] Slot {slot_num} history: {len(data['slot_history'][slot_num])} past selections")

    # NEW: Add semantic context from decorated stories
    if decorated_stories:
        print(f"[Step 2] Processing {len(decorated_stories)} decorated stories for semantic context")
        skipped_no_headline = 0
        skipped_no_bullets = 0
        for story in decorated_stories[:30]:  # Limit to most recent 30
            fields = story.get('fields', {})
            headline = fields.get('headline', '')
            bullets = [
                fields.get('b1', ''),
                fields.get('b2', ''),
                fields.get('b3', '')
            ]
            summary = {
                "headline": headline,
                "bullets": bullets,
                "dek": fields.get('ai_dek', ''),
                "label": fields.get('label', ''),  # FIXED 1/7/26: 'company' doesn't exist, use 'label'
                "storyId": fields.get('story_id', '')  # Newsletter Issue Stories uses snake_case
            }
            # Add ALL stories with headlines for semantic deduplication
            # FIXED 1/7/26: Previously skipped stories without bullets, but this caused
            # semantic duplicates to slip through (e.g., Utah AI story)
            # Headlines alone are sufficient for Claude to detect semantic duplicates
            if not headline:
                skipped_no_headline += 1
                continue
            # Track but don't skip stories without bullets
            if not any(bullets):
                skipped_no_bullets += 1
            data["story_summaries"].append(summary)

        print(f"[Step 2] Story summaries built: {len(data['story_summaries'])} added, {skipped_no_headline} skipped (no headline), {skipped_no_bullets} without bullets (included anyway)")
        # Log first 3 summaries for debugging
        for i, s in enumerate(data["story_summaries"][:3]):
            print(f"[Step 2] Summary {i+1}: '{s['headline'][:60]}...' bullets={len([b for b in s['bullets'] if b])}")
    else:
        print("[Step 2] WARNING: No decorated_stories provided for semantic deduplication!")

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
