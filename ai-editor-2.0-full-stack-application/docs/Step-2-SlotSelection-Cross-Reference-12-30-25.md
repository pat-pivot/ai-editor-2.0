# Step 2: Slot Selection - Cross-Reference Analysis

**Date:** December 30, 2025
**n8n Workflow ID:** `SZmPztKNEmisG3Zf`
**Python Worker:** `/workers/jobs/slot_selection.py`
**Last Updated:** December 30, 2025 - Bugs #1-4 FIXED

## Overview

This document provides a detailed cross-reference between the n8n Step 2 workflow and the Python worker implementation, identifying matches, differences, and required action items.

## FIXES APPLIED (December 30, 2025)

| Bug | Issue | Status | Files Modified |
|-----|-------|--------|----------------|
| #1 | Issue date uses TODAY, not next issue with weekend skip | **FIXED** | `slot_selection.py` - Added `get_next_issue_date()` |
| #2 | 14-day lookback not implemented (only yesterday) | **FIXED** | `slot_selection.py`, `claude.py` - Now uses `get_recent_sent_issues(14)` |
| #3 | Filter uses `date_prefiltered` instead of `date_og_published` | **FIXED** | `airtable.py` line 284 |
| #4 | Weekend freshness extension missing (72h) | **FIXED** | `slot_selection.py` - Added `get_slot_freshness()` |

---

## 1. Model Configuration

### n8n Workflow
- **Model:** `claude-sonnet-4-5-20250929` (all 5 slot agents + subject line)
- **Temperature:** Not explicitly set (uses default)

### Python Implementation
- **File:** `/workers/utils/claude.py`, line 30
- **Model:** `claude-sonnet-4-5-20250929` (MATCHES)
- **Temperature:** 0.5 for slot selection (line 61), 0.7 for subject line (line 244)

### Status: PARTIAL MATCH
- Model is correct
- Temperature is explicitly set in Python but not in n8n (n8n uses Claude defaults)

---

## 2. Candidate Pool Freshness Windows

### n8n Workflow (Airtable Filter Formulas)

| Slot | n8n Filter | Freshness |
|------|-----------|-----------|
| 1 | `IS_AFTER({date_og_published}, DATEADD(NOW(), IF(OR(WEEKDAY(NOW())=0, WEEKDAY(NOW())=1), -72, -24), 'hours'))` | 24h (72h on weekends) |
| 2 | `IS_AFTER({date_og_published}, DATEADD(NOW(), IF(OR(WEEKDAY(NOW())=0, WEEKDAY(NOW())=1), -72, -48), 'hours'))` | 48h (72h on weekends) |
| 3 | `IS_AFTER({date_og_published}, DATEADD(NOW(), -7, 'days'))` | 7 days |
| 4 | `IS_AFTER({date_og_published}, DATEADD(NOW(), IF(OR(WEEKDAY(NOW())=0, WEEKDAY(NOW())=1), -72, -48), 'hours'))` | 48h (72h on weekends) |
| 5 | `IS_AFTER({date_og_published}, DATEADD(NOW(), -7, 'days'))` | 7 days |

### Python Implementation
- **File:** `/workers/jobs/slot_selection.py`, lines 19-25

```python
SLOT_FRESHNESS = {
    1: 1,   # 0-24 hours
    2: 2,   # 24-48 hours
    3: 7,   # 0-7 days
    4: 2,   # 0-48 hours
    5: 7,   # 0-7 days
}
```

### Status: FIXED (December 30, 2025)
1. **Weekend logic**: ✅ FIXED - Added `get_slot_freshness()` function that extends to 72h on Sun/Mon runs
2. **Filter formula in Python** (`/workers/utils/airtable.py`, line 284):
   ✅ FIXED - Now uses `date_og_published` instead of `date_prefiltered`
   ```python
   filter_formula = f"AND({{slot}}={slot}, IS_AFTER({{date_og_published}}, DATEADD(TODAY(), -{freshness_days}, 'days')))"
   ```

---

## 3. Airtable Table & Fields

### n8n Workflow
- **Pull candidates from:** Pre-Filter Log (`tbl72YMsm9iRHj3sp`)
- **Write to:** Selected Slots (`tblzt2z7r512Kto3O`)

### Python Implementation
- **Pull from:** Pre-Filter Log (line 33: `tbl72YMsm9iRHj3sp`) - MATCHES
- **Write to:** Selected Slots (line 34: `tblzt2z7r512Kto3O`) - MATCHES

### Status: MATCH

---

## 4. Fields Read from Pre-Filter Log

### n8n Workflow (from `Prepare Slot X Context` nodes)
Fields used in candidate formatting:
- `storyID`
- `headline` (falls back to `ai_headline`)
- `source_id` (falls back to `source_name`, `source`)
- `date_og_published`
- `primary_company` (falls back to `company`)
- `pivotId`
- `core_url` (falls back to `url`, `decorated_url`)

### Python Implementation
- **File:** `/workers/utils/airtable.py`, line 284

```python
fields=['storyID', 'pivotId', 'headline', 'core_url', 'source_id', 'date_og_published', 'slot']
```

### Status: PARTIAL MATCH
- Missing `primary_company` field from candidates read
- This means company diversity tracking may be incomplete

---

## 5. Fields Written to Selected Slots Table

### n8n Workflow
```
issue_id, issue_date, subject_line, status, social_post_status,
slot_1_storyId, slot_1_pivotId, slot_1_headline,
slot_2_storyId, slot_2_pivotId, slot_2_headline,
slot_3_storyId, slot_3_pivotId, slot_3_headline,
slot_4_storyId, slot_4_pivotId, slot_4_headline,
slot_5_storyId, slot_5_pivotId, slot_5_headline
```

### Python Implementation
- **File:** `/workers/jobs/slot_selection.py`, lines 149-157

```python
issue_data[f"slot_{slot}_headline"] = selected_headline
issue_data[f"slot_{slot}_storyId"] = selected_story_id
issue_data[f"slot_{slot}_pivotId"] = selected_pivot_id
issue_data[f"slot_{slot}_source"] = source_id
issue_data[f"slot_{slot}_company"] = company
```

Also includes: `issue_date`, `status`, `subject_line` (lines 75-80, 172)

### Status: PARTIAL MATCH - DIFFERENCES
1. Python writes `slot_X_source` and `slot_X_company` - n8n does NOT write these
2. n8n writes `social_post_status` - Python does NOT
3. n8n uses `issue_id` formatted as "Pivot 5 - Dec 30" - Python uses `issue_date_label` but field name is `issue_date` (line 75-76)

---

## 6. Diversity Rules Implementation

### n8n Workflow Diversity Rules (from prompts)

1. **Yesterday's Headlines (Rule 1)**: Last 14 days of headlines from `recentHeadlines`
2. **Company Diversity (Rule 2)**: Don't repeat companies selected today (`previouslySelectedCompanies`)
3. **Source Diversity (Rule 3)**: Max 2 stories per source per day (`previouslySelectedSources`)
4. **Already Selected Today (Rule 4)**: Don't reselect same storyID (`previouslySelectedIds`)
5. **Slot 1 Two-Day Rotation**: Don't use yesterday's Slot 1 company

### Python Implementation

| Rule | Python Location | Status |
|------|-----------------|--------|
| Yesterday's Headlines | `claude.py` lines 123-124 | Uses `yesterday_headlines` not 14-day window |
| Company Diversity | `slot_selection.py` lines 68-70, 143-144 | MATCHES |
| Source Diversity | `slot_selection.py` lines 68-70, 145-146 | Tracked but not enforced with max 2 |
| Already Selected Today | `slot_selection.py` lines 101-104 | MATCHES |
| Slot 1 Rotation | `claude.py` lines 102-103, 136-140 | MATCHES |

### Status: MOSTLY FIXED (December 30, 2025)
1. ✅ **14-day lookback FIXED**: Now uses `get_recent_sent_issues(14)` instead of `get_yesterday_issue()`
2. **Source max 2 not enforced**: Python tracks sources but doesn't enforce max 2 in filtering (LOW priority)
3. ✅ `get_recent_sent_issues(lookback_days=14)` now called in slot_selection.py

---

## 7. Slot Agent Prompts

### n8n Workflow Prompts (Summary)

**Slot 1 (Breaking News):**
- Focus: OpenAI, Google, Meta, Nvidia OR Jobs/Economy impact
- Tier 1 companies priority
- Credibility score table (2-5 scale)

**Slot 2 (Recent Important):**
- Focus: Broader tier 1 (OpenAI, GOOG, META, NVDA, MSFT, Anthropic, xAI, AMZN)
- Economic themes, research
- 14-day semantic deduplication

**Slot 3 (Evergreen/Feature):**
- Focus: Industry verticals (healthcare, govt, education, legal, etc.)
- Non-tech industries impacted by AI

**Slot 4 (Emerging):**
- Focus: Less-known companies, NOT tier 1
- Product launches, fundraises, partnerships

**Slot 5 (Consumer AI):**
- Focus: Human interest, "nice to know"
- AI in everyday life, societal impact

**Common to all n8n prompts:**
- Stories to avoid: Leadership shuffles, gossip, geeky content, CSAM
- Editorial lens: "Is this useful to a working professional?"
- JSON output format with: selected_id, selected_headline, selected_source, selected_company, reasoning

### Python Implementation
- **File:** `/workers/utils/claude.py`, lines 72-152

The Python implementation:
1. Attempts to load prompts from database using `get_prompt(f"slot_{slot}_agent")`
2. Falls back to hardcoded prompts if database prompts not found

**Fallback prompt slot focus (lines 111-117):**
```python
slot_focus = {
    1: "Jobs, economy, stock market, broad societal impact. Must be FRESH (0-24 hours).",
    2: "Tier 1 AI companies (OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon), economic themes, research breakthroughs.",
    3: "Industry verticals: Healthcare, Government, Education, Legal, Accounting, Retail, Security, Transportation, Manufacturing, Real Estate, Agriculture, Energy.",
    4: "Emerging companies: product launches, fundraising, acquisitions, new AI tools. Must be FRESH (0-48 hours).",
    5: "Consumer AI, human interest, ethics, entertainment, societal impact, fun/quirky uses."
}
```

### Status: SIGNIFICANT DIFFERENCES
1. **Slot 1 n8n focus is different**: n8n prioritizes big 4 companies (OpenAI/Google/Meta/Nvidia), Python focuses on jobs/economy
2. **Stories to avoid**: n8n has detailed list (leadership shuffles, gossip, CSAM), Python fallback doesn't include this
3. **Source credibility guide**: n8n includes detailed tier tables, Python fallback doesn't
4. **14-day deduplication language**: n8n has "CRITICAL: Semantic Deduplication" section, Python doesn't
5. **JSON output format differs**: n8n uses `selected_id`, Python expects `selected_storyId`

---

## 8. Subject Line Generation

### n8n Workflow
- **Prompt content:**
```
Generate an email subject line for today's AI newsletter.

The 5 stories are:
{{ $json.allHeadlines }}

Format:
- Combine 2-3 stories into short, punchy phrases
- Separate with commas
- Each phrase should be a condensed version of the headline (5-8 words max per phrase)
- Total length: 60-90 characters
- News-style tone, not clickbait
- No "+" symbols

Examples of good subject lines:
- "ChatGPT's Mobile App Hits $3 Billion, Anthropic Expands AI Commerce Experiment"
...
```

### Python Implementation
- **File:** `/workers/utils/claude.py`, lines 197-253
- Uses database prompt with fallback

**Fallback differences (lines 223-239):**
- Max 60 characters (n8n says 60-90)
- "Create urgency and curiosity" (n8n says "news-style, not clickbait")
- No specific examples provided
- Different format guidance

### Status: DIFFERENT
- Character limits differ
- Tone guidance differs
- Examples not included in Python fallback
- n8n specifically says "No + symbols" - Python doesn't mention this

---

## 9. Critical Bug: `max_records` Limit

### Issue Identified
- **File:** `/workers/utils/airtable.py`
- The `get_prefilter_candidates` method (lines 272-287) does NOT have a `max_records` limit
- However, `get_fresh_stories` (lines 50-89) defaults to no limit but can accept `max_records`

### n8n Behavior
- n8n Airtable nodes pull ALL matching records by default
- No explicit limit in the workflow

### Python Behavior
- `get_prefilter_candidates()` has no limit (CORRECT)
- This is NOT a bug in the current implementation

### Status: FALSE ALARM - No bug in get_prefilter_candidates

---

## 10. Issue Date Calculation

### n8n Workflow (from `Assembly Code` and `Prepare Write Data`)
```javascript
const dayOfWeek = today.getDay();
let daysToAdd;
if (dayOfWeek === 5) daysToAdd = 3;      // Friday -> Monday
else if (dayOfWeek === 6) daysToAdd = 2;  // Saturday -> Monday
else daysToAdd = 1;                        // Sun-Thu -> next day

const issueId = `Pivot 5 - ${month} ${day}`;
```

### Python Implementation
- **File:** `/workers/jobs/slot_selection.py`, lines 74-76

```python
today_date = datetime.utcnow().strftime('%Y-%m-%d')
issue_date_label = f"Pivot 5 - {datetime.utcnow().strftime('%b %d')}"
```

### Status: FIXED (December 30, 2025)
✅ Python now uses `get_next_issue_date()` which implements proper weekend skipping:
- Friday → Monday (skip Sat/Sun)
- Saturday → Monday (skip Sun)
- Otherwise → next day

---

## Implementation Checklist

### MATCHES (No Action Needed)
- [x] Claude model: `claude-sonnet-4-5-20250929`
- [x] Pre-Filter Log table ID: `tbl72YMsm9iRHj3sp`
- [x] Selected Slots table ID: `tblzt2z7r512Kto3O`
- [x] Company diversity tracking across slots
- [x] Story ID deduplication within same day
- [x] Slot 1 two-day company rotation rule
- [x] Sequential slot processing order (1-5)

### DIFFERS - Requires Update
| Item | Python Location | Issue | Priority | Status |
|------|-----------------|-------|----------|--------|
| Weekend freshness extension | `slot_selection.py` | Missing 72h weekend logic | HIGH | ✅ FIXED |
| 14-day headline lookback | `slot_selection.py` | Only uses yesterday, not 14 days | HIGH | ✅ FIXED |
| Issue date calculation | `slot_selection.py` | Uses today, not next issue date | HIGH | ✅ FIXED |
| Date field filter | `airtable.py` | Wrong date field | HIGH | ✅ FIXED |
| Source max 2 enforcement | Slot filtering logic | Tracked but not enforced | MEDIUM | PENDING |
| `primary_company` field read | `airtable.py` line 284 | Not included in candidate fields | MEDIUM | PENDING |
| `social_post_status` write | `airtable.py` write | Not written to Selected Slots | LOW | PENDING |
| Subject line format | `claude.py` lines 223-239 | Different character limits, examples | LOW | PENDING |

### PROMPTS - Require Database Update
| Prompt Key | Issue |
|------------|-------|
| `slot_1_agent` | Focus mismatch (n8n = big 4 companies, fallback = jobs/economy) |
| `slot_2_agent` | Missing semantic deduplication language |
| `slot_3_agent` | Missing stories-to-avoid section |
| `slot_4_agent` | Missing stories-to-avoid section |
| `slot_5_agent` | Missing stories-to-avoid section |
| `subject_line` | Different format, missing examples |

### Bugs Found → ALL FIXED
1. ✅ **Issue date logic**: FIXED - Now uses `get_next_issue_date()` with weekend skipping
2. ✅ **14-day lookback**: FIXED - Now uses `get_recent_sent_issues(14)`
3. ✅ **Filter date field**: FIXED - Now filters on `date_og_published`
4. ✅ **Weekend freshness**: FIXED - Now extends to 72h for slots 1, 2, 4 on Sun/Mon runs

---

## Action Items

### Immediate (Required for parity) - ALL DONE ✅

1. ✅ **Fix issue date calculation** - Added `get_next_issue_date()` with weekend skipping
2. ✅ **Implement 14-day lookback** - Now uses `get_recent_sent_issues(14)` with `_extract_recent_issues_data()`
3. ✅ **Fix candidate filter date field** - Changed to `date_og_published` in `get_prefilter_candidates()`
4. ✅ **Add weekend freshness extension** - Added `get_slot_freshness()` function

### Medium Priority

5. **Add `primary_company` to candidate fields** - Update `get_prefilter_candidates()` to include this field
6. **Enforce source max 2 rule** - Add filtering logic to exclude stories from sources already used twice
7. **Add `social_post_status` field** - Write this to Selected Slots table

### Low Priority (Prompt Updates)

8. **Update database prompts** - Match n8n prompt content for all 5 slot agents
9. **Update subject line prompt** - Match n8n format with examples
10. **Add stories-to-avoid section** - Ensure all prompts have leadership shuffle, gossip, CSAM exclusions

---

## File References

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `/workers/jobs/slot_selection.py` | Main Step 2 job | 19-25 (freshness), 62-63 (yesterday), 74-76 (date), 101-104 (filtering) |
| `/workers/utils/claude.py` | Claude API client | 30 (model), 61 (temp), 72-152 (prompts), 197-253 (subject line) |
| `/workers/utils/airtable.py` | Airtable client | 220-242 (recent issues), 272-287 (candidates), 289-296 (write) |
| `/workers/utils/prompts.py` | Prompt loader | 77-100 (get_slot_prompt) |
| `/src/app/(dashboard)/step/[id]/page.tsx` | Frontend | 32 (job name: slot_selection) |
