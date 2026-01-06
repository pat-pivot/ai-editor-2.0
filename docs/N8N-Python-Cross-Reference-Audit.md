# N8N vs Python Implementation Cross-Reference Audit

**Date:** 2025-12-31
**Workflow:** SZmPztKNEmisG3Zf (Step 2: Slot Selection)
**Status:** CRITICAL GAPS IDENTIFIED

---

## Executive Summary

This audit compares the n8n workflow `SZmPztKNEmisG3Zf` against our Python implementation to identify all data flow gaps. The analysis reveals **multiple critical differences** that can cause duplicate story selection and other bugs.

### Critical Finding

The Python implementation was **NOT passing recent headlines to Claude for semantic deduplication** - only storyIDs. This has been partially fixed, but additional gaps remain.

---

## Table of Contents

1. [Slot Agent Data Flow Comparison](#1-slot-agent-data-flow-comparison)
2. [Candidate Data Structure](#2-candidate-data-structure)
3. [Context Tracking Variables](#3-context-tracking-variables)
4. [Subject Line Generator](#4-subject-line-generator)
5. [Critical Gaps Summary](#5-critical-gaps-summary)
6. [Recommendations](#6-recommendations)

---

## 1. Slot Agent Data Flow Comparison

### N8N Claude Agent Inputs (Per Slot)

The n8n workflow passes the following JSON structure to each Claude agent:

```javascript
{
  candidates: [                           // Array of formatted candidates
    {
      storyID: "...",
      headline: "...",
      source_name: "...",                 // Extracted from source_id or URL
      date_og_published: "...",
      primary_company: "...",             // From fields.primary_company or fields.company
      pivotId: "...",
      url: "..."                          // core_url or decorated_url
    }
  ],
  candidateCount: number,                 // candidates.length
  recentHeadlines: string[],              // ALL headlines from 14-day lookback
  recentStoryIds: string[],               // ALL storyIDs from 14-day lookback
  yesterdayHeadlines: string[],           // Same as recentHeadlines (backward compat)
  yesterdayStoryIds: string[],            // Same as recentStoryIds (backward compat)
  yesterdaySlot1Company: string|null,     // For Slot 1 two-day rotation rule
  previouslySelectedIds: string[],        // StoryIDs selected in earlier slots TODAY
  previouslySelectedCompanies: string[],  // Companies selected in earlier slots TODAY
  previouslySelectedSources: {            // Source counts from earlier slots TODAY
    "TechCrunch": 1,
    "Bloomberg": 1
  },
  recentIssueCount: number                // Number of recent issues loaded
}
```

### Python Claude Agent Inputs (Current Implementation)

From `claude.py` `select_slot()` method:

```python
# Arguments passed:
slot: int
candidates: List[dict]                    # Raw Airtable records
recent_data: dict                         # From _extract_recent_issues_data()
cumulative_state: dict                    # {selectedToday, selectedCompanies, selectedSources}
```

#### What Python Passes to Claude System Prompt:

```python
# From _build_slot_system_prompt():
selected_stories = cumulative_state.selectedToday    # storyIDs as list
selected_companies = cumulative_state.selectedCompanies
selected_sources = cumulative_state.selectedSources
yesterday_slot = sample_headlines[slot-1]            # Single headline sample

# Recent headlines section (ADDED after bug discovery):
recent_headlines[:30]                                 # Up to 30 headlines for semantic dedup
recent_story_ids[:20]                                # Story IDs to avoid
```

#### What Python Passes to Claude User Prompt:

From `_build_slot_user_prompt()`:

```python
# Per candidate:
- storyID: fields.get('storyID', '')
- pivotId: fields.get('pivotId', '')
- headline: fields.get('headline', '')
- source: fields.get('source_id', '')
- published: fields.get('date_og_published', '')
```

---

## 2. Candidate Data Structure

### Gap #1: Missing Fields in Candidate Formatting

| Field | N8N | Python | Status |
|-------|-----|--------|--------|
| `storyID` | Yes | Yes | OK |
| `headline` | Yes | Yes | OK |
| `source_name` | Yes (extracted from URL if needed) | `source_id` (raw) | **DIFFERENT** |
| `date_og_published` | Yes | Yes | OK |
| `primary_company` | Yes | **NO** | **MISSING** |
| `pivotId` | Yes | Yes | OK |
| `url` | Yes (core_url) | **NO** | **MISSING** |
| `credibility_score` | Referenced in prompts | **NO** | **MISSING** |

### Gap #2: Source Name Extraction

**N8N Implementation:**
```javascript
const extractSourceFromUrl = (url) => {
  const hostname = new URL(url).hostname.replace('www.', '');
  const domainMap = {
    'techcrunch.com': 'TechCrunch',
    'theverge.com': 'The Verge',
    'bloomberg.com': 'Bloomberg',
    // ... etc
  };
  return domainMap[hostname] || hostname.split('.')[0];
};
```

**Python Implementation:**
- Uses raw `source_id` field directly
- No URL-based extraction fallback
- No domain name normalization

---

## 3. Context Tracking Variables

### Gap #3: recentHeadlines Semantic Deduplication

**N8N Prompt (Slots 2-5):**
```
### Rule 1: Recent Headlines (Last 14 Days)
**CRITICAL: Semantic Deduplication** - Do NOT select any story about
the same topic/event as these recent headlines. Consider headlines
as duplicates if they cover:
- The same announcement, deal, acquisition, or news event
- The same company action with different wording
- The same research study, product launch, or partnership

{{ JSON.stringify($json.recentHeadlines, null, 2) }}
```

**Python (After Fix):**
```python
# In _build_slot_system_prompt():
if recent_headlines:
    prompt += "\n\n### RECENT HEADLINES (Last 14 Days) - CRITICAL SEMANTIC DEDUPLICATION"
    prompt += "\nDo NOT select any story about the same topic/event..."
    for i, headline in enumerate(recent_headlines[:30], 1):
        prompt += f"\n{i}. {headline}"
```

**Status:** FIXED in claude.py, but:
- Missing the explicit duplicate criteria explanation
- Wording differs slightly from n8n
- No JSON.stringify formatting

### Gap #4: previouslySelectedSources Structure

**N8N Format:**
```javascript
previouslySelectedSources: {
  "TechCrunch": 1,
  "Bloomberg": 1
}
```

**Python Format:**
```python
selected_sources = ', '.join(selected_sources) if selected_sources else '(none yet)'
# Outputs: "source1, source2, source3"
```

**Issue:** Python passes a comma-separated string; n8n passes an object with counts. The "max 2 per source" rule cannot be enforced with the Python format.

### Gap #5: candidateCount Display

**N8N:**
```
## CANDIDATES ({{ $json.candidateCount }} stories)
```

**Python:**
- No explicit candidate count shown to Claude
- Candidates are just listed without count context

### Gap #6: credibility_score Inclusion

**N8N Candidate Format:**
```javascript
{
  storyID: "...",
  headline: "...",
  source_name: "...",
  credibility_score: 4,  // From source scores table
  date_og_published: "...",
  primary_company: "..."
}
```

**Python:**
- Fetches source scores in `airtable.py` (`build_source_lookup()`)
- BUT these scores are NOT included in candidate data passed to Claude
- The claude.py `_build_slot_user_prompt()` does NOT include credibility_score

---

## 4. Subject Line Generator

### N8N Implementation

**Input:**
```javascript
{
  allHeadlines: [
    slot1.selection?.selected_headline,
    slot2.selection?.selected_headline,
    slot3.selection?.selected_headline,
    slot4.selection?.selected_headline,
    slot5Selection?.selected_headline
  ].filter(Boolean)
}
```

**Prompt:**
- Detailed deliverability/anti-spam guardrails
- Title case rules
- Examples provided
- 90 character limit
- References "THE 5 STORIES FOR TODAY'S NEWSLETTER"

### Python Implementation

**Input:** `headlines: List[str]` (list of 5 headlines)

**Prompt (from database or fallback):**
```python
# Fallback prompt:
"""Generate a compelling email subject line for this daily AI newsletter.

TODAY'S HEADLINES:
1. {headlines[0]}
2. {headlines[1]}
...

REQUIREMENTS:
- Maximum 60 characters  # DIFFERENT - n8n says 90
- Create urgency and curiosity
- Reference 1-2 key stories
- Avoid clickbait, be substantive
- Match professional newsletter tone
"""
```

### Gap #7: Subject Line Prompt Differences

| Aspect | N8N | Python |
|--------|-----|--------|
| Character limit | 90 | 60 |
| Anti-spam rules | Detailed (20+ rules) | None |
| Title case rules | Explicit | None |
| Examples | 3 examples provided | None |
| Format | "PIVOT 5 EMAIL COPY PROMPT" | Simple prompt |

---

## 5. Critical Gaps Summary

### SEVERITY: CRITICAL

| Gap | Description | Impact |
|-----|-------------|--------|
| **#1** | Missing `credibility_score` in candidates | Claude cannot weigh source quality |
| **#2** | Missing `primary_company` in candidates | Cannot enforce company diversity |
| **#3** | Source counts not object format | "Max 2 per source" rule broken |
| **#4** | Missing `url` field in candidates | No fallback for source extraction |

### SEVERITY: HIGH

| Gap | Description | Impact |
|-----|-------------|--------|
| **#5** | No candidate count shown | Less context for Claude |
| **#6** | Subject line prompt differs significantly | Deliverability issues, format inconsistency |
| **#7** | Source name not normalized | "techcrunch.com" vs "TechCrunch" mismatches |

### SEVERITY: MEDIUM

| Gap | Description | Impact |
|-----|-------------|--------|
| **#8** | Prompt wording differs | Slightly different Claude behavior |
| **#9** | Slot 1 uses `yesterdayHeadlines` vs `recentHeadlines` | Minor semantic difference |

---

## 6. Recommendations

### Immediate Fixes Required

1. **Add credibility_score to candidates**
   - File: `claude.py` `_build_slot_user_prompt()`
   - Load source scores lookup, add to each candidate

2. **Add primary_company to candidates**
   - File: `airtable.py` `get_prefilter_candidates()`
   - Include `primary_company` field in query

3. **Change source tracking to object with counts**
   - File: `slot_selection.py`
   - Change `cumulative_state["selectedSources"]` from list to dict
   - Track counts: `{"TechCrunch": 1, "Bloomberg": 1}`

4. **Add URL to candidates**
   - File: `airtable.py` `get_prefilter_candidates()`
   - Already fetches `core_url` - verify it's passed through

5. **Update subject line prompt**
   - File: Database `system_prompts` table
   - Update `subject_line` prompt to match n8n version

### Code Changes Required

#### claude.py - `_build_slot_user_prompt()`

```python
def _build_slot_user_prompt(self, candidates: List[dict], source_lookup: Dict[str, int] = None) -> str:
    """Build user prompt with candidate stories including credibility scores"""
    prompt = f"CANDIDATE STORIES ({len(candidates)} stories):\n\n"

    for i, candidate in enumerate(candidates, 1):
        fields = candidate.get('fields', candidate)
        source = fields.get('source_id', 'Unknown')
        cred_score = source_lookup.get(source.lower(), 2) if source_lookup else 2

        prompt += f"""Story {i}:
- storyID: {fields.get('storyID', '')}
- pivotId: {fields.get('pivotId', '')}
- headline: {fields.get('headline', '')}
- source_name: {source}
- credibility_score: {cred_score}
- date_og_published: {fields.get('date_og_published', '')}
- primary_company: {fields.get('primary_company', 'null')}
- url: {fields.get('core_url', '')}

"""

    prompt += "Select the BEST story for this slot. Return JSON only."
    return prompt
```

#### slot_selection.py - Source tracking fix

```python
# Change from:
cumulative_state = {
    "selectedToday": [],
    "selectedCompanies": [],
    "selectedSources": []  # List
}

# Change to:
cumulative_state = {
    "selectedToday": [],
    "selectedCompanies": [],
    "selectedSources": {}  # Dict with counts
}

# When updating:
if source_id:
    cumulative_state["selectedSources"][source_id] = \
        cumulative_state["selectedSources"].get(source_id, 0) + 1
```

---

## Appendix: Full N8N Workflow Node Reference

### Node Flow

```
Schedule Trigger 9:15pm ET
    |
    v
Pull Recent Issues (14-day lookback)
    |
    +---> Pull Slot 1 Candidates
    |         |
    |         v
    |     Prepare Slot 1 Context
    |         |
    |         v
    |     Merge Slot 1 Inputs
    |         |
    |         v
    |     Slot 1 - Agent (Claude)
    |         |
    |         v
    |     Remove Slot 1 Stories
    |         |
    +---> Pull Slot 2 Candidates
              |
              ... (repeat for slots 2-5)
              |
              v
          Assembly Code
              |
              v
          Subject Line Generator (Claude)
              |
              v
          Prepare Write Data
              |
              v
          Write AI Editor - Selected Slots
```

### Key N8N Query Parameters

| Node | Table | Filter |
|------|-------|--------|
| Pull Recent Issues | Selected Slots | `IS_AFTER({issue_date}, DATEADD(TODAY(), -14, 'days'))` |
| Pull Slot 1 Candidates | Pre-Filter Log | `{slot}="1" AND IS_AFTER({date_og_published}, DATEADD(NOW(), IF(weekend, -72, -24), 'hours'))` |
| Pull Slot 2 Candidates | Pre-Filter Log | `{slot}="2" AND IS_AFTER({date_og_published}, DATEADD(NOW(), IF(weekend, -72, -48), 'hours'))` |
| Pull Slot 3 Candidates | Pre-Filter Log | `{slot}="3" AND IS_AFTER({date_og_published}, DATEADD(NOW(), -7, 'days'))` |
| Pull Slot 4 Candidates | Pre-Filter Log | `{slot}="4" AND IS_AFTER({date_og_published}, DATEADD(NOW(), IF(weekend, -72, -48), 'hours'))` |
| Pull Slot 5 Candidates | Pre-Filter Log | `{slot}="5" AND IS_AFTER({date_og_published}, DATEADD(NOW(), -7, 'days'))` |

---

## Audit Sign-Off

- Auditor: Claude Code
- Date: 2025-12-31
- Workflow Version: SZmPztKNEmisG3Zf (current production)
- Python Files Audited:
  - `/workers/jobs/slot_selection.py`
  - `/workers/utils/claude.py`
  - `/workers/utils/airtable.py`

**Next Steps:** Implement fixes in priority order, test each slot individually before full pipeline test.
