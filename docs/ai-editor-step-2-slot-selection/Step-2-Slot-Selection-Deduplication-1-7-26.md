# Step 2 Slot Selection - pivotId Not Being Saved Investigation

**Date:** January 7, 2026
**Issue:** pivotId is NOT being saved to Selected Slots table even though it EXISTS in Pre-Filter Log candidate data.

---

## Executive Summary

**ROOT CAUSE FOUND:** Claude returns headlines WITHOUT the source suffix (e.g., "Meta lays off 600..." instead of "Meta lays off 600... - Mashable"), causing exact headline matching to fail. When both storyID match AND headline match fail, pivotId lookup fails.

**FIX IMPLEMENTED:** Added multi-tier headline matching (exact, startswith, reverse-startswith, substring) to handle Claude's headline modifications.

---

## Tables Investigated

### 1. Pre-Filter Log (tbl72YMsm9iRHj3sp)

**Actual Airtable Field Names:**
```json
{
  "headline": "Meta lays off 600 in AI division despite billion-dollar AI push - Mashable",
  "date_og_published": "2026-01-07T06:26:20.000Z",
  "date_prefiltered": "2026-01-07T16:54:38.000Z",
  "slot": "2",
  "pivotId": "p_mw7feg",           // camelCase - CORRECT
  "storyID": "recSCfGfRRaBycgpc",  // camelCase - CORRECT
  "core_url": "https://mashable.com/article/meta-lay-off-600-ai",
  "source_id": "Mashable"
}
```

**Code Field Name Usage (airtable.py:496):**
```python
fields=['storyID', 'pivotId', 'headline', 'core_url', 'source_id', 'date_og_published', 'slot']
```
**VERDICT: FIELD NAMES MATCH**

---

### 2. Selected Slots (tblzt2z7r512Kto3O)

**Actual Airtable Field Names:**
```json
{
  "issue_date": "2026-01-08",
  "issue_id": "Pivot 5 - Jan 08",
  "status": "pending",
  "slot_1_storyId": "rec37",        // NOTE: Truncated/invalid!
  "slot_1_headline": "Meta lays off 600 in AI division despite billion-dollar AI push",
  "slot_1_pivotId": null,           // MISSING!
  "slot_2_storyId": "rec19CYYLGp6hQtNs",
  "slot_2_pivotId": null,           // ALSO MISSING!
  "slot_3_storyId": "rec0NRh8kapnRmtIH",
  "slot_3_pivotId": "p_apfdrk",     // Present
  "slot_4_storyId": "reccrgt00PzjlgXPF",
  "slot_4_pivotId": "p_11x5l9",     // Present
  "slot_5_storyId": "recWY5ki51LAG6gTq",
  "slot_5_pivotId": "p_1mnb9yv"     // Present
}
```

**Code Field Name Usage (slot_selection.py:303-305):**
```python
issue_data[f"slot_{slot}_headline"] = selected_headline
issue_data[f"slot_{slot}_storyId"] = selected_story_id
issue_data[f"slot_{slot}_pivotId"] = selected_pivot_id
```
**VERDICT: FIELD NAMES MATCH** (camelCase: storyId, pivotId)

---

### 3. Newsletter Issue Stories / Decoration (tbla16LJCf5Z6cRn3)

**Actual Airtable Field Names:**
```json
{
  "issue_id": "Pivot 5 - Dec 31",
  "slot_order": 2,
  "story_id": "recKR43IErhpDsrar",  // snake_case! Different from other tables
  "headline": "AI Workloads Force Data Centers...",
  "label": "INFRASTRUCTURE",
  "b1": "...",
  "b2": "...",
  "b3": "...",
  "ai_dek": "...",
  "image_url": "...",
  "pivotnews_url": "..."
}
```

**Code Field Name Usage (airtable.py:387-391):**
```python
fields=[
    'story_id', 'headline',  # Note: Newsletter Issue Stories uses snake_case
    'b1', 'b2', 'b3',
    'ai_dek', 'label',
    'issue_id'
]
```
**VERDICT: FIELD NAMES MATCH** (snake_case: story_id)

---

## Root Cause Analysis

### The Problem Flow

1. **Claude returns selection:**
   ```json
   {
     "selected_id": "rec37",  // TRUNCATED/INVALID storyID!
     "selected_headline": "Meta lays off 600 in AI division despite billion-dollar AI push"
     // Note: NO source suffix " - Mashable"
   }
   ```

2. **Code tries storyID match (FAILS):**
   ```python
   for c in available_candidates:
       if c.get('fields', {}).get('storyID') == "rec37":  # No match!
           # storyID in Pre-Filter Log is "recSCfGfRRaBycgpc"
   ```

3. **Code tries headline match (FAILS):**
   ```python
   selected_headline_lower = "meta lays off 600 in ai division despite billion-dollar ai push"
   candidate_headline = "meta lays off 600 in ai division despite billion-dollar ai push - mashable"

   if candidate_headline == selected_headline_lower:  # FALSE! Different strings
   ```

4. **Result: No match found, pivotId = ""**

### Evidence from Jan 08 Issue

| Slot | storyId | pivotId | Analysis |
|------|---------|---------|----------|
| 1 | `rec37` (invalid!) | MISSING | Claude truncated storyID, headline missing source suffix |
| 2 | `rec19CYYLGp6hQtNs` | MISSING | Likely same headline mismatch issue |
| 3 | `rec0NRh8kapnRmtIH` | `p_apfdrk` | Match succeeded (storyID or headline matched) |
| 4 | `reccrgt00PzjlgXPF` | `p_11x5l9` | Match succeeded |
| 5 | `recWY5ki51LAG6gTq` | `p_1mnb9yv` | Match succeeded |

---

## Fix Implemented

**File:** `/workers/jobs/slot_selection.py`
**Lines:** 271-325

### Before (exact match only):
```python
if candidate_headline == selected_headline_lower:
    matched_candidate = c
```

### After (multi-tier matching):
```python
# 1. Exact match
if candidate_headline == selected_headline_lower:
    matched_candidate = c

# 2. Startswith match (Claude strips " - Source" suffix)
if not matched_candidate:
    if candidate_headline.startswith(selected_headline_lower):
        matched_candidate = c

# 3. Reverse startswith (selected might have extra text)
if not matched_candidate:
    if selected_headline_lower.startswith(candidate_headline):
        matched_candidate = c

# 4. Substring match (50 char minimum for precision)
if not matched_candidate and len(selected_headline_lower) >= 50:
    search_text = selected_headline_lower[:50]
    if search_text in candidate_headline:
        matched_candidate = c
```

---

## Field Name Reference Summary

| Table | Story ID Field | Pivot ID Field | Notes |
|-------|---------------|----------------|-------|
| Pre-Filter Log | `storyID` (camelCase) | `pivotId` (camelCase) | Source of candidates |
| Selected Slots | `slot_X_storyId` | `slot_X_pivotId` | Destination for selections |
| Newsletter Issue Stories | `story_id` (snake_case) | N/A | Used for decoration |

**KEY INSIGHT:** Field names ARE correct in the code. The bug was in the headline matching logic, not field naming.

---

## Testing Recommendations

1. **Verify fix works** - Run Step 2 and check logs for "MATCH by headline startswith" messages
2. **Check existing records** - Update any records where pivotId is missing but should be present
3. **Monitor Claude responses** - Log the exact `selected_id` Claude returns to track truncation issues

---

## Files Modified

- `/workers/jobs/slot_selection.py` - Added multi-tier headline matching fallback

---

## Related Documentation

- `/docs/Step-2-SlotSelection-Cross-Reference-12-30-25.md`
- `/.claude/skills/step-2-slot-selection.md`
- `/.claude/skills/airtable-api.md`
