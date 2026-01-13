/**
 * Signal Newsletter - Decorations API
 *
 * GET /api/signal/decorations - Get decorated stories for a Signal issue
 *
 * Query params:
 *   issueId: string - The issue ID to fetch decorations for (required)
 *   skipCache: boolean - Skip Airtable cache (optional, default: false)
 *
 * Signal decorations differ from Pivot 5:
 *   - Full stories have: ai_headline, ai_dek, label, ai_bullet_1/2/3
 *   - SIGNALS (quick-hits) have: ai_headline, signal_summary (2 sentences)
 *   - NO images (unlike Pivot 5)
 *   - NO links in the email body
 */

import { NextRequest, NextResponse } from "next/server";
import { getSignalIssueStories } from "@/lib/airtable";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const issueId = searchParams.get("issueId");
    const skipCache = searchParams.get("skipCache") === "true";

    if (!issueId) {
      return NextResponse.json(
        { error: "issueId query parameter is required" },
        { status: 400 }
      );
    }

    const decorations = await getSignalIssueStories(issueId, skipCache);

    // Group decorations by section type for easier frontend consumption
    const grouped = {
      fullStories: decorations.filter(d =>
        ["top_story", "ai_at_work", "emerging", "beyond"].includes(d.section)
      ),
      signals: decorations.filter(d => d.section === "signal")
        .sort((a, b) => (a.signalNum || 0) - (b.signalNum || 0)),
    };

    return NextResponse.json({
      decorations,
      grouped,
      count: decorations.length,
    });
  } catch (error) {
    console.error("Error fetching Signal decorations:", error);
    return NextResponse.json(
      { error: "Failed to fetch Signal decorations" },
      { status: 500 }
    );
  }
}
