"""
Step 1: Pre-Filter Job
Workflow ID: VoSZu0MIJAw1IuLL
Schedule: 9:00 PM EST (0 2 * * 2-6 UTC)

ARCHITECTURE:
- 5 separate AI calls (one per slot) with slot-specific prompts
- Each slot gets ALL articles as a BATCH for TOPIC-based filtering
- Slot 1 Company Filter runs IN PARALLEL with AI Slot 1
- Response format: {matches: [{story_id, headline}]}

FIX (1/9/26): Removed freshness-based slot eligibility filtering
- Step 1 filters by TOPIC only (via AI prompts)
- Step 2 (Slot Selection) handles FRESHNESS filtering
- All articles go to all 5 slots for topic evaluation

TEMPORARY (1/6/26): Using Claude Sonnet 4.5 instead of Gemini (quota exhausted)
TODO(gemini-quota): Set PREFILTER_MODEL=gemini to revert when quota restored
See docs/Gemini-Temporary-Swap-1-6-26.md for details
"""

import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any, Set
from zoneinfo import ZoneInfo

from utils.airtable import AirtableClient

# TEMPORARY: Use Claude instead of Gemini (Gemini quota exhausted 1/6/26)
# TODO(gemini-quota): Set PREFILTER_MODEL=gemini to revert when quota restored
PREFILTER_MODEL = os.environ.get('PREFILTER_MODEL', 'claude').lower()

if PREFILTER_MODEL == 'gemini':
    from utils.gemini import GeminiClient as PrefilterClient
    PREFILTER_CLIENT_NAME = "Gemini"
else:
    from utils.claude_prefilter import ClaudePrefilterClient as PrefilterClient
    PREFILTER_CLIENT_NAME = "Claude (TEMPORARY)"

# Tier 1 companies for Slot 1 Company Filter (runs parallel to Gemini)
# Updated 12/26/25: Reduced to 4 companies to match n8n workflow (line 1262)
SLOT_1_COMPANIES = ['openai', 'google', 'meta', 'nvidia']


def prefilter_stories(lookback_hours: int = 10) -> dict:
    """
    Step 1: Pre-Filter Cron Job - Main entry point

    BATCH PROCESSING FLOW (matches n8n exactly):
    1. Get fresh stories from Newsletter Stories (last N hours)
    2. Get queued stories from AI Editor base
    3. Merge story sources
    4. Get source credibility scores
    5. Get yesterday's issue for diversity + exclusion
    6. Build article batch with freshness pre-calculation
    7. Run 5 BATCH Gemini calls (one per slot)
    8. Run Slot 1 Company Filter in parallel
    9. Merge all results
    10. Write eligible stories to Pre-Filter Log (one record per slot)

    Args:
        lookback_hours: How many hours back to look for stories.
                       Default 10h for cron (covers ~7.5h between pipeline cycles + buffer).
                       Use 24h for manual dashboard execution.

    Returns:
        {processed: int, eligible: int, written: int, errors: list}
    """
    print(f"[Step 1] Starting pre-filter job at {datetime.utcnow().isoformat()}", flush=True)
    print(f"[Step 1] Lookback window: {lookback_hours} hours", flush=True)
    print("[Step 1] Using BATCH PROCESSING architecture (matches n8n)", flush=True)

    # Initialize clients
    airtable = AirtableClient()
    # TEMPORARY: Using Claude instead of Gemini (quota exhausted 1/6/26)
    print(f"[Step 1] PREFILTER_MODEL={PREFILTER_MODEL} → Using {PREFILTER_CLIENT_NAME}", flush=True)
    prefilter_client = PrefilterClient()

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

        # 1. Get fresh stories from Newsletter Selects table (AI Editor 2.0 base)
        # Updated 12/31/25: Migrated from Newsletter Stories to Newsletter Selects
        # This is the FreshRSS data source with pre-processed articles
        # Updated 1/5/26: Use lookback_hours parameter (10h cron, 24h manual)
        print("[Step 1] Fetching stories from Newsletter Selects...", flush=True)
        lookback_datetime = datetime.utcnow() - timedelta(hours=lookback_hours)
        lookback_date_str = lookback_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        print(f"[Step 1] Date filter: since {lookback_date_str} ({lookback_hours} hours ago)", flush=True)
        fresh_stories = airtable.get_newsletter_selects(since_date=lookback_date_str)
        print(f"[Step 1] Found {len(fresh_stories)} stories from Newsletter Selects", flush=True)

        # 2. Get queued stories (manual priority) - optional, may not have API access
        print("[Step 1] Fetching queued stories...", flush=True)
        try:
            queued_stories = airtable.get_queued_stories()
            print(f"[Step 1] Found {len(queued_stories)} queued stories", flush=True)
        except Exception as e:
            print(f"[Step 1] Warning: Could not fetch queued stories (API access issue): {e}", flush=True)
            queued_stories = []

        # 3. Merge story sources (queued have priority)
        all_stories = _merge_stories(fresh_stories, queued_stories)
        print(f"[Step 1] Total stories to process: {len(all_stories)}", flush=True)

        # 4. Source credibility lookup - disabled (method removed)
        source_lookup = {}

        # 5. Get yesterday's issue for diversity rules + exclusion - optional
        print("[Step 1] Fetching yesterday's issue...", flush=True)
        try:
            yesterday_issue = airtable.get_yesterday_issue()
            yesterday_data = _extract_yesterday_data(yesterday_issue)
            print(f"[Step 1] Yesterday's headlines: {len(yesterday_data['headlines'])}", flush=True)
        except Exception as e:
            print(f"[Step 1] Warning: Could not fetch yesterday's issue (API access issue): {e}", flush=True)
            yesterday_data = {"headlines": [], "storyIds": [], "pivotIds": [], "slot1Headline": None}

        # Build yesterday's storyId exclusion set
        yesterday_story_ids = set(yesterday_data['storyIds'])
        print(f"[Step 1] Excluding {len(yesterday_story_ids)} stories from yesterday's issue", flush=True)

        # 6. Get article details for source lookup
        pivot_ids = [s.get('fields', {}).get('pivotId') for s in all_stories if s.get('fields', {}).get('pivotId')]
        print(f"[Step 1] Fetching article details for {len(pivot_ids)} pivot IDs...", flush=True)
        articles_lookup = airtable.get_articles_batch(pivot_ids)
        print(f"[Step 1] Loaded {len(articles_lookup)} article details", flush=True)

        # =================================================================
        # PHASE 2: BUILD ARTICLE BATCHES FOR ALL SLOTS
        # =================================================================
        # FIX (1/9/26): Step 1 evaluates ALL articles for ALL slots by TOPIC.
        # Freshness filtering is Step 2's responsibility (Slot Selection).
        # Every article fetched by Step 1 is "new" (within 10h of AI processing).
        # Old articles were already pre-filtered in previous Step 1 runs.

        # All articles go to ALL 5 slots - no freshness-based slot filtering
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

            # Get source credibility - prioritize Newsletter Selects fields
            source_id = fields.get('source_id', '') or article_fields.get('source_id', '')
            source_score = source_lookup.get(source_id.lower(), 3) if source_id else 3

            # Skip low-credibility sources
            if source_score < 2:
                results["skipped"] += 1
                continue

            # Calculate freshness hours (for informational purposes only)
            date_og_published = fields.get('date_og_published', '')
            hours_ago = _calculate_hours_ago(date_og_published)

            # Build headline (prefer ai_headline)
            headline = fields.get('ai_headline', '') or fields.get('headline', '')
            # Get core_url - prioritize Newsletter Selects fields
            core_url = fields.get('core_url', '') or article_fields.get('core_url', '') or article_fields.get('original_url', '')

            # Build summary from bullets (n8n Gap #3)
            summary_parts = [
                fields.get('ai_dek', ''),
                fields.get('ai_bullet_1', ''),
                fields.get('ai_bullet_2', ''),
                fields.get('ai_bullet_3', '')
            ]
            summary = ' | '.join(p for p in summary_parts if p)

            # Build article data for AI batch
            article_data = {
                "story_id": story_id,
                "pivot_id": pivot_id,
                "headline": headline,
                "summary": summary or fields.get('ai_dek', ''),
                "source_score": source_score,
                "freshness_hours": hours_ago,  # Kept for AI context, not for filtering
                "source_id": source_id,
                "core_url": core_url,
                "date_og_published": fields.get('date_og_published', ''),
                "topic": fields.get('topic', '')
            }

            # Store for later lookup
            article_lookup[story_id] = article_data

            # FIX (1/9/26): Add to ALL slot batches - no freshness filtering in Step 1
            # Step 1 filters by TOPIC (via AI prompts), Step 2 filters by FRESHNESS
            for slot in [1, 2, 3, 4, 5]:
                slot_batches[slot].append(article_data)

        print(f"[Step 1] ========== SLOT BATCH SUMMARY ==========", flush=True)
        for slot_num, batch in slot_batches.items():
            print(f"[Step 1] Slot {slot_num}: {len(batch)} articles eligible", flush=True)
        print(f"[Step 1] ==========================================", flush=True)

        # =================================================================
        # PHASE 3: RUN 5 BATCH GEMINI CALLS + INCREMENTAL AIRTABLE WRITES
        # Each slot writes immediately after processing (crash-safe)
        # =================================================================

        # Get current time in EST timezone for all records
        est = ZoneInfo("America/New_York")
        now_est = datetime.now(est)
        date_prefiltered_iso = now_est.isoformat()  # ISO 8601 format with EST timezone

        # Track which stories have been written (to avoid duplicates across slots)
        written_story_slot_pairs: Set[tuple] = set()

        def _write_slot_records(slot_num: int, matches: List[dict], source: str = "Gemini"):
            """
            Helper to build and write records for a slot immediately.
            Returns number of records written.
            """
            print(f"[Step 1] _write_slot_records called for Slot {slot_num} ({source}) with {len(matches)} matches", flush=True)

            slot_records = []
            skipped_no_sid = 0
            skipped_duplicate = 0

            for match in matches:
                sid = match.get('story_id')
                if not sid:
                    skipped_no_sid += 1
                    continue

                # Skip if we already wrote this story+slot combination
                pair = (sid, slot_num)
                if pair in written_story_slot_pairs:
                    skipped_duplicate += 1
                    continue
                written_story_slot_pairs.add(pair)

                article_data = article_lookup.get(sid, {})
                if not article_data:
                    print(f"[Step 1] WARNING: No article_lookup data for story_id={sid}", flush=True)

                record = {
                    "storyID": sid,
                    "pivotId": article_data.get("pivot_id", ""),
                    "headline": article_data.get("headline", ""),
                    "core_url": article_data.get("core_url", ""),
                    "source_id": article_data.get("source_id", ""),
                    "date_prefiltered": date_prefiltered_iso,
                    "slot": str(slot_num)
                }
                if article_data.get("date_og_published"):
                    record["date_og_published"] = article_data["date_og_published"]
                slot_records.append(record)
                results["slot_counts"][slot_num] += 1

            print(f"[Step 1] Slot {slot_num} ({source}): Built {len(slot_records)} records (skipped: {skipped_no_sid} no-sid, {skipped_duplicate} duplicates)", flush=True)

            if slot_records:
                print(f"[Step 1] Slot {slot_num} ({source}): Calling airtable.write_prefilter_log_batch with {len(slot_records)} records...", flush=True)
                try:
                    record_ids = airtable.write_prefilter_log_batch(slot_records)
                    results["written"] += len(record_ids)
                    print(f"[Step 1] Slot {slot_num} ({source}): ✓ SUCCESS - Wrote {len(record_ids)} records to Airtable", flush=True)
                    print(f"[Step 1] Slot {slot_num} ({source}): Record IDs: {record_ids[:5]}{'...' if len(record_ids) > 5 else ''}", flush=True)
                    return len(record_ids)
                except Exception as e:
                    print(f"[Step 1] Slot {slot_num} ({source}): ✗ ERROR writing to Airtable: {e}", flush=True)
                    print(f"[Step 1] Slot {slot_num} ({source}): Error type: {type(e).__name__}", flush=True)
                    results["errors"].append({"slot": slot_num, "source": source, "write_error": str(e)})
                    return 0
            else:
                print(f"[Step 1] Slot {slot_num} ({source}): No records to write (slot_records is empty)", flush=True)
            return 0

        # SLOT 1: AI Batch + Company Filter (parallel in n8n)
        print(f"[Step 1] ========== SLOT 1 PROCESSING ==========", flush=True)
        print(f"[Step 1] Slot 1 input batch size: {len(slot_batches[1])} articles", flush=True)
        print(f"[Step 1] Running Slot 1 {PREFILTER_CLIENT_NAME} batch pre-filter...", flush=True)
        try:
            slot1_ai_matches = prefilter_client.prefilter_batch_slot_1(slot_batches[1], yesterday_data['headlines'])
            print(f"[Step 1] Slot 1 {PREFILTER_CLIENT_NAME} returned: {len(slot1_ai_matches)} matches", flush=True)
            if slot1_ai_matches:
                print(f"[Step 1] Slot 1 {PREFILTER_CLIENT_NAME} first match: {slot1_ai_matches[0]}", flush=True)
            _write_slot_records(1, slot1_ai_matches, PREFILTER_CLIENT_NAME)
        except Exception as e:
            print(f"[Step 1] Slot 1 {PREFILTER_CLIENT_NAME} ERROR (continuing): {e}", flush=True)
            import traceback
            print(f"[Step 1] Slot 1 {PREFILTER_CLIENT_NAME} traceback: {traceback.format_exc()}", flush=True)
            results["errors"].append({"slot": 1, "source": PREFILTER_CLIENT_NAME, "error": str(e)})
            slot1_ai_matches = []

        # Slot 1 Company Filter (runs in parallel, merged with Gemini results)
        print("[Step 1] Running Slot 1 Company Filter...", flush=True)
        try:
            slot1_company_matches = _slot1_company_filter_batch(slot_batches[1])
            # Convert to match format for _write_slot_records
            slot1_company_match_dicts = [{"story_id": sid} for sid in slot1_company_matches]
            print(f"[Step 1] Slot 1 Company Filter returned: {len(slot1_company_matches)} matches", flush=True)
            _write_slot_records(1, slot1_company_match_dicts, "CompanyFilter")
        except Exception as e:
            print(f"[Step 1] Slot 1 Company Filter ERROR (continuing): {e}", flush=True)
            results["errors"].append({"slot": 1, "source": "CompanyFilter", "error": str(e)})
        print(f"[Step 1] ========== SLOT 1 COMPLETE ==========", flush=True)

        # SLOT 2: AI Batch
        print(f"[Step 1] ========== SLOT 2 PROCESSING ==========", flush=True)
        print(f"[Step 1] Slot 2 input batch size: {len(slot_batches[2])} articles", flush=True)
        print(f"[Step 1] Running Slot 2 {PREFILTER_CLIENT_NAME} batch pre-filter...", flush=True)
        try:
            slot2_matches = prefilter_client.prefilter_batch_slot_2(slot_batches[2], yesterday_data['headlines'])
            print(f"[Step 1] Slot 2 {PREFILTER_CLIENT_NAME} returned: {len(slot2_matches)} matches", flush=True)
            if slot2_matches:
                print(f"[Step 1] Slot 2 {PREFILTER_CLIENT_NAME} first match: {slot2_matches[0]}", flush=True)
            _write_slot_records(2, slot2_matches, PREFILTER_CLIENT_NAME)
        except Exception as e:
            print(f"[Step 1] Slot 2 ERROR (continuing): {e}", flush=True)
            import traceback
            print(f"[Step 1] Slot 2 traceback: {traceback.format_exc()}", flush=True)
            results["errors"].append({"slot": 2, "error": str(e)})
        print(f"[Step 1] ========== SLOT 2 COMPLETE ==========", flush=True)

        # SLOT 3: AI Batch
        print(f"[Step 1] ========== SLOT 3 PROCESSING ==========", flush=True)
        print(f"[Step 1] Slot 3 input batch size: {len(slot_batches[3])} articles", flush=True)
        print(f"[Step 1] Running Slot 3 {PREFILTER_CLIENT_NAME} batch pre-filter...", flush=True)
        try:
            slot3_matches = prefilter_client.prefilter_batch_slot_3(slot_batches[3], yesterday_data['headlines'])
            print(f"[Step 1] Slot 3 {PREFILTER_CLIENT_NAME} returned: {len(slot3_matches)} matches", flush=True)
            if slot3_matches:
                print(f"[Step 1] Slot 3 {PREFILTER_CLIENT_NAME} first match: {slot3_matches[0]}", flush=True)
            _write_slot_records(3, slot3_matches, PREFILTER_CLIENT_NAME)
        except Exception as e:
            print(f"[Step 1] Slot 3 ERROR (continuing): {e}", flush=True)
            import traceback
            print(f"[Step 1] Slot 3 traceback: {traceback.format_exc()}", flush=True)
            results["errors"].append({"slot": 3, "error": str(e)})
        print(f"[Step 1] ========== SLOT 3 COMPLETE ==========", flush=True)

        # SLOT 4: AI Batch
        print(f"[Step 1] ========== SLOT 4 PROCESSING ==========", flush=True)
        print(f"[Step 1] Slot 4 input batch size: {len(slot_batches[4])} articles", flush=True)
        print(f"[Step 1] Running Slot 4 {PREFILTER_CLIENT_NAME} batch pre-filter...", flush=True)
        try:
            slot4_matches = prefilter_client.prefilter_batch_slot_4(slot_batches[4], yesterday_data['headlines'])
            print(f"[Step 1] Slot 4 {PREFILTER_CLIENT_NAME} returned: {len(slot4_matches)} matches", flush=True)
            if slot4_matches:
                print(f"[Step 1] Slot 4 {PREFILTER_CLIENT_NAME} first match: {slot4_matches[0]}", flush=True)
            _write_slot_records(4, slot4_matches, PREFILTER_CLIENT_NAME)
        except Exception as e:
            print(f"[Step 1] Slot 4 ERROR (continuing): {e}", flush=True)
            import traceback
            print(f"[Step 1] Slot 4 traceback: {traceback.format_exc()}", flush=True)
            results["errors"].append({"slot": 4, "error": str(e)})
        print(f"[Step 1] ========== SLOT 4 COMPLETE ==========", flush=True)

        # SLOT 5: AI Batch
        print(f"[Step 1] ========== SLOT 5 PROCESSING ==========", flush=True)
        print(f"[Step 1] Slot 5 input batch size: {len(slot_batches[5])} articles", flush=True)
        print(f"[Step 1] Running Slot 5 {PREFILTER_CLIENT_NAME} batch pre-filter...", flush=True)
        try:
            slot5_matches = prefilter_client.prefilter_batch_slot_5(slot_batches[5], yesterday_data['headlines'])
            print(f"[Step 1] Slot 5 {PREFILTER_CLIENT_NAME} returned: {len(slot5_matches)} matches", flush=True)
            if slot5_matches:
                print(f"[Step 1] Slot 5 {PREFILTER_CLIENT_NAME} first match: {slot5_matches[0]}", flush=True)
            _write_slot_records(5, slot5_matches, PREFILTER_CLIENT_NAME)
        except Exception as e:
            print(f"[Step 1] Slot 5 ERROR (continuing): {e}", flush=True)
            import traceback
            print(f"[Step 1] Slot 5 traceback: {traceback.format_exc()}", flush=True)
            results["errors"].append({"slot": 5, "error": str(e)})
        print(f"[Step 1] ========== SLOT 5 COMPLETE ==========", flush=True)

        # Count unique eligible stories (each story may appear in multiple slots)
        unique_stories = set(pair[0] for pair in written_story_slot_pairs)
        results["eligible"] = len(unique_stories)

        print(f"[Step 1] ========== PRE-FILTER COMPLETE ==========", flush=True)
        print(f"[Step 1] Processed: {results['processed']}", flush=True)
        print(f"[Step 1] Eligible stories: {results['eligible']}", flush=True)
        print(f"[Step 1] Records written: {results['written']}", flush=True)
        print(f"[Step 1] Skipped: {results['skipped']}", flush=True)
        print(f"[Step 1] Slot distribution: {results['slot_counts']}", flush=True)
        if results['errors']:
            print(f"[Step 1] Errors encountered: {len(results['errors'])}", flush=True)
            for err in results['errors']:
                print(f"[Step 1]   - {err}", flush=True)
        print(f"[Step 1] ============================================", flush=True)

        return results

    except Exception as e:
        import traceback
        print(f"[Step 1] FATAL ERROR: {e}", flush=True)
        print(f"[Step 1] Traceback: {traceback.format_exc()}", flush=True)
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
        "slot1Headline": None  # Yesterday's Slot 1 headline for two-day company rotation
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

    # Slot 1 headline for two-day company rotation (Claude infers company from headline)
    data["slot1Headline"] = fields.get('slot_1_headline')

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


# =============================================================================
# INDIVIDUAL SLOT FUNCTIONS (for testing/debugging via dashboard)
# =============================================================================

def _gather_prefilter_data(lookback_hours: int = 24) -> dict:
    """
    Shared data gathering logic for all prefilter functions.
    Returns all the data needed to run any slot.

    Args:
        lookback_hours: How many hours back to look for stories.
                       Default 24h for manual dashboard execution.
    """
    print(f"[Prefilter] Gathering data at {datetime.utcnow().isoformat()}", flush=True)
    print(f"[Prefilter] Lookback window: {lookback_hours} hours", flush=True)

    airtable = AirtableClient()

    # 1. Get fresh stories from Newsletter Selects table
    # Updated 1/5/26: Use lookback_hours parameter (24h default for manual)
    print("[Prefilter] Fetching stories from Newsletter Selects...", flush=True)
    lookback_datetime = datetime.utcnow() - timedelta(hours=lookback_hours)
    lookback_date_str = lookback_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f"[Prefilter] Date filter: since {lookback_date_str} ({lookback_hours} hours ago)", flush=True)
    fresh_stories = airtable.get_newsletter_selects(since_date=lookback_date_str)
    print(f"[Prefilter] Found {len(fresh_stories)} stories from Newsletter Selects", flush=True)

    # 2. Get queued stories (manual priority)
    print("[Prefilter] Fetching queued stories...", flush=True)
    try:
        queued_stories = airtable.get_queued_stories()
        print(f"[Prefilter] Found {len(queued_stories)} queued stories", flush=True)
    except Exception as e:
        print(f"[Prefilter] Warning: Could not fetch queued stories: {e}", flush=True)
        queued_stories = []

    # 3. Merge story sources
    all_stories = _merge_stories(fresh_stories, queued_stories)
    print(f"[Prefilter] Total stories to process: {len(all_stories)}", flush=True)

    # 4. Source credibility lookup - disabled (method removed)
    source_lookup = {}

    # 5. Get yesterday's issue
    print("[Prefilter] Fetching yesterday's issue...", flush=True)
    try:
        yesterday_issue = airtable.get_yesterday_issue()
        yesterday_data = _extract_yesterday_data(yesterday_issue)
        print(f"[Prefilter] Yesterday's headlines: {len(yesterday_data['headlines'])}", flush=True)
    except Exception as e:
        print(f"[Prefilter] Warning: Could not fetch yesterday's issue: {e}", flush=True)
        yesterday_data = {"headlines": [], "storyIds": [], "pivotIds": [], "slot1Headline": None}

    yesterday_story_ids = set(yesterday_data['storyIds'])

    # 6. Get article details
    pivot_ids = [s.get('fields', {}).get('pivotId') for s in all_stories if s.get('fields', {}).get('pivotId')]
    print(f"[Prefilter] Fetching article details for {len(pivot_ids)} pivot IDs...", flush=True)
    articles_lookup = airtable.get_articles_batch(pivot_ids)
    print(f"[Prefilter] Loaded {len(articles_lookup)} article details", flush=True)

    # Build slot batches
    # FIX (1/9/26): ALL articles go to ALL slots - no freshness filtering in Step 1
    slot_batches: Dict[int, List[Dict]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    article_lookup: Dict[str, Dict] = {}
    processed = 0
    skipped = 0

    for story in all_stories:
        processed += 1
        fields = story.get('fields', {})
        story_id = fields.get('storyID', '')

        if story_id in yesterday_story_ids:
            skipped += 1
            continue

        pivot_id = fields.get('pivotId', '')
        article = articles_lookup.get(pivot_id, {})
        article_fields = article.get('fields', {}) if article else {}

        source_id = fields.get('source_id', '') or article_fields.get('source_id', '')
        source_score = source_lookup.get(source_id.lower(), 3) if source_id else 3

        if source_score < 2:
            skipped += 1
            continue

        date_og_published = fields.get('date_og_published', '')
        hours_ago = _calculate_hours_ago(date_og_published)

        headline = fields.get('ai_headline', '') or fields.get('headline', '')
        core_url = fields.get('core_url', '') or article_fields.get('core_url', '') or article_fields.get('original_url', '')

        summary_parts = [
            fields.get('ai_dek', ''),
            fields.get('ai_bullet_1', ''),
            fields.get('ai_bullet_2', ''),
            fields.get('ai_bullet_3', '')
        ]
        summary = ' | '.join(p for p in summary_parts if p)

        article_data = {
            "story_id": story_id,
            "pivot_id": pivot_id,
            "headline": headline,
            "summary": summary or fields.get('ai_dek', ''),
            "source_score": source_score,
            "freshness_hours": hours_ago,  # Kept for AI context, not for filtering
            "source_id": source_id,
            "core_url": core_url,
            "date_og_published": fields.get('date_og_published', ''),
            "topic": fields.get('topic', '')
        }

        article_lookup[story_id] = article_data

        # FIX (1/9/26): Add to ALL slot batches - Step 1 filters by TOPIC, Step 2 by FRESHNESS
        for slot in [1, 2, 3, 4, 5]:
            slot_batches[slot].append(article_data)

    print(f"[Prefilter] Data gathering complete. Processed: {processed}, Skipped: {skipped}", flush=True)
    for slot_num, batch in slot_batches.items():
        print(f"[Prefilter] Slot {slot_num}: {len(batch)} articles eligible", flush=True)

    return {
        "airtable": airtable,
        "slot_batches": slot_batches,
        "article_lookup": article_lookup,
        "yesterday_data": yesterday_data,
        "processed": processed,
        "skipped": skipped
    }


def _run_single_slot(slot_num: int) -> dict:
    """
    Run prefilter for a single slot.
    Used by individual slot functions for testing.
    """
    print(f"[Slot {slot_num}] ========== STARTING SINGLE SLOT PREFILTER ==========", flush=True)
    print(f"[Slot {slot_num}] Time: {datetime.utcnow().isoformat()}", flush=True)

    results = {
        "slot": slot_num,
        "processed": 0,
        "matches": 0,
        "written": 0,
        "errors": []
    }

    try:
        # Gather all data
        data = _gather_prefilter_data()
        airtable = data["airtable"]
        slot_batches = data["slot_batches"]
        article_lookup = data["article_lookup"]
        yesterday_data = data["yesterday_data"]
        results["processed"] = data["processed"]

        # Get current time in EST
        est = ZoneInfo("America/New_York")
        now_est = datetime.now(est)
        date_prefiltered_iso = now_est.isoformat()

        # Track written pairs
        written_story_slot_pairs: Set[tuple] = set()

        def write_records(matches: List[dict], source: str):
            """Write records to Airtable"""
            print(f"[Slot {slot_num}] Writing {len(matches)} {source} matches to Airtable...", flush=True)
            slot_records = []

            for match in matches:
                sid = match.get('story_id')
                if not sid:
                    continue
                pair = (sid, slot_num)
                if pair in written_story_slot_pairs:
                    continue
                written_story_slot_pairs.add(pair)

                article_data = article_lookup.get(sid, {})
                record = {
                    "storyID": sid,
                    "pivotId": article_data.get("pivot_id", ""),
                    "headline": article_data.get("headline", ""),
                    "core_url": article_data.get("core_url", ""),
                    "source_id": article_data.get("source_id", ""),
                    "date_prefiltered": date_prefiltered_iso,
                    "slot": str(slot_num)
                }
                if article_data.get("date_og_published"):
                    record["date_og_published"] = article_data["date_og_published"]
                slot_records.append(record)

            if slot_records:
                try:
                    record_ids = airtable.write_prefilter_log_batch(slot_records)
                    print(f"[Slot {slot_num}] ✓ Wrote {len(record_ids)} records ({source})", flush=True)
                    return len(record_ids)
                except Exception as e:
                    print(f"[Slot {slot_num}] ✗ Write error ({source}): {e}", flush=True)
                    results["errors"].append({"source": source, "error": str(e)})
                    return 0
            return 0

        # Initialize prefilter client (TEMPORARY: Claude instead of Gemini)
        print(f"[Slot {slot_num}] PREFILTER_MODEL={PREFILTER_MODEL} → Using {PREFILTER_CLIENT_NAME}", flush=True)
        prefilter_client = PrefilterClient()
        batch = slot_batches[slot_num]
        print(f"[Slot {slot_num}] Input batch size: {len(batch)} articles", flush=True)

        # Run slot-specific AI call (TEMPORARY: Claude instead of Gemini)
        if slot_num == 1:
            print(f"[Slot {slot_num}] Running {PREFILTER_CLIENT_NAME} batch prefilter...", flush=True)
            matches = prefilter_client.prefilter_batch_slot_1(batch, yesterday_data['headlines'])
            results["matches"] = len(matches)
            results["written"] += write_records(matches, PREFILTER_CLIENT_NAME)

            # Also run company filter for Slot 1
            print(f"[Slot {slot_num}] Running Company Filter...", flush=True)
            company_matches = _slot1_company_filter_batch(batch)
            company_match_dicts = [{"story_id": sid} for sid in company_matches]
            print(f"[Slot {slot_num}] Company Filter found {len(company_matches)} matches", flush=True)
            results["written"] += write_records(company_match_dicts, "CompanyFilter")

        elif slot_num == 2:
            print(f"[Slot {slot_num}] Running {PREFILTER_CLIENT_NAME} batch prefilter...", flush=True)
            matches = prefilter_client.prefilter_batch_slot_2(batch, yesterday_data['headlines'])
            results["matches"] = len(matches)
            results["written"] += write_records(matches, PREFILTER_CLIENT_NAME)

        elif slot_num == 3:
            print(f"[Slot {slot_num}] Running {PREFILTER_CLIENT_NAME} batch prefilter...", flush=True)
            matches = prefilter_client.prefilter_batch_slot_3(batch, yesterday_data['headlines'])
            results["matches"] = len(matches)
            results["written"] += write_records(matches, PREFILTER_CLIENT_NAME)

        elif slot_num == 4:
            print(f"[Slot {slot_num}] Running {PREFILTER_CLIENT_NAME} batch prefilter...", flush=True)
            matches = prefilter_client.prefilter_batch_slot_4(batch, yesterday_data['headlines'])
            results["matches"] = len(matches)
            results["written"] += write_records(matches, PREFILTER_CLIENT_NAME)

        elif slot_num == 5:
            print(f"[Slot {slot_num}] Running {PREFILTER_CLIENT_NAME} batch prefilter...", flush=True)
            matches = prefilter_client.prefilter_batch_slot_5(batch, yesterday_data['headlines'])
            results["matches"] = len(matches)
            results["written"] += write_records(matches, PREFILTER_CLIENT_NAME)

        print(f"[Slot {slot_num}] ========== COMPLETE ==========", flush=True)
        print(f"[Slot {slot_num}] Matches: {results['matches']}, Written: {results['written']}", flush=True)

    except Exception as e:
        import traceback
        print(f"[Slot {slot_num}] FATAL ERROR: {e}", flush=True)
        print(f"[Slot {slot_num}] Traceback: {traceback.format_exc()}", flush=True)
        results["errors"].append({"fatal": str(e)})
        raise

    return results


def prefilter_slot_1() -> dict:
    """Run prefilter for Slot 1 only (Breaking News)"""
    return _run_single_slot(1)


def prefilter_slot_2() -> dict:
    """Run prefilter for Slot 2 only (AI Research)"""
    return _run_single_slot(2)


def prefilter_slot_3() -> dict:
    """Run prefilter for Slot 3 only (Business/Industry)"""
    return _run_single_slot(3)


def prefilter_slot_4() -> dict:
    """Run prefilter for Slot 4 only (Product/Tool)"""
    return _run_single_slot(4)


def prefilter_slot_5() -> dict:
    """Run prefilter for Slot 5 only (Human Interest/Trend)"""
    return _run_single_slot(5)


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
