---
name: decorating-stories
description: Generates headlines, bullet points, and image prompts for selected stories using Claude. Writes to Newsletter Issue Stories table. Use when working on Step 3, the Decoration tab, editing headline/bullet prompts, or debugging content generation issues.
---

# Step 3: Decoration (Claude + Gemini)

> **Status: WORKING** (as of January 2, 2026)
> Worker deployed to Render. Migrated from n8n workflow `HCbd2g852rkQgSqr`.
> Step 3b (Image Generation) ready for testing.

This skill covers the decoration step that generates headlines, bullet points, and image prompts for selected stories.

---

## Frontend UI (Dashboard)

**Location:** `/src/app/(dashboard)/step/[id]/page.tsx`

Step 3 has **two separate buttons** in the dashboard:

| Button | Triggers | Job Name | Description |
|--------|----------|----------|-------------|
| **Run Decoration** | `/jobs/decoration` | `decoration` | Generates headlines, deks, bullets, labels |
| **Generate Images** | `/jobs/images` | `images` | Generates images for decorated stories |

### State Variables (Step 3 Specific)
```typescript
// Standard job state (decoration)
const [isRunning, setIsRunning] = useState(false);
const [currentJobId, setCurrentJobId] = useState<string | null>(null);

// Image generation state (separate tracking)
const [isImageGenRunning, setIsImageGenRunning] = useState(false);
const [imageGenJobId, setImageGenJobId] = useState<string | null>(null);
const [imageGenJobStatus, setImageGenJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
const [imageGenElapsedTime, setImageGenElapsedTime] = useState(0);
```

### handleRunNow Logic
```typescript
// Step 3 job mapping
const STEP_3_JOBS: Record<string, string> = {
  decoration: "decoration",
  images: "images",
};

// In handleRunNow:
if (stepId === 3 && jobType) {
  jobName = STEP_3_JOBS[jobType] || jobType;
}
```

---

## ⛔ CRITICAL: Data Flow & Table Configuration

### Complete Data Flow

```
1. Selected Slots (tblzt2z7r512Kto3O)
   - Contains pending issues with 5 story slots
   - Fields: slot_1_pivotId, slot_1_storyId, slot_1_headline, etc.
   - Filter: status='pending'
       ↓
2. Newsletter Selects (tblKhICCdWnyuqgry)
   - Lookup article content by pivot_id
   - Fields: pivot_id, headline, core_url, source_name, raw
   - Formula: {pivot_id}='<pivotId from Selected Slots>'
       ↓
3. Newsletter Issue Stories (tbla16LJCf5Z6cRn3)
   - OUTPUT: Write decorated content
   - Fields: story_id, issue_id, headline, b1, b2, b3, ai_dek, label, etc.
```

### Airtable Base

| Base | ID | Status |
|------|----|---------|
| **AI Editor 2.0** | `appglKSJZxmA9iHpl` | ✅ USE THIS |

### Airtable Tables

| Table Name | Table ID | Purpose |
|------------|----------|---------|
| **Selected Slots** | `tblzt2z7r512Kto3O` | INPUT: Pending issues with 5 story slots |
| **Newsletter Selects** | `tblKhICCdWnyuqgry` | LOOKUP: Article content by pivot_id |
| **Newsletter Issue Stories** | `tbla16LJCf5Z6cRn3` | OUTPUT: Decorated stories |

---

## ⛔ EXACT FIELD NAMES (Verified via Airtable API Jan 1, 2026)

### Selected Slots Table (`tblzt2z7r512Kto3O`)

| Field Name | Type | Notes |
|------------|------|-------|
| `issue_id` | autoNumber | |
| `issue_date` | singleLineText | e.g., "Dec 31" |
| `slot_1_headline`, `slot_2_headline`, etc. | singleLineText | |
| `slot_1_storyId`, `slot_2_storyId`, etc. | singleLineText | **lowercase 'd'** |
| `slot_1_pivotId`, `slot_2_pivotId`, etc. | singleLineText | **capital 'I'** |
| `slot_1_source`, `slot_2_source`, etc. | singleLineText | |
| `status` | singleSelect | pending, decorated, compiled, sent |

### Newsletter Selects Table (`tblKhICCdWnyuqgry`)

| Field Name | Type | Notes |
|------------|------|-------|
| `pivot_id` | singleLineText | **lowercase with underscore** |
| `headline` | singleLineText | |
| `core_url` | url | |
| `source_name` | singleLineText | |
| `raw` | multilineText | Article markdown content |
| `topic` | singleLineText | |
| `interest_score` | number | |

### Newsletter Issue Stories Table (`tbla16LJCf5Z6cRn3`) - OUTPUT

| Field Name | Type | Notes |
|------------|------|-------|
| `story_id` | singleLineText | ✅ **lowercase with underscore** |
| `issue_id` | singleLineText | e.g., "Pivot 5 - Dec 31" |
| `slot_order` | number | 1-5 |
| `headline` | multilineText | ✅ **NOT ai_headline** |
| `ai_dek` | multilineText | |
| `b1` | multilineText | ✅ **NOT ai_bullet_1** - with `<b>` tags |
| `b2` | multilineText | ✅ **NOT ai_bullet_2** - with `<b>` tags |
| `b3` | multilineText | ✅ **NOT ai_bullet_3** - with `<b>` tags |
| `label` | singleLineText | WORK, POLICY, ENTERPRISE, etc. |
| `raw` | multilineText | Cleaned article content |
| `image_status` | singleSelect | needs_image, generated, failed |
| `image_url` | url | |
| `social_status` | singleSelect | |
| `article_slug` | singleLineText | |
| `pivotnews_url` | url | |

### ⚠️ Common Field Name Mistakes

| ❌ WRONG | ✅ CORRECT | Notes |
|----------|-----------|-------|
| `storyID` | `story_id` | lowercase with underscore |
| `pivotId` | N/A | Not in output table |
| `ai_headline` | `headline` | No ai_ prefix |
| `ai_bullet_1` | `b1` | Short name |
| `ai_bullet_2` | `b2` | Short name |
| `ai_bullet_3` | `b3` | Short name |
| `image_prompt` | N/A | Not in this table |
| `original_url` | N/A | Not in this table |

---

## Triggering Decoration

### Via Trigger Service (Direct)
```bash
curl -X POST "https://ai-editor-trigger.onrender.com/jobs/decoration" \
  -H "Authorization: Bearer pivot5-trigger-secret-2024" \
  -H "Content-Type: application/json" \
  -d '{"newsletter": "pivot_ai"}'
```

### Newsletter Style Variants
| Style | Description |
|-------|-------------|
| `pivot_ai` | AI-focused technology news (default) |
| `pivot_build` | Builder/developer-focused |
| `pivot_invest` | Investment/finance-focused |

### Check Job Status
```bash
curl "https://ai-editor-trigger.onrender.com/jobs/status/<job_id>" \
  -H "Authorization: Bearer pivot5-trigger-secret-2024"
```

---

## Python Code Reference

### decoration.py Write Block (CORRECT)

```python
# Field names from Airtable API query (table tbla16LJCf5Z6cRn3)
decoration_data = {
    # Record identifiers (verified via Airtable API)
    "story_id": story_id,           # singleLineText
    "issue_id": issue_id_text,      # singleLineText (e.g., "Pivot 5 - Dec 31")
    "slot_order": slot,             # number (1-5)
    # AI-generated content (field names from Airtable schema)
    "headline": decoration.get("ai_headline", headline),  # multilineText
    "ai_dek": decoration.get("ai_dek", ""),                # multilineText
    "b1": decoration.get("ai_bullet_1", ""),              # multilineText with <b> tags
    "b2": decoration.get("ai_bullet_2", ""),              # multilineText with <b> tags
    "b3": decoration.get("ai_bullet_3", ""),              # multilineText with <b> tags
    # Metadata
    "label": decoration.get("label", "ENTERPRISE"),       # singleLineText
    "raw": cleaned_content[:10000] if cleaned_content else "",  # multilineText
    # Image generation
    "image_status": "needs_image",  # singleSelect
}
```

### airtable.py get_article_by_pivot_id (CORRECT)

```python
def get_article_by_pivot_id(self, pivot_id: str) -> Optional[dict]:
    """
    Lookup article details by pivotId from Newsletter Selects table.
    Uses AI Editor 2.0 base and Newsletter Selects table.
    """
    table = self._get_table(self.ai_editor_base_id, self.newsletter_selects_table_id)

    records = table.all(
        formula=f"{{pivot_id}}='{pivot_id}'",  # lowercase pivot_id
        max_records=1,
        fields=['pivot_id', 'source_name', 'core_url', 'raw', 'headline']
    )
```

---

## How Decoration Works

```
Selected Slots (pending issue with 5 stories)
    ↓
For each slot 1-5:
    ↓
    Extract pivot_id from slot_X_pivotId
    ↓
    Lookup article in Newsletter Selects by pivot_id
    ↓
    Clean content with Gemini (remove ads, noise)
    ↓
    Generate decoration with Claude (headline, dek, bullets, label)
    ↓
    Apply HTML <b> bolding to bullets
    ↓
    Write to Newsletter Issue Stories
    ↓
Update issue status to 'decorated'
```

---

## Content Guidelines

### Headlines
- 8-12 words ideal
- Lead with action or impact
- No colons

### Bullet Points
- **Each bullet: EXACTLY 2 sentences** (not 1, not 3)
- Sentence 1: Main fact/announcement
- Sentence 2: Additional context/impact

### Bold Formatting
- Use HTML `<b>` tags, NOT markdown `**`
- Bold single most important phrase (5-15 words) per bullet
- Example: `Netflix <b>unveiled a generative-AI search feature</b> that recommends...`

---

## Label Categories (18 Valid Options)

```
WORK, EDUCATION, INFRASTRUCTURE, POLICY, TALENT, HEALTH,
RETAIL, ENTERPRISE, COMPETITION, FUNDING, SECURITY, TOOLS,
SEARCH, INVESTORS, CHINA, REGULATION, ETHICS, LAWSUITS
```

---

## Quick Reference

**Files:**
- `workers/jobs/decoration.py` - Main decoration job
- `workers/utils/airtable.py` - Airtable client with table configs
- `workers/utils/claude.py` - Claude API client with prompts
- `workers/utils/gemini.py` - Gemini content cleaning

**AI Models:**
- Claude Sonnet 4.5 - Content generation & bolding
- Gemini - Content cleaning

**Prompts:** `headline_generator`, `bold_formatter` (stored in PostgreSQL system_prompts)

---

## Claude Prompts (Verified Working)

### headline_generator (MASTER PROMPT)
**Purpose:** Generate ai_headline, ai_dek, ai_bullet_1/2/3, label
**Outputs:**
- `ai_headline` - Title case, no colons
- `ai_dek` - Short deck/summary
- `ai_bullet_1/2/3` - Each EXACTLY 2 sentences
- `label` - One of 18 categories (WORK, ENTERPRISE, etc.)

### bold_formatter
**Purpose:** Apply HTML `<b>` tags to key phrases in bullets
**Input:** ai_bullet_1, ai_bullet_2, ai_bullet_3
**Output:** Same bullets with `<b>` wrapped around most important phrase (5-15 words)
**Example:** `Netflix <b>unveiled a generative-AI search feature</b> that recommends...`

---

## Step 3b: Image Generation

**Status:** Exists but needs testing
**File:** `workers/jobs/image_generation.py`
**Trigger:** `POST /jobs/images`

```bash
curl -X POST "https://ai-editor-trigger.onrender.com/jobs/images" \
  -H "Authorization: Bearer pivot5-trigger-secret-2024"
```

**Flow:**
1. Query Newsletter Issue Stories for `image_status='needs_image'`
2. For each story, generate image from headline using Gemini Imagen 3
3. Upload to Cloudflare
4. Update `image_url` and set `image_status='generated'`

---

## Bug Fixes Applied

### image_status Invalid Option "failed" (Jan 2, 2026) - 422 ERROR FIX
**File:** `workers/jobs/image_generation.py`, `workers/utils/images.py`
**Issue:** Code tried to set `image_status: "failed"` but this is NOT a valid option in Airtable
**Valid Options:** `needs_image`, `generated` (ONLY THESE TWO!)
**Fix:**
1. Removed all `image_status: "failed"` updates
2. On failure, leave status as `needs_image` so stories can be retried
3. Added timestamp to Cloudflare image IDs to avoid 409 conflicts
4. Added better Cloudinary error logging
**Commit:** (pending)

### Cloudflare 409 Conflict (Jan 2, 2026)
**File:** `workers/utils/images.py`
**Issue:** Same image ID used on re-runs, causing "Resource already exists" error
**Fix:** Added Unix timestamp to image IDs for uniqueness + retry logic for 409s
**Commit:** (pending)

### Non-existent image_prompt Field (Jan 2, 2026) - 422 ERROR FIX
**File:** `workers/jobs/image_generation.py`
**Issue:** `_get_pending_decorations()` requested `image_prompt` field which does NOT exist in Newsletter Issue Stories table, causing 422 Unprocessable Entity error
**Root Cause:** The n8n workflow builds image prompts dynamically from `headline` + `b1` + `b2` + `b3`, it doesn't store them
**Fix:**
1. Changed field list to: `['story_id', 'headline', 'b1', 'b2', 'b3', 'image_status', 'slot_order', 'label']`
2. Added `_build_image_prompt(headline, b1, b2, b3)` helper function matching n8n format
3. Updated `regenerate_image()` to use same pattern
**Commit:** 6434602

### Gemini API Config Mismatch (Jan 2, 2026)
**File:** `workers/utils/images.py`
**Issue:** Python used `imageDimensions: {width: 636, height: 358}` but n8n uses `imageConfig.aspectRatio: "16:9"`
**Fix:**
1. Changed to `imageConfig.aspectRatio: "16:9"` to match n8n
2. Removed redundant prompt wrapper (prompt already formatted by `_build_image_prompt()`)
3. Added detailed logging for debugging
4. Increased timeout to 90s
**Commit:** `57d46f8`

### Cloudinary SDK vs HTTP Upload Preset (Jan 2, 2026) - CRITICAL FIX
**File:** `workers/utils/images.py`
**Issue:** Python used Cloudinary SDK with `CLOUDINARY_URL` but n8n uses HTTP POST with upload preset `MakeImage`
**Root Cause:** Two completely different upload methods:
- n8n: HTTP POST to `https://api.cloudinary.com/v1_1/dzocuy47k/image/upload` with `upload_preset: "MakeImage"`
- Python (wrong): `cloudinary.uploader.upload()` SDK call requiring auth from `CLOUDINARY_URL`
**Fix:**
1. Replaced Cloudinary SDK upload with HTTP POST matching n8n exactly
2. Use `upload_preset: "MakeImage"` (no API key/secret needed)
3. Apply URL transformation: `/upload/` → `/upload/c_scale,w_636,q_auto:eco,f_webp/`
4. Removed cloudinary SDK imports and config
**Commit:** `57d46f8`

### Wrong Field Names in _get_pending_decorations (Jan 2, 2026)
**File:** `workers/jobs/image_generation.py`
**Issue:** `_get_pending_decorations()` and `regenerate_image()` using wrong field names:
- `storyID` → `story_id`
- `ai_headline` → `headline`
- `pivotId` removed (doesn't exist in Newsletter Issue Stories table)
**Fix:** Updated field names to match actual Airtable schema
**Commit:** (pending)

### Wrong issue_id Format (Jan 2, 2026)
**File:** `workers/jobs/decoration.py`
**Issue:** issue_id was "Pivot 5-2026-01-02" but should be "Pivot 5 - Jan 02"
**Fix:** Parse date and format as `%b %d` (e.g., "Jan 02")
**Commit:** `becdad8`

### Wrong Field Names in Image Generation (Jan 2, 2026)
**File:** `workers/jobs/image_generation.py`
**Issue:** Using `storyID`, `ai_headline` but Airtable has `story_id`, `headline`
**Fix:** Updated field names to match actual Airtable schema
**Commit:** `becdad8`

### Wrong Field Names (Jan 1, 2026)
**File:** `workers/jobs/decoration.py`
**Issue:** Using `storyID`, `ai_headline`, `ai_bullet_1/2/3` but Airtable has `story_id`, `headline`, `b1/b2/b3`
**Fix:** Updated field names to match actual Airtable schema
**Commit:** `447e7bb`

### Wrong Table for Article Lookup (Jan 1, 2026)
**File:** `workers/utils/airtable.py`
**Issue:** `get_article_by_pivot_id()` was using wrong base and table
**Fix:** Changed to use AI Editor 2.0 base with Newsletter Selects table
**Commit:** `5689e6d`

### AirtableClient Import Shadowing (Jan 1, 2026)
**File:** `workers/jobs/decoration.py`
**Issue:** Local import on line 204 shadowed top-level import
**Fix:** Removed redundant import
**Commit:** `c58cba1`

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis for job queue |
| `ANTHROPIC_API_KEY` | Claude API key |
| `GOOGLE_API_KEY` | Gemini API key |
| `AIRTABLE_API_KEY` | Airtable API key |
| `TRIGGER_SECRET` | `pivot5-trigger-secret-2024` |
