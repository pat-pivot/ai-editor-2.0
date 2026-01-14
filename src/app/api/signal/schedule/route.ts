/**
 * Signal Newsletter - Schedule to Ongage API
 *
 * POST /api/signal/schedule - Schedule a compiled Signal issue to Ongage
 *
 * Body:
 *   issueRecordId: string - The Airtable record ID of the compiled issue
 *   scheduleTime?: string - Optional ISO timestamp for scheduled send (default: tomorrow 5am ET)
 *
 * Flow:
 *   1. Fetch issue from Airtable (Signal - Selected Slots)
 *   2. Validate status === 'compiled' and compiled_html exists
 *   3. Create Ongage email message (POST /emails)
 *   4. Create Ongage campaign/mailing (POST /mailings)
 *   5. Update Airtable status to 'sent' and set sent_at
 *   6. Return campaign details
 */

import { NextRequest, NextResponse } from "next/server";

// Ongage configuration
const ONGAGE_BASE_URL = "https://api.ongage.net";
const ONGAGE_LIST_ID = process.env.ONGAGE_LIST_ID || "1322085";
const ONGAGE_ESP_CONNECTION_ID = parseInt(process.env.ONGAGE_ESP_CONNECTION_ID || "1092866", 10);
const SIGNAL_FROM_EMAIL = process.env.SIGNAL_FROM_EMAIL || "newsletter@signalainews.com";
const SIGNAL_FROM_NAME = process.env.SIGNAL_FROM_NAME || "Signal AI News";

// Airtable configuration
const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const SIGNAL_BASE_ID = process.env.SIGNAL_BASE_ID || "appWGkUBuyrzmFnFM";
const SIGNAL_SELECTED_SLOTS_TABLE = process.env.SIGNAL_SELECTED_SLOTS_TABLE || "tblNxfdFYRxXtBBO2";

interface OngageHeaders {
  x_username: string;
  x_password: string;
  x_account_code: string;
  "Content-Type": string;
}

/**
 * Get Ongage API headers
 */
function getOngageHeaders(): OngageHeaders {
  const username = process.env.ONGAGE_USERNAME;
  const password = process.env.ONGAGE_PASSWORD;
  const accountCode = process.env.ONGAGE_ACCOUNT_CODE;

  if (!username || !password || !accountCode) {
    throw new Error("Ongage credentials not configured (ONGAGE_USERNAME, ONGAGE_PASSWORD, ONGAGE_ACCOUNT_CODE)");
  }

  return {
    x_username: username,
    x_password: password,
    x_account_code: accountCode,
    "Content-Type": "application/json",
  };
}

/**
 * Fetch a Signal issue from Airtable by record ID
 */
async function fetchSignalIssue(recordId: string) {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY not configured");
  }

  const url = `https://api.airtable.com/v0/${SIGNAL_BASE_ID}/${SIGNAL_SELECTED_SLOTS_TABLE}/${recordId}`;

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${AIRTABLE_API_KEY}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch issue from Airtable: ${response.status} - ${error}`);
  }

  return response.json();
}

/**
 * Update Signal issue status in Airtable
 */
async function updateSignalIssueStatus(recordId: string, status: string, sentAt?: string) {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY not configured");
  }

  const url = `https://api.airtable.com/v0/${SIGNAL_BASE_ID}/${SIGNAL_SELECTED_SLOTS_TABLE}/${recordId}`;

  const fields: Record<string, string> = { status };
  if (sentAt) {
    fields.sent_at = sentAt;
  }

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
    throw new Error(`Failed to update issue in Airtable: ${response.status} - ${error}`);
  }

  return response.json();
}

/**
 * Strip HTML tags to create plain text version
 */
function stripHtmlToText(html: string): string {
  // Remove HTML tags
  let text = html.replace(/<[^>]*>/g, " ");
  // Decode HTML entities
  text = text.replace(/&nbsp;/g, " ");
  text = text.replace(/&amp;/g, "&");
  text = text.replace(/&lt;/g, "<");
  text = text.replace(/&gt;/g, ">");
  text = text.replace(/&quot;/g, '"');
  text = text.replace(/&#39;/g, "'");
  // Clean up whitespace
  text = text.replace(/\s+/g, " ").trim();
  return text;
}

/**
 * Calculate schedule timestamp for 5am ET tomorrow
 */
function getDefaultScheduleTimestamp(): number {
  // Get current date in UTC
  const now = new Date();

  // Calculate tomorrow's date
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // Set to 5am ET (10am UTC during EST, 9am UTC during EDT)
  // We'll use 10am UTC to be safe (5am EST)
  tomorrow.setUTCHours(10, 0, 0, 0);

  return Math.floor(tomorrow.getTime() / 1000);
}

/**
 * Create an email message in Ongage
 */
async function createOngageEmailMessage(
  name: string,
  subject: string,
  htmlContent: string,
  textContent: string
): Promise<number> {
  const headers = getOngageHeaders();

  const payload = {
    type: "email_message",
    name,
    subject,
    content_html: htmlContent,
    content_text: textContent,
    addresses: [
      {
        from_name: SIGNAL_FROM_NAME,
        from_address: SIGNAL_FROM_EMAIL,
        reply_address: SIGNAL_FROM_EMAIL,
        esp_connection_id: ONGAGE_ESP_CONNECTION_ID,
      },
    ],
    unsubscribe_default_link: true,
  };

  const response = await fetch(`${ONGAGE_BASE_URL}/${ONGAGE_LIST_ID}/api/emails`, {
    method: "POST",
    headers: headers as unknown as HeadersInit,
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok || !data.metadata?.success) {
    console.error("Ongage email creation failed:", data);
    throw new Error(`Failed to create Ongage email: ${data.metadata?.error || response.status}`);
  }

  return data.payload.id;
}

/**
 * Create a campaign/mailing in Ongage
 */
async function createOngageCampaign(
  name: string,
  emailMessageId: number,
  scheduleTimestamp: number
): Promise<{ campaignId: number; status: string }> {
  const headers = getOngageHeaders();

  const payload = {
    name,
    description: "Daily Signal AI News newsletter",
    email_message: [emailMessageId],
    segments: [], // Empty = entire list
    distribution: [
      {
        esp_connection_id: ONGAGE_ESP_CONNECTION_ID,
        percent: 100,
      },
    ],
    schedule_date: scheduleTimestamp,
  };

  const response = await fetch(`${ONGAGE_BASE_URL}/${ONGAGE_LIST_ID}/api/mailings`, {
    method: "POST",
    headers: headers as unknown as HeadersInit,
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok || !data.metadata?.success) {
    console.error("Ongage campaign creation failed:", data);
    throw new Error(`Failed to create Ongage campaign: ${data.metadata?.error || response.status}`);
  }

  return {
    campaignId: data.payload.id,
    status: data.payload.status_desc || "Scheduled",
  };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { issueRecordId, scheduleTime } = body;

    if (!issueRecordId) {
      return NextResponse.json(
        { error: "issueRecordId is required" },
        { status: 400 }
      );
    }

    // Step 1: Fetch the issue from Airtable
    console.log(`[Signal Schedule] Fetching issue ${issueRecordId} from Airtable...`);
    const issueRecord = await fetchSignalIssue(issueRecordId);
    const fields = issueRecord.fields;

    // Step 2: Validate status and compiled_html
    const status = fields.status as string;
    const compiledHtml = fields.compiled_html as string;
    const subjectLine = fields.subject_line as string;
    const issueId = fields.issue_id as string;

    if (status !== "compiled") {
      return NextResponse.json(
        { error: `Issue status must be 'compiled', got '${status}'` },
        { status: 400 }
      );
    }

    if (!compiledHtml) {
      return NextResponse.json(
        { error: "Issue does not have compiled_html" },
        { status: 400 }
      );
    }

    if (!subjectLine) {
      return NextResponse.json(
        { error: "Issue does not have subject_line" },
        { status: 400 }
      );
    }

    // Step 3: Prepare schedule timestamp
    let scheduleTimestamp: number;
    if (scheduleTime) {
      scheduleTimestamp = Math.floor(new Date(scheduleTime).getTime() / 1000);
    } else {
      scheduleTimestamp = getDefaultScheduleTimestamp();
    }

    const scheduleDate = new Date(scheduleTimestamp * 1000);
    const formattedDate = scheduleDate.toISOString().split("T")[0];

    // Step 4: Create Ongage email message
    console.log(`[Signal Schedule] Creating Ongage email message...`);
    const emailName = `Signal AI News - ${formattedDate}`;
    const textContent = stripHtmlToText(compiledHtml);

    const emailMessageId = await createOngageEmailMessage(
      emailName,
      subjectLine,
      compiledHtml,
      textContent
    );
    console.log(`[Signal Schedule] Created email message ID: ${emailMessageId}`);

    // Step 5: Create Ongage campaign
    console.log(`[Signal Schedule] Creating Ongage campaign...`);
    const campaignName = `Signal AI News - ${formattedDate}`;
    const { campaignId, status: campaignStatus } = await createOngageCampaign(
      campaignName,
      emailMessageId,
      scheduleTimestamp
    );
    console.log(`[Signal Schedule] Created campaign ID: ${campaignId}, status: ${campaignStatus}`);

    // Step 6: Update Airtable status
    console.log(`[Signal Schedule] Updating Airtable status to 'sent'...`);
    const sentAt = new Date().toISOString();
    await updateSignalIssueStatus(issueRecordId, "sent", sentAt);

    // Return success response
    return NextResponse.json({
      success: true,
      issueId,
      issueRecordId,
      emailMessageId,
      campaignId,
      campaignStatus,
      scheduledFor: scheduleDate.toISOString(),
      sentAt,
      message: `Signal newsletter scheduled successfully for ${scheduleDate.toLocaleString("en-US", { timeZone: "America/New_York" })} ET`,
    });
  } catch (error) {
    console.error("[Signal Schedule] Error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to schedule Signal newsletter" },
      { status: 500 }
    );
  }
}
