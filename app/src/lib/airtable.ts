// Airtable API client for AI Editor 2.0
// Uses the Airtable REST API directly (no SDK needed)

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const PIVOT_MEDIA_BASE_ID = process.env.AIRTABLE_BASE_ID; // appwSozYTkrsQWUXB
const AI_EDITOR_BASE_ID = process.env.AI_EDITOR_BASE_ID; // appglKSJZxmA9iHpl

// Table IDs
const TABLES = {
  // Pivot Media Master Base
  articles: process.env.AIRTABLE_ARTICLES_TABLE,
  newsletterStories: process.env.AIRTABLE_NEWSLETTER_STORIES_TABLE,
  newsletterIssueStories: process.env.AIRTABLE_NEWSLETTER_ISSUE_STORIES_TABLE,
  newsletterIssues: process.env.AIRTABLE_NEWSLETTER_ISSUES_TABLE,
  newsletterIssuesArchive: process.env.AIRTABLE_NEWSLETTER_ISSUES_ARCHIVE_TABLE,
  // AI Editor 2.0 Base
  prefilterLog: process.env.AI_EDITOR_PREFILTER_LOG_TABLE,
  selectedSlots: process.env.AI_EDITOR_SELECTED_SLOTS_TABLE,
  decoration: process.env.AI_EDITOR_DECORATION_TABLE,
  sourceScores: process.env.AI_EDITOR_SOURCE_SCORES_TABLE,
};

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
    view?: string;
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
    url.searchParams.set("maxRecords", options.maxRecords.toString());
  }
  if (options.view) {
    url.searchParams.set("view", options.view);
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
    next: { revalidate: 60 }, // Cache for 60 seconds
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Airtable API error: ${response.status} - ${error}`);
  }

  const data: AirtableResponse = await response.json();
  return data.records;
}

async function updateAirtable(
  baseId: string,
  tableId: string,
  recordId: string,
  fields: Record<string, unknown>
): Promise<AirtableRecord> {
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

  return response.json();
}

async function createAirtable(
  baseId: string,
  tableId: string,
  fields: Record<string, unknown>
): Promise<AirtableRecord> {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY is not set");
  }

  const url = `https://api.airtable.com/v0/${baseId}/${tableId}`;

  const response = await fetch(url, {
    method: "POST",
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

  return response.json();
}

async function deleteAirtable(
  baseId: string,
  tableId: string,
  recordId: string
): Promise<void> {
  if (!AIRTABLE_API_KEY) {
    throw new Error("AIRTABLE_API_KEY is not set");
  }

  const url = `https://api.airtable.com/v0/${baseId}/${tableId}/${recordId}`;

  const response = await fetch(url, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${AIRTABLE_API_KEY}`,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Airtable API error: ${response.status} - ${error}`);
  }
}

// Source Credibility / Source Scores
// Documentation: Table tbl3Zkdl1No2edDLK in AI Editor 2.0 Base
// Fields: source_name, credibility_score
export interface Source {
  id: string;
  name: string;
  credibilityScore: number;
}

export async function getSources(): Promise<Source[]> {
  if (!AI_EDITOR_BASE_ID || !TABLES.sourceScores) {
    throw new Error("AI Editor base ID or source scores table not configured");
  }

  const records = await fetchAirtable(AI_EDITOR_BASE_ID, TABLES.sourceScores, {
    maxRecords: 100,
    sort: [{ field: "source_name", direction: "asc" }],
    fields: ["source_name", "credibility_score"],
  });

  return records.map((record) => ({
    id: record.id,
    name: (record.fields.source_name as string) || "Unknown",
    credibilityScore: (record.fields.credibility_score as number) || 3,
  }));
}

export async function updateSource(
  id: string,
  fields: Partial<{ name: string; credibilityScore: number }>
): Promise<Source> {
  if (!AI_EDITOR_BASE_ID || !TABLES.sourceScores) {
    throw new Error("AI Editor base ID or source scores table not configured");
  }

  const updateFields: Record<string, unknown> = {};
  if (fields.name) updateFields.source_name = fields.name;
  if (fields.credibilityScore !== undefined) {
    updateFields.credibility_score = fields.credibilityScore;
  }

  const record = await updateAirtable(
    AI_EDITOR_BASE_ID,
    TABLES.sourceScores,
    id,
    updateFields
  );

  return {
    id: record.id,
    name: (record.fields.source_name as string) || "Unknown",
    credibilityScore: (record.fields.credibility_score as number) || 3,
  };
}

export async function createSource(
  name: string,
  credibilityScore: number = 3
): Promise<Source> {
  if (!AI_EDITOR_BASE_ID || !TABLES.sourceScores) {
    throw new Error("AI Editor base ID or source scores table not configured");
  }

  const record = await createAirtable(AI_EDITOR_BASE_ID, TABLES.sourceScores, {
    source_name: name,
    credibility_score: credibilityScore,
  });

  return {
    id: record.id,
    name: (record.fields.source_name as string) || name,
    credibilityScore: (record.fields.credibility_score as number) || credibilityScore,
  };
}

export async function deleteSource(id: string): Promise<void> {
  if (!AI_EDITOR_BASE_ID || !TABLES.sourceScores) {
    throw new Error("AI Editor base ID or source scores table not configured");
  }

  await deleteAirtable(AI_EDITOR_BASE_ID, TABLES.sourceScores, id);
}

// Newsletter Stories
export interface Story {
  id: string;
  storyId: string;
  pivotId: string;
  headline: string;
  source: string;
  date: string;
  eligibleSlots: number[];
  selected: boolean;
  selectedSlot?: number;
}

export async function getStories(): Promise<Story[]> {
  if (!PIVOT_MEDIA_BASE_ID || !TABLES.newsletterStories) {
    throw new Error("Pivot Media base ID or newsletter stories table not configured");
  }

  // Fetch Newsletter Stories with exact field names from infrastructure doc
  // Fields: storyID, pivotId, ai_headline, date_og_published, newsletter
  const records = await fetchAirtable(PIVOT_MEDIA_BASE_ID, TABLES.newsletterStories, {
    maxRecords: 100,
    filterByFormula: "AND(IS_AFTER({date_og_published}, DATEADD(TODAY(), -7, 'days')), {newsletter}='pivot_ai')",
    sort: [{ field: "date_og_published", direction: "desc" }],
    fields: ["storyID", "pivotId", "ai_headline", "date_og_published", "newsletter"],
  });

  // Also fetch Articles to get source_id for each story
  const articles = await fetchAirtable(PIVOT_MEDIA_BASE_ID, TABLES.articles!, {
    maxRecords: 500,
    filterByFormula: "IS_AFTER({date_published}, DATEADD(TODAY(), -7, 'days'))",
    fields: ["pivot_Id", "source_id", "original_url"],
  });

  // Build lookup map: pivotId -> source_id
  const sourceMap = new Map<string, string>();
  articles.forEach((article) => {
    const pivotId = article.fields.pivot_Id as string;
    const sourceId = article.fields.source_id as string;
    if (pivotId && sourceId) {
      sourceMap.set(pivotId, sourceId);
    }
  });

  return records.map((record) => {
    const headline = (record.fields.ai_headline as string) || "Untitled";
    const pivotId = (record.fields.pivotId as string) || "";
    const source = sourceMap.get(pivotId) || "Unknown";

    // Determine eligible slots based on headline content
    const eligibleSlots: number[] = [];
    const headlineLower = headline.toLowerCase();

    if (headlineLower.includes("job") || headlineLower.includes("economy") || headlineLower.includes("market") || headlineLower.includes("worker")) eligibleSlots.push(1);
    if (headlineLower.includes("openai") || headlineLower.includes("google") || headlineLower.includes("anthropic") ||
        headlineLower.includes("nvidia") || headlineLower.includes("meta") || headlineLower.includes("microsoft") ||
        headlineLower.includes("amazon") || headlineLower.includes("xai")) eligibleSlots.push(2);
    if (headlineLower.includes("health") || headlineLower.includes("hospital") || headlineLower.includes("government") ||
        headlineLower.includes("education") || headlineLower.includes("legal") || headlineLower.includes("manufacturing")) eligibleSlots.push(3);
    if (headlineLower.includes("startup") || headlineLower.includes("funding") || headlineLower.includes("launch") ||
        headlineLower.includes("raises") || headlineLower.includes("acquisition") || headlineLower.includes("million")) eligibleSlots.push(4);
    if (headlineLower.includes("consumer") || headlineLower.includes("art") || headlineLower.includes("entertainment") ||
        headlineLower.includes("ethics") || headlineLower.includes("creative")) eligibleSlots.push(5);
    if (eligibleSlots.length === 0) eligibleSlots.push(2); // Default to Tier 1 AI

    return {
      id: record.id,
      storyId: (record.fields.storyID as string) || record.id,
      pivotId,
      headline,
      source,
      date: (record.fields.date_og_published as string) || record.createdTime || "",
      eligibleSlots,
      selected: false,
      selectedSlot: undefined,
    };
  });
}

// Pre-Filter Log
// Documentation: Table tbl72YMsm9iRHj3sp in AI Editor 2.0 Base
// Fields: storyID, pivotId, headline, original_url, source_id, date_og_published, date_prefiltered, slot
export interface PreFilterEntry {
  id: string;
  storyId: string;
  pivotId: string;
  headline: string;
  originalUrl: string;
  sourceId: string;
  datePublished: string;
  datePrefiltered: string;
  slot: number;
}

export async function getPreFilterLog(): Promise<PreFilterEntry[]> {
  if (!AI_EDITOR_BASE_ID || !TABLES.prefilterLog) {
    throw new Error("AI Editor base ID or prefilter log table not configured");
  }

  const records = await fetchAirtable(AI_EDITOR_BASE_ID, TABLES.prefilterLog, {
    maxRecords: 200,
    sort: [{ field: "date_prefiltered", direction: "desc" }],
    fields: ["storyID", "pivotId", "headline", "core_url", "source_id", "date_og_published", "date_prefiltered", "slot"],
  });

  return records.map((record) => ({
    id: record.id,
    storyId: (record.fields.storyID as string) || "",
    pivotId: (record.fields.pivotId as string) || "",
    headline: (record.fields.headline as string) || "Untitled",
    originalUrl: (record.fields.core_url as string) || "",
    sourceId: (record.fields.source_id as string) || "",
    datePublished: (record.fields.date_og_published as string) || "",
    datePrefiltered: (record.fields.date_prefiltered as string) || "",
    slot: (record.fields.slot as number) || 0,
  }));
}

// Selected Slots (Today's Issue)
// Documentation: Table tblzt2z7r512Kto3O in AI Editor 2.0 Base
// Fields: issue_id, issue_date, subject_line, status, social_post_status,
//         slot_1_storyId, slot_1_pivotId, slot_1_headline through slot_5_*
export interface SelectedSlots {
  id: string;
  issueId: string;
  issueDate: string;
  subjectLine: string;
  status: string;
  socialPostStatus: string;
  slots: Array<{
    slot: number;
    headline: string;
    storyId: string;
    pivotId: string;
  }>;
}

export async function getSelectedSlots(): Promise<SelectedSlots | null> {
  if (!AI_EDITOR_BASE_ID || !TABLES.selectedSlots) {
    throw new Error("AI Editor base ID or selected slots table not configured");
  }

  const records = await fetchAirtable(AI_EDITOR_BASE_ID, TABLES.selectedSlots, {
    maxRecords: 1,
    sort: [{ field: "issue_date", direction: "desc" }],
    fields: [
      "issue_id",
      "issue_date",
      "subject_line",
      "status",
      "social_post_status",
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
    ],
  });

  if (records.length === 0) return null;

  const record = records[0];
  const fields = record.fields;

  return {
    id: record.id,
    issueId: (fields.issue_id as string) || "",
    issueDate: (fields.issue_date as string) || "",
    subjectLine: (fields.subject_line as string) || "",
    status: (fields.status as string) || "pending",
    socialPostStatus: (fields.social_post_status as string) || "pending",
    slots: [
      {
        slot: 1,
        headline: (fields.slot_1_headline as string) || "",
        storyId: (fields.slot_1_storyId as string) || "",
        pivotId: (fields.slot_1_pivotId as string) || "",
      },
      {
        slot: 2,
        headline: (fields.slot_2_headline as string) || "",
        storyId: (fields.slot_2_storyId as string) || "",
        pivotId: (fields.slot_2_pivotId as string) || "",
      },
      {
        slot: 3,
        headline: (fields.slot_3_headline as string) || "",
        storyId: (fields.slot_3_storyId as string) || "",
        pivotId: (fields.slot_3_pivotId as string) || "",
      },
      {
        slot: 4,
        headline: (fields.slot_4_headline as string) || "",
        storyId: (fields.slot_4_storyId as string) || "",
        pivotId: (fields.slot_4_pivotId as string) || "",
      },
      {
        slot: 5,
        headline: (fields.slot_5_headline as string) || "",
        storyId: (fields.slot_5_storyId as string) || "",
        pivotId: (fields.slot_5_pivotId as string) || "",
      },
    ],
  };
}

// Decoration Table (Newsletter Issue Stories)
// Documentation: Table tbla16LJCf5Z6cRn3 in AI Editor 2.0 Base
// Fields: story_id, issue_id, slot_order, pivotId, headline, ai_dek, label,
//         b1, b2, b3, image_prompt, image_status, image_url, raw, core_url,
//         source_id, social_status, cloudflare_id
export interface DecorationEntry {
  id: string;
  storyId: string;
  issueId: string;
  slotOrder: number;
  pivotId: string;
  headline: string;
  aiDek: string;
  label: string;
  b1: string;
  b2: string;
  b3: string;
  imagePrompt: string;
  imageStatus: string;
  imageUrl: string;
  raw: string;
  coreUrl: string;
  sourceId: string;
  socialStatus: string;
  cloudflareId: string;
}

export async function getDecorations(): Promise<DecorationEntry[]> {
  if (!AI_EDITOR_BASE_ID || !TABLES.decoration) {
    throw new Error("AI Editor base ID or decoration table not configured");
  }

  const records = await fetchAirtable(AI_EDITOR_BASE_ID, TABLES.decoration, {
    maxRecords: 50,
    sort: [{ field: "slot_order", direction: "asc" }],
    fields: [
      "story_id",
      "issue_id",
      "slot_order",
      "pivotId",
      "headline",
      "ai_dek",
      "label",
      "b1",
      "b2",
      "b3",
      "image_prompt",
      "image_status",
      "image_url",
      "raw",
      "core_url",
      "source_id",
      "social_status",
      "cloudflare_id",
    ],
  });

  return records.map((record) => ({
    id: record.id,
    storyId: (record.fields.story_id as string) || "",
    issueId: (record.fields.issue_id as string) || "",
    slotOrder: (record.fields.slot_order as number) || 0,
    pivotId: (record.fields.pivotId as string) || "",
    headline: (record.fields.headline as string) || "",
    aiDek: (record.fields.ai_dek as string) || "",
    label: (record.fields.label as string) || "",
    b1: (record.fields.b1 as string) || "",
    b2: (record.fields.b2 as string) || "",
    b3: (record.fields.b3 as string) || "",
    imagePrompt: (record.fields.image_prompt as string) || "",
    imageStatus: (record.fields.image_status as string) || "pending",
    imageUrl: (record.fields.image_url as string) || "",
    raw: (record.fields.raw as string) || "",
    coreUrl: (record.fields.core_url as string) || "",
    sourceId: (record.fields.source_id as string) || "",
    socialStatus: (record.fields.social_status as string) || "",
    cloudflareId: (record.fields.cloudflare_id as string) || "",
  }));
}
