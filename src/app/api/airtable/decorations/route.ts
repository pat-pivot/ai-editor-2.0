/**
 * AI Editor 2.0 - Airtable Decorations API
 *
 * GET /api/airtable/decorations
 *   Returns decorated stories from Newsletter Issue Stories table (tbla16LJCf5Z6cRn3).
 *   Stories are grouped by issue_id and sorted by slot_order.
 *
 * Query Parameters:
 *   - limit: Maximum number of records (default: 100)
 *   - refresh: Set to 'true' to skip cache
 *
 * Returns:
 * {
 *   "decorations": [...],
 *   "uniqueIssueDates": ["Jan 09", "Jan 08", ...],
 *   "total": number
 * }
 */

import { NextRequest, NextResponse } from "next/server";

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AI_EDITOR_BASE_ID = process.env.AI_EDITOR_BASE_ID || "appglKSJZxmA9iHpl";
const DECORATION_TABLE_ID = "tbla16LJCf5Z6cRn3";

interface DecorationEntry {
  id: string;
  storyId: string;
  issueId: string;
  issueDate: string; // Parsed from issue_id like "Pivot 5 - Jan 09"
  slot: number;
  headline: string;
  aiDek: string;
  label: string;
  b1: string;
  b2: string;
  b3: string;
  imageStatus: string;
  imageUrl: string;
  coreUrl: string;
  pivotId: string;
}

interface AirtableRecord {
  id: string;
  fields: Record<string, unknown>;
  createdTime: string;
}

interface AirtableResponse {
  records: AirtableRecord[];
  offset?: string;
}

/**
 * Parse issue date from issue_id format "Pivot 5 - Jan 09"
 */
function parseIssueDate(issueId: string): string {
  if (!issueId) return "";

  // Extract date part after "Pivot 5 - "
  const match = issueId.match(/Pivot 5 - (.+)/);
  if (match) {
    return match[1]; // "Jan 09"
  }

  return issueId;
}

async function fetchDecorations(
  limit: number = 100,
  skipCache: boolean = false
): Promise<{ decorations: DecorationEntry[]; uniqueIssueDates: string[] }> {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY is not set");
  }

  const allRecords: AirtableRecord[] = [];
  let offset: string | undefined;

  do {
    const url = new URL(
      `https://api.airtable.com/v0/${AI_EDITOR_BASE_ID}/${DECORATION_TABLE_ID}`
    );
    url.searchParams.set("pageSize", "100");

    if (offset) {
      url.searchParams.set("offset", offset);
    }

    // Sort by issue_id descending (newest issues first), then by slot_order ascending
    url.searchParams.set("sort[0][field]", "issue_id");
    url.searchParams.set("sort[0][direction]", "desc");
    url.searchParams.set("sort[1][field]", "slot_order");
    url.searchParams.set("sort[1][direction]", "asc");

    // Request required fields - using EXACT field names from documentation
    const fields = [
      "story_id",
      "issue_id",
      "slot_order",
      "headline",
      "ai_dek",
      "label",
      "b1",
      "b2",
      "b3",
      "image_status",
      "image_url",
      "core_url",
      "pivotId",
    ];
    fields.forEach((f) => url.searchParams.append("fields[]", f));

    const response = await fetch(url.toString(), {
      headers: {
        Authorization: `Bearer ${AIRTABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      ...(skipCache
        ? { cache: "no-store" as const }
        : { next: { revalidate: 60 } }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Airtable API error: ${response.status} - ${error}`);
    }

    const data: AirtableResponse = await response.json();
    allRecords.push(...data.records);
    offset = data.offset;

    // Stop if we've reached the limit
    if (allRecords.length >= limit) {
      break;
    }
  } while (offset);

  // Trim to limit
  const records = allRecords.slice(0, limit);

  // Track unique issue dates for pagination
  const issueDateSet = new Set<string>();

  const decorations: DecorationEntry[] = records.map((record) => {
    const fields = record.fields;
    const issueId = (fields.issue_id as string) || "";
    const issueDate = parseIssueDate(issueId);

    if (issueDate) {
      issueDateSet.add(issueDate);
    }

    return {
      id: record.id,
      storyId: (fields.story_id as string) || "",
      issueId,
      issueDate,
      slot: (fields.slot_order as number) || 0,
      headline: (fields.headline as string) || "",
      aiDek: (fields.ai_dek as string) || "",
      label: (fields.label as string) || "",
      b1: (fields.b1 as string) || "",
      b2: (fields.b2 as string) || "",
      b3: (fields.b3 as string) || "",
      imageStatus: (fields.image_status as string) || "needs_image",
      imageUrl: (fields.image_url as string) || "",
      coreUrl: (fields.core_url as string) || "",
      pivotId: (fields.pivotId as string) || "",
    };
  });

  // Convert set to array, sorted with newest dates first
  // Issue dates are like "Jan 09", "Jan 08" - we need to sort chronologically
  const uniqueIssueDates = Array.from(issueDateSet).sort((a, b) => {
    // Parse dates for comparison (assuming current year)
    const currentYear = new Date().getFullYear();
    const dateA = new Date(`${a} ${currentYear}`);
    const dateB = new Date(`${b} ${currentYear}`);
    return dateB.getTime() - dateA.getTime(); // Descending (newest first)
  });

  return { decorations, uniqueIssueDates };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limitParam = searchParams.get("limit");
  const refresh = searchParams.get("refresh") === "true";

  const limit = limitParam ? parseInt(limitParam, 10) : 100;

  try {
    const { decorations, uniqueIssueDates } = await fetchDecorations(
      limit,
      refresh
    );

    return NextResponse.json({
      decorations,
      uniqueIssueDates,
      total: decorations.length,
    });
  } catch (error) {
    console.error("[Airtable Decorations API] Error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    if (errorMessage.includes("not set")) {
      return NextResponse.json({
        decorations: [],
        uniqueIssueDates: [],
        total: 0,
        message: "Airtable not configured. Set AIRTABLE_API_KEY.",
      });
    }

    return NextResponse.json(
      { error: "Failed to fetch decorations", details: errorMessage },
      { status: 500 }
    );
  }
}
