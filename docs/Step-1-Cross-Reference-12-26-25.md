# Step 1 Pre-Filter: n8n vs Full-Stack Cross-Reference

**Date:** December 26, 2025
**n8n Workflow:** `STEP-1-AI-Editor-2.0-AI-Editor-Pre-Filter Cron-12-26-25.json`
**Full-Stack Files:** `workers/jobs/prefilter.py`, `workers/utils/airtable.py`

---

## Executive Summary

This document identifies **6 critical differences** between the updated n8n workflow and the current full-stack Python implementation. The most significant change is the **deduplication via UPSERT** operation, which prevents duplicate Pre-Filter Log entries.

---

## Differences Summary

| # | Area | n8n Workflow | Full-Stack App | Priority |
|---|------|--------------|----------------|----------|
| 1 | **Airtable Write Operation** | UPSERT with `storyID` matching | batch_create (creates duplicates) | **CRITICAL** |
| 2 | **Newsletter Filter** | 3 newsletters (pivot_ai, pivot_build, pivot_invest) | 1 newsletter (pivot_ai only) | HIGH |
| 3 | **Slot 1 Company Filter** | 4 companies | 8 companies | MEDIUM |
| 4 | **Yesterday Issue Lookback** | 14-day lookback | Most recent only | MEDIUM |
| 5 | **Queued Stories Filter** | Includes expires_date check | No expiration check | LOW |
| 6 | **Pull Articles Source** | Separate node with 7-day filter | get_articles_batch | LOW |

---

## Detailed Analysis

### 1. UPSERT vs CREATE (CRITICAL - Deduplication)

**The Problem:** Every time the pre-filter runs, it creates new records in the Pre-Filter Log table even if the same story was already pre-filtered. This causes duplicate entries and inflated candidate counts.

**n8n Implementation:**
```json
// Write Slot 1 Log (line 210), Write Slot 2 Log (line 395), etc.
{
  "operation": "upsert",
  "matchingColumns": ["storyID"],
  "fieldsToSend": "autoMapInputData"
}
```
Uses `storyID` as the unique key - if a story already exists, it updates instead of creating a duplicate.

**Full-Stack Implementation:**
```python
# workers/utils/airtable.py lines 226-233
def write_prefilter_log_batch(self, records: List[dict]) -> List[str]:
    table = self._get_table(self.ai_editor_base_id, self.prefilter_log_table_id)
    created = table.batch_create(records)  # <-- Creates duplicates!
    return [r['id'] for r in created]
```

**Required Fix:**
```python
def write_prefilter_log_batch(self, records: List[dict]) -> List[str]:
    table = self._get_table(self.ai_editor_base_id, self.prefilter_log_table_id)
    # Use batch_upsert with storyID as the matching key
    upserted = table.batch_upsert(
        records,
        key_fields=['storyID'],
        replace=True
    )
    return [r['id'] for r in upserted]
```

---

### 2. Newsletter Filter Expansion (HIGH)

**The Problem:** Full-stack app only pulls stories tagged for `pivot_ai` newsletter, missing stories from `pivot_build` and `pivot_invest`.

**n8n Implementation (line 1137):**
```
OR({newsletter} = 'pivot_ai', {newsletter} = 'pivot_build', {newsletter} = 'pivot_invest')
```

**Full-Stack Implementation:**
```python
# workers/utils/airtable.py line 65
filter_formula = f"AND(IS_AFTER({{date_og_published}}, DATEADD(TODAY(), -{days}, 'days')), {{ai_headline}}!='', {{newsletter}}='pivot_ai')"
```

**Required Fix:**
```python
filter_formula = f"AND(IS_AFTER({{date_og_published}}, DATEADD(TODAY(), -{days}, 'days')), {{ai_headline}}!='', OR({{newsletter}}='pivot_ai', {{newsletter}}='pivot_build', {{newsletter}}='pivot_invest'))"
```

---

### 3. Slot 1 Company Filter (MEDIUM)

**The Problem:** Full-stack has 8 Tier 1 companies, n8n only has 4. The expanded list may cause more stories to pass the company filter than intended.

**n8n Implementation (line 1262):**
```javascript
const slot1Companies = ['openai', 'google', 'meta', 'nvidia'];
```

**Full-Stack Implementation:**
```python
# workers/jobs/prefilter.py line 23
SLOT_1_COMPANIES = ['openai', 'google', 'meta', 'nvidia', 'microsoft', 'anthropic', 'xai', 'amazon']
```

**Required Fix:**
```python
SLOT_1_COMPANIES = ['openai', 'google', 'meta', 'nvidia']
```

---

### 4. Yesterday Issue Lookback (MEDIUM)

**The Problem:** When checking for recently used stories, n8n looks back 14 days while full-stack only gets the single most recent sent issue.

**n8n Implementation (line 1190):**
```
{status} = 'sent',
IS_AFTER({issue_date}, DATEADD(TODAY(), -14, 'days'))
```
Returns ALL issues from the last 14 days for comprehensive duplicate checking.

**Full-Stack Implementation:**
```python
# workers/utils/airtable.py lines 207-216
def get_yesterday_issue(self) -> Optional[dict]:
    records = table.all(
        formula="{status}='sent'",
        sort=['-issue_date'],
        max_records=1  # <-- Only gets 1 record
    )
    return records[0] if records else None
```

**Required Fix:**
```python
def get_recent_sent_issues(self, lookback_days: int = 14) -> List[dict]:
    """Get all sent issues from the last N days for duplicate checking"""
    table = self._get_table(self.ai_editor_base_id, self.selected_slots_table_id)

    filter_formula = f"AND({{status}}='sent', IS_AFTER({{issue_date}}, DATEADD(TODAY(), -{lookback_days}, 'days')))"

    records = table.all(
        formula=filter_formula,
        sort=['-issue_date']
    )

    return records
```

---

### 5. Queued Stories Filter (LOW)

**The Problem:** n8n checks for expiration date on queued stories, full-stack doesn't.

**n8n Implementation (line 1540):**
```
AND({status} = 'pending', IS_AFTER({expires_date}, TODAY()))
```

**Full-Stack Implementation:**
```python
# workers/utils/airtable.py lines 187-200
filter_formula = "{status}='pending'"  # No expiration check
```

**Required Fix:**
```python
filter_formula = "AND({status}='pending', IS_AFTER({expires_date}, TODAY()))"
```

**Note:** This depends on the `expires_date` field existing in the AI Editor Queue table. Based on CLAUDE.md, the table only has `original slot` and `status` fields. Verify field existence before implementing.

---

### 6. Pull Articles Source (LOW)

**n8n has a separate "Pull Articles Source" node (lines 1466-1502)** that fetches article details from the Articles table with a 7-day freshness filter. The full-stack implementation uses `get_articles_batch()` which is called differently.

**n8n Implementation:**
- Pulls from Articles table with specific fields: `pivot_Id`, `source_id`, `core_url`
- Filter: Last 7 days of articles
- Used to build source lookup

**Full-Stack Implementation:**
```python
# workers/utils/airtable.py lines 105-126
def get_articles_batch(self, pivot_ids: List[str]) -> Dict[str, dict]:
    # Lookup by specific pivotIds, no date filter
```

**Assessment:** The full-stack implementation handles this via the `get_articles_batch` method which is called with specific pivotIds. The approach differs but achieves the same result. **No change required** unless testing reveals missing source data.

---

## Implementation Plan

### Phase 1: Critical Fix (UPSERT)
**Priority:** CRITICAL
**Files:** `workers/utils/airtable.py`

1. Import pyairtable's batch_upsert capability (verify pyairtable version supports it)
2. Update `write_prefilter_log_batch` to use `batch_upsert` with `storyID` key
3. Test that duplicate stories are updated instead of created

### Phase 2: Newsletter Filter
**Priority:** HIGH
**Files:** `workers/utils/airtable.py`

1. Update `get_fresh_stories` filter formula to include all 3 newsletters
2. Test that stories from pivot_build and pivot_invest are now included

### Phase 3: Configuration Alignment
**Priority:** MEDIUM
**Files:** `workers/jobs/prefilter.py`, `workers/utils/airtable.py`

1. Reduce `SLOT_1_COMPANIES` to 4 companies
2. Create `get_recent_sent_issues` method with 14-day lookback
3. Update prefilter.py to use new method for duplicate checking

### Phase 4: Optional Enhancements
**Priority:** LOW

1. Add expires_date check to queued stories filter (verify field exists first)
2. Review Pull Articles Source alignment if issues arise

---

## Testing Checklist

After implementing changes:

- [ ] Run pre-filter job
- [ ] Verify Pre-Filter Log has no duplicate storyIDs
- [ ] Verify stories from pivot_build and pivot_invest are included
- [ ] Verify Slot 1 Company Filter only matches 4 companies
- [ ] Verify duplicate checking uses 14-day lookback
- [ ] Compare output counts with n8n execution

---

## Files to Modify

| File | Changes |
|------|---------|
| `workers/utils/airtable.py` | UPSERT, newsletter filter, yesterday issue lookback, queued stories filter |
| `workers/jobs/prefilter.py` | Company filter list (8 → 4 companies) |

---

## pyairtable UPSERT Reference

The pyairtable library supports `batch_upsert` starting from version 2.0+:

```python
from pyairtable import Table

table.batch_upsert(
    records=[{"fields": {...}}],
    key_fields=["storyID"],  # Field(s) to match on
    replace=True             # Replace all fields (True) or merge (False)
)
```

Verify current pyairtable version in `requirements.txt` supports this.
