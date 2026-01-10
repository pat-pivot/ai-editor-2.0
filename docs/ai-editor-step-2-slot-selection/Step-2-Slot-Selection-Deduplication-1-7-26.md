# Step 2 Slot Selection - Deduplication Investigation

**Last Updated:** January 9, 2026
**Investigation Status:** BOTH BUGS FIXED - Ready for deployment

---

## EXECUTIVE SUMMARY

**TWO SEPARATE BUGS have been identified in the deduplication system:**

### Bug 1: Within-Issue Headline Deduplication (Jan 8, 2026)
**The within-issue headline deduplication logic WAS NEVER CODED.**

The user's assumption that this was "coded weeks ago" is incorrect. After a thorough investigation of the git history and codebase, I can confirm:

1. **`selectedHeadlinesToday` was NEVER added to `cumulative_state`** - It only exists as a proposed fix in this documentation file
2. **Claude NEVER receives today's selected headlines** - Only storyIDs are tracked in `cumulative_state`
3. **The deduplication that WAS implemented** only covers the 14-day historical lookback, NOT within-issue duplicates
4. **Git history confirms** - No commit has ever added headline tracking for within-issue deduplication

### Bug 2: 14-Day Semantic Deduplication Story Limit (Jan 9, 2026)
**The 14-day semantic deduplication uses only 30 stories, not all 45 from the 14-day window.**

New investigation on Jan 9, 2026 revealed:

1. **`story_summaries` is limited to 30 stories** - Line 413 in slot_selection.py: `for story in decorated_stories[:30]`
2. **14-day lookback has ~45 storyIDs** - 9 issues × 5 slots = 45 stories
3. **Older stories get pushed out** - After 4 days, a story at position 30+ is NOT sent to Claude for semantic comparison
4. **Evidence:** Utah AI prescription story (Jan 06) reappeared Jan 10 because it was pushed to position 30+ after 4 days of new stories

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

## EVIDENCE: BUG 1 IN ACTION (Within-Issue Deduplication)

### Jan 09 Newsletter Duplicate (Same Day, Different Sources)

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

## EVIDENCE: BUG 2 IN ACTION (30-Story Limit)

### Jan 10 Newsletter Duplicate (4 Days Apart, Same News Event)

| Date | Headline | storyID |
|------|----------|---------|
| Jan 06 | "Utah Becomes First State to Allow AI Systems to Renew Prescriptions Without Human Review" | (original ID) |
| Jan 10 | "Utah tests AI for routine medication refills through regulatory relief program" | (different ID) |

**Same news event (Utah AI prescription regulation), 4 days apart, reselected because the Jan 06 story was pushed out of the 30-story limit.**

### Render Logs from Jan 10, 2026 00:36:34 UTC (7:36 PM EST Jan 9)

```
[Step 2] Found 50 decorated stories for semantic context
[Step 2] Story summaries built: 30 added, 0 skipped (no headline), 0 without bullets
[Step 2] Summary 1: 'Alphabet Overtakes Apple...' bullets=3
[Step 2] Summary 2: 'Samsung Reports Record Profit...' bullets=3
[Step 2] Summary 3: 'JPMorgan Drops Proxy Advisory Firms...' bullets=3
[Step 2] Recent issues found: 9, total storyIds: 45, story_summaries: 30
[Step 2] Slot 3: Found 200 candidates
[Step 2] Slot 3: Filtered out 2 duplicates (by storyID/headline/pivotId)
[Step 2] Slot 3: 198 available after filtering
[Step 2] Slot 3 selected: Utah tests AI for routine medication refills throu...
```

### Why This Happened

1. **50 decorated stories fetched** - `get_recent_decorated_stories()` returns 50 records
2. **Only 30 used for Claude** - Line 413: `for story in decorated_stories[:30]`
3. **14-day lookback has 45 storyIDs** - 9 issues × 5 slots = 45 unique stories
4. **Jan 06 Utah story at position 30+** - After 4 days of new stories (~20 new stories), it was pushed out
5. **Exact headline match failed** - "Utah Becomes First State..." != "Utah tests AI..."
6. **Different storyIDs** - Not caught by storyID deduplication
7. **Not in story_summaries** - Claude never received the Jan 06 Utah story for semantic comparison
8. **Result:** Claude selected the Jan 10 Utah story, creating a duplicate news event

### The Code That Causes This

**File:** `/workers/jobs/slot_selection.py` (lines 406-419)

```python
def _extract_recent_issues_data(self, selected_slots: list, decorated_stories: list) -> dict:
    """Extract data from recent issues for deduplication."""
    data = {
        "storyIds": set(),
        "headlines": [],
        "pivotIds": set(),
        "story_summaries": []
    }

    # ... storyIds extraction (uses ALL selected_slots) ...

    # Build story summaries from decorated stories
    for story in decorated_stories[:30]:  # <-- THE BUG: Only first 30!
        fields = story.get('fields', {})
        summary = {
            "headline": fields.get('headline', ''),
            # ... bullets, dek, label, storyId ...
        }
        if summary["headline"]:
            data["story_summaries"].append(summary)
```

### The Fix for Bug 2

**Option A: Match 14-day storyID count**
```python
# Use all decorated stories, not just first 30
for story in decorated_stories:  # Remove [:30] limit
```

**Option B: Filter by date instead of count**
```python
# Only include stories from the 14-day window
cutoff_date = (datetime.now() - timedelta(days=14)).isoformat()
for story in decorated_stories:
    if story.get('fields', {}).get('issue_date', '') >= cutoff_date:
        # ... build summary ...
```

**Option C: Increase limit to 50**
```python
# Match the fetch limit
for story in decorated_stories[:50]:  # Increased from 30
```

---

## RECOMMENDED FIX IMPLEMENTATION

### Priority: HIGH - Both bugs should be fixed immediately

---

### Bug 1 Fix: Within-Issue Headline Deduplication - ✅ FIXED Jan 8, 2026

**Files Modified:**

1. **`/workers/jobs/slot_selection.py`**
   - Added `selectedHeadlinesToday` to `cumulative_state` initialization (line 150)
   - Added headline tracking after each selection (line 343)

2. **`/workers/utils/claude.py`**
   - Added "CRITICAL: Headlines Already Selected for TODAY'S Issue" section (lines 209-217, 288-295)
   - Included in both database-prompt path AND fallback path

**Commit:** `3449a16` - "Add within-issue headline deduplication to slot selection"

**Testing:**

1. Run Step 2 manually and verify logs show headline tracking
2. Check that Slot 3+ prompts include previous slot headlines
3. Test with known duplicate news events (same story, different sources)

---

### Bug 2 Fix: 30-Story Limit for Semantic Deduplication - ✅ FIXED Jan 9, 2026

**File Modified:** `/workers/jobs/slot_selection.py`

**Fix Applied (Option A):**

```python
# Lines 429 and 484: Removed the [:30] limit
for story in decorated_stories:  # FIX 1/9/26: Use ALL stories (removed [:30] limit)
```

Both occurrences were fixed:
- Line 429: In the `if not issues` branch
- Line 484: In the main processing branch

**Testing:**

1. Check logs show "Story summaries built: ~45-50 added" instead of 30
2. Verify Utah-style stories from 4+ days ago are in story_summaries
3. Confirm Claude rejects semantically similar stories from older issues

---

## RELATED DOCUMENTATION

- `/.claude/skills/step-2-slot-selection.md`
- `/.claude/skills/airtable-api.md`
- `/docs/Step-2-SlotSelection-Cross-Reference-12-30-25.md`

---

## APPENDIX: Original pivotId Issue (Jan 7, 2026) - RESOLVED

The original investigation was about pivotId not being saved. This was FIXED in commit `5a0f81e` by having Claude return `selected_pivotId` directly instead of relying on storyID lookup.

This documentation was then updated to include the within-issue headline deduplication gap that was discovered during that investigation.
