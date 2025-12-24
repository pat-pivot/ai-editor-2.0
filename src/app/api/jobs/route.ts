/**
 * AI Editor 2.0 - Jobs API
 *
 * Endpoints:
 *   POST /api/jobs        - Trigger a pipeline step
 *   GET /api/jobs         - Get queue status
 *   GET /api/jobs/status  - Get specific job status by ID
 *
 * Environment:
 *   TRIGGER_SERVICE_URL: URL of the Python trigger service
 *   TRIGGER_SECRET: Shared secret for authentication
 */

import { NextRequest, NextResponse } from "next/server";

const TRIGGER_SERVICE_URL = process.env.TRIGGER_SERVICE_URL || "http://localhost:5001";
const TRIGGER_SECRET = process.env.TRIGGER_SECRET || "";

// Valid step names that can be triggered
const VALID_STEPS = [
  "prefilter",
  "slot_selection",
  "decoration",
  "images",
  "html_compile",
  "mautic_send",
  "social_sync",
] as const;

type StepName = (typeof VALID_STEPS)[number];

interface TriggerResponse {
  success: boolean;
  job_id?: string;
  step?: string;
  queue?: string;
  enqueued_at?: string;
  error?: string;
}

interface QueueStatus {
  queues: {
    [key: string]: {
      count: number;
      jobs: Array<{
        id: string;
        func_name: string;
        status: string;
        created_at: string;
      }>;
    };
  };
}

/**
 * POST /api/jobs
 * Trigger a specific pipeline step
 *
 * Request Body:
 * {
 *   "step": "prefilter" | "slot_selection" | "decoration" | "images" | "html_compile" | "mautic_send" | "social_sync",
 *   "params": { ... optional parameters ... }
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { step, params = {} } = body as { step: string; params?: Record<string, unknown> };

    // Validate step name
    if (!step || !VALID_STEPS.includes(step as StepName)) {
      return NextResponse.json(
        {
          success: false,
          error: `Invalid step: ${step}`,
          valid_steps: VALID_STEPS,
        },
        { status: 400 }
      );
    }

    // Call Python trigger service
    const triggerUrl = `${TRIGGER_SERVICE_URL}/jobs/${step}`;
    console.log(`[Jobs API] Triggering ${step} at ${triggerUrl}`);

    const response = await fetch(triggerUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(TRIGGER_SECRET && { Authorization: `Bearer ${TRIGGER_SECRET}` }),
      },
      body: JSON.stringify(params),
    });

    const data: TriggerResponse = await response.json();

    if (!response.ok) {
      console.error(`[Jobs API] Trigger failed: ${JSON.stringify(data)}`);
      return NextResponse.json(data, { status: response.status });
    }

    console.log(`[Jobs API] Job ${data.job_id} enqueued for step ${step}`);
    return NextResponse.json(data);
  } catch (error) {
    console.error("[Jobs API] Error:", error);

    // Check if it's a connection error
    if (error instanceof TypeError && error.message.includes("fetch")) {
      return NextResponse.json(
        {
          success: false,
          error: "Cannot connect to trigger service",
          details: "The Python trigger service may not be running",
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

/**
 * GET /api/jobs
 * Get queue status
 */
export async function GET() {
  try {
    const response = await fetch(`${TRIGGER_SERVICE_URL}/jobs/queue`, {
      headers: {
        ...(TRIGGER_SECRET && { Authorization: `Bearer ${TRIGGER_SECRET}` }),
      },
    });

    const data: QueueStatus = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("[Jobs API] Error getting queue status:", error);

    return NextResponse.json(
      {
        success: false,
        error: "Cannot connect to trigger service",
        queues: {
          high: { count: 0, jobs: [] },
          default: { count: 0, jobs: [] },
          low: { count: 0, jobs: [] },
        },
      },
      { status: 503 }
    );
  }
}
