"""
Signal Newsletter: Slot Selection Job
Added 1/12/26 for Signal Newsletter pipeline

Schedule: TBD (separate from Pivot 5)

Signal Newsletter uses a DIFFERENT selection approach than Pivot 5:
- Selection order: Slot 1 -> Slot 3 -> Slot 4 -> Slot 5 -> Slot 2 (x5)
- Sections: TOP STORY, AI AT WORK, EMERGING MOVES, BEYOND BUSINESS, SIGNALS (5 items)
- Freshness: 24h for Slot 1, 72h for all others (no weekend extension)
- Deduplication: By pivot_id from Signal Selected Slots table
- NO source diversity checks (unlike Pivot 5)

IMPORTANT: Signal uses its own Airtable base (appWGkUBuyrzmFnFM) for:
- Signal Selected Slots table
- Signal Issue Stories table
But shares the Pre-Filter Log table with Pivot 5 (in AI Editor 2.0 base)
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.claude import ClaudeClient

# EST timezone (UTC-5) for newsletter scheduling
# Signal is for US East Coast readers, so all date calculations must use EST
EST = timezone(timedelta(hours=-5))

# Signal-specific freshness windows (in hours)
# TOP STORY needs to be fresh; other sections have more flexibility
SIGNAL_SLOT_FRESHNESS_HOURS = {
    1: 24,   # TOP STORY: 24 hours for breaking news
    2: 72,   # SIGNALS: 72 hours
    3: 72,   # AI AT WORK: 72 hours
    4: 72,   # EMERGING MOVES: 72 hours
    5: 72,   # BEYOND BUSINESS: 72 hours
}

# Selection order for Signal Newsletter
# Different from Pivot 5 - designed to build cumulative context
SIGNAL_SELECTION_ORDER = [
    (1, "top_story", "TOP STORY"),
    (3, "ai_at_work", "AI AT WORK"),
    (4, "emerging", "EMERGING MOVES"),
    (5, "beyond", "BEYOND BUSINESS"),
    (2, "signal", "SIGNALS"),  # Selects 5 stories
]

# Lookback window for pivot_id deduplication
DUPLICATE_LOOKBACK_DAYS = 14


def get_signal_issue_date() -> tuple[str, str]:
    """
    Calculate the next Signal newsletter issue date with weekend skipping.

    Uses same logic as Pivot 5 - newsletter runs Tue-Sat for Mon-Fri issues.

    Returns:
        Tuple of (issue_date_iso, issue_date_label)
        e.g., ('2026-01-12', 'Signal - Jan 12')
    """
    now = datetime.now(EST)
    weekday = now.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

    print(f"[Signal Selection] Date calculation: EST now = {now.strftime('%Y-%m-%d %H:%M %Z')}, weekday = {weekday}")

    # Calculate next issue date based on day of week
    if weekday == 4:  # Friday -> Monday (skip Sat/Sun)
        next_issue = now + timedelta(days=3)
    elif weekday == 5:  # Saturday -> Monday (skip Sun)
        next_issue = now + timedelta(days=2)
    else:
        next_issue = now + timedelta(days=1)

    issue_date_iso = next_issue.strftime('%Y-%m-%d')
    issue_date_label = f"Signal - {next_issue.strftime('%b %d')}"

    return issue_date_iso, issue_date_label


def format_candidates_for_prompt(candidates: List[dict]) -> str:
    """
    Format candidates list for insertion into Claude prompt.

    Args:
        candidates: List of candidate records from Pre-Filter Log

    Returns:
        Formatted string of candidates for the prompt
    """
    formatted = []
    for i, c in enumerate(candidates, 1):
        fields = c.get('fields', {})
        formatted.append(f"""
### Candidate {i}
- **storyID:** {fields.get('storyID', 'N/A')}
- **pivotId:** {fields.get('pivotId', 'N/A')}
- **Headline:** {fields.get('headline', 'N/A')}
- **Source:** {fields.get('source_id', 'N/A')}
- **Published:** {fields.get('date_og_published', 'N/A')}
- **URL:** {fields.get('core_url', 'N/A')}
""")
    return "\n".join(formatted)


def build_recent_headlines_text(
    current_slot: int,
    current_run_selections: dict,
    recent_pivot_ids: List[str],
    recent_headlines: List[str]
) -> str:
    """
    Build recent headlines string for pivot_id deduplication.

    Combines:
    1. Stories selected earlier in the current run (by slot order)
    2. Stories from recent Signal issues (pivot_ids and headlines)

    Args:
        current_slot: The slot being selected (1, 2, 3, 4, or 5)
        current_run_selections: Dict of {slot_num: selection_dict} from current run
        recent_pivot_ids: List of pivot_ids from recent Signal issues
        recent_headlines: List of headlines from recent Signal issues

    Returns:
        Formatted string of headlines with pivot_ids for the prompt
    """
    headline_entries = []
    seen_pivot_ids = set()

    # 1. Add selections from earlier slots in THIS run
    # Selection order: 1 -> 3 -> 4 -> 5 -> 2
    slot_order = [1, 3, 4, 5, 2]
    try:
        current_slot_index = slot_order.index(current_slot)
    except ValueError:
        current_slot_index = 0

    for slot in slot_order[:current_slot_index]:
        if slot in current_run_selections:
            selection = current_run_selections[slot]

            # Handle single selections (slots 1, 3, 4, 5)
            if isinstance(selection, dict):
                pivot_id = selection.get('selected_pivotId')
                headline = selection.get('selected_headline')
                if pivot_id and pivot_id not in seen_pivot_ids:
                    seen_pivot_ids.add(pivot_id)
                    headline_entries.append(f"- [{pivot_id}] {headline} (today's issue)")

            # Handle multiple selections (slot 2 = SIGNALS x5)
            elif isinstance(selection, list):
                for item in selection:
                    pivot_id = item.get('selected_pivotId')
                    headline = item.get('selected_headline')
                    if pivot_id and pivot_id not in seen_pivot_ids:
                        seen_pivot_ids.add(pivot_id)
                        headline_entries.append(f"- [{pivot_id}] {headline} (today's issue)")

    # 2. Add recent pivot_ids from Signal Selected Slots (lookback period)
    for pivot_id, headline in zip(recent_pivot_ids, recent_headlines):
        if pivot_id and pivot_id not in seen_pivot_ids:
            seen_pivot_ids.add(pivot_id)
            headline_entries.append(f"- [{pivot_id}] {headline}")

    if not headline_entries:
        return "None - this is the first selection"

    return "\n".join(headline_entries)


def build_selected_companies_text(current_run_selections: dict) -> str:
    """
    Build cumulative list of companies selected so far.

    Signal tracks companies to avoid multiple stories about the same company
    in one issue.

    Args:
        current_run_selections: Dict of {slot_num: selection_dict} from current run

    Returns:
        Formatted string of companies for the prompt
    """
    companies = []

    # Selection order: 1 -> 3 -> 4 -> 5 (don't include slot 2 which runs last)
    for slot in [1, 3, 4, 5]:
        if slot in current_run_selections:
            selection = current_run_selections[slot]
            company = selection.get('selected_company')
            if company and company.lower() not in ['null', 'none', 'n/a', ''] and company not in companies:
                companies.append(company)

    if not companies:
        return "None - this is the first selection"

    return "\n".join([f"- {company}" for company in companies])


def select_signal_slots() -> dict:
    """
    Signal Newsletter: Slot Selection - Main entry point

    Flow:
    1. Get recent Signal issues for pivot_id deduplication
    2. For each section in selection order:
       a. Get pre-filter candidates for that slot
       b. Filter out already-used pivot_ids
       c. Call Claude agent with cumulative state
       d. Track selected story and company
    3. Generate subject line from section headlines
    4. Write to Signal Selected Slots table

    Returns:
        {slots_filled: int, signals_filled: int, subject_line: str, record_id: str, errors: list}
    """
    print(f"[Signal Selection] Starting slot selection at {datetime.utcnow().isoformat()}")

    # Initialize clients
    airtable = AirtableClient()
    claude = ClaudeClient()

    # Track results
    results = {
        "slots_filled": 0,      # Main sections (4)
        "signals_filled": 0,    # SIGNALS items (5)
        "subject_line": "",
        "record_id": "",
        "errors": []
    }

    try:
        # 1. Get recent Signal issues for deduplication
        print(f"[Signal Selection] Fetching recent Signal issues (last {DUPLICATE_LOOKBACK_DAYS} days)...")
        used_pivot_ids = airtable.get_signal_used_pivot_ids(DUPLICATE_LOOKBACK_DAYS)
        recent_headlines = airtable.get_signal_recent_headlines(DUPLICATE_LOOKBACK_DAYS)
        print(f"[Signal Selection] Found {len(used_pivot_ids)} used pivot_ids, {len(recent_headlines)} recent headlines")

        # 2. Initialize cumulative state for tracking across slots
        current_run_selections = {}  # {slot_num: selection_dict or list}
        excluded_pivot_ids = set(used_pivot_ids)

        # 3. Build today's issue data
        issue_date_iso, issue_date_label = get_signal_issue_date()
        print(f"[Signal Selection] Next issue date: {issue_date_label}")

        issue_data = {
            "issue_date": issue_date_iso,
            "issue_id": issue_date_label,
            "status": "pending"
        }

        section_headlines = {}  # For subject line generation

        # 4. Process each section in selection order
        for slot, section_key, section_name in SIGNAL_SELECTION_ORDER:
            print(f"[Signal Selection] Processing {section_name} (Slot {slot})...")

            try:
                # Get pre-filter candidates for this slot
                freshness_hours = SIGNAL_SLOT_FRESHNESS_HOURS.get(slot, 72)
                candidates = airtable.get_signal_candidates(slot, freshness_hours)
                print(f"[Signal Selection] {section_name}: Found {len(candidates)} candidates")

                if not candidates:
                    results["errors"].append({
                        "section": section_name,
                        "slot": slot,
                        "error": "No candidates available"
                    })
                    continue

                # Filter out already-selected pivot_ids
                available_candidates = [
                    c for c in candidates
                    if c.get('fields', {}).get('pivotId') not in excluded_pivot_ids
                ]

                filtered_count = len(candidates) - len(available_candidates)
                if filtered_count > 0:
                    print(f"[Signal Selection] {section_name}: Filtered out {filtered_count} already-used pivot_ids")

                if not available_candidates:
                    results["errors"].append({
                        "section": section_name,
                        "slot": slot,
                        "error": "All candidates already selected"
                    })
                    continue

                print(f"[Signal Selection] {section_name}: {len(available_candidates)} available after filtering")

                # Build prompt context
                candidates_text = format_candidates_for_prompt(available_candidates)
                recent_headlines_text = build_recent_headlines_text(
                    slot, current_run_selections, list(excluded_pivot_ids), recent_headlines
                )
                selected_companies_text = build_selected_companies_text(current_run_selections)

                # Call Claude for selection
                if section_key == "signal":
                    # SIGNALS section: Select 5 stories
                    selection = _select_signals(
                        claude, available_candidates, candidates_text,
                        recent_headlines_text, selected_companies_text
                    )

                    if "error" in selection:
                        results["errors"].append({
                            "section": section_name,
                            "slot": slot,
                            "error": selection.get("error")
                        })
                        continue

                    # Process 5 signal selections
                    signals = selection.get("signals", [])
                    for i, sig in enumerate(signals, 1):
                        pivot_id = sig.get("selected_pivotId")
                        if pivot_id:
                            excluded_pivot_ids.add(pivot_id)
                            issue_data[f"signal_{i}_story_id"] = sig.get("selected_id", "")
                            issue_data[f"signal_{i}_pivot_id"] = pivot_id
                            results["signals_filled"] += 1

                    current_run_selections[slot] = signals
                    print(f"[Signal Selection] SIGNALS: Selected {len(signals)} items")

                else:
                    # Main sections: Select 1 story
                    selection = _select_single_slot(
                        claude, slot, section_key, section_name,
                        available_candidates, candidates_text,
                        recent_headlines_text, selected_companies_text
                    )

                    if "error" in selection:
                        results["errors"].append({
                            "section": section_name,
                            "slot": slot,
                            "error": selection.get("error")
                        })
                        continue

                    # Extract selection results
                    pivot_id = selection.get("selected_pivotId")
                    headline = selection.get("selected_headline", "")

                    if pivot_id:
                        excluded_pivot_ids.add(pivot_id)

                    # Update issue data with section-specific field names
                    issue_data[f"{section_key}_story_id"] = selection.get("selected_id", "")
                    issue_data[f"{section_key}_pivot_id"] = pivot_id or ""

                    current_run_selections[slot] = selection
                    section_headlines[section_key] = headline
                    results["slots_filled"] += 1

                    print(f"[Signal Selection] {section_name}: Selected '{headline[:50]}...'")

            except Exception as e:
                print(f"[Signal Selection] Error processing {section_name}: {e}")
                import traceback
                traceback.print_exc()
                results["errors"].append({
                    "section": section_name,
                    "slot": slot,
                    "error": str(e)
                })

        # 5. Generate subject line from main section headlines
        if section_headlines:
            print("[Signal Selection] Generating subject line...")
            try:
                subject_line = _generate_signal_subject_line(
                    claude, section_headlines
                )
                issue_data["subject_line"] = subject_line
                results["subject_line"] = subject_line
                print(f"[Signal Selection] Subject line: {subject_line}")
            except Exception as e:
                print(f"[Signal Selection] Error generating subject line: {e}")
                results["errors"].append({
                    "step": "subject_line",
                    "error": str(e)
                })

        # 6. Write to Signal Selected Slots table
        total_selections = results["slots_filled"] + results["signals_filled"]
        if total_selections > 0:
            print("[Signal Selection] Writing to Signal Selected Slots table...")
            try:
                record_id = airtable.create_signal_issue(issue_data)
                results["record_id"] = record_id
                print(f"[Signal Selection] Created record: {record_id}")
            except Exception as e:
                print(f"[Signal Selection] Error writing signal slots: {e}")
                results["errors"].append({
                    "step": "write_slots",
                    "error": str(e)
                })

        print(f"[Signal Selection] Slot selection complete: {results}")
        return results

    except Exception as e:
        print(f"[Signal Selection] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        results["errors"].append({"fatal": str(e)})
        raise


def _select_single_slot(
    claude: ClaudeClient,
    slot: int,
    section_key: str,
    section_name: str,
    candidates: List[dict],
    candidates_text: str,
    recent_headlines_text: str,
    selected_companies_text: str
) -> dict:
    """
    Call Claude to select a single story for a main section.

    Args:
        claude: ClaudeClient instance
        slot: Slot number (1, 3, 4, or 5)
        section_key: Section key for prompt lookup (top_story, ai_at_work, etc.)
        section_name: Human-readable section name
        candidates: List of candidate records
        candidates_text: Formatted candidates for prompt
        recent_headlines_text: Recent headlines for deduplication
        selected_companies_text: Companies already selected today

    Returns:
        Selection dict with selected_id, selected_pivotId, selected_headline, etc.
    """
    # Map section keys to prompt keys
    prompt_key_map = {
        "top_story": "signal_top_story_agent",
        "ai_at_work": "signal_ai_at_work_agent",
        "emerging": "signal_emerging_moves_agent",
        "beyond": "signal_beyond_business_agent"
    }

    prompt_key = prompt_key_map.get(section_key)
    if not prompt_key:
        return {"error": f"Unknown section key: {section_key}"}

    # Get prompt from database and fill placeholders
    try:
        prompt_template = claude.get_prompt_content(prompt_key)
        if not prompt_template:
            # Fallback: Use a basic selection prompt
            print(f"[Signal Selection] Warning: No prompt found for {prompt_key}, using fallback")
            prompt_template = _get_fallback_prompt(section_name)

        # Fill placeholders
        prompt = prompt_template.format(
            candidates=candidates_text,
            candidate_count=len(candidates),
            recent_headlines=recent_headlines_text,
            selected_companies=selected_companies_text
        )

        # Call Claude
        response = claude.call_claude_raw(prompt)

        # Parse JSON response
        selection = _parse_json_response(response)
        if not selection:
            return {"error": "Failed to parse Claude response as JSON"}

        # Validate required fields
        if not selection.get("selected_pivotId"):
            # Try to look up pivotId from candidate list
            selected_id = selection.get("selected_id", "")
            for c in candidates:
                if c.get('fields', {}).get('storyID') == selected_id:
                    selection["selected_pivotId"] = c.get('fields', {}).get('pivotId', '')
                    break

        return selection

    except Exception as e:
        print(f"[Signal Selection] Error in _select_single_slot: {e}")
        return {"error": str(e)}


def _select_signals(
    claude: ClaudeClient,
    candidates: List[dict],
    candidates_text: str,
    recent_headlines_text: str,
    selected_companies_text: str
) -> dict:
    """
    Call Claude to select 5 stories for the SIGNALS section.

    Args:
        claude: ClaudeClient instance
        candidates: List of candidate records
        candidates_text: Formatted candidates for prompt
        recent_headlines_text: Recent headlines for deduplication
        selected_companies_text: Companies already selected today

    Returns:
        Dict with "signals" key containing list of 5 selections
    """
    try:
        prompt_template = claude.get_prompt_content("signal_signals_agent")
        if not prompt_template:
            print("[Signal Selection] Warning: No prompt found for signal_signals_agent, using fallback")
            prompt_template = _get_fallback_signals_prompt()

        # Fill placeholders
        prompt = prompt_template.format(
            candidates=candidates_text,
            candidate_count=len(candidates),
            recent_headlines=recent_headlines_text,
            selected_companies=selected_companies_text
        )

        # Call Claude
        response = claude.call_claude_raw(prompt)

        # Parse JSON response
        selection = _parse_json_response(response)
        if not selection:
            return {"error": "Failed to parse Claude response as JSON"}

        # Validate we got 5 signals
        signals = selection.get("signals", [])
        if len(signals) < 5:
            print(f"[Signal Selection] Warning: Claude only selected {len(signals)} signals, expected 5")

        # Look up pivot_ids if not returned
        for sig in signals:
            if not sig.get("selected_pivotId"):
                selected_id = sig.get("selected_id", "")
                for c in candidates:
                    if c.get('fields', {}).get('storyID') == selected_id:
                        sig["selected_pivotId"] = c.get('fields', {}).get('pivotId', '')
                        break

        return {"signals": signals}

    except Exception as e:
        print(f"[Signal Selection] Error in _select_signals: {e}")
        return {"error": str(e)}


def _generate_signal_subject_line(
    claude: ClaudeClient,
    section_headlines: dict
) -> str:
    """
    Generate subject line for Signal newsletter.

    Args:
        claude: ClaudeClient instance
        section_headlines: Dict of {section_key: headline}

    Returns:
        Subject line string
    """
    try:
        prompt_template = claude.get_prompt_content("signal_subject_line")
        if not prompt_template:
            # Fallback: Use a simple template
            return section_headlines.get('top_story', 'AI News Today')[:90]

        # Fill placeholders
        prompt = prompt_template.format(
            top_story_headline=section_headlines.get('top_story', ''),
            ai_at_work_headline=section_headlines.get('ai_at_work', ''),
            emerging_moves_headline=section_headlines.get('emerging', ''),
            beyond_business_headline=section_headlines.get('beyond', '')
        )

        # Call Claude
        response = claude.call_claude_raw(prompt)

        # Subject line should be plain text
        return response.strip().strip('"')[:90]

    except Exception as e:
        print(f"[Signal Selection] Error generating subject line: {e}")
        # Fallback
        return section_headlines.get('top_story', 'AI News Today')[:90]


def _parse_json_response(response: str) -> Optional[dict]:
    """
    Parse JSON from Claude response, handling code fences.

    Args:
        response: Raw response string from Claude

    Returns:
        Parsed dict or None if parsing fails
    """
    if not response:
        return None

    # Clean up response
    text = response.strip()

    # Remove code fences if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[Signal Selection] JSON parse error: {e}")
        print(f"[Signal Selection] Response was: {text[:500]}...")
        return None


def _get_fallback_prompt(section_name: str) -> str:
    """Fallback prompt if database prompt is not found."""
    return f"""You are selecting ONE story for **{section_name}** in the Signal newsletter.

## CANDIDATES ({{candidate_count}} stories)
{{candidates}}

## AVOID - Recent Headlines
{{recent_headlines}}

## AVOID - Companies Already Featured Today
{{selected_companies}}

## OUTPUT
Return ONLY valid JSON:
{{{{
  "selected_id": "storyID from candidate",
  "selected_pivotId": "pivotId from candidate",
  "selected_headline": "headline text",
  "selected_source": "source_name",
  "selected_company": "primary company or null",
  "reasoning": "2-3 sentences explaining selection"
}}}}
"""


def _get_fallback_signals_prompt() -> str:
    """Fallback prompt for SIGNALS section if database prompt is not found."""
    return """You are selecting FIVE stories for the **SIGNALS** section.

## CANDIDATES ({candidate_count} stories)
{candidates}

## AVOID - Recent Headlines
{recent_headlines}

## AVOID - Companies Already Featured Today
{selected_companies}

## OUTPUT
Return ONLY valid JSON with exactly 5 selections:
{{
  "signals": [
    {{
      "selected_id": "storyID",
      "selected_pivotId": "pivotId",
      "selected_headline": "headline",
      "selected_source": "source_name",
      "reasoning": "1 sentence"
    }},
    // ... repeat for 5 items
  ]
}}
"""


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": select_signal_slots,
    "trigger": "cron",
    "hour": 5,  # 5 AM UTC = 12:00 AM EST (midnight)
    "minute": 0,
    "day_of_week": "tue-sat",  # Mon-Fri in EST
    "id": "signal_slot_selection",
    "replace_existing": True
}
