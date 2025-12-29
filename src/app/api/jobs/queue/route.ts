import { NextResponse } from "next/server";

const TRIGGER_SERVICE_URL = process.env.TRIGGER_SERVICE_URL || "https://ai-editor-trigger.onrender.com";
const TRIGGER_SECRET = process.env.TRIGGER_SECRET || "";

export async function GET() {
  try {
    const response = await fetch(`${TRIGGER_SERVICE_URL}/jobs/queue`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${TRIGGER_SECRET}`,
      },
      cache: "no-store",
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || "Failed to get queue status" },
        { status: response.status }
      );
    }

    // Calculate total jobs across all queues
    const totalJobs = Object.values(data.queues as Record<string, { count: number }>)
      .reduce((sum, queue) => sum + queue.count, 0);

    return NextResponse.json({
      ...data,
      totalJobs,
      hasRunningJobs: totalJobs > 0,
    });
  } catch (error) {
    console.error("[Jobs Queue API] Error:", error);
    return NextResponse.json(
      { error: "Failed to get queue status" },
      { status: 500 }
    );
  }
}
