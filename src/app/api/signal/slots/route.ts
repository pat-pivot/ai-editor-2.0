/**
 * Signal Newsletter - Selected Slots API
 *
 * GET /api/signal/slots - Get the latest Signal issue with selected stories
 *
 * Signal uses a SEPARATE Airtable base from Pivot 5.
 * The slots structure is different:
 *   - top_story (from Slot 1) - TOP STORY
 *   - ai_at_work (from Slot 3) - AI AT WORK
 *   - emerging (from Slot 4) - EMERGING MOVES
 *   - beyond (from Slot 5) - BEYOND BUSINESS
 *   - signals 1-5 (all from Slot 2) - Quick-hit SIGNALS
 */

import { NextRequest, NextResponse } from "next/server";
import { getSignalPendingIssue, getSignalLatestIssue } from "@/lib/airtable";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status");
    const skipCache = searchParams.get("skipCache") === "true";

    let selectedSlots;

    if (status === "pending") {
      // Get only pending issues (ready for processing)
      selectedSlots = await getSignalPendingIssue(skipCache);
    } else {
      // Get the most recent issue (any status)
      selectedSlots = await getSignalLatestIssue(skipCache);
    }

    if (!selectedSlots) {
      return NextResponse.json(
        {
          selectedSlots: null,
          message: status === "pending"
            ? "No pending Signal issues found"
            : "No Signal issues found",
        },
        { status: 200 }
      );
    }

    return NextResponse.json({ selectedSlots });
  } catch (error) {
    console.error("Error fetching Signal selected slots:", error);
    return NextResponse.json(
      { error: "Failed to fetch Signal selected slots" },
      { status: 500 }
    );
  }
}
