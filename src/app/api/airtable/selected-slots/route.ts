/**
 * AI Editor 2.0 - Airtable Selected Slots API
 *
 * GET /api/airtable/selected-slots
 *   Returns selected slots issues from AI Editor Selected Slots table.
 *   Issues are sorted by issue_date DESC (newest first).
 *
 * Query Parameters:
 *   - limit: Maximum number of issues (default: 10)
 *   - refresh: Set to 'true' to skip cache
 *
 * PATCH /api/airtable/selected-slots
 *   Updates the subject_line field for a specific record.
 *
 * Body:
 *   - recordId: Airtable record ID
 *   - subject_line: New subject line value
 */

import { NextRequest, NextResponse } from "next/server";

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AI_EDITOR_BASE_ID = process.env.AI_EDITOR_BASE_ID || "appglKSJZxmA9iHpl";
const SELECTED_SLOTS_TABLE_ID = "tblzt2z7r512Kto3O";

interface SlotData {
  slot: number;
  headline: string;
  storyId: string;
  pivotId: string;
  source: string;
}

interface SelectedSlotsIssue {
  id: string;
  issueId: number;
  issueDate: string;
  subjectLine: string;
  status: string;
  slots: SlotData[];
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

async function fetchSelectedSlots(
  limit: number = 10,
  skipCache: boolean = false
): Promise<SelectedSlotsIssue[]> {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY is not set");
  }

  const url = new URL(
    `https://api.airtable.com/v0/${AI_EDITOR_BASE_ID}/${SELECTED_SLOTS_TABLE_ID}`
  );
  url.searchParams.set("pageSize", "100");
  url.searchParams.set("maxRecords", String(limit));
  url.searchParams.set("sort[0][field]", "issue_date");
  url.searchParams.set("sort[0][direction]", "desc");

  // Request all slot fields
  // Note: slot_X_source fields don't exist in Airtable (see slot_selection.py line 356)
  const fields = [
    "issue_id",
    "issue_date",
    "subject_line",
    "status",
    "slot_1_storyId",
    "slot_1_pivotId",
    "slot_1_headline",
    "slot_2_storyId",
    "slot_2_pivotId",
    "slot_2_headline",
    "slot_3_storyId",
    "slot_3_pivotId",
    "slot_3_headline",
    "slot_4_storyId",
    "slot_4_pivotId",
    "slot_4_headline",
    "slot_5_storyId",
    "slot_5_pivotId",
    "slot_5_headline",
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

  return data.records.map((record) => {
    const fields = record.fields;

    // Build slots array from individual slot fields
    // Note: source field doesn't exist in Airtable Selected Slots table
    const slots: SlotData[] = [];
    for (let i = 1; i <= 5; i++) {
      const headline = (fields[`slot_${i}_headline`] as string) || "";
      const storyId = (fields[`slot_${i}_storyId`] as string) || "";
      const pivotId = (fields[`slot_${i}_pivotId`] as string) || "";

      // Only add slot if it has at least a headline or storyId
      if (headline || storyId) {
        slots.push({
          slot: i,
          headline,
          storyId,
          pivotId,
          source: "", // Not stored in Airtable
        });
      }
    }

    return {
      id: record.id,
      issueId: (fields.issue_id as number) || 0,
      issueDate: (fields.issue_date as string) || "",
      subjectLine: (fields.subject_line as string) || "",
      status: (fields.status as string) || "pending",
      slots,
    };
  });
}

async function updateSubjectLine(
  recordId: string,
  subjectLine: string
): Promise<AirtableRecord> {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY is not set");
  }

  const url = `https://api.airtable.com/v0/${AI_EDITOR_BASE_ID}/${SELECTED_SLOTS_TABLE_ID}/${recordId}`;

  const response = await fetch(url, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${AIRTABLE_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      fields: {
        subject_line: subjectLine,
      },
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Airtable API error: ${response.status} - ${error}`);
  }

  return response.json();
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limitParam = searchParams.get("limit");
  const refresh = searchParams.get("refresh") === "true";

  const limit = limitParam ? parseInt(limitParam, 10) : 10;

  try {
    const issues = await fetchSelectedSlots(limit, refresh);

    return NextResponse.json({
      issues,
      total: issues.length,
      pageSize: limit,
    });
  } catch (error) {
    console.error("[Airtable Selected Slots API] Error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    if (errorMessage.includes("not set")) {
      return NextResponse.json({
        issues: [],
        total: 0,
        message: "Airtable not configured. Set AIRTABLE_API_KEY.",
      });
    }

    return NextResponse.json(
      { error: "Failed to fetch selected slots", details: errorMessage },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json();
    const { recordId, subject_line } = body;

    if (!recordId) {
      return NextResponse.json(
        { error: "recordId is required" },
        { status: 400 }
      );
    }

    if (typeof subject_line !== "string") {
      return NextResponse.json(
        { error: "subject_line must be a string" },
        { status: 400 }
      );
    }

    const record = await updateSubjectLine(recordId, subject_line);

    return NextResponse.json({
      success: true,
      record: {
        id: record.id,
        subject_line: record.fields.subject_line,
      },
    });
  } catch (error) {
    console.error("[Airtable Selected Slots API] PATCH Error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";

    return NextResponse.json(
      { error: "Failed to update subject line", details: errorMessage },
      { status: 500 }
    );
  }
}
