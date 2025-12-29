import { NextRequest, NextResponse } from "next/server";

const TRIGGER_SERVICE_URL = process.env.TRIGGER_SERVICE_URL || "https://ai-editor-trigger.onrender.com";
const TRIGGER_SECRET = process.env.TRIGGER_SECRET || "";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const { jobId } = body;

    // If jobId is provided, cancel specific job; otherwise cancel all
    const endpoint = jobId
      ? `${TRIGGER_SERVICE_URL}/jobs/cancel/${jobId}`
      : `${TRIGGER_SERVICE_URL}/jobs/cancel-all`;

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${TRIGGER_SECRET}`,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || "Failed to cancel job(s)" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("[Jobs Cancel API] Error:", error);
    return NextResponse.json(
      { error: "Failed to cancel job(s)" },
      { status: 500 }
    );
  }
}
