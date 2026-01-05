/**
 * AI Editor 2.0 - Live Logs SSE Stream
 *
 * GET /api/logs/stream
 *   Server-Sent Events endpoint that streams logs from Render API.
 *   Polls Render API every 3 seconds for new logs (within 30/min rate limit).
 *
 * Query Parameters:
 *   - stepId: Filter by pipeline step ('0', '1', 'all')
 *   - filter: Time filter ('live', '1h', '12h', '24h')
 *
 * SSE Events:
 *   - data: JSON array of log entries
 *   - error: Error message if fetch fails
 *
 * Usage:
 *   const eventSource = new EventSource('/api/logs/stream?stepId=all&filter=live');
 *   eventSource.onmessage = (e) => console.log(JSON.parse(e.data));
 */

import { NextRequest } from "next/server";

const RENDER_API_KEY = process.env.RENDER_API_KEY;
const RENDER_API_URL = "https://api.render.com/v1/logs";

// Polling interval in ms (3 seconds = 20 requests/min, well under 30/min limit)
const POLL_INTERVAL_MS = 3000;

// Service IDs - same as render/route.ts
const SERVICE_IDS = {
  worker: process.env.RENDER_WORKER_SERVICE_ID || "srv-d55i64juibrs7392tcn0",
  scheduler: process.env.RENDER_SCHEDULER_SERVICE_ID || "srv-d55i64juibrs7392tcmg",
  trigger: process.env.RENDER_TRIGGER_SERVICE_ID || "srv-d563ffvgi27c73dtqdq0",
  pipelineNight: process.env.RENDER_PIPELINE_NIGHT_ID,
  pipelineMorning: process.env.RENDER_PIPELINE_MORNING_ID,
  pipelineEod: process.env.RENDER_PIPELINE_EOD_ID,
  ingestCron: process.env.RENDER_INGEST_CRON_ID,
  prefilterSlot1: process.env.RENDER_PREFILTER_SLOT1_ID,
  prefilterSlot2: process.env.RENDER_PREFILTER_SLOT2_ID,
  prefilterSlot3: process.env.RENDER_PREFILTER_SLOT3_ID,
  prefilterSlot4: process.env.RENDER_PREFILTER_SLOT4_ID,
  prefilterSlot5: process.env.RENDER_PREFILTER_SLOT5_ID,
};

function getServiceIdsForStep(stepId: string): string[] {
  const ids: string[] = [];

  switch (stepId) {
    case "0":
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.trigger) ids.push(SERVICE_IDS.trigger);
      if (SERVICE_IDS.ingestCron) ids.push(SERVICE_IDS.ingestCron);
      break;
    case "1":
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.prefilterSlot1) ids.push(SERVICE_IDS.prefilterSlot1);
      if (SERVICE_IDS.prefilterSlot2) ids.push(SERVICE_IDS.prefilterSlot2);
      if (SERVICE_IDS.prefilterSlot3) ids.push(SERVICE_IDS.prefilterSlot3);
      if (SERVICE_IDS.prefilterSlot4) ids.push(SERVICE_IDS.prefilterSlot4);
      if (SERVICE_IDS.prefilterSlot5) ids.push(SERVICE_IDS.prefilterSlot5);
      break;
    case "all":
    default:
      if (SERVICE_IDS.worker) ids.push(SERVICE_IDS.worker);
      if (SERVICE_IDS.trigger) ids.push(SERVICE_IDS.trigger);
      if (SERVICE_IDS.scheduler) ids.push(SERVICE_IDS.scheduler);
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

async function fetchRenderLogs(
  serviceIds: string[],
  hours: number,
  limit: number = 50
): Promise<Array<{
  id: string;
  timestamp: string;
  message: string;
  level: string;
  type: string;
  service: string;
}>> {
  if (!RENDER_API_KEY || serviceIds.length === 0) {
    return [];
  }

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

    if (!response.ok) {
      console.error("[SSE Stream] Render API error:", response.status);
      return [];
    }

    const data = await response.json();

    return data.logs.map((log: RenderLogEntry) => ({
      id: log.id,
      timestamp: log.timestamp,
      message: log.message,
      level: log.labels.find((l) => l.name === "level")?.value || "info",
      type: log.labels.find((l) => l.name === "type")?.value || "app",
      service: log.labels.find((l) => l.name === "service")?.value || "unknown",
    }));
  } catch (error) {
    console.error("[SSE Stream] Fetch error:", error);
    return [];
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const stepId = searchParams.get("stepId") || "all";
  const filter = searchParams.get("filter") || "live";

  const serviceIds = getServiceIdsForStep(stepId);
  const encoder = new TextEncoder();

  // Track last seen timestamp to filter duplicates
  let lastTimestamp: string | null = null;
  let seenIds = new Set<string>();

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
        const initialLogs = await fetchRenderLogs(serviceIds, initialHours, initialLimit);

        // Send initial batch
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(initialLogs)}\n\n`));

        // Track seen IDs and last timestamp
        initialLogs.forEach((log) => seenIds.add(log.id));
        if (initialLogs.length > 0) {
          lastTimestamp = initialLogs[0].timestamp; // Most recent (backward order)
        }

        // For non-live views, we're done after initial fetch
        if (filter !== "live") {
          controller.close();
          return;
        }

        // For live view, poll every 3 seconds
        const pollInterval = setInterval(async () => {
          try {
            // Fetch last 3 minutes of logs
            const newLogs = await fetchRenderLogs(serviceIds, 0.05, 30);

            // Filter to only truly new logs (not seen before)
            const filteredLogs = newLogs.filter((log) => !seenIds.has(log.id));

            if (filteredLogs.length > 0) {
              // Send new logs
              controller.enqueue(encoder.encode(`data: ${JSON.stringify(filteredLogs)}\n\n`));

              // Update tracking
              filteredLogs.forEach((log) => seenIds.add(log.id));
              lastTimestamp = filteredLogs[0].timestamp;

              // Limit seen IDs set size (keep last 1000)
              if (seenIds.size > 1000) {
                const idsArray = Array.from(seenIds);
                seenIds = new Set(idsArray.slice(-500));
              }
            }
          } catch (error) {
            console.error("[SSE Stream] Poll error:", error);
            // Don't close stream on poll error, just skip this interval
          }
        }, POLL_INTERVAL_MS);

        // Cleanup on client disconnect
        request.signal.addEventListener("abort", () => {
          clearInterval(pollInterval);
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
