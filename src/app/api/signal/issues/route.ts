/**
 * Signal Newsletter - Issues API
 *
 * GET /api/signal/issues - Get Signal issues filtered by status
 *
 * Query params:
 *   status?: string - Filter by status (e.g., 'compiled', 'sent', 'pending')
 *   skipCache?: boolean - Skip Airtable cache (optional, default: false)
 *
 * Returns issues with: issue_id, subject_line, compiled_html, status, record_id
 */

import { NextRequest, NextResponse } from "next/server";

// Airtable configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const SIGNAL_BASE_ID = process.env.SIGNAL_BASE_ID || "appWGkUBuyrzmFnFM";
const SIGNAL_SELECTED_SLOTS_TABLE = process.env.SIGNAL_SELECTED_SLOTS_TABLE || "tblNxfdFYRxXtBBO2";

interface SignalIssue {
  recordId: string;
  issueId: string;
  issueDate: string;
  subjectLine: string;
  status: string;
  compiledHtml: string | null;
  sentAt: string | null;
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

async function fetchSignalIssues(
  status?: string,
  skipCache: boolean = false
): Promise<SignalIssue[]> {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY not configured");
  }

  const url = new URL(`https://api.airtable.com/v0/${SIGNAL_BASE_ID}/${SIGNAL_SELECTED_SLOTS_TABLE}`);
  url.searchParams.set("pageSize", "100");
  url.searchParams.set("sort[0][field]", "issue_date");
  url.searchParams.set("sort[0][direction]", "desc");

  // Filter by status if provided
  if (status) {
    url.searchParams.set("filterByFormula", `{status} = '${status}'`);
  }

  // Only request the fields we need
  const fields = ["issue_id", "issue_date", "subject_line", "status", "compiled_html", "sent_at"];
  fields.forEach((f) => url.searchParams.append("fields[]", f));

  const response = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${AIRTABLE_API_KEY}`,
      "Content-Type": "application/json",
    },
    ...(skipCache ? { cache: "no-store" as const } : { next: { revalidate: 60 } }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Airtable API error: ${response.status} - ${error}`);
  }

  const data: AirtableResponse = await response.json();

  return data.records.map((record) => ({
    recordId: record.id,
    issueId: (record.fields.issue_id as string) || "",
    issueDate: (record.fields.issue_date as string) || "",
    subjectLine: (record.fields.subject_line as string) || "",
    status: (record.fields.status as string) || "",
    compiledHtml: (record.fields.compiled_html as string) || null,
    sentAt: (record.fields.sent_at as string) || null,
  }));
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status") || undefined;
    const skipCache = searchParams.get("skipCache") === "true";

    const issues = await fetchSignalIssues(status, skipCache);

    return NextResponse.json({
      issues,
      count: issues.length,
      filter: status || "all",
    });
  } catch (error) {
    console.error("Error fetching Signal issues:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch Signal issues" },
      { status: 500 }
    );
  }
}
