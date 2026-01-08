# Step 2 Slot Selection - Deduplication Investigation

**Last Updated:** January 8, 2026
**Investigation Status:** COMPLETE - Root cause confirmed, fix NEVER IMPLEMENTED

---

## EXECUTIVE SUMMARY

**The within-issue headline deduplication logic WAS NEVER CODED.**

The user's assumption that this was "coded weeks ago" is incorrect. After a thorough investigation of the git history and codebase, I can confirm:

1. **`selectedHeadlinesToday` was NEVER added to `cumulative_state`** - It only exists as a proposed fix in this documentation file
2. **Claude NEVER receives today's selected headlines** - Only storyIDs are tracked in `cumulative_state`
3. **The deduplication that WAS implemented** only covers the 14-day historical lookback, NOT within-issue duplicates
4. **Git history confirms** - No commit has ever added headline tracking for within-issue deduplication

---

## CRITICAL FINDING: The Code Gap

### What cumulative_state ACTUALLY Contains (Current Code)

**File:** `/workers/jobs/slot_selection.py` (lines 147-153)

```python
cumulative_state = {
    "selectedToday": [],       # storyIDs selected today
    "selectedCompanies": [],   # companies featured today
    "selectedSources": {}      # sources used today {source: count}
}
```

**MISSING:** `selectedHeadlinesToday` was NEVER added!

### What Gets Updated After Each Slot (Current Code)

**File:** `/workers/jobs/slot_selection.py` (lines 339-346)

```python
# Update cumulative state
if selected_story_id:
    cumulative_state["selectedToday"].append(selected_story_id)
if company:
    cumulative_state["selectedCompanies"].append(company)
if source_id:
    cumulative_state["selectedSources"][source_id] = \
        cumulative_state["selectedSources"].get(source_id, 0) + 1
```

**MISSING:** No code adds `selected_headline` to cumulative_state!

### What Claude ACTUALLY Receives for Slot 3 Selection

**File:** `/workers/utils/claude.py` (lines 117-208)

When Claude selects Slot 3, the prompt contains:

1. **Recent headlines (14-day lookback)** - From database, does NOT include today's Slot 1 or Slot 2 headlines
2. **Story summaries (14-day)** - Decorated stories from database, does NOT include today's selections
3. **Slot history (14-day)** - Past selections for this specific slot, does NOT include today
4. **`selected_stories`** - Only storyIDs: `"ABC, DEF"` (NOT the actual headline text!)
5. **`selected_companies`** - Company names from today's selections
6. **`selected_sources`** - Source names with counts

**Claude NEVER sees:**
- The headline text "JPMorgan Replaces Proxy Advisers With AI for Voting US Shares" (Slot 2)
- Any way to semantically compare candidates with today's previous selections

---

## GIT HISTORY INVESTIGATION

### Commits Related to Slot Selection Deduplication

| Date | Commit | Description | Added `selectedHeadlinesToday`? |
|------|--------|-------------|--------------------------------|
| Dec 23 | 1fb6b56 | Initial commit | NO - only `selectedToday` (storyIDs) |
| Dec 30 | 8f34ddb | UTC to EST fix | NO |
| Dec 30 | fbd00d6 | CRITICAL: Add recent headlines to Claude | NO - only 14-day lookback |
| Dec 31 | 2459355 | Fix 4 critical gaps from n8n audit | NO |
| Dec 31 | 2fa0ced | Fix Step 2 to match n8n workflow exactly | NO |
| Dec 31 | 6f98e5e | Fix Slot 1 two-day company rotation | NO |
| Dec 31 | 9892155 | Remove Source Scores table references | NO |
| Jan 7 | 06de29f | Add semantic deduplication | NO - only 14-day summaries |
| Jan 7 | 5886584 | Fix semantic deduplication | NO - added slot-specific history (past issues only) |
| Jan 7 | 5a0f81e | Fix pivotId | NO |

### Search Results

```bash
# Searched for any commit with "selectedHeadlines"
git log -p --all -S "selectedHeadlinesToday" -- .
# Result: NO COMMITS FOUND

# Searched for "headlines_today" variable
git log -p --all -S "headlines_today" -- .
# Result: NO COMMITS FOUND

# Searched current codebase
grep -rn "selectedHeadlines" workers/
# Result: NO MATCHES IN CODE
```

**CONCLUSION: The within-issue headline tracking was NEVER implemented. It only exists as a proposed fix in this documentation file.**

---

## DETAILED CODE FLOW ANALYSIS

### Slot 2 Selection (Example)

```python
# Step 1: Candidates loaded (includes JPMorgan story from Bloomberg)
candidates = [
    {"storyID": "ABC", "headline": "JPMorgan Replaces Proxy Advisers With AI...", "source": "Bloomberg"},
    # ... other candidates
]

# Step 2: Claude selects
selection = claude.select_slot(slot=2, candidates=candidates, ...)
# Returns: {"selected_id": "ABC", "selected_headline": "JPMorgan Replaces Proxy Advisers..."}

# Step 3: Update cumulative_state
cumulative_state["selectedToday"].append("ABC")  # Only storyID!
cumulative_state["selectedCompanies"].append("JPMorgan")
cumulative_state["selectedSources"]["Bloomberg"] = 1

# NOTE: selected_headline is NOT added anywhere!
```

### Slot 3 Selection (Example - THE BUG)

```python
# Step 1: Candidates loaded (includes JPMorgan story from Morning Brew)
candidates = [
    {"storyID": "XYZ", "headline": "JPMorgan Chase is replacing its proxy advisors with AI...", "source": "Morning Brew"},
    # ... other candidates
]

# Step 2: Code filters out already selected storyIDs
excluded_ids = {"ABC"}  # From cumulative_state["selectedToday"]
available_candidates = [c for c in candidates if c["storyID"] not in excluded_ids]
# "XYZ" PASSES - different storyID from "ABC"

# Step 3: Code filters out 14-day historical duplicates
recent_headlines = ["Old headline 1", "Old headline 2", ...]  # From database
# "JPMorgan Chase is replacing..." NOT in recent_headlines - it's brand new news
# PASSES

# Step 4: Claude selects from available_candidates
# Claude's prompt contains:
#   - recent_headlines: [14-day historical headlines] - NO JPMorgan proxy story
#   - selected_stories: "ABC" (just the storyID, NOT "JPMorgan Replaces Proxy Advisers...")
#   - story_summaries: [14-day decorated stories] - NO JPMorgan proxy story
#
# Claude has NO WAY to know Slot 2 already has a JPMorgan proxy story!
# Claude selects "XYZ" - the Morning Brew version

# Step 5: Issue now has DUPLICATE NEWS EVENT in Slot 2 and Slot 3
```

---

## WHAT CLAUDE RECEIVES (EXACT PROMPT CONTENT)

For Slot 3 selection, Claude's prompt includes these sections:

### 1. Recent Headlines (14-day) - DOES NOT INCLUDE TODAY

```
### Rule 1: Recent Headlines (Last 14 Days) - CRITICAL SEMANTIC DEDUPLICATION
Do NOT select any story about the same topic/event as these recent headlines:

1. [14-day old headline 1]
2. [14-day old headline 2]
... (up to 30 headlines from past issues in database)
```

**PROBLEM:** Today's Slot 2 headline is NOT in this list because it's not in the database yet.

### 2. Selected Today - ONLY STORYIDS, NOT HEADLINES

```
### Rule 2: Already Selected Today
Do NOT select these storyIDs: ABC, DEF
```

**PROBLEM:** Claude sees "ABC" but has no way to know ABC is "JPMorgan Replaces Proxy Advisers With AI for Voting US Shares"

### 3. Story Summaries (14-day) - DOES NOT INCLUDE TODAY

```
## RECENT STORY SUMMARIES (for semantic deduplication)
**CRITICAL:** Do NOT select stories about the SAME NEWS EVENT as these:

### Recent Story 1
- Headline: [14-day old headline]
- Key Points: [bullets from decorated story]
...
```

**PROBLEM:** Today's Slot 2 selection is not decorated yet, so it's not in this list.

### 4. Slot-Specific History - DOES NOT INCLUDE TODAY

```
## SLOT 3 SPECIFIC HISTORY (CRITICAL)
Stories that were specifically selected for SLOT 3 in recent issues:

1. [2026-01-07] Old Slot 3 headline
2. [2026-01-06] Another old Slot 3 headline
...
```

**PROBLEM:** This only shows PAST issues from the database, not today's in-progress selections.

---

## THE FIX THAT SHOULD HAVE BEEN IMPLEMENTED

### In `slot_selection.py`

```python
# Line 147-154: Initialize cumulative_state
cumulative_state = {
    "selectedToday": [],           # storyIDs selected today
    "selectedHeadlinesToday": [],  # NEW: headlines selected today
    "selectedCompanies": [],       # companies featured today
    "selectedSources": {}          # sources used today {source: count}
}

# Lines 339-347: After selection, update cumulative state
if selected_story_id:
    cumulative_state["selectedToday"].append(selected_story_id)
if selected_headline:  # NEW: Track headline
    cumulative_state["selectedHeadlinesToday"].append(selected_headline)
if company:
    cumulative_state["selectedCompanies"].append(company)
if source_id:
    cumulative_state["selectedSources"][source_id] = \
        cumulative_state["selectedSources"].get(source_id, 0) + 1
```

### In `claude.py` `_build_slot_system_prompt()`

```python
# After existing prompt building, add:
headlines_today = cumulative_state.get('selectedHeadlinesToday', [])
if headlines_today:
    prompt += "\n\n## HEADLINES ALREADY SELECTED FOR TODAY'S ISSUE (CRITICAL)"
    prompt += "\n**Do NOT select any story about the SAME NEWS EVENT as these:**\n"
    for i, h in enumerate(headlines_today, 1):
        prompt += f"\n{i}. {h}"
    prompt += "\n\n**Even if worded differently or from a different source, if it covers the same underlying news, REJECT IT.**"
```

---

## EVIDENCE: THE BUG IN ACTION

### Jan 09 Newsletter Duplicate

| Slot | Headline | Source | News Event |
|------|----------|--------|------------|
| 2 | "JPMorgan Replaces Proxy Advisers With AI for Voting US Shares" | Bloomberg | JPMorgan AI proxy voting |
| 3 | "JPMorgan Chase is replacing its proxy advisors with AI" | Morning Brew | JPMorgan AI proxy voting |

**Same news event, different sources, both selected because Claude had no way to compare.**

### Why This Happened

1. Slot 2 selected the Bloomberg version of the JPMorgan story
2. cumulative_state only tracked `selectedToday: ["ABC"]` (storyID)
3. Slot 3 candidate list included the Morning Brew version (storyID: "XYZ")
4. Code filter passed: "XYZ" != "ABC"
5. Claude's prompt had no mention of "JPMorgan Replaces Proxy Advisers With AI..."
6. Claude selected the Morning Brew version, thinking it was unique
7. Both stories ended up in the same issue

---

## RECOMMENDED FIX IMPLEMENTATION

### Priority: HIGH - Should be implemented immediately

### Files to Modify:

1. **`/workers/jobs/slot_selection.py`**
   - Add `selectedHeadlinesToday` to `cumulative_state` initialization
   - Add headline tracking after each selection

2. **`/workers/utils/claude.py`**
   - Add "HEADLINES ALREADY SELECTED FOR TODAY'S ISSUE" section to prompt
   - Include in both database-prompt path and fallback path

### Testing:

1. Run Step 2 manually and verify logs show headline tracking
2. Check that Slot 3+ prompts include previous slot headlines
3. Test with known duplicate news events (same story, different sources)

---

## RELATED DOCUMENTATION

- `/.claude/skills/step-2-slot-selection.md`
- `/.claude/skills/airtable-api.md`
- `/docs/Step-2-SlotSelection-Cross-Reference-12-30-25.md`

---

## APPENDIX: Original pivotId Issue (Jan 7, 2026) - RESOLVED

The original investigation was about pivotId not being saved. This was FIXED in commit `5a0f81e` by having Claude return `selected_pivotId` directly instead of relying on storyID lookup.

This documentation was then updated to include the within-issue headline deduplication gap that was discovered during that investigation.
