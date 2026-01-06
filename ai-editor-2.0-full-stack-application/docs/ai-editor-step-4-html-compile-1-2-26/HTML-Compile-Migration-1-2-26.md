# Step 4: HTML Compile & Send Migration Plan

**Date:** January 2, 2026
**Author:** Claude Code
**Status:** IMPLEMENTATION COMPLETE - PENDING TESTING

---

## Implementation Status (Updated January 2, 2026)

### Phase 1: Backend Python Workers - ✅ COMPLETE

| Task | File | Status |
|------|------|--------|
| Task 1.1: Airtable methods | `/workers/utils/airtable.py` | ✅ Complete |
| Task 1.2: Mautic API client | `/workers/utils/mautic.py` | ✅ Complete |
| Task 1.3: Gmail API client | `/workers/utils/gmail.py` | ✅ Complete |
| Task 1.4: HTML compile worker | `/workers/jobs/html_compile.py` | ✅ Complete |
| Task 1.5: Mautic send worker | `/workers/jobs/mautic_send.py` | ✅ Complete |
| Task 1.6: Gmail send worker | `/workers/jobs/gmail_send.py` | ✅ Complete |
| Task 1.7: Trigger routes | `/workers/trigger.py` | ✅ Complete |
| HTML stripper utility | `/workers/utils/html_stripper.py` | ✅ Complete |

### Phase 2: Frontend UI Components - ✅ COMPLETE

| Task | File | Status |
|------|------|--------|
| Step 4 state management | `/src/app/(dashboard)/step/[id]/page.tsx` | ✅ Complete |
| Three action buttons UI | `/src/app/(dashboard)/step/[id]/page.tsx` | ✅ Complete |
| Job polling for Mautic/Gmail | `/src/app/(dashboard)/step/[id]/page.tsx` | ✅ Complete |
| Cancel job functionality | `/src/app/(dashboard)/step/[id]/page.tsx` | ✅ Complete |
| Running status banners | `/src/app/(dashboard)/step/[id]/page.tsx` | ✅ Complete |

### Phase 3: Testing - ⏳ PENDING

| Test | Status |
|------|--------|
| HTML Compile job execution | ⏳ Pending |
| Mautic API authentication | ⏳ Pending |
| Mautic send execution | ⏳ Pending |
| Gmail API authentication | ⏳ Pending |
| Gmail test send execution | ⏳ Pending |
| End-to-end workflow test | ⏳ Pending |

### Phase 4: Deployment - ⏳ PENDING

| Task | Status |
|------|--------|
| Environment variables on Render | ⏳ Pending |
| Worker deployment verification | ⏳ Pending |
| Production test run | ⏳ Pending |

---

## Overview

Migrate n8n workflow "STEP 4 AI Editor 2.0 - Compile HTML and Send" (ID: `NKjC8hb0EDHIXx3U`) to the AI Editor 2.0 full-stack application with a new frontend UI featuring three action cards:

1. **Compile HTML** - Generate responsive email HTML from decorated stories
2. **Send via Mautic** - Create and send email campaign via Mautic API
3. **Manual Send (Gmail)** - Send test email via Gmail for deliverability testing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                          │
├─────────────────────────────────────────────────────────────────────┤
│  Step 4 Page: /src/app/(dashboard)/step/[id]/page.tsx               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐        │
│  │  Compile HTML   │ │ Send via Mautic │ │  Manual Send    │        │
│  │  [Run Button]   │ │  [Run Button]   │ │  [Run Button]   │        │
│  │  Status: ●      │ │  Status: ●      │ │  Status: ●      │        │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API ROUTES (Next.js)                         │
├─────────────────────────────────────────────────────────────────────┤
│  POST /api/jobs                                                     │
│    step: "html_compile" | "mautic_send" | "gmail_send"              │
│    params: { issue_id?: string }                                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TRIGGER SERVICE (Flask)                          │
├─────────────────────────────────────────────────────────────────────┤
│  /workers/trigger.py                                                │
│  Routes: /jobs/html_compile, /jobs/mautic_send, /jobs/gmail_send    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PYTHON WORKERS (RQ Jobs)                         │
├─────────────────────────────────────────────────────────────────────┤
│  /workers/jobs/html_compile.py    - Compile HTML from decorations   │
│  /workers/jobs/mautic_send.py     - Send via Mautic API             │
│  /workers/jobs/gmail_send.py      - Send test via Gmail             │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                           │
├─────────────────────────────────────────────────────────────────────┤
│  Airtable API    - Read decorations, write Newsletter Issues        │
│  Claude API      - Generate 15/20 word summaries                    │
│  Mautic API      - Create email, attach transport, send             │
│  Gmail API       - Send test emails                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Airtable Configuration

### Base IDs
| Base Name | Base ID | Environment Variable |
|-----------|---------|---------------------|
| AI Editor 2.0 | `appglKSJZxmA9iHpl` | `AI_EDITOR_BASE_ID` |
| Pivot Media Master | `appwSozYTkrsQWUXB` | `AIRTABLE_BASE_ID` |

### Table IDs and Fields

#### 1. Newsletter Issue Stories (Decoration) - INPUT
- **Base:** AI Editor 2.0 (`appglKSJZxmA9iHpl`)
- **Table ID:** `tbla16LJCf5Z6cRn3`
- **Query Filter:** `AND({image_status} = 'generated', {issue_id} = 'Pivot 5 - {date}')`

| Field Name | Type | Description |
|------------|------|-------------|
| `issue_id` | String | Issue identifier (e.g., "Pivot 5 - Jan 02") |
| `slot_order` | Number | Story position 1-5 |
| `story_id` | String | Story identifier |
| `headline` | String | AI-generated headline |
| `label` | String | Topic category (Competition, Infrastructure, Health, etc.) |
| `b1` | String | Bullet point 1 |
| `b2` | String | Bullet point 2 |
| `b3` | String | Bullet point 3 |
| `pivotnews_url` | URL | Link to story on pivotnews.com |
| `image_url` | URL | Generated image URL |
| `image_status` | String | "generated" when ready for compile |

#### 2. AI Editor - Selected Slots - SUBJECT LINE SOURCE
- **Base:** AI Editor 2.0 (`appglKSJZxmA9iHpl`)
- **Table ID:** `tblzt2z7r512Kto3O`
- **Query Filter:** `{issue_id} = '{issue_id}'`

| Field Name | Type | Description |
|------------|------|-------------|
| `issue_id` | String | Issue identifier |
| `subject_line` | String | Email subject line |

#### 3. Newsletter Issues Final - OUTPUT (Compile)
- **Base:** AI Editor 2.0 (`appglKSJZxmA9iHpl`)
- **Table ID:** `tblPBfWZzRdLuiqYr`
- **Operation:** CREATE

| Field Name | Type | Description |
|------------|------|-------------|
| `issue_id` | String | Issue identifier |
| `newsletter_id` | String | "pivot_ai" |
| `html` | Long Text | Compiled HTML email |
| `subject_line` | String | Email subject |
| `status` | Select | "next-send" after compile |
| `summary` | String | 15-word summary (stories 1-3) |
| `summary_plus` | String | 20-word summary (stories 4-5) |

#### 4. Newsletter Issues Archive - OUTPUT (After Send)
- **Base:** AI Editor 2.0 (`appglKSJZxmA9iHpl`)
- **Table ID:** `tblB7j5qGcTxyXmfa`
- **Operation:** UPSERT (match on `issue_id`)

| Field Name | Type | Description |
|------------|------|-------------|
| `issue_id` | String | Issue identifier |
| `newsletter_id` | String | "pivot_ai" |
| `send_date` | Date | Send date |
| `sent_at` | DateTime | Actual send timestamp (ET) |
| `subject_line` | String | Email subject |
| `status` | Select | "sent", "failed", "partial_failure" |
| `html` | Long Text | Compiled HTML |
| `summary` | String | 15-word summary |
| `mautic_sent_count` | Number | Recipients sent |
| `mautic_failed_recipients` | Number | Failed deliveries |
| `mautic_send_status` | String | "success", "partial_failure", "failed" |
| `mautic_response_raw` | Long Text | Raw Mautic API response JSON |

---

## Mautic API Configuration

### Environment Variables Required
```bash
MAUTIC_BASE_URL=https://app.pivotnews.com
MAUTIC_CLIENT_ID=<oauth_client_id>
MAUTIC_CLIENT_SECRET=<oauth_client_secret>
MAUTIC_USERNAME=<username>
MAUTIC_PASSWORD=<password>
```

### API Endpoints

#### 1. Create Email
```
POST https://app.pivotnews.com/api/emails/new
Authorization: Bearer {oauth_token}
Content-Type: application/json

{
  "name": "{issue_id}",
  "subject": "{subject_line}",
  "customHtml": "{plain_html}",
  "emailType": "list",
  "lists": [5, 14],
  "fromAddress": "pivotnews@daily.pivotnews.com",
  "fromName": "Daily AI Briefing",
  "replyToAddress": "pivotnews@daily.pivotnews.com",
  "headers": {
    "X-GreenArrow-MailClass": "daily.pivotnews.com"
  },
  "isPublished": true,
  "template": "mautic_code_mode"
}
```

**Response:**
```json
{
  "email": {
    "id": 12345,
    "name": "Pivot 5 - Jan 02",
    ...
  }
}
```

#### 2. Attach Transport
```
POST https://app.pivotnews.com/api/multipleTransport/transportEmail/{email_id}
Authorization: Bearer {oauth_token}
Content-Type: application/json

{
  "transportId": 3
}
```

#### 3. Send Email
```
POST https://app.pivotnews.com/api/emails/{email_id}/send
Authorization: Bearer {oauth_token}
```

**Response:**
```json
{
  "sentCount": 50000,
  "failedRecipients": 0
}
```

---

## Gmail Configuration (Manual Send)

### Environment Variables Required
```bash
GMAIL_SERVICE_ACCOUNT_JSON=<base64_encoded_service_account>
# OR
GMAIL_CLIENT_ID=<oauth_client_id>
GMAIL_CLIENT_SECRET=<oauth_client_secret>
GMAIL_REFRESH_TOKEN=<refresh_token>
```

### Recipients
```python
MANUAL_SEND_RECIPIENTS = [
    "patsimmons21@gmail.com",
    "hi@kunal.live",
    "pat@persimmons.studio"
]
```

### Email Format
- **Subject:** Dynamic from `subject_line` field
- **Body:** `plain_html` (stripped/cleaned HTML for deliverability)
- **Sender Name:** "Daily AI Briefing"

---

## Implementation Tasks

### Phase 1: Backend Python Workers

#### Task 1.1: Update `/workers/utils/airtable.py`

Add new table constants and methods:

```python
# New table IDs
NEWSLETTER_ISSUES_FINAL_TABLE = "tblPBfWZzRdLuiqYr"
NEWSLETTER_ISSUES_ARCHIVE_TABLE = "tblB7j5qGcTxyXmfa"
SELECTED_SLOTS_TABLE = "tblzt2z7r512Kto3O"

# New methods
def get_decorated_stories_for_compile(self, issue_id: str) -> list:
    """Fetch stories with image_status='generated' for specific issue"""

def get_subject_line(self, issue_id: str) -> str:
    """Fetch subject_line from Selected Slots table"""

def create_newsletter_issue_final(self, data: dict) -> dict:
    """Create record in Newsletter Issues Final table"""

def get_newsletter_issue_for_send(self) -> dict:
    """Fetch issue with status='next-send'"""

def archive_newsletter_issue(self, data: dict) -> dict:
    """Upsert record to Newsletter Issues Archive"""

def delete_newsletter_issue_final(self, record_id: str) -> bool:
    """Delete record from Newsletter Issues Final after send"""
```

#### Task 1.2: Create `/workers/utils/mautic.py`

New Mautic API client:

```python
class MauticClient:
    def __init__(self):
        self.base_url = os.environ.get("MAUTIC_BASE_URL", "https://app.pivotnews.com")
        self.oauth_token = None

    def authenticate(self) -> str:
        """Get OAuth2 access token"""

    def create_email(self, issue_id: str, subject: str, html: str) -> dict:
        """Create email campaign in Mautic"""

    def attach_transport(self, email_id: int, transport_id: int = 3) -> dict:
        """Attach GreenArrow transport to email"""

    def send_email(self, email_id: int) -> dict:
        """Trigger email send, returns sentCount and failedRecipients"""
```

#### Task 1.3: Create `/workers/utils/gmail.py`

Gmail API client for manual sends:

```python
class GmailClient:
    def __init__(self):
        self.service = self._build_service()

    def send_email(self, to: list, subject: str, html_body: str, sender_name: str) -> dict:
        """Send email via Gmail API"""
```

#### Task 1.4: Update `/workers/jobs/html_compile.py`

Complete rewrite matching n8n workflow:

```python
def compile_html() -> dict:
    """
    Step 4a: Compile HTML from decorated stories

    1. Fetch decorated stories (image_status='generated') for today's issue
    2. Fetch subject_line from Selected Slots
    3. Group and sort stories by slot_order
    4. Generate summaries via Claude (15-word for top 3, 20-word for 4-5)
    5. Compile responsive HTML email using template
    6. Strip HTML for deliverability (plain_html version)
    7. Create record in Newsletter Issues Final (status='next-send')

    Returns:
        {
            "compiled": bool,
            "issue_id": str,
            "subject_line": str,
            "html_length": int,
            "plain_html_length": int,
            "summary": str,
            "summary_plus": str,
            "errors": list
        }
    """
```

#### Task 1.5: Update `/workers/jobs/mautic_send.py`

Complete implementation:

```python
def send_via_mautic() -> dict:
    """
    Step 4b: Send newsletter via Mautic

    1. Fetch newsletter issue (status='next-send')
    2. Create email in Mautic with plain_html
    3. Attach transport (ID: 3)
    4. Send email
    5. Archive with send metrics
    6. Delete from Newsletter Issues Final

    Returns:
        {
            "sent": bool,
            "issue_id": str,
            "mautic_email_id": int,
            "sent_count": int,
            "failed_recipients": int,
            "errors": list
        }
    """
```

#### Task 1.6: Create `/workers/jobs/gmail_send.py`

New file for manual test sends:

```python
def send_via_gmail() -> dict:
    """
    Step 4c: Send test email via Gmail

    1. Fetch newsletter issue (status='next-send')
    2. Strip HTML for deliverability
    3. Send to test recipients via Gmail

    Returns:
        {
            "sent": bool,
            "issue_id": str,
            "recipients": list,
            "errors": list
        }
    """
```

#### Task 1.7: Update `/workers/trigger.py`

Add new job routes:

```python
JOB_FUNCTIONS = {
    # ... existing jobs
    "html_compile": "jobs.html_compile.compile_html",
    "mautic_send": "jobs.mautic_send.send_via_mautic",
    "gmail_send": "jobs.gmail_send.send_via_gmail",
}

QUEUE_MAP = {
    # ... existing queues
    "html_compile": "default",
    "mautic_send": "high",
    "gmail_send": "high",
}
```

---

### Phase 2: Frontend UI Components

#### Task 2.1: Update `/src/lib/step-config.ts`

Update Step 4 configuration:

```typescript
{
  id: 4,
  name: "HTML Compile & Send",
  description: "Compile decorated stories into HTML and send newsletter",
  schedule: "Compile: 10 PM ET | Send: 5 AM ET",
  icon: "mail",
  actions: [
    {
      id: "html_compile",
      name: "Compile HTML",
      description: "Generate responsive email from decorated stories",
      jobStep: "html_compile",
      buttonText: "Compile Now",
      buttonIcon: "code"
    },
    {
      id: "mautic_send",
      name: "Send via Mautic",
      description: "Send to all subscribers via Mautic + GreenArrow",
      jobStep: "mautic_send",
      buttonText: "Send Newsletter",
      buttonIcon: "send",
      confirmRequired: true,
      confirmMessage: "This will send to ALL subscribers. Are you sure?"
    },
    {
      id: "gmail_send",
      name: "Manual Test Send",
      description: "Send test email to internal team via Gmail",
      jobStep: "gmail_send",
      buttonText: "Send Test",
      buttonIcon: "mail"
    }
  ],
  prompts: [
    { id: "summary_generator", name: "Summary Generator", model: "claude-sonnet-4-5-20250929", temperature: 0.5 }
  ],
  dataTable: {
    name: "Newsletter Issues Final",
    tableId: "tblPBfWZzRdLuiqYr",
    baseId: "appglKSJZxmA9iHpl"
  }
}
```

#### Task 2.2: Create `/src/components/step/step-action-card.tsx`

New reusable action card component:

```tsx
interface StepActionCardProps {
  action: {
    id: string;
    name: string;
    description: string;
    jobStep: string;
    buttonText: string;
    buttonIcon: string;
    confirmRequired?: boolean;
    confirmMessage?: string;
  };
  onRun: (jobStep: string) => void;
  isRunning: boolean;
  lastResult?: {
    success: boolean;
    timestamp: string;
    data?: any;
  };
}

export function StepActionCard({ action, onRun, isRunning, lastResult }: StepActionCardProps) {
  // Card with:
  // - Action name and description
  // - Run button with icon
  // - Status indicator (idle/running/success/error)
  // - Last run timestamp
  // - Confirmation dialog if confirmRequired
}
```

#### Task 2.3: Update `/src/app/(dashboard)/step/[id]/page.tsx`

Add Step 4 specific UI:

```tsx
// For step 4, render action cards grid instead of single run button
{step.id === 4 && step.actions && (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
    {step.actions.map(action => (
      <StepActionCard
        key={action.id}
        action={action}
        onRun={handleRunAction}
        isRunning={runningAction === action.id}
        lastResult={actionResults[action.id]}
      />
    ))}
  </div>
)}
```

---

### Phase 3: HTML Template

#### Full HTML Template (Port from n8n)

Store in `/workers/templates/newsletter_email.html` or as Python string constant:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{subject}</title>
  <style>
    body { margin: 0; padding: 0; background-color: #f3f4f6; }
    table { border-collapse: collapse; }
    img { border: 0; max-width: 100%; height: auto; display: block; }
    .wrapper { width: 640px; max-width: 100%; }
    @media only screen and (max-width: 640px) {
      .wrapper { width: 100% !important; }
      .stack { display: block !important; width: 100% !important; }
    }
  </style>
</head>
<body style="margin:0; padding:0; background-color:#f3f4f6;">
  <!-- Hidden preheader -->
  <div style="display:none; max-height:0; overflow:hidden; opacity:0; font-size:1px; line-height:1px; color:#f3f4f6;">
    {preheader}
  </div>

  <center style="width:100%; background-color:#f3f4f6;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" class="wrapper" cellspacing="0" cellpadding="0" border="0" style="background-color:#f3f4f6;">

            <!-- Header with logo -->
            <tr>
              <td style="padding:0 0 16px 0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td align="center" style="padding:0 12px;">
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#ffffff;">
                        <tr>
                          <td style="padding:18px 22px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                              <tr>
                                <td style="width:37%;"></td>
                                <td style="width:34%; text-align:center; vertical-align:middle;">
                                  <img src="https://img.pivotnews.com/cdn-cgi/imagedelivery/KXy14RehLGC3ziMxzD_shA/8423e6dd-0804-45f0-d570-e595634da200/logo" alt="Pivot 5" style="display:block; margin:0 auto; max-width:180px; height:auto;" />
                                </td>
                                <td style="width:29%;"></td>
                              </tr>
                              <tr>
                                <td colspan="3" style="padding-top:10px;">
                                  <div style="margin:0 auto; max-width:520px; text-align:center; font-size:15px; line-height:1.5; color:#4b5563;">
                                    The must-read daily AI briefing for over 1 million busy professionals who need signal, not noise.
                                  </div>
                                  <div style="margin:4px auto 0 auto; max-width:520px; text-align:center; font-size:15px; line-height:1.5; color:#4b5563; font-style:italic;">
                                    5 headlines. 5 minutes. 5 days a week.
                                  </div>
                                </td>
                              </tr>
                            </table>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Story blocks -->
            <tr>
              <td style="padding:0 12px 24px 12px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#ffffff; border:1px solid #e5e7eb;">
                  {story_blocks}
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding:0 12px 24px 12px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%; background-color:#f9fafb; border:1px solid #e5e7eb;">
                  <tr>
                    <td style="padding:12px 16px; font-size:11px; line-height:1.6; color:#6b7280;">
                      You're receiving this email because you subscribed to Pivot 5.<br />
                      <a href="{{unsubscribe_url}}" style="color:#4b5563; text-decoration:underline;">Unsubscribe</a> &bull;
                      <a href="{{manage_prefs_url}}" style="color:#4b5563; text-decoration:underline;">Manage preferences</a>
                    </td>
                    <td align="right" style="padding:12px 16px; font-size:11px; color:#6b7280; white-space:nowrap;">
                      &copy; {year} Pivot 5
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </center>
</body>
</html>
```

#### Story Block Template

```html
<!-- Story {index} -->
<tr>
  <td style="padding:20px 22px; border-bottom:1px solid #e5e7eb;">
    <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.14em; color:#9ca3af; padding-bottom:6px;">
      {topic}
    </div>
    <div style="font-size:20px; line-height:1.4; font-weight:600; color:#0f172a; padding-bottom:10px;">
      <a href="{url}" style="color:#0f172a; text-decoration:none;">
        {title}
      </a>
    </div>
    {image_block}
    {bullets_html}
    <div style="font-size:13px; color:#4b5563; padding-top:10px;">
      Read More <a href="{url}" style="color:#f97316; text-decoration:underline;">Here</a>.
    </div>
  </td>
</tr>
```

---

### Phase 4: Strip HTML for Deliverability

Create `/workers/utils/html_stripper.py`:

```python
def strip_html_for_deliverability(html: str, subject_line: str) -> str:
    """
    Convert rich HTML email to clean, deliverability-optimized format.

    - Arial font family
    - No images
    - No external links (except unsubscribe)
    - No "Pivot 5" branding (use "Daily AI Briefing")
    - Simple bullet formatting
    """
    # Extract story blocks from HTML
    story_blocks = parse_story_blocks(html)

    output = '<div style="font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.7; color: #333;">'

    for i, story in enumerate(story_blocks):
        # Topic label
        if story.get('label'):
            output += f'<div style="font-size: 12px; font-weight: bold; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{story["label"]}</div>'

        # Headline
        if story.get('headline'):
            output += f'<div style="font-size: 16px; font-weight: 600; color: #111; margin-bottom: 12px;">{story["headline"]}</div>'

        # Bullets
        for bullet in story.get('bullets', []):
            output += f'<div style="margin-bottom: 10px; padding-left: 16px;">• {bullet}</div>'

        # Separator
        if i < len(story_blocks) - 1:
            output += '<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;">'

    # Footer
    output += '<div style="font-size: 12px; color: #888; margin-top: 20px;">You\'re receiving this because you subscribed to our daily AI briefing.<br>Unsubscribe: {{unsubscribe_url}}</div>'
    output += '</div>'

    # Replace Pivot 5 with Daily AI Briefing
    output = re.sub(r'Pivot\s*5', 'Daily AI Briefing', output, flags=re.IGNORECASE)

    return output
```

---

## Environment Variables Checklist

Add to `.env.local` and Render environment:

```bash
# Airtable (existing)
AIRTABLE_API_KEY=patQVZtZjQS8GU78r.xxx
AI_EDITOR_BASE_ID=appglKSJZxmA9iHpl
AIRTABLE_BASE_ID=appwSozYTkrsQWUXB

# Mautic (new)
MAUTIC_BASE_URL=https://app.pivotnews.com
MAUTIC_CLIENT_ID=<get from n8n credentials>
MAUTIC_CLIENT_SECRET=<get from n8n credentials>

# Gmail (new - for manual send)
GMAIL_SENDER_EMAIL=pivot2034@gmail.com
GMAIL_CREDENTIALS_JSON=<base64 encoded service account or OAuth credentials>

# Claude (existing)
ANTHROPIC_API_KEY=<existing key>
```

---

## Testing Checklist

### HTML Compile Testing
- [ ] Verify `tbla16LJCf5Z6cRn3` query returns 5 stories with `image_status='generated'`
- [ ] Verify `tblzt2z7r512Kto3O` lookup returns subject_line
- [ ] Verify stories are sorted by `slot_order` (1-5)
- [ ] Verify Claude generates valid 15-word and 20-word summaries
- [ ] Verify HTML template renders correctly in email clients
- [ ] Verify record created in `tblPBfWZzRdLuiqYr` with status='next-send'

### Mautic Send Testing
- [ ] Verify OAuth authentication works
- [ ] Verify email creation returns valid email ID
- [ ] Verify transport attachment succeeds
- [ ] Verify send returns sentCount > 0
- [ ] Verify archive record created in `tblB7j5qGcTxyXmfa`
- [ ] Verify Newsletter Issues Final record deleted after send

### Gmail Send Testing
- [ ] Verify email sent to all 3 test recipients
- [ ] Verify subject line matches
- [ ] Verify plain_html renders correctly in Gmail

---

## Migration Timeline

| Phase | Tasks | Estimated Effort |
|-------|-------|------------------|
| Phase 1 | Backend Python workers | 4-6 hours |
| Phase 2 | Frontend UI components | 2-3 hours |
| Phase 3 | HTML template integration | 1-2 hours |
| Phase 4 | Testing and debugging | 2-3 hours |
| **Total** | | **9-14 hours** |

---

## Files to Create/Modify

### New Files
- `/workers/utils/mautic.py` - Mautic API client
- `/workers/utils/gmail.py` - Gmail API client
- `/workers/utils/html_stripper.py` - HTML deliverability stripper
- `/workers/jobs/gmail_send.py` - Gmail send job
- `/src/components/step/step-action-card.tsx` - Action card component

### Modified Files
- `/workers/utils/airtable.py` - Add new table methods
- `/workers/jobs/html_compile.py` - Complete rewrite
- `/workers/jobs/mautic_send.py` - Complete implementation
- `/workers/trigger.py` - Add new job routes
- `/src/lib/step-config.ts` - Update Step 4 config
- `/src/app/(dashboard)/step/[id]/page.tsx` - Add action cards UI
- `.env.local` - Add Mautic and Gmail credentials

---

## Notes

1. **Date Format:** Issue IDs use format "Pivot 5 - MMM dd" (zero-padded day)
2. **Timezone:** All timestamps should use America/New_York (ET)
3. **Mautic Lists:** Send to lists [5, 14] as configured in n8n
4. **Transport ID:** Always use transport ID 3 (GreenArrow)
5. **Deliverability:** Plain HTML version removes images, branding, and unnecessary formatting
