"""
Step 4a: HTML Compile Job
Workflow ID: NKjC8hb0EDHIXx3U
Schedule: 10 PM EST (0 3 * * 2-6 UTC)

Compiles 5 decorated stories into responsive HTML email template and writes
to Newsletter Issues Final table with status='next-send'.

Migrated from n8n 1/2/26 to match workflow exactly.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

import pytz

from utils.airtable import AirtableClient
from utils.claude import ClaudeClient
from utils.html_stripper import build_full_html_email

logger = logging.getLogger(__name__)

# Timezone for issue date formatting
ET_TIMEZONE = pytz.timezone('America/New_York')

# Default subject line fallback (from n8n workflow)
DEFAULT_SUBJECT_LINE = "5 headlines. 5 minutes. 5 days a week."


def get_next_issue_id() -> str:
    """
    Generate issue_id for the NEXT newsletter issue in format "Pivot 5 - MMM dd".

    Newsletter runs tonight for TOMORROW's issue (or Monday if Friday/Saturday).
    Uses zero-padded day format to match n8n workflow.
    Example: "Pivot 5 - Jan 05" (NOT "Jan 5")

    Returns:
        Issue ID string for next issue
    """
    from datetime import timedelta
    now_et = datetime.now(ET_TIMEZONE)
    weekday = now_et.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

    # Calculate next issue date (same logic as slot_selection.py)
    if weekday == 4:  # Friday -> Monday (skip Sat/Sun)
        next_issue = now_et + timedelta(days=3)
    elif weekday == 5:  # Saturday -> Monday (skip Sun)
        next_issue = now_et + timedelta(days=2)
    else:
        next_issue = now_et + timedelta(days=1)

    return f"Pivot 5 - {next_issue.strftime('%b %d')}"


def _detect_issue_id_from_decorated_stories(airtable: AirtableClient) -> Optional[str]:
    """
    Auto-detect issue_id from decorated stories with image_status='generated'.

    This fixes the date mismatch bug where Step 3 uses actual issue_date from
    Selected Slots, but Step 4 was calculating a future date.

    Args:
        airtable: AirtableClient instance

    Returns:
        issue_id string from decorated stories, or None if none found
    """
    try:
        # Query for ANY stories with image_status='generated' (no issue_id filter)
        # This uses the existing method that doesn't require issue_id
        records = airtable.get_decorations_for_compile(max_records=5)

        if not records:
            logger.info("[Step 4a] No decorated stories found for auto-detection")
            return None

        # Get issue_id from the first story
        first_story = records[0]
        issue_id = first_story.get('fields', {}).get('issue_id', '')

        if issue_id:
            logger.info(f"[Step 4a] Auto-detected issue_id: {issue_id} from {len(records)} decorated stories")
            return issue_id

        logger.warning("[Step 4a] Decorated stories found but no issue_id field")
        return None

    except Exception as e:
        logger.error(f"[Step 4a] Error detecting issue_id: {e}")
        return None


def compile_html(issue_id: Optional[str] = None) -> dict:
    """
    Step 4a: HTML Compile - Main entry point

    Matches n8n workflow nodes:
    - List2: Query Newsletter Issue Stories (image_status='generated')
    - prepare_issue_and_filter2: Group/filter complete issues
    - Fetch Subject Line: Get subject from Selected Slots
    - attach_issue_and_sort2: Sort by slot_order
    - Build Summary Prompt / Message a model: Generate summaries via Claude
    - compile_html_email2: Build responsive HTML
    - Strip HTML for Deliverability: Clean HTML for Mautic
    - Create a record: Write to Newsletter Issues Final (status='next-send')

    Args:
        issue_id: Optional specific issue ID. Defaults to auto-detect from decorated stories.

    Returns:
        {
            "compiled": bool,
            "issue_id": str,
            "subject_line": str,
            "html_length": int,
            "plain_html_length": int,
            "summary": str,
            "summary_plus": str,
            "record_id": str,
            "story_count": int,
            "errors": list
        }
    """
    # Initialize client early to detect issue_id if needed
    airtable = AirtableClient()

    # If no issue_id provided, find the most recent issue with decorated stories
    if issue_id:
        target_issue_id = issue_id
        logger.info(f"[Step 4a] Using provided issue_id: {target_issue_id}")
    else:
        # Query for any stories with image_status='generated' to find the issue_id
        target_issue_id = _detect_issue_id_from_decorated_stories(airtable)
        if not target_issue_id:
            # Fall back to calculated date if no decorated stories found
            target_issue_id = get_next_issue_id()
            logger.warning(f"[Step 4a] No decorated stories found, falling back to calculated date: {target_issue_id}")
        else:
            logger.info(f"[Step 4a] Auto-detected issue_id from decorated stories: {target_issue_id}")

    logger.info(f"[Step 4a] Starting HTML compilation for: {target_issue_id}")

    # Initialize Claude client (airtable already initialized above)
    claude = ClaudeClient()

    # Track results
    results = {
        "compiled": False,
        "issue_id": target_issue_id,
        "subject_line": "",
        "html_length": 0,
        "summary": "",
        "record_id": "",
        "story_count": 0,
        "errors": []
    }

    try:
        # =====================================================================
        # Step 1: Fetch decorated stories with image_status='generated'
        # Matches n8n node: List2
        # =====================================================================
        logger.info(f"[Step 4a] Fetching decorated stories for issue: {target_issue_id}")

        stories = airtable.get_decorated_stories_for_compile(target_issue_id)

        if not stories:
            error_msg = f"No stories with image_status='generated' found for {target_issue_id}"
            logger.warning(f"[Step 4a] {error_msg}")
            results["errors"].append({"step": "fetch_stories", "error": error_msg})
            return results

        results["story_count"] = len(stories)
        logger.info(f"[Step 4a] Found {len(stories)} decorated stories")

        # Check if we have all 5 stories
        if len(stories) < 5:
            logger.warning(f"[Step 4a] Only {len(stories)}/5 stories found. Proceeding anyway.")
            results["errors"].append({
                "step": "story_count",
                "warning": f"Only {len(stories)}/5 stories found"
            })

        # =====================================================================
        # Step 2: Sort stories by slot_order (1-5)
        # Matches n8n node: attach_issue_and_sort2
        # =====================================================================
        stories.sort(key=lambda x: x.get('fields', {}).get('slot_order', 99))
        logger.info(f"[Step 4a] Stories sorted by slot_order")

        # =====================================================================
        # Step 3: Fetch subject line from Selected Slots table
        # Matches n8n node: Fetch Subject Line
        # =====================================================================
        logger.info(f"[Step 4a] Fetching subject line...")

        subject_line = airtable.get_subject_line_for_issue(target_issue_id)

        if not subject_line:
            subject_line = DEFAULT_SUBJECT_LINE
            logger.warning(f"[Step 4a] No subject line found, using default: {subject_line}")
            results["errors"].append({
                "step": "subject_line",
                "warning": "Using default subject line"
            })

        results["subject_line"] = subject_line
        logger.info(f"[Step 4a] Subject line: {subject_line}")

        # =====================================================================
        # Step 4: Generate summary via Claude
        # Matches n8n nodes: Build Summary Prompt, Message a model, Parse Summaries
        # =====================================================================
        logger.info(f"[Step 4a] Generating summary via Claude...")

        try:
            summaries = _generate_summaries(claude, stories)
            results["summary"] = summaries.get("summary", "")
            logger.info(f"[Step 4a] Summary: {results['summary']}")
        except Exception as e:
            error_msg = f"Summary generation failed: {e}"
            logger.error(f"[Step 4a] {error_msg}")
            results["errors"].append({"step": "summary", "error": str(e)})
            # Continue without summaries

        # =====================================================================
        # Step 5: Compile responsive HTML email
        # Matches n8n node: compile_html_email2
        # =====================================================================
        logger.info(f"[Step 4a] Compiling responsive HTML email...")

        full_html = build_full_html_email(
            stories=stories,
            subject_line=subject_line,
            summary=results["summary"],
            include_images=True
        )

        results["html_length"] = len(full_html)
        logger.info(f"[Step 4a] Full HTML compiled: {len(full_html)} chars")

        # =====================================================================
        # Step 6: Create record in Newsletter Issues Final (status='next-send')
        # Matches n8n node: Create a record
        # =====================================================================
        logger.info(f"[Step 4a] Creating record in Newsletter Issues Final...")

        # Get current timestamp in ET
        now_et = datetime.now(ET_TIMEZONE)

        issue_data = {
            "issue_id": target_issue_id,
            "newsletter_id": "pivot_ai",
            "html": full_html,
            "subject_line": subject_line,
            "summary": results["summary"],
            "status": "next-send",
        }

        record = airtable.create_newsletter_issue_final(issue_data)
        results["record_id"] = record.get("id", "")
        results["compiled"] = True

        logger.info(f"[Step 4a] Created Newsletter Issue Final: {results['record_id']}")

        # =====================================================================
        # Success!
        # =====================================================================
        logger.info(f"[Step 4a] HTML compilation complete for {target_issue_id}")
        logger.info(f"[Step 4a] Results: {results}")

        return results

    except Exception as e:
        logger.error(f"[Step 4a] Fatal error: {e}", exc_info=True)
        results["errors"].append({"fatal": str(e)})
        raise


def _generate_summaries(claude: ClaudeClient, stories: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Generate 15-word and 20-word summaries using Claude.

    Matches n8n workflow summary generation:
    - summary: 15 words covering stories 1-3
    - summary_plus: 20 words covering all 5 stories

    Args:
        claude: Claude API client
        stories: List of decorated story records

    Returns:
        {"summary": str, "summary_plus": str}
    """
    # Extract headlines for summary generation
    headlines = []
    for story in stories:
        fields = story.get('fields', {})
        headline = fields.get('headline', '')
        if headline:
            headlines.append(headline)

    if not headlines:
        return {"summary": "", "summary_plus": ""}

    # Generate 15-word summary (first 3 stories)
    top_headlines = headlines[:3]
    summary_15 = claude.generate_summary(top_headlines, max_words=15)

    # Generate 20-word summary (all stories)
    summary_20 = claude.generate_summary(headlines, max_words=20)

    return {
        "summary": summary_15 or "",
        "summary_plus": summary_20 or ""
    }


def preview_html(issue_id: str) -> Optional[Dict[str, str]]:
    """
    Get HTML preview for a specific issue.

    Args:
        issue_id: Newsletter Issue record ID or issue_id string

    Returns:
        {"html": str, "plain_html": str, "subject_line": str} or None if not found
    """
    airtable = AirtableClient()

    try:
        # Try to get from Newsletter Issues Final
        record = airtable.get_newsletter_issue_for_send()

        if record:
            fields = record.get('fields', {})
            return {
                "html": fields.get('html', ''),
                "plain_html": fields.get('plain_html', ''),
                "subject_line": fields.get('subject_line', ''),
                "issue_id": fields.get('issue_id', ''),
                "status": fields.get('status', '')
            }

    except Exception as e:
        logger.error(f"[Step 4a] Error fetching HTML preview: {e}")

    return None


def recompile_for_issue(issue_id: str) -> dict:
    """
    Recompile HTML for a specific issue.

    Use this to regenerate HTML for a past or future issue.

    Args:
        issue_id: Issue ID (e.g., "Pivot 5 - Jan 02")

    Returns:
        Same as compile_html()
    """
    logger.info(f"[Step 4a] Recompiling for specific issue: {issue_id}")
    return compile_html(issue_id=issue_id)


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": compile_html,
    "trigger": "cron",
    "hour": 3,   # 3 AM UTC = 10 PM EST
    "minute": 0,
    "day_of_week": "tue-sat",
    "id": "step4_html_compile",
    "replace_existing": True
}
