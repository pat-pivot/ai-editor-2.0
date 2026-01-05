/**
 * AI Editor 2.0 - Last Run API
 *
 * GET /api/jobs/last-run?step=<step_name>
 *   Returns the last execution info for a pipeline step
 *
 * Returns:
 * {
 *   "step": "ingest",
 *   "last_run": {
 *     "timestamp": "2025-01-05T14:30:00Z",
 *     "duration_seconds": 102,
 *     "status": "success" | "failed",
 *     "result": { ... }
 *   }
 * }
 */

import { NextRequest, NextResponse } from "next/server";

const TRIGGER_SERVICE_URL = process.env.TRIGGER_SERVICE_URL || "http://localhost:5001";
const TRIGGER_SECRET = process.env.TRIGGER_SECRET || "";

// Step name to numeric ID mapping
const STEP_NAME_TO_ID: Record<string, number> = {
  "ingest": 0,
  "ingest_sandbox": 0,
  "ai_scoring": 0,
  "ai_scoring_sandbox": 0,
  "prefilter": 1,
  "prefilter_slot_1": 1,
  "prefilter_slot_2": 1,
  "prefilter_slot_3": 1,
  "prefilter_slot_4": 1,
  "prefilter_slot_5": 1,
  "slot_selection": 2,
  "decoration": 3,
  "images": 3,
  "html_compile": 4,
  "mautic_send": 5,
  "social_sync": 5,
};

interface LastRunInfo {
  timestamp: string;
  duration_seconds: number;
  status: "success" | "failed" | "running";
  result?: Record<string, unknown>;
  job_id?: string;
}

interface LastRunResponse {
  step: string;
  step_id: number;
  last_run: LastRunInfo | null;
}

/**
 * GET /api/jobs/last-run
 * Get last run info for a specific step
 *
 * Query params:
 *   step: Step name (e.g., "ingest", "prefilter")
 *   step_id: Numeric step ID (0-5) - alternative to step name
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const stepName = searchParams.get("step");
  const stepIdParam = searchParams.get("step_id");

  // Determine step name and ID
  let step: string;
  let stepId: number;

  if (stepIdParam !== null) {
    stepId = parseInt(stepIdParam, 10);
    // Find corresponding step name
    const entry = Object.entries(STEP_NAME_TO_ID).find(([_, id]) => id === stepId);
    step = entry?.[0] || `step_${stepId}`;
  } else if (stepName) {
    step = stepName;
    stepId = STEP_NAME_TO_ID[stepName] ?? -1;
  } else {
    return NextResponse.json(
      { error: "Missing step or step_id parameter" },
      { status: 400 }
    );
  }

  try {
    // Try to fetch last run from trigger service
    const response = await fetch(`${TRIGGER_SERVICE_URL}/jobs/history?step=${step}&limit=1`, {
      headers: {
        ...(TRIGGER_SECRET && { Authorization: `Bearer ${TRIGGER_SECRET}` }),
      },
    });

    if (response.ok) {
      const data = await response.json();

      if (data.jobs && data.jobs.length > 0) {
        const lastJob = data.jobs[0];

        const lastRunInfo: LastRunInfo = {
          timestamp: lastJob.finished_at || lastJob.started_at || lastJob.created_at,
          duration_seconds: lastJob.duration_seconds || 0,
          status: lastJob.status === "finished" ? "success" : lastJob.status === "failed" ? "failed" : "running",
          result: lastJob.result,
          job_id: lastJob.id,
        };

        return NextResponse.json({
          step,
          step_id: stepId,
          last_run: lastRunInfo,
        } satisfies LastRunResponse);
      }
    }

    // If trigger service doesn't have history endpoint or no results, return null
    return NextResponse.json({
      step,
      step_id: stepId,
      last_run: null,
    } satisfies LastRunResponse);
  } catch (error) {
    console.error("[Last Run API] Error fetching last run:", error);

    // Return null if service is unavailable (graceful degradation)
    return NextResponse.json({
      step,
      step_id: stepId,
      last_run: null,
    } satisfies LastRunResponse);
  }
}
