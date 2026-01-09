"""
Scheduled Send Checker Job
Schedule: Every 5 minutes

Checks for newsletters with status='scheduled' and sends them when
their scheduled_send_time has arrived.

This fills the gap between the "Schedule via Mautic" button (which stores
scheduling info in Airtable) and the actual send (via mautic_send.py).
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

import pytz

from utils.airtable import AirtableClient

logger = logging.getLogger(__name__)

# Timezone for logging
ET_TIMEZONE = pytz.timezone('America/New_York')


def check_scheduled_newsletters() -> Dict[str, Any]:
    """
    Check for scheduled newsletters and trigger sends when their time arrives.

    Process:
    1. Query Newsletter Issues Final for status='scheduled'
    2. For each, check if scheduled_send_time <= now
    3. If ready, update status to 'next-send' (mautic_send will pick it up)
    4. Optionally trigger mautic_send immediately

    Returns:
        {
            "checked_at": str,
            "found": int,
            "ready_to_send": int,
            "triggered": list[str],
            "not_yet_due": list[str],
            "errors": list
        }
    """
    now_utc = datetime.now(timezone.utc)
    now_et = datetime.now(ET_TIMEZONE)

    logger.info(f"[Scheduled Checker] Starting check at {now_et.strftime('%Y-%m-%d %H:%M:%S ET')}")

    results = {
        "checked_at": now_et.isoformat(),
        "found": 0,
        "ready_to_send": 0,
        "triggered": [],
        "not_yet_due": [],
        "errors": []
    }

    try:
        airtable = AirtableClient()

        # Get all scheduled newsletters
        scheduled = get_scheduled_newsletters(airtable)
        results["found"] = len(scheduled)

        if not scheduled:
            logger.info("[Scheduled Checker] No scheduled newsletters found")
            return results

        logger.info(f"[Scheduled Checker] Found {len(scheduled)} scheduled newsletter(s)")

        for record in scheduled:
            record_id = record.get('id', '')
            fields = record.get('fields', {})
            issue_id = fields.get('issue_id', 'Unknown')
            scheduled_time_str = fields.get('scheduled_send_time', '')

            if not scheduled_time_str:
                logger.warning(f"[Scheduled Checker] {issue_id}: No scheduled_send_time, skipping")
                results["errors"].append({
                    "issue_id": issue_id,
                    "error": "No scheduled_send_time field"
                })
                continue

            # Parse the scheduled time
            try:
                scheduled_time = parse_datetime(scheduled_time_str)
            except Exception as e:
                logger.error(f"[Scheduled Checker] {issue_id}: Failed to parse time '{scheduled_time_str}': {e}")
                results["errors"].append({
                    "issue_id": issue_id,
                    "error": f"Failed to parse scheduled_send_time: {e}"
                })
                continue

            # Check if it's time to send
            if scheduled_time <= now_utc:
                logger.info(f"[Scheduled Checker] {issue_id}: Ready to send (scheduled: {scheduled_time_str})")

                # Update status to 'next-send' so mautic_send.py picks it up
                try:
                    update_status_to_next_send(airtable, record_id, issue_id)
                    results["ready_to_send"] += 1
                    results["triggered"].append(issue_id)

                    # Immediately trigger mautic_send job
                    trigger_mautic_send(issue_id)

                except Exception as e:
                    logger.error(f"[Scheduled Checker] {issue_id}: Failed to trigger send: {e}")
                    results["errors"].append({
                        "issue_id": issue_id,
                        "error": str(e)
                    })
            else:
                # Not yet time
                time_until = scheduled_time - now_utc
                minutes_until = int(time_until.total_seconds() / 60)
                logger.info(f"[Scheduled Checker] {issue_id}: Not yet due ({minutes_until} minutes remaining)")
                results["not_yet_due"].append({
                    "issue_id": issue_id,
                    "scheduled_for": scheduled_time_str,
                    "minutes_until": minutes_until
                })

        logger.info(f"[Scheduled Checker] Complete - triggered: {len(results['triggered'])}, not yet due: {len(results['not_yet_due'])}")
        return results

    except Exception as e:
        logger.error(f"[Scheduled Checker] Fatal error: {e}", exc_info=True)
        results["errors"].append({"fatal": str(e)})
        return results


def get_scheduled_newsletters(airtable: AirtableClient) -> List[dict]:
    """
    Query Newsletter Issues Final for scheduled newsletters.

    Returns:
        List of Airtable records with status='scheduled'
    """
    # Access the Newsletter Issues Final table directly
    table = airtable._get_table(
        airtable.ai_editor_base_id,
        airtable.newsletter_issues_final_table_id
    )

    records = table.all(
        formula="{status}='scheduled'",
        fields=['issue_id', 'newsletter_id', 'scheduled_send_time', 'scheduled_at', 'status']
    )

    return records


def update_status_to_next_send(airtable: AirtableClient, record_id: str, issue_id: str) -> bool:
    """
    Update newsletter status from 'scheduled' to 'next-send'.

    This allows mautic_send.py to pick it up with its existing logic.
    """
    table = airtable._get_table(
        airtable.ai_editor_base_id,
        airtable.newsletter_issues_final_table_id
    )

    table.update(record_id, {
        'status': 'next-send'
    })

    logger.info(f"[Scheduled Checker] Updated {issue_id} status to 'next-send'")
    return True


def trigger_mautic_send(issue_id: str) -> None:
    """
    Immediately queue the mautic_send job.

    This ensures the newsletter is sent right away rather than waiting
    for the next scheduled mautic_send cron (5 AM).
    """
    try:
        import os
        from redis import Redis
        from rq import Queue
        from jobs.mautic_send import send_via_mautic

        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        conn = Redis.from_url(redis_url)
        queue = Queue('high', connection=conn)

        job = queue.enqueue(send_via_mautic)
        logger.info(f"[Scheduled Checker] Queued mautic_send job for {issue_id}: {job.id}")

    except Exception as e:
        # Log but don't fail - mautic_send will run on next cron
        logger.warning(f"[Scheduled Checker] Could not queue immediate send for {issue_id}: {e}")
        logger.info(f"[Scheduled Checker] {issue_id} will be sent on next mautic_send cron run")


def parse_datetime(dt_string: str) -> datetime:
    """
    Parse datetime string from Airtable (ISO format with Z suffix).

    Examples:
        "2026-01-09T10:00:00.000Z" -> datetime with UTC timezone
        "2026-01-09T05:00:00-05:00" -> datetime with offset
    """
    # Handle Z suffix (UTC)
    if dt_string.endswith('Z'):
        dt_string = dt_string.replace('Z', '+00:00')

    # Handle milliseconds
    if '.' in dt_string:
        # Remove milliseconds for parsing
        base, rest = dt_string.rsplit('.', 1)
        if '+' in rest:
            tz_part = '+' + rest.split('+')[1]
        elif '-' in rest and rest.rfind('-') > 0:
            tz_part = '-' + rest.rsplit('-', 1)[1]
        else:
            tz_part = '+00:00'
        dt_string = base + tz_part

    return datetime.fromisoformat(dt_string)


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": check_scheduled_newsletters,
    "trigger": "cron",
    "minute": "*/5",  # Every 5 minutes
    "id": "scheduled_send_checker",
    "replace_existing": True
}
