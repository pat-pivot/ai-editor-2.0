# AI Editor 2.0 Infrastructure - Step 1: Pre-Filter Workflow

**Document:** AI-Editor-2.0-Infrastructure-Step-1-12-23-25.md
**Date:** December 23, 2025
**Purpose:** Complete node-by-node analysis of Step 1: Pre-Filter workflow

---

## Workflow Overview

**Workflow Name:** STEP 1 AI Editor 2.0 - Pre-Filter Cron
**Workflow ID:** `VoSZu0MIJAw1IuLL`
**Total Nodes:** 27
**Schedule:** `0 2 * * 2-6` (9:00 PM EST, Monday-Friday)

### Purpose
Filters fresh candidate articles into 5 newsletter slot categories using Google Gemini AI, considering source credibility scores and content relevance.

### AI Model
- **Model:** `gemini-3-flash-preview`
- **Provider:** Google
- **Purpose:** Pre-filtering articles into slot categories

---

## Airtable Tables Referenced

### Input Tables

| Base | Table | Table ID | Purpose |
|------|-------|----------|---------|
| Pivot Media Master | Newsletter Stories | `tblY78ziWp5yhiGXp` | Fresh candidate articles |
| AI Editor 2.0 | Queued Stories | `tblN1RypWAOBMOfQ5` | Manually queued priority stories |
| AI Editor 2.0 | Selected Slots | `tblzt2z7r512Kto3O` | Yesterday's issue (for diversity) |
| AI Editor 2.0 | Source Credibility | `tbl3Zkdl1No2edDLK` | Source ratings (1-5) |
| Pivot Media Master | Articles | `tblGumae8KDpsrWvh` | Raw articles with source_id |

### Output Table

| Base | Table | Table ID | Purpose |
|------|-------|----------|---------|
| AI Editor 2.0 | Pre-Filter Log | `tbl72YMsm9iRHj3sp` | Filtered candidates per slot |

---

## Slot Eligibility Criteria

| Slot | Focus | Freshness |
|------|-------|-----------|
| 1 | AI impact on jobs/economy/stock market/broad impact | 0-24 hours |
| 2 | Tier 1 AI companies (OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon) + economic themes + research | 24-48 hours |
| 3 | Industry impact (Healthcare, Government, Education, Legal, Accounting, Retail, Security, Transportation, Manufacturing, Real Estate, Agriculture, Energy) | 0-7 days |
| 4 | Emerging companies (product launches, fundraising, acquisitions, new AI tools) | 0-48 hours |
| 5 | Consumer AI / human interest (ethics, entertainment, societal impact, fun/quirky uses) | 0-7 days |

---

## Node-by-Node Analysis

### Node 1: Schedule Trigger
**Node ID:** `schedule-trigger`
**Type:** `n8n-nodes-base.scheduleTrigger`
**Version:** 1.2
**Position:** [-1920, 256]

**Configuration:**
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "0 2 * * 2-6"
      }
    ]
  }
}
```

**Purpose:** Triggers at 9:00 PM EST (2:00 AM UTC next day) Monday through Friday.

---

### Node 2: Get Fresh Stories
**Node ID:** `get-fresh-stories`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1696, 256]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tblY78ziWp5yhiGXp` (Newsletter Stories)

**Filter Formula:**
```
AND(
  IS_AFTER({date_og_published}, DATEADD(TODAY(), -7, 'days')),
  {ai_headline}!=''
)
```

**Sort:** `date_og_published` DESC
**Max Records:** 100

**Fields Retrieved:**
| Field | Type |
|-------|------|
| storyID | Text |
| pivotId | Text |
| ai_headline | Text |
| ai_dek | Text |
| date_og_published | DateTime |
| newsletter | Select |
| topic | Text |

**Output:** Stories array → Connects to "Filter Pivot AI Stories"

---

### Node 3: Filter Pivot AI Stories
**Node ID:** `filter-pivot-ai`
**Type:** `n8n-nodes-base.filter`
**Version:** 2
**Position:** [-1472, 256]

**Condition:**
```json
{
  "conditions": [
    {
      "leftValue": "={{ $json.fields.newsletter }}",
      "rightValue": "pivot_ai",
      "operator": {
        "type": "string",
        "operation": "equals"
      }
    }
  ]
}
```

**Output:** Filtered stories → Connects to "Get Queued Stories"

---

### Node 4: Get Queued Stories
**Node ID:** `get-queued-stories`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1248, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblN1RypWAOBMOfQ5` (AI Editor - Queued Stories)

**Filter Formula:**
```
{status}='pending'
```

**Purpose:** Retrieves manually queued priority stories that should be considered first.

---

### Node 5: Merge Story Sources
**Node ID:** `merge-stories`
**Type:** `n8n-nodes-base.merge`
**Version:** 3
**Position:** [-1024, 256]

**Mode:** `combine`
**Combination Mode:** `mergeByPosition`

**Purpose:** Combines fresh stories with queued stories for processing.

---

### Node 6: Get Source Scores
**Node ID:** `get-source-scores`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-800, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbl3Zkdl1No2edDLK` (Source Credibility)

**Max Records:** 500

**Fields Retrieved:**
| Field | Type |
|-------|------|
| source_name | Text |
| credibility_score | Number (1-5) |

**Output:** Source scores → Connects to "Build Source Lookup"

---

### Node 7: Build Source Lookup
**Node ID:** `build-source-lookup`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-576, 256]

**JavaScript Code:**
```javascript
const sources = $input.all();
const lookup = {};

for (const item of sources) {
  const name = item.json.fields.source_name;
  const score = item.json.fields.credibility_score || 3;
  lookup[name.toLowerCase()] = score;
}

return [{ json: { sourceLookup: lookup } }];
```

**Output:** Lookup object → Connects to "Get Yesterday's Issue"

---

### Node 8: Get Yesterday's Issue
**Node ID:** `get-yesterday-issue`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-352, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)

**Filter Formula:**
```
{status}='sent'
```

**Sort:** `issue_date` DESC
**Max Records:** 1

**Purpose:** Retrieves yesterday's sent issue to enforce diversity rules.

---

### Node 9: Extract Yesterday's Data
**Node ID:** `extract-yesterday`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-128, 256]

**JavaScript Code:**
```javascript
const yesterday = $input.first()?.json?.fields || {};

const yesterdayData = {
  headlines: [
    yesterday.slot_1_headline,
    yesterday.slot_2_headline,
    yesterday.slot_3_headline,
    yesterday.slot_4_headline,
    yesterday.slot_5_headline
  ].filter(Boolean),
  storyIds: [
    yesterday.slot_1_storyId,
    yesterday.slot_2_storyId,
    yesterday.slot_3_storyId,
    yesterday.slot_4_storyId,
    yesterday.slot_5_storyId
  ].filter(Boolean),
  pivotIds: [
    yesterday.slot_1_pivotId,
    yesterday.slot_2_pivotId,
    yesterday.slot_3_pivotId,
    yesterday.slot_4_pivotId,
    yesterday.slot_5_pivotId
  ].filter(Boolean)
};

return [{ json: yesterdayData }];
```

---

### Node 10: Split In Batches
**Node ID:** `split-batches`
**Type:** `n8n-nodes-base.splitInBatches`
**Version:** 3
**Position:** [96, 256]

**Configuration:**
```json
{
  "batchSize": 10
}
```

**Purpose:** Processes stories in batches of 10 for Gemini API calls.

---

### Node 11: Lookup Source ID
**Node ID:** `lookup-source-id`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [320, 256]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tblGumae8KDpsrWvh` (Articles)

**Filter Formula:**
```
{pivot_Id}='{{ $json.fields.pivotId }}'
```

**Fields Retrieved:**
| Field | Type |
|-------|------|
| source_id | Text |
| original_url | Text |

**Purpose:** Retrieves source_id from original Articles table.

---

### Node 12: Prepare Gemini Prompt
**Node ID:** `prepare-gemini-prompt`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [544, 256]

**JavaScript Code:**
```javascript
const story = $('Split In Batches').item.json;
const sourceData = $input.first().json.fields;
const sourceLookup = $('Build Source Lookup').first().json.sourceLookup;
const yesterday = $('Extract Yesterday\'s Data').first().json;

const sourceName = sourceData.source_id || 'Unknown';
const credibilityScore = sourceLookup[sourceName.toLowerCase()] || 3;

const publishedDate = new Date(story.fields.date_og_published);
const now = new Date();
const hoursAgo = Math.round((now - publishedDate) / (1000 * 60 * 60));

return [{
  json: {
    storyId: story.fields.storyID,
    pivotId: story.fields.pivotId,
    headline: story.fields.ai_headline,
    dek: story.fields.ai_dek,
    topic: story.fields.topic,
    source: sourceName,
    credibilityScore: credibilityScore,
    hoursAgo: hoursAgo,
    originalUrl: sourceData.original_url,
    yesterdayHeadlines: yesterday.headlines,
    yesterdayStoryIds: yesterday.storyIds
  }
}];
```

---

### Node 13: Gemini Pre-Filter
**Node ID:** `gemini-prefilter`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [768, 256]

**HTTP Configuration:**
- **Method:** POST
- **URL:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent`

**Query Parameters:**
```json
{
  "key": "{{ $env.GEMINI_API_KEY }}"
}
```

**Request Body:**
```json
{
  "contents": [{
    "parts": [{
      "text": "You are a newsletter editor for Pivot 5, a daily AI newsletter.\n\nAnalyze this article and determine which newsletter slots (1-5) it is eligible for:\n\nHEADLINE: {{ $json.headline }}\nDEK: {{ $json.dek }}\nSOURCE: {{ $json.source }} (credibility: {{ $json.credibilityScore }}/5)\nAGE: {{ $json.hoursAgo }} hours ago\nTOPIC: {{ $json.topic }}\n\nSLOT DEFINITIONS:\n1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.\n2. TIER 1 AI: News about OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.\n3. INDUSTRY IMPACT: AI in Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.\n4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.\n5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.\n\nYESTERDAY'S HEADLINES (avoid similar topics):\n{{ $json.yesterdayHeadlines.join('\\n') }}\n\nReturn JSON only:\n{\n  \"eligible_slots\": [1, 2, ...],\n  \"primary_slot\": 1,\n  \"reasoning\": \"Brief explanation\"\n}"
    }]
  }],
  "generationConfig": {
    "temperature": 0.3,
    "maxOutputTokens": 256,
    "responseMimeType": "application/json"
  }
}
```

**Output:** Gemini response → Connects to "Parse Gemini Response"

---

### Node 14: Parse Gemini Response
**Node ID:** `parse-gemini`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [992, 256]

**JavaScript Code:**
```javascript
const story = $('Prepare Gemini Prompt').first().json;
const geminiResponse = $input.first().json;

let eligibility;
try {
  const text = geminiResponse.candidates[0].content.parts[0].text;
  eligibility = JSON.parse(text);
} catch (e) {
  eligibility = { eligible_slots: [], primary_slot: null, reasoning: 'Parse error' };
}

return [{
  json: {
    ...story,
    eligibleSlots: eligibility.eligible_slots || [],
    primarySlot: eligibility.primary_slot,
    reasoning: eligibility.reasoning
  }
}];
```

---

### Node 15: Filter Has Eligible Slots
**Node ID:** `filter-eligible`
**Type:** `n8n-nodes-base.filter`
**Version:** 2
**Position:** [1216, 256]

**Condition:**
```json
{
  "conditions": [
    {
      "leftValue": "={{ $json.eligibleSlots.length }}",
      "rightValue": 0,
      "operator": {
        "type": "number",
        "operation": "gt"
      }
    }
  ]
}
```

---

### Node 16: Split by Slot
**Node ID:** `split-by-slot`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [1440, 256]

**JavaScript Code:**
```javascript
const story = $input.first().json;
const records = [];

for (const slot of story.eligibleSlots) {
  records.push({
    json: {
      storyID: story.storyId,
      pivotId: story.pivotId,
      headline: story.headline,
      original_url: story.originalUrl,
      source_id: story.source,
      date_og_published: new Date().toISOString(),
      date_prefiltered: new Date().toISOString().split('T')[0],
      slot: slot
    }
  });
}

return records;
```

**Purpose:** Creates one record per eligible slot for each story.

---

### Node 17: Write Pre-Filter Log
**Node ID:** `write-prefilter-log`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [1664, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbl72YMsm9iRHj3sp` (Pre-Filter Log)
- **Operation:** Create record

**Column Mapping:**
| Airtable Field | Source Expression |
|----------------|-------------------|
| storyID | `{{ $json.storyID }}` |
| pivotId | `{{ $json.pivotId }}` |
| headline | `{{ $json.headline }}` |
| original_url | `{{ $json.original_url }}` |
| source_id | `{{ $json.source_id }}` |
| date_og_published | `{{ $json.date_og_published }}` |
| date_prefiltered | `{{ $json.date_prefiltered }}` |
| slot | `{{ $json.slot }}` |

**Output:** → Connects back to "Split In Batches" (loop)

---

## Step 1 Data Flow Summary

```
Schedule Trigger (9:00 PM EST)
       │
       ▼
Get Fresh Stories (last 7 days, has headline)
       │
       ▼
Filter Pivot AI Stories (newsletter='pivot_ai')
       │
       ▼
Get Queued Stories (status='pending')
       │
       ▼
Merge Story Sources
       │
       ▼
Get Source Scores (credibility table)
       │
       ▼
Build Source Lookup (name → score map)
       │
       ▼
Get Yesterday's Issue (status='sent')
       │
       ▼
Extract Yesterday's Data (headlines, storyIds)
       │
       ▼
Split In Batches (10 at a time)
       │
       ├──────────────────────────────────────┐
       ▼                                      │
Lookup Source ID (get source from Articles)  │
       │                                      │
       ▼                                      │
Prepare Gemini Prompt                        │
       │                                      │
       ▼                                      │
Gemini Pre-Filter (categorize into slots)   │
       │                                      │
       ▼                                      │
Parse Gemini Response                        │
       │                                      │
       ▼                                      │
Filter Has Eligible Slots (length > 0)       │
       │                                      │
       ▼                                      │
Split by Slot (1 record per eligible slot)   │
       │                                      │
       ▼                                      │
Write Pre-Filter Log (tbl72YMsm9iRHj3sp)    │
       │                                      │
       └──────────────────────────────────────┘
```

---

## API Credentials for Step 1

### Airtable
| Key | Value |
|-----|-------|
| API Key | `[REDACTED]` |
| Base: AI Editor 2.0 | `appglKSJZxmA9iHpl` |
| Base: Pivot Media Master | `appwSozYTkrsQWUXB` |

### Google Gemini
| Key | Value |
|-----|-------|
| Model | `gemini-3-flash-preview` |
| API Key | Environment variable: `GEMINI_API_KEY` |

---

## Pre-Filter Log Table Schema (tbl72YMsm9iRHj3sp)

| Field | Type | Description |
|-------|------|-------------|
| storyID | Text | Story identifier (same as article_id) |
| pivotId | Text | Link to Articles table |
| headline | Text | Story headline |
| original_url | Text | Source URL |
| source_id | Text | Publisher name |
| date_og_published | DateTime | Original publication date |
| date_prefiltered | Date | Pre-filter timestamp |
| slot | Number | Eligible slot (1-5) |

---

*Document generated: December 23, 2025*
