# Codebase Structure Audit

**Date:** January 6, 2026
**Status:** CRITICAL - Action Required
**Author:** Claude Code Audit

---

## Executive Summary

The AI Editor 2.0 codebase has code in **TWO locations** that are **OUT OF SYNC**. This creates a risk where:
- Manual dashboard triggers use CURRENT code ✅
- Automated cron jobs use OUTDATED code ⚠️

---

## Repository Structure

```
/Users/patsimmons/client-coding/pivot-5-website_11.19.25/
│
├── .git/                        # ROOT repo: github.com/per-simmons/pivot-5-website.git
│
├── workers/                     # ⚠️ COPY of worker code - OUTDATED
│   ├── jobs/
│   │   ├── pipeline.py          # 169 lines - MISSING Direct Feed Ingest
│   │   ├── ingest_sandbox.py
│   │   ├── ai_scoring_sandbox.py
│   │   ├── prefilter.py
│   │   └── ...
│   ├── config/
│   ├── utils/
│   ├── render.yaml              # Render Blueprint (identical to ai-editor copy)
│   └── trigger.py
│
└── ai-editor-2.0-full-stack-application/
    │
    ├── workers/                 # EMPTY stub folder (just utils/)
    │
    └── app/                     # SEPARATE GIT REPO: github.com/pat-pivot/ai-editor-2.0.git
        ├── .git/                # Its own git history
        │
        ├── workers/             # ✅ ORIGINAL/CURRENT worker code
        │   ├── jobs/
        │   │   ├── pipeline.py  # 198 lines - INCLUDES Direct Feed Ingest
        │   │   ├── ingest_sandbox.py
        │   │   ├── ai_scoring_sandbox.py
        │   │   ├── prefilter.py
        │   │   ├── ingest_direct_feeds.py
        │   │   └── ...
        │   ├── config/
        │   ├── utils/
        │   ├── render.yaml      # Render Blueprint (identical to root copy)
        │   └── trigger.py
        │
        └── src/                 # Next.js dashboard (CURRENT)
            └── app/
```

---

## Git Remotes

### ROOT Level (`/pivot-5-website_11.19.25/`)
```
origin    https://github.com/per-simmons/pivot-5-website.git
ai-editor https://github.com/pat-pivot/ai-editor-2.0.git
```

### ai-editor/app/ Level (`/ai-editor-2.0-full-stack-application/app/`)
```
origin    https://github.com/pat-pivot/ai-editor-2.0.git
```

**Note:** ai-editor/app/ is NOT a git submodule - it's a nested repository (separate .git folder).

---

## Render Configuration Analysis

From `render.yaml`, Render is connected to the **ROOT** repository (`pivot-5-website`).

### Service rootDir Paths

| Service Type | rootDir in render.yaml | Resolves To |
|--------------|------------------------|-------------|
| Dashboard (web) | `ai-editor-2.0-full-stack-application/app` | ✅ ai-editor/app/ |
| Trigger Service | `ai-editor-2.0-full-stack-application/app/workers` | ✅ ai-editor/app/workers/ |
| **Cron Jobs** | `workers` | ⚠️ **ROOT/workers/** |

### The Critical Problem

```yaml
# From render.yaml - Cron jobs use ROOT's workers/
- type: cron
  name: ai-editor-pipeline-night
  rootDir: workers                    # <-- Points to ROOT/workers/
  startCommand: python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"
```

This means cron jobs run the **169-line pipeline.py** at ROOT/workers/, which is **MISSING**:
- Direct Feed Ingest step
- Potentially other recent changes

---

## Code Divergence: pipeline.py

### ROOT/workers/jobs/pipeline.py (169 lines) - OUTDATED
```python
# Missing Direct Feed Ingest
print(f"[Pipeline] Chain: Ingest → AI Scoring → Pre-Filter (5 slots)")
```

### ai-editor/app/workers/jobs/pipeline.py (198 lines) - CURRENT
```python
# Includes Direct Feed Ingest
print(f"[Pipeline] Chain: Ingest → Direct Feeds → AI Scoring → Pre-Filter (5 slots)")
```

---

## Which Code Is "Real"?

| Question | Answer |
|----------|--------|
| Which code is production? | **Both** - different services use different paths |
| Which has latest changes? | `ai-editor-2.0-full-stack-application/app/workers/` |
| Which do cron jobs use? | `workers/` (ROOT) - **outdated** |
| Which does dashboard use? | `ai-editor-2.0-full-stack-application/app/workers/` |
| What's safe to delete? | **Nothing yet** - cron jobs depend on ROOT/workers/ |

---

## Recommended Fix

### Option A: Update render.yaml (Safest)

Change cron job rootDir to use ai-editor path:

```yaml
# BEFORE (uses outdated ROOT/workers/)
- type: cron
  name: ai-editor-pipeline-night
  rootDir: workers

# AFTER (uses current ai-editor/app/workers/)
- type: cron
  name: ai-editor-pipeline-night
  rootDir: ai-editor-2.0-full-stack-application/app/workers
```

**After deploying this change**, the ROOT/workers/ folder can be deleted.

### Option B: Sync ROOT/workers/ with ai-editor/app/workers/

Copy all files from ai-editor/app/workers/ to ROOT/workers/ so they match.

**Downside:** Maintains two copies of the same code (technical debt).

---

## Verification Steps Before Any Changes

1. **Check current cron execution:**
   - Go to Render Dashboard → Cron Jobs
   - Look at recent runs for pipeline-night, pipeline-morning, pipeline-eod
   - Verify if Direct Feed Ingest is running (it shouldn't be if using ROOT/workers/)

2. **Check Airtable:**
   - Look for records with `gnews_url` field empty (direct feed articles)
   - If no recent direct feed articles, crons are indeed using outdated code

3. **Test in staging before production changes**

---

## Files in ROOT/workers/ That May Be Safe to Delete

**Only after fixing render.yaml to use ai-editor path:**

- `workers/jobs/` - All job files
- `workers/config/` - All config files
- `workers/utils/` - All utility files
- `workers/trigger.py`
- `workers/requirements.txt`
- `workers/render.yaml` - Keep ONE copy (probably in ai-editor/app/workers/)

---

## Summary

| Item | Location | Status |
|------|----------|--------|
| Dashboard (Next.js) | ai-editor/app/src/ | ✅ Current |
| Worker code (manual triggers) | ai-editor/app/workers/ | ✅ Current |
| Worker code (cron jobs) | ROOT/workers/ | ⚠️ **OUTDATED** |
| render.yaml | Both (identical) | Need to update cron rootDir |

**Action Required:**
1. Update render.yaml cron job rootDir paths
2. Deploy changes
3. Verify cron jobs run correctly
4. Delete ROOT/workers/ folder

---

## Related Documentation

- `docs/ai-ingestion-engine-step-0/` - Ingestion pipeline docs
- `docs/Logging-Refactor-1-5-26.md` - Cron schedule documentation
- `.claude/skills/` - Claude Code skill files
