/**
 * AI Editor 2.0 - Render Logs API
 *
 * GET /api/logs/render
 *   Fetches logs directly from Render's Logs API for AI Editor services.
 *   Provides real-time visibility into pipeline execution without custom DB logging.
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
 *   "nextEndTime": null
 * }
 */

import { NextRequest, NextResponse } from "next/server";

const RENDER_API_KEY = process.env.RENDER_API_KEY;
const RENDER_API_URL = "https://api.render.com/v1/logs";

// Service IDs for AI Editor components
// These will be populated once the new cron jobs are deployed
const SERVICE_IDS = {
  // Existing services
  worker: process.env.RENDER_WORKER_SERVICE_ID || "srv-d55i64juibrs7392tcn0",
  scheduler: process.env.RENDER_SCHEDULER_SERVICE_ID || "srv-d55i64juibrs7392tcmg",
  trigger: process.env.RENDER_TRIGGER_SERVICE_ID || "srv-d563ffvgi27c73dtqdq0",
  // Pipeline cron jobs (to be added after render.yaml deployment)
  pipelineNight: process.env.RENDER_PIPELINE_NIGHT_ID,
  pipelineMorning: process.env.RENDER_PIPELINE_MORNING_ID,
  pipelineEod: process.env.RENDER_PIPELINE_EOD_ID,
  // Individual cron jobs (current architecture)
  ingestCron: process.env.RENDER_INGEST_CRON_ID,
  prefilterSlot1: process.env.RENDER_PREFILTER_SLOT1_ID,
  prefilterSlot2: process.env.RENDER_PREFILTER_SLOT2_ID,
  prefilterSlot3: process.env.RENDER_PREFILTER_SLOT3_ID,
  prefilterSlot4: process.env.RENDER_PREFILTER_SLOT4_ID,
  prefilterSlot5: process.env.RENDER_PREFILTER_SLOT5_ID,
};

// Map step IDs to relevant Render services
function getServiceIdsForStep(stepId: string): string[] {
  const ids: string[] = [];

  switch (stepId) {
    case "0":
      // Step 0: Ingest + AI Scoring (runs on worker or trigger)
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.trigger) ids.push(SERVICE_IDS.trigger);
      if (SERVICE_IDS.ingestCron) ids.push(SERVICE_IDS.ingestCron);
      break;

    case "1":
      // Step 1: Pre-Filter (runs on worker or individual slot crons)
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.prefilterSlot1) ids.push(SERVICE_IDS.prefilterSlot1);
      if (SERVICE_IDS.prefilterSlot2) ids.push(SERVICE_IDS.prefilterSlot2);
      if (SERVICE_IDS.prefilterSlot3) ids.push(SERVICE_IDS.prefilterSlot3);
      if (SERVICE_IDS.prefilterSlot4) ids.push(SERVICE_IDS.prefilterSlot4);
      if (SERVICE_IDS.prefilterSlot5) ids.push(SERVICE_IDS.prefilterSlot5);
      break;

    case "all":
    default:
      // All services - for pipeline view
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.trigger) ids.push(SERVICE_IDS.trigger);
      if (SERVICE_IDS.scheduler) ids.push(SERVICE_IDS.scheduler);
      // Add pipeline crons if configured
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

  const startTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

  try {
    // Build query params for Render API
    const params = new URLSearchParams();
    serviceIds.forEach((id) => params.append("resource[]", id));
    params.append("startTime", startTime);
    params.append("limit", limit.toString());
    params.append("direction", "backward"); // Most recent first
    if (level) params.append("level[]", level);

    const response = await fetch(`${RENDER_API_URL}?${params}`, {
      headers: {
        Authorization: `Bearer ${RENDER_API_KEY}`,
        Accept: "application/json",
      },
      // Cache for 5 seconds to reduce API calls
      next: { revalidate: 5 },
    });

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
        return NextResponse.json(
          { error: "Rate limited by Render API. Try again in a minute.", logs: [] },
          { status: 429 }
        );
      }

      return NextResponse.json(
        { error: `Render API error: ${response.status}`, logs: [] },
        { status: response.status }
      );
    }

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

    return NextResponse.json({
      logs,
      hasMore: data.hasMore,
      nextEndTime: data.nextEndTime,
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
