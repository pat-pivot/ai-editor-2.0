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

## Issues Fixed

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

## Future Improvements

1. **Step-specific filtering**: Parse log prefixes (`[Step 0]`, `[Step 1]`) to show only logs for selected step
2. **Cron job detection**: Detect which cron is currently running and focus on that resource
3. **Log level filtering**: Allow filtering by level (info, warn, error)
4. **Persistent caching**: Consider Redis for cache if multiple dashboard instances
