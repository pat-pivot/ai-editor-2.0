# AI Editor Scheduler Service - DELETED

**Date:** January 5, 2026
**Service ID:** `srv-d55i64juibrs7392tcmg`
**Service Name:** `ai-editor-scheduler`
**Action:** DELETE from Render

---

## Why This Service Was Deleted

### 1. Broken Due to Version Incompatibility

The service was failing on every restart with this error:

```
ImportError: cannot import name 'resolve_connection' from 'rq.connections'
```

**Root Cause:**
- `rq==2.1.0` (current) removed the `resolve_connection` function
- `rq-scheduler==0.13.1` still tries to import it
- `rq-scheduler` is unmaintained and incompatible with rq 2.x

### 2. Redundant - Render Crons Handle All Scheduling

The `ai-editor-scheduler` service was the **old** scheduling mechanism that used Python's `rq-scheduler` library to schedule jobs via Redis.

**It has been replaced by Render native cron jobs:**

| Old (rq-scheduler) | New (Render Crons) |
|---|---|
| Python-based scheduling via Redis | Render's native cron infrastructure |
| Required a running background worker | Runs as standalone cron jobs |
| Single point of failure | Each cron is independent |
| Complex setup | Simple YAML configuration |

### 3. What rq-scheduler Was Doing

From `worker.py`, the scheduler was configured to run:

```python
# Step 1: Prefilter at 2:00 AM UTC Tue-Sat
# Step 2: Slot Selection at 2:15 AM UTC Tue-Sat
# Step 3: Decoration at 2:25 AM UTC Tue-Sat
# Step 3b: Images at 2:30 AM UTC Tue-Sat
# Step 4: HTML Compile at 3:00 AM UTC Tue-Sat
# Step 4b: Mautic Send at 10:00 AM UTC Tue-Sat
# Step 5: Social Sync at 9:30 AM UTC Tue-Sat
# Step 5b: Social Sync 2 at 10:00 AM UTC Tue-Sat
```

### 4. What Replaced It

Render native crons in `render.yaml` now handle everything:

**Pipeline Crons (Ingest → AI Scoring → Pre-Filter):**
- `ai-editor-pipeline-night` - 2:00 AM ET (7:00 UTC)
- `ai-editor-pipeline-morning` - 9:30 AM ET (14:30 UTC)
- `ai-editor-pipeline-eod` - 5:00 PM ET (22:00 UTC)

**Direct Feed Crons:**
- `ai-editor-direct-feeds-night` - 6:30 AM ET
- `ai-editor-direct-feeds-morning` - 2:00 PM ET
- `ai-editor-direct-feeds-eod` - 9:30 PM ET

These crons call `run_full_pipeline()` which chains:
1. Ingest (Google News decoding)
2. AI Scoring
3. Pre-Filter (all 5 slots sequential)

---

## Cleanup Actions

### 1. Delete Service from Render Dashboard

Go to: https://dashboard.render.com/worker/srv-d55i64juibrs7392tcmg

Click **Settings** → **Delete Service**

### 2. Remove rq-scheduler from requirements.txt (Optional)

Since nothing uses `rq-scheduler` anymore, it can be removed from `workers/requirements.txt`:

```diff
- rq-scheduler==0.13.1
```

However, leaving it doesn't cause issues since the scheduler service is deleted.

### 3. Clean Up worker.py (Optional)

The `run_scheduler()` function and `setup_scheduled_jobs()` in `worker.py` are now dead code. They can be removed in a future cleanup, but leaving them doesn't affect anything since:
- The `--with-scheduler` flag is only used by the deleted service
- The main worker runs with just `python worker.py` (no scheduler flag)

---

## Summary

| Before | After |
|---|---|
| `ai-editor-scheduler` service running 24/7 | Deleted |
| `rq-scheduler` Python library | Not used |
| Scheduling via Redis | Scheduling via Render crons |
| Broken (import error) | Working |
| Paying for background worker | No cost |

**The Render cron approach is simpler, more reliable, and doesn't require a constantly-running background service.**
