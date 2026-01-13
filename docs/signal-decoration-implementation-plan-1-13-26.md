# Signal Newsletter Decoration Implementation Plan

**Date:** January 13, 2026
**Reference:** [Signal Airtable Schema Verification](./signal-airtable-verification-1-13-26.md)
**Status:** Ready for Implementation

---

## Overview

This document outlines the implementation changes required to update the Signal decoration job to use the new Airtable schema with semantic field names.

---

## Field Name Mapping

### Before → After (Main Sections)

| Old Field Name | New Field Name | Purpose |
|----------------|----------------|---------|
| `story_id` | `pivot_id` | Unique story identifier |
| `summary` | `one_liner` | Single-sentence hook for At-a-Glance section |
| `paragraph` | `lead` | 2-3 sentence intro paragraph |
| `b1` | `why_it_matters` | 2 sentences explaining relevance (with HTML `<b>` bolding) |
| `b2` | `whats_next` | 2 sentences on implications/next steps (with HTML `<b>` bolding) |
| `b3` | *(removed)* | Consolidated into 2 bullets instead of 3 |
| `label` | `label` | Category tag - **NEEDS TO BE ADDED TO AIRTABLE** |
| `core_url` | `core_url` | Link to original article - **NEEDS TO BE ADDED TO AIRTABLE** |

### Before → After (Signals Section)

| Old Field Name | New Field Name | Purpose |
|----------------|----------------|---------|
| `story_id` | `pivot_id` | Unique story identifier |
| `summary` | `signal_blurb` | 2-sentence summary for quick-hit signals |
| `headline` | `headline` | *(unchanged)* |
| `source_attribution` | `source_attribution` | *(unchanged)* |

---

## Files to Update

### 1. `/workers/jobs/signal_decoration.py`

**Location:** Lines 249-287 (story_data dictionaries)

#### Current Code (Full Story):
```python
story_data = {
    "story_id": story_id,
    "issue_id": issue_id_text,
    "section": section,
    "slot_order": 1,
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
```

#### New Code (Full Story):
```python
story_data = {
    "issue_id": issue_id_text,
    "section": section,
    "slot_order": 1,
    "pivot_id": pivot_id,
    "headline": decoration.get("ai_headline", original_headline),
    "one_liner": decoration.get("one_liner", ""),
    "lead": decoration.get("lead", ""),
    "signal_blurb": "",  # Not used for full stories
    "why_it_matters": decoration.get("why_it_matters", ""),
    "whats_next": decoration.get("whats_next", ""),
    "source_attribution": f"via {source_id}" if source_id else "",
    "raw": cleaned_content[:5000],  # Store raw content for reference
    "decoration_status": "decorated",
    # NOTE: core_url and label fields need to be added to Airtable first
}
```

#### Current Code (Signals):
```python
story_data = {
    "story_id": story_id,
    "issue_id": issue_id_text,
    "section": "signal",
    "slot_order": signal_num,
    "source_slot": source_slot,
    "headline": decoration.get("ai_headline", original_headline),
    "summary": decoration.get("signal_summary", ""),
    "paragraph": "",
    "b1": "",
    "b2": "",
    "b3": "",
    "source_attribution": f"via {decoration.get('source', source_id)}" if decoration.get('source') or source_id else "",
    "pivot_id": pivot_id,
    "core_url": core_url,
    "decoration_status": "decorated",
    "label": "",
}
```

#### New Code (Signals):
```python
story_data = {
    "issue_id": issue_id_text,
    "section": f"signal_{signal_num}",  # Match section select options
    "slot_order": signal_num,
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
```

---

### 2. `/workers/jobs/signal_decoration.py` - Claude Prompts

**Location:** Lines 377-432 (`_decorate_full_story` fallback prompt)

#### Current Claude Output Format:
```json
{
  "label": "CATEGORY",
  "ai_headline": "...",
  "ai_dek": "...",
  "ai_bullet_1": "...",
  "ai_bullet_2": "...",
  "ai_bullet_3": "...",
  "source": "..."
}
```

#### New Claude Output Format:
```json
{
  "ai_headline": "Title Case headline, max 80 chars",
  "one_liner": "Single sentence hook for At-a-Glance section",
  "lead": "2-3 sentence intro paragraph when story is expanded",
  "why_it_matters": "2 sentences with key phrase in <b>bold</b> tags",
  "whats_next": "2 sentences with key phrase in <b>bold</b> tags",
  "source": "Publication name"
}
```

**Location:** Lines 507-544 (`_decorate_signal_item` fallback prompt)

#### Current SIGNALS Output Format:
```json
{
  "ai_headline": "...",
  "signal_summary": "...",
  "source": "..."
}
```

#### New SIGNALS Output Format:
```json
{
  "ai_headline": "Title Case headline, max 60 chars",
  "signal_blurb": "Exactly 2 sentences providing context",
  "source": "Publication name"
}
```

---

### 3. `/workers/utils/airtable.py`

**Location:** Lines 971-996 (`write_signal_story` docstring)

Update the docstring to reflect new field names:

```python
def write_signal_story(self, story_data: dict) -> str:
    """
    Write decorated story to Signal Issue Stories table.

    Expected story_data fields (updated 1/13/26):
        - issue_id: str (links to Signal Selected Slots)
        - section: str ('top_story', 'ai_at_work', 'emerging_moves', 'beyond_business',
                        'signal_1', 'signal_2', 'signal_3', 'signal_4', 'signal_5')
        - slot_order: int (1-5 for signals, 1 for main sections)
        - pivot_id: str (unique story identifier)
        - headline: str (max 80 chars, AI-rewritten)
        - one_liner: str (single sentence for At-a-Glance - main sections only)
        - lead: str (2-3 sentence intro - main sections only)
        - signal_blurb: str (2 sentences - signals only)
        - why_it_matters: str (2 sentences with <b> bolding - main sections only)
        - whats_next: str (2 sentences with <b> bolding - main sections only)
        - source_attribution: str (e.g., "via TechCrunch")
        - raw: str (cleaned article content for reference)
        - decoration_status: str ('undecorated', 'decorating', 'decorated')

    Returns:
        Record ID of created story
    """
```

**Location:** Lines 1013-1018 (`get_signal_stories_for_issue` fields)

Update fields list:
```python
fields=[
    'issue_id', 'section', 'slot_order', 'pivot_id',
    'headline', 'one_liner', 'lead', 'signal_blurb',
    'why_it_matters', 'whats_next',
    'source_attribution', 'raw', 'decoration_status'
]
```

**Location:** Lines 1060-1067 (`get_signal_stories_for_compile` fields)

Update fields list:
```python
fields=[
    'issue_id', 'section', 'slot_order', 'pivot_id',
    'headline', 'one_liner', 'lead', 'signal_blurb',
    'why_it_matters', 'whats_next',
    'source_attribution'
]
```

---

### 4. PostgreSQL Database Prompts

Add or update these prompts in the `system_prompts` table:

#### `signal_story_decorator` (for main sections)

```
You are an expert newsletter editor creating content for the Signal AI newsletter.

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

{
  "ai_headline": "Title Case headline, max 80 chars, NO colons or semi-colons",
  "one_liner": "Single compelling sentence summarizing the story for At-a-Glance",
  "lead": "2-3 sentences introducing the story. What happened and why it matters.",
  "why_it_matters": "2 sentences explaining relevance. Wrap key phrase in <b>bold</b> tags.",
  "whats_next": "2 sentences on implications or what to watch. Wrap key phrase in <b>bold</b> tags.",
  "source": "Publication name"
}

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
- 2-3 sentences, ~50-75 words
- Expand on the one-liner with key details
- Who, what, when, where

### Why It Matters:
- EXACTLY 2 sentences
- Explain relevance to reader
- Wrap one key phrase (5-10 words) in <b></b> tags

### What's Next:
- EXACTLY 2 sentences
- Forward-looking implications
- Wrap one key phrase (5-10 words) in <b></b> tags

=== ARTICLE METADATA ===
Headline: {headline}
Source: {source_id}
Section: {section_name}

=== ARTICLE CONTENT ===
{cleaned_content}

Return ONLY the JSON object. No commentary, no code fences.
```

#### `signal_signals_decorator` (for signals section)

```
You are an expert newsletter editor creating quick-hit content for the SIGNALS section.

## SIGNALS Format
Each SIGNALS item is a quick scan:
- One headline (max 60 chars)
- Two sentences of context
- No expanded treatment, no bullets

## AUDIENCE
- Busy executives scanning for key developments
- Readers who want breadth, not depth
- "What else is happening in AI?"

## OUTPUT FORMAT
Return ONLY valid JSON:

{
  "ai_headline": "Title Case headline, max 60 chars, NO colons",
  "signal_blurb": "EXACTLY 2 sentences providing context and why this matters.",
  "source": "Publication name"
}

## RULES
1. Headline: Title Case, max 60 characters, max 10 words
2. Signal Blurb: EXACTLY 2 sentences - not 1, not 3
3. First sentence: What happened
4. Second sentence: Why it matters or what it means
5. Keep total blurb under 40 words
6. No HTML bolding for signals

=== ARTICLE METADATA ===
Headline: {headline}
Source: {source_id}

=== ARTICLE CONTENT ===
{cleaned_content}

Return ONLY the JSON object. No commentary.
```

---

## Airtable Schema Updates Required

Before implementing, these fields must be added to Signal - Issue Stories:

| Field Name | Type | Purpose |
|------------|------|---------|
| `core_url` | url | Link to original article |
| `label` | singleSelect | Category tag with options: WORK, EDUCATION, INFRASTRUCTURE, POLICY, TALENT, HEALTH, RETAIL, ENTERPRISE, COMPETITION, FUNDING, SECURITY, TOOLS, SEARCH, INVESTORS, CHINA, REGULATION, ETHICS, LAWSUITS |

---

## Implementation Order

1. **Pre-requisite:** Add `core_url` and `label` fields to Airtable (optional - can skip if not needed immediately)

2. **Update PostgreSQL prompts:**
   - Add `signal_story_decorator` prompt with new output format
   - Add `signal_signals_decorator` prompt with new output format

3. **Update `/workers/jobs/signal_decoration.py`:**
   - Modify `_decorate_full_story()` to use new field names in prompt and return
   - Modify `_decorate_signal_item()` to use `signal_blurb` instead of `signal_summary`
   - Update story_data dictionaries in main function
   - Remove `b3` references (now using 2 bullets instead of 3)

4. **Update `/workers/utils/airtable.py`:**
   - Update `write_signal_story()` docstring
   - Update `get_signal_stories_for_issue()` fields list
   - Update `get_signal_stories_for_compile()` fields list

5. **Test locally:**
   - Run decoration job on test issue
   - Verify fields are written correctly to Airtable
   - Check HTML bolding is applied to `why_it_matters` and `whats_next`

6. **Deploy to Render:**
   - Push changes to main branch
   - Monitor first production run

---

## HTML Email Structure Reference

The new field structure supports this email layout:

### At-a-Glance Section (top of email)
```
TOP STORY: {headline}
{one_liner}

AI AT WORK: {headline}
{one_liner}

EMERGING MOVES: {headline}
{one_liner}

BEYOND BUSINESS: {headline}
{one_liner}
```

### Main Story Sections (expanded)
```
{label}
{headline}

{lead}

Why It Matters: {why_it_matters}

What's Next: {whats_next}

{source_attribution}
```

### Signals Section (bottom of email)
```
SIGNALS

{headline}
{signal_blurb}
{source_attribution}

{headline}
{signal_blurb}
{source_attribution}

... (5 total)
```

---

## Notes

- The `raw` field stores cleaned article content for reference/debugging
- HTML `<b>` bolding is only applied to `why_it_matters` and `whats_next` fields
- Signals use `signal_blurb` with no bolding
- The `section` field values must match Airtable select options exactly:
  - `top_story`, `ai_at_work`, `emerging_moves`, `beyond_business`
  - `signal_1`, `signal_2`, `signal_3`, `signal_4`, `signal_5`
