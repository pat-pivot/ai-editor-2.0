# Render Logs Frontend Fix - Comprehensive Plan

**Date:** January 7, 2026
**Author:** Claude Code
**Status:** Planning Phase - Ready for Implementation

---

## 1. Executive Summary

The AI Editor 2.0 frontend displays "Waiting for logs..." instead of showing actual Render logs. Investigation reveals the root cause is **429 rate limiting errors** from the Render Logs API. The current implementation polls every 3 seconds (20 requests/minute), but the Render Logs API has a strict **30 requests/minute limit**. When multiple browser tabs, users, or automated refreshes are active, this limit is quickly exceeded.

### Key Findings

| Aspect | Current State | Issue |
|--------|---------------|-------|
| Polling Interval | 3 seconds (20 req/min) | Too aggressive for multi-user scenarios |
| Rate Limit | 30 req/min for logs endpoint | Easily exceeded with concurrent connections |
| Error Handling | Returns empty logs on 429 | No backoff, no caching, no retry |
| Log Separation | All services fetched together | No filtering by step prefix |

### Recommended Solution

1. **MVP (Phase 1):** Fix rate limiting with server-side caching, exponential backoff, and singleton SSE connections
2. **Phase 2:** Add log filtering by step using message prefix patterns (`[Step 0]`, `[Step 1]`, `[Pipeline]`, etc.)

---

## 2. Current Code Analysis

### 2.1 API Routes

#### `/api/logs/stream/route.ts` (SSE Streaming Endpoint)
**Location:** `/Users/patsimmons/client-coding/pivot-5-website_11.19.25/ai-editor-2.0-full-stack-application/app/src/app/api/logs/stream/route.ts`

**Purpose:** Server-Sent Events endpoint that polls Render API and streams logs to the frontend.

**Current Implementation Issues:**

```typescript
// Line 27: Polling every 3 seconds = 20 req/min per connection
const POLL_INTERVAL_MS = 3000;

// Lines 31-39: Hardcoded service IDs (correct approach)
const SERVICE_IDS = {
  worker: "srv-d55i64juibrs7392tcn0",
  trigger: "srv-d563ffvgi27c73dtqdq0",
  pipelineNight: "crn-d5e2shv5r7bs73ca4dp0",
  pipelineMorning: "crn-d5e2sl2li9vc73dt5q40",
  pipelineEod: "crn-d5e2smq4d50c73fjo0tg",
};
```

**Problems Identified:**
1. No rate limit tracking using response headers (`Ratelimit-Remaining`, `Ratelimit-Reset`)
2. No exponential backoff on 429 errors
3. No server-side caching - every SSE connection makes independent API calls
4. Each browser tab opens a new SSE connection, multiplying API calls
5. Error on line 140: silently returns empty array on non-200 responses

#### `/api/logs/render/route.ts` (Non-Streaming Endpoint)
**Location:** `/Users/patsimmons/client-coding/pivot-5-website_11.19.25/ai-editor-2.0-full-stack-application/app/src/app/api/logs/render/route.ts`

**Purpose:** One-time fetch endpoint for historical logs.

**Current 429 Handling (Insufficient):**
```typescript
// Lines 181-185: Returns error but no retry logic
if (response.status === 429) {
  return NextResponse.json(
    { error: "Rate limited by Render API. Try again in a minute.", logs: [] },
    { status: 429 }
  );
}
```

### 2.2 Frontend Components

#### `live-execution-logs.tsx`
**Location:** `/Users/patsimmons/client-coding/pivot-5-website_11.19.25/ai-editor-2.0-full-stack-application/app/src/components/step/live-execution-logs.tsx`

**Current Implementation:**
```typescript
// Lines 87-91: Opens new EventSource on every render/filter change
const stepParam = stepId === 0 ? "0" : stepId === 1 ? "1" : "all";
const url = `/api/logs/stream?stepId=${stepParam}&filter=${filter}`;
const eventSource = new EventSource(url);
```

**Problems Identified:**
1. No singleton pattern - multiple components = multiple SSE connections
2. No reconnection backoff after errors (lines 99-108 have 5-second timeout but no backoff)
3. Clears logs on filter change (line 153), causing "waiting for logs" state

### 2.3 Log Message Prefix Patterns

Analysis of worker code reveals these log prefixes for filtering by step:

| Prefix Pattern | Step | Source File |
|---------------|------|-------------|
| `[Pipeline]` | Pipeline orchestration | `jobs/pipeline.py` |
| `[Ingest]`, `[Ingest Sandbox]`, `[DIRECT FEED INGEST]` | Step 0 - Ingest | `jobs/ingest*.py` |
| `[Step 1]`, `[Prefilter]`, `[Gemini slot_X]` | Step 1 - Pre-filter | `jobs/prefilter.py` |
| `[Step 2]` | Step 2 - Slot Selection | Various |
| `[Step 3]`, `[Step 3b]` | Step 3 - Decoration | Various |
| `[Step 4]`, `[Step 4a]`, `[Step 4b]`, `[Step 4c]` | Step 4 - Compile/Send | Various |
| `[Step 5]` | Step 5 - Social Sync | Various |

---

## 3. Render API Findings

### 3.1 Rate Limits (Official Documentation)

From Render API docs (https://api-docs.render.com/reference/rate-limiting):

| Endpoint Category | Rate Limit |
|-------------------|------------|
| **Logs endpoints** (`/v1/logs`, `/subscribe`, `/values`) | **30 per minute** |
| GET requests (general) | 400 per minute |
| POST/PATCH/DELETE (general) | 30 per minute |
| Deploy operations | 10 per minute per service |

### 3.2 Rate Limit Headers

Every Render API response includes:
- `Ratelimit-Limit`: Maximum requests allowed per time window
- `Ratelimit-Remaining`: Requests remaining in current window
- `Ratelimit-Reset`: UTC epoch seconds when window resets

**These headers should be read and used for intelligent rate limiting.**

### 3.3 Log Data Limits

From Render documentation:
- **6,000 log lines per minute** per service instance (application-generated)
- Excess logs are dropped and won't appear in API or dashboard
- Log retention depends on workspace plan

### 3.4 API Endpoint Details

```
GET https://api.render.com/v1/logs
Headers:
  Authorization: Bearer {RENDER_API_KEY}
  Accept: application/json

Query Parameters:
  resource[]: Service ID (can repeat for multiple services)
  startTime: ISO 8601 timestamp
  endTime: ISO 8601 timestamp (optional)
  limit: Number of logs to return
  direction: "backward" (newest first) or "forward"
  level[]: Filter by log level
```

---

## 4. MVP Solution: 1:1 Render Log Mirroring

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LiveExecutionLogs Component                             │   │
│  │  - Singleton EventSource connection                      │   │
│  │  - Exponential backoff on disconnect                     │   │
│  │  - Connection state indicator                            │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │ SSE                                    │
└─────────────────────────┼───────────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────────┐
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  /api/logs/stream (Next.js API Route)                    │   │
│  │  - Single shared cache for all SSE clients               │   │
│  │  - Rate limit header tracking                            │   │
│  │  - Exponential backoff on 429                            │   │
│  │  - Poll interval: 6 seconds (10 req/min base)            │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Server-Side Log Cache (In-Memory)                       │   │
│  │  - TTL: 5 seconds                                        │   │
│  │  - Shared across all SSE connections                     │   │
│  │  - Keyed by service IDs                                  │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │                                        │
│                    API Call (if cache miss/stale)                │
│                         │                                        │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Render Logs API     │
              │   30 req/min limit    │
              └───────────────────────┘
```

### 4.2 Implementation Plan

#### Step 1: Add Server-Side Log Cache

Create a simple in-memory cache module:

**New File:** `/src/lib/render-logs-cache.ts`

```typescript
/**
 * Server-side cache for Render logs
 * Prevents multiple SSE connections from hitting rate limits
 */

interface CachedLogs {
  logs: RenderLog[];
  timestamp: number;
  rateLimitRemaining: number;
  rateLimitReset: number;
}

interface RenderLog {
  id: string;
  timestamp: string;
  message: string;
  level: string;
  type: string;
  service: string;
}

// In-memory cache (survives across SSE connections but not server restarts)
const logCache: Map<string, CachedLogs> = new Map();

// Cache TTL in milliseconds (5 seconds)
const CACHE_TTL_MS = 5000;

// Minimum interval between API calls (even on cache miss)
let lastFetchTime = 0;
const MIN_FETCH_INTERVAL_MS = 2000; // 2 seconds minimum between fetches

export function getCacheKey(serviceIds: string[]): string {
  return serviceIds.sort().join(',');
}

export function getCachedLogs(serviceIds: string[]): CachedLogs | null {
  const key = getCacheKey(serviceIds);
  const cached = logCache.get(key);

  if (!cached) return null;

  // Check if cache is still valid
  if (Date.now() - cached.timestamp > CACHE_TTL_MS) {
    return null; // Cache expired
  }

  return cached;
}

export function setCachedLogs(
  serviceIds: string[],
  logs: RenderLog[],
  rateLimitRemaining: number,
  rateLimitReset: number
): void {
  const key = getCacheKey(serviceIds);
  logCache.set(key, {
    logs,
    timestamp: Date.now(),
    rateLimitRemaining,
    rateLimitReset,
  });
}

export function canFetch(): boolean {
  return Date.now() - lastFetchTime >= MIN_FETCH_INTERVAL_MS;
}

export function markFetchTime(): void {
  lastFetchTime = Date.now();
}

export function getRateLimitInfo(serviceIds: string[]): { remaining: number; resetAt: number } | null {
  const cached = logCache.get(getCacheKey(serviceIds));
  if (!cached) return null;
  return {
    remaining: cached.rateLimitRemaining,
    resetAt: cached.rateLimitReset,
  };
}
```

#### Step 2: Update SSE Stream Endpoint

**File:** `/src/app/api/logs/stream/route.ts`

Key changes:
1. Use shared cache
2. Read rate limit headers
3. Implement exponential backoff
4. Increase base poll interval to 6 seconds

```typescript
import { NextRequest } from "next/server";
import {
  getCachedLogs,
  setCachedLogs,
  canFetch,
  markFetchTime,
  getCacheKey,
} from "@/lib/render-logs-cache";

const RENDER_API_KEY = process.env.RENDER_API_KEY;
const RENDER_API_URL = "https://api.render.com/v1/logs";

// Base polling interval: 6 seconds (10 req/min baseline)
const BASE_POLL_INTERVAL_MS = 6000;
// Maximum backoff: 30 seconds
const MAX_POLL_INTERVAL_MS = 30000;

// Service IDs (unchanged)
const SERVICE_IDS = {
  worker: process.env.RENDER_WORKER_SERVICE_ID || "srv-d55i64juibrs7392tcn0",
  trigger: process.env.RENDER_TRIGGER_SERVICE_ID || "srv-d563ffvgi27c73dtqdq0",
  pipelineNight: process.env.RENDER_PIPELINE_NIGHT_ID || "crn-d5e2shv5r7bs73ca4dp0",
  pipelineMorning: process.env.RENDER_PIPELINE_MORNING_ID || "crn-d5e2sl2li9vc73dt5q40",
  pipelineEod: process.env.RENDER_PIPELINE_EOD_ID || "crn-d5e2smq4d50c73fjo0tg",
};

// ... (getServiceIdsForStep function unchanged)

async function fetchRenderLogsWithCache(
  serviceIds: string[],
  hours: number,
  limit: number = 50
): Promise<{ logs: RenderLog[]; fromCache: boolean; rateLimitRemaining: number }> {
  // Check cache first
  const cached = getCachedLogs(serviceIds);
  if (cached) {
    return { logs: cached.logs, fromCache: true, rateLimitRemaining: cached.rateLimitRemaining };
  }

  // Check if we can make an API call
  if (!canFetch()) {
    // Return empty if we're rate-limited locally
    return { logs: [], fromCache: false, rateLimitRemaining: 0 };
  }

  if (!RENDER_API_KEY || serviceIds.length === 0) {
    return { logs: [], fromCache: false, rateLimitRemaining: 30 };
  }

  markFetchTime();

  const startTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

  const params = new URLSearchParams();
  serviceIds.forEach((id) => params.append("resource[]", id));
  params.append("startTime", startTime);
  params.append("limit", limit.toString());
  params.append("direction", "backward");

  try {
    const response = await fetch(`${RENDER_API_URL}?${params}`, {
      headers: {
        Authorization: `Bearer ${RENDER_API_KEY}`,
        Accept: "application/json",
      },
    });

    // Extract rate limit headers
    const rateLimitRemaining = parseInt(response.headers.get("Ratelimit-Remaining") || "30", 10);
    const rateLimitReset = parseInt(response.headers.get("Ratelimit-Reset") || "0", 10);

    if (response.status === 429) {
      console.warn("[SSE Stream] Rate limited by Render API");
      return { logs: [], fromCache: false, rateLimitRemaining: 0 };
    }

    if (!response.ok) {
      console.error("[SSE Stream] Render API error:", response.status);
      return { logs: [], fromCache: false, rateLimitRemaining };
    }

    const data = await response.json();

    const logs = data.logs.map((log: RenderLogEntry) => ({
      id: log.id,
      timestamp: log.timestamp,
      message: log.message,
      level: log.labels.find((l) => l.name === "level")?.value || "info",
      type: log.labels.find((l) => l.name === "type")?.value || "app",
      service: log.labels.find((l) => l.name === "service")?.value || "unknown",
    }));

    // Cache the results
    setCachedLogs(serviceIds, logs, rateLimitRemaining, rateLimitReset);

    return { logs, fromCache: false, rateLimitRemaining };
  } catch (error) {
    console.error("[SSE Stream] Fetch error:", error);
    return { logs: [], fromCache: false, rateLimitRemaining: 0 };
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const stepId = searchParams.get("stepId") || "all";
  const filter = searchParams.get("filter") || "live";

  const serviceIds = getServiceIdsForStep(stepId);
  const encoder = new TextEncoder();

  let seenIds = new Set<string>();
  let currentPollInterval = BASE_POLL_INTERVAL_MS;
  let consecutiveErrors = 0;

  const stream = new ReadableStream({
    async start(controller) {
      if (!RENDER_API_KEY) {
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              error: "RENDER_API_KEY not configured",
              logs: [],
            })}\n\n`
          )
        );
        controller.close();
        return;
      }

      const initialHours = getHoursFromFilter(filter);
      const initialLimit = filter === "live" ? 50 : 100;

      try {
        const { logs: initialLogs, rateLimitRemaining } = await fetchRenderLogsWithCache(
          serviceIds,
          initialHours,
          initialLimit
        );

        controller.enqueue(encoder.encode(`data: ${JSON.stringify(initialLogs)}\n\n`));

        initialLogs.forEach((log) => seenIds.add(log.id));

        if (filter !== "live") {
          controller.close();
          return;
        }

        // Adaptive polling with exponential backoff
        const poll = async () => {
          try {
            const { logs: newLogs, fromCache, rateLimitRemaining } = await fetchRenderLogsWithCache(
              serviceIds,
              0.05, // Last 3 minutes
              30
            );

            const filteredLogs = newLogs.filter((log) => !seenIds.has(log.id));

            if (filteredLogs.length > 0) {
              controller.enqueue(encoder.encode(`data: ${JSON.stringify(filteredLogs)}\n\n`));
              filteredLogs.forEach((log) => seenIds.add(log.id));

              if (seenIds.size > 1000) {
                const idsArray = Array.from(seenIds);
                seenIds = new Set(idsArray.slice(-500));
              }
            }

            // Adjust poll interval based on rate limit remaining
            if (rateLimitRemaining < 5) {
              // Getting close to limit, back off
              currentPollInterval = Math.min(currentPollInterval * 1.5, MAX_POLL_INTERVAL_MS);
              consecutiveErrors++;
            } else if (rateLimitRemaining > 20 && consecutiveErrors === 0) {
              // Plenty of headroom, can poll faster
              currentPollInterval = BASE_POLL_INTERVAL_MS;
            }

            // Reset error counter on success
            if (!fromCache && rateLimitRemaining > 0) {
              consecutiveErrors = 0;
            }
          } catch (error) {
            console.error("[SSE Stream] Poll error:", error);
            consecutiveErrors++;
            // Exponential backoff on errors
            currentPollInterval = Math.min(
              BASE_POLL_INTERVAL_MS * Math.pow(2, consecutiveErrors),
              MAX_POLL_INTERVAL_MS
            );
          }

          // Schedule next poll with current interval
          pollTimeout = setTimeout(poll, currentPollInterval);
        };

        let pollTimeout = setTimeout(poll, currentPollInterval);

        request.signal.addEventListener("abort", () => {
          clearTimeout(pollTimeout);
          controller.close();
        });
      } catch (error) {
        console.error("[SSE Stream] Initial fetch error:", error);
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              error: "Failed to fetch initial logs",
              logs: [],
            })}\n\n`
          )
        );
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
```

#### Step 3: Update Frontend Component

**File:** `/src/components/step/live-execution-logs.tsx`

Key changes:
1. Add reconnection with exponential backoff
2. Keep logs on filter change (only clear for different step)
3. Show connection quality indicator

```typescript
"use client";

import { useState, useEffect, useRef, useCallback } from "react";
// ... other imports

export function LiveExecutionLogs({ stepId, title = "Execution Logs" }: LiveExecutionLogsProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<TimeFilter>("live");
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Exponential backoff for reconnection
  const getReconnectDelay = useCallback((attempt: number) => {
    const baseDelay = 1000; // 1 second
    const maxDelay = 30000; // 30 seconds
    const delay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
    // Add jitter (+-25%)
    return delay + (Math.random() - 0.5) * delay * 0.5;
  }, []);

  const connect = useCallback(() => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    const stepParam = stepId === 0 ? "0" : stepId === 1 ? "1" : "all";
    const url = `/api/logs/stream?stepId=${stepParam}&filter=${filter}`;

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setConnectionError(null);
      setReconnectAttempt(0); // Reset on successful connection
    };

    eventSource.onerror = () => {
      setIsConnected(false);

      // Schedule reconnection with exponential backoff
      const delay = getReconnectDelay(reconnectAttempt);
      setConnectionError(`Connection lost. Reconnecting in ${Math.round(delay / 1000)}s...`);

      reconnectTimeoutRef.current = setTimeout(() => {
        setReconnectAttempt((prev) => prev + 1);
        connect();
      }, delay);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.error) {
          setConnectionError(data.error);
          return;
        }

        const newLogs: LogEntry[] = Array.isArray(data) ? data : (data.logs || []);

        if (newLogs.length > 0) {
          setLogs((prev) => {
            if (filter === "live") {
              const combined = [...prev, ...newLogs];
              return combined.slice(-500);
            }
            return newLogs;
          });
        }
      } catch (e) {
        console.error("[LiveLogs] Parse error:", e);
      }
    };
  }, [stepId, filter, reconnectAttempt, getReconnectDelay]);

  useEffect(() => {
    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  // Don't clear logs on filter change - only when stepId changes
  const handleFilterChange = (newFilter: TimeFilter) => {
    setFilter(newFilter);
    // Only clear logs when switching to historical view
    if (newFilter !== "live") {
      setLogs([]);
    }
  };

  // ... rest of component unchanged
}
```

---

## 5. Phase 2 Solution: Log Separation by Step

### 5.1 Overview

Phase 2 adds client-side filtering to separate logs by pipeline step using message prefixes.

### 5.2 Step Prefix Mapping

```typescript
// /src/lib/log-filters.ts

export const STEP_LOG_PREFIXES: Record<string, RegExp[]> = {
  // Step 0: Ingest + AI Scoring
  "0": [
    /^\[Ingest/i,
    /^\[DIRECT FEED INGEST\]/i,
    /^\[Pipeline\]/i,
    /scoring/i,
  ],

  // Step 1: Pre-filter
  "1": [
    /^\[Step 1\]/i,
    /^\[Prefilter\]/i,
    /^\[Gemini slot_\d\]/i,
    /pre-?filter/i,
  ],

  // Step 2: Slot Selection
  "2": [
    /^\[Step 2\]/i,
    /slot selection/i,
  ],

  // Step 3: Decoration
  "3": [
    /^\[Step 3\]/i,
    /^\[Step 3b\]/i,
    /decoration/i,
  ],

  // Step 4: Compile & Send
  "4": [
    /^\[Step 4/i,
    /compile/i,
    /mautic/i,
    /gmail/i,
  ],

  // Step 5: Social Sync
  "5": [
    /^\[Step 5\]/i,
    /social/i,
  ],
};

export function filterLogsByStep(logs: LogEntry[], stepId: string): LogEntry[] {
  if (stepId === "all") return logs;

  const prefixes = STEP_LOG_PREFIXES[stepId];
  if (!prefixes) return logs;

  return logs.filter((log) =>
    prefixes.some((regex) => regex.test(log.message))
  );
}
```

### 5.3 Frontend Integration

Update `LiveExecutionLogs` to apply filtering:

```typescript
// In the onmessage handler:
eventSource.onmessage = (event) => {
  // ... parse data ...

  if (newLogs.length > 0) {
    // Apply step filter
    const stepParam = stepId === 0 ? "0" : stepId === 1 ? "1" : "all";
    const filteredByStep = filterLogsByStep(newLogs, stepParam);

    setLogs((prev) => {
      if (filter === "live") {
        const combined = [...prev, ...filteredByStep];
        return combined.slice(-500);
      }
      return filteredByStep;
    });
  }
};
```

---

## 6. Implementation Steps

### Phase 1: MVP (Fix Rate Limiting)

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 1 | Create log cache module | `/src/lib/render-logs-cache.ts` | 30 min |
| 2 | Update SSE endpoint with caching + backoff | `/src/app/api/logs/stream/route.ts` | 1 hour |
| 3 | Update render endpoint with backoff | `/src/app/api/logs/render/route.ts` | 30 min |
| 4 | Update frontend with reconnection logic | `/src/components/step/live-execution-logs.tsx` | 45 min |
| 5 | Test with multiple tabs | - | 30 min |
| 6 | Deploy and verify in production | - | 15 min |

**Total Phase 1:** ~3.5 hours

### Phase 2: Log Separation

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 1 | Create log filter utility | `/src/lib/log-filters.ts` | 20 min |
| 2 | Integrate filter in frontend | `/src/components/step/live-execution-logs.tsx` | 20 min |
| 3 | Add step filter UI if needed | Same file | 30 min |
| 4 | Test filtering accuracy | - | 30 min |

**Total Phase 2:** ~1.5 hours

---

## 7. Rate Limit Mitigation Strategies

### 7.1 Primary Strategy: Server-Side Caching

- **Cache TTL:** 5 seconds
- **Benefit:** All SSE clients share one cached result
- **Reduction:** N clients = 1 API call (instead of N API calls)

### 7.2 Secondary Strategy: Exponential Backoff

```
Attempt 1: 6 seconds (base)
Attempt 2: 12 seconds (6 * 2^1)
Attempt 3: 24 seconds (6 * 2^2)
Attempt 4: 30 seconds (capped)
```

### 7.3 Tertiary Strategy: Rate Limit Header Tracking

```typescript
// Read headers after each request
const remaining = response.headers.get("Ratelimit-Remaining");
const reset = response.headers.get("Ratelimit-Reset");

// Adjust behavior based on remaining quota
if (remaining < 5) {
  // Switch to longer polling interval
  pollInterval = 15000; // 15 seconds
}
```

### 7.4 Client-Side Connection Management

- Use singleton pattern for EventSource
- Track connection state globally
- Prevent multiple tabs from creating duplicate streams

### 7.5 Emergency Fallback

If rate limiting persists despite mitigations:

1. **Reduce poll frequency further** (10s, 15s, 30s)
2. **Implement "pull to refresh"** instead of live streaming
3. **Contact Render support** to request rate limit increase
4. **Consider log aggregation service** (Datadog, Sumo Logic) via Render Log Streams

---

## 8. Testing Checklist

### MVP Tests

- [ ] Single tab shows live logs correctly
- [ ] Multiple tabs don't cause 429 errors
- [ ] Connection reconnects after disconnect
- [ ] Rate limit headers are being read
- [ ] Cache is working (check console logs)
- [ ] Historical views (1h, 12h, 24h) load correctly

### Phase 2 Tests

- [ ] Step 0 filter shows only ingest logs
- [ ] Step 1 filter shows only pre-filter logs
- [ ] "All" shows complete logs
- [ ] Filter changes don't lose existing logs in live mode

---

## 9. Appendix

### A. Environment Variables

```bash
# Required
RENDER_API_KEY=rnd_xxxxx

# Optional (defaults provided in code)
RENDER_WORKER_SERVICE_ID=srv-d55i64juibrs7392tcn0
RENDER_TRIGGER_SERVICE_ID=srv-d563ffvgi27c73dtqdq0
RENDER_PIPELINE_NIGHT_ID=crn-d5e2shv5r7bs73ca4dp0
RENDER_PIPELINE_MORNING_ID=crn-d5e2sl2li9vc73dt5q40
RENDER_PIPELINE_EOD_ID=crn-d5e2smq4d50c73fjo0tg
```

### B. Render API Quick Reference

```bash
# Test API connectivity
curl -I "https://api.render.com/v1/logs?resource[]=srv-d55i64juibrs7392tcn0&limit=5" \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Accept: application/json"

# Check rate limit headers in response:
# Ratelimit-Limit: 30
# Ratelimit-Remaining: 29
# Ratelimit-Reset: 1704654120
```

### C. Related Files

| File | Purpose |
|------|---------|
| `/src/app/api/logs/stream/route.ts` | SSE streaming endpoint |
| `/src/app/api/logs/render/route.ts` | One-time fetch endpoint |
| `/src/components/step/live-execution-logs.tsx` | Live log viewer |
| `/src/components/step/execution-logs.tsx` | Database-backed log viewer |

---

**Document Status:** Complete and ready for implementation review.
