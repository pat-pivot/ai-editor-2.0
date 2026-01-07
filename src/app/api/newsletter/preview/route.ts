/**
 * Newsletter Preview API
 *
 * GET /api/newsletter/preview
 * Fetches the latest "next-send" newsletter issue from Airtable
 * Returns { html, subject_line, summary, issue_id, send_date, status, scheduled_send_time, scheduled_at, record_id }
 */

import { NextResponse } from "next/server";

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AI_EDITOR_BASE_ID = process.env.AI_EDITOR_BASE_ID || "appglKSJZxmA9iHpl";
const NEWSLETTER_ISSUES_FINAL_TABLE = "tblPBfWZzRdLuiqYr";

interface AirtableRecord {
  id: string;
  fields: Record<string, unknown>;
  createdTime: string;
}

interface AirtableResponse {
  records: AirtableRecord[];
  offset?: string;
}

async function fetchAirtable(
  baseId: string,
  tableId: string,
  options: {
    maxRecords?: number;
    filterByFormula?: string;
    sort?: Array<{ field: string; direction: "asc" | "desc" }>;
    fields?: string[];
  } = {}
): Promise<AirtableRecord[]> {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY is not set");
  }

  const url = new URL(`https://api.airtable.com/v0/${baseId}/${tableId}`);

  if (options.maxRecords) {
    url.searchParams.set("maxRecords", String(options.maxRecords));
  }
  if (options.filterByFormula) {
    url.searchParams.set("filterByFormula", options.filterByFormula);
  }
  if (options.sort) {
    options.sort.forEach((s, i) => {
      url.searchParams.set(`sort[${i}][field]`, s.field);
      url.searchParams.set(`sort[${i}][direction]`, s.direction);
    });
  }
  if (options.fields) {
    options.fields.forEach((f) => {
      url.searchParams.append("fields[]", f);
    });
  }

  const response = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${AIRTABLE_API_KEY}`,
      "Content-Type": "application/json",
    },
    cache: "no-store", // Always fetch fresh data
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Airtable API error: ${response.status} - ${error}`);
  }

  const data: AirtableResponse = await response.json();
  return data.records;
}

export async function GET() {
  try {
    // Fetch the latest issue with status "next-send" or "scheduled"
    // Newsletter Issues Final table fields:
    // issue_id, newsletter_id, status, send_date, subject_line, summary, html,
    // scheduled_send_time, scheduled_at, Stories
    // Fetch multiple records and sort client-side to get the most recently created one
    // (Airtable doesn't allow sorting by system fields like createdTime)
    const records = await fetchAirtable(AI_EDITOR_BASE_ID, NEWSLETTER_ISSUES_FINAL_TABLE, {
      maxRecords: 10,
      filterByFormula: `OR({status}="next-send", {status}="scheduled", {status}="compiled")`,
      sort: [{ field: "issue_id", direction: "desc" }],
      fields: [
        "issue_id",
        "subject_line",
        "summary",
        "status",
        "html",
        "send_date",
      ],
    });

    if (records.length === 0) {
      return NextResponse.json(
        { error: "No newsletter ready for preview. Status must be 'next-send' or 'scheduled'." },
        { status: 404 }
      );
    }

    // Sort by createdTime descending to get the most recently created record
    // This ensures we get the newest record when multiple exist with the same issue_id
    const sortedRecords = [...records].sort((a, b) => {
      return new Date(b.createdTime).getTime() - new Date(a.createdTime).getTime();
    });

    const record = sortedRecords[0];
    const fields = record.fields;

    // Extract and return the preview data
    const previewData = {
      html: (fields.html as string) || "",
      subject_line: (fields.subject_line as string) || "",
      summary: (fields.summary as string) || "",
      issue_id: (fields.issue_id as string) || record.id,
      send_date: (fields.send_date as string) || "",
      status: (fields.status as string) || "unknown",
      scheduled_send_time: null, // Field not yet created in Airtable
      scheduled_at: null, // Field not yet created in Airtable
      record_id: record.id,
    };

    return NextResponse.json(previewData);
  } catch (error) {
    console.error("[Newsletter Preview API] Error:", error);

    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Failed to fetch newsletter preview",
      },
      { status: 500 }
    );
  }
}
