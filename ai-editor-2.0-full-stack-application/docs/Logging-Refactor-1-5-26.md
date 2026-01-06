# Dashboard Logging Refactor & Cron Schedule Update

**Date:** January 5, 2026
**Status:** ✅ IMPLEMENTED (with fixes applied 1/5/26 @ 5:05 PM ET)

---

## CRITICAL FIX APPLIED (1/5/26)

### Problem
Pipeline crons (night, morning, EOD) were failing immediately with:
```
cd: /opt/render/project/src/ai-editor-2.0-full-stack-application/app/workers: No such file or directory
❌ Your cronjob failed because of an error: Exited with status 1
```

### Root Cause
The `rootDir` in render.yaml was set incorrectly:
- **WRONG:** `rootDir: ai-editor-2.0-full-stack-application/app/workers`
- **CORRECT:** `rootDir: workers`

The Render deploy process already clones to `/opt/render/project/src/ai-editor-2.0-full-stack-application/app/`, so the rootDir should be **relative to that**, not include the full repo path.

### Fix Applied
Used Render API to update all 3 pipeline crons:
```bash
curl -X PATCH "https://api.render.com/v1/services/{cron_id}" \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rootDir": "workers"}'
```

All crons redeployed and now live.

---

## Overview

Comprehensive refactor of the AI Editor 2.0 dashboard including:
1. **New cron schedule** with chained pipeline execution (Ingest → AI Scoring → Pre-Filter)
2. **Sequential pre-filter execution** with per-slot Airtable writes (fail-safe)
3. **Render-style live logging** with time-based filtering (Live / Past Hour / Past 12h / Past 24h)
4. **AI Scoring added to cron** (was manual-only)
5. **Newsletter Extraction added to cron** (new feature)

---

## Part 1: New Cron Schedule (Chained Pipeline)

### Key Changes from Old Schedule

| What | OLD | NEW |
|------|-----|-----|
| AI Scoring | Manual only (dashboard) | **Added to cron** |
| Newsletter Extract | Not implemented | **Added to cron** (once daily) |
| Pre-Filter Slots | 5 separate crons, fixed 30min gaps | **Sequential chain**, no wasted time |
| Cycles per day | 3 (6AM, 2PM, 10PM) | **3 (2AM, 9:30AM, 5PM)** |
| 8 PM Deadline | Not considered | **Cycle 3 completes by ~8:30 PM** |

### New Schedule: 3 Chained Cycles

Each cycle runs a **single pipeline job** that chains: Ingest → AI Scoring → Pre-Filter (all 5 slots sequential)

| Cycle | Start (ET) | Start (UTC) | Purpose | Est. Complete |
|-------|------------|-------------|---------|---------------|
| 1 (Night) | 2:00 AM | 7:00 UTC | Overnight/international | ~5:30 AM |
| 2 (Morning) | 9:30 AM | 14:30 UTC | Morning pubs (WSJ, NYT, etc.) | ~1:00 PM |
| 3 (EOD) | 5:00 PM | 22:00 UTC | End-of-day stories | ~8:30 PM |

**Newsletter Extraction:** Runs once at **4:30 PM ET** (before Cycle 3 ingest picks up extracted links)

### Cron Configuration (render.yaml)

```yaml
# =============================================================================
# CHAINED PIPELINE CRONS - Run complete pipeline each cycle
# =============================================================================
- type: cron
  name: ai-editor-pipeline-cycle-1
  schedule: "0 7 * * *"  # 2:00 AM ET
  startCommand: python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"

- type: cron
  name: ai-editor-pipeline-cycle-2
  schedule: "30 14 * * *"  # 9:30 AM ET
  startCommand: python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"

- type: cron
  name: ai-editor-pipeline-cycle-3
  schedule: "0 22 * * *"  # 5:00 PM ET
  startCommand: python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"

# =============================================================================
# NEWSLETTER EXTRACTION - Once daily before EOD cycle
# =============================================================================
- type: cron
  name: ai-editor-newsletter-extract
  schedule: "30 21 * * *"  # 4:30 PM ET
  startCommand: python -c "from jobs.newsletter_extraction import run_newsletter_extraction; run_newsletter_extraction()"
```

### Timeline Visualization

```
CYCLE 1 (Night) - 2:00 AM ET
═══════════════════════════════════════════════════════
2:00 AM  ████████████████ Ingest (~1.5 hr)
3:30 AM        ██████████ AI Scoring (~45 min)
4:15 AM              ████████████████ Pre-Filter 1→2→3→4→5 (sequential)
5:30 AM                              ✓ Complete

CYCLE 2 (Morning) - 9:30 AM ET
═══════════════════════════════════════════════════════
9:30 AM  ████████████████ Ingest (~1.5 hr)
11:00 AM       ██████████ AI Scoring (~45 min)
11:45 AM             ████████████████ Pre-Filter 1→2→3→4→5 (sequential)
1:00 PM                              ✓ Complete

CYCLE 3 (EOD) - 5:00 PM ET → 8 PM DEADLINE
═══════════════════════════════════════════════════════
4:30 PM  ██ Newsletter Extract (~30 min)
5:00 PM  ████████████████ Ingest (~1.5 hr)
6:30 PM        ██████████ AI Scoring (~45 min)
7:15 PM              ████████████████ Pre-Filter 1→2→3→4→5 (sequential)
8:30 PM                              ✓ Complete
```

---

## Part 2: Sequential Pre-Filter with Per-Slot Writes

### Problem with Old Approach
- Pre-filter ran all 5 slots, but only wrote to Airtable at the END
- If slot 3 failed, slots 1 & 2 results were LOST
- No visibility into which slot was running

### New Approach: Write After Each Slot

**File:** `workers/jobs/pre_filter.py` (MODIFY)

```python
def run_all_prefilter_slots_sequential():
    """
    Run all 5 pre-filter slots sequentially.
    Writes to Airtable immediately after EACH slot completes.
    If slot 3 fails, slots 1 & 2 are already saved.
    """
    results = {
        "slots_completed": [],
        "slots_failed": [],
        "total_selected": 0,
        "total_rejected": 0
    }

    for slot in [1, 2, 3, 4, 5]:
        try:
            print(f"[Pre-Filter] ===== Starting Slot {slot} =====")

            # Run the slot
            slot_result = run_slot(slot)

            # Write to Airtable IMMEDIATELY after this slot
            write_slot_results_to_airtable(slot, slot_result)

            # Log to execution_logs table for dashboard
            log_slot_completion(slot, slot_result, status="success")

            results["slots_completed"].append(slot)
            results["total_selected"] += slot_result.get("selected", 0)
            results["total_rejected"] += slot_result.get("rejected", 0)

            print(f"[Pre-Filter] ===== Slot {slot} Complete: {slot_result['selected']} selected =====")

        except Exception as e:
            print(f"[Pre-Filter] !!!!! Slot {slot} FAILED: {e} !!!!!")
            log_slot_completion(slot, None, status="error", error=str(e))
            results["slots_failed"].append({"slot": slot, "error": str(e)})
            # Continue to next slot - don't abort entire pipeline

    return results
```

### Dashboard Visibility

Each slot completion will:
1. Write results to Airtable Selected Slots table immediately
2. Log to `execution_logs` table with slot-specific details
3. Appear in dashboard logs in real-time

---

## Part 3: Render API Live Logging (DIRECT CONNECTION)

### Key Finding: We CAN Connect Directly to Render!

Render provides a **public REST API** for fetching logs. Instead of building our own logging infrastructure, we can pull REAL Render logs directly.

**Render Logs API:** `GET https://api.render.com/v1/logs`

### Why This is Better

| Custom DB Approach | Render API Approach |
|-------------------|---------------------|
| Must modify all Python jobs to log | No Python changes needed |
| Logs are duplicated (Render + our DB) | Single source of truth |
| Additional DB schema/migrations | No new tables |
| Must maintain logging code | Render maintains it |
| Different from actual Render logs | EXACT same logs as Render dashboard |

### Render API Capabilities

| Feature | Support |
|---------|---------|
| Filter by service ID | ✅ Yes |
| Filter by time range | ✅ Yes (RFC3339 timestamps) |
| Filter by log level | ✅ Yes (debug, info, warning, error) |
| Filter by log type | ✅ Yes (app, build, request) |
| Text search | ✅ Yes (wildcards/regex) |
| Pagination | ✅ Yes (hasMore, nextStartTime) |
| Real-time streaming | ❌ No (must poll) |
| Rate limit | 30 requests/minute |

### Authentication

Add to dashboard `.env`:
```
RENDER_API_KEY=rnd_xxxxxxxxxx
```

Get API key from: [Render Dashboard > Account Settings > API Keys](https://dashboard.render.com/u/settings)

### Architecture

```
[Render Services] → [Render Logs API] → [Our Next.js API] → [SSE] → [Frontend]
                          ↑                    ↑
                     (polling 3s)        (streaming to browser)
```

### Service IDs for Filtering (ACTUAL VALUES)

| Service | Render ID |
|---------|-----------|
| ai-editor-pipeline-night | `crn-d5e2shv5r7bs73ca4dp0` |
| ai-editor-pipeline-morning | `crn-d5e2sl2li9vc73dt5q40` |
| ai-editor-pipeline-eod | `crn-d5e2smq4d50c73fjo0tg` |
| ai-editor-worker | `srv-d55i64juibrs7392tcn0` |
| ai-editor-trigger | `srv-d563ffvgi27c73dtqdq0` |
| ai-editor-scheduler | `srv-d55i64juibrs7392tcmg` |

**Dashboard env vars configured:**
```
RENDER_PIPELINE_NIGHT_ID=crn-d5e2shv5r7bs73ca4dp0
RENDER_PIPELINE_MORNING_ID=crn-d5e2sl2li9vc73dt5q40
RENDER_PIPELINE_EOD_ID=crn-d5e2smq4d50c73fjo0tg
RENDER_WORKER_SERVICE_ID=srv-d55i64juibrs7392tcn0
RENDER_TRIGGER_SERVICE_ID=srv-d563ffvgi27c73dtqdq0
RENDER_SCHEDULER_SERVICE_ID=srv-d55i64juibrs7392tcmg
RENDER_API_KEY=rnd_OxXhKEGyIjH13lKvfCySfhekdHX1
```

### API Endpoint: Fetch Render Logs

**File:** `src/app/api/logs/render/route.ts` (NEW)

```typescript
import { NextRequest, NextResponse } from 'next/server';

const RENDER_API_KEY = process.env.RENDER_API_KEY;
const RENDER_API_URL = 'https://api.render.com/v1/logs';

// Map step IDs to Render service IDs
const STEP_TO_SERVICES: Record<string, string[]> = {
  '0': ['srv-ingest-xxx', 'srv-scoring-xxx'],  // Step 0: Ingest + AI Scoring
  '1': ['srv-prefilter-xxx'],                   // Step 1: Pre-Filter
  'all': ['srv-pipeline-night', 'srv-pipeline-morning', 'srv-pipeline-eod']
};

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const stepId = searchParams.get('stepId') || 'all';
  const hours = parseInt(searchParams.get('hours') || '1');
  const level = searchParams.get('level');

  const serviceIds = STEP_TO_SERVICES[stepId] || STEP_TO_SERVICES['all'];
  const startTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

  try {
    // Fetch logs from Render API
    const params = new URLSearchParams();
    serviceIds.forEach(id => params.append('resource[]', id));
    params.append('startTime', startTime);
    params.append('limit', '100');
    params.append('direction', 'backward');
    if (level) params.append('level[]', level);

    const response = await fetch(`${RENDER_API_URL}?${params}`, {
      headers: {
        'Authorization': `Bearer ${RENDER_API_KEY}`,
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`Render API error: ${response.status}`);
    }

    const data = await response.json();

    // Transform to simpler format
    const logs = data.logs.map((log: any) => ({
      id: log.id,
      message: log.message,
      timestamp: log.timestamp,
      level: log.labels.find((l: any) => l.name === 'level')?.value || 'info',
      type: log.labels.find((l: any) => l.name === 'type')?.value || 'app',
      service: log.labels.find((l: any) => l.name === 'service')?.value
    }));

    return NextResponse.json({
      logs,
      hasMore: data.hasMore,
      nextEndTime: data.nextEndTime
    });
  } catch (error) {
    console.error('Failed to fetch Render logs:', error);
    return NextResponse.json({ error: 'Failed to fetch logs' }, { status: 500 });
  }
}
```

### API Endpoint: SSE Stream (Wraps Render API)

**File:** `src/app/api/logs/stream/route.ts` (NEW)

```typescript
import { NextRequest } from 'next/server';

const RENDER_API_KEY = process.env.RENDER_API_KEY;
const RENDER_API_URL = 'https://api.render.com/v1/logs';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const stepId = searchParams.get('stepId') || 'all';
  const filter = searchParams.get('filter') || 'live';

  const encoder = new TextEncoder();
  let lastTimestamp: string | null = null;

  const stream = new ReadableStream({
    async start(controller) {
      // Fetch initial logs based on filter
      const hours = filter === 'live' ? 0.1 : filter === '1h' ? 1 : filter === '12h' ? 12 : 24;
      const initialLogs = await fetchRenderLogs(stepId, hours);

      controller.enqueue(encoder.encode(`data: ${JSON.stringify(initialLogs)}\n\n`));

      if (initialLogs.length > 0) {
        lastTimestamp = initialLogs[initialLogs.length - 1].timestamp;
      }

      // For live view, poll every 3 seconds (safe within 30/min rate limit)
      if (filter === 'live') {
        const interval = setInterval(async () => {
          try {
            const newLogs = await fetchRenderLogs(stepId, 0.05, lastTimestamp); // Last 3 min
            if (newLogs.length > 0) {
              // Filter to only truly new logs
              const filtered = lastTimestamp
                ? newLogs.filter((l: any) => l.timestamp > lastTimestamp)
                : newLogs;

              if (filtered.length > 0) {
                controller.enqueue(encoder.encode(`data: ${JSON.stringify(filtered)}\n\n`));
                lastTimestamp = filtered[filtered.length - 1].timestamp;
              }
            }
          } catch (e) {
            console.error('Polling error:', e);
          }
        }, 3000);

        request.signal.addEventListener('abort', () => {
          clearInterval(interval);
          controller.close();
        });
      }
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}

async function fetchRenderLogs(stepId: string, hours: number, since?: string | null) {
  const serviceIds = getServiceIdsForStep(stepId);
  const startTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

  const params = new URLSearchParams();
  serviceIds.forEach(id => params.append('resource[]', id));
  params.append('startTime', startTime);
  params.append('limit', '50');
  params.append('direction', 'backward');

  const response = await fetch(`${RENDER_API_URL}?${params}`, {
    headers: {
      'Authorization': `Bearer ${RENDER_API_KEY}`,
      'Accept': 'application/json'
    }
  });

  if (!response.ok) return [];

  const data = await response.json();
  return data.logs.map((log: any) => ({
    id: log.id,
    message: log.message,
    timestamp: log.timestamp,
    level: log.labels.find((l: any) => l.name === 'level')?.value || 'info',
    type: log.labels.find((l: any) => l.name === 'type')?.value || 'app'
  }));
}

function getServiceIdsForStep(stepId: string): string[] {
  // These IDs will be populated from Render dashboard
  const SERVICE_MAP: Record<string, string[]> = {
    '0': [process.env.RENDER_INGEST_SERVICE_ID!],
    '1': [process.env.RENDER_PREFILTER_SERVICE_ID!],
    'all': [
      process.env.RENDER_PIPELINE_NIGHT_ID!,
      process.env.RENDER_PIPELINE_MORNING_ID!,
      process.env.RENDER_PIPELINE_EOD_ID!
    ]
  };
  return SERVICE_MAP[stepId] || SERVICE_MAP['all'];
}
```

### Frontend Component: Live Logs

**File:** `src/components/step/live-execution-logs.tsx` (NEW)

```tsx
"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type TimeFilter = "live" | "1h" | "12h" | "24h";

interface LogEntry {
  id: string;
  timestamp: string;
  level: "info" | "warn" | "error" | "debug";
  message: string;
  metadata?: Record<string, any>;
  step_id?: number;
  job_type?: string;
  slot_number?: number;
}

interface LiveExecutionLogsProps {
  stepId: number;
}

export function LiveExecutionLogs({ stepId }: LiveExecutionLogsProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<TimeFilter>("live");
  const [isConnected, setIsConnected] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Open SSE connection
    const url = `/api/logs/stream?stepId=${stepId}&filter=${filter}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => setIsConnected(true);
    eventSource.onerror = () => setIsConnected(false);

    eventSource.onmessage = (event) => {
      const newLogs = JSON.parse(event.data);
      setLogs((prev) => {
        if (filter === "live") {
          // Append new logs, keep last 500
          return [...prev, ...newLogs].slice(-500);
        }
        // Replace for historical views
        return newLogs;
      });
    };

    return () => eventSource.close();
  }, [stepId, filter]);

  // Auto-scroll for live view
  useEffect(() => {
    if (filter === "live") {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, filter]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            Execution Logs
            {filter === "live" && (
              <Badge variant={isConnected ? "default" : "destructive"}>
                {isConnected ? "● Live" : "Disconnected"}
              </Badge>
            )}
          </CardTitle>

          {/* Time Filter Buttons - Render Style */}
          <div className="flex gap-1">
            {(["live", "1h", "12h", "24h"] as TimeFilter[]).map((f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "ghost"}
                size="sm"
                onClick={() => setFilter(f)}
                className="text-xs"
              >
                {f === "live" ? "Live" : f === "1h" ? "Past Hour" : f === "12h" ? "Past 12h" : "Past 24h"}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="h-[400px] overflow-y-auto bg-zinc-950 rounded-md p-3 font-mono text-sm">
          {logs.length === 0 ? (
            <div className="text-zinc-500 text-center py-8">
              {filter === "live" ? "Waiting for logs..." : "No logs in this time period"}
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className={cn(
                  "py-0.5 flex gap-2",
                  log.level === "error" && "text-red-400",
                  log.level === "warn" && "text-amber-400",
                  log.level === "info" && "text-zinc-300",
                  log.level === "debug" && "text-zinc-500"
                )}
              >
                <span className="text-zinc-500 shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString("en-US", {
                    timeZone: "America/New_York",
                    hour12: false,
                  })}
                </span>
                <span className={cn(
                  "shrink-0 w-12",
                  log.level === "error" && "text-red-500",
                  log.level === "warn" && "text-amber-500"
                )}>
                  [{log.level.toUpperCase()}]
                </span>
                {log.slot_number && (
                  <Badge variant="outline" className="shrink-0 text-xs">
                    Slot {log.slot_number}
                  </Badge>
                )}
                <span className="break-all">{log.message}</span>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Part 4: Pipeline Job Implementation

**File:** `workers/jobs/pipeline.py` (NEW)

```python
"""
Chained Pipeline Job
Runs: Ingest → AI Scoring → Pre-Filter (all slots sequential)
"""

import time
from datetime import datetime

def run_full_pipeline():
    """
    Execute the complete pipeline as a single chained job.
    Each step runs only after the previous completes.
    """
    pipeline_start = datetime.now()
    print(f"[Pipeline] ===== STARTING FULL PIPELINE at {pipeline_start} =====")

    results = {
        "pipeline_started_at": pipeline_start.isoformat(),
        "ingest": None,
        "ai_scoring": None,
        "pre_filter": None,
        "pipeline_completed_at": None,
        "total_duration_seconds": None
    }

    try:
        # Step 0: Ingest
        print("[Pipeline] ----- Step 0: Ingest -----")
        from jobs.ingest_sandbox import run_all_ingest_jobs
        ingest_result = run_all_ingest_jobs()
        results["ingest"] = ingest_result
        print(f"[Pipeline] Ingest complete: {ingest_result.get('articles_ingested', 0)} articles")

        # Step 0.5: AI Scoring (only if articles were ingested)
        if ingest_result.get("articles_ingested", 0) > 0:
            print("[Pipeline] ----- Step 0.5: AI Scoring -----")
            from jobs.ai_scoring_sandbox import run_ai_scoring_sandbox
            scoring_result = run_ai_scoring_sandbox()
            results["ai_scoring"] = scoring_result
            print(f"[Pipeline] AI Scoring complete: {scoring_result.get('articles_scored', 0)} scored")
        else:
            print("[Pipeline] Skipping AI Scoring (no new articles)")
            results["ai_scoring"] = {"skipped": True, "reason": "no_new_articles"}

        # Step 1: Pre-Filter (all 5 slots sequential)
        print("[Pipeline] ----- Step 1: Pre-Filter (All Slots) -----")
        from jobs.pre_filter import run_all_prefilter_slots_sequential
        prefilter_result = run_all_prefilter_slots_sequential()
        results["pre_filter"] = prefilter_result
        print(f"[Pipeline] Pre-Filter complete: {prefilter_result.get('total_selected', 0)} selected")

    except Exception as e:
        print(f"[Pipeline] !!!!! PIPELINE ERROR: {e} !!!!!")
        results["error"] = str(e)
        raise

    finally:
        pipeline_end = datetime.now()
        duration = (pipeline_end - pipeline_start).total_seconds()
        results["pipeline_completed_at"] = pipeline_end.isoformat()
        results["total_duration_seconds"] = duration

        print(f"[Pipeline] ===== PIPELINE COMPLETE in {duration:.1f}s =====")
        print(f"[Pipeline] Results: {results}")

    return results
```

---

## Part 5: Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `workers/jobs/pipeline.py` | Chained pipeline job (Ingest → AI Scoring → Pre-Filter) |
| `src/app/api/logs/render/route.ts` | Fetch logs from Render API |
| `src/app/api/logs/stream/route.ts` | SSE endpoint wrapping Render API |
| `src/components/step/live-execution-logs.tsx` | Render-style live logs component |

### Files to Modify

| File | Changes |
|------|---------|
| `workers/jobs/pre_filter.py` | Add `run_all_prefilter_slots_sequential()`, per-slot Airtable writes |
| `workers/render.yaml` | Replace 5 slot crons with 3 pipeline crons |
| `src/components/step/zeroin-ingest-panel.tsx` | Replace execution-logs with live-execution-logs |
| `src/components/step/prefilter-panel.tsx` | Add live-execution-logs component |
| `.env.local` | Add `RENDER_API_KEY` and service IDs |

### NO LONGER NEEDED (Render API simplification)

| Was Planned | Why Not Needed |
|-------------|----------------|
| `db/migrations/xxx_add_log_entries.sql` | Using Render's logs directly |
| Modify `ingest_sandbox.py` for logging | Render already captures all print() |
| Modify `ai_scoring_sandbox.py` for logging | Render already captures all print() |

---

## Part 6: Render.yaml Changes

### REMOVE (Old Separate Crons)

```yaml
# DELETE THESE:
- name: ai-editor-ingest-cron
- name: ai-editor-prefilter-slot-1
- name: ai-editor-prefilter-slot-2
- name: ai-editor-prefilter-slot-3
- name: ai-editor-prefilter-slot-4
- name: ai-editor-prefilter-slot-5
```

### ADD (New Chained Pipeline Crons)

**⚠️ CRITICAL: `rootDir` must be `workers` NOT the full path!**

```yaml
# =============================================================================
# CHAINED PIPELINE - 3 daily cycles
# =============================================================================
- type: cron
  name: ai-editor-pipeline-night
  runtime: python
  region: oregon
  plan: starter
  schedule: "0 7 * * *"  # 2:00 AM ET
  rootDir: workers  # ⚠️ JUST "workers" - NOT the full nested path!
  buildCommand: pip install -r requirements.txt
  startCommand: python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"
  envVars:
    # ... (same as existing worker envVars)

- type: cron
  name: ai-editor-pipeline-morning
  runtime: python
  region: oregon
  plan: starter
  schedule: "30 14 * * *"  # 9:30 AM ET
  rootDir: workers  # ⚠️ JUST "workers" - NOT the full nested path!
  buildCommand: pip install -r requirements.txt
  startCommand: python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"
  envVars:
    # ... (same as existing worker envVars)

- type: cron
  name: ai-editor-pipeline-eod
  runtime: python
  region: oregon
  plan: starter
  schedule: "0 22 * * *"  # 5:00 PM ET
  rootDir: workers  # ⚠️ JUST "workers" - NOT the full nested path!
  buildCommand: pip install -r requirements.txt
  startCommand: python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"
  envVars:
    # ... (same as existing worker envVars)

- type: cron
  name: ai-editor-newsletter-extract
  runtime: python
  region: oregon
  plan: starter
  schedule: "30 21 * * *"  # 4:30 PM ET
  rootDir: workers  # ⚠️ JUST "workers" - NOT the full nested path!
  buildCommand: pip install -r requirements.txt
  startCommand: python -c "from jobs.newsletter_extraction import run_newsletter_extraction; run_newsletter_extraction()"
  envVars:
    # ... (same as existing worker envVars)
```

---

## Part 7: Implementation Order

### Phase 1: Pipeline & Pre-Filter (Backend)
1. Create `workers/jobs/pipeline.py` - chained pipeline job
2. Modify `workers/jobs/pre_filter.py` - add sequential function with per-slot Airtable writes
3. Test locally: `python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"`

### Phase 2: Render API Integration (Frontend)
1. Get Render API key from dashboard
2. Get service IDs for each pipeline cron job
3. Add env vars to `.env.local`: `RENDER_API_KEY`, service IDs
4. Create `src/app/api/logs/render/route.ts` - fetch logs from Render
5. Create `src/app/api/logs/stream/route.ts` - SSE wrapper
6. Test API: `curl http://localhost:3000/api/logs/render?hours=1`

### Phase 3: Live Logs Component (Frontend)
1. Create `src/components/step/live-execution-logs.tsx`
2. Replace old execution-logs in zeroin-ingest-panel.tsx
3. Add to prefilter-panel.tsx
4. Test live view with time filters

### Phase 4: Cron Migration (Deploy)
1. Update `workers/render.yaml`:
   - Remove 6 old crons (1 ingest + 5 prefilter slots)
   - Add 4 new crons (3 pipelines + 1 newsletter extract)
2. Deploy to Render
3. Monitor first pipeline run
4. Verify logs appear in dashboard

---

## Summary: What Changed

| Area | OLD | NEW |
|------|-----|-----|
| **Ingest Schedule** | 3x daily (6AM, 2PM, 10PM) | 3x daily (2AM, 9:30AM, 5PM) |
| **AI Scoring** | Manual only | Automated in pipeline |
| **Pre-Filter** | 5 separate crons, staggered | 1 job, sequential, per-slot writes |
| **Newsletter Extract** | Not implemented | 4:30 PM daily |
| **Logging Source** | Custom DB logging | **Direct Render API** |
| **Logging Method** | Polling every 5s | SSE (polling Render every 3s) |
| **Time Filters** | None | Live / 1h / 12h / 24h |
| **Cron Jobs** | 6 (1 ingest + 5 slots × 3 cycles) | 4 (3 pipelines + 1 newsletter) |
| **DB Changes** | Would need new tables | **None needed** |
| **Python Changes** | Would need logging calls | **None needed** (Render captures print()) |

---

## Key Simplification: Render API

The biggest win from this plan is using **Render's Logs API directly** instead of building custom logging infrastructure:

```
BEFORE (Custom approach):
Python jobs → Custom log calls → Our Postgres → Custom API → Frontend

AFTER (Render API approach):
Python jobs → print() → Render captures → Render API → Our SSE wrapper → Frontend
```

**Benefits:**
1. No database schema changes
2. No Python code changes (just use print())
3. Exact same logs as Render dashboard
4. Single source of truth
5. Less code to maintain

---

## Appendix: Timezone Reference

| Eastern Time | UTC | Action |
|--------------|-----|--------|
| 2:00 AM ET | 7:00 UTC | Pipeline Cycle 1 (Night) |
| 4:30 PM ET | 21:30 UTC | Newsletter Extraction |
| 5:00 PM ET | 22:00 UTC | Pipeline Cycle 3 (EOD) |
| 9:30 AM ET | 14:30 UTC | Pipeline Cycle 2 (Morning) |

**Note:** During Daylight Saving Time (EDT), UTC offset changes from -5 to -4 hours. Cron jobs in UTC will run at different local times.

---

## Part 8: 24-Hour Pre-Filter Window (Deduplication Fix)

**Added:** January 5, 2026
**Status:** PLANNED (not yet implemented)

### The Problem: Wasted Processing & No Deduplication

Currently, the pre-filter agent fetches stories from Newsletter Selects using a **7-day lookback window**:

```python
# Line 72-74 in prefilter.py (cron path)
seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
fresh_stories = airtable.get_newsletter_selects(since_date=seven_days_ago)
```

**Critical issue:** There is **NO deduplication** against the Pre-Filter Log table. The pre-filter has no awareness of what it already processed yesterday.

#### What Actually Happens Each Run

1. Pre-filter fetches ALL stories from Newsletter Selects with `date_og_published` in last 7 days
2. For each story, it checks:
   - Is this story in yesterday's newsletter issue? → Skip (only exclusion)
   - Is story > 168 hours old? → Skip (too stale)
   - Is source low credibility? → Skip
3. Everything else gets **re-processed by AI**, even if it was already categorized yesterday

#### Example of Wasted Processing

```
Monday:    200 stories in Newsletter Selects → Pre-filter processes all 200
Tuesday:   230 stories (200 from Mon + 30 new) → Pre-filter processes all 230
Wednesday: 260 stories (230 from Tue + 30 new) → Pre-filter processes all 260
```

By Wednesday, stories from Monday have been processed **3 times** by the AI pre-filter agents.

### The Solution: 24-Hour Lookback Window

Since the pipeline runs **3 times daily** (2AM, 9:30AM, 5PM ET) with no weekend gaps:
- Pre-filter only needs to look at stories from the **last 24 hours**
- Stories older than 24 hours were already processed in a previous run
- This eliminates redundant AI processing

#### Why 7-Day Existed (Historical Context)

The 7-day window was originally designed to:
1. Handle weekend gaps (no processing Sat/Sun)
2. Apply "freshness rules" for slot eligibility
3. Act as a safety net if crons failed

**With daily automation, these reasons no longer apply:**
- No weekend gaps - pipeline runs every day
- Freshness rules apply to `date_og_published`, not when pre-filtered
- If a cron fails, the next run (same day) will catch new stories

### Code Changes Required

#### File: `workers/jobs/prefilter.py`

Two locations need to be updated:

##### 1. Cron Path: `prefilter_stories()` function (Line 72-74)

This is called by the pipeline crons via `run_full_pipeline()`.

```python
# CURRENT (7-day window):
seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
print(f"[Step 1] Date filter: since {seven_days_ago}", flush=True)
fresh_stories = airtable.get_newsletter_selects(since_date=seven_days_ago)

# NEW (24-hour window):
one_day_ago = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
print(f"[Step 1] Date filter: since {one_day_ago} (24h window)", flush=True)
fresh_stories = airtable.get_newsletter_selects(since_date=one_day_ago)
```

##### 2. Manual Path: `_gather_prefilter_data()` function (Line 541-542)

This is called when clicking slot buttons 1-5 on the dashboard via `_run_single_slot()`.

```python
# CURRENT (7-day window):
seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
fresh_stories = airtable.get_newsletter_selects(since_date=seven_days_ago)

# NEW (24-hour window):
one_day_ago = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
fresh_stories = airtable.get_newsletter_selects(since_date=one_day_ago)
```

### Code Path Details

Understanding both code paths is critical for this change:

#### Manual Slot Button Flow (Dashboard)

```
User clicks "Run Slot 1" button on dashboard
    ↓
Frontend: POST /api/trigger/prefilter_slot_1
    ↓
Next.js API → ai-editor-trigger service (trigger.py)
    ↓
trigger.py routes to: prefilter_slot_1() (prefilter.py line 784)
    ↓
prefilter_slot_1() calls: _run_single_slot(1) (line 751)
    ↓
_run_single_slot() calls: _gather_prefilter_data(slot=1) (line 656)
    ↓
_gather_prefilter_data() uses 7-day window (LINE 541-542) ← CHANGE HERE
```

#### Cron Pipeline Flow (Automated)

```
Render cron triggers at scheduled time
    ↓
startCommand: python -c "from jobs.pipeline import run_full_pipeline; run_full_pipeline()"
    ↓
run_full_pipeline() (pipeline.py)
    ↓
Calls: prefilter_stories() directly (prefilter.py line 72)
    ↓
prefilter_stories() uses 7-day window (LINE 72-74) ← CHANGE HERE
```

### Freshness Rules (UNCHANGED)

The freshness rules that determine slot eligibility remain **unchanged**. These are based on `date_og_published`, not when the story enters the pipeline:

```python
# prefilter.py lines 475-496 - NO CHANGES NEEDED
def _calculate_eligible_slots(freshness_hours: int) -> List[int]:
    """
    0-24 hours old:  eligible for slots 1, 2, 3, 4, 5
    24-48 hours old: eligible for slots 2, 3, 4, 5
    48-72 hours old: eligible for slots 3, 4, 5
    72-168 hours old: eligible for slots 3, 5 only
    >168 hours: not eligible
    """
    if freshness_hours <= 24:
        return [1, 2, 3, 4, 5]
    elif freshness_hours <= 48:
        return [2, 3, 4, 5]
    elif freshness_hours <= 72:
        return [3, 4, 5]
    elif freshness_hours <= 168:
        return [3, 5]
    else:
        return []
```

A story published 36 hours ago will still only be eligible for slots 2-5. The 24-hour lookback window just means we won't **re-process** stories that were already categorized yesterday.

### Summary of Changes

| Item | Change |
|------|--------|
| `prefilter.py` line 72 | `timedelta(days=7)` → `timedelta(days=1)` |
| `prefilter.py` line 541 | `timedelta(days=7)` → `timedelta(days=1)` |
| Variable name | `seven_days_ago` → `one_day_ago` |
| Print statement | Update to reflect "24h window" |

### Expected Impact

| Metric | Before (7-day) | After (24-hour) |
|--------|----------------|-----------------|
| Stories processed per run | ~500-1000 | ~100-200 |
| AI API calls per run | ~500-1000 | ~100-200 |
| Duplicate processing | High (same story 3-7x) | None |
| Processing time | ~45-60 min | ~10-15 min |
| API costs | Higher | ~80% reduction |

### Implementation Checklist

- [ ] Update `prefilter_stories()` line 72-74 (cron path)
- [ ] Update `_gather_prefilter_data()` line 541-542 (manual path)
- [ ] Update variable names and print statements
- [ ] Test manual slot button (dashboard)
- [ ] Test via cron pipeline
- [ ] Monitor first full day of runs
- [ ] Verify no duplicate processing in Pre-Filter Log

### Rollback Plan

If issues arise, simply revert to 7-day window:
```python
one_day_ago = (datetime.utcnow() - timedelta(days=1))  # New
seven_days_ago = (datetime.utcnow() - timedelta(days=7))  # Rollback
```

The 7-day window is safe but inefficient. Rolling back would just mean redundant processing, not data loss.
