# AI Editor 2.0 Infrastructure - Step 4: HTML Compile and Send Workflow

**Date:** December 23, 2025
**Workflow Name:** STEP 4 AI Editor 2.0 - Compile HTML and Send
**Workflow ID:** `NKjC8hb0EDHIXx3U`
**Total Nodes:** 17

---

## Overview

Compiles the 5 decorated stories into HTML email format, generates newsletter summaries, archives to Newsletter Issues table, and sends via Mautic email marketing platform.

---

## Schedule

| Schedule | Cron Expression | EST Time | Purpose |
|----------|-----------------|----------|---------|
| HTML Compilation | `0 3 * * 2-6` | 10:00 PM | Compile HTML template |
| Email Send | `0 10 * * 1-5` | 5:00 AM | Send via Mautic |

---

## AI Models Used

| Model | Provider | Purpose |
|-------|----------|---------|
| `claude-sonnet-4-5-20250929` | Anthropic | Newsletter summary generation |

---

## Airtable Tables

### Input Tables

| Table | Base | Table ID | Purpose |
|-------|------|----------|---------|
| Newsletter Issue Stories (Decoration) | AI Editor 2.0 | `tbla16LJCf5Z6cRn3` | Decorated stories with images |
| Selected Slots | AI Editor 2.0 | `tblzt2z7r512Kto3O` | Issue metadata, subject line |

### Output Tables

| Table | Base | Table ID | Purpose |
|-------|------|----------|---------|
| Newsletter Issues | Pivot Media Master | `tbl7mcCCGbjEfli25` | Compiled HTML storage |
| Newsletter Issues Archive | Pivot Media Master | `tblHo0xNj8nbzMHNI` | Sent email archive |

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
        "expression": "0 3 * * 2-6"
      },
      {
        "field": "cronExpression",
        "expression": "0 10 * * 1-5"
      }
    ]
  }
}
```

**Purpose:**
- 10:00 PM EST: Compile HTML
- 5:00 AM EST: Send email

---

### Node 2: Get Decorated Stories
**Node ID:** `get-decorated-stories`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1696, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories)

**Filter Formula:**
```
{image_status}='generated'
```

**Sort:** `slot_order` ASC
**Max Records:** 5

**Fields Retrieved:**
| Field | Type |
|-------|------|
| story_id | Text |
| issue_id | Text |
| slot_order | Number |
| headline | Text |
| ai_dek | Text |
| label | Text |
| b1 | Text |
| b2 | Text |
| b3 | Text |
| image_url | Text |
| core_url | Text |

**Output:** 5 decorated stories → Connects to "Aggregate Stories"

---

### Node 3: Aggregate Stories
**Node ID:** `aggregate-stories`
**Type:** `n8n-nodes-base.aggregate`
**Version:** 1
**Position:** [-1472, 256]

**Configuration:**
```json
{
  "aggregate": "aggregateAllItemData",
  "destinationFieldName": "stories"
}
```

**Purpose:** Combines 5 stories into single object for HTML template.

**Output:** Aggregated stories → Connects to "Get Subject Line"

---

### Node 4: Get Subject Line
**Node ID:** `get-subject-line`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1248, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)

**Filter Formula:**
```
{status}='pending'
```

**Sort:** `issue_date` DESC
**Max Records:** 1

**Fields Retrieved:**
| Field | Type |
|-------|------|
| issue_id | Text |
| issue_date | Text |
| subject_line | Text |

**Output:** Issue metadata → Connects to "Compile HTML"

---

### Node 5: Compile HTML
**Node ID:** `compile-html`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-1024, 256]

**JavaScript Code:**
```javascript
const stories = $('Aggregate Stories').first().json.stories;
const issue = $('Get Subject Line').first().json.fields;

// HTML Template structure
const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${issue.subject_line}</title>
  <style>
    /* Responsive email styles */
    body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
    .container { max-width: 640px; margin: 0 auto; }
    .story-block { padding: 24px; border-bottom: 1px solid #eee; }
    .label {
      background: #ff6f00;
      color: white;
      padding: 4px 12px;
      font-size: 12px;
      border-radius: 4px;
    }
    .headline { font-size: 22px; font-weight: bold; margin: 16px 0; }
    .dek { font-size: 16px; color: #666; margin-bottom: 16px; }
    .bullet { margin: 8px 0; line-height: 1.5; }
    .read-more {
      color: #ff6f00;
      text-decoration: none;
      font-weight: bold;
    }
    img { max-width: 100%; height: auto; }
  </style>
</head>
<body>
  <div class="container">
    <!-- Preheader -->
    <span style="display:none;">${issue.subject_line}</span>

    <!-- Header -->
    <div style="text-align:center; padding:24px;">
      <img src="https://img.pivotnews.com/pivot5-logo.png" alt="Pivot 5" width="200">
      <p style="color:#666;">5 headlines • 5 minutes • 5 days a week</p>
    </div>

    <!-- Stories -->
    ${stories.map((story, i) => `
      <div class="story-block">
        <span class="label">${story.fields.label}</span>
        <h2 class="headline">${story.fields.headline}</h2>
        <img src="${story.fields.image_url}" alt="${story.fields.headline}">
        <p class="dek">${story.fields.ai_dek}</p>
        <ul>
          <li class="bullet">${story.fields.b1}</li>
          <li class="bullet">${story.fields.b2}</li>
          <li class="bullet">${story.fields.b3}</li>
        </ul>
        <a href="${story.fields.core_url}" class="read-more">Read More →</a>
      </div>
    `).join('')}

    <!-- Footer -->
    <div style="padding:24px; text-align:center; background:#f5f5f5;">
      <p>© 2025 Pivot Media. All rights reserved.</p>
      <a href="{unsubscribe_url}">Unsubscribe</a> |
      <a href="{preferences_url}">Manage Preferences</a>
    </div>
  </div>
</body>
</html>
`;

return [{
  json: {
    html: html,
    issue_id: issue.issue_id,
    issue_date: issue.issue_date,
    subject_line: issue.subject_line
  }
}];
```

**Output:** Compiled HTML → Connects to "Generate Summary"

---

### Node 6: Generate Summary
**Node ID:** `generate-summary`
**Type:** `@n8n/n8n-nodes-langchain.chainLlm`
**Version:** 1.4
**Position:** [-800, 256]

**AI Model Configuration:**
- **Model:** `claude-sonnet-4-5-20250929`
- **Temperature:** 0.5

**System Prompt:**
```
Generate two newsletter summaries:

HEADLINES FROM TODAY'S ISSUE:
{{ $('Aggregate Stories').first().json.stories.map(s => s.fields.headline).join('\n') }}

1. SUMMARY (exactly 15 words): A punchy overview of today's newsletter
2. SUMMARY_PLUS (exactly 20 words): Slightly more detailed overview

Return as JSON:
{
  "summary": "...",
  "summary_plus": "..."
}
```

**Output:** Summaries → Connects to "Prepare Issue Record"

---

### Node 7: Prepare Issue Record
**Node ID:** `prepare-issue-record`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-576, 256]

**JavaScript Code:**
```javascript
const compiled = $('Compile HTML').first().json;
const summaries = $('Generate Summary').first().json;

return [{
  json: {
    issue_id: compiled.issue_id,
    newsletter_id: 'pivot_ai',
    html: compiled.html,
    subject_line: compiled.subject_line,
    summary: summaries.summary,
    summary_plus: summaries.summary_plus,
    status: 'compiled'
  }
}];
```

---

### Node 8: Write Newsletter Issue
**Node ID:** `write-newsletter-issue`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-352, 256]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tbl7mcCCGbjEfli25` (Newsletter Issues)
- **Operation:** Upsert
- **Match Field:** `issue_id`

**Column Mapping:**
| Airtable Field | Source Expression |
|----------------|-------------------|
| issue_id | `{{ $json.issue_id }}` |
| newsletter_id | `{{ $json.newsletter_id }}` |
| html | `{{ $json.html }}` |
| subject_line | `{{ $json.subject_line }}` |
| summary | `{{ $json.summary }}` |
| summary_plus | `{{ $json.summary_plus }}` |
| status | `{{ $json.status }}` |

**Output:** Written issue → Connects to "Check Time for Send"

---

### Node 9: Check Time for Send
**Node ID:** `check-time-for-send`
**Type:** `n8n-nodes-base.if`
**Version:** 2
**Position:** [-128, 256]

**Purpose:** Determines if this is the 5 AM send trigger or 10 PM compile trigger.

**Condition:**
```javascript
// Check if current hour is 5 AM EST (10:00 UTC)
const hour = new Date().getUTCHours();
return hour >= 9 && hour <= 11; // 5 AM - 6 AM EST window
```

**True Branch:** → "Create Mautic Email"
**False Branch:** → End (compile only)

---

### Node 10: Create Mautic Email
**Node ID:** `create-mautic-email`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [96, 256]

**HTTP Configuration:**
- **Method:** POST
- **URL:** `https://app.pivotnews.com/api/emails/new`

**Authentication:**
- **Type:** OAuth2
- **Credentials:** Mautic OAuth2

**Request Body:**
```json
{
  "name": "{{ $json.issue_id }}",
  "subject": "{{ $json.subject_line }}",
  "customHtml": "{{ $json.html }}",
  "emailType": "list",
  "lists": [1],
  "isPublished": true,
  "template": null,
  "utmTags": {
    "utmSource": "newsletter",
    "utmMedium": "email",
    "utmCampaign": "pivot5_daily"
  }
}
```

**Output:** Mautic email ID → Connects to "Attach Transport"

---

### Node 11: Attach Transport
**Node ID:** `attach-transport`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [320, 256]

**HTTP Configuration:**
- **Method:** PATCH
- **URL:** `https://app.pivotnews.com/api/emails/{{ $json.email.id }}/transport`

**Request Body:**
```json
{
  "transport_id": "{{ $env.GREENARROW_TRANSPORT_ID }}"
}
```

**Purpose:** Associates email with GreenArrow SMTP transport for deliverability.

---

### Node 12: Send Email
**Node ID:** `send-email`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [544, 256]

**HTTP Configuration:**
- **Method:** POST
- **URL:** `https://app.pivotnews.com/api/emails/{{ $json.email.id }}/send`

**Request Body:**
```json
{
  "lists": [1]
}
```

**Output:** Send response → Connects to "Archive Sent"

---

### Node 13: Archive Sent
**Node ID:** `archive-sent`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [768, 256]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tblHo0xNj8nbzMHNI` (Newsletter Issues Archive)
- **Operation:** Create record

**Column Mapping:**
| Airtable Field | Source Expression |
|----------------|-------------------|
| issue_id | `{{ $('Prepare Issue Record').first().json.issue_id }}` |
| sent_status | `sent` |
| mautic_email_id | `{{ $json.email.id }}` |
| mautic_response | `{{ JSON.stringify($json) }}` |
| sent_at | `{{ $now.toISO() }}` |

---

### Node 14: Update Selected Slots Status
**Node ID:** `update-selected-slots-status`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [992, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)
- **Operation:** Update record

**Column Mapping:**
| Airtable Field | Value |
|----------------|-------|
| status | `sent` |

---

## Data Flow Diagram

```
Schedule Trigger (10 PM compile / 5 AM send)
       │
       ▼
Get Decorated Stories (image_status='generated')
       │
       ▼
Aggregate Stories (combine 5 stories)
       │
       ▼
Get Subject Line (from Selected Slots)
       │
       ▼
Compile HTML (build email template)
       │
       ▼
Generate Summary (15 + 20 word versions)
       │
       ▼
Prepare Issue Record
       │
       ▼
Write Newsletter Issue (tbl7mcCCGbjEfli25)
       │
       ▼
Check Time for Send?
   │         │
   ▼         ▼
 5 AM      10 PM
(send)    (compile only)
   │
   ▼
Create Mautic Email
   │
   ▼
Attach Transport (GreenArrow)
   │
   ▼
Send Email
   │
   ▼
Archive Sent (tblHo0xNj8nbzMHNI)
   │
   ▼
Update Selected Slots Status (status='sent')
```

---

## Mautic API Configuration

**Base URL:** `https://app.pivotnews.com`

**Authentication:**
- **Type:** OAuth2
- **Client ID:** `1_4lyjt9grlc04o0wgwkkcgg48w4oo88s40wsog44sow0o808ggk`
- **Client Secret:** Environment variable

**Endpoints Used:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/emails/new` | POST | Create new email |
| `/api/emails/{id}/transport` | PATCH | Attach transport |
| `/api/emails/{id}/send` | POST | Send email |

**GreenArrow Transport:**
- **Transport ID:** Environment variable `GREENARROW_TRANSPORT_ID`
- **Purpose:** High-deliverability SMTP relay

---

## Newsletter Issues Table Schema

**Base:** Pivot Media Master (`appwSozYTkrsQWUXB`)
**Table:** Newsletter Issues (`tbl7mcCCGbjEfli25`)

| Field | Type | Description |
|-------|------|-------------|
| issue_id | Text | Unique issue identifier (e.g., "pivot5_2025-12-23") |
| newsletter_id | Text | "pivot_ai", "pivot_build", "pivot_invest" |
| html | Long Text | Compiled HTML email content |
| subject_line | Text | Email subject |
| summary | Text | 15-word summary |
| summary_plus | Text | 20-word summary |
| status | Select | "compiled", "next_send", "sent" |
| sent_at | DateTime | When email was sent |

---

## Newsletter Issues Archive Table Schema

**Base:** Pivot Media Master (`appwSozYTkrsQWUXB`)
**Table:** Newsletter Issues Archive (`tblHo0xNj8nbzMHNI`)

| Field | Type | Description |
|-------|------|-------------|
| issue_id | Text | Links to Newsletter Issues |
| sent_status | Text | "sent", "failed" |
| mautic_email_id | Number | Mautic email record ID |
| mautic_response | Long Text | Full API response JSON |
| sent_at | DateTime | Timestamp of send |

---

## HTML Email Template Structure

### Sections

1. **Preheader** - Hidden text that appears in email previews
2. **Header** - Logo and tagline ("5 headlines • 5 minutes • 5 days a week")
3. **Story Blocks (x5)** - Each contains:
   - Topic label (orange badge)
   - Headline
   - Story image
   - Dek/intro
   - 3 bullet points
   - "Read More" link
4. **Footer** - Copyright, unsubscribe, manage preferences

### Styling

- **Max Width:** 640px
- **Primary Color:** `#ff6f00` (orange)
- **Font:** Arial, sans-serif
- **Responsive:** Mobile-friendly with viewport meta tag

---

## Environment Variables Required

```bash
# Mautic OAuth2
MAUTIC_CLIENT_ID=1_4lyjt9grlc04o0wgwkkcgg48w4oo88s40wsog44sow0o808ggk
MAUTIC_CLIENT_SECRET=<secret>

# GreenArrow SMTP
GREENARROW_TRANSPORT_ID=<transport_id>
```

---

*Last updated: December 23, 2025*
