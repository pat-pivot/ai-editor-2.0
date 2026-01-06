# Step 4: HTML Compile & Send Cross-Reference Analysis

**Document:** Step-4-Cross-Reference-12-23-25.md
**Date:** December 23, 2025
**Infrastructure Doc:** AI-Editor-2.0-Infrastructure-Step-4-12-23-25.md
**Implementation Files:**
- `/app/src/lib/airtable.ts`
- `/app/src/app/(dashboard)/newsletter/page.tsx`

---

## Summary

| Category | Status |
|----------|--------|
| Dashboard READ Operations | ✅ Implemented |
| HTML Compilation Logic | ❌ Not Implemented |
| Claude Summary Generation | ❌ Not Implemented |
| Newsletter Issues Table WRITE | ❌ Not Implemented |
| Mautic API Integration | ❌ Not Implemented |
| Archive Table WRITE | ❌ Not Implemented |
| Python Worker Job | ❌ Not Implemented |

---

## Critical Architecture: Two-Phase Processing

Step 4 uses a **two-phase processing pattern**:

1. **Phase 1 (10 PM EST):** Compile HTML from decorated stories
2. **Phase 2 (5 AM EST):** Send via Mautic + archive

```
10 PM Phase:
Decorated Stories → Aggregate → Get Subject Line → Compile HTML → Generate Summary → Write Issue

5 AM Phase:
Write Issue → Create Mautic Email → Attach Transport → Send → Archive → Update Status
```

---

## Node-by-Node Cross-Reference

### Node 1: Schedule Trigger
**Infrastructure:** Two cron expressions:
- `0 3 * * 2-6` (10:00 PM EST, Mon-Fri) - HTML Compilation
- `0 10 * * 1-5` (5:00 AM EST, Mon-Fri) - Email Send

**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker with Redis Queue (RQ) scheduled job
- Two separate cron triggers:
  - `0 3 * * 2-6` UTC → `compile_html` job
  - `0 10 * * 1-5` UTC → `send_mautic` job
- File: `workers/jobs/html_compile.py`

---

### Node 2: Get Decorated Stories
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories)
- Filter: `{image_status}='generated'`
- Sort: `slot_order` ASC
- Max Records: 5
- Fields: 11 fields

**Implementation:** ✅ Implemented in `getDecorations()` (lines 496-547)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Base ID | `appglKSJZxmA9iHpl` | `process.env.AI_EDITOR_BASE_ID` | ✅ |
| Table ID | `tbla16LJCf5Z6cRn3` | `process.env.AI_EDITOR_DECORATION_TABLE` | ✅ |
| Filter | `{image_status}='generated'` | `{image_status}='generated'` | ✅ |
| Sort | `slot_order` ASC | `slot_order` ASC | ✅ |
| Max Records | 5 | 5 | ✅ |
| Fields | 11 | 18 | ✅ More fields |

**Status:** Dashboard READ matches infrastructure. Python worker needs same query.

---

### Node 3: Aggregate Stories
**Infrastructure:** Combine 5 stories into single array for template
**Implementation Status:** ⚠️ Partial (dashboard side only)

**Dashboard Implementation:** Newsletter page aggregates via `slots` state (lines 97-111)

**Action Required for Python Worker:**
```python
def aggregate_stories(stories: List[dict]) -> dict:
    """Combine 5 decorated stories for HTML template"""
    return {
        "stories": sorted(stories, key=lambda s: s['slot_order'])
    }
```

---

### Node 4: Get Subject Line
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tblzt2z7r512Kto3O` (Selected Slots)
- Filter: `{status}='pending'`
- Sort: `issue_date` DESC
- Max Records: 1
- Fields: `issue_id`, `issue_date`, `subject_line`

**Implementation:** ✅ Implemented in `getSelectedSlots()` (lines 390-467)

**Gap:** Implementation returns latest issue without status filter. Infrastructure filters for `{status}='pending'`.

**Action Required:**
```python
filter_formula = "{status}='pending'"
```

---

### Node 5: Compile HTML
**Infrastructure:** JavaScript code that builds email HTML template

**Implementation Status:** ❌ Not Implemented

**Dashboard Shows:** Hardcoded placeholder HTML in `newsletter/page.tsx` (lines 353-381)

**Gap:** Dashboard shows a static HTML snippet, NOT dynamically compiled from stories.

**Action Required for Python Worker:**
```python
def compile_html(stories: List[dict], issue: dict) -> str:
    """Compile 5 stories into HTML email template"""

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{issue['subject_line']}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; }}
    .container {{ max-width: 640px; margin: 0 auto; }}
    .story-block {{ padding: 24px; border-bottom: 1px solid #eee; }}
    .label {{
      background: #ff6f00;
      color: white;
      padding: 4px 12px;
      font-size: 12px;
      border-radius: 4px;
    }}
    .headline {{ font-size: 22px; font-weight: bold; margin: 16px 0; }}
    .dek {{ font-size: 16px; color: #666; margin-bottom: 16px; }}
    .bullet {{ margin: 8px 0; line-height: 1.5; }}
    .read-more {{
      color: #ff6f00;
      text-decoration: none;
      font-weight: bold;
    }}
    img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>
  <div class="container">
    <span style="display:none;">{issue['subject_line']}</span>

    <div style="text-align:center; padding:24px;">
      <img src="https://img.pivotnews.com/pivot5-logo.png" alt="Pivot 5" width="200">
      <p style="color:#666;">5 headlines • 5 minutes • 5 days a week</p>
    </div>

    {"".join([compile_story_block(story) for story in stories])}

    <div style="padding:24px; text-align:center; background:#f5f5f5;">
      <p>© 2025 Pivot Media. All rights reserved.</p>
      <a href="{{unsubscribe_url}}">Unsubscribe</a> |
      <a href="{{preferences_url}}">Manage Preferences</a>
    </div>
  </div>
</body>
</html>
"""
    return html


def compile_story_block(story: dict) -> str:
    """Compile single story block HTML"""
    return f"""
    <div class="story-block">
      <span class="label">{story['label']}</span>
      <h2 class="headline">{story['headline']}</h2>
      <img src="{story['image_url']}" alt="{story['headline']}">
      <p class="dek">{story['ai_dek']}</p>
      <ul>
        <li class="bullet">{story['b1']}</li>
        <li class="bullet">{story['b2']}</li>
        <li class="bullet">{story['b3']}</li>
      </ul>
      <a href="{story['core_url']}" class="read-more">Read More →</a>
    </div>
    """
```

---

### Node 6: Generate Summary
**Infrastructure:**
- Model: `claude-sonnet-4-5-20250929`
- Temperature: 0.5
- Output: 15-word summary + 20-word summary_plus

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def generate_summary(headlines: List[str], anthropic_client: Anthropic) -> dict:
    """Generate 15-word and 20-word newsletter summaries"""

    prompt = f"""Generate two newsletter summaries:

HEADLINES FROM TODAY'S ISSUE:
{chr(10).join(headlines)}

1. SUMMARY (exactly 15 words): A punchy overview of today's newsletter
2. SUMMARY_PLUS (exactly 20 words): Slightly more detailed overview

Return as JSON:
{{
  "summary": "...",
  "summary_plus": "..."
}}"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=200,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text)
```

---

### Node 7: Prepare Issue Record
**Infrastructure:** Combine HTML, summaries, and metadata
**Implementation Status:** ❌ Not Implemented

**Output Fields:**
```python
issue_record = {
    "issue_id": issue['issue_id'],
    "newsletter_id": "pivot_ai",
    "html": compiled_html,
    "subject_line": issue['subject_line'],
    "summary": summaries['summary'],
    "summary_plus": summaries['summary_plus'],
    "status": "compiled"
}
```

---

### Node 8: Write Newsletter Issue
**Infrastructure:**
- Base: `appwSozYTkrsQWUXB` (Pivot Media Master)
- Table: `tbl7mcCCGbjEfli25` (Newsletter Issues)
- Operation: UPSERT on `issue_id`
- Fields: 7 fields

**Implementation Status:** ❌ Not Implemented

**Gap:** No `getNewsletterIssues()` or `writeNewsletterIssue()` function exists.

**Action Required:**
```python
def write_newsletter_issue(issue_record: dict) -> str:
    """Upsert issue record to Newsletter Issues table"""
    # Airtable UPSERT operation on issue_id
    pass
```

**Environment Variable Needed:**
```bash
AIRTABLE_NEWSLETTER_ISSUES_TABLE=tbl7mcCCGbjEfli25  # Already configured
```

---

### Node 9: Check Time for Send
**Infrastructure:** Conditional check if current time is 5 AM EST window
**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def is_send_window() -> bool:
    """Check if current time is 5 AM EST send window"""
    from datetime import datetime
    import pytz

    est = pytz.timezone('America/New_York')
    current_hour = datetime.now(est).hour

    return 5 <= current_hour < 6
```

---

### Node 10: Create Mautic Email
**Infrastructure:**
- Method: POST
- URL: `https://app.pivotnews.com/api/emails/new`
- Auth: OAuth2
- Creates email campaign in Mautic

**Implementation Status:** ❌ Not Implemented

**Dashboard Shows:** "Send to Mautic" button (line 161) but NO actual integration

**Action Required:**
```python
def create_mautic_email(issue: dict, mautic_client: MauticClient) -> dict:
    """Create new email in Mautic"""

    payload = {
        "name": issue['issue_id'],
        "subject": issue['subject_line'],
        "customHtml": issue['html'],
        "emailType": "list",
        "lists": [1],
        "isPublished": True,
        "template": None,
        "utmTags": {
            "utmSource": "newsletter",
            "utmMedium": "email",
            "utmCampaign": "pivot5_daily"
        }
    }

    response = mautic_client.post("/api/emails/new", json=payload)
    return response.json()
```

---

### Node 11: Attach Transport
**Infrastructure:**
- Method: PATCH
- URL: `https://app.pivotnews.com/api/emails/{id}/transport`
- Associates email with GreenArrow SMTP transport

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def attach_transport(email_id: int, transport_id: str, mautic_client: MauticClient) -> dict:
    """Attach GreenArrow transport to email"""

    response = mautic_client.patch(
        f"/api/emails/{email_id}/transport",
        json={"transport_id": transport_id}
    )
    return response.json()
```

---

### Node 12: Send Email
**Infrastructure:**
- Method: POST
- URL: `https://app.pivotnews.com/api/emails/{id}/send`
- Triggers actual email send

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def send_email(email_id: int, mautic_client: MauticClient) -> dict:
    """Send email via Mautic"""

    response = mautic_client.post(
        f"/api/emails/{email_id}/send",
        json={"lists": [1]}
    )
    return response.json()
```

---

### Node 13: Archive Sent
**Infrastructure:**
- Base: `appwSozYTkrsQWUXB` (Pivot Media Master)
- Table: `tblHo0xNj8nbzMHNI` (Newsletter Issues Archive)
- Operation: Create record

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def archive_sent_email(issue_id: str, mautic_response: dict) -> str:
    """Archive sent email to Newsletter Issues Archive table"""

    archive_record = {
        "issue_id": issue_id,
        "sent_status": "sent",
        "mautic_email_id": mautic_response['email']['id'],
        "mautic_response": json.dumps(mautic_response),
        "sent_at": datetime.utcnow().isoformat()
    }

    # Airtable CREATE operation
    pass
```

**Environment Variable Needed:**
```bash
AIRTABLE_NEWSLETTER_ISSUES_ARCHIVE_TABLE=tblHo0xNj8nbzMHNI  # Already configured
```

---

### Node 14: Update Selected Slots Status
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tblzt2z7r512Kto3O` (Selected Slots)
- Operation: Update record
- Set `status='sent'`

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def update_issue_status(issue_record_id: str, status: str) -> dict:
    """Update Selected Slots record status"""
    # Airtable PATCH operation
    pass
```

---

## Environment Variables Required

### Currently Configured
```bash
AIRTABLE_API_KEY=✅ Configured
AIRTABLE_BASE_ID=✅ Configured (appwSozYTkrsQWUXB)
AI_EDITOR_BASE_ID=✅ Configured (appglKSJZxmA9iHpl)
AI_EDITOR_DECORATION_TABLE=✅ Configured (tbla16LJCf5Z6cRn3)
AI_EDITOR_SELECTED_SLOTS_TABLE=✅ Configured (tblzt2z7r512Kto3O)
AIRTABLE_NEWSLETTER_ISSUES_TABLE=✅ Configured (tbl7mcCCGbjEfli25)
AIRTABLE_NEWSLETTER_ISSUES_ARCHIVE_TABLE=✅ Configured (tblHo0xNj8nbzMHNI)
```

### Missing
```bash
ANTHROPIC_API_KEY=❌ Required for Claude summary generation
MAUTIC_CLIENT_ID=❌ Required for Mautic OAuth2
MAUTIC_CLIENT_SECRET=❌ Required for Mautic OAuth2
GREENARROW_TRANSPORT_ID=❌ Required for email deliverability
```

---

## Python Worker Specification

### Phase 1: HTML Compilation

**File:** `workers/jobs/html_compile.py`
**Queue:** Redis Queue (RQ)
**Schedule:** `0 3 * * 2-6` UTC (10:00 PM EST)

```python
def compile_newsletter() -> dict:
    """Step 4 Phase 1: Compile HTML from decorated stories"""

    # 1. Get decorated stories (image_status='generated')
    stories = get_decorated_stories()

    # 2. Aggregate and sort by slot_order
    aggregated = aggregate_stories(stories)

    # 3. Get subject line from pending issue
    issue = get_pending_issue()

    # 4. Compile HTML template
    html = compile_html(aggregated['stories'], issue)

    # 5. Generate 15 + 20 word summaries
    headlines = [s['headline'] for s in aggregated['stories']]
    summaries = generate_summary(headlines)

    # 6. Prepare issue record
    issue_record = {
        "issue_id": issue['issue_id'],
        "newsletter_id": "pivot_ai",
        "html": html,
        "subject_line": issue['subject_line'],
        "summary": summaries['summary'],
        "summary_plus": summaries['summary_plus'],
        "status": "compiled"
    }

    # 7. Write to Newsletter Issues table
    record_id = write_newsletter_issue(issue_record)

    return {"record_id": record_id, "issue_id": issue['issue_id']}
```

### Phase 2: Mautic Send

**File:** `workers/jobs/mautic_send.py`
**Queue:** Redis Queue (RQ)
**Schedule:** `0 10 * * 1-5` UTC (5:00 AM EST)

```python
def send_newsletter() -> dict:
    """Step 4 Phase 2: Send compiled newsletter via Mautic"""

    # 1. Get latest compiled issue
    issue = get_latest_compiled_issue()

    if not issue or issue['status'] != 'compiled':
        raise ValueError("No compiled issue ready to send")

    # 2. Create Mautic email
    mautic_email = create_mautic_email(issue)

    # 3. Attach GreenArrow transport
    attach_transport(mautic_email['email']['id'], os.environ['GREENARROW_TRANSPORT_ID'])

    # 4. Send email
    send_response = send_email(mautic_email['email']['id'])

    # 5. Archive sent email
    archive_sent_email(issue['issue_id'], send_response)

    # 6. Update Selected Slots status to 'sent'
    update_issue_status(issue['record_id'], 'sent')

    return {
        "issue_id": issue['issue_id'],
        "mautic_email_id": mautic_email['email']['id'],
        "status": "sent"
    }
```

---

## Mautic API Client Specification

**File:** `workers/utils/mautic.py`

```python
import os
import requests
from datetime import datetime, timedelta

class MauticClient:
    """Mautic API client with OAuth2 authentication"""

    def __init__(self):
        self.base_url = "https://app.pivotnews.com"
        self.client_id = os.environ['MAUTIC_CLIENT_ID']
        self.client_secret = os.environ['MAUTIC_CLIENT_SECRET']
        self.access_token = None
        self.token_expires_at = None

    def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token"""
        if self.access_token and self.token_expires_at > datetime.utcnow():
            return self.access_token

        response = requests.post(
            f"{self.base_url}/oauth/v2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        response.raise_for_status()

        data = response.json()
        self.access_token = data['access_token']
        self.token_expires_at = datetime.utcnow() + timedelta(seconds=data['expires_in'] - 60)

        return self.access_token

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to Mautic API"""
        token = self._get_access_token()
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f"Bearer {token}"

        response = requests.request(
            method,
            f"{self.base_url}{endpoint}",
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        return self._request('POST', endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> requests.Response:
        return self._request('PATCH', endpoint, **kwargs)

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        return self._request('GET', endpoint, **kwargs)
```

---

## Critical Issues Found

### Issue 1: No HTML Compilation
**Location:** `newsletter/page.tsx` lines 353-381
**Problem:** Dashboard shows hardcoded placeholder HTML, not dynamically compiled
**Impact:** Cannot preview actual compiled newsletter
**Resolution:** Python worker compiles HTML; dashboard fetches from Newsletter Issues table

### Issue 2: No Mautic Integration
**Location:** `newsletter/page.tsx` lines 161-163
**Problem:** "Send to Mautic" button exists but has no actual functionality
**Impact:** Cannot send newsletters programmatically
**Resolution:** Python worker handles Mautic API; add API route for manual trigger

### Issue 3: No Summary Generation
**Problem:** No Claude integration for generating 15/20-word summaries
**Impact:** Summary fields empty in Newsletter Issues
**Resolution:** Python worker calls Claude Sonnet 4.5 for summary generation

### Issue 4: Missing Newsletter Issues WRITE
**Location:** `lib/airtable.ts`
**Problem:** No function to write to Newsletter Issues table
**Impact:** Cannot save compiled HTML
**Resolution:** Python worker handles UPSERT on `issue_id`

---

## Dashboard Updates Required

### 1. Fetch Compiled HTML from Newsletter Issues
```typescript
// Add to lib/airtable.ts
export async function getNewsletterIssue(issueId?: string): Promise<NewsletterIssue | null> {
  const filter = issueId
    ? `{issue_id}='${issueId}'`
    : `{status}='compiled'`;

  const records = await base(TABLES.newsletterIssues)
    .select({
      filterByFormula: filter,
      sort: [{ field: 'created_at', direction: 'desc' }],
      maxRecords: 1
    })
    .firstPage();

  // Transform and return
}
```

### 2. Display Real HTML in Preview
Update `newsletter/page.tsx` to fetch compiled HTML from Newsletter Issues instead of showing placeholder.

### 3. Add Manual Send Trigger
Add API route `/api/newsletter/send` that enqueues the `send_newsletter` job.

---

## Implementation Priority

1. **High Priority (Worker Core):**
   - [ ] Create `workers/jobs/html_compile.py`
   - [ ] Create `workers/jobs/mautic_send.py`
   - [ ] Create `workers/utils/mautic.py` (OAuth2 client)
   - [ ] Implement Claude summary generation
   - [ ] Implement HTML compilation

2. **Medium Priority (Dashboard Updates):**
   - [ ] Add `getNewsletterIssue()` function to airtable.ts
   - [ ] Update newsletter page to display compiled HTML
   - [ ] Add API route for manual send trigger

3. **Low Priority (Enhancements):**
   - [ ] Add test send functionality (single recipient)
   - [ ] Display Mautic send status/response
   - [ ] Archive history view

---

*Cross-reference generated: December 23, 2025*
