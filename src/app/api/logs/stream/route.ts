/**
 * AI Editor 2.0 - Live Logs SSE Stream
 *
 * GET /api/logs/stream
 *   Server-Sent Events endpoint that streams logs from Render API.
 *   Uses server-side caching and exponential backoff to stay within
 *   Render's 30 requests/minute rate limit.
 *
 * Query Parameters:
 *   - stepId: Filter by pipeline step ('0', '1', 'all')
 *   - filter: Time filter ('live', '1h', '12h', '24h')
 *
 * SSE Events:
 *   - data: JSON array of log entries
 *   - error: Error message if fetch fails
 *
 * Rate Limit Strategy:
 *   - Base poll interval: 6 seconds (10 req/min baseline)
 *   - Server-side cache: 5 second TTL shared across all clients
 *   - Exponential backoff on 429 or low remaining quota
 *   - Reads Ratelimit-* headers from Render API
 *
 * Usage:
 *   const eventSource = new EventSource('/api/logs/stream?stepId=all&filter=live');
 *   eventSource.onmessage = (e) => console.log(JSON.parse(e.data));
 */

import { NextRequest } from "next/server";
import {
  getCachedLogs,
  setCachedLogs,
  canFetch,
  markFetchTime,
  markRateLimited,
  clearRateLimit,
  isCurrentlyRateLimited,
  getTimeUntilReset,
  type RenderLog,
} from "@/lib/render-logs-cache";

const RENDER_API_KEY = process.env.RENDER_API_KEY;
const RENDER_API_URL = "https://api.render.com/v1/logs";
// Owner ID required by Render Logs API (team/workspace ID)
const RENDER_OWNER_ID = process.env.RENDER_OWNER_ID || "tea-d4pch32dbo4c73ediu3g";

// Base polling interval: 6 seconds (10 req/min baseline)
const BASE_POLL_INTERVAL_MS = 6000;
// Maximum backoff: 60 seconds
const MAX_POLL_INTERVAL_MS = 60000;

// Service IDs - hardcoded from Render dashboard
// NOTE: Cron jobs use 'crn-' prefix, services use 'srv-'
const SERVICE_IDS = {
  // Core services
  worker: process.env.RENDER_WORKER_SERVICE_ID || "srv-d55i64juibrs7392tcn0",
  trigger: process.env.RENDER_TRIGGER_SERVICE_ID || "srv-d563ffvgi27c73dtqdq0",
  // Pipeline cron jobs (run Ingest -> AI Scoring -> Pre-Filter)
  pipelineNight: process.env.RENDER_PIPELINE_NIGHT_ID || "crn-d5e2shv5r7bs73ca4dp0",
  pipelineMorning: process.env.RENDER_PIPELINE_MORNING_ID || "crn-d5e2sl2li9vc73dt5q40",
  pipelineEod: process.env.RENDER_PIPELINE_EOD_ID || "crn-d5e2smq4d50c73fjo0tg",
};

function getServiceIdsForStep(stepId: string): string[] {
  const ids: string[] = [];

  // Pipeline crons handle ALL steps (Ingest -> AI Scoring -> Pre-Filter)
  // So both Step 0 and Step 1 logs come from the same pipeline crons
  switch (stepId) {
    case "0":
      // Step 0: Ingest + AI Scoring
      // Manual: worker + trigger
      // Automated: pipeline crons
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.trigger) ids.push(SERVICE_IDS.trigger);
      if (SERVICE_IDS.pipelineNight) ids.push(SERVICE_IDS.pipelineNight);
      if (SERVICE_IDS.pipelineMorning) ids.push(SERVICE_IDS.pipelineMorning);
      if (SERVICE_IDS.pipelineEod) ids.push(SERVICE_IDS.pipelineEod);
      break;
    case "1":
      // Step 1: Pre-Filter
      // Manual: worker + trigger
      // Automated: pipeline crons (pre-filter is part of chained pipeline)
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.trigger) ids.push(SERVICE_IDS.trigger);
      if (SERVICE_IDS.pipelineNight) ids.push(SERVICE_IDS.pipelineNight);
      if (SERVICE_IDS.pipelineMorning) ids.push(SERVICE_IDS.pipelineMorning);
      if (SERVICE_IDS.pipelineEod) ids.push(SERVICE_IDS.pipelineEod);
      break;
    case "all":
    default:
      // All services and crons
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.trigger) ids.push(SERVICE_IDS.trigger);
      if (SERVICE_IDS.pipelineNight) ids.push(SERVICE_IDS.pipelineNight);
      if (SERVICE_IDS.pipelineMorning) ids.push(SERVICE_IDS.pipelineMorning);
      if (SERVICE_IDS.pipelineEod) ids.push(SERVICE_IDS.pipelineEod);
      break;
  }

  if (ids.length === 0 && SERVICE_IDS.worker) {
    ids.push(SERVICE_IDS.worker);
  }

  return ids;
}

function getHoursFromFilter(filter: string): number {
  switch (filter) {
    case "live":
      return 0.1; // Last 6 minutes for initial load
    case "1h":
      return 1;
    case "12h":
      return 12;
    case "24h":
      return 24;
    default:
      return 1;
  }
}

interface RenderLogEntry {
  id: string;
  timestamp: string;
  message: string;
  labels: Array<{ name: string; value: string }>;
}

/**
 * Patterns that indicate EXECUTION logs from our pipeline.
 * We use a whitelist approach to ONLY show logs that match these patterns.
 * This filters out HTTP request logs, access logs, build logs, etc.
 */
const EXECUTION_LOG_PATTERNS = [
  // Pipeline orchestration
  /^\[Pipeline\]/i,
  /^\[Step \d/i,
  // Ingest step
  /^\[Ingest/i,
  /^\[FreshRSS/i,
  /^\[Google News/i,
  /^\[Direct Feed/i,
  // AI Scoring
  /^\[AI Scoring/i,
  /^\[Claude/i,
  /^\[Anthropic/i,
  // Pre-filter
  /^\[Pre-?[Ff]ilter/i,
  /^\[Gemini/i,
  /^\[Slot \d/i,
  // Airtable operations
  /^\[Airtable/i,
  // Generic step markers
  /^  (Ingest|Direct Feeds|AI Scoring|Pre-Filter):/i,
  // Summary lines (indented stats)
  /^  → /,
  // Worker messages
  /Worker .+ \[PID/i,
  /^Starting worker/i,
  /^Registering jobs/i,
];

/**
 * Filter to ONLY show execution logs from our pipeline.
 * This uses a whitelist approach - only logs matching our patterns are shown.
 * This filters out: HTTP request logs, access logs, build logs, etc.
 */
function isExecutionLog(message: string): boolean {
  // Empty messages are filtered out
  if (!message || message.trim() === "") return false;

  // Check if it matches any execution pattern (whitelist)
  for (const pattern of EXECUTION_LOG_PATTERNS) {
    if (pattern.test(message)) {
      return true;
    }
  }

  // Does not match any execution pattern - filter it out
  return false;
}

interface FetchResult {
  logs: RenderLog[];
  fromCache: boolean;
  rateLimitRemaining: number;
  wasRateLimited: boolean;
}

// Pagination configuration
const MAX_PAGES = 5; // Maximum pages to fetch to stay under rate limits
const MIN_EXECUTION_LOGS = 50; // Stop fetching once we have this many execution logs
const PAGE_DELAY_MS = 200; // Delay between page requests to avoid rate limits

interface RenderLogsApiResponse {
  logs: RenderLogEntry[];
  hasMore: boolean;
  nextStartTime?: string;
  nextEndTime?: string;
}

/**
 * Fetch logs from Render API with caching, rate limit awareness, and PAGINATION.
 *
 * Key fix: The Render Logs API is time-window paginated. A single request only returns
 * one page of results. We now:
 * 1. Check `hasMore` in the response
 * 2. Use `nextStartTime` and `nextEndTime` to fetch subsequent pages
 * 3. Stop when we have enough execution logs OR no more pages OR hit max pages
 */
async function fetchRenderLogsWithCache(
  serviceIds: string[],
  hours: number,
  limit: number = 100
): Promise<FetchResult> {
  // Check cache first (now includes hours in cache key)
  const cached = getCachedLogs(serviceIds, hours);
  if (cached) {
    return {
      logs: cached.logs,
      fromCache: true,
      rateLimitRemaining: cached.rateLimitRemaining,
      wasRateLimited: false,
    };
  }

  // Check if we're rate limited
  if (isCurrentlyRateLimited()) {
    const waitTime = getTimeUntilReset();
    console.log(`[SSE Stream] Rate limited, ${Math.round(waitTime / 1000)}s until reset`);
    return { logs: [], fromCache: false, rateLimitRemaining: 0, wasRateLimited: true };
  }

  // Check if we can make an API call (respects minimum interval)
  if (!canFetch()) {
    // Return empty if we're locally throttled - use cache next time
    return { logs: [], fromCache: false, rateLimitRemaining: 10, wasRateLimited: false };
  }

  if (!RENDER_API_KEY || serviceIds.length === 0) {
    return { logs: [], fromCache: false, rateLimitRemaining: 30, wasRateLimited: false };
  }

  markFetchTime();

  // Initialize pagination state
  let allLogs: RenderLog[] = [];
  let currentStartTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
  let currentEndTime: string | undefined = undefined;
  let hasMore = true;
  let pageCount = 0;
  let lastRateLimitRemaining = 30;
  let lastRateLimitReset = 0;

  // Pagination loop
  while (hasMore && pageCount < MAX_PAGES) {
    const params = new URLSearchParams();
    params.append("ownerId", RENDER_OWNER_ID);
    serviceIds.forEach((id) => params.append("resource", id));
    params.append("startTime", currentStartTime);
    if (currentEndTime) params.append("endTime", currentEndTime);
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
      lastRateLimitRemaining = parseInt(
        response.headers.get("Ratelimit-Remaining") || "30",
        10
      );
      lastRateLimitReset = parseInt(
        response.headers.get("Ratelimit-Reset") || "0",
        10
      );

      // Handle rate limit
      if (response.status === 429) {
        console.warn(`[SSE Stream] Rate limited by Render API (429) on page ${pageCount + 1}`);
        markRateLimited(lastRateLimitReset || Math.floor(Date.now() / 1000) + 60);
        // Return what we have so far
        break;
      }

      if (!response.ok) {
        const errorText = await response.text();
        console.error("[SSE Stream] Render API error:", response.status, errorText);
        console.error("[SSE Stream] Request URL was:", `${RENDER_API_URL}?${params}`);
        break;
      }

      // Clear rate limit on successful response
      clearRateLimit();

      const data: RenderLogsApiResponse = await response.json();

      // Map and filter logs from this page
      const pageLogs: RenderLog[] = (data.logs || [])
        .map((log: RenderLogEntry) => ({
          id: log.id,
          timestamp: log.timestamp,
          message: log.message,
          level: log.labels.find((l) => l.name === "level")?.value || "info",
          type: log.labels.find((l) => l.name === "type")?.value || "app",
          service: log.labels.find((l) => l.name === "service")?.value || "unknown",
        }))
        .filter((log: RenderLog) => isExecutionLog(log.message));

      // Add to accumulated logs
      allLogs = [...allLogs, ...pageLogs];
      pageCount++;

      console.log(`[SSE Stream] Page ${pageCount}: fetched ${data.logs?.length || 0} raw logs, ${pageLogs.length} execution logs (total: ${allLogs.length})`);

      // Check if we should continue fetching
      hasMore = data.hasMore === true;

      // Stop early if we have enough execution logs
      if (allLogs.length >= MIN_EXECUTION_LOGS) {
        console.log(`[SSE Stream] Stopping pagination: have ${allLogs.length} execution logs (minimum: ${MIN_EXECUTION_LOGS})`);
        hasMore = false;
      }

      // Update pagination cursors for next request
      if (hasMore && data.nextStartTime && data.nextEndTime) {
        currentStartTime = data.nextStartTime;
        currentEndTime = data.nextEndTime;

        // Add delay between page requests to avoid hitting rate limits
        await new Promise(resolve => setTimeout(resolve, PAGE_DELAY_MS));
      } else {
        hasMore = false;
      }

      // Log rate limit warning
      if (lastRateLimitRemaining < 10) {
        console.warn(`[SSE Stream] Low rate limit remaining: ${lastRateLimitRemaining} after page ${pageCount}`);
      }

    } catch (error) {
      console.error(`[SSE Stream] Fetch error on page ${pageCount + 1}:`, error);
      break;
    }
  }

  if (pageCount >= MAX_PAGES) {
    console.log(`[SSE Stream] Reached max pages (${MAX_PAGES}), returning ${allLogs.length} logs`);
  }

  // Cache the results (with hours in key)
  if (allLogs.length > 0) {
    setCachedLogs(serviceIds, allLogs, lastRateLimitRemaining, lastRateLimitReset, hours);
  }

  return {
    logs: allLogs,
    fromCache: false,
    rateLimitRemaining: lastRateLimitRemaining,
    wasRateLimited: false
  };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const stepId = searchParams.get("stepId") || "all";
  const filter = searchParams.get("filter") || "live";

  const serviceIds = getServiceIdsForStep(stepId);
  const encoder = new TextEncoder();

  // Track last seen timestamp to filter duplicates
  let seenIds = new Set<string>();
  let currentPollInterval = BASE_POLL_INTERVAL_MS;
  let consecutiveErrors = 0;

  const stream = new ReadableStream({
    async start(controller) {
      // Check for API key
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

      // Fetch initial logs based on filter
      const initialHours = getHoursFromFilter(filter);
      const initialLimit = filter === "live" ? 50 : 100;

      try {
        const { logs: initialLogs, rateLimitRemaining, wasRateLimited } =
          await fetchRenderLogsWithCache(serviceIds, initialHours, initialLimit);

        // Send initial batch
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(initialLogs)}\n\n`));

        // Track seen IDs
        initialLogs.forEach((log) => seenIds.add(log.id));

        // Adjust poll interval based on initial rate limit
        if (wasRateLimited || rateLimitRemaining < 5) {
          currentPollInterval = Math.min(BASE_POLL_INTERVAL_MS * 3, MAX_POLL_INTERVAL_MS);
        }

        // For non-live views, we're done after initial fetch
        if (filter !== "live") {
          controller.close();
          return;
        }

        // For live view, poll with adaptive interval
        let pollTimeout: NodeJS.Timeout;

        const poll = async () => {
          try {
            // Fetch last 3 minutes of logs
            const { logs: newLogs, fromCache, rateLimitRemaining, wasRateLimited } =
              await fetchRenderLogsWithCache(serviceIds, 0.05, 30);

            // Filter to only truly new logs (not seen before)
            const filteredLogs = newLogs.filter((log) => !seenIds.has(log.id));

            if (filteredLogs.length > 0) {
              // Send new logs
              controller.enqueue(encoder.encode(`data: ${JSON.stringify(filteredLogs)}\n\n`));

              // Update tracking
              filteredLogs.forEach((log) => seenIds.add(log.id));

              // Limit seen IDs set size (keep last 1000)
              if (seenIds.size > 1000) {
                const idsArray = Array.from(seenIds);
                seenIds = new Set(idsArray.slice(-500));
              }
            }

            // Adjust poll interval based on rate limit remaining
            if (wasRateLimited) {
              // We hit a rate limit - back off significantly
              currentPollInterval = Math.min(currentPollInterval * 2, MAX_POLL_INTERVAL_MS);
              consecutiveErrors++;
              console.log(`[SSE Stream] Backing off to ${currentPollInterval}ms after rate limit`);
            } else if (rateLimitRemaining < 5) {
              // Getting close to limit, back off
              currentPollInterval = Math.min(currentPollInterval * 1.5, MAX_POLL_INTERVAL_MS);
              consecutiveErrors++;
              console.log(`[SSE Stream] Low quota (${rateLimitRemaining}), backing off to ${currentPollInterval}ms`);
            } else if (rateLimitRemaining > 20 && consecutiveErrors === 0) {
              // Plenty of headroom, can poll at base rate
              currentPollInterval = BASE_POLL_INTERVAL_MS;
            } else if (!fromCache && rateLimitRemaining > 10) {
              // Gradually recover from backoff
              currentPollInterval = Math.max(
                currentPollInterval * 0.9,
                BASE_POLL_INTERVAL_MS
              );
            }

            // Reset error counter on successful non-cached fetch with good quota
            if (!fromCache && rateLimitRemaining > 10) {
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

        // Start polling
        pollTimeout = setTimeout(poll, currentPollInterval);

        // Cleanup on client disconnect
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
      "X-Accel-Buffering": "no", // Disable nginx buffering
    },
  });
}
