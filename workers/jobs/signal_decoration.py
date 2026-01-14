"""
Signal Newsletter Step 3: Decoration Job

Creates AI-generated headlines and content for Signal stories.
Uses Gemini for content cleaning and Claude for decoration generation.

Key Differences from Pivot 5:
- NO images (no image_status field)
- NO links in email (core_url not needed)
- Two decoration modes:
  - Full story: TOP STORY, AI AT WORK, EMERGING MOVES, BEYOND BUSINESS
    Fields: headline, one_liner, lead, why_it_matters, whats_next
  - Quick-hit: SIGNALS (5 items) - headline + signal_blurb only
    Fields: headline, signal_blurb
- Uses Signal Issue Stories table in Signal base

Section Order: top_story -> ai_at_work -> emerging_moves -> beyond_business -> signal_1..signal_5

Created: January 12, 2026
Updated: January 13, 2026 - New semantic field names
"""

import os
import re
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
# Section names must match Airtable singleSelect options exactly
SIGNAL_SECTIONS = [
    {"section": "top_story", "source_slot": 1, "full_story": True, "display_name": "TOP STORY"},
    {"section": "ai_at_work", "source_slot": 3, "full_story": True, "display_name": "AI AT WORK"},
    {"section": "emerging_moves", "source_slot": 4, "full_story": True, "display_name": "EMERGING MOVES"},
    {"section": "beyond_business", "source_slot": 5, "full_story": True, "display_name": "BEYOND BUSINESS"},
    # SIGNALS section - 5 quick-hit items (headline + signal_blurb only)
    {"section": "signal_1", "signal_num": 1, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #1"},
    {"section": "signal_2", "signal_num": 2, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #2"},
    {"section": "signal_3", "signal_num": 3, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #3"},
    {"section": "signal_4", "signal_num": 4, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #4"},
    {"section": "signal_5", "signal_num": 5, "source_slot": 2, "full_story": False, "display_name": "SIGNAL #5"},
]


def decorate_signal_stories() -> dict:
    """
    Signal Step 3: Decoration Job - Main entry point

    Flow:
    1. Get pending issue from Signal Selected Slots (status='pending')
    2. For each section (top_story, ai_at_work, emerging_moves, beyond_business, signal_1..5):
       a. Lookup article markdown by pivot_id from Newsletter Selects (shared table)
       b. Clean content using Gemini (content_cleaner prompt)
       c. Generate decoration using Claude:
          - Full stories: headline, one_liner, lead, why_it_matters, whats_next
          - SIGNALS: headline + signal_blurb (1 sentence)
       d. Apply HTML <b> bolding to why_it_matters and whats_next (full stories only)
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
                # Note: Signal Selected Slots uses section names for field prefixes
                if signal_num:
                    # SIGNALS: signal_1, signal_2, etc.
                    pivot_id_field = f'signal_{signal_num}_pivotId'
                    headline_field = f'signal_{signal_num}_headline'
                else:
                    # Main sections: top_story, ai_at_work, emerging_moves, beyond_business
                    pivot_id_field = f'{section}_pivotId'
                    headline_field = f'{section}_headline'

                # Extract data from issue
                pivot_id = issue_fields.get(pivot_id_field, '')
                original_headline = issue_fields.get(headline_field, '')

                _log(f"{display_name}: Extracted data:")
                _log(f"  pivot_id ({pivot_id_field}): {pivot_id or '(empty)'}")
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

                _log(f"{display_name}: Article found:")
                _log(f"  Record ID: {article.get('id', 'unknown')}")
                _log(f"  Markdown length: {len(markdown)} chars")
                _log(f"  Source: {source_id}")

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

                # 2d. HTML <b> bolding is now included in the decoration prompt directly
                # The prompt instructs Claude to add <b>key phrase</b> tags inline
                # No separate bolding step needed anymore
                if is_full_story:
                    _log(f"{display_name}: Bolding included in decoration output (inline)")

                # 2e. Write to Signal Issue Stories table
                _log(f"{display_name}: Writing to Signal Issue Stories...")

                # Build story data based on section type
                # Field names match Airtable schema (verified 1/13/26)
                if is_full_story:
                    # Main sections: headline, one_liner, lead, why_it_matters, whats_next
                    story_data = {
                        "issue_id": issue_id_text,
                        "section": section,
                        "pivot_id": pivot_id,
                        "headline": decoration.get("ai_headline", original_headline),
                        "one_liner": decoration.get("one_liner", ""),
                        "lead": decoration.get("lead", ""),
                        "signal_blurb": "",  # Not used for full stories
                        "why_it_matters": decoration.get("why_it_matters", ""),
                        "whats_next": decoration.get("whats_next", ""),
                        "source_attribution": f"via {source_id}" if source_id else "",
                        "raw": cleaned_content[:5000],  # Store for reference
                        "decoration_status": "decorated",
                    }
                else:
                    # SIGNALS items - headline + signal_blurb only
                    story_data = {
                        "issue_id": issue_id_text,
                        "section": section,  # signal_1, signal_2, etc.
                        "pivot_id": pivot_id,
                        "headline": decoration.get("ai_headline", original_headline),
                        "one_liner": "",  # Not used for signals
                        "lead": "",  # Not used for signals
                        "signal_blurb": decoration.get("signal_blurb", ""),
                        "why_it_matters": "",  # Not used for signals
                        "whats_next": "",  # Not used for signals
                        "source_attribution": f"via {decoration.get('source', source_id)}" if decoration.get('source') or source_id else "",
                        "raw": cleaned_content[:3000],
                        "decoration_status": "decorated",
                    }

                _log(f"{display_name}: Story data to write:")
                _log(f"  pivot_id: {story_data['pivot_id']}")
                _log(f"  section: {story_data['section']}")
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

    Output: ai_headline, one_liner, lead, why_it_matters, whats_next, source

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
  "ai_headline": "Title Case headline, max 80 chars, NO colons or semi-colons",
  "one_liner": "Single compelling sentence for At-a-Glance section (15-25 words)",
  "lead": "First sentence here.\\n\\nSecond sentence here.\\n\\nThird sentence here (if needed).",
  "why_it_matters": "• First bullet point with <b>key phrase</b> bolded.\\n• Second bullet point with <b>key phrase</b> bolded.",
  "whats_next": "• First bullet point with <b>key phrase</b> bolded.\\n• Second bullet point with <b>key phrase</b> bolded.",
  "source": "Publication name"
}}

## CRITICAL RULES

### Headline:
- Title Case (capitalize major words)
- Maximum 80 characters
- NO colons, semi-colons, or em-dashes
- One complete, scannable sentence

### One-Liner (At-a-Glance):
- Single sentence, 15-25 words
- Hook that makes reader want to learn more
- Must stand alone without context

### Lead:
- 2-3 sentences, ~50-75 words total
- CRITICAL FORMATTING: You MUST separate EVERY sentence with \\n\\n (double newline)
- Format: "Sentence one.\\n\\nSentence two.\\n\\nSentence three."
- Each sentence becomes its own visual paragraph
- Expand on the one-liner with key details
- Who, what, when, where

### Why It Matters:
- YOU MUST PROVIDE EXACTLY 2 BULLET POINTS - NOT 1, NOT 3, EXACTLY 2
- Format EXACTLY like this (two separate lines):
  • First bullet point with <b>key phrase</b> bolded.
  • Second bullet point with <b>key phrase</b> bolded.
- Each bullet starts with "• " (bullet character followed by space)
- Bullets separated by single line break (\\n)
- Use HTML <b>key phrase</b> tags to bold the most important phrase (5-15 words) in each bullet
- Explain relevance to reader
- Focus on business consequences

### What's Next:
- YOU MUST PROVIDE EXACTLY 2 BULLET POINTS - NOT 1, NOT 3, EXACTLY 2
- Format EXACTLY like this (two separate lines):
  • First bullet point with <b>key phrase</b> bolded.
  • Second bullet point with <b>key phrase</b> bolded.
- Each bullet starts with "• " (bullet character followed by space)
- Bullets separated by single line break (\\n)
- Use HTML <b>key phrase</b> tags to bold the most important phrase (5-15 words) in each bullet
- Forward-looking implications
- What to watch, competitive dynamics

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

        response_text = response.content[0].text
        try:
            result = json.loads(response_text)
            _log(f"  Full story decoration parsed successfully")
            return result
        except json.JSONDecodeError:
            _log(f"  Failed to parse JSON response, attempting extraction...")
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return {
                "error": "Failed to parse decoration response",
                "ai_headline": headline,
                "one_liner": "",
                "lead": "",
                "why_it_matters": "",
                "whats_next": "",
                "source": source_id
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

    Output: ai_headline, signal_blurb (EXACTLY 1 sentence - not 2, not 3), source

    Uses signal_signals_decorator prompt from database.
    CRITICAL: signal_blurb must be exactly ONE sentence only.
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
- One headline (max 60 chars)
- ONE SENTENCE ONLY of context (this is critical!)
- No bullets, no expanded treatment

## AUDIENCE
- Busy executives scanning for key developments
- Readers who want breadth, not depth
- "What else is happening in AI?"

## OUTPUT FORMAT
Return ONLY valid JSON:

{{
  "ai_headline": "Title Case headline, max 60 chars, NO colons",
  "signal_blurb": "EXACTLY ONE SENTENCE. Not two. Not three. ONE.",
  "source": "Publication name"
}}

## CRITICAL RULE FOR signal_blurb
⚠️ signal_blurb MUST be EXACTLY ONE SENTENCE.
- NOT two sentences. NOT three sentences. ONE SENTENCE ONLY.
- Count the periods. There should be exactly ONE period at the end.
- If you write more than one sentence, you have failed the task.
- Combine your key insight into a single, powerful sentence.
- Maximum 25 words in that ONE sentence.

## OTHER RULES
1. Headline: Title Case, max 60 characters, max 10 words
2. The single sentence should capture what happened and why it matters

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

        response_text = response.content[0].text
        try:
            result = json.loads(response_text)
            _log(f"  SIGNALS decoration parsed successfully")
            return result
        except json.JSONDecodeError:
            _log(f"  Failed to parse JSON response, attempting extraction...")
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return {
                "error": "Failed to parse decoration response",
                "ai_headline": headline,
                "signal_blurb": "",
                "source": source_id
            }
    except Exception as e:
        _log(f"  Decoration API error: {e}")
        return {"error": str(e)}


def _apply_signal_bolding(claude: ClaudeClient, decoration: dict) -> dict:
    """
    Apply HTML <b> tags to key phrases in why_it_matters and whats_next.

    Takes the decoration dict and applies HTML bold formatting.
    Uses a simple prompt to identify the most important phrase in each field.

    Args:
        claude: ClaudeClient instance
        decoration: Dict with why_it_matters and whats_next fields

    Returns:
        Dict with same fields but containing <b>phrase</b> HTML tags
    """
    _log(f"  Applying bolding to why_it_matters and whats_next...")

    prompt = f"""You are a formatting assistant. Add HTML bold tags to highlight the most important phrase in each field.

## INSTRUCTIONS
For each field (why_it_matters, whats_next):
1. Identify the SINGLE most important phrase (5-15 words) that captures the key information
2. Wrap that phrase in HTML bold tags: <b>phrase here</b>
3. Only bold ONE phrase per field
4. Do NOT bold entire sentences
5. Do NOT change any wording, punctuation, or content

## INPUT
why_it_matters: {decoration.get('why_it_matters', '')}
whats_next: {decoration.get('whats_next', '')}

## OUTPUT FORMAT
Return ONLY valid JSON with the bolded versions:

{{
  "why_it_matters": "Text with <b>key phrase</b> bolded.",
  "whats_next": "Text with <b>key phrase</b> bolded."
}}

Return ONLY the JSON object. No commentary."""

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

        response = client.messages.create(
            model='claude-sonnet-4-5-20250929',
            max_tokens=500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)
        _log(f"  Bolding applied successfully")
        return result
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        _log(f"  Failed to parse bolding response, using original")
        return decoration
    except Exception as e:
        _log(f"  Bolding API error: {e}")
        return decoration


# Job configuration for RQ
# NOTE: Typically triggered via API endpoint
# API endpoint: POST /api/signal/decorations
JOB_CONFIG = {
    "func": decorate_signal_stories,
    "id": "signal_step3_decoration",
    "queue": "default",
    "timeout": "30m",
}
