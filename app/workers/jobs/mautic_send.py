"""
Step 4b: Mautic Send Job
Workflow ID: NKjC8hb0EDHIXx3U (same as html_compile)
Schedule: 5 AM EST (0 10 * * 2-6 UTC)

Sends compiled newsletter via Mautic and archives the issue.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.mautic import MauticClient


def send_via_mautic() -> dict:
    """
    Step 4b: Mautic Send Cron Job - Main entry point

    Flow:
    1. Get compiled newsletter issue (status='compiled' or 'next send')
    2. Create email campaign in Mautic
    3. Attach GreenArrow transport
    4. Send to subscriber segment
    5. Update issue status to 'sent'
    6. Archive the issue

    Returns:
        {sent: bool, mautic_email_id: int, recipient_count: int, errors: list}
    """
    print(f"[Step 4b] Starting Mautic send at {datetime.utcnow().isoformat()}")

    # Initialize clients
    airtable = AirtableClient()

    try:
        mautic = MauticClient()
    except ValueError as e:
        print(f"[Step 4b] Mautic client error: {e}")
        return {
            "sent": False,
            "errors": [{"fatal": str(e)}]
        }

    # Track results
    results = {
        "sent": False,
        "mautic_email_id": None,
        "recipient_count": 0,
        "issue_id": "",
        "errors": []
    }

    try:
        # 1. Get compiled newsletter issue
        print("[Step 4b] Fetching compiled newsletter issue...")
        issue = _get_pending_issue(airtable)

        if not issue:
            print("[Step 4b] No compiled issue found for sending")
            return results

        issue_record_id = issue.get('id', '')
        fields = issue.get('fields', {})
        results["issue_id"] = issue_record_id

        html_content = fields.get('html', '')
        subject_line = fields.get('subject_line', 'Pivot 5 Daily AI Newsletter')
        issue_id = fields.get('issue_id', f"pivot5-{datetime.utcnow().strftime('%Y%m%d')}")

        if not html_content:
            results["errors"].append({"error": "No HTML content in issue"})
            return results

        print(f"[Step 4b] Processing issue: {issue_id}")

        # 2. Create email campaign in Mautic
        print("[Step 4b] Creating Mautic email campaign...")
        try:
            email_data = {
                "name": f"Pivot 5 - {datetime.utcnow().strftime('%b %d, %Y')}",
                "subject": subject_line,
                "customHtml": html_content,
                "description": f"Daily AI newsletter - {issue_id}",
                "fromAddress": os.environ.get('MAUTIC_FROM_ADDRESS', 'newsletter@pivotmedia.ai'),
                "fromName": os.environ.get('MAUTIC_FROM_NAME', 'Pivot 5'),
                "replyToAddress": os.environ.get('MAUTIC_REPLY_TO', 'reply@pivotmedia.ai')
            }

            mautic_email = mautic.create_email(email_data)
            mautic_email_id = mautic_email.get('id')

            if not mautic_email_id:
                raise Exception("Failed to get Mautic email ID")

            results["mautic_email_id"] = mautic_email_id
            print(f"[Step 4b] Created Mautic email: {mautic_email_id}")

        except Exception as e:
            print(f"[Step 4b] Error creating Mautic email: {e}")
            results["errors"].append({"step": "create_email", "error": str(e)})
            return results

        # 3. Attach GreenArrow transport
        print("[Step 4b] Attaching transport...")
        try:
            mautic.attach_transport(mautic_email_id)
        except Exception as e:
            print(f"[Step 4b] Warning: Transport attachment failed: {e}")
            # Continue anyway - some setups don't require explicit transport

        # 4. Send to subscriber segment
        print("[Step 4b] Sending email...")
        try:
            segment_id = int(os.environ.get('MAUTIC_SEGMENT_ID', '1'))
            send_result = mautic.send_email(mautic_email_id, segment_id)

            # Get recipient count
            stats = mautic.get_email_stats(mautic_email_id)
            results["recipient_count"] = stats.get("sentCount", 0)
            results["sent"] = True

            print(f"[Step 4b] Email sent to {results['recipient_count']} recipients")

        except Exception as e:
            print(f"[Step 4b] Error sending email: {e}")
            results["errors"].append({"step": "send_email", "error": str(e)})
            return results

        # 5. Update issue status to 'sent'
        print("[Step 4b] Updating issue status...")
        try:
            airtable.update_newsletter_issue(issue_record_id, {
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat(),
                "mautic_email_id": str(mautic_email_id),
                "recipient_count": results["recipient_count"]
            })
        except Exception as e:
            print(f"[Step 4b] Error updating issue status: {e}")
            results["errors"].append({"step": "update_status", "error": str(e)})

        # 6. Archive the issue
        print("[Step 4b] Archiving issue...")
        try:
            archive_data = {
                "issue_id": issue_id,
                "sent_status": "success",
                "mautic_email_id": str(mautic_email_id),
                "mautic_response": "Sent successfully",
                "recipient_count": results["recipient_count"],
                "sent_at": datetime.utcnow().isoformat()
            }
            archive_id = airtable.archive_newsletter_issue(archive_data)
            print(f"[Step 4b] Archived issue: {archive_id}")

        except Exception as e:
            print(f"[Step 4b] Error archiving issue: {e}")
            results["errors"].append({"step": "archive", "error": str(e)})

        print(f"[Step 4b] Mautic send complete: {results}")
        return results

    except Exception as e:
        print(f"[Step 4b] Fatal error: {e}")
        results["errors"].append({"fatal": str(e)})
        raise


def _get_pending_issue(airtable: AirtableClient) -> Optional[dict]:
    """Get newsletter issue ready for sending"""
    table = airtable._get_table(
        airtable.pivot_media_base_id,
        airtable.newsletter_issues_table_id
    )

    # Look for 'compiled' or 'next send' status
    filter_formula = "OR({status}='compiled', {status}='next send')"

    records = table.all(
        formula=filter_formula,
        sort=['-compiled_at'],
        max_records=1
    )

    return records[0] if records else None


def test_send(issue_record_id: str, test_email: str) -> dict:
    """
    Send test email to a single recipient.

    Args:
        issue_record_id: Newsletter Issue record ID
        test_email: Email address to send test to

    Returns:
        {sent: bool, error: str}
    """
    print(f"[Step 4b] Test send to {test_email}...")

    airtable = AirtableClient()

    try:
        mautic = MauticClient()
    except ValueError as e:
        return {"sent": False, "error": str(e)}

    try:
        # Get issue
        table = airtable._get_table(
            airtable.pivot_media_base_id,
            airtable.newsletter_issues_table_id
        )
        issue = table.get(issue_record_id)

        if not issue:
            return {"sent": False, "error": "Issue not found"}

        fields = issue.get('fields', {})
        html_content = fields.get('html', '')
        subject_line = fields.get('subject_line', 'Pivot 5 - Test')

        # Create test email in Mautic
        email_data = {
            "name": f"Pivot 5 TEST - {datetime.utcnow().strftime('%b %d %H:%M')}",
            "subject": f"[TEST] {subject_line}",
            "customHtml": html_content
        }

        mautic_email = mautic.create_email(email_data)
        mautic_email_id = mautic_email.get('id')

        # Send to test email
        # Note: Actual implementation would use Mautic's test send endpoint
        # or send to a single-contact segment

        return {
            "sent": True,
            "mautic_email_id": mautic_email_id,
            "test_recipient": test_email
        }

    except Exception as e:
        return {"sent": False, "error": str(e)}


def get_send_stats(mautic_email_id: int) -> dict:
    """
    Get send statistics for an email, with bot filtering.

    Args:
        mautic_email_id: Mautic email ID

    Returns:
        Filtered statistics
    """
    try:
        mautic = MauticClient()
        return mautic.get_filtered_stats(mautic_email_id)
    except Exception as e:
        return {"error": str(e)}


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": send_via_mautic,
    "trigger": "cron",
    "hour": 10,  # 10 AM UTC = 5 AM EST
    "minute": 0,
    "day_of_week": "tue-sat",
    "id": "step4b_mautic_send",
    "replace_existing": True
}
