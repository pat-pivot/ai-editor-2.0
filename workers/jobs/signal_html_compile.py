"""
Signal Newsletter Step 4: HTML Compile Job

Compiles decorated Signal stories into responsive HTML email template.
Writes compiled HTML to Signal Selected Slots table with status='compiled'.

Key Differences from Pivot 5:
- NO LINKS (deliverability optimization)
- NO IMAGES (simplified production)
- Georgia 16px font (vs Arial 15px)
- Green accent #059669 (vs orange #f97316)
- 600px max width (vs 640px)
- 32px spacing (vs 24px)
- Different CSS classes (.signal-wrap, .sig-block vs .wrapper, .stack)

Structure:
1. Header with "SIGNAL" logo and date
2. At-a-Glance section (4 main stories + 5 signals as numbered list)
3. Full stories section (4 expanded treatments)

Created: January 13, 2026
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

import pytz

from utils.airtable import AirtableClient

logger = logging.getLogger(__name__)

# Timezone for issue date formatting
ET_TIMEZONE = pytz.timezone('America/New_York')

# Section display order for HTML compilation
# Matches signal_decoration.py SIGNAL_SECTIONS order
SIGNAL_SECTION_ORDER = [
    "top_story",
    "ai_at_work",
    "emerging_moves",
    "beyond_business",
    "signal_1",
    "signal_2",
    "signal_3",
    "signal_4",
    "signal_5"
]

# Section display names for HTML
SECTION_DISPLAY_NAMES = {
    "top_story": "TOP STORY",
    "ai_at_work": "AI AT WORK",
    "emerging_moves": "EMERGING MOVES",
    "beyond_business": "BEYOND BUSINESS",
}

# Default subject line for Signal
DEFAULT_SUBJECT_LINE = "Your daily AI briefing is ready"


def _log(msg: str, data: Any = None):
    """Enhanced logging with timestamp and optional data dump"""
    timestamp = datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
    print(f"[Signal Step 4][{timestamp}] {msg}")
    if data is not None:
        if isinstance(data, (dict, list)):
            print(f"[Signal Step 4][{timestamp}]   └─ {json.dumps(data, indent=2, default=str)[:2000]}")
        else:
            print(f"[Signal Step 4][{timestamp}]   └─ {str(data)[:500]}")


def _escape_html(text: str, preserve_bold: bool = True) -> str:
    """
    Escape HTML special characters, optionally preserving bold tags.

    Args:
        text: Text to escape
        preserve_bold: If True, preserve <b> and </b> tags

    Returns:
        HTML-escaped text with bold tags preserved if requested
    """
    if not text:
        return ""

    if preserve_bold:
        # Temporarily replace bold tags with placeholders
        text = text.replace('<b>', '___BOLD_OPEN___')
        text = text.replace('</b>', '___BOLD_CLOSE___')

    # Escape HTML special characters
    text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

    if preserve_bold:
        # Restore bold tags
        text = text.replace('___BOLD_OPEN___', '<b>')
        text = text.replace('___BOLD_CLOSE___', '</b>')

    return text


def _format_as_bullet_list(text: str) -> str:
    """
    Format text containing bullet points (• ) as HTML bullet list.

    The decoration output has bullets prefixed with "• " on separate lines.
    This converts them to styled HTML list items.

    Args:
        text: Text with bullet points (e.g., "• First point\n• Second point")

    Returns:
        HTML formatted bullet list
    """
    if not text:
        return ""

    # Split by bullet character and filter empty lines
    lines = text.split('• ')
    bullets = [line.strip() for line in lines if line.strip()]

    if not bullets:
        # No bullets found, return escaped text as-is
        return _escape_html(text, preserve_bold=True)

    # Build HTML bullet list
    bullet_items = []
    for bullet in bullets:
        escaped_bullet = _escape_html(bullet, preserve_bold=True)
        bullet_items.append(f'''
                    <tr>
                      <td valign="top" style="width:20px; font-family:Georgia, serif; font-size:15px; color:#059669; padding-right:8px;">&#8226;</td>
                      <td style="font-family:Georgia, serif; font-size:15px; color:#475569; line-height:1.7;">
                        {escaped_bullet}
                      </td>
                    </tr>''')

    return f'''<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0;">
                  {"".join(bullet_items)}
                  </table>'''


def compile_signal_html(issue_id: Optional[str] = None) -> dict:
    """
    Signal Step 4: HTML Compile - Main entry point

    Flow:
    1. Get decorated issue from Signal Selected Slots (status='decorated')
    2. Fetch decorated stories from Signal Issue Stories
    3. Build HTML with At-a-Glance + Full Stories sections
    4. Update issue status to 'compiled' and store HTML
    5. Return results

    Args:
        issue_id: Optional specific issue ID. Auto-detects if not provided.

    Returns:
        {
            "compiled": bool,
            "issue_id": str,
            "subject_line": str,
            "html_length": int,
            "story_count": int,
            "errors": list
        }
    """
    _log("=" * 60)
    _log("SIGNAL HTML COMPILE JOB STARTED")
    _log("=" * 60)

    # Initialize client
    _log("Initializing AirtableClient...")
    airtable = AirtableClient()
    _log(f"  Signal base: {airtable.signal_base_id}")

    # Track results
    results = {
        "compiled": False,
        "issue_id": "",
        "subject_line": "",
        "html_length": 0,
        "story_count": 0,
        "errors": []
    }

    try:
        # =====================================================================
        # Step 1: Find decorated issue
        # =====================================================================
        _log("-" * 40)
        _log("STEP 1: Finding decorated issue...")

        if issue_id:
            target_issue_id = issue_id
            _log(f"Using provided issue_id: {target_issue_id}")
            # Get the issue record
            issue = airtable.get_signal_issue_by_id(target_issue_id)
        else:
            # Auto-detect: find most recent decorated issue
            _log("Auto-detecting decorated issue...")
            issues = airtable.get_signal_recent_issues(lookback_days=7)
            decorated = [i for i in issues if i.get('fields', {}).get('status') == 'decorated']
            if decorated:
                issue = decorated[0]
                target_issue_id = issue.get('fields', {}).get('issue_id', '')
                _log(f"Found decorated issue: {target_issue_id}")
            else:
                _log("No decorated issues found")
                results["errors"].append({"step": "find_issue", "error": "No decorated issues found"})
                return results

        if not issue:
            _log(f"Issue not found: {target_issue_id}")
            results["errors"].append({"step": "find_issue", "error": f"Issue not found: {target_issue_id}"})
            return results

        issue_record_id = issue.get('id', '')
        issue_fields = issue.get('fields', {})
        results["issue_id"] = target_issue_id

        _log(f"  Record ID: {issue_record_id}")
        _log(f"  Issue ID: {target_issue_id}")
        _log(f"  Status: {issue_fields.get('status', 'unknown')}")

        # Get subject line
        subject_line = issue_fields.get('subject_line', '') or DEFAULT_SUBJECT_LINE
        results["subject_line"] = subject_line
        _log(f"  Subject line: {subject_line}")

        # Get issue date for header
        issue_date_str = issue_fields.get('issue_date', '')
        if issue_date_str:
            try:
                issue_date = datetime.fromisoformat(issue_date_str.replace('Z', '+00:00'))
                issue_date_display = issue_date.strftime('%B %d, %Y')
            except:
                issue_date_display = datetime.now(ET_TIMEZONE).strftime('%B %d, %Y')
        else:
            issue_date_display = datetime.now(ET_TIMEZONE).strftime('%B %d, %Y')

        _log(f"  Issue date display: {issue_date_display}")

        # =====================================================================
        # Step 2: Fetch decorated stories
        # =====================================================================
        _log("-" * 40)
        _log("STEP 2: Fetching decorated stories...")

        stories = airtable.get_signal_stories_for_compile(target_issue_id)

        if not stories:
            error_msg = f"No decorated stories found for {target_issue_id}"
            _log(error_msg)
            results["errors"].append({"step": "fetch_stories", "error": error_msg})
            return results

        results["story_count"] = len(stories)
        _log(f"Found {len(stories)} decorated stories")

        # Sort stories by section order
        def section_sort_key(story):
            section = story.get('fields', {}).get('section', '')
            try:
                return SIGNAL_SECTION_ORDER.index(section)
            except ValueError:
                return 999

        stories.sort(key=section_sort_key)
        _log(f"Stories sorted by section order")

        # Organize stories by section
        stories_by_section = {}
        for story in stories:
            section = story.get('fields', {}).get('section', '')
            stories_by_section[section] = story
            _log(f"  {section}: {story.get('fields', {}).get('headline', '')[:50]}...")

        # =====================================================================
        # Step 3: Build HTML
        # =====================================================================
        _log("-" * 40)
        _log("STEP 3: Building HTML...")

        html = _build_signal_html(
            stories_by_section=stories_by_section,
            subject_line=subject_line,
            issue_date_display=issue_date_display
        )

        results["html_length"] = len(html)
        _log(f"HTML built: {len(html)} characters")

        # =====================================================================
        # Step 4: Update issue status and store HTML
        # =====================================================================
        _log("-" * 40)
        _log("STEP 4: Updating issue...")

        update_data = {
            "status": "compiled",
            "compiled_html": html,
        }

        airtable.update_signal_issue(issue_record_id, update_data)
        results["compiled"] = True
        _log(f"Issue status updated to 'compiled'")

        # =====================================================================
        # Success!
        # =====================================================================
        _log("=" * 60)
        _log("SIGNAL HTML COMPILE JOB COMPLETE")
        _log(f"  Issue ID: {results['issue_id']}")
        _log(f"  Stories: {results['story_count']}")
        _log(f"  HTML Length: {results['html_length']}")
        _log(f"  Compiled: {results['compiled']}")
        _log("=" * 60)

        return results

    except Exception as e:
        _log("=" * 60)
        _log(f"FATAL ERROR: {e}")
        import traceback
        _log(f"Traceback: {traceback.format_exc()}")
        _log("=" * 60)
        results["errors"].append({"fatal": str(e)})
        raise


def _build_signal_html(
    stories_by_section: Dict[str, dict],
    subject_line: str,
    issue_date_display: str
) -> str:
    """
    Build the complete Signal HTML email.

    Structure:
    1. Header with logo and date
    2. At-a-Glance section (4 main stories + 5 signals)
    3. Full Stories section (4 expanded treatments)
    4. Footer

    Args:
        stories_by_section: Dict mapping section name to story record
        subject_line: Email subject line for preheader
        issue_date_display: Formatted date for header

    Returns:
        Complete HTML email string
    """
    year = datetime.now().year

    # Build At-a-Glance section
    at_a_glance_html = _build_at_a_glance(stories_by_section)

    # Build Full Stories section
    full_stories_html = _build_full_stories(stories_by_section)

    # Full email template
    # Signal uses: Georgia font, blue accent, 600px width, 32px spacing
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(subject_line)}</title>
  <style>
    body {{ margin: 0; padding: 0; background-color: #f8fafc; }}
    table {{ border-collapse: collapse; }}
    .signal-wrap {{ width: 600px; max-width: 100%; }}
    @media only screen and (max-width: 640px) {{
      .signal-wrap {{ width: 100% !important; }}
      .sig-block {{ display: block !important; width: 100% !important; }}
    }}
  </style>
</head>
<body style="margin:0; padding:0; background-color:#f8fafc;">
  <!-- Hidden preheader -->
  <div style="display:none; max-height:0; overflow:hidden; opacity:0; font-size:1px; line-height:1px; color:#f8fafc;">
    {_escape_html(subject_line)}
  </div>

  <center style="width:100%; background-color:#f8fafc;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <td align="center" style="padding:32px 16px;">
          <table role="presentation" class="signal-wrap" cellspacing="0" cellpadding="0" border="0" style="background-color:#ffffff; border:1px solid #e2e8f0; border-radius:8px;">

            <!-- Green Brand Accent Bar -->
            <tr>
              <td style="background-color:#143330; height:4px; padding:0; border-radius:8px 8px 0 0;"></td>
            </tr>

            <!-- Header -->
            <tr>
              <td style="padding:32px 32px 24px 32px; border-bottom:1px solid #e2e8f0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td align="center">
                      <div style="font-family:Georgia, serif; font-size:32px; font-weight:bold; color:#1e293b; letter-spacing:2px;">
                        SIGNAL
                      </div>
                      <div style="font-family:Georgia, serif; font-size:13px; color:#64748b; margin-top:8px;">
                        {_escape_html(issue_date_display)}
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Intro -->
            <tr>
              <td style="padding:24px 32px; background-color:#f8fafc;">
                <div style="font-family:Georgia, serif; font-size:16px; line-height:1.7; color:#475569; text-align:center;">
                  Your daily AI briefing is ready. Here's what matters today.
                </div>
              </td>
            </tr>

            <!-- At-a-Glance Section -->
            <tr>
              <td style="padding:0 32px 24px 32px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f1f5f9; border-radius:6px;">
                  <tr>
                    <td style="padding:24px;">
                      {at_a_glance_html}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Full Stories Section -->
            {full_stories_html}

            <!-- Footer -->
            <tr>
              <td style="padding:24px 32px; border-top:1px solid #e2e8f0; background-color:#f8fafc;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="font-family:Georgia, serif; font-size:12px; line-height:1.6; color:#94a3b8; text-align:center;">
                      You're receiving this because you subscribed to Signal.<br />
                      {{{{unsubscribe_url}}}}
                    </td>
                  </tr>
                  <tr>
                    <td align="center" style="padding-top:16px; font-family:Georgia, serif; font-size:11px; color:#94a3b8;">
                      &copy; {year} Signal AI Briefing
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </center>
</body>
</html>'''

    return html


def _build_at_a_glance(stories_by_section: Dict[str, dict]) -> str:
    """
    Build the At-a-Glance section HTML.

    Shows:
    - 4 main stories (headline + one_liner)
    - 5 signals (numbered list with headline only)

    Args:
        stories_by_section: Dict mapping section name to story record

    Returns:
        HTML string for At-a-Glance section
    """
    parts = []

    # Main stories (top_story, ai_at_work, emerging_moves, beyond_business)
    main_sections = ["top_story", "ai_at_work", "emerging_moves", "beyond_business"]

    for section in main_sections:
        story = stories_by_section.get(section, {})
        fields = story.get('fields', {})
        headline = fields.get('headline', '')
        one_liner = fields.get('one_liner', '')
        display_name = SECTION_DISPLAY_NAMES.get(section, section.upper())

        if headline:
            parts.append(f'''
              <div style="margin-bottom:16px;">
                <div style="font-family:Georgia, serif; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:0.5px; color:#059669; margin-bottom:4px;">
                  {_escape_html(display_name)}
                </div>
                <div style="font-family:Georgia, serif; font-size:15px; font-weight:600; color:#1e293b; line-height:1.4;">
                  {_escape_html(headline)}
                </div>
                <div style="font-family:Georgia, serif; font-size:14px; color:#64748b; line-height:1.5; margin-top:4px;">
                  {_escape_html(one_liner)}
                </div>
              </div>''')

    # Signals section
    signal_items = []
    for i in range(1, 6):
        section = f"signal_{i}"
        story = stories_by_section.get(section, {})
        fields = story.get('fields', {})
        headline = fields.get('headline', '')
        if headline:
            signal_items.append(f'''
                <div style="font-family:Georgia, serif; font-size:14px; color:#475569; line-height:1.5; margin-bottom:8px; padding-left:20px; text-indent:-20px;">
                  <span style="color:#059669; font-weight:600;">{i}.</span> {_escape_html(headline)}
                </div>''')

    if signal_items:
        parts.append(f'''
              <div style="margin-top:20px; padding-top:16px; border-top:1px solid #cbd5e1;">
                <div style="font-family:Georgia, serif; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:0.5px; color:#64748b; margin-bottom:12px;">
                  SIGNALS
                </div>
                {"".join(signal_items)}
              </div>''')

    return "".join(parts)


def _build_full_stories(stories_by_section: Dict[str, dict]) -> str:
    """
    Build the Full Stories section HTML.

    Shows 4 main stories with:
    - Section label
    - Headline
    - Lead paragraph
    - Why It Matters (2 sentences with bolding)
    - What's Next (2 sentences with bolding)

    Args:
        stories_by_section: Dict mapping section name to story record

    Returns:
        HTML string for Full Stories section
    """
    parts = []

    main_sections = ["top_story", "ai_at_work", "emerging_moves", "beyond_business"]

    for section in main_sections:
        story = stories_by_section.get(section, {})
        fields = story.get('fields', {})

        headline = fields.get('headline', '')
        lead = fields.get('lead', '')
        why_it_matters = fields.get('why_it_matters', '')
        whats_next = fields.get('whats_next', '')
        source = fields.get('source_attribution', '')
        display_name = SECTION_DISPLAY_NAMES.get(section, section.upper())

        if not headline:
            continue

        # Build story block
        story_html = f'''
            <tr>
              <td class="sig-block" style="padding:24px 32px; border-top:1px solid #e2e8f0;">
                <!-- Section Label -->
                <div style="font-family:Georgia, serif; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:1px; color:#059669; margin-bottom:8px;">
                  {_escape_html(display_name)}
                </div>

                <!-- Headline -->
                <div style="font-family:Georgia, serif; font-size:20px; font-weight:600; color:#1e293b; line-height:1.3; margin-bottom:16px;">
                  {_escape_html(headline)}
                </div>'''

        # Lead paragraph (may contain \n\n for paragraph breaks)
        if lead:
            # Convert double newlines to paragraph breaks
            lead_paragraphs = lead.split('\n\n')
            lead_html_parts = []
            for para in lead_paragraphs:
                para = para.strip()
                if para:
                    lead_html_parts.append(f'''<p style="font-family:Georgia, serif; font-size:16px; color:#475569; line-height:1.7; margin:0 0 12px 0;">
                  {_escape_html(para)}
                </p>''')
            lead_html = ''.join(lead_html_parts)
            story_html += f'''
                <!-- Lead -->
                <div style="margin-bottom:16px;">
                  {lead_html}
                </div>'''

        # Why It Matters (formatted as bullet list)
        if why_it_matters:
            why_it_matters_html = _format_as_bullet_list(why_it_matters)
            story_html += f'''
                <!-- Why It Matters -->
                <div style="margin-bottom:16px;">
                  <div style="font-family:Georgia, serif; font-size:12px; font-weight:bold; text-transform:uppercase; letter-spacing:0.5px; color:#64748b; margin-bottom:6px;">
                    Why It Matters
                  </div>
                  <div>
                    {why_it_matters_html}
                  </div>
                </div>'''

        # What's Next (formatted as bullet list)
        if whats_next:
            whats_next_html = _format_as_bullet_list(whats_next)
            story_html += f'''
                <!-- What's Next -->
                <div style="margin-bottom:12px;">
                  <div style="font-family:Georgia, serif; font-size:12px; font-weight:bold; text-transform:uppercase; letter-spacing:0.5px; color:#64748b; margin-bottom:6px;">
                    What's Next
                  </div>
                  <div>
                    {whats_next_html}
                  </div>
                </div>'''

        story_html += '''
              </td>
            </tr>'''

        parts.append(story_html)

    # Add SIGNALS section (signal_1 through signal_5) with headline + signal_blurb
    signal_parts = []
    for i in range(1, 6):
        section = f"signal_{i}"
        story = stories_by_section.get(section, {})
        fields = story.get('fields', {})
        headline = fields.get('headline', '')
        signal_blurb = fields.get('signal_blurb', '')

        if headline:
            signal_parts.append(f'''
                <div style="margin-bottom:16px;">
                  <div style="font-family:Georgia, serif; font-size:15px; font-weight:600; color:#1e293b; line-height:1.4;">
                    <span style="color:#059669;">{i}.</span> {_escape_html(headline)}
                  </div>
                  <div style="font-family:Georgia, serif; font-size:14px; color:#64748b; line-height:1.5; margin-top:4px;">
                    {_escape_html(signal_blurb)}
                  </div>
                </div>''')

    if signal_parts:
        parts.append(f'''
            <tr>
              <td class="sig-block" style="padding:24px 32px; border-top:1px solid #e2e8f0;">
                <!-- Signals Section Label -->
                <div style="font-family:Georgia, serif; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:1px; color:#059669; margin-bottom:16px;">
                  SIGNALS
                </div>
                {"".join(signal_parts)}
              </td>
            </tr>''')

    return "".join(parts)


def preview_signal_html(issue_id: str) -> Optional[Dict[str, str]]:
    """
    Get HTML preview for a specific Signal issue.

    Args:
        issue_id: Signal issue ID (e.g., "Signal - Jan 14")

    Returns:
        {"html": str, "subject_line": str, "issue_id": str} or None
    """
    airtable = AirtableClient()

    try:
        issue = airtable.get_signal_issue_by_id(issue_id)
        if issue:
            fields = issue.get('fields', {})
            return {
                "html": fields.get('compiled_html', ''),
                "subject_line": fields.get('subject_line', ''),
                "issue_id": fields.get('issue_id', ''),
                "status": fields.get('status', '')
            }
    except Exception as e:
        logger.error(f"[Signal Step 4] Error fetching HTML preview: {e}")

    return None


def recompile_signal_html(issue_id: str) -> dict:
    """
    Recompile HTML for a specific Signal issue.

    Args:
        issue_id: Signal issue ID (e.g., "Signal - Jan 14")

    Returns:
        Same as compile_signal_html()
    """
    _log(f"Recompiling for specific issue: {issue_id}")
    return compile_signal_html(issue_id=issue_id)


# Job configuration for RQ
# NOTE: Typically triggered via API endpoint
# API endpoint: POST /api/signal/html
JOB_CONFIG = {
    "func": compile_signal_html,
    "id": "signal_step4_html_compile",
    "queue": "default",
    "timeout": "10m",
}
