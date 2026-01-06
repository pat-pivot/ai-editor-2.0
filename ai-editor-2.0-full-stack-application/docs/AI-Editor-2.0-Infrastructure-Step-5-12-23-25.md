# AI Editor 2.0 Infrastructure - Step 5: Social Post Trigger Workflow

**Date:** December 23, 2025
**Workflow Name:** STEP 5 AI Editor 2.0 - Airtable Social Post Trigger
**Workflow ID:** `I8U8LgJVDsO8PeBJ`
**Total Nodes:** 10

---

## Overview

Syndicates decorated newsletter stories to the P5 Social Posts table for downstream social media workflows, preventing duplicate posts.

---

## Schedule

| Schedule | Cron Expression | EST Time | Days |
|----------|-----------------|----------|------|
| Run 1 | `30 4 * * 1-5` | 4:30 AM | Monday-Friday |
| Run 2 | `0 5 * * 1-5` | 5:00 AM | Monday-Friday |

**Purpose:** Runs at 4:30 AM and 5:00 AM EST to catch newly generated content.

---

## AI Models Used

None - This workflow is purely data synchronization.

---

## Airtable Tables

### Input Tables

| Table | Base | Table ID | Purpose |
|-------|------|----------|---------|
| Newsletter Issue Stories (Decoration) | AI Editor 2.0 (`appglKSJZxmA9iHpl`) | `tbla16LJCf5Z6cRn3` | Source decorated stories |

### Output Tables

| Table | Base | Table ID | Purpose |
|-------|------|----------|---------|
| P5 Social Posts | P5 Social Posts (`appRUgK44hQnXH1PM`) | `tbllJMN2QBPJoG3jA` | Social media queue |

---

## Node-by-Node Analysis

### Node 1: Schedule Trigger
**Node ID:** `schedule-trigger`
**Type:** `n8n-nodes-base.scheduleTrigger`
**Version:** 1.2
**Position:** [-1104, -80]

**Configuration:**
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "30 4 * * 1-5"
      },
      {
        "field": "cronExpression",
        "expression": "0 5 * * 1-5"
      }
    ]
  }
}
```

**Purpose:** Runs at 4:30 AM and 5:00 AM EST to catch newly generated content.

---

### Node 2: GET Decorated Stories Ready for Social
**Node ID:** `1719734d-da69-48a3-938f-731622d0ae24`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [-768, -16]

**HTTP Configuration:**
- **Method:** GET
- **URL:** `https://api.airtable.com/v0/appglKSJZxmA9iHpl/tbla16LJCf5Z6cRn3`

**Query Parameters:**
| Parameter | Value |
|-----------|-------|
| filterByFormula | `AND({image_status}='generated', OR({social_status}='', {social_status}='pending'))` |
| maxRecords | `10` |

**Headers:**
| Header | Value |
|--------|-------|
| Authorization | `Bearer [REDACTED]` |
| Content-Type | `application/json` |

**Purpose:** Fetches stories that have images generated but haven't been synced to social yet.

**Output:** Airtable records → Connects to "Extract Records"

---

### Node 3: Extract Records
**Node ID:** `b8371e59-1270-45a1-8deb-46b4650adf11`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-544, -16]

**JavaScript Code:**
```javascript
// Extract records array from Airtable API response
const airtableResponse = $input.first().json;

return airtableResponse.records.map(record => {
  // Clean the raw field if it exists
  if (record.fields?.raw) {
    let raw = record.fields.raw;

    // Remove HTML tags
    raw = raw.replace(/<[^>]*>/g, '');

    // Decode common HTML entities
    raw = raw.replace(/&nbsp;/g, ' ')
             .replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"')
             .replace(/&#39;/g, "'");

    // Normalize whitespace: replace multiple newlines/spaces with single space
    raw = raw.replace(/\s+/g, ' ');

    // Trim
    raw = raw.trim();

    // Update the field
    record.fields.raw = raw;
  }

  return {json: record};
});
```

**Purpose:** Extracts individual records from Airtable response and cleans HTML from raw content.

**Output:** Individual story records → Connects to "Split In Batches"

---

### Node 4: Split In Batches
**Node ID:** `406eacf1-187d-4b43-900b-de444f6abfab`
**Type:** `n8n-nodes-base.splitInBatches`
**Version:** 3
**Position:** [-320, -176]

**Configuration:**
```json
{
  "options": {
    "reset": false
  }
}
```

**Purpose:** Process stories one at a time to handle deduplication.

**Output:** Single story → Connects to "Find Existing in P5 Social Posts"

---

### Node 5: Find Existing in P5 Social Posts
**Node ID:** `342fed88-5e06-4a9a-8c32-bbc1e047bfbd`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [-112, 48]

**HTTP Configuration:**
- **Method:** GET
- **URL:** `https://api.airtable.com/v0/appRUgK44hQnXH1PM/tbllJMN2QBPJoG3jA`

**Query Parameters:**
| Parameter | Value |
|-----------|-------|
| filterByFormula | `AND({source_record_id}="{{ $json.id }}",{source_record_id}!="")` |

**Headers:**
| Header | Value |
|--------|-------|
| Authorization | `Bearer [REDACTED]` |

**Purpose:** Checks if a social post already exists for this source record.

**Output:** Existing records (if any) → Connects to "Check If Exists"

---

### Node 6: Check If Exists
**Node ID:** `ea3b0b03-8d00-496a-b3b1-0d82ca2a49a9`
**Type:** `n8n-nodes-base.function`
**Version:** 1
**Position:** [96, 96]

**JavaScript Code:**
```javascript
const sourceRecord = $input.item.json;
const existingRecordsResponse = $('Find Existing in P5 Social Posts').first().json;

// If record already exists, mark it as 'skip' so we continue the loop
if (existingRecordsResponse.records && existingRecordsResponse.records.length > 0) {
  return {json: {...sourceRecord, action: 'skip'}};
}

// Record doesn't exist, pass it through with action='create'
return {json: {...sourceRecord, action: 'create'}};
```

**Purpose:** Determines whether to create new social post or skip duplicate.

**Output:** Record with action flag → Connects to "Does Newsletter Post Already Exist?"

---

### Node 7: Does Newsletter Post Already Exist?
**Node ID:** `0361a445-a621-436d-a63a-f651a3d065e5`
**Type:** `n8n-nodes-base.if`
**Version:** 2
**Position:** [320, 96]

**Condition:**
```json
{
  "conditions": {
    "conditions": [
      {
        "id": "condition1",
        "leftValue": "={{ $json.action }}",
        "rightValue": "skip",
        "operator": {
          "type": "string",
          "operation": "equals"
        }
      }
    ],
    "combinator": "and"
  }
}
```

**True Branch (Skip):** → "Split In Batches" (continue loop)
**False Branch (Create):** → "Create a record"

---

### Node 8: Create a record
**Node ID:** `bfb7c3aa-36f1-4928-91df-597fcd3835c9`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [528, 192]

**Airtable Configuration:**
- **Base ID:** `appRUgK44hQnXH1PM` (P5 Social Posts)
- **Table ID:** `tbllJMN2QBPJoG3jA` (P5 Social Posts)
- **Operation:** Create record

**Credentials:**
- **Name:** Airtable Pivot Studio
- **ID:** `oWcf5peCOkQe8Rem`

**Column Mapping:**
| Airtable Field | Source Expression | Type |
|----------------|-------------------|------|
| source_record_id | `{{ $('Split In Batches').item.json.id }}` | Text |
| label | `{{ $('Split In Batches').item.json.fields.label }}` | Text |
| headline | `{{ $('Split In Batches').item.json.fields.headline }}` | Text |
| image_raw_url | `{{ $('Split In Batches').item.json.fields.image_url }}` | Text |
| Raw | `{{ $('Split In Batches').item.json.fields.raw }}` | Long Text |
| publish_status | `ready` | Select (ready/processing/published) |
| Order | `{{ $('Split In Batches').item.json.fields.slot_order }}` | Number |
| Name | `{{ $('Split In Batches').item.json.fields.headline }}` | Text |
| b1 | `{{ $('Split In Batches').item.json.fields.b1 }}` | Text |
| b2 | `{{ $('Split In Batches').item.json.fields.b2 }}` | Text |
| b3 | `{{ $('Split In Batches').item.json.fields.b3 }}` | Text |

**Output:** Created record → Connects to "Mark Social Synced"

---

### Node 9: Mark Social Synced
**Node ID:** `mark-social-synced`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [752, 192]

**HTTP Configuration:**
- **Method:** PATCH
- **URL:** `https://api.airtable.com/v0/appglKSJZxmA9iHpl/tbla16LJCf5Z6cRn3/{{ $('Split In Batches').item.json.id }}`

**Headers:**
| Header | Value |
|--------|-------|
| Authorization | `Bearer [REDACTED]` |
| Content-Type | `application/json` |

**Request Body:**
```json
{"fields": {"social_status": "synced"}}
```

**Purpose:** Updates the source decoration record to mark it as synced to social.

**Output:** → Connects back to "Split In Batches" (continue loop)

---

## Data Flow Diagram

```
Schedule Trigger (4:30 AM / 5:00 AM EST)
       │
       ▼
GET Decorated Stories Ready for Social
(filter: image_status='generated' AND social_status empty/pending)
       │
       ▼
Extract Records (clean HTML from raw)
       │
       ▼
Split In Batches
       │
       ├─────────────────────────────────────────────┐
       ▼                                             │
Find Existing in P5 Social Posts                    │
(check if source_record_id already exists)          │
       │                                             │
       ▼                                             │
Check If Exists (add action: skip/create)           │
       │                                             │
       ▼                                             │
Does Newsletter Post Already Exist?                 │
       │              │                              │
       ▼              ▼                              │
     YES            NO                              │
   (skip)        (create)                           │
       │              │                              │
       │              ▼                              │
       │      Create a record                       │
       │    (P5 Social Posts table)                 │
       │              │                              │
       │              ▼                              │
       │      Mark Social Synced                    │
       │    (social_status='synced')                │
       │              │                              │
       └──────────────┴──────────────────────────────┘
                      │
                      ▼
             (Loop until all done)
```

---

## P5 Social Posts Table Schema

**Base:** P5 Social Posts (`appRUgK44hQnXH1PM`)
**Table:** P5 Social Posts (`tbllJMN2QBPJoG3jA`)

| Field | Type | Description |
|-------|------|-------------|
| source_record_id | Text | Links back to Decoration table record ID |
| Name | Text | Same as headline |
| headline | Text | Story headline |
| label | Text | Topic label (e.g., "JOBS & ECONOMY") |
| b1 | Text | Bullet point 1 |
| b2 | Text | Bullet point 2 |
| b3 | Text | Bullet point 3 |
| Raw | Long Text | Cleaned article content (HTML stripped) |
| image_raw_url | Text | Image URL from Cloudflare CDN |
| publish_status | Select | "ready", "processing", "published" |
| Order | Number | Slot order (1-5) |

---

## Deduplication Logic

The workflow prevents duplicate social posts by:

1. **Query Filter:** Only fetches records where `social_status` is empty or "pending"
2. **Existence Check:** For each record, queries P5 Social Posts by `source_record_id`
3. **Skip Logic:** If existing record found, skips to next item in batch
4. **Sync Flag:** After creating, updates source record with `social_status='synced'`

**Filter Formula for Eligible Stories:**
```
AND({image_status}='generated', OR({social_status}='', {social_status}='pending'))
```

---

## API Credentials

### Airtable API

**API Key:** `[REDACTED - use environment variable]`

**Bases Used:**
| Base | Base ID | Purpose |
|------|---------|---------|
| AI Editor 2.0 | `appglKSJZxmA9iHpl` | Source decoration records |
| P5 Social Posts | `appRUgK44hQnXH1PM` | Target social posts queue |

**Endpoints Used:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v0/{baseId}/{tableId}` | GET | Fetch records |
| `/v0/{baseId}/{tableId}` | POST | Create record |
| `/v0/{baseId}/{tableId}/{recordId}` | PATCH | Update record |

---

## Content Cleaning

The "Extract Records" node cleans the `raw` field by:

1. **Removing HTML tags:** `raw.replace(/<[^>]*>/g, '')`
2. **Decoding HTML entities:**
   - `&nbsp;` → space
   - `&amp;` → `&`
   - `&lt;` → `<`
   - `&gt;` → `>`
   - `&quot;` → `"`
   - `&#39;` → `'`
3. **Normalizing whitespace:** Multiple spaces/newlines → single space
4. **Trimming:** Remove leading/trailing whitespace

---

## Downstream Workflows

The P5 Social Posts table feeds into downstream social media automation workflows (not part of AI Editor 2.0):

- **LinkedIn posting**
- **X/Twitter posting**
- **Facebook posting**

These workflows monitor the `publish_status` field and process records with status "ready".

---

*Last updated: December 23, 2025*
