"""
Step 3: Decoration Job
Workflow ID: HCbd2g852rkQgSqr
Schedule: 9:25 PM EST (0 2 25 * * 2-6 UTC)

Creates AI-generated headlines, deks, bullet points for each selected story.
Uses Gemini for content cleaning and Claude for decoration generation.

Updated Jan 1, 2026:
- Uses HTML <b> tags for bolding (not Markdown **)
- Field names match Airtable Newsletter Issue Stories table (tbla16LJCf5Z6cRn3):
  - headline (not ai_headline)
  - b1, b2, b3 (not ai_bullet_1/2/3)
  - story_id (not storyID)
  - issue_id (text, not record ID)
- Supports newsletter style variants (pivot_ai, pivot_build, pivot_invest)
- 18 label categories
"""

import os
import json
import traceback
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.gemini import GeminiClient
from utils.claude import ClaudeClient


def _log(msg: str, data: Any = None):
    """Enhanced logging with timestamp and optional data dump"""
    timestamp = datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
    print(f"[Step 3][{timestamp}] {msg}")
    if data is not None:
        if isinstance(data, (dict, list)):
            print(f"[Step 3][{timestamp}]   └─ {json.dumps(data, indent=2, default=str)[:2000]}")
        else:
            print(f"[Step 3][{timestamp}]   └─ {str(data)[:500]}")


def decorate_stories(newsletter: str = 'pivot_ai') -> dict:
    """
    Step 3: Decoration Cron Job - Main entry point

    Flow (matching n8n workflow HCbd2g852rkQgSqr):
    1. Get pending issue from Selected Slots (status='pending')
    2. For each slot (1-5):
       a. Lookup article markdown by pivotId from Newsletter Selects
       b. Clean content using Gemini (content_cleaner prompt)
       c. Generate decoration using Claude (headline_generator MASTER PROMPT)
          - Outputs: ai_headline, ai_dek, ai_bullet_1/2/3, label, source, clean_url
       d. Apply HTML <b> bolding to bullets (bold_formatter prompt)
       e. Write to Newsletter Issue Stories table
    3. Update issue status to 'decorated'

    Args:
        newsletter: Style variant - 'pivot_ai', 'pivot_build', or 'pivot_invest'

    Returns:
        {decorated: int, issue_id: str, decoration_ids: list, errors: list}
    """
    _log("=" * 60)
    _log(f"DECORATION JOB STARTED")
    _log(f"Newsletter style: {newsletter}")
    _log("=" * 60)

    # Validate newsletter style
    valid_newsletters = ['pivot_ai', 'pivot_build', 'pivot_invest']
    if newsletter not in valid_newsletters:
        _log(f"WARNING: Unknown newsletter '{newsletter}', defaulting to 'pivot_ai'")
        newsletter = 'pivot_ai'

    # Initialize clients
    _log("Initializing clients...")
    airtable = AirtableClient()
    _log(f"  ✓ AirtableClient initialized (base: {airtable.ai_editor_base_id})")
    gemini = GeminiClient()
    _log("  ✓ GeminiClient initialized")
    claude = ClaudeClient()
    _log("  ✓ ClaudeClient initialized")

    # Track results
    results = {
        "decorated": 0,
        "issue_id": "",
        "decoration_ids": [],
        "errors": []
    }

    try:
        # 1. Get pending issue from Selected Slots
        _log("-" * 40)
        _log("STEP 1: Fetching pending issue from Selected Slots...")
        _log(f"  Table ID: {airtable.selected_slots_table_id}")
        pending_issue = airtable.get_pending_issue()

        if not pending_issue:
            _log("❌ No pending issue found - exiting")
            return results

        issue_record_id = pending_issue.get('id', '')
        issue_fields = pending_issue.get('fields', {})
        results["issue_id"] = issue_record_id

        _log(f"✓ Found pending issue:")
        _log(f"  Record ID: {issue_record_id}")
        _log(f"  Issue Date: {issue_fields.get('issue_date', 'unknown')}")
        _log(f"  Status: {issue_fields.get('status', 'unknown')}")
        _log(f"  All fields:", list(issue_fields.keys()))

        # 2. Process each slot
        for slot in range(1, 6):
            _log("-" * 40)
            _log(f"SLOT {slot}: Starting decoration...")

            try:
                # Extract slot data from issue
                pivot_id = issue_fields.get(f'slot_{slot}_pivotId', '')
                story_id = issue_fields.get(f'slot_{slot}_storyId', '')
                headline = issue_fields.get(f'slot_{slot}_headline', '')
                source_id = issue_fields.get(f'slot_{slot}_source', '')

                _log(f"SLOT {slot}: Extracted slot data:")
                _log(f"  pivot_id: {pivot_id or '(empty)'}")
                _log(f"  story_id: {story_id or '(empty)'}")
                _log(f"  headline: {headline[:80] if headline else '(empty)'}...")
                _log(f"  source_id: {source_id or '(empty)'}")

                if not pivot_id:
                    _log(f"SLOT {slot}: ⚠️ No pivotId, skipping this slot")
                    continue

                # 2a. Lookup article markdown
                _log(f"SLOT {slot}: Fetching article from Newsletter Selects...")
                _log(f"  Table: {airtable.newsletter_selects_table_id}")
                _log(f"  Filter: pivot_id='{pivot_id}'")
                article = airtable.get_article_by_pivot_id(pivot_id)

                if not article:
                    _log(f"SLOT {slot}: ❌ Article not found in Newsletter Selects")
                    results["errors"].append({
                        "slot": slot,
                        "error": f"Article not found: {pivot_id}"
                    })
                    continue

                article_fields = article.get('fields', {})
                markdown = article_fields.get('markdown', '') or article_fields.get('raw', '')
                original_url = article_fields.get('original_url', '') or article_fields.get('core_url', '')

                _log(f"SLOT {slot}: ✓ Article found:")
                _log(f"  Record ID: {article.get('id', 'unknown')}")
                _log(f"  Fields available: {list(article_fields.keys())}")
                _log(f"  Markdown length: {len(markdown)} chars")
                _log(f"  Original URL: {original_url or '(empty)'}")

                if not markdown:
                    _log(f"SLOT {slot}: ❌ No markdown/raw content found")
                    results["errors"].append({
                        "slot": slot,
                        "error": f"No markdown content for {pivot_id}"
                    })
                    continue

                # 2b. Clean content using Gemini
                _log(f"SLOT {slot}: Cleaning content with Gemini...")
                _log(f"  Input length: {len(markdown)} chars")
                try:
                    cleaned_content = gemini.clean_content(markdown)
                    _log(f"SLOT {slot}: ✓ Gemini cleaning complete")
                    _log(f"  Output length: {len(cleaned_content)} chars")
                    _log(f"  Preview: {cleaned_content[:200]}...")
                except Exception as e:
                    _log(f"SLOT {slot}: ⚠️ Gemini cleaning failed: {e}")
                    _log(f"  Using raw markdown (first 8000 chars)")
                    cleaned_content = markdown[:8000]

                # 2c. Generate decoration using Claude MASTER PROMPT
                _log(f"SLOT {slot}: Generating decoration with Claude...")
                _log(f"  Newsletter style: {newsletter}")
                story_data = {
                    "headline": headline,
                    "source_id": source_id,
                    "core_url": original_url,
                    "date_published": issue_fields.get('issue_date', ''),
                    "newsletter": newsletter
                }
                _log(f"  Story data:", story_data)

                # Pass newsletter style variant to Claude
                decoration = claude.decorate_story(story_data, cleaned_content, newsletter=newsletter)

                if "error" in decoration:
                    _log(f"SLOT {slot}: ❌ Claude decoration failed")
                    _log(f"  Error: {decoration.get('error')}")
                    results["errors"].append({
                        "slot": slot,
                        "error": decoration.get("error")
                    })
                    continue

                _log(f"SLOT {slot}: ✓ Claude decoration complete")
                _log(f"  ai_headline: {decoration.get('ai_headline', '')[:80]}...")
                _log(f"  ai_dek: {decoration.get('ai_dek', '')[:80]}...")
                _log(f"  ai_bullet_1: {decoration.get('ai_bullet_1', '')[:80]}...")
                _log(f"  ai_bullet_2: {decoration.get('ai_bullet_2', '')[:80]}...")
                _log(f"  ai_bullet_3: {decoration.get('ai_bullet_3', '')[:80]}...")
                _log(f"  label: {decoration.get('label', '')}")

                # 2d. Apply HTML <b> bolding to bullets
                _log(f"SLOT {slot}: Applying HTML <b> bolding...")
                try:
                    # apply_bolding now takes full decoration dict and returns dict with bolded bullets
                    bolded_decoration = claude.apply_bolding(decoration)
                    # Update decoration with bolded versions
                    decoration["ai_bullet_1"] = bolded_decoration.get("ai_bullet_1", decoration.get("ai_bullet_1", ""))
                    decoration["ai_bullet_2"] = bolded_decoration.get("ai_bullet_2", decoration.get("ai_bullet_2", ""))
                    decoration["ai_bullet_3"] = bolded_decoration.get("ai_bullet_3", decoration.get("ai_bullet_3", ""))
                    _log(f"SLOT {slot}: ✓ Bolding complete")
                    _log(f"  b1 has <b>: {'<b>' in decoration['ai_bullet_1']}")
                    _log(f"  b2 has <b>: {'<b>' in decoration['ai_bullet_2']}")
                    _log(f"  b3 has <b>: {'<b>' in decoration['ai_bullet_3']}")
                except Exception as e:
                    _log(f"SLOT {slot}: ⚠️ Bolding failed: {e}")
                    _log(f"  Using unbolded bullets")

                # 2e. Write to Newsletter Issue Stories table
                # Field names from Airtable API query (table tbla16LJCf5Z6cRn3)
                _log(f"SLOT {slot}: Writing to Newsletter Issue Stories...")
                _log(f"  Table: {airtable.decoration_table_id}")

                # Build issue_id from issue date (format: "Pivot 5 - Jan 02")
                issue_date_raw = issue_fields.get('issue_date', '')
                _log(f"  Building issue_id from date: {issue_date_raw}")
                # Convert "2026-01-02" to "Jan 02" format
                if issue_date_raw and '-' in issue_date_raw:
                    try:
                        from datetime import datetime as dt
                        parsed = dt.strptime(issue_date_raw, '%Y-%m-%d')
                        issue_date_fmt = parsed.strftime('%b %d')  # "Jan 02"
                    except ValueError:
                        issue_date_fmt = issue_date_raw  # Fallback to raw
                else:
                    issue_date_fmt = issue_date_raw  # Already formatted or empty
                issue_id_text = f"Pivot 5 - {issue_date_fmt}" if issue_date_fmt else "Pivot 5"
                _log(f"  Formatted issue_id: {issue_id_text}")

                decoration_data = {
                    # Record identifiers (verified via Airtable API)
                    "story_id": story_id,           # singleLineText
                    "issue_id": issue_id_text,      # singleLineText (e.g., "Pivot 5 - Dec 31")
                    "slot_order": slot,             # number (1-5)
                    # AI-generated content (field names from Airtable schema)
                    "headline": decoration.get("ai_headline", headline),  # multilineText
                    "ai_dek": decoration.get("ai_dek", ""),                # multilineText
                    "b1": decoration.get("ai_bullet_1", ""),              # multilineText with <b> tags
                    "b2": decoration.get("ai_bullet_2", ""),              # multilineText with <b> tags
                    "b3": decoration.get("ai_bullet_3", ""),              # multilineText with <b> tags
                    # Metadata
                    "label": decoration.get("label", "ENTERPRISE"),       # singleLineText
                    "raw": cleaned_content[:10000] if cleaned_content else "",  # multilineText
                    # Image generation
                    "image_status": "needs_image",  # singleSelect
                }

                _log(f"SLOT {slot}: Decoration data to write:")
                _log(f"  story_id: {decoration_data['story_id']}")
                _log(f"  issue_id: {decoration_data['issue_id']}")
                _log(f"  slot_order: {decoration_data['slot_order']}")
                _log(f"  headline: {decoration_data['headline'][:60]}...")
                _log(f"  ai_dek: {decoration_data['ai_dek'][:60]}...")
                _log(f"  b1 length: {len(decoration_data['b1'])} chars")
                _log(f"  b2 length: {len(decoration_data['b2'])} chars")
                _log(f"  b3 length: {len(decoration_data['b3'])} chars")
                _log(f"  label: {decoration_data['label']}")
                _log(f"  raw length: {len(decoration_data['raw'])} chars")
                _log(f"  image_status: {decoration_data['image_status']}")

                record_id = airtable.write_decoration(decoration_data)
                results["decoration_ids"].append(record_id)
                results["decorated"] += 1

                _log(f"SLOT {slot}: ✓ Created decoration record: {record_id}")

            except Exception as e:
                _log(f"SLOT {slot}: ❌ EXCEPTION: {e}")
                _log(f"  Traceback: {traceback.format_exc()}")
                results["errors"].append({
                    "slot": slot,
                    "error": str(e)
                })

        # 3. Update issue status to 'decorated' if any slots were processed
        _log("=" * 60)
        _log("STEP 3: Updating issue status...")
        if results["decorated"] > 0:
            _log(f"  Decorated {results['decorated']} slots successfully")
            _log(f"  Updating status to 'decorated'...")
            try:
                # Use the existing airtable client from line 56
                table = airtable._get_table(
                    airtable.ai_editor_base_id,
                    airtable.selected_slots_table_id
                )
                table.update(issue_record_id, {"status": "decorated"})
                _log(f"  ✓ Issue status updated to 'decorated'")
            except Exception as e:
                _log(f"  ❌ Failed to update issue status: {e}")
                _log(f"  Traceback: {traceback.format_exc()}")
                results["errors"].append({
                    "step": "update_status",
                    "error": str(e)
                })
        else:
            _log(f"  ⚠️ No slots were decorated, skipping status update")

        _log("=" * 60)
        _log("DECORATION JOB COMPLETE")
        _log(f"  Decorated: {results['decorated']}")
        _log(f"  Decoration IDs: {results['decoration_ids']}")
        _log(f"  Errors: {len(results['errors'])}")
        if results['errors']:
            _log(f"  Error details:", results['errors'])
        _log("=" * 60)
        return results

    except Exception as e:
        _log("=" * 60)
        _log(f"❌ FATAL ERROR: {e}")
        _log(f"Traceback: {traceback.format_exc()}")
        _log("=" * 60)
        results["errors"].append({"fatal": str(e)})
        raise


# Job configuration for RQ
# NOTE: Typically triggered via API endpoint, not cron
# API endpoint: POST /jobs/decoration with optional {"newsletter": "pivot_ai"}
JOB_CONFIG = {
    "func": decorate_stories,
    "id": "step3_decoration",
    "queue": "default",
    "timeout": "30m",
    # Default newsletter style - can be overridden via API params
    "default_params": {
        "newsletter": "pivot_ai"
    }
}
