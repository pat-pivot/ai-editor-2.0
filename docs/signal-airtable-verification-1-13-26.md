# Signal Newsletter Airtable Schema Verification

**Date:** January 13, 2026
**Verified via:** Airtable Metadata API
**Base ID:** `appWGkUBuyrzmFnFM`

---

## Tables

| Table Name | Table ID | Purpose |
|------------|----------|---------|
| Signal - Selected Slots | `tblNxfdFYRxXtBBO2` | Stores selected stories per issue (INPUT to decoration) |
| Signal - Issue Stories | `tbltUl5QYSBoWbnbD` | Stores decorated content (OUTPUT of decoration) |

---

## Signal - Selected Slots (tblNxfdFYRxXtBBO2)

This table stores the stories selected for each Signal issue. The decoration job reads from here and writes to Signal - Issue Stories.

### Fields (Verified via API)

| Field Name | Type | Purpose |
|------------|------|---------|
| `issue_id` | singleLineText | Issue identifier (e.g., "Signal - Jan 13") |
| `issue_date` | dateTime | Date of the newsletter issue |
| `subject_line` | singleLineText | Email subject line |
| `status` | singleSelect | Pipeline status (pending, decorated, compiled, sent) |
| `sent_at` | dateTime | When the newsletter was sent |
| `compiled_html` | multilineText | Final HTML for the email |
| `created_by` | createdBy | Airtable user who created |
| `created_time` | createdTime | When record was created |
| `last_edited_by` | lastModifiedBy | Last editor |
| `last_edited_time` | lastModifiedTime | Last edit timestamp |
| `Signal Issue Stories` | multipleRecordLinks | Links to decorated stories |

### Section-Specific Fields

**Top Story:**
| Field Name | Type |
|------------|------|
| `top_story_headline` | singleLineText |
| `top_story_storyId` | singleLineText |
| `top_story_pivotId` | singleLineText |

**AI at Work:**
| Field Name | Type |
|------------|------|
| `ai_at_work_headline` | singleLineText |
| `ai_at_work_storyId` | singleLineText |
| `ai_at_work_pivotId` | singleLineText |

**Emerging Moves:**
| Field Name | Type |
|------------|------|
| `emerging_moves_headline` | singleLineText |
| `emerging_moves_storyId` | singleLineText |
| `emerging_moves_pivotId` | singleLineText |

**Beyond Business:**
| Field Name | Type |
|------------|------|
| `beyond_business_headline` | singleLineText |
| `beyond_business_storyId` | singleLineText |
| `beyond_business_pivotId` | singleLineText |

**Signals (5 items):**
| Field Name | Type |
|------------|------|
| `signal_1_headline` | singleLineText |
| `signal_1_storyId` | singleLineText |
| `signal_1_pivotId` | singleLineText |
| `signal_2_headline` | singleLineText |
| `signal_2_storyId` | singleLineText |
| `signal_2_pivotId` | singleLineText |
| `signal_3_headline` | singleLineText |
| `signal_3_storyId` | singleLineText |
| `signal_3_pivotId` | singleLineText |
| `signal_4_headline` | singleLineText |
| `signal_4_storyId` | singleLineText |
| `signal_4_pivotId` | singleLineText |
| `signal_5_headline` | singleLineText |
| `signal_5_storyId` | singleLineText |
| `signal_5_pivotId` | singleLineText |

---

## Signal - Issue Stories (tbltUl5QYSBoWbnbD)

This is the OUTPUT table where decorated content is written. Updated schema as of January 13, 2026.

### Fields (Verified via API)

| Field Name | Type | Purpose | Used For |
|------------|------|---------|----------|
| `issue_id` | singleLineText | Issue identifier (e.g., "Signal - Jan 13") | All |
| `section` | singleSelect | Section type (top_story, ai_at_work, emerging, beyond, signal) | All |
| `slot_order` | number | Order within section (1 for main sections, 1-5 for signals) | All |
| `pivot_id` | singleLineText | Unique story identifier from source | All |
| `headline` | multilineText | AI-rewritten headline (Title Case, max 80 chars) | All |
| `one_liner` | multilineText | Single sentence hook for At-a-Glance section | Main sections |
| `lead` | multilineText | 2-3 sentence intro paragraph | Main sections |
| `signal_blurb` | multilineText | 2-sentence summary for signals | Signals only |
| `why_it_matters` | multilineText | Bullet: relevance to reader (with HTML bold) | Main sections |
| `whats_next` | multilineText | Bullet: implications/next steps (with HTML bold) | Main sections |
| `source_attribution` | singleLineText | "via Publication Name" | All |
| `raw` | multilineText | Cleaned article content (for reference) | All |
| `decoration_status` | singleSelect | Status (pending, decorated) | All |
| `Signal - Selected Slots` | multipleRecordLinks | Link back to Selected Slots record | All |
| `Summary (one_liner)` | aiText | Airtable AI-generated summary (auto-populated) | N/A |

---

## Field Usage by Section Type

### Main Sections (top_story, ai_at_work, emerging, beyond)

These fields are populated for main section stories:

```
headline          - Required (AI-rewritten)
one_liner         - Required (for At-a-Glance summary)
lead              - Required (2-3 sentence intro)
why_it_matters    - Required (2 sentences, HTML <b> bolding)
whats_next        - Required (2 sentences, HTML <b> bolding)
signal_blurb      - NOT USED (empty)
source_attribution - Required
```

### Signals (signal_1 through signal_5)

These fields are populated for Signal quick-hit items:

```
headline          - Required (AI-rewritten, shorter)
signal_blurb      - Required (2 sentences, no bolding)
one_liner         - NOT USED (empty)
lead              - NOT USED (empty)
why_it_matters    - NOT USED (empty)
whats_next        - NOT USED (empty)
source_attribution - Required
```

---

## Missing Fields (Noted for Future)

The following fields from the original implementation are NOT in the current schema:

| Field | Status | Notes |
|-------|--------|-------|
| `core_url` | Missing | Need to add for linking to original article |
| `label` | Missing | Need to add for category tags (ENTERPRISE, WORK, etc.) |
| `story_id` | Replaced | Now using `pivot_id` as identifier |
| `summary` | Replaced | Split into `one_liner` and `signal_blurb` |
| `paragraph` | Removed | Replaced by `lead` |
| `b1`, `b2`, `b3` | Replaced | Now `why_it_matters` and `whats_next` (only 2 bullets) |
| `the_impact` | Removed | Consolidated into 2 bullets |

---

## Recommended Schema Additions

Before implementing, add these fields to Signal - Issue Stories:

1. **`core_url`** (url type) - Link to original article
2. **`label`** (singleSelect) - Category tag with options:
   - WORK, EDUCATION, INFRASTRUCTURE, POLICY, TALENT, HEALTH
   - RETAIL, ENTERPRISE, COMPETITION, FUNDING, SECURITY, TOOLS
   - SEARCH, INVESTORS, CHINA, REGULATION, ETHICS, LAWSUITS

---

## API Verification Command

To re-verify this schema:

```bash
curl -s 'https://api.airtable.com/v0/meta/bases/appWGkUBuyrzmFnFM/tables' \
  -H 'Authorization: Bearer YOUR_AIRTABLE_API_KEY' | \
  jq '.tables[] | {name: .name, id: .id, fields: [.fields[] | {name: .name, type: .type}]}'
```
