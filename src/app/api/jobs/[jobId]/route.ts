/**
 * AI Editor 2.0 - Job Status API
 *
 * Endpoint:
 *   GET /api/jobs/[jobId] - Get status of a specific job
 */

import { NextRequest, NextResponse } from "next/server";

const TRIGGER_SERVICE_URL = process.env.TRIGGER_SERVICE_URL || "http://localhost:5001";
const TRIGGER_SECRET = process.env.TRIGGER_SECRET || "";

interface JobStatus {
  job_id: string;
  status: "queued" | "started" | "finished" | "failed" | "not_found";
  created_at?: string;
  started_at?: string;
  ended_at?: string;
  result?: Record<string, unknown>;
  error?: string;
}

/**
 * GET /api/jobs/[jobId]
 * Get status of a specific job by ID
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;

  try {
    const response = await fetch(`${TRIGGER_SERVICE_URL}/jobs/status/${jobId}`, {
      headers: {
        ...(TRIGGER_SECRET && { Authorization: `Bearer ${TRIGGER_SECRET}` }),
      },
    });

    const data: JobStatus = await response.json();

    if (!response.ok && response.status !== 404) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error(`[Jobs API] Error getting job ${jobId}:`, error);

    return NextResponse.json(
      {
        job_id: jobId,
        status: "not_found" as const,
        error: "Cannot connect to trigger service",
      },
      { status: 503 }
    );
  }
}
