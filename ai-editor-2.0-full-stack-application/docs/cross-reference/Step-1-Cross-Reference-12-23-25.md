# Step 1: Pre-Filter Cross-Reference Analysis

**Document:** Step-1-Cross-Reference-12-23-25.md
**Date:** December 23, 2025
**Infrastructure Doc:** AI-Editor-2.0-Infrastructure-Step-1-12-23-25.md
**Implementation File:** `/app/src/lib/airtable.ts`

---

## Summary

| Category | Status |
|----------|--------|
| Dashboard READ Operations | ✅ Implemented |
| Python Worker Job | ❌ Not Implemented |
| Gemini AI Integration | ❌ Not Implemented |
| Airtable WRITE Operations | ❌ Not Implemented |

---

## Node-by-Node Cross-Reference

### Node 1: Schedule Trigger
**Infrastructure:** `0 2 * * 2-6` (9:00 PM EST, Mon-Fri)
**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker with Redis Queue (RQ) scheduled job
- Cron expression: `0 2 * * 2-6` UTC (9:00 PM EST)
- File: `workers/jobs/prefilter.py`

---

### Node 2: Get Fresh Stories
**Infrastructure:**
- Base: `appwSozYTkrsQWUXB` (Pivot Media Master)
- Table: `tblY78ziWp5yhiGXp` (Newsletter Stories)
- Filter: `AND(IS_AFTER({date_og_published}, DATEADD(TODAY(), -7, 'days')), {ai_headline}!='')`
- Sort: `date_og_published` DESC
- Max Records: 100
- Fields: `storyID`, `pivotId`, `ai_headline`, `ai_dek`, `date_og_published`, `newsletter`, `topic`

**Implementation:** ✅ Implemented in `getStories()` (lines 266-330)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Base ID | `appwSozYTkrsQWUXB` | `process.env.AIRTABLE_BASE_ID` | ✅ |
| Table ID | `tblY78ziWp5yhiGXp` | `process.env.AIRTABLE_NEWSLETTER_STORIES_TABLE` | ✅ |
| Filter | `IS_AFTER + ai_headline!=''` | `IS_AFTER + newsletter='pivot_ai'` | ⚠️ Partial |
| Max Records | 100 | 100 | ✅ |
| Sort | `date_og_published` DESC | `date_og_published` DESC | ✅ |
| Fields | 7 fields | 5 fields | ⚠️ Missing `ai_dek`, `topic` |

**Gaps:**
1. Filter uses `newsletter='pivot_ai'` but should also check `ai_headline!=''`
2. Missing fields: `ai_dek`, `topic` - needed for Gemini prompt

---

### Node 3: Filter Pivot AI Stories
**Infrastructure:** Filter `{{ $json.fields.newsletter }}` equals `pivot_ai`
**Implementation:** ✅ Implemented in `getStories()` filterByFormula

The implementation combines Node 2 + Node 3 into a single Airtable query which is correct and efficient.

---

### Node 4: Get Queued Stories
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tblN1RypWAOBMOfQ5` (AI Editor - Queued Stories)
- Filter: `{status}='pending'`

**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Add `queuedStories` table to `TABLES` object
- Add environment variable: `AI_EDITOR_QUEUED_STORIES_TABLE`
- Create `getQueuedStories()` function
- Python worker must fetch and merge with fresh stories

---

### Node 5: Merge Story Sources
**Infrastructure:** Combine fresh stories + queued stories
**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker: merge arrays before processing

---

### Node 6: Get Source Scores
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tbl3Zkdl1No2edDLK` (Source Credibility)
- Max Records: 500
- Fields: `source_name`, `credibility_score`

**Implementation:** ✅ Implemented in `getSources()` (lines 179-195)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Base ID | `appglKSJZxmA9iHpl` | `process.env.AI_EDITOR_BASE_ID` | ✅ |
| Table ID | `tbl3Zkdl1No2edDLK` | `process.env.AI_EDITOR_SOURCE_SCORES_TABLE` | ✅ |
| Max Records | 500 | 100 | ⚠️ Lower |
| Fields | 2 | 2 | ✅ |

**Gap:** Max records is 100 in implementation but 500 in infrastructure. Should update to 500.

---

### Node 7: Build Source Lookup
**Infrastructure:** JavaScript code that builds `{sourceName.toLowerCase(): score}` lookup map
**Implementation Status:** ⚠️ Dashboard-only (no worker)

The dashboard `getStories()` function builds a similar `sourceMap` (lines 288-295) but it maps `pivotId` → `source_id`, not `source_name` → `credibility_score`.

**Action Required:**
- Python worker function: `build_source_lookup(sources: List[dict]) -> dict`
- Returns: `{source_name.lower(): credibility_score}`

---

### Node 8: Get Yesterday's Issue
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tblzt2z7r512Kto3O` (Selected Slots)
- Filter: `{status}='sent'`
- Sort: `issue_date` DESC
- Max Records: 1

**Implementation:** ✅ Implemented in `getSelectedSlots()` (lines 390-467)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Filter | `{status}='sent'` | None | ❌ Missing filter |
| Sort | `issue_date` DESC | `issue_date` DESC | ✅ |
| Max Records | 1 | 1 | ✅ |

**Gap:** Implementation fetches latest issue regardless of status. Infrastructure specifically filters for `status='sent'`.

---

### Node 9: Extract Yesterday's Data
**Infrastructure:** JavaScript code that extracts headlines, storyIds, pivotIds from yesterday's issue
**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker function: `extract_yesterday_data(slots: SelectedSlots) -> dict`
- Returns: `{headlines: [], storyIds: [], pivotIds: []}`

---

### Node 10: Split In Batches
**Infrastructure:** Batch size 10 for Gemini API calls
**Implementation Status:** ❌ Not Implemented (Python worker needed)

**Action Required:**
- Python worker: process stories in batches of 10

---

### Node 11: Lookup Source ID
**Infrastructure:**
- Base: `appwSozYTkrsQWUXB` (Pivot Media Master)
- Table: `tblGumae8KDpsrWvh` (Articles)
- Filter: `{pivot_Id}='{{ $json.fields.pivotId }}'`
- Fields: `source_id`, `original_url`

**Implementation:** ⚠️ Partial in `getStories()` (lines 281-295)

The dashboard fetches all recent articles and builds a lookup map. The infrastructure does per-story lookups. Both approaches work, but:
- Dashboard: Bulk fetch (more efficient for UI)
- Worker: Per-story fetch (matches n8n exactly)

---

### Node 12: Prepare Gemini Prompt
**Infrastructure:** JavaScript code that assembles:
- `storyId`, `pivotId`, `headline`, `dek`, `topic`
- `source`, `credibilityScore`
- `hoursAgo` (calculated from `date_og_published`)
- `originalUrl`
- `yesterdayHeadlines`, `yesterdayStoryIds`

**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker function: `prepare_gemini_prompt(story: dict, context: dict) -> dict`

---

### Node 13: Gemini Pre-Filter
**Infrastructure:**
- Model: `gemini-3-flash-preview`
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent`
- Temperature: 0.3
- Max Tokens: 256
- Response Type: `application/json`

**Implementation Status:** ❌ Not Implemented

**Critical Gap:** The dashboard `getStories()` function (lines 302-316) uses **keyword matching** to determine eligible slots, NOT Gemini AI. This is a fundamental difference.

**Dashboard Fallback (WRONG):**
```typescript
// Lines 302-316: keyword-based slot assignment
if (headlineLower.includes("job")) eligibleSlots.push(1);
if (headlineLower.includes("openai")) eligibleSlots.push(2);
// ... etc
```

**Infrastructure Requirement (CORRECT):**
```python
# Python worker must use Gemini AI
response = gemini_client.generate_content(
    model="gemini-3-flash-preview",
    prompt=prefilter_prompt,
    temperature=0.3
)
eligibility = json.loads(response)
```

**Action Required:**
- Python worker: Gemini API client
- Environment variable: `GEMINI_API_KEY`
- Function: `gemini_prefilter(story: dict) -> dict`

---

### Node 14: Parse Gemini Response
**Infrastructure:** JavaScript code that parses JSON response
**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker: JSON parsing with error handling
- Extract: `eligible_slots`, `primary_slot`, `reasoning`

---

### Node 15: Filter Has Eligible Slots
**Infrastructure:** Filter where `eligibleSlots.length > 0`
**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker: skip stories with no eligible slots

---

### Node 16: Split by Slot
**Infrastructure:** Create one Pre-Filter Log record per eligible slot
**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker: for each story, create N records (one per eligible slot)

---

### Node 17: Write Pre-Filter Log
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tbl72YMsm9iRHj3sp` (Pre-Filter Log)
- Operation: Create record
- Fields: `storyID`, `pivotId`, `headline`, `original_url`, `source_id`, `date_og_published`, `date_prefiltered`, `slot`

**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker: Airtable CREATE operation
- Function: `write_prefilter_log(record: dict) -> str` (returns record ID)

---

## Environment Variables Required

### Currently Configured
```bash
AIRTABLE_API_KEY=✅ Configured
AIRTABLE_BASE_ID=✅ Configured (appwSozYTkrsQWUXB)
AI_EDITOR_BASE_ID=✅ Configured (appglKSJZxmA9iHpl)
AI_EDITOR_PREFILTER_LOG_TABLE=✅ Configured (tbl72YMsm9iRHj3sp)
AI_EDITOR_SELECTED_SLOTS_TABLE=✅ Configured (tblzt2z7r512Kto3O)
AI_EDITOR_SOURCE_SCORES_TABLE=✅ Configured (tbl3Zkdl1No2edDLK)
AIRTABLE_NEWSLETTER_STORIES_TABLE=✅ Configured (tblY78ziWp5yhiGXp)
AIRTABLE_ARTICLES_TABLE=✅ Configured (tblGumae8KDpsrWvh)
```

### Missing
```bash
AI_EDITOR_QUEUED_STORIES_TABLE=❌ Missing (tblN1RypWAOBMOfQ5)
GEMINI_API_KEY=❌ Missing for worker
```

---

## Python Worker Specification

**File:** `workers/jobs/prefilter.py`
**Queue:** Redis Queue (RQ)
**Schedule:** `0 2 * * 2-6` UTC

### Required Functions

```python
# 1. Main job function
def prefilter_stories() -> dict:
    """Step 1: Pre-Filter Cron Job"""
    pass

# 2. Airtable operations
def get_fresh_stories() -> List[dict]:
    """Node 2: Get Fresh Stories from Newsletter Stories table"""
    pass

def get_queued_stories() -> List[dict]:
    """Node 4: Get Queued Stories from AI Editor base"""
    pass

def get_source_scores() -> List[dict]:
    """Node 6: Get Source Credibility scores"""
    pass

def get_yesterday_issue() -> Optional[dict]:
    """Node 8: Get yesterday's sent issue"""
    pass

def write_prefilter_log(record: dict) -> str:
    """Node 17: Write to Pre-Filter Log table"""
    pass

# 3. Data transformation
def build_source_lookup(sources: List[dict]) -> dict:
    """Node 7: Build source_name -> score lookup"""
    pass

def extract_yesterday_data(issue: dict) -> dict:
    """Node 9: Extract headlines, storyIds, pivotIds"""
    pass

def prepare_gemini_prompt(story: dict, context: dict) -> dict:
    """Node 12: Prepare prompt data"""
    pass

# 4. AI integration
def gemini_prefilter(prompt_data: dict) -> dict:
    """Node 13: Call Gemini API for slot eligibility"""
    pass

def parse_gemini_response(response: dict) -> dict:
    """Node 14: Parse JSON response"""
    pass
```

---

## Critical Issues Found

### Issue 1: Keyword-Based Slot Assignment (Dashboard)
**Location:** `lib/airtable.ts` lines 302-316
**Problem:** Dashboard uses string matching instead of Gemini AI
**Impact:** Slot eligibility will differ from n8n workflow
**Resolution:** This is acceptable as a dashboard fallback for viewing. The Python worker MUST use Gemini AI.

### Issue 2: Missing Queued Stories Table
**Location:** `lib/airtable.ts` TABLES object
**Problem:** No reference to AI Editor - Queued Stories table
**Impact:** Manual priority stories won't be considered
**Resolution:** Add table configuration and create worker function

### Issue 3: Yesterday's Issue Filter Missing
**Location:** `getSelectedSlots()` line 395
**Problem:** Does not filter by `{status}='sent'`
**Impact:** May return draft/pending issue instead of yesterday's sent issue
**Resolution:** Add filterByFormula to match infrastructure

---

## Implementation Priority

1. **High Priority (Worker Core):**
   - [ ] Create `workers/jobs/prefilter.py`
   - [ ] Implement Gemini API integration
   - [ ] Implement Pre-Filter Log WRITE operation

2. **Medium Priority (Dashboard Updates):**
   - [ ] Add `AI_EDITOR_QUEUED_STORIES_TABLE` environment variable
   - [ ] Fix `getSelectedSlots()` filter for `status='sent'`
   - [ ] Increase `getSources()` maxRecords to 500

3. **Low Priority (Enhancements):**
   - [ ] Add `ai_dek`, `topic` fields to `getStories()`
   - [ ] Display Pre-Filter Log in dashboard with Gemini reasoning

---

*Cross-reference generated: December 23, 2025*
