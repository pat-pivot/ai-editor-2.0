# Browserbase Scraping Debug Report

**Date:** January 9, 2026
**Issue:** Browserbase extraction failing for all articles - `raw` field is empty
**Affected Record:** `p_pcs5uj` (New York Times article)

---

## Root Cause Analysis

### PRIMARY ISSUE: Missing `project_id` in Browserbase API Call

The Render logs show this error repeating for **every single extraction attempt**:

```
[Browserbase Retry] Failed: SessionsResource.create() missing 1 required keyword-only argument: 'project_id'
```

**Location:** `/workers/utils/browserbase_scraper.py` lines 142-163

The `browserbase` Python SDK version 1.4.0 **requires** `project_id` as a mandatory argument for `sessions.create()`. The current code treats it as optional:

```python
# Line 151-153 in browserbase_scraper.py
if self.project_id:
    session_settings["project_id"] = self.project_id
```

**When `BROWSERBASE_PROJECT_ID` is not set, `project_id` is never passed, and the API call fails.**

---

## Secondary Issues Found

### Issue 2: Wrong Airtable Field Name

**Location:** `/workers/jobs/browserbase_retry.py` line 167

```python
pivot_id = fields.get("pivotId", "")  # WRONG - should be "pivot_id"
```

The Newsletter Selects table (`tblKhICCdWnyuqgry`) uses `pivot_id` (snake_case), not `pivotId` (camelCase).

**Verified field names from Airtable API:**
- `pivot_id` (NOT `pivotId`)
- `core_url`
- `source_name`
- `date_ai_process`
- `date_og_published`
- `topic`
- `interest_score`
- `sentiment`
- `headline`
- `gnews_url`

**Note:** The `raw` field does NOT exist yet in the Airtable schema! This may need to be added.

---

### Issue 3: Missing Environment Variables

The `.env.local` file has **NO Browserbase configuration**:

```bash
# Missing from .env.local:
BROWSERBASE_API_KEY=???
BROWSERBASE_PROJECT_ID=???
```

Even if `BROWSERBASE_API_KEY` is set in Render's environment, `BROWSERBASE_PROJECT_ID` is also required by the SDK.

---

## Evidence from Render Logs

### Pipeline Night Run (2026-01-09 at 04:10 AM ET)

```
[Browserbase Retry] Starting at 04:10 AM ET
[Browserbase Retry] Query formula: AND(OR({source_name}='WSJ', {source_name}='Wall Street Journal', {source_name}='Bloomberg', {source_...
[Browserbase Retry] Found 11 articles needing retry
[Browserbase Retry] Extracting: Bloomberg - https://www.bloomberg.com/news/articles/2026-01-08/uk-s-star...
[Browserbase Retry] Failed: SessionsResource.create() missing 1 required keyword-only argument: 'project_id'
[Browserbase Retry] Extracting: Bloomberg - https://www.bloomberg.com/news/videos/2026-01-08/ai-policy-r...
[Browserbase Retry] Failed: SessionsResource.create() missing 1 required keyword-only argument: 'project_id'
... (all 11 articles failed with same error)
[Browserbase Retry] Complete: 0/11 succeeded in 1.2s
```

The pipeline found 11 articles needing retry, but **all 11 failed** because `project_id` was not passed.

---

## The Specific Record: p_pcs5uj

**Airtable Record:**
```json
{
  "id": "recykkwoIakFtynzZ",
  "fields": {
    "pivot_id": "p_pcs5uj",
    "core_url": "https://www.nytimes.com/2026/01/09/technology/grok-deepfakes-ai-x.html",
    "source_name": "New York Times",
    "date_ai_process": "2026-01-09T16:14:15.598Z",
    "date_og_published": "2026-01-09T14:10:21.000Z",
    "topic": "SECURITY",
    "interest_score": 20,
    "sentiment": -7,
    "headline": "Elon Musk's A.I. Is Generating Sexualized Images of Real People, Fueling Outrage"
  }
}
```

**Why it has no `raw` field:**
1. Source is "New York Times" - which IS in `BROWSERBASE_SOURCES` list
2. Browserbase was supposed to extract it but failed due to missing `project_id`
3. The `raw` field was never populated because extraction failed

---

## Required Fixes

### Fix 1: Update browserbase_scraper.py (CRITICAL)

**File:** `/workers/utils/browserbase_scraper.py`
**Lines:** 142-163 (`_create_session` method)

The `project_id` must ALWAYS be passed, not conditionally. Two options:

**Option A:** Make `project_id` required (fail fast if not set)
```python
def __init__(self):
    # ...existing code...
    self.project_id = os.environ.get("BROWSERBASE_PROJECT_ID")
    if not self.project_id:
        raise ValueError("BROWSERBASE_PROJECT_ID environment variable not set")
```

**Option B:** Always include `project_id` in session creation
```python
def _create_session(self, site_key: Optional[str] = None) -> object:
    session_settings = {
        "project_id": self.project_id,  # REQUIRED - must always be passed
        "browser_settings": {
            "advanced_stealth": True,
        },
        "proxies": True,
    }
    # ... rest of method
```

### Fix 2: Update browserbase_retry.py Field Name

**File:** `/workers/jobs/browserbase_retry.py`
**Line:** 167

Change:
```python
pivot_id = fields.get("pivotId", "")
```

To:
```python
pivot_id = fields.get("pivot_id", "")
```

### Fix 3: Add Environment Variables to Render

Add these to ALL pipeline cron jobs in Render:

1. `BROWSERBASE_API_KEY` - Get from Browserbase dashboard
2. `BROWSERBASE_PROJECT_ID` - Get from Browserbase dashboard (usually visible in the URL or settings)

**Services to update:**
- `crn-d5e2shv5r7bs73ca4dp0` (ai-editor-pipeline-night)
- `crn-d5e2sl2li9vc73dt5q40` (ai-editor-pipeline-morning)
- `crn-d5e2smq4d50c73fjo0tg` (ai-editor-pipeline-eod)
- `srv-d563ffvgi27c73dtqdq0` (ai-editor-trigger)

### Fix 4: Add `raw` Field to Airtable (if not exists)

The Newsletter Selects table may need a `raw` field added for storing extracted content.

---

## Verification Steps After Fix

1. Set `BROWSERBASE_API_KEY` and `BROWSERBASE_PROJECT_ID` in Render
2. Deploy updated code
3. Manually trigger pipeline or wait for next scheduled run
4. Check logs for:
   - `[Browserbase Retry] Session created: xxx`
   - `[Browserbase Retry] Success: XXXX chars extracted`
5. Verify `raw` field is populated in Airtable

---

## Summary

| Issue | File | Line | Fix |
|-------|------|------|-----|
| Missing `project_id` | `browserbase_scraper.py` | 151-153 | Make `project_id` required |
| Wrong field name | `browserbase_retry.py` | 167 | Change `pivotId` to `pivot_id` |
| Missing env vars | Render dashboard | - | Add `BROWSERBASE_PROJECT_ID` |
| Missing `raw` field? | Airtable | - | Add field if needed |

**Priority:** Fix #1 (project_id) is the blocking issue - must be resolved first.

---

## Code References

### browserbase_scraper.py - Session Creation (THE BUG)

**File:** `/Users/patsimmons/client-coding/pivot-5-website_11.19.25/ai-editor-2.0-full-stack-application/app/workers/utils/browserbase_scraper.py`

```python
# Lines 142-163 - _create_session method
def _create_session(self, site_key: Optional[str] = None) -> object:
    """Create a Browserbase session with stealth settings."""
    session_settings = {
        "browser_settings": {
            "advanced_stealth": True,
        },
        "proxies": True,  # Enable proxy rotation
    }

    # BUG: project_id is only added if self.project_id is set
    # But browserbase SDK 1.4.0 REQUIRES project_id
    if self.project_id:
        session_settings["project_id"] = self.project_id

    # This call fails with:
    # "SessionsResource.create() missing 1 required keyword-only argument: 'project_id'"
    return self.bb.sessions.create(**session_settings)
```

### browserbase_retry.py - Field Name Mismatch

**File:** `/Users/patsimmons/client-coding/pivot-5-website_11.19.25/ai-editor-2.0-full-stack-application/app/workers/jobs/browserbase_retry.py`

```python
# Line 167 - WRONG field name
pivot_id = fields.get("pivotId", "")  # Should be "pivot_id"
```

### airtable.py - Correctly Uses pivot_id

**File:** `/Users/patsimmons/client-coding/pivot-5-website_11.19.25/ai-editor-2.0-full-stack-application/app/workers/utils/airtable.py`

```python
# Lines 817-820 - Correct field name
fields=[
    'pivot_id', 'source_name', 'core_url', 'raw',  # pivot_id is correct
    'headline', 'date_ai_process', 'interest_score'
]
```
