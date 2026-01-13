"""
Signal Newsletter Step 3: Decoration Job

Creates AI-generated headlines, summaries, and bullet points for Signal stories.
Uses Gemini for content cleaning and Claude for decoration generation.

Key Differences from Pivot 5:
- NO images (no image_status field)
- Two decoration modes:
  - Full story: TOP STORY, AI AT WORK, EMERGING MOVES, BEYOND BUSINESS
  - Quick-hit: SIGNALS (5 items) - headline + 2 sentences only
- Uses Signal Issue Stories table in Signal base
- Different section mapping and field names

Section Order: top_story -> ai_at_work -> emerging -> beyond -> signal_1..signal_5

Created: January 12, 2026
"""

import os
import json
import traceback
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.gemini import GeminiClient
from utils.claude import ClaudeClient
from utils.prompts import get_prompt, get_prompt_with_metadata


def _log(msg: str, data: Any = None):
    """Enhanced logging with timestamp and optional data dump"""
    timestamp = datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
    print(f"[Signal Step 3][{timestamp}] {msg}")
    if data is not None:
        if isinstance(data, (dict, list)):
            print(f"[Signal Step 3][{timestamp}]   └─ {json.dumps(data, indent=2, default=str)[:2000]}")
        else:
            print(f"[Signal Step 3][{timestamp}]   └─ {str(data)[:500]}")


# Signal section configuration
# Order matches slot selection: 1 -> 3 -> 4 -> 5 -> 2 (5 items)
SIGNAL_SECTIONS = [
    {"section": "top_story", "source_slot": 1, "full_story": True, "display_name": "TOP STORY"},
    {"section": "ai_at_work", "source_slot": 3, "full_story": True, "display_name": "AI AT WORK"},
    {"section": "emerging", "source_slot": 4, "full_story": True, "display_name": "EMERGING MOVES"},
    {"section": "beyond", "source_slot": 5, "full_story": True, "display_name": "BEYOND BUSINESS"},
    # SIGNALS section - 5 quick-hit items
    {"section": "signal", "signal_num": 1, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #1"},
    {"section": "signal", "signal_num": 2, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #2"},
    {"section": "signal", "signal_num": 3, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #3"},
    {"section": "signal", "signal_num": 4, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #4"},
    {"section": "signal", "signal_num": 5, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #5"},
]


def decorate_signal_stories() -> dict:
    """
    Signal Step 3: Decoration Job - Main entry point

    Flow:
    1. Get pending issue from Signal Selected Slots (status='pending')
    2. For each section (top_story, ai_at_work, emerging, beyond, signal_1..5):
       a. Lookup article markdown by pivot_id from Newsletter Selects (shared table)
       b. Clean content using Gemini (content_cleaner prompt)
       c. Generate decoration using Claude:
          - Full stories: headline, dek, 3 bullets
          - SIGNALS: headline + 2 sentences summary
       d. Apply HTML <b> bolding to bullets (full stories only)
       e. Write to Signal Issue Stories table
    3. Update issue status to 'decorated'

    Returns:
        {decorated: int, issue_id: str, story_ids: list, errors: list}
    """
    _log("=" * 60)
    _log("SIGNAL DECORATION JOB STARTED")
    _log("=" * 60)

    # Initialize clients
    _log("Initializing clients...")
    airtable = AirtableClient()
    _log(f"  AirtableClient initialized")
    _log(f"  Signal base: {airtable.signal_base_id}")
    _log(f"  AI Editor base (shared): {airtable.ai_editor_base_id}")
    gemini = GeminiClient()
    _log("  GeminiClient initialized")
    claude = ClaudeClient()
    _log("  ClaudeClient initialized")

    # Track results
    results = {
        "decorated": 0,
        "issue_id": "",
        "story_ids": [],
        "errors": []
    }

    try:
        # 1. Get pending issue from Signal Selected Slots
        _log("-" * 40)
        _log("STEP 1: Fetching pending Signal issue...")
        pending_issue = airtable.get_signal_pending_issue()

        if not pending_issue:
            _log("No pending Signal issue found - exiting")
            return results

        issue_record_id = pending_issue.get('id', '')
        issue_fields = pending_issue.get('fields', {})
        issue_id_text = issue_fields.get('issue_id', '')
        results["issue_id"] = issue_id_text

        _log(f"Found pending issue:")
        _log(f"  Record ID: {issue_record_id}")
        _log(f"  Issue ID: {issue_id_text}")
        _log(f"  Issue Date: {issue_fields.get('issue_date', 'unknown')}")
        _log(f"  Status: {issue_fields.get('status', 'unknown')}")
        _log(f"  All fields:", list(issue_fields.keys()))

        # 2. Process each section
        for section_config in SIGNAL_SECTIONS:
            section = section_config["section"]
            display_name = section_config["display_name"]
            is_full_story = section_config["full_story"]
            source_slot = section_config["source_slot"]
            signal_num = section_config.get("signal_num")

            _log("-" * 40)
            _log(f"{display_name}: Starting decoration...")

            try:
                # Determine field names based on section type
                if section == "signal" and signal_num:
                    pivot_id_field = f'signal_{signal_num}_pivot_id'
                    story_id_field = f'signal_{signal_num}_story_id'
                    headline_field = f'signal_{signal_num}_headline'
                else:
                    pivot_id_field = f'{section}_pivot_id'
                    story_id_field = f'{section}_story_id'
                    headline_field = f'{section}_headline'

                # Extract data from issue
                pivot_id = issue_fields.get(pivot_id_field, '')
                story_id = issue_fields.get(story_id_field, '')
                original_headline = issue_fields.get(headline_field, '')

                _log(f"{display_name}: Extracted data:")
                _log(f"  pivot_id ({pivot_id_field}): {pivot_id or '(empty)'}")
                _log(f"  story_id ({story_id_field}): {story_id or '(empty)'}")
                _log(f"  headline: {original_headline[:60] if original_headline else '(empty)'}...")

                if not pivot_id:
                    _log(f"{display_name}: No pivot_id, skipping this section")
                    continue

                # 2a. Lookup article markdown from shared Newsletter Selects table
                _log(f"{display_name}: Fetching article from Newsletter Selects...")
                article = airtable.get_article_by_pivot_id(pivot_id)

                if not article:
                    _log(f"{display_name}: Article not found in Newsletter Selects")
                    results["errors"].append({
                        "section": display_name,
                        "error": f"Article not found: {pivot_id}"
                    })
                    continue

                article_fields = article.get('fields', {})
                markdown = article_fields.get('markdown', '') or article_fields.get('raw', '')
                source_id = article_fields.get('source_id', '') or article_fields.get('source_name', '')
                core_url = article_fields.get('original_url', '') or article_fields.get('core_url', '')

                _log(f"{display_name}: Article found:")
                _log(f"  Record ID: {article.get('id', 'unknown')}")
                _log(f"  Markdown length: {len(markdown)} chars")
                _log(f"  Source: {source_id}")
                _log(f"  URL: {core_url[:60] if core_url else '(empty)'}...")

                if not markdown:
                    _log(f"{display_name}: No markdown/raw content found")
                    results["errors"].append({
                        "section": display_name,
                        "error": f"No markdown content for {pivot_id}"
                    })
                    continue

                # 2b. Clean content using Gemini
                _log(f"{display_name}: Cleaning content with Gemini...")
                try:
                    cleaned_content = gemini.clean_content(markdown)
                    _log(f"{display_name}: Gemini cleaning complete")
                    _log(f"  Output length: {len(cleaned_content)} chars")
                except Exception as e:
                    _log(f"{display_name}: Gemini cleaning failed: {e}")
                    _log(f"  Using raw markdown (first 8000 chars)")
                    cleaned_content = markdown[:8000]

                # 2c. Generate decoration using Claude
                if is_full_story:
                    # Full story decoration (TOP STORY, AI AT WORK, EMERGING, BEYOND)
                    decoration = _decorate_full_story(
                        claude=claude,
                        headline=original_headline,
                        source_id=source_id,
                        section_name=display_name,
                        cleaned_content=cleaned_content
                    )
                else:
                    # Quick-hit decoration (SIGNALS)
                    decoration = _decorate_signal_item(
                        claude=claude,
                        headline=original_headline,
                        source_id=source_id,
                        cleaned_content=cleaned_content
                    )

                if "error" in decoration:
                    _log(f"{display_name}: Claude decoration failed")
                    _log(f"  Error: {decoration.get('error')}")
                    results["errors"].append({
                        "section": display_name,
                        "error": decoration.get("error")
                    })
                    continue

                _log(f"{display_name}: Claude decoration complete")
                _log(f"  headline: {decoration.get('ai_headline', '')[:60]}...")

                # 2d. Apply HTML <b> bolding to bullets (full stories only)
                if is_full_story and decoration.get('ai_bullet_1'):
                    _log(f"{display_name}: Applying HTML <b> bolding...")
                    try:
                        bolded_decoration = claude.apply_bolding(decoration)
                        decoration["ai_bullet_1"] = bolded_decoration.get("ai_bullet_1", decoration.get("ai_bullet_1", ""))
                        decoration["ai_bullet_2"] = bolded_decoration.get("ai_bullet_2", decoration.get("ai_bullet_2", ""))
                        decoration["ai_bullet_3"] = bolded_decoration.get("ai_bullet_3", decoration.get("ai_bullet_3", ""))
                        _log(f"{display_name}: Bolding complete")
                    except Exception as e:
                        _log(f"{display_name}: Bolding failed: {e}")
                        _log(f"  Using unbolded bullets")

                # 2e. Write to Signal Issue Stories table
                _log(f"{display_name}: Writing to Signal Issue Stories...")

                # Build story data based on section type
                if is_full_story:
                    story_data = {
                        "story_id": story_id,
                        "issue_id": issue_id_text,
                        "section": section,
                        "slot_order": 1,  # Single story per main section
                        "source_slot": source_slot,
                        "headline": decoration.get("ai_headline", original_headline),
                        "summary": decoration.get("ai_dek", ""),
                        "paragraph": "",  # Signal doesn't use paragraph
                        "b1": decoration.get("ai_bullet_1", ""),
                        "b2": decoration.get("ai_bullet_2", ""),
                        "b3": decoration.get("ai_bullet_3", ""),
                        "source_attribution": f"via {source_id}" if source_id else "",
                        "pivot_id": pivot_id,
                        "core_url": core_url,
                        "decoration_status": "decorated",
                        "label": decoration.get("label", "ENTERPRISE"),
                    }
                else:
                    # SIGNALS items - headline + summary only, no bullets
                    story_data = {
                        "story_id": story_id,
                        "issue_id": issue_id_text,
                        "section": "signal",
                        "slot_order": signal_num,
                        "source_slot": source_slot,
                        "headline": decoration.get("ai_headline", original_headline),
                        "summary": decoration.get("signal_summary", ""),
                        "paragraph": "",
                        "b1": "",  # No bullets for SIGNALS
                        "b2": "",
                        "b3": "",
                        "source_attribution": f"via {decoration.get('source', source_id)}" if decoration.get('source') or source_id else "",
                        "pivot_id": pivot_id,
                        "core_url": core_url,
                        "decoration_status": "decorated",
                        "label": "",  # No label for SIGNALS
                    }

                _log(f"{display_name}: Story data to write:")
                _log(f"  story_id: {story_data['story_id']}")
                _log(f"  section: {story_data['section']}")
                _log(f"  slot_order: {story_data['slot_order']}")
                _log(f"  headline: {story_data['headline'][:50]}...")

                record_id = airtable.write_signal_story(story_data)
                results["story_ids"].append(record_id)
                results["decorated"] += 1

                _log(f"{display_name}: Created story record: {record_id}")

            except Exception as e:
                _log(f"{display_name}: EXCEPTION: {e}")
                _log(f"  Traceback: {traceback.format_exc()}")
                results["errors"].append({
                    "section": display_name,
                    "error": str(e)
                })

        # 3. Update issue status to 'decorated' if any sections were processed
        _log("=" * 60)
        _log("STEP 3: Updating issue status...")
        if results["decorated"] > 0:
            _log(f"  Decorated {results['decorated']} sections successfully")
            _log(f"  Updating status to 'decorated'...")
            try:
                airtable.update_signal_issue(issue_record_id, {"status": "decorated"})
                _log(f"  Issue status updated to 'decorated'")
            except Exception as e:
                _log(f"  Failed to update issue status: {e}")
                results["errors"].append({
                    "step": "update_status",
                    "error": str(e)
                })
        else:
            _log(f"  No sections were decorated, skipping status update")

        _log("=" * 60)
        _log("SIGNAL DECORATION JOB COMPLETE")
        _log(f"  Decorated: {results['decorated']}")
        _log(f"  Story IDs: {results['story_ids']}")
        _log(f"  Errors: {len(results['errors'])}")
        if results['errors']:
            _log(f"  Error details:", results['errors'])
        _log("=" * 60)
        return results

    except Exception as e:
        _log("=" * 60)
        _log(f"FATAL ERROR: {e}")
        _log(f"Traceback: {traceback.format_exc()}")
        _log("=" * 60)
        results["errors"].append({"fatal": str(e)})
        raise


def _decorate_full_story(
    claude: ClaudeClient,
    headline: str,
    source_id: str,
    section_name: str,
    cleaned_content: str
) -> dict:
    """
    Generate full story decoration for main sections.

    Output: headline, dek, 3 bullets, label, source

    Uses signal_story_decorator prompt from database.
    """
    _log(f"  Generating full story decoration...")

    # Load Signal story decorator prompt from database
    prompt_template = get_prompt('signal_story_decorator')

    if prompt_template:
        try:
            prompt = prompt_template.format(
                headline=headline,
                source_id=source_id,
                section_name=section_name,
                cleaned_content=cleaned_content[:8000]  # Truncate for context
            )
        except KeyError as e:
            _log(f"  Missing variable in signal_story_decorator prompt: {e}")
            prompt_template = None

    if not prompt_template:
        # Fallback to hardcoded Signal full story prompt
        _log("  signal_story_decorator prompt not found in database, using fallback")
        prompt = f"""You are an expert newsletter editor creating content for the Signal AI newsletter.

## AUDIENCE
- CEOs, founders, and senior business leaders
- Busy professionals who want actionable insights
- They care about business impact and what matters for decision-making

## VOICE & STYLE
- Confident, clear, informed
- Present tense, active voice
- No jargon, no hedging (avoid "could/might/possibly")
- Avoid vague terms like "impact" or "transformation"
- Professional but not stiff

## OUTPUT FORMAT
Return ONLY valid JSON:

{{
  "label": "CATEGORY from list below",
  "ai_headline": "Title Case headline, one sentence, NO colons or semi-colons",
  "ai_dek": "One compelling sentence summarizing the story",
  "ai_bullet_1": "EXACTLY 2 sentences - the main announcement or news",
  "ai_bullet_2": "EXACTLY 2 sentences - additional context or details",
  "ai_bullet_3": "EXACTLY 2 sentences - key insight, implication, or what happens next",
  "source": "Publication name"
}}

## LABEL OPTIONS
WORK, EDUCATION, INFRASTRUCTURE, POLICY, TALENT, HEALTH, RETAIL, ENTERPRISE, COMPETITION, FUNDING, SECURITY, TOOLS, SEARCH, INVESTORS, CHINA, REGULATION, ETHICS, LAWSUITS

## CRITICAL RULES

### For Bullets:
1. Each bullet MUST be EXACTLY 2 sentences. Not 1. Not 3. Exactly 2.
2. Bullet 1: Lead with the news - what happened, who did it
3. Bullet 2: Context - why this matters, relevant background
4. Bullet 3: Forward-looking - implications, what to watch

### For Headline:
- Title Case (capitalize major words)
- One complete sentence
- NO colons, semi-colons, or em-dashes
- Make it scannable and specific

=== ARTICLE METADATA ===
Headline: {headline}
Source: {source_id}
Section: {section_name}

=== ARTICLE CONTENT ===
{cleaned_content[:8000]}

Return ONLY the JSON object. No commentary, no code fences."""

    # Get model/temperature from database
    prompt_meta = get_prompt_with_metadata('signal_story_decorator')
    model = prompt_meta.get('model', 'claude-sonnet-4-5-20250929') if prompt_meta else 'claude-sonnet-4-5-20250929'
    temperature = prompt_meta.get('temperature', 0.5) if prompt_meta else 0.5

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

        response = client.messages.create(
            model=model,
            max_tokens=1500,
            temperature=float(temperature),
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)
        _log(f"  Full story decoration parsed successfully")
        return result
    except json.JSONDecodeError:
        _log(f"  Failed to parse JSON response, attempting extraction...")
        import re
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "error": "Failed to parse decoration response",
            "ai_headline": headline,
            "ai_dek": "",
            "ai_bullet_1": "",
            "ai_bullet_2": "",
            "ai_bullet_3": "",
            "label": "ENTERPRISE"
        }
    except Exception as e:
        _log(f"  Decoration API error: {e}")
        return {"error": str(e)}


def _decorate_signal_item(
    claude: ClaudeClient,
    headline: str,
    source_id: str,
    cleaned_content: str
) -> dict:
    """
    Generate quick-hit decoration for SIGNALS section.

    Output: headline + 2 sentences (signal_summary)

    Uses signal_signals_decorator prompt from database.
    """
    _log(f"  Generating SIGNALS quick-hit decoration...")

    # Load Signal signals decorator prompt from database
    prompt_template = get_prompt('signal_signals_decorator')

    if prompt_template:
        try:
            prompt = prompt_template.format(
                headline=headline,
                source_id=source_id,
                cleaned_content=cleaned_content[:5000]  # Shorter for quick-hit
            )
        except KeyError as e:
            _log(f"  Missing variable in signal_signals_decorator prompt: {e}")
            prompt_template = None

    if not prompt_template:
        # Fallback to hardcoded Signal quick-hit prompt
        _log("  signal_signals_decorator prompt not found in database, using fallback")
        prompt = f"""You are an expert newsletter editor creating quick-hit content for the SIGNALS section.

## SIGNALS Format
Each SIGNALS item is a quick scan:
- One headline
- Two sentences of context
- No bullets, no expanded treatment

## AUDIENCE
- Busy executives scanning for key developments
- Readers who want breadth, not depth
- "What else is happening in AI?"

## OUTPUT FORMAT
Return ONLY valid JSON:

{{
  "ai_headline": "Title Case headline, one sentence, NO colons",
  "signal_summary": "EXACTLY 2 sentences providing context and why this matters.",
  "source": "Publication name"
}}

## RULES
1. Headline: Title Case, one sentence, max 12 words
2. Summary: EXACTLY 2 sentences - not 1, not 3
3. First sentence: What happened
4. Second sentence: Why it matters or what it means
5. Keep total summary under 40 words

=== ARTICLE METADATA ===
Headline: {headline}
Source: {source_id}

=== ARTICLE CONTENT ===
{cleaned_content[:5000]}

Return ONLY the JSON object. No commentary."""

    # Get model/temperature from database
    prompt_meta = get_prompt_with_metadata('signal_signals_decorator')
    model = prompt_meta.get('model', 'claude-sonnet-4-5-20250929') if prompt_meta else 'claude-sonnet-4-5-20250929'
    temperature = prompt_meta.get('temperature', 0.5) if prompt_meta else 0.5

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

        response = client.messages.create(
            model=model,
            max_tokens=500,  # Shorter for quick-hit
            temperature=float(temperature),
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)
        _log(f"  SIGNALS decoration parsed successfully")
        return result
    except json.JSONDecodeError:
        _log(f"  Failed to parse JSON response, attempting extraction...")
        import re
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "error": "Failed to parse decoration response",
            "ai_headline": headline,
            "signal_summary": "",
            "source": source_id
        }
    except Exception as e:
        _log(f"  Decoration API error: {e}")
        return {"error": str(e)}


# Job configuration for RQ
# NOTE: Typically triggered via API endpoint
# API endpoint: POST /api/signal/decorations
JOB_CONFIG = {
    "func": decorate_signal_stories,
    "id": "signal_step3_decoration",
    "queue": "default",
    "timeout": "30m",
}
