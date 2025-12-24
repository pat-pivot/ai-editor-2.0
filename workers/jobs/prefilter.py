"""
Step 1: Pre-Filter Job
Workflow ID: VoSZu0MIJAw1IuLL
Schedule: 9:00 PM EST (0 2 * * 2-6 UTC)

MATCHES n8n WORKFLOW ARCHITECTURE EXACTLY:
- 5 separate Gemini calls (one per slot) with slot-specific prompts
- Each slot gets ALL eligible articles as a BATCH for comparison
- Slot 1 Company Filter runs IN PARALLEL with Gemini Slot 1
- Freshness pre-calculated BEFORE Gemini calls
- Response format: {matches: [{story_id, headline}]}
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set

from utils.airtable import AirtableClient
from utils.gemini import GeminiClient

# Tier 1 companies for Slot 1 Company Filter (runs parallel to Gemini)
SLOT_1_COMPANIES = ['openai', 'google', 'meta', 'nvidia', 'microsoft', 'anthropic', 'xai', 'amazon']


def prefilter_stories() -> dict:
    """
    Step 1: Pre-Filter Cron Job - Main entry point

    BATCH PROCESSING FLOW (matches n8n exactly):
    1. Get fresh stories from Newsletter Stories (last 7 days)
    2. Get queued stories from AI Editor base
    3. Merge story sources
    4. Get source credibility scores
    5. Get yesterday's issue for diversity + exclusion
    6. Build article batch with freshness pre-calculation
    7. Run 5 BATCH Gemini calls (one per slot)
    8. Run Slot 1 Company Filter in parallel
    9. Merge all results
    10. Write eligible stories to Pre-Filter Log (one record per slot)

    Returns:
        {processed: int, eligible: int, written: int, errors: list}
    """
    print(f"[Step 1] Starting pre-filter job at {datetime.utcnow().isoformat()}")
    print("[Step 1] Using BATCH PROCESSING architecture (matches n8n)")

    # Initialize clients
    airtable = AirtableClient()
    gemini = GeminiClient()

    # Track results
    results = {
        "processed": 0,
        "eligible": 0,
        "written": 0,
        "skipped": 0,
        "errors": [],
        "slot_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    }

    try:
        # =================================================================
        # PHASE 1: GATHER ALL DATA
        # =================================================================

        # 1. Get fresh stories from Newsletter Stories table
        print("[Step 1] Fetching fresh stories...")
        fresh_stories = airtable.get_fresh_stories(days=7, max_records=100)
        print(f"[Step 1] Found {len(fresh_stories)} fresh stories")

        # 2. Get queued stories (manual priority) - optional, may not have API access
        print("[Step 1] Fetching queued stories...")
        try:
            queued_stories = airtable.get_queued_stories()
            print(f"[Step 1] Found {len(queued_stories)} queued stories")
        except Exception as e:
            print(f"[Step 1] Warning: Could not fetch queued stories (API access issue): {e}")
            queued_stories = []

        # 3. Merge story sources (queued have priority)
        all_stories = _merge_stories(fresh_stories, queued_stories)
        print(f"[Step 1] Total stories to process: {len(all_stories)}")

        # 4. Get source credibility lookup - optional, may not have API access
        print("[Step 1] Building source credibility lookup...")
        try:
            source_lookup = airtable.build_source_lookup()
            print(f"[Step 1] Loaded {len(source_lookup)} source scores")
        except Exception as e:
            print(f"[Step 1] Warning: Could not load source scores (API access issue): {e}")
            source_lookup = {}  # Default: no source filtering

        # 5. Get yesterday's issue for diversity rules + exclusion - optional
        print("[Step 1] Fetching yesterday's issue...")
        try:
            yesterday_issue = airtable.get_yesterday_issue()
            yesterday_data = _extract_yesterday_data(yesterday_issue)
            print(f"[Step 1] Yesterday's headlines: {len(yesterday_data['headlines'])}")
        except Exception as e:
            print(f"[Step 1] Warning: Could not fetch yesterday's issue (API access issue): {e}")
            yesterday_data = {"headlines": [], "storyIds": [], "pivotIds": [], "slot1Company": None}

        # Build yesterday's storyId exclusion set
        yesterday_story_ids = set(yesterday_data['storyIds'])
        print(f"[Step 1] Excluding {len(yesterday_story_ids)} stories from yesterday's issue")

        # 6. Get article details for source lookup
        pivot_ids = [s.get('fields', {}).get('pivotId') for s in all_stories if s.get('fields', {}).get('pivotId')]
        articles_lookup = airtable.get_articles_batch(pivot_ids)
        print(f"[Step 1] Loaded {len(articles_lookup)} article details")

        # =================================================================
        # PHASE 2: BUILD ARTICLE BATCHES BY SLOT ELIGIBILITY
        # =================================================================

        # Group articles by which slots they're eligible for (based on freshness)
        slot_batches: Dict[int, List[Dict]] = {1: [], 2: [], 3: [], 4: [], 5: []}
        article_lookup: Dict[str, Dict] = {}  # story_id -> full article data

        for story in all_stories:
            results["processed"] += 1
            fields = story.get('fields', {})
            story_id = fields.get('storyID', '')

            # EXCLUSION: Skip stories from yesterday's issue
            if story_id in yesterday_story_ids:
                results["skipped"] += 1
                print(f"[Step 1] Skipping {story_id} - was in yesterday's issue")
                continue

            # Get article details
            pivot_id = fields.get('pivotId', '')
            article = articles_lookup.get(pivot_id, {})
            article_fields = article.get('fields', {}) if article else {}

            # Get source credibility
            source_id = article_fields.get('source_id', '')
            source_score = source_lookup.get(source_id.lower(), 3)

            # Skip low-credibility sources
            if source_score < 2:
                results["skipped"] += 1
                continue

            # Calculate freshness hours
            hours_ago = _calculate_hours_ago(fields.get('date_og_published', ''))

            # PRE-CALCULATE eligible slots based on freshness
            freshness_eligible_slots = _calculate_eligible_slots(hours_ago)
            if not freshness_eligible_slots:
                results["skipped"] += 1
                print(f"[Step 1] Skipping {story_id} - too old ({hours_ago}h)")
                continue

            # Build headline (prefer ai_headline)
            headline = fields.get('ai_headline', '') or fields.get('headline', '')
            core_url = article_fields.get('core_url', '') or article_fields.get('original_url', '')

            # Build summary from bullets (n8n Gap #3)
            summary_parts = [
                fields.get('ai_dek', ''),
                fields.get('ai_bullet_1', ''),
                fields.get('ai_bullet_2', ''),
                fields.get('ai_bullet_3', '')
            ]
            summary = ' | '.join(p for p in summary_parts if p)

            # Build article data for Gemini batch
            article_data = {
                "story_id": story_id,
                "pivot_id": pivot_id,
                "headline": headline,
                "summary": summary or fields.get('ai_dek', ''),
                "source_score": source_score,
                "freshness_hours": hours_ago,
                "source_id": source_id,
                "core_url": core_url,
                "date_og_published": fields.get('date_og_published', ''),
                "topic": fields.get('topic', '')
            }

            # Store for later lookup
            article_lookup[story_id] = article_data

            # Add to eligible slot batches
            for slot in freshness_eligible_slots:
                slot_batches[slot].append(article_data)

        print(f"[Step 1] Articles per slot batch: {', '.join(f'Slot {s}: {len(b)}' for s, b in slot_batches.items())}")

        # =================================================================
        # PHASE 3: RUN 5 BATCH GEMINI CALLS + SLOT 1 COMPANY FILTER
        # =================================================================

        # Results will be: {story_id: set of eligible slots}
        story_slots: Dict[str, Set[int]] = {}

        # SLOT 1: Gemini Batch + Company Filter (parallel in n8n)
        print("[Step 1] Running Slot 1 batch pre-filter...")
        slot1_gemini_matches = gemini.prefilter_batch_slot_1(slot_batches[1], yesterday_data['headlines'])
        for match in slot1_gemini_matches:
            sid = match.get('story_id')
            if sid:
                if sid not in story_slots:
                    story_slots[sid] = set()
                story_slots[sid].add(1)

        # Slot 1 Company Filter (runs in parallel, merged with Gemini results)
        slot1_company_matches = _slot1_company_filter_batch(slot_batches[1])
        for sid in slot1_company_matches:
            if sid not in story_slots:
                story_slots[sid] = set()
            story_slots[sid].add(1)
        print(f"[Step 1] Slot 1: {len(slot1_gemini_matches)} Gemini + {len(slot1_company_matches)} Company Filter matches")

        # SLOT 2: Gemini Batch
        print("[Step 1] Running Slot 2 batch pre-filter...")
        slot2_matches = gemini.prefilter_batch_slot_2(slot_batches[2], yesterday_data['headlines'])
        for match in slot2_matches:
            sid = match.get('story_id')
            if sid:
                if sid not in story_slots:
                    story_slots[sid] = set()
                story_slots[sid].add(2)
        print(f"[Step 1] Slot 2: {len(slot2_matches)} matches")

        # SLOT 3: Gemini Batch
        print("[Step 1] Running Slot 3 batch pre-filter...")
        slot3_matches = gemini.prefilter_batch_slot_3(slot_batches[3], yesterday_data['headlines'])
        for match in slot3_matches:
            sid = match.get('story_id')
            if sid:
                if sid not in story_slots:
                    story_slots[sid] = set()
                story_slots[sid].add(3)
        print(f"[Step 1] Slot 3: {len(slot3_matches)} matches")

        # SLOT 4: Gemini Batch
        print("[Step 1] Running Slot 4 batch pre-filter...")
        slot4_matches = gemini.prefilter_batch_slot_4(slot_batches[4], yesterday_data['headlines'])
        for match in slot4_matches:
            sid = match.get('story_id')
            if sid:
                if sid not in story_slots:
                    story_slots[sid] = set()
                story_slots[sid].add(4)
        print(f"[Step 1] Slot 4: {len(slot4_matches)} matches")

        # SLOT 5: Gemini Batch
        print("[Step 1] Running Slot 5 batch pre-filter...")
        slot5_matches = gemini.prefilter_batch_slot_5(slot_batches[5], yesterday_data['headlines'])
        for match in slot5_matches:
            sid = match.get('story_id')
            if sid:
                if sid not in story_slots:
                    story_slots[sid] = set()
                story_slots[sid].add(5)
        print(f"[Step 1] Slot 5: {len(slot5_matches)} matches")

        # =================================================================
        # PHASE 4: BUILD PRE-FILTER LOG RECORDS
        # =================================================================

        prefilter_records = []

        for story_id, eligible_slots in story_slots.items():
            if not eligible_slots:
                continue

            results["eligible"] += 1
            article_data = article_lookup.get(story_id, {})

            # Create one pre-filter log record per eligible slot
            for slot in sorted(eligible_slots):
                results["slot_counts"][slot] += 1
                record = {
                    "storyID": story_id,
                    "pivotId": article_data.get("pivot_id", ""),
                    "headline": article_data.get("headline", ""),
                    "core_url": article_data.get("core_url", ""),
                    "source_id": article_data.get("source_id", ""),
                    "date_og_published": article_data.get("date_og_published", ""),
                    "date_prefiltered": datetime.utcnow().strftime('%Y-%m-%d'),
                    "slot": str(slot)  # Airtable expects string for Single Select field
                }
                prefilter_records.append(record)

        # =================================================================
        # PHASE 5: BATCH WRITE TO AIRTABLE
        # =================================================================

        if prefilter_records:
            print(f"[Step 1] Writing {len(prefilter_records)} pre-filter records...")
            try:
                record_ids = airtable.write_prefilter_log_batch(prefilter_records)
                results["written"] = len(record_ids)
                print(f"[Step 1] Successfully wrote {len(record_ids)} records")
            except Exception as e:
                print(f"[Step 1] ERROR: Could not write pre-filter records: {e}")
                results["errors"].append({"write_error": str(e)})
                # Still report what would have been written
                results["would_have_written"] = len(prefilter_records)
                print(f"[Step 1] Would have written {len(prefilter_records)} records")

        print(f"[Step 1] Pre-filter complete:")
        print(f"  Processed: {results['processed']}")
        print(f"  Eligible stories: {results['eligible']}")
        print(f"  Records written: {results['written']}")
        print(f"  Skipped: {results['skipped']}")
        print(f"  Slot distribution: {results['slot_counts']}")

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


def _calculate_eligible_slots(freshness_hours: int) -> List[int]:
    """
    Pre-calculate which slots a story is eligible for based on freshness.
    This matches n8n workflow's "Prepare Candidates" node logic.

    Freshness Rules:
    - 0-24h: All slots (1, 2, 3, 4, 5)
    - 24-48h: Slots 2, 3, 4, 5
    - 48-72h: Slots 3, 4, 5
    - 72-168h (1 week): Slots 3, 5 only
    - >168h: No slots (too old)
    """
    if freshness_hours <= 24:
        return [1, 2, 3, 4, 5]
    elif freshness_hours <= 48:
        return [2, 3, 4, 5]
    elif freshness_hours <= 72:
        return [3, 4, 5]
    elif freshness_hours <= 168:
        return [3, 5]
    else:
        return []


def _slot1_company_filter_batch(articles: List[Dict]) -> List[str]:
    """
    Slot 1 Company Filter - runs in PARALLEL with Gemini.

    Scans all Slot 1 eligible articles for Tier 1 company mentions.
    Returns list of story_ids that match.

    Args:
        articles: List of article dicts with story_id, headline

    Returns:
        List of story_ids that mention Tier 1 companies
    """
    matches = []

    for article in articles:
        headline = article.get('headline', '').lower()
        story_id = article.get('story_id', '')

        for company in SLOT_1_COMPANIES:
            if company in headline:
                matches.append(story_id)
                break  # Only add once per article

    return matches


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
