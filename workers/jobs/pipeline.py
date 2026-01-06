"""
Chained Pipeline Job for AI Editor 2.0

Executes the full pipeline as a single chained job:
  1. Ingest (Step 0) - Fetch articles from FreshRSS, decode Google News URLs
  2. Direct Feed Ingest (Step 0a) - Ingest non-Google News RSS feeds
  3. AI Scoring (Step 0.5) - Score articles with Claude, create Newsletter Selects
  4. Pre-Filter (Step 1) - Run all 5 slots sequentially with Gemini

CHAINED EXECUTION:
  - Each step runs only after the previous completes
  - Direct Feed Ingest runs after Google News ingest (processes different URLs)
  - AI Scoring only runs if new articles were ingested (from either source)
  - Pre-Filter runs regardless (picks up any pending Newsletter Selects)
  - Each slot writes to Airtable immediately (crash-safe)

CRON SCHEDULE (see render.yaml):
  Cycle 1: 2:00 AM ET (7:00 UTC) - Overnight/international
  Cycle 2: 9:30 AM ET (14:30 UTC) - Morning publications
  Cycle 3: 5:00 PM ET (22:00 UTC) - End-of-day stories

Each cycle takes ~3-4 hours to complete (Ingest + Direct Feeds + Scoring + PreFilter).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# EST timezone for logging
EST = ZoneInfo("America/New_York")


def run_full_pipeline() -> dict:
    """
    Execute the complete pipeline as a single chained job.
    Each step runs only after the previous completes.

    Pipeline Flow:
      1. Ingest → Fetches articles from FreshRSS (Google News URLs)
      2. Direct Feed Ingest → Fetches non-Google News RSS feeds
      3. AI Scoring → Scores articles (only if either ingest found new articles)
      4. Pre-Filter → Runs all 5 slots sequentially

    Returns:
        Results dict with timing and counts from each step
    """
    pipeline_start = datetime.now(EST)
    print(f"[Pipeline] ===== STARTING FULL PIPELINE =====")
    print(f"[Pipeline] Start time: {pipeline_start.strftime('%Y-%m-%d %I:%M %p ET')}")
    print(f"[Pipeline] Chain: Ingest → Direct Feeds → AI Scoring → Pre-Filter (5 slots)")

    results = {
        "pipeline_started_at": pipeline_start.isoformat(),
        "ingest": None,
        "direct_feeds": None,
        "ai_scoring": None,
        "pre_filter": None,
        "pipeline_completed_at": None,
        "total_duration_seconds": None,
        "status": "running"
    }

    try:
        # =====================================================================
        # STEP 0: INGEST
        # Fetch articles from FreshRSS, decode Google News URLs
        # =====================================================================
        print(f"\n[Pipeline] ----- STEP 0: INGEST -----")
        step_start = datetime.now(EST)

        from jobs.ingest_sandbox import ingest_articles_sandbox
        ingest_result = ingest_articles_sandbox()
        results["ingest"] = ingest_result

        articles_ingested = ingest_result.get("articles_ingested", 0)
        step_duration = (datetime.now(EST) - step_start).total_seconds()
        print(f"[Pipeline] Ingest complete in {step_duration:.1f}s")
        print(f"[Pipeline] → Articles fetched: {ingest_result.get('articles_fetched', 0)}")
        print(f"[Pipeline] → Articles ingested: {articles_ingested}")
        print(f"[Pipeline] → Google News resolved: {ingest_result.get('google_news_resolved', 0)}")
        print(f"[Pipeline] → Duplicates skipped: {ingest_result.get('articles_skipped_duplicate', 0)}")

        # =====================================================================
        # STEP 0a: DIRECT FEED INGEST
        # Fetch non-Google News RSS feeds (Reuters, TechCrunch, etc.)
        # Runs AFTER Google News ingest to avoid being skipped
        # =====================================================================
        print(f"\n[Pipeline] ----- STEP 0a: DIRECT FEED INGEST -----")
        step_start = datetime.now(EST)

        from jobs.ingest_direct_feeds import ingest_direct_feeds
        direct_feeds_result = ingest_direct_feeds()
        results["direct_feeds"] = direct_feeds_result

        direct_feeds_ingested = direct_feeds_result.get("articles_ingested", 0)
        step_duration = (datetime.now(EST) - step_start).total_seconds()
        print(f"[Pipeline] Direct Feeds complete in {step_duration:.1f}s")
        print(f"[Pipeline] → Direct feeds found: {direct_feeds_result.get('direct_feeds_found', 0)}")
        print(f"[Pipeline] → Articles ingested: {direct_feeds_ingested}")
        print(f"[Pipeline] → Google News skipped: {direct_feeds_result.get('google_news_skipped', 0)}")
        print(f"[Pipeline] → Duplicates skipped: {direct_feeds_result.get('articles_skipped_duplicate', 0)}")

        # Total articles from both ingest steps
        total_ingested = articles_ingested + direct_feeds_ingested

        # =====================================================================
        # STEP 0.5: AI SCORING
        # Score articles with Claude, create Newsletter Selects
        # Only runs if new articles were ingested (from either source)
        # =====================================================================
        print(f"\n[Pipeline] ----- STEP 0.5: AI SCORING -----")

        if total_ingested > 0:
            step_start = datetime.now(EST)
            print(f"[Pipeline] Running AI Scoring for {total_ingested} new articles...")

            from jobs.ai_scoring_sandbox import run_ai_scoring_sandbox
            scoring_result = run_ai_scoring_sandbox()
            results["ai_scoring"] = scoring_result

            step_duration = (datetime.now(EST) - step_start).total_seconds()
            print(f"[Pipeline] AI Scoring complete in {step_duration:.1f}s")
            print(f"[Pipeline] → Articles scored: {scoring_result.get('articles_scored', 0)}")
            print(f"[Pipeline] → High-interest: {scoring_result.get('high_interest_count', 0)}")
            print(f"[Pipeline] → Newsletter Selects created: {scoring_result.get('newsletter_selects_created', 0)}")
        else:
            print(f"[Pipeline] Skipping AI Scoring (no new articles ingested)")
            results["ai_scoring"] = {"skipped": True, "reason": "no_new_articles"}

        # =====================================================================
        # STEP 1: PRE-FILTER
        # Run all 5 slots sequentially with Gemini
        # Writes to Airtable after each slot (crash-safe)
        # =====================================================================
        print(f"\n[Pipeline] ----- STEP 1: PRE-FILTER (5 slots) -----")
        step_start = datetime.now(EST)

        from jobs.prefilter import prefilter_stories
        prefilter_result = prefilter_stories()
        results["pre_filter"] = prefilter_result

        step_duration = (datetime.now(EST) - step_start).total_seconds()
        print(f"[Pipeline] Pre-Filter complete in {step_duration:.1f}s")
        print(f"[Pipeline] → Stories processed: {prefilter_result.get('processed', 0)}")
        print(f"[Pipeline] → Eligible stories: {prefilter_result.get('eligible', 0)}")
        print(f"[Pipeline] → Records written: {prefilter_result.get('written', 0)}")
        print(f"[Pipeline] → Slot counts: {prefilter_result.get('slot_counts', {})}")

        results["status"] = "completed"

    except Exception as e:
        import traceback
        print(f"\n[Pipeline] !!!!! PIPELINE ERROR !!!!!")
        print(f"[Pipeline] Error: {e}")
        print(f"[Pipeline] Traceback:\n{traceback.format_exc()}")
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()
        results["status"] = "failed"
        raise

    finally:
        pipeline_end = datetime.now(EST)
        duration = (pipeline_end - pipeline_start).total_seconds()
        results["pipeline_completed_at"] = pipeline_end.isoformat()
        results["total_duration_seconds"] = duration

        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        print(f"\n[Pipeline] ===== PIPELINE {'COMPLETE' if results['status'] == 'completed' else 'FAILED'} =====")
        print(f"[Pipeline] End time: {pipeline_end.strftime('%Y-%m-%d %I:%M %p ET')}")
        print(f"[Pipeline] Duration: {hours}h {minutes}m {seconds}s ({duration:.1f}s total)")

        # Summary stats
        ingest = results.get("ingest") or {}
        direct_feeds = results.get("direct_feeds") or {}
        scoring = results.get("ai_scoring") or {}
        prefilter = results.get("pre_filter") or {}

        print(f"[Pipeline] SUMMARY:")
        print(f"  Ingest (Google News): {ingest.get('articles_ingested', 0)} articles")
        print(f"  Direct Feeds:         {direct_feeds.get('articles_ingested', 0)} articles")
        print(f"  AI Scoring:           {scoring.get('articles_scored', 0) if not scoring.get('skipped') else 'skipped'}")
        print(f"  Pre-Filter:           {prefilter.get('written', 0)} records to Airtable")
        print(f"[Pipeline] ============================================")

    return results


# Job configuration for RQ scheduler (if used via worker.py)
JOB_CONFIG = {
    "func": run_full_pipeline,
    "trigger": "cron",
    "hour": 7,  # 2 AM ET = 7 AM UTC (Cycle 1)
    "minute": 0,
    "id": "pipeline_full",
    "replace_existing": True
}
