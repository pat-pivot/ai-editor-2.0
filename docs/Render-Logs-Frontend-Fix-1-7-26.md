# Render Logs Frontend Fix - January 7, 2026

## Summary

Fixed the AI Editor dashboard to display pipeline execution logs from Render's Logs API, with proper rate limiting, caching, and filtering to show only execution logs (not build logs).

---

## Service Architecture

### Render Services & Cron Jobs

| Service | ID | Type | Purpose |
|---------|-----|------|---------|
| ai-editor-worker | `srv-d55i64juibrs7392tcn0` | Background Worker | Processes RQ jobs |
| ai-editor-trigger | `srv-d563ffvgi27c73dtqdq0` | Web Service | Dashboard + API triggers |
| ai-editor-pipeline-night | `crn-d5e2shv5r7bs73ca4dp0` | Cron Job | 2:00 AM ET pipeline |
| ai-editor-pipeline-morning | `crn-d5e2sl2li9vc73dt5q40` | Cron Job | 9:30 AM ET pipeline |
| ai-editor-pipeline-eod | `crn-d5e2smq4d50c73fjo0tg` | Cron Job | 5:00 PM ET pipeline |

### Key Finding: Pipeline Crons Handle ALL Steps

The pipeline cron jobs execute the **complete chained pipeline**:
- Step 0: Ingest (FreshRSS + Google News)
- Step 0a: Direct Feed Ingest (Reuters, TechCrunch, etc.)
- Step 0.5: AI Scoring (Claude)
- Step 1: Pre-Filter (Gemini, 5 slots)

Therefore, **both Step 0 and Step 1 logs come from the same cron job resources**.

---

## Issues Fixed (Session 1 & 2)

### Issue 1: 429 Rate Limit Errors

**Problem:** Dashboard was hitting Render's 30 req/min rate limit, showing "waiting for logs" errors.

**Root Cause:**
- Multiple SSE connections polling independently
- No server-side caching
- 3-second poll interval too aggressive

**Solution:**
1. Created `src/lib/render-logs-cache.ts` - Server-side in-memory cache
2. 5-second TTL for shared cache across all SSE connections
3. Increased base poll interval from 3s to 6s
4. Exponential backoff when quota runs low

### Issue 2: 400 Bad Request

**Problem:** After fixing rate limits, API returned 400 errors.

**Root Cause:** Render API parameter changes:
- `resource[]` changed to `resource` (no brackets)
- `ownerId` parameter became required

**Solution:**
```typescript
// Before (broken)
params.append("resource[]", serviceId);

// After (working)
params.append("ownerId", RENDER_OWNER_ID);
serviceIds.forEach((id) => params.append("resource", id));
```

### Issue 3: Build Logs Instead of Execution Logs

**Problem:** Logs showed pip install, package downloads instead of pipeline execution.

**Root Cause:** Render's `type` label returns `"app"` for BOTH:
- Build logs: `Using cached google_auth_httplib2-0.3.0-py3-none-any.whl`
- Execution logs: `[Pipeline] ===== PIPELINE COMPLETE =====`

**Solution:** Content-based regex filtering in `src/app/api/logs/stream/route.ts`:

```typescript
const BUILD_LOG_PATTERNS = [
  /^Using cached .+\.whl/i,
  /^Downloading .+\.whl/i,
  /^Collecting [a-z]/i,
  /^Installing collected packages/i,
  /^Successfully installed/i,
  /^Requirement already satisfied/i,
  /^\[notice\] A new release of pip/i,
  /^\[notice\] To update, run: pip install/i,
  /==> (Cloning|Building|Uploading|Build successful|Uploaded)/i,
  /==>\s+\x1b\[\d+m.*?(Cloning|Building|Uploading|Build successful|Uploaded)/i,
  /^npm (WARN|notice|info)/i,
  /^added \d+ packages/i,
  /^Preparing build/i,
  /^Build started/i,
  /^Fetching .* repository/i,
];

function isExecutionLog(message: string): boolean {
  if (!message || message.trim() === "") return true;
  for (const pattern of BUILD_LOG_PATTERNS) {
    if (pattern.test(message)) return false;
  }
  return true;
}
```

---

## Files Modified

| File | Purpose |
|------|---------|
| `src/lib/render-logs-cache.ts` | NEW - Server-side cache module |
| `src/app/api/logs/stream/route.ts` | SSE endpoint with caching, backoff, filtering |
| `src/app/api/logs/render/route.ts` | REST endpoint with same fixes |
| `src/components/step/live-execution-logs.tsx` | Frontend reconnect with backoff |

---

## API Configuration

### Environment Variables

```bash
RENDER_API_KEY=rnd_xxx          # From dashboard.render.com
RENDER_OWNER_ID=tea-d4pch32dbo4c73ediu3g  # Team/workspace ID
```

### Rate Limit Headers

Render returns these headers on each response:
- `Ratelimit-Remaining`: Requests remaining in current window
- `Ratelimit-Reset`: Unix timestamp when limit resets

### Backoff Strategy

```
Base interval: 6 seconds (10 req/min baseline)
Low quota (<5 remaining): interval * 1.5
Rate limited: interval * 2
Max interval: 60 seconds
Recovery: Gradually decrease when quota > 10
```

---

## Execution Log Patterns

Logs we WANT to show (execution):
```
[Pipeline] ===== STARTING FULL PIPELINE =====
[Pipeline] ----- STEP 0: INGEST -----
[Pipeline] → Articles fetched: 280
[Step 1] ========== SLOT 1 START ==========
[Step 1] Slot 1 (Gemini): ✓ SUCCESS - Wrote 39 records
[Airtable] batch_create SUCCESS: 21 records created
```

Logs we FILTER OUT (build):
```
Using cached google_auth_httplib2-0.3.0-py3-none-any.whl
Collecting uritemplate<5,>=3.0.1
Successfully installed anthropic-0.44.0
==> Building...
==> Uploading build...
```

---

## Testing Checklist

- [x] Rate limit errors (429) handled with backoff
- [x] API parameter format updated (resource, ownerId)
- [x] Build logs filtered out
- [x] Execution logs showing correctly
- [x] Deploy verified live on Render

---

## Session 2 Fixes (Same Day)

### Issue 4: HTTP Request Logs Instead of Execution Logs

**Problem:** Dashboard showed HTTP access logs like `GET /jobs/status/...` instead of pipeline execution logs.

**Root Cause:** Blacklist approach filtered build logs but let HTTP request/access logs through.

**Solution:** Changed to **whitelist approach** - ONLY show logs matching execution patterns:

```typescript
const EXECUTION_LOG_PATTERNS = [
  /^\[Pipeline\]/i,
  /^\[Step \d/i,
  /^\[Ingest/i,
  /^\[FreshRSS/i,
  /^\[Google News/i,
  /^\[Direct Feed/i,
  /^\[AI Scoring/i,
  /^\[Claude/i,
  /^\[Pre-?[Ff]ilter/i,
  /^\[Gemini/i,
  /^\[Slot \d/i,
  /^\[Airtable/i,
  /^  (Ingest|Direct Feeds|AI Scoring|Pre-Filter):/i,
  /^  → /,
  /Worker .+ \[PID/i,
  /^Starting worker/i,
  /^Registering jobs/i,
];

function isExecutionLog(message: string): boolean {
  if (!message || message.trim() === "") return false;
  for (const pattern of EXECUTION_LOG_PATTERNS) {
    if (pattern.test(message)) return true;
  }
  return false; // Doesn't match = filter out
}
```

### Issue 5: 24-Hour Timestamp Format

**Problem:** Timestamps showed as "13:08:42" instead of "1:08:42 PM".

**Solution:** Changed `hour12: false` to `hour12: true` in `formatLogTime()`.

---

## Session 3 Investigation (January 8, 2026)

### Reported Issues

1. **"Waiting for logs" when logs should exist** - Dashboard shows empty state even when pipeline has run
2. **Only ~2 runs showing instead of historical data** - Time filters (1h, 12h, 24h) not returning proper history

### Root Cause Analysis

After researching the Render Logs API and reviewing the current implementation, I've identified **two critical bugs**:

#### Bug 1: NO PAGINATION - Only fetching first page of results

**Current Code (route.ts lines 228-237):**
```typescript
const startTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

const params = new URLSearchParams();
params.append("ownerId", RENDER_OWNER_ID);
serviceIds.forEach((id) => params.append("resource", id));
params.append("startTime", startTime);
params.append("limit", limit.toString());  // limit = 50 or 100
params.append("direction", "backward");
```

**Problem:** The Render Logs API is **time-window paginated**. When you request 24 hours of logs:
- Render returns only ONE PAGE of results (up to `limit` entries)
- Response includes `hasMore: true/false`, `nextStartTime`, `nextEndTime`
- **We NEVER check `hasMore` or make follow-up requests**

**Result:** For a 24-hour filter, we're only getting the MOST RECENT ~100 logs, which might be just 1-2 pipeline runs. All older logs within the time window are silently ignored.

#### Bug 2: Aggressive whitelist filtering AFTER pagination truncation

**Current Flow:**
1. Request 24h of logs with limit=100
2. Render returns 100 most recent logs (might span only 2 hours)
3. **Then** we apply whitelist filter (`isExecutionLog()`)
4. If 80 of those 100 logs are HTTP/build logs, we show only 20 execution logs

**Problem:** We filter AFTER fetching, so if the first page is mostly noise, we get very few execution logs. We should either:
- Fetch more pages to accumulate enough execution logs
- OR use Render's `type` filter in the API request (if supported)

#### Bug 3: Cache key doesn't include time filter

**Current Code (render-logs-cache.ts line 40-42):**
```typescript
export function getCacheKey(serviceIds: string[]): string {
  return serviceIds.sort().join(",");
}
```

**Problem:** Cache key is ONLY based on service IDs. If user:
1. Views "Live" (0.1h) -> cache stores ~6 min of logs
2. Switches to "24h" -> cache hit returns same 6 min of logs!

The cache TTL of 5 seconds helps, but there's still a race condition where stale data from a different filter could be served.

### Why "Waiting for logs" appears

1. User selects "24h" filter
2. API fetches first page (limit=100) of last 24 hours
3. Due to `direction: backward`, this is the MOST RECENT 100 logs
4. If there hasn't been a pipeline run in the last few hours, most logs are HTTP requests
5. Whitelist filter removes all HTTP logs
6. Result: 0 execution logs -> "Waiting for logs" displayed
7. **Meanwhile, pipeline runs from 6-12 hours ago exist but are on page 2, 3, 4, etc.**

### Why only ~2 runs show

1. Pipeline runs every ~8 hours (2 AM, 9:30 AM, 5 PM)
2. Each run generates ~200-500 log lines
3. With limit=100 and direction=backward, we get only the most recent logs
4. After whitelist filtering, we're left with logs from just the last 1-2 runs
5. **Older runs within the 24h window are never fetched**

---

## Implementation Plan

### Phase 1: Fix Pagination (Critical)

**File:** `src/app/api/logs/stream/route.ts`

**Changes:**

1. **Add pagination loop to `fetchRenderLogsWithCache()`:**
```typescript
async function fetchRenderLogsWithCache(
  serviceIds: string[],
  hours: number,
  limit: number = 100,
  maxPages: number = 5  // Safety limit to prevent infinite loops
): Promise<FetchResult> {
  // ... existing cache check ...

  let allLogs: RenderLog[] = [];
  let currentStartTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
  let currentEndTime: string | undefined = undefined;
  let hasMore = true;
  let pageCount = 0;

  while (hasMore && pageCount < maxPages) {
    const params = new URLSearchParams();
    params.append("ownerId", RENDER_OWNER_ID);
    serviceIds.forEach((id) => params.append("resource", id));
    params.append("startTime", currentStartTime);
    if (currentEndTime) params.append("endTime", currentEndTime);
    params.append("limit", limit.toString());
    params.append("direction", "backward");

    const response = await fetch(`${RENDER_API_URL}?${params}`, { ... });
    const data = await response.json();

    // Process this page of logs
    const pageLogs = data.logs.map(...).filter(isExecutionLog);
    allLogs = [...allLogs, ...pageLogs];

    // Check pagination
    hasMore = data.hasMore === true;
    if (hasMore && data.nextStartTime && data.nextEndTime) {
      currentStartTime = data.nextStartTime;
      currentEndTime = data.nextEndTime;
    } else {
      hasMore = false;
    }

    pageCount++;

    // Rate limit protection: small delay between pages
    if (hasMore) await new Promise(r => setTimeout(r, 200));
  }

  return { logs: allLogs, ... };
}
```

2. **Adjust page limits by filter:**
```typescript
const PAGE_LIMITS: Record<string, number> = {
  "live": 1,   // Live only needs latest
  "1h": 2,     // 1 hour: up to 2 pages
  "12h": 4,    // 12 hours: up to 4 pages
  "24h": 6,    // 24 hours: up to 6 pages
};
```

### Phase 2: Fix Cache Key

**File:** `src/lib/render-logs-cache.ts`

**Change:**
```typescript
export function getCacheKey(serviceIds: string[], hours: number): string {
  return `${serviceIds.sort().join(",")}_${hours}h`;
}
```

Update all callers to pass the `hours` parameter.

### Phase 3: Optimize Filtering (Optional)

**Option A: Filter during pagination**
- Stop fetching more pages once we have enough execution logs (e.g., 200)
- Prevents over-fetching when recent pages have good data

**Option B: Request type filter from API**
- Check if Render API supports `type=app` filter to exclude request logs at source
- Would reduce payload size and improve performance

### Phase 4: Rate Limit Awareness for Pagination

**Considerations:**
- Current rate limit: 30 req/min
- With 5 services and 6 pages per service = 30 requests for a single 24h load
- **This could exhaust the entire rate limit!**

**Mitigation:**
- Fetch all services in ONE request (current approach, correct)
- But pagination adds multiple requests per filter change
- Add inter-page delay (200ms suggested above)
- Consider reducing maxPages or increasing per-page limit

### Estimated Impact

| Filter | Current Behavior | After Fix |
|--------|-----------------|-----------|
| Live | Works (last 6 min) | No change |
| 1h | ~100 logs, 1-2 runs | ~200 logs, all runs in hour |
| 12h | ~100 logs, 1-2 runs | ~400 logs, all runs in 12h |
| 24h | ~100 logs, 1-2 runs | ~600 logs, all runs in 24h |

---

## Future Improvements (Phase 2)

### 1. Step-Specific Log Filtering

**Goal:** When user selects Step 0 tab, only show logs from Ingest/AI Scoring. When Step 1 tab, only show Pre-Filter logs.

**Implementation Plan:**
```typescript
// Add step-specific patterns
const STEP_0_PATTERNS = [
  /^\[Ingest/i,
  /^\[FreshRSS/i,
  /^\[Google News/i,
  /^\[Direct Feed/i,
  /^\[AI Scoring/i,
  /^\[Claude/i,
];

const STEP_1_PATTERNS = [
  /^\[Pre-?[Ff]ilter/i,
  /^\[Gemini/i,
  /^\[Slot \d/i,
];

function filterLogsByStep(logs: RenderLog[], stepId: string): RenderLog[] {
  if (stepId === "all") return logs;
  const patterns = stepId === "0" ? STEP_0_PATTERNS : STEP_1_PATTERNS;
  return logs.filter(log => patterns.some(p => p.test(log.message)));
}
```

**When to implement:** After confirming whitelist approach works well in production.

### 2. Cron Job Detection
Detect which pipeline cron is currently running and highlight its logs.

### 3. Log Level UI Filtering
Add dropdown to filter by level (info, warn, error) in the frontend.

### 4. Persistent Caching
Consider Redis for cache if running multiple dashboard instances.
