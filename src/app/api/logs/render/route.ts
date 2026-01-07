/**
 * AI Editor 2.0 - Render Logs API
 *
 * GET /api/logs/render
 *   Fetches logs directly from Render's Logs API for AI Editor services.
 *   Provides real-time visibility into pipeline execution without custom DB logging.
 *   Uses server-side caching to respect Render's 30 req/min rate limit.
 *
 * Query Parameters:
 *   - stepId: Filter by pipeline step ('0' for ingest/scoring, '1' for pre-filter, 'all' for everything)
 *   - hours: Time range in hours (default: 1, max: 24)
 *   - level: Filter by log level ('info', 'warn', 'error', 'debug')
 *   - limit: Maximum number of logs to return (default: 100, max: 500)
 *
 * Environment Variables Required:
 *   - RENDER_API_KEY: Render API key from dashboard.render.com
 *
 * Returns:
 * {
 *   "logs": [
 *     {
 *       "id": "log-xxx",
 *       "timestamp": "2025-01-05T14:30:00Z",
 *       "message": "[Pipeline] Starting full pipeline...",
 *       "level": "info",
 *       "type": "app",
 *       "service": "ai-editor-worker"
 *     }
 *   ],
 *   "hasMore": false,
 *   "nextEndTime": null,
 *   "rateLimitInfo": { "remaining": 25, "resetAt": 1704654120 }
 * }
 */

import { NextRequest, NextResponse } from "next/server";
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

// Map step IDs to relevant Render services
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

  // Fallback to worker if no specific services configured
  if (ids.length === 0 && SERVICE_IDS.worker) {
    ids.push(SERVICE_IDS.worker);
  }

  return ids;
}

interface RenderLogLabel {
  name: string;
  value: string;
}

interface RenderLogEntry {
  id: string;
  timestamp: string;
  message: string;
  labels: RenderLogLabel[];
}

interface RenderLogsResponse {
  logs: RenderLogEntry[];
  hasMore: boolean;
  nextEndTime?: string;
  nextStartTime?: string;
}

export async function GET(request: NextRequest) {
  // Check for API key
  if (!RENDER_API_KEY) {
    return NextResponse.json(
      {
        error: "Render API not configured",
        message: "Set RENDER_API_KEY environment variable to enable live logs.",
        logs: [],
      },
      { status: 503 }
    );
  }

  const { searchParams } = new URL(request.url);
  const stepId = searchParams.get("stepId") || "all";
  const hoursParam = searchParams.get("hours") || "1";
  const level = searchParams.get("level");
  const limitParam = searchParams.get("limit") || "100";

  const hours = Math.min(Math.max(parseFloat(hoursParam), 0.1), 24);
  const limit = Math.min(Math.max(parseInt(limitParam, 10), 1), 500);

  const serviceIds = getServiceIdsForStep(stepId);

  if (serviceIds.length === 0) {
    return NextResponse.json({
      logs: [],
      message: "No service IDs configured for this step. Add RENDER_*_SERVICE_ID env vars.",
      hasMore: false,
    });
  }

  // Check if we're currently rate limited
  if (isCurrentlyRateLimited()) {
    const waitTime = getTimeUntilReset();
    return NextResponse.json(
      {
        error: "Rate limited by Render API",
        message: `Please wait ${Math.ceil(waitTime / 1000)} seconds before retrying.`,
        logs: [],
        retryAfter: Math.ceil(waitTime / 1000),
      },
      {
        status: 429,
        headers: {
          "Retry-After": Math.ceil(waitTime / 1000).toString(),
        },
      }
    );
  }

  // Check cache first
  const cached = getCachedLogs(serviceIds);
  if (cached) {
    // Transform cached logs to include instance field
    const logs = cached.logs.map((log) => ({
      ...log,
      instance: undefined, // Instance info not stored in cache
    }));

    return NextResponse.json({
      logs,
      hasMore: false,
      fromCache: true,
      rateLimitInfo: {
        remaining: cached.rateLimitRemaining,
        resetAt: cached.rateLimitReset,
      },
      serviceIds,
      query: {
        stepId,
        hours,
        level,
        limit,
      },
    });
  }

  // Check if we can make an API call
  if (!canFetch()) {
    return NextResponse.json(
      {
        error: "Too many requests",
        message: "Please wait a moment before fetching logs again.",
        logs: [],
      },
      { status: 429 }
    );
  }

  markFetchTime();

  const startTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

  try {
    // Build query params for Render API
    const params = new URLSearchParams();
    // Render API requires ownerId parameter
    params.append("ownerId", RENDER_OWNER_ID);
    // Render API uses "resource" (not "resource[]") for array parameters
    serviceIds.forEach((id) => params.append("resource", id));
    params.append("startTime", startTime);
    params.append("limit", limit.toString());
    params.append("direction", "backward"); // Most recent first
    if (level) params.append("level", level);

    const response = await fetch(`${RENDER_API_URL}?${params}`, {
      headers: {
        Authorization: `Bearer ${RENDER_API_KEY}`,
        Accept: "application/json",
      },
    });

    // Extract rate limit headers
    const rateLimitRemaining = parseInt(
      response.headers.get("Ratelimit-Remaining") || "30",
      10
    );
    const rateLimitReset = parseInt(
      response.headers.get("Ratelimit-Reset") || "0",
      10
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[Render Logs API] Error from Render:", response.status, errorText);

      if (response.status === 401) {
        return NextResponse.json(
          { error: "Invalid Render API key", logs: [] },
          { status: 401 }
        );
      }
      if (response.status === 429) {
        // Mark rate limited in cache
        markRateLimited(rateLimitReset || Math.floor(Date.now() / 1000) + 60);
        const waitTime = getTimeUntilReset();

        return NextResponse.json(
          {
            error: "Rate limited by Render API",
            message: `Please wait ${Math.ceil(waitTime / 1000)} seconds before retrying.`,
            logs: [],
            retryAfter: Math.ceil(waitTime / 1000),
          },
          {
            status: 429,
            headers: {
              "Retry-After": Math.ceil(waitTime / 1000).toString(),
            },
          }
        );
      }

      return NextResponse.json(
        { error: `Render API error: ${response.status}`, logs: [] },
        { status: response.status }
      );
    }

    // Clear rate limit on success
    clearRateLimit();

    const data: RenderLogsResponse = await response.json();

    // Transform Render logs to our simpler format
    const logs = data.logs.map((log) => ({
      id: log.id,
      timestamp: log.timestamp,
      message: log.message,
      level: log.labels.find((l) => l.name === "level")?.value || "info",
      type: log.labels.find((l) => l.name === "type")?.value || "app",
      service: log.labels.find((l) => l.name === "service")?.value || "unknown",
      instance: log.labels.find((l) => l.name === "instance")?.value,
    }));

    // Cache the results (without instance field for cache)
    const logsForCache: RenderLog[] = logs.map((log) => ({
      id: log.id,
      timestamp: log.timestamp,
      message: log.message,
      level: log.level,
      type: log.type,
      service: log.service,
    }));
    setCachedLogs(serviceIds, logsForCache, rateLimitRemaining, rateLimitReset);

    // Log warning if running low on quota
    if (rateLimitRemaining < 10) {
      console.warn(`[Render Logs API] Low rate limit remaining: ${rateLimitRemaining}`);
    }

    return NextResponse.json({
      logs,
      hasMore: data.hasMore,
      nextEndTime: data.nextEndTime,
      rateLimitInfo: {
        remaining: rateLimitRemaining,
        resetAt: rateLimitReset,
      },
      serviceIds,
      query: {
        stepId,
        hours,
        level,
        limit,
      },
    });
  } catch (error) {
    console.error("[Render Logs API] Error:", error);
    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      { error: "Failed to fetch Render logs", details: errorMessage, logs: [] },
      { status: 500 }
    );
  }
}
