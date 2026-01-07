# Step 2 Slot Selection - Deduplication Investigation & Fix

**Date:** January 7, 2026
**Issue:** Duplicate stories appearing in consecutive newsletters
**Severity:** High - User-facing quality issue

---

## Status

**Status:** ✅ IMPLEMENTED - Pending Pat's test/approval

**Deployed:** January 7, 2026
**Commit:** `06de29f` - "Add semantic deduplication to Step 2 Slot Selection"
**Services Updated:**
- ai-editor-worker (live)
- ai-editor-trigger (live)

### To Test
1. Go to AI Editor Dashboard → Step 2: Slot Selection → Click "Run Now"
2. Check logs for: `[Step 2] Fetching decorated stories for semantic deduplication...`
3. Verify no duplicate stories appear in next newsletter issue

---

## 1. Investigation Results

### Confirmed Duplicates Found

#### Duplicate 1: Utah AI Prescription Story

| Field | Jan 6 (Slot 3) | Jan 8 (Slot 3) |
|-------|---------------|---------------|
| **storyID** | `rec5sx335pKRheaGe` | `rec2jhon9fc1Dqft9` |
| **headline** | "Utah Becomes First State to Allow AI Systems to Renew Prescriptions Without Human Review" | "Utah Launches First US Program Allowing AI to Renew Prescriptions Without Doctors" |
| **pivotId** | Different | Different |

**Same underlying news story** - Utah's AI prescription renewal program. Different wording, different IDs, but semantically identical content.

#### Duplicate 2: xAI $20B Funding Story

| Field | Jan 7 (Slot 1) | Jan 8 (Slot 1) |
|-------|---------------|---------------|
| **headline** | "Elon Musk's xAI raises $20 billion from investors including Nvidia, Cisco, Fidelity" | "Musk's xAI Closed $20 Billion Funding With Nvidia Backing" |

**Same underlying news story** - xAI's $20 billion funding round. Different headline phrasing for the same event.

---

## 2. Root Cause Analysis

### Current Deduplication Logic

**File:** `app/workers/jobs/slot_selection.py` (lines 189-205)

```python
def is_duplicate(candidate):
    """Check if candidate matches any recently used story by ID, headline, or pivotId"""
    fields = candidate.get('fields', {})
    story_id = fields.get('storyID', '')
    headline = (fields.get('headline', '') or '').lower().strip()
    pivot_id = fields.get('pivotId', '')

    # Check storyID
    if story_id in excluded_ids:
        return True
    # Check headline (case-insensitive)
    if headline and headline in recent_headlines:
        return True
    # Check pivotId
    if pivot_id and pivot_id in recent_pivot_ids:
        return True
    return False
```

### Why Current Logic Fails

The current deduplication only checks for **exact matches** of:
1. `storyID` - Unique per ingestion, same story gets new ID when re-ingested
2. `headline` - Case-insensitive exact match, fails on paraphrased headlines
3. `pivotId` - Unique per article record, same story gets new pivotId

**This fails because:**
- Same news story can be published by multiple sources with different headlines
- FreshRSS re-ingests articles, assigning new storyIDs/pivotIds
- Headlines are often paraphrased ("Utah Becomes First State..." vs "Utah Launches First US Program...")
- No semantic/content comparison exists

### Data Source Limitation

**File:** `app/workers/utils/airtable.py` (lines 324-349)

```python
def get_recent_sent_issues(self, lookback_days: int = 14) -> List[dict]:
    """Currently pulls from Selected Slots table"""
    table = self._get_table(self.ai_editor_base_id, self.selected_slots_table_id)
    filter_formula = f"IS_AFTER({{issue_date}}, DATEADD(TODAY(), -{lookback_days}, 'days'))"
    records = table.all(formula=filter_formula, sort=['-issue_date'])
    return records
```

**Selected Slots table only contains:**
- `slot_X_headline` - Just the headline text
- `slot_X_storyId` - The storyID
- `slot_X_pivotId` - The pivotId

**No semantic content available** for Claude to compare against.

---

## 3. Proposed Solution

### Strategy: Use Newsletter Issue Stories for Richer Context

The **Newsletter Issue Stories** table (Decoration table) contains much richer context:

| Field | Description | Use for Deduplication |
|-------|-------------|----------------------|
| `headline` | Article headline | Primary comparison |
| `raw` | Full article text | Semantic comparison |
| `b1`, `b2`, `b3` | AI-generated bullet points | Content summary |
| `ai_dek` | AI-generated description | Story essence |
| `source_id` | Source publication | Context |
| `company` | Featured company | Entity matching |

### Two-Phase Approach

#### Phase 1: Semantic Deduplication (Claude-based)
Pass richer context to Claude's slot selection prompt, enabling semantic comparison:
- Include bullet points and ai_dek from recent stories
- Let Claude identify semantic duplicates based on content, not just exact headline match

#### Phase 2: Embedding-based Similarity (Future Enhancement)
- Generate embeddings for headlines + bullet points
- Use cosine similarity to flag potential duplicates
- Threshold-based filtering before Claude call

---

## 4. Implementation Plan

### Step 1: Create New Query Function for Recent Story Context

**File:** `app/workers/utils/airtable.py`

Add new function to query Newsletter Issue Stories table:

```python
def get_recent_decorated_stories(self, lookback_days: int = 14) -> List[dict]:
    """
    Get recently decorated stories with full content for semantic deduplication.

    Uses Newsletter Issue Stories (Decoration) table which has:
    - headline, raw, b1, b2, b3, ai_dek for semantic comparison
    - storyID, pivotId for exact match fallback
    - company, source_id for entity matching

    Returns:
        List of decorated story records from last N days
    """
    # Newsletter Issue Stories table in AI Editor 2.0 base
    table = self._get_table(
        self.ai_editor_base_id,
        "tbla16LJCf5Z6cRn3"  # Newsletter Issue Stories (Decoration)
    )

    # Filter for recent stories that have been decorated
    filter_formula = (
        f"AND("
        f"IS_AFTER({{created_at}}, DATEADD(TODAY(), -{lookback_days}, 'days')),"
        f"{{headline}}!=''"
        f")"
    )

    records = table.all(
        formula=filter_formula,
        sort=['-created_at'],
        fields=[
            'storyID', 'pivotId', 'headline',
            'b1', 'b2', 'b3', 'ai_dek',
            'company', 'source_id', 'issue_id'
        ]
    )

    return records
```

### Step 2: Update _extract_recent_issues_data() Function

**File:** `app/workers/jobs/slot_selection.py`

Modify to include richer context:

```python
def _extract_recent_issues_data(issues: List[dict], decorated_stories: List[dict] = None) -> dict:
    """
    Extract data from recent issues for diversity rule enforcement.

    Now includes semantic context from decorated stories for Claude comparison.
    """
    data = {
        "headlines": [],
        "storyIds": [],
        "pivotIds": [],
        "slot1Headline": None,
        "story_summaries": []  # NEW: For semantic deduplication
    }

    if not issues:
        return data

    # Extract from Selected Slots (existing logic)
    for idx, issue in enumerate(issues):
        fields = issue.get('fields', {})

        for i in range(1, 6):
            headline = fields.get(f'slot_{i}_headline', '')
            story_id = fields.get(f'slot_{i}_storyId', '')
            pivot_id = fields.get(f'slot_{i}_pivotId', '')

            if headline:
                data["headlines"].append(headline)
            if story_id:
                data["storyIds"].append(story_id)
            if pivot_id:
                data["pivotIds"].append(pivot_id)

        if idx == 0:
            data["slot1Headline"] = fields.get('slot_1_headline')

    # NEW: Add semantic context from decorated stories
    if decorated_stories:
        for story in decorated_stories[:30]:  # Limit to most recent 30
            fields = story.get('fields', {})
            summary = {
                "headline": fields.get('headline', ''),
                "bullets": [
                    fields.get('b1', ''),
                    fields.get('b2', ''),
                    fields.get('b3', '')
                ],
                "dek": fields.get('ai_dek', ''),
                "company": fields.get('company', ''),
                "storyId": fields.get('storyID', '')
            }
            # Only add if has content
            if summary["headline"] and any(summary["bullets"]):
                data["story_summaries"].append(summary)

    return data
```

### Step 3: Update select_slots() Main Function

**File:** `app/workers/jobs/slot_selection.py`

Add call to fetch decorated stories:

```python
def select_slots() -> dict:
    # ... existing code ...

    try:
        # 1. Get recent issues for diversity rules (14-day lookback)
        print(f"[Step 2] Fetching recent issues (last {DUPLICATE_LOOKBACK_DAYS} days)...")
        recent_issues = airtable.get_recent_sent_issues(DUPLICATE_LOOKBACK_DAYS)

        # NEW: Get decorated stories for semantic context
        print(f"[Step 2] Fetching decorated stories for semantic deduplication...")
        decorated_stories = airtable.get_recent_decorated_stories(DUPLICATE_LOOKBACK_DAYS)
        print(f"[Step 2] Found {len(decorated_stories)} decorated stories")

        # Pass decorated_stories to extraction function
        recent_data = _extract_recent_issues_data(recent_issues, decorated_stories)
        print(f"[Step 2] Recent issues found: {len(recent_issues)}, "
              f"total storyIds: {len(recent_data['storyIds'])}, "
              f"story_summaries: {len(recent_data.get('story_summaries', []))}")

        # ... rest of function ...
```

### Step 4: Update Claude System Prompt

**Database:** `system_prompts` table
**Key:** `slot_selection_agent`

Add instruction for semantic deduplication:

```
## SEMANTIC DEDUPLICATION RULES

You have access to recent story summaries including:
- Headlines
- Bullet points (b1, b2, b3)
- AI-generated descriptions (ai_dek)
- Companies mentioned

**CRITICAL:** Do NOT select a story if it covers the SAME NEWS EVENT as any recent story, even if:
- The headline is worded differently
- It comes from a different source
- It has a different storyID

Examples of SAME news event (reject):
- "Utah Becomes First State to Allow AI..." vs "Utah Launches First US Program Allowing AI..."
- "xAI raises $20 billion..." vs "Musk's xAI Closed $20 Billion Funding..."

When comparing, consider:
1. Are they about the same company/entity?
2. Are they about the same announcement, product, or event?
3. Do the bullet points describe the same key facts?

If yes to all three, it's a DUPLICATE - skip to next candidate.
```

### Step 5: Update Claude Client to Pass Summaries

**File:** `app/workers/utils/claude.py`

Modify `_build_slot_system_prompt()` to include story summaries:

```python
def _build_slot_system_prompt(self, slot: int, recent_data: dict, cumulative_state: dict) -> str:
    # ... existing code ...

    # NEW: Add story summaries section
    story_summaries = recent_data.get('story_summaries', [])
    if story_summaries:
        prompt += "\n\n## RECENT STORY SUMMARIES (for semantic deduplication)\n"
        prompt += "Do NOT select stories about the same news event as these:\n\n"

        for i, summary in enumerate(story_summaries[:20], 1):  # Limit to 20
            prompt += f"### Recent Story {i}\n"
            prompt += f"- Headline: {summary.get('headline', 'N/A')}\n"
            bullets = [b for b in summary.get('bullets', []) if b]
            if bullets:
                prompt += f"- Key Points: {'; '.join(bullets)}\n"
            if summary.get('company'):
                prompt += f"- Company: {summary.get('company')}\n"
            prompt += "\n"

    return prompt
```

---

## 5. Files to Modify

| File | Changes |
|------|---------|
| `app/workers/utils/airtable.py` | Add `get_recent_decorated_stories()` function |
| `app/workers/jobs/slot_selection.py` | Update `_extract_recent_issues_data()`, modify `select_slots()` |
| `app/workers/utils/claude.py` | Update `_build_slot_system_prompt()` to include summaries |
| Database: `system_prompts` | Update `slot_selection_agent` prompt with semantic rules |

---

## 6. Testing Plan

### Unit Tests

1. **Test `get_recent_decorated_stories()`**
   - Verify correct table queried
   - Verify fields returned (headline, b1, b2, b3, ai_dek)
   - Verify date filtering works

2. **Test `_extract_recent_issues_data()` with summaries**
   - Verify story_summaries populated correctly
   - Verify limit of 30 stories respected
   - Verify empty/missing fields handled gracefully

### Integration Tests

1. **Run against Jan 6-8 data**
   - Feed Jan 6 decorated stories as context
   - Present Jan 8 candidates (including Utah AI story)
   - Verify Claude rejects Utah story as semantic duplicate

2. **Manual verification**
   - Run Step 2 locally with verbose logging
   - Confirm story_summaries appear in Claude prompt
   - Confirm semantic duplicates rejected

### Regression Tests

1. **Performance**
   - Measure time increase from additional Airtable query
   - Ensure prompt size stays within Claude context limits

2. **False positives**
   - Verify similar-but-different stories still get selected
   - Example: Two different AI funding rounds should both be selectable

---

## 7. Rollout Plan

### ✅ Phase 1: Deploy Code Changes (COMPLETE - Jan 7, 2026)
1. ✅ Add `get_recent_decorated_stories()` to airtable.py
2. ✅ Update slot_selection.py functions
3. ✅ Update claude.py prompt builder
4. ✅ Deploy to Render

### ✅ Phase 2: Update System Prompt (COMPLETE - Jan 7, 2026)
1. ✅ Update `slot_selection_agent` prompt in database
2. ✅ Add semantic deduplication rules
3. ✅ Test via dashboard prompt editor

### ⏳ Phase 3: Monitor (Pending Pat's Verification)
1. Check daily newsletter output for duplicates
2. Review Step 2 logs for rejection reasons
3. Gather feedback on story diversity

### ⏳ Phase 4: Tune (Pending Pat's Verification)
1. Adjust number of story summaries passed (currently 20)
2. Refine semantic comparison instructions
3. Consider adding embedding-based pre-filtering

---

## 8. Alternative Approaches Considered

### Approach 1: URL-based Deduplication
- Pro: Simple, deterministic
- Con: Same story from different sources has different URLs

### Approach 2: Embedding Similarity
- Pro: Very accurate semantic matching
- Con: Requires embedding infrastructure, adds latency

### Approach 3: Entity Extraction + Event Matching
- Pro: Precise matching on company + event type
- Con: Complex to implement, requires NER pipeline

**Chosen Approach:** Semantic context for Claude is the best balance of:
- Low implementation complexity
- High accuracy (Claude excels at semantic understanding)
- No new infrastructure required
- Easy to tune via prompt adjustments

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Duplicate stories in 14-day window | 0 |
| False positive rejections | < 5% |
| Step 2 execution time increase | < 10 seconds |
| Prompt token count increase | < 2000 tokens |

---

## 10. Appendix: Airtable Table References

| Table | Base ID | Table ID |
|-------|---------|----------|
| Selected Slots | `appglKSJZxmA9iHpl` | `tblzt2z7r512Kto3O` |
| Newsletter Issue Stories | `appglKSJZxmA9iHpl` | `tbla16LJCf5Z6cRn3` |
| Pre-Filter Log | `appglKSJZxmA9iHpl` | `tbl72YMsm9iRHj3sp` |

### Newsletter Issue Stories Fields

| Field | Type | Description |
|-------|------|-------------|
| `storyID` | Text | Unique story identifier |
| `pivotId` | Text | Pivot internal ID |
| `headline` | Text | Article headline |
| `raw` | Long text | Full article content |
| `b1`, `b2`, `b3` | Text | AI-generated bullet points |
| `ai_dek` | Text | AI-generated description |
| `company` | Text | Featured company name |
| `source_id` | Text | Source publication |
| `issue_id` | Text | Associated newsletter issue |
| `created_at` | Date | Record creation timestamp |
