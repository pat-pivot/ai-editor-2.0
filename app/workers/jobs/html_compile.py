"""
Step 4: HTML Compile Job
Workflow ID: NKjC8hb0EDHIXx3U
Schedule: 10 PM EST (0 3 * * 2-6 UTC)

Compiles 5 decorated stories into HTML email template and writes
to Newsletter Issues table.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.claude import ClaudeClient


# Newsletter HTML template
EMAIL_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pivot 5 - {issue_date}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 640px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
        }}
        .header {{
            background-color: #ff6f00;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .tagline {{
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        .preheader {{
            display: none;
            max-height: 0;
            overflow: hidden;
        }}
        .story {{
            padding: 25px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .story:last-child {{
            border-bottom: none;
        }}
        .topic-label {{
            display: inline-block;
            background-color: #ff6f00;
            color: white;
            padding: 4px 10px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }}
        .headline {{
            font-size: 22px;
            font-weight: 700;
            color: #1a1a1a;
            margin: 0 0 10px 0;
            line-height: 1.3;
        }}
        .dek {{
            font-size: 16px;
            color: #555;
            margin: 0 0 15px 0;
        }}
        .story-image {{
            width: 100%;
            height: auto;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .bullets {{
            margin: 0;
            padding-left: 20px;
        }}
        .bullets li {{
            margin-bottom: 10px;
            font-size: 15px;
            color: #444;
        }}
        .read-more {{
            display: inline-block;
            color: #ff6f00;
            text-decoration: none;
            font-weight: 600;
            margin-top: 12px;
            font-size: 14px;
        }}
        .read-more:hover {{
            text-decoration: underline;
        }}
        .footer {{
            background-color: #f8f8f8;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
        }}
        .footer a {{
            color: #ff6f00;
            text-decoration: none;
        }}
        .unsubscribe {{
            margin-top: 15px;
        }}
        @media only screen and (max-width: 480px) {{
            body {{
                padding: 10px;
            }}
            .story {{
                padding: 20px 15px;
            }}
            .headline {{
                font-size: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="preheader">{preheader}</div>
    <div class="container">
        <div class="header">
            <h1>PIVOT 5</h1>
            <div class="tagline">5 headlines \u2022 5 minutes \u2022 5 days a week</div>
        </div>

        {stories_html}

        <div class="footer">
            <p>You're receiving this because you subscribed to Pivot 5.</p>
            <p class="unsubscribe">
                <a href="{{{{unsubscribe_url}}}}">Unsubscribe</a> |
                <a href="{{{{preferences_url}}}}">Manage Preferences</a>
            </p>
            <p>\u00a9 {year} Pivot Media. All rights reserved.</p>
        </div>
    </div>
</body>
</html>'''

STORY_TEMPLATE = '''
<div class="story">
    <span class="topic-label">{label}</span>
    <h2 class="headline">{headline}</h2>
    <p class="dek">{dek}</p>
    {image_html}
    <ul class="bullets">
        <li>{bullet_1}</li>
        <li>{bullet_2}</li>
        <li>{bullet_3}</li>
    </ul>
    <a href="{url}" class="read-more">Read More \u2192</a>
</div>
'''


def compile_html() -> dict:
    """
    Step 4: HTML Compile Cron Job - Main entry point

    Flow:
    1. Get decorated stories with image_status='generated'
    2. Sort by slot_order (1-5)
    3. Generate 15-word and 20-word summaries
    4. Compile HTML email template
    5. Write to Newsletter Issues table

    Returns:
        {compiled: bool, issue_id: str, html_length: int, errors: list}
    """
    print(f"[Step 4] Starting HTML compilation at {datetime.utcnow().isoformat()}")

    # Initialize clients
    airtable = AirtableClient()
    claude = ClaudeClient()

    # Track results
    results = {
        "compiled": False,
        "issue_id": "",
        "html_length": 0,
        "errors": []
    }

    try:
        # 1. Get decorated stories ready for compilation
        print("[Step 4] Fetching decorated stories...")
        decorations = airtable.get_decorations_for_compile(max_records=5)

        if not decorations:
            print("[Step 4] No stories ready for compilation")
            return results

        print(f"[Step 4] Found {len(decorations)} decorated stories")

        # 2. Sort by slot_order
        decorations.sort(key=lambda x: x.get('fields', {}).get('slot_order', 99))

        # 3. Extract headlines for summary generation
        headlines = [
            d.get('fields', {}).get('ai_headline', '')
            for d in decorations
        ]

        # Generate summaries
        print("[Step 4] Generating summaries...")
        try:
            summary_15 = claude.generate_summary(headlines, max_words=15)
            summary_20 = claude.generate_summary(headlines, max_words=20)
            print(f"[Step 4] Summary (15): {summary_15}")
        except Exception as e:
            print(f"[Step 4] Summary generation failed: {e}")
            summary_15 = ""
            summary_20 = ""
            results["errors"].append({"step": "summary", "error": str(e)})

        # 4. Build stories HTML
        print("[Step 4] Compiling stories HTML...")
        stories_html_parts = []

        for decoration in decorations:
            fields = decoration.get('fields', {})

            # Build image HTML if available
            image_url = fields.get('image_url', '')
            image_html = ''
            if image_url:
                image_html = f'<img src="{image_url}" alt="" class="story-image" />'

            # Apply story template
            story_html = STORY_TEMPLATE.format(
                label=fields.get('label', 'AI NEWS'),
                headline=fields.get('ai_headline', ''),
                dek=fields.get('ai_dek', ''),
                image_html=image_html,
                bullet_1=fields.get('ai_bullet_1', ''),
                bullet_2=fields.get('ai_bullet_2', ''),
                bullet_3=fields.get('ai_bullet_3', ''),
                url=fields.get('original_url', '#')
            )
            stories_html_parts.append(story_html)

        stories_html = '\n'.join(stories_html_parts)

        # 5. Get subject line from selected slots
        subject_line = _get_subject_line(airtable)
        if not subject_line:
            subject_line = f"Pivot 5: {headlines[0][:40]}..." if headlines else "Pivot 5 Daily AI Newsletter"

        # Build full HTML
        issue_date = datetime.utcnow().strftime('%b %d, %Y')
        full_html = EMAIL_TEMPLATE.format(
            issue_date=issue_date,
            preheader=summary_15 or subject_line,
            stories_html=stories_html,
            year=datetime.utcnow().year
        )

        results["html_length"] = len(full_html)
        print(f"[Step 4] HTML compiled: {len(full_html)} characters")

        # 6. Write to Newsletter Issues table
        print("[Step 4] Writing to Newsletter Issues table...")
        issue_data = {
            "issue_id": f"pivot5-{datetime.utcnow().strftime('%Y%m%d')}",
            "newsletter_id": "pivot_ai",
            "html": full_html,
            "subject_line": subject_line,
            "summary": summary_15,
            "summary_plus": summary_20,
            "status": "compiled",
            "compiled_at": datetime.utcnow().isoformat()
        }

        record_id = airtable.write_newsletter_issue(issue_data)
        results["issue_id"] = record_id
        results["compiled"] = True

        print(f"[Step 4] Created Newsletter Issue: {record_id}")

        # 7. Update decoration records to mark as compiled
        print("[Step 4] Updating decoration statuses...")
        for decoration in decorations:
            try:
                airtable.update_decoration(decoration['id'], {
                    "compile_status": "compiled",
                    "newsletter_issue_id": record_id
                })
            except Exception as e:
                print(f"[Step 4] Error updating decoration: {e}")

        print(f"[Step 4] HTML compilation complete: {results}")
        return results

    except Exception as e:
        print(f"[Step 4] Fatal error: {e}")
        results["errors"].append({"fatal": str(e)})
        raise


def _get_subject_line(airtable: AirtableClient) -> Optional[str]:
    """Get subject line from latest selected slots record"""
    try:
        table = airtable._get_table(
            airtable.ai_editor_base_id,
            airtable.selected_slots_table_id
        )

        records = table.all(
            formula="OR({status}='pending', {status}='decorated')",
            sort=['-issue_date'],
            max_records=1,
            fields=['subject_line']
        )

        if records:
            return records[0].get('fields', {}).get('subject_line', '')

    except Exception as e:
        print(f"[Step 4] Error fetching subject line: {e}")

    return None


def preview_html(issue_id: str) -> Optional[str]:
    """
    Get HTML preview for a specific issue.

    Args:
        issue_id: Newsletter Issue record ID

    Returns:
        HTML string or None if not found
    """
    airtable = AirtableClient()

    try:
        table = airtable._get_table(
            airtable.pivot_media_base_id,
            airtable.newsletter_issues_table_id
        )

        record = table.get(issue_id)
        if record:
            return record.get('fields', {}).get('html', '')

    except Exception as e:
        print(f"[Step 4] Error fetching HTML preview: {e}")

    return None


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
