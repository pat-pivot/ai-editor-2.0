/**
 * Newsletter Schedule API
 *
 * POST /api/newsletter/schedule
 * Schedules a newsletter to be sent via Mautic at a specific time
 *
 * Request Body:
 * {
 *   "issue_id": "string",
 *   "record_id": "string",
 *   "scheduled_time": "ISO 8601 datetime string"
 * }
 *
 * Response:
 * {
 *   "success": true,
 *   "scheduled_time": "ISO 8601 datetime string",
 *   "issue_id": "string"
 * }
 */

import { NextRequest, NextResponse } from "next/server";

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AI_EDITOR_BASE_ID = process.env.AI_EDITOR_BASE_ID || "appglKSJZxmA9iHpl";
const NEWSLETTER_ISSUES_FINAL_TABLE = "tblPBfWZzRdLuiqYr";

// For triggering the mautic_send job
const TRIGGER_SERVICE_URL = process.env.TRIGGER_SERVICE_URL || "http://localhost:5001";
const TRIGGER_SECRET = process.env.TRIGGER_SECRET || "";

async function updateAirtable(
  baseId: string,
  tableId: string,
  recordId: string,
  fields: Record<string, unknown>
): Promise<void> {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY is not set");
  }

  const url = `https://api.airtable.com/v0/${baseId}/${tableId}/${recordId}`;

  const response = await fetch(url, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${AIRTABLE_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Airtable API error: ${response.status} - ${error}`);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { issue_id, record_id, scheduled_time } = body;

    // Validate required fields
    if (!record_id) {
      return NextResponse.json(
        { error: "record_id is required" },
        { status: 400 }
      );
    }

    if (!scheduled_time) {
      return NextResponse.json(
        { error: "scheduled_time is required" },
        { status: 400 }
      );
    }

    // Parse and validate the scheduled time
    const scheduledDate = new Date(scheduled_time);
    if (isNaN(scheduledDate.getTime())) {
      return NextResponse.json(
        { error: "Invalid scheduled_time format" },
        { status: 400 }
      );
    }

    // Ensure the scheduled time is in the future
    const now = new Date();
    if (scheduledDate <= now) {
      return NextResponse.json(
        { error: "Scheduled time must be in the future" },
        { status: 400 }
      );
    }

    // Update Airtable with scheduled status and time
    await updateAirtable(AI_EDITOR_BASE_ID, NEWSLETTER_ISSUES_FINAL_TABLE, record_id, {
      status: "scheduled",
      scheduled_send_time: scheduledDate.toISOString(),
      scheduled_at: now.toISOString(),
    });

    console.log(`[Newsletter Schedule API] Scheduled newsletter ${issue_id} for ${scheduledDate.toISOString()}`);

    // Note: The actual Mautic scheduling would be triggered by a cron job
    // that checks for scheduled newsletters and sends them at the appropriate time.
    // This API just updates the status in Airtable.

    return NextResponse.json({
      success: true,
      scheduled_time: scheduledDate.toISOString(),
      issue_id: issue_id,
      message: `Newsletter scheduled for ${scheduledDate.toLocaleString("en-US", {
        timeZone: "America/New_York",
        dateStyle: "full",
        timeStyle: "short",
      })} ET`,
    });
  } catch (error) {
    console.error("[Newsletter Schedule API] Error:", error);

    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Failed to schedule newsletter",
      },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/newsletter/schedule
 * Cancels a scheduled newsletter
 *
 * Request Body:
 * {
 *   "record_id": "string"
 * }
 */
export async function DELETE(request: NextRequest) {
  try {
    const body = await request.json();
    const { record_id } = body;

    if (!record_id) {
      return NextResponse.json(
        { error: "record_id is required" },
        { status: 400 }
      );
    }

    // Update Airtable to remove scheduling
    await updateAirtable(AI_EDITOR_BASE_ID, NEWSLETTER_ISSUES_FINAL_TABLE, record_id, {
      status: "next-send",
      scheduled_send_time: null,
      scheduled_at: null,
    });

    console.log(`[Newsletter Schedule API] Cancelled scheduling for record ${record_id}`);

    return NextResponse.json({
      success: true,
      message: "Newsletter scheduling cancelled",
    });
  } catch (error) {
    console.error("[Newsletter Schedule API] Error:", error);

    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Failed to cancel scheduling",
      },
      { status: 500 }
    );
  }
}
