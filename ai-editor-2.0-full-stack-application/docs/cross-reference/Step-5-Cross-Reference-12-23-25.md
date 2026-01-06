# Step 5: Social Post Trigger Cross-Reference Analysis

**Document:** Step-5-Cross-Reference-12-23-25.md
**Date:** December 23, 2025
**Infrastructure Doc:** AI-Editor-2.0-Infrastructure-Step-5-12-23-25.md
**Implementation Files:**
- `/app/src/lib/airtable.ts`
- `/app/src/app/(dashboard)/jobs/page.tsx`

---

## Summary

| Category | Status |
|----------|--------|
| Dashboard READ Operations | ⚠️ Partial (social_status field only) |
| Decoration Table Filter | ❌ Not Implemented (no image_status + social_status filter) |
| P5 Social Posts Table | ❌ Not Implemented (different base) |
| Deduplication Logic | ❌ Not Implemented |
| Airtable WRITE Operations | ❌ Not Implemented |
| Python Worker Job | ❌ Not Implemented |

---

## Overview

Step 5 is a **data synchronization workflow** (no AI models) that syndicates decorated newsletter stories to the P5 Social Posts table for downstream social media workflows. It includes deduplication logic to prevent duplicate posts.

---

## Node-by-Node Cross-Reference

### Node 1: Schedule Trigger
**Infrastructure:** Two cron expressions:
- `30 4 * * 1-5` (4:30 AM EST, Mon-Fri)
- `0 5 * * 1-5` (5:00 AM EST, Mon-Fri)

**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker with Redis Queue (RQ) scheduled job
- Cron expressions: `30 9 * * 1-5` and `0 10 * * 1-5` UTC
- File: `workers/jobs/social_sync.py`

---

### Node 2: GET Decorated Stories Ready for Social
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories)
- Filter: `AND({image_status}='generated', OR({social_status}='', {social_status}='pending'))`
- Max Records: 10

**Implementation:** ⚠️ Partial in `getDecorations()` (lines 496-547)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Base ID | `appglKSJZxmA9iHpl` | `process.env.AI_EDITOR_BASE_ID` | ✅ |
| Table ID | `tbla16LJCf5Z6cRn3` | `process.env.AI_EDITOR_DECORATION_TABLE` | ✅ |
| Filter | `image_status='generated' AND social_status empty/pending` | `{image_status}='generated'` only | ❌ |
| Fields | Includes `social_status` | Includes `social_status` | ✅ |
| Max Records | 10 | 5 | ⚠️ |

**Gap:** Implementation filters only on `image_status`, not the combined filter with `social_status`.

**Action Required for Python Worker:**
```python
def get_stories_ready_for_social() -> List[dict]:
    """Get decorated stories ready for social syndication"""
    filter_formula = "AND({image_status}='generated', OR({social_status}='', {social_status}='pending'))"

    records = airtable.table(
        os.environ['AI_EDITOR_BASE_ID'],
        os.environ['AI_EDITOR_DECORATION_TABLE']
    ).all(
        formula=filter_formula,
        max_records=10
    )
    return records
```

---

### Node 3: Extract Records
**Infrastructure:** JavaScript code that:
1. Extracts individual records from Airtable response
2. Cleans HTML from `raw` field (strips tags, decodes entities)

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
import re
import html

def clean_raw_content(raw: str) -> str:
    """Clean HTML from raw content"""
    if not raw:
        return ""

    # Remove HTML tags
    raw = re.sub(r'<[^>]*>', '', raw)

    # Decode HTML entities
    raw = html.unescape(raw)

    # Normalize whitespace
    raw = re.sub(r'\s+', ' ', raw)

    return raw.strip()
```

---

### Node 4: Split In Batches
**Infrastructure:** Process stories one at a time for deduplication
**Implementation Status:** ❌ Not Implemented

**Action Required:** Python worker processes stories sequentially.

---

### Node 5: Find Existing in P5 Social Posts
**Infrastructure:**
- **Different Base:** `appRUgK44hQnXH1PM` (P5 Social Posts)
- Table: `tbllJMN2QBPJoG3jA` (P5 Social Posts)
- Filter: `AND({source_record_id}="<record_id>",{source_record_id}!="")`

**Implementation Status:** ❌ Not Implemented

**Gap:** This is a DIFFERENT Airtable base than the AI Editor base. No reference to this base exists in the implementation.

**Action Required:**
```python
def find_existing_social_post(source_record_id: str) -> Optional[dict]:
    """Check if social post already exists for this source record"""
    filter_formula = f'AND({{source_record_id}}="{source_record_id}",{{source_record_id}}!="")'

    records = airtable.table(
        os.environ['P5_SOCIAL_POSTS_BASE_ID'],
        os.environ['P5_SOCIAL_POSTS_TABLE']
    ).all(
        formula=filter_formula,
        max_records=1
    )

    return records[0] if records else None
```

**New Environment Variables Required:**
```bash
P5_SOCIAL_POSTS_BASE_ID=appRUgK44hQnXH1PM
P5_SOCIAL_POSTS_TABLE=tbllJMN2QBPJoG3jA
```

---

### Node 6: Check If Exists
**Infrastructure:** Add `action: 'skip'` or `action: 'create'` based on existence
**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def determine_action(source_record_id: str) -> str:
    """Determine if we should create or skip this record"""
    existing = find_existing_social_post(source_record_id)
    return "skip" if existing else "create"
```

---

### Node 7: Does Newsletter Post Already Exist?
**Infrastructure:** IF node - routes to create or skip
**Implementation Status:** ❌ Not Implemented

**Handled in Python worker orchestration.**

---

### Node 8: Create a record
**Infrastructure:**
- **Base:** `appRUgK44hQnXH1PM` (P5 Social Posts)
- **Table:** `tbllJMN2QBPJoG3jA` (P5 Social Posts)
- Operation: Create record
- 11 fields mapped

**Implementation Status:** ❌ Not Implemented

**Column Mapping:**
| P5 Social Posts Field | Source Field | Type |
|-----------------------|--------------|------|
| source_record_id | Record ID from Decoration table | Text |
| label | `fields.label` | Text |
| headline | `fields.headline` | Text |
| image_raw_url | `fields.image_url` | Text |
| Raw | `fields.raw` (cleaned) | Long Text |
| publish_status | `"ready"` (hardcoded) | Select |
| Order | `fields.slot_order` | Number |
| Name | `fields.headline` | Text |
| b1 | `fields.b1` | Text |
| b2 | `fields.b2` | Text |
| b3 | `fields.b3` | Text |

**Action Required:**
```python
def create_social_post(decoration_record: dict) -> str:
    """Create new record in P5 Social Posts table"""
    fields = decoration_record['fields']

    social_post = {
        "source_record_id": decoration_record['id'],
        "Name": fields.get('headline', ''),
        "label": fields.get('label', ''),
        "headline": fields.get('headline', ''),
        "image_raw_url": fields.get('image_url', ''),
        "Raw": clean_raw_content(fields.get('raw', '')),
        "publish_status": "ready",
        "Order": fields.get('slot_order', 0),
        "b1": fields.get('b1', ''),
        "b2": fields.get('b2', ''),
        "b3": fields.get('b3', '')
    }

    record = airtable.table(
        os.environ['P5_SOCIAL_POSTS_BASE_ID'],
        os.environ['P5_SOCIAL_POSTS_TABLE']
    ).create(social_post)

    return record['id']
```

---

### Node 9: Mark Social Synced
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories)
- Method: PATCH
- Update: `{social_status: 'synced'}`

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def mark_social_synced(decoration_record_id: str) -> dict:
    """Update decoration record to mark as synced to social"""

    record = airtable.table(
        os.environ['AI_EDITOR_BASE_ID'],
        os.environ['AI_EDITOR_DECORATION_TABLE']
    ).update(decoration_record_id, {"social_status": "synced"})

    return record
```

---

## Environment Variables Required

### Currently Configured
```bash
AIRTABLE_API_KEY=✅ Configured
AI_EDITOR_BASE_ID=✅ Configured (appglKSJZxmA9iHpl)
AI_EDITOR_DECORATION_TABLE=✅ Configured (tbla16LJCf5Z6cRn3)
```

### Missing
```bash
P5_SOCIAL_POSTS_BASE_ID=❌ Required (appRUgK44hQnXH1PM)
P5_SOCIAL_POSTS_TABLE=❌ Required (tbllJMN2QBPJoG3jA)
```

---

## Python Worker Specification

**File:** `workers/jobs/social_sync.py`
**Queue:** Redis Queue (RQ)
**Schedule:**
- `30 9 * * 1-5` UTC (4:30 AM EST)
- `0 10 * * 1-5` UTC (5:00 AM EST)

### Required Functions

```python
import os
import re
import html
from typing import List, Optional
from pyairtable import Api

# Initialize Airtable
airtable = Api(os.environ['AIRTABLE_API_KEY'])


def clean_raw_content(raw: str) -> str:
    """Clean HTML from raw content for social posts"""
    if not raw:
        return ""

    # Remove HTML tags
    raw = re.sub(r'<[^>]*>', '', raw)

    # Decode HTML entities
    raw = html.unescape(raw)

    # Normalize whitespace
    raw = re.sub(r'\s+', ' ', raw)

    return raw.strip()


def get_stories_ready_for_social() -> List[dict]:
    """Get decorated stories ready for social syndication"""
    filter_formula = "AND({image_status}='generated', OR({social_status}='', {social_status}='pending'))"

    table = airtable.table(
        os.environ['AI_EDITOR_BASE_ID'],
        os.environ['AI_EDITOR_DECORATION_TABLE']
    )

    return table.all(formula=filter_formula, max_records=10)


def find_existing_social_post(source_record_id: str) -> Optional[dict]:
    """Check if social post already exists for this source record"""
    filter_formula = f'AND({{source_record_id}}="{source_record_id}",{{source_record_id}}!="")'

    table = airtable.table(
        os.environ['P5_SOCIAL_POSTS_BASE_ID'],
        os.environ['P5_SOCIAL_POSTS_TABLE']
    )

    records = table.all(formula=filter_formula, max_records=1)
    return records[0] if records else None


def create_social_post(decoration_record: dict) -> str:
    """Create new record in P5 Social Posts table"""
    fields = decoration_record['fields']

    social_post = {
        "source_record_id": decoration_record['id'],
        "Name": fields.get('headline', ''),
        "label": fields.get('label', ''),
        "headline": fields.get('headline', ''),
        "image_raw_url": fields.get('image_url', ''),
        "Raw": clean_raw_content(fields.get('raw', '')),
        "publish_status": "ready",
        "Order": fields.get('slot_order', 0),
        "b1": fields.get('b1', ''),
        "b2": fields.get('b2', ''),
        "b3": fields.get('b3', '')
    }

    table = airtable.table(
        os.environ['P5_SOCIAL_POSTS_BASE_ID'],
        os.environ['P5_SOCIAL_POSTS_TABLE']
    )

    record = table.create(social_post)
    return record['id']


def mark_social_synced(decoration_record_id: str) -> dict:
    """Update decoration record to mark as synced to social"""
    table = airtable.table(
        os.environ['AI_EDITOR_BASE_ID'],
        os.environ['AI_EDITOR_DECORATION_TABLE']
    )

    return table.update(decoration_record_id, {"social_status": "synced"})


def sync_social_posts() -> dict:
    """Step 5: Social Post Sync Job - Main entry point"""

    # 1. Get decorated stories ready for social
    stories = get_stories_ready_for_social()

    created = []
    skipped = []

    # 2. Process each story sequentially (for deduplication)
    for story in stories:
        record_id = story['id']

        # 3. Check if already exists in P5 Social Posts
        existing = find_existing_social_post(record_id)

        if existing:
            skipped.append(record_id)
            continue

        # 4. Create new social post
        try:
            social_post_id = create_social_post(story)
            created.append(social_post_id)

            # 5. Mark source as synced
            mark_social_synced(record_id)

        except Exception as e:
            print(f"Error creating social post for {record_id}: {e}")
            continue

    return {
        "processed": len(stories),
        "created": len(created),
        "skipped": len(skipped),
        "created_ids": created,
        "skipped_ids": skipped
    }
```

---

## Deduplication Logic Summary

The workflow prevents duplicate social posts by:

1. **Query Filter:** Only fetches records where `social_status` is empty or "pending"
2. **Existence Check:** For each record, queries P5 Social Posts by `source_record_id`
3. **Skip Logic:** If existing record found, skips to next item
4. **Sync Flag:** After creating, updates source record with `social_status='synced'`

```
Filter Formula for Eligible Stories:
AND({image_status}='generated', OR({social_status}='', {social_status}='pending'))
```

---

## P5 Social Posts Table Schema

**Base:** P5 Social Posts (`appRUgK44hQnXH1PM`)
**Table:** P5 Social Posts (`tbllJMN2QBPJoG3jA`)

| Field | Type | Description |
|-------|------|-------------|
| source_record_id | Text | Links back to Decoration table record ID |
| Name | Text | Same as headline |
| headline | Text | Story headline |
| label | Text | Topic label (e.g., "JOBS & ECONOMY") |
| b1 | Text | Bullet point 1 |
| b2 | Text | Bullet point 2 |
| b3 | Text | Bullet point 3 |
| Raw | Long Text | Cleaned article content (HTML stripped) |
| image_raw_url | Text | Image URL from Cloudflare CDN |
| publish_status | Select | "ready", "processing", "published" |
| Order | Number | Slot order (1-5) |

---

## Critical Issues Found

### Issue 1: Missing P5 Social Posts Base
**Problem:** The P5 Social Posts table is in a DIFFERENT Airtable base (`appRUgK44hQnXH1PM`) than the AI Editor base
**Impact:** Cannot sync to social without access to this base
**Resolution:** Add environment variables for P5 Social Posts base

### Issue 2: Dashboard social_status Field Only
**Location:** `lib/airtable.ts` lines 492, 521, 544
**Problem:** Dashboard reads `social_status` but cannot update it
**Impact:** Dashboard is read-only for social sync status
**Resolution:** Python worker handles PATCH operation

### Issue 3: Jobs Page Reference
**Location:** `jobs/page.tsx` line 108
**Problem:** Jobs page references `sync_social_posts` job but no job exists
**Resolution:** Python worker implements this job

---

## Dashboard Updates Required

### 1. Add Social Sync Status Display
The dashboard already shows `socialPostStatus` on the home page. Add a dedicated view for social posts.

### 2. Add Manual Sync Trigger
Add API route `/api/social/sync` that enqueues the `sync_social_posts` job.

---

## Implementation Priority

1. **High Priority (Worker Core):**
   - [ ] Create `workers/jobs/social_sync.py`
   - [ ] Add P5 Social Posts environment variables
   - [ ] Implement deduplication logic
   - [ ] Implement PATCH for social_status

2. **Medium Priority (Dashboard Updates):**
   - [ ] Add social sync status view
   - [ ] Add API route for manual sync trigger
   - [ ] Display sync counts (created/skipped)

3. **Low Priority (Enhancements):**
   - [ ] View P5 Social Posts table in dashboard
   - [ ] Manual approve/reject before sync

---

## Downstream Workflows

The P5 Social Posts table feeds into downstream social media automation workflows (NOT part of AI Editor 2.0):

- **LinkedIn posting**
- **X/Twitter posting**
- **Facebook posting**

These workflows monitor the `publish_status` field and process records with status "ready".

---

*Cross-reference generated: December 23, 2025*
