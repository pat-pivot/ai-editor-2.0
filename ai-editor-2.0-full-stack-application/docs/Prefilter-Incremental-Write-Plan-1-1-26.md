# Prefilter Incremental Write Plan

**Date:** January 1, 2026
**Status:** ✅ IMPLEMENTED
**Priority:** HIGH - Data loss occurred on 1/1/26 due to job timeout

---

## Problem

The prefilter job accumulates all records in memory across 5 slots, then writes to Airtable in a single batch at the end (Phase 5). If the job crashes or times out before Phase 5, **all work is lost**.

### Incident: January 1, 2026 at 4:10 PM ET

Job started at 21:10:45 UTC and processed through Slot 4 before hitting RQ's 30-minute timeout:

```
21:10:49 - Slot 1 started
21:14:15 - Slot 2 started
21:23:01 - Slot 3 started
21:33:01 - Slot 4 started
21:40:45 - ERROR: Task exceeded maximum timeout value (1800 seconds)
21:41:45 - Job killed, moved to FailedJobRegistry
```

**Result:** ~30 minutes of Gemini API calls, zero records written to Airtable.

---

## Solution: Option A - Write to Airtable After Each Slot

Move the Airtable write inside the slot processing loop so each slot's results are persisted immediately.

### Current Flow (Risky)

```python
prefilter_records = []

for slot in range(1, 6):
    results = process_slot(slot)
    prefilter_records.extend(results)  # Accumulate in memory

# Phase 5: Single batch write at end
airtable.write_prefilter_log_batch(prefilter_records)  # ALL OR NOTHING
```

### New Flow (Safe)

```python
for slot in range(1, 6):
    slot_records = process_slot(slot)

    # Write immediately after each slot completes
    if slot_records:
        airtable.write_prefilter_log_batch(slot_records)
        print(f"[Step 1] Wrote {len(slot_records)} records for slot {slot}")
```

---

## Implementation Steps

### Step 1: Modify `workers/jobs/prefilter.py`

**Location:** Lines 270-316 (Phase 4-5)

**Changes:**
1. Remove the `prefilter_records = []` accumulator outside the loop
2. Move `write_prefilter_log_batch()` call inside the slot loop
3. Write each slot's records immediately after processing
4. Update logging to show per-slot writes

### Step 2: Update Job Timeout (Optional)

Current RQ timeout is 1800 seconds (30 min). Consider:
- Increasing to 3600 seconds (1 hour) for safety margin
- Or accept that long jobs may timeout but data is preserved

**Location:** `workers/worker.py` or job decorator

### Step 3: Test

1. Trigger prefilter job manually
2. Verify Airtable records appear after each slot (not just at end)
3. Optionally kill job mid-way to confirm partial data is saved

---

## Code Diff Preview

```python
# BEFORE (lines ~270-316 in prefilter.py)
prefilter_records = []

for slot_num in range(1, 6):
    # ... process slot ...
    for record in slot_results:
        prefilter_records.append(record)

# Phase 5: Write all at once
if prefilter_records:
    record_ids = airtable.write_prefilter_log_batch(prefilter_records)

# AFTER
for slot_num in range(1, 6):
    slot_records = []

    # ... process slot ...
    for record in slot_results:
        slot_records.append(record)

    # Write immediately after each slot
    if slot_records:
        try:
            record_ids = airtable.write_prefilter_log_batch(slot_records)
            print(f"[Step 1] Slot {slot_num}: Wrote {len(record_ids)} records to Airtable")
            results["written"] += len(record_ids)
        except Exception as e:
            print(f"[Step 1] Slot {slot_num}: ERROR writing to Airtable: {e}")
            results["errors"].append({"slot": slot_num, "write_error": str(e)})
```

---

## Benefits

| Before | After |
|--------|-------|
| Job timeout = 0 records | Job timeout = partial records saved |
| 30+ min work lost on crash | Only current slot's work lost |
| No visibility during run | Can see records appear in real-time |
| Single large API batch | 5 smaller API batches |

---

## Future Enhancement: Option B (PostgreSQL Staging)

If we need full crash recovery with resume capability:

1. Create `prefilter_staging` table in PostgreSQL
2. Write each slot's results to Postgres first
3. Track job progress (which slots completed)
4. Final step: sync Postgres → Airtable
5. On restart: resume from last completed slot

This is more complex (~150 lines) but provides:
- Resume capability after crash
- Transaction safety
- Audit trail of all runs

**Recommendation:** Implement Option A now, add Option B if we see frequent mid-slot crashes.

---

## Files to Modify

| File | Change |
|------|--------|
| `workers/jobs/prefilter.py` | Move Airtable write inside slot loop |
| `workers/worker.py` | (Optional) Increase job timeout |

---

## Estimated Effort

- Option A: **15-20 minutes**
- Testing: **10 minutes**
- Total: **~30 minutes**

---

## ✅ Implementation Completed (1/1/26)

### Changes Made

#### 1. Extended Job Timeout (worker.py)
```python
# Before: Default 180s timeout (RQ default)
Queue('default', connection=conn)

# After: 2 hour timeout for long-running jobs
Queue('default', connection=conn, default_timeout=7200)
```

#### 2. Incremental Writes (prefilter.py)
- Moved Airtable write inside the slot processing loop
- Each slot's matches are written immediately after Gemini returns
- Deduplication via `written_story_slot_pairs` set prevents double-writes
- Detailed logging shows progress after each slot: `Slot X: Wrote Y records to Airtable ✓`

#### 3. Per-Slot Error Handling (prefilter.py)
- Each slot is wrapped in try/except
- If one slot fails, job continues to remaining slots
- Errors logged but don't crash the entire job
- Example: If Slot 4 times out, Slots 1-3 data is already saved

### New Log Output Example
```
[Step 1] Running Slot 1 batch pre-filter...
[Step 1] Slot 1 Gemini: 15 matches
[Step 1] Slot 1 (Gemini): Wrote 15 records to Airtable ✓
[Step 1] Slot 1 Company Filter: 3 matches
[Step 1] Slot 1 (CompanyFilter): Wrote 2 records to Airtable ✓
[Step 1] Running Slot 2 batch pre-filter...
[Step 1] Slot 2: 22 matches
[Step 1] Slot 2 (Gemini): Wrote 22 records to Airtable ✓
...
```

### Files Modified
| File | Change |
|------|--------|
| `workers/worker.py` | Set `default_timeout=7200` on all queues |
| `workers/jobs/prefilter.py` | Incremental writes + per-slot error handling |
| `docs/Prefilter-Incremental-Write-Plan-1-1-26.md` | This documentation |

### Deployment Required
These changes require redeploying the worker service on Render for them to take effect.
