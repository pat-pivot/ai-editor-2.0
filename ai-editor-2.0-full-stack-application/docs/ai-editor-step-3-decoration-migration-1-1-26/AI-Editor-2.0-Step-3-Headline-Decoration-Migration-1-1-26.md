# AI Editor 2.0 - Step 3: Headline Decoration Migration

**Date:** January 1, 2026
**Status:** BLOCKED - Fixing Wrong Airtable Base Reference
**Source:** n8n Workflow `HCbd2g852rkQgSqr` (STEP 3 AI Editor 2.0 - Decoration_12.19.25)
**Target:** Python Workers in `ai-editor-2.0-full-stack-application`

---

## ⛔ CRITICAL BUG: Wrong Airtable Base Reference (Jan 1, 2026)

### Problem

The Python worker code is using the **DEPRECATED** Pivot Media Master base instead of AI Editor 2.0:

| Base | ID | Status |
|------|----|--------|
| **AI Editor 2.0** | `appglKSJZxmA9iHpl` | ✅ CORRECT - Use for ALL operations |
| Pivot Media Master | `appwSozYTkrsQWUXB` | ❌ DEPRECATED - DO NOT USE |

### Symptom

When running decoration job, ALL 5 stories return "Article not found" errors:
```json
{
  "decorated": 0,
  "errors": [
    {"error": "Article not found: p_abseoo", "slot": 1},
    {"error": "Article not found: p_1wx8v01", "slot": 2},
    {"error": "Article not found: p_f7lruk", "slot": 4}
  ]
}
```

### Root Cause

`workers/utils/airtable.py` has wrong table references:

**WRONG (Current Code):**
```python
# Line 25 - WRONG BASE ID
self.pivot_media_base_id = os.environ.get('AIRTABLE_BASE_ID', 'appwSozYTkrsQWUXB')

# Line 30 - WRONG TABLE ID (doesn't exist in AI Editor 2.0)
self.articles_table_id = os.environ.get('AIRTABLE_ARTICLES_TABLE', 'tblGumae8KDpsrWvh')

# get_article_by_pivot_id() uses wrong base and wrong field name
formula=f"{{pivot_Id}}='{pivot_id}'"  # ← Wrong: capital I
```

**CORRECT (From n8n Workflow):**
```python
# Use AI Editor 2.0 base for EVERYTHING
self.ai_editor_base_id = 'appglKSJZxmA9iHpl'

# Correct table for article lookup
self.articles_all_ingested_table_id = 'tblMfRgSNSyoRIhx1'

# Correct field name (lowercase)
formula=f"{{pivot_id}}='{pivot_id}'"  # ← Correct: lowercase
```

### Files Affected

All files referencing the deprecated `appwSozYTkrsQWUXB` base:

| File | Lines | Fix Required |
|------|-------|--------------|
| `workers/utils/airtable.py` | 25, 67, 100, 120, 138, 144, 152 | Update to AI Editor 2.0 base |
| `workers/jobs/ingest.py` | 256 | Update base reference |
| `workers/jobs/html_compile.py` | 364 | Update base reference |
| `workers/jobs/mautic_send.py` | 174, 213 | Update base reference |
| `workers/render.yaml` | 33, 102, 173, 202 | Update env vars |

### Required Fix

Update `airtable.py` with correct configuration:

```python
# CORRECT TABLE IDS (All in AI Editor 2.0 base: appglKSJZxmA9iHpl)
AIRTABLE_TABLES = {
    "selected_slots": "tblzt2z7r512Kto3O",
    "articles_all_ingested": "tblMfRgSNSyoRIhx1",  # For article lookup
    "newsletter_selects": "tblKhICCdWnyuqgry",    # For story metadata
    "newsletter_issue_stories": "tbla16LJCf5Z6cRn3",  # Output table
}
```

---

## 🎯 OBJECTIVE & SUCCESS CRITERIA

### What Constitutes a Successful Run

A successful STEP 3 Decoration run will:

1. **Read from AI Editor Selected Slots** (`tblzt2z7r512Kto3O`)
   - Filter: `status='pending'`
   - Get issue with 5 slots containing `pivotId` for each slot
   - Example: Issue for `pivot5-jan-02` (next day's newsletter)

2. **Fetch raw content from Newsletter Selects** (`tblKhICCdWnyuqgry`)
   - Lookup each slot's `pivotId` (e.g., `pivot_id` field in Newsletter Selects)
   - Get the `raw` column containing full article content
   - Get `headline`, `source_name`, `core_url`, `date_og_published`

3. **Generate AI decoration via Claude**
   - Create `ai_headline` (punchy, Title Case, max 80 chars)
   - Create `ai_dek` (one sentence hook)
   - Create `ai_bullet_1`, `ai_bullet_2`, `ai_bullet_3` (EXACTLY 2 sentences each)
   - Create `label` (from 18 categories: WORK, EDUCATION, etc.)
   - Create `image_prompt` (for later image generation)

4. **Apply HTML bolding to bullets**
   - Use `<b>text</b>` format (NOT Markdown `**text**`)
   - Bold ONE key phrase per bullet (5-15 words)

5. **Write to Newsletter Issue Stories** (`tbla16LJCf5Z6cRn3`)
   - Create one record per slot with all decorated fields
   - Include `storyID`, `pivotId`, `raw` (from Newsletter Selects)
   - Set `image_status='needs_image'` for image generation step

6. **Update Selected Slots status**
   - Change status from `pending` to `decorated`

### Verification Checklist

After a successful run, verify in Airtable:

- [ ] **Newsletter Issue Stories** has 5 new records (one per slot)
- [ ] Each record has `ai_headline` populated
- [ ] Each record has `ai_dek` populated
- [ ] Each record has `ai_bullet_1`, `ai_bullet_2`, `ai_bullet_3` populated
- [ ] Bullets contain `<b>` HTML tags (not Markdown `**`)
- [ ] Bullets are EXACTLY 2 sentences each
- [ ] `label` is from the 18 allowed categories
- [ ] `raw` column is populated from Newsletter Selects
- [ ] `pivotId` matches source from Selected Slots
- [ ] `image_status='needs_image'`
- [ ] Selected Slots record status changed to `decorated`

---

## 📊 STEP-BY-STEP DATA FLOW

### Table Relationships

```
┌─────────────────────────────────────┐
│  AI Editor Selected Slots           │
│  tblzt2z7r512Kto3O                  │
│  https://airtable.com/appglKSJZxmA9iHpl/tblzt2z7r512Kto3O
│                                     │
│  Filter: status='pending'           │
│  Fields:                            │
│  ├── issue_date                     │
│  ├── slot_1_pivotId                 │
│  ├── slot_1_storyId                 │
│  ├── slot_1_headline                │
│  ├── slot_1_source                  │
│  ├── slot_2_pivotId ... slot_5_*   │
│  └── status                         │
└───────────────┬─────────────────────┘
                │
                │ For each slot 1-5, lookup pivotId
                ▼
┌─────────────────────────────────────┐
│  Newsletter Selects                 │
│  tblKhICCdWnyuqgry                  │
│  https://airtable.com/appglKSJZxmA9iHpl/tblKhICCdWnyuqgry
│                                     │
│  Lookup: pivot_id = slot_X_pivotId  │
│  Fields to retrieve:                │
│  ├── pivot_id                       │
│  ├── headline                       │
│  ├── raw          ◄─── CRITICAL!    │
│  ├── source_name                    │
│  ├── core_url                       │
│  ├── date_og_published              │
│  └── topic                          │
└───────────────┬─────────────────────┘
                │
                │ Pass to Claude for AI decoration
                ▼
┌─────────────────────────────────────┐
│  Claude API (Sonnet 4.5)            │
│                                     │
│  Input:                             │
│  ├── headline (from Newsletter Selects)
│  ├── raw content (from Newsletter Selects)
│  ├── source_name                    │
│  └── newsletter style variant       │
│                                     │
│  Output:                            │
│  ├── ai_headline                    │
│  ├── ai_dek                         │
│  ├── ai_bullet_1 (2 sentences)      │
│  ├── ai_bullet_2 (2 sentences)      │
│  ├── ai_bullet_3 (2 sentences)      │
│  ├── label (from 18 categories)     │
│  └── image_prompt                   │
└───────────────┬─────────────────────┘
                │
                │ Apply HTML bolding
                ▼
┌─────────────────────────────────────┐
│  Claude API (Bolding Pass)          │
│                                     │
│  Transform bullets:                 │
│  "Text here..." → "Text <b>key phrase</b> here..."
│                                     │
│  Rules:                             │
│  ├── Use <b></b> NOT **             │
│  ├── ONE phrase per bullet          │
│  └── 5-15 words per phrase          │
└───────────────┬─────────────────────┘
                │
                │ Write decorated record
                ▼
┌─────────────────────────────────────┐
│  Newsletter Issue Stories           │
│  tbla16LJCf5Z6cRn3                  │
│  https://airtable.com/appglKSJZxmA9iHpl/tbla16LJCf5Z6cRn3
│                                     │
│  Fields to write:                   │
│  ├── storyID (from Selected Slots)  │
│  ├── pivotId (from Selected Slots)  │
│  ├── slot_order (1-5)               │
│  ├── raw (from Newsletter Selects)  │
│  ├── ai_headline (from Claude)      │
│  ├── ai_dek (from Claude)           │
│  ├── ai_bullet_1 (from Claude)      │
│  ├── ai_bullet_2 (from Claude)      │
│  ├── ai_bullet_3 (from Claude)      │
│  ├── label (from Claude)            │
│  ├── image_prompt (from Claude)     │
│  ├── image_status = 'needs_image'   │
│  ├── source_id (from Newsletter Selects)
│  ├── core_url (from Newsletter Selects)
│  └── date_decorated (today)         │
└─────────────────────────────────────┘
```

### Execution Flow (Step by Step)

```
1. Query Selected Slots where status='pending'
   └─► Get issue record (e.g., pivot5-jan-02)

2. For each slot 1-5:
   a. Extract slot_X_pivotId from issue record
   b. Query Newsletter Selects where pivot_id = slot_X_pivotId
      └─► Get 'raw' content, 'headline', 'source_name', 'core_url'

   c. Call Gemini to clean content (optional)
      └─► Remove navigation, ads, boilerplate

   d. Call Claude Content Creator
      Input: headline, raw content, source, newsletter_style
      Output: ai_headline, ai_dek, ai_bullet_1/2/3, label, image_prompt

   e. Call Claude Bolding Pass
      Input: ai_bullet_1, ai_bullet_2, ai_bullet_3
      Output: Bullets with <b>key phrase</b> tags

   f. Write to Newsletter Issue Stories
      └─► Create new record with all decorated fields

3. Update Selected Slots
   └─► Set status='decorated'
```

---

## 🔑 ENVIRONMENT VARIABLES

**File:** `/app/.env.local`

### Available Credentials

```bash
# Database
DATABASE_URL=postgresql://ai_editor_db_user:***@dpg-d55iqn4hg0os73a55ka0-a/ai_editor_db

# Airtable
AIRTABLE_API_KEY=patQVZtZjQS8GU78r.***
AI_EDITOR_BASE_ID=appglKSJZxmA9iHpl

# AI APIs
GEMINI_API_KEY=AIzaSyDvnr0VDD_F5UhE4JTDnKEg_D34KpdQSIE
# ANTHROPIC_API_KEY=  <-- NEEDS TO BE ADDED

# Trigger Service
TRIGGER_SECRET=pivot5-trigger-secret-2024
```

### Required for Decoration

| Variable | Status | Purpose |
|----------|--------|---------|
| `DATABASE_URL` | ✅ Present | PostgreSQL for prompts |
| `AIRTABLE_API_KEY` | ✅ Present | Airtable read/write |
| `AI_EDITOR_BASE_ID` | ✅ Present | AI Editor 2.0 base |
| `GEMINI_API_KEY` | ✅ Present | Content cleaning |
| `ANTHROPIC_API_KEY` | ⚠️ MISSING | Claude API for decoration |

**NOTE:** ANTHROPIC_API_KEY must be added to `.env.local` before running.

---

## Overview

This document covers the migration of STEP 3 Decoration from n8n to the Python full-stack application. The n8n workflow handles two distinct operations that will be split into **two separate UI cards** in the dashboard:

1. **Card 1: Text Decoration** - Generate headlines, DEKs, bullets, and labels
2. **Card 2: Image Generation** - Generate images using Gemini/OpenAI with Cloudflare upload

---

## IMPORTANT: No Cron Triggers

**Schedule triggers will be added later.** This migration focuses on:
- Manual trigger via dashboard UI button
- API endpoint trigger (`/api/trigger/decoration`)
- Getting the core functionality working first

Do NOT implement cron/scheduler jobs for this migration phase.

---

## CRITICAL: n8n Is Source of Truth for Prompts

**The Python codebase has OUTDATED prompts.** The n8n workflow contains the latest, tested, and optimized prompts.

| Component | n8n (CORRECT) | Python (WRONG) |
|-----------|---------------|----------------|
| Bolding Format | HTML `<b>text</b>` | Markdown `**text**` |
| Bullet Fields | `ai_bullet_1`, `ai_bullet_2`, `ai_bullet_3` | `b1`, `b2`, `b3` |
| Label Categories | 18 specific labels (WORK, EDUCATION, etc.) | Generic labels ("AI NEWS") |
| Audience Context | Full CEO/Executive briefing | Partial |
| Newsletter Styles | pivot_ai, pivot_build, pivot_invest | None |
| Sentence Rule | "EXACTLY 2 sentences per bullet" | Not enforced |

**MUST use the EXACT n8n prompts from `n8n-prompts-extracted.md`**

---

## Target Architecture

### UI/UX Design

The dashboard will have **two separate cards** (similar to the Sandbox Pipeline layout with "Run Ingest" and "AI Scoring"):

```
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│  STEP 3a: TEXT DECORATION       │  │  STEP 3b: IMAGE GENERATION      │
│                                 │  │                                 │
│  Generate headlines, DEKs,      │  │  Generate images from prompts   │
│  bullets for selected stories   │  │  and upload to Cloudflare       │
│                                 │  │                                 │
│  ┌─────────────────────────┐    │  │  ┌─────────────────────────┐    │
│  │   Run Text Decoration   │    │  │  │   Run Image Generation  │    │
│  └─────────────────────────┘    │  │  └─────────────────────────┘    │
│                                 │  │                                 │
│  Status: Pending                │  │  Status: Pending                │
│  Last Run: --                   │  │  Last Run: --                   │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

### Worker Architecture

```
Dashboard UI
    │
    ├── /api/trigger/decoration ───────► Redis Queue ───► decoration.py
    │                                                          │
    │                                                          ▼
    │                                                    Claude API
    │                                                    (headline, bullets, dek)
    │                                                          │
    │                                                          ▼
    │                                                    Newsletter Issue Stories
    │                                                    (Airtable write)
    │
    └── /api/trigger/image-generation ─► Redis Queue ───► image_generation.py
                                                               │
                                                               ▼
                                                         Gemini Imagen 3
                                                         (or OpenAI fallback)
                                                               │
                                                               ▼
                                                         Cloudflare Images
                                                               │
                                                               ▼
                                                         Newsletter Issue Stories
                                                         (image_url update)
```

---

## Data Passing Strategy

### Python Pattern (NOT JSON.stringify)

Based on research of Step 2 slot selection implementation, Python workers use **native Python dicts** for data passing between LLM calls:

```python
# CORRECT: Native dict approach
story_data = {
    "headline": article.get("headline"),
    "source": article.get("source_id"),
    "content": cleaned_content
}

# Pass dict directly to next function
decoration_result = claude.decorate_story(story_data, cleaned_content)

# Result is already a dict (from JSON parsing)
bolded_result = claude.apply_bolding(decoration_result)
```

**Key principles:**
1. **Keep data as Python dicts** throughout the pipeline
2. **Use `.format()` for prompt variable substitution**
3. **JSON only at API boundaries** (API responses, Claude output parsing)
4. **Never serialize for internal passing** - just pass the dict object

---

## CRITICAL GAPS: Python vs n8n

### Gap 1: Bolding Uses Wrong Format

**Location:** `claude.py:486`

```python
# WRONG (current Python)
prompt = f"""Apply markdown bold (**text**) to 1-2 key phrases...
```

```
# CORRECT (n8n)
Wrap that phrase in HTML bold tags: <b>phrase here</b>
```

**Fix:** Replace Markdown `**text**` with HTML `<b>text</b>` in bolding prompt

### Gap 2: Wrong Field Names for Bullets

**Location:** `claude.py:345, 412-413`

```python
# WRONG (current Python)
Returns: {ai_headline, ai_dek, b1, b2, b3, image_prompt, label}
```

```json
// CORRECT (n8n)
{
  "ai_bullet_1": "...",
  "ai_bullet_2": "...",
  "ai_bullet_3": "..."
}
```

**Fix:** Change `b1/b2/b3` to `ai_bullet_1/ai_bullet_2/ai_bullet_3` throughout

### Gap 3: Missing 18 Label Categories

**Location:** `claude.py:439, 543`

```python
# WRONG (current Python fallback)
label: Topic label in ALL CAPS (e.g., "JOBS & ECONOMY", "BIG TECH", "HEALTHCARE AI")
```

```
# CORRECT (n8n - 18 categories)
WORK, EDUCATION, INFRASTRUCTURE, POLICY, TALENT, HEALTH, RETAIL,
ENTERPRISE, COMPETITION, FUNDING, SECURITY, TOOLS, SEARCH,
INVESTORS, CHINA, REGULATION, ETHICS, LAWSUITS
```

### Gap 4: Missing Newsletter Style Variants

**n8n has 3 styles, Python has none:**

| Style | Audience | Focus |
|-------|----------|-------|
| `pivot_ai` | AI field professionals | Capabilities, limitations, ecosystem |
| `pivot_build` | Builders, product managers | Execution, experiments, roadmaps |
| `pivot_invest` | Investors, markets-focused | Capital flows, valuations, risk |

### Gap 5: Missing CEO Audience Context

**n8n prompt includes:**
```
## AUDIENCE
- CEOs, founders, general managers, and senior business leaders
- They are busy, strategic thinkers who want actionable insights
- They care about business impact, competitive dynamics, and what matters for decision-making

## VOICE & STYLE
- Confident, clear, informed — like a trusted advisor briefing an executive
```

**Python fallback is missing this entirely.**

### Gap 6: Missing "Exactly 2 Sentences" Rule

**n8n prompt:**
```
## CRITICAL RULES FOR BULLETS
1. Each bullet MUST be EXACTLY 2 sentences. Not 1. Not 3. Exactly 2.
```

**This is why Kunal sees 1-sentence bullets in output.**

---

## Airtable Field Name Corrections

### Newsletter Issue Stories Table (`tbla16LJCf5Z6cRn3`)

| Field | n8n Uses | Python Uses | Correction |
|-------|----------|-------------|------------|
| Bullet 1 | `ai_bullet_1` | `b1` | Change to `ai_bullet_1` |
| Bullet 2 | `ai_bullet_2` | `b2` | Change to `ai_bullet_2` |
| Bullet 3 | `ai_bullet_3` | `b3` | Change to `ai_bullet_3` |
| Story ID | `storyID` | Varies | Ensure exact case |
| Pivot ID | `pivotId` | `pivot_id` | Check case sensitivity |
| Image Status | `needs_image` | `pending` | Verify allowed values |

---

## Implementation Tasks

### Phase 1: Text Decoration Worker (Card 1)

**No cron triggers - manual trigger only.**

#### 1.1 Store n8n Prompts in PostgreSQL

- [ ] Insert Content Creator prompt (EXACT from n8n-prompts-extracted.md)
- [ ] Insert Bolding Pass prompt (with HTML `<b>` tags)
- [ ] Insert Newsletter Style variants (pivot_ai, pivot_build, pivot_invest)
- [ ] Insert Gemini Content Cleaner prompt

#### 1.2 Update claude.py

- [ ] Replace bolding prompt: `**text**` → `<b>text</b>`
- [ ] Change output field names: `b1/b2/b3` → `ai_bullet_1/ai_bullet_2/ai_bullet_3`
- [ ] Add 18 label categories to fallback prompt
- [ ] Add CEO audience context to fallback prompt
- [ ] Add "EXACTLY 2 sentences" rule enforcement

#### 1.3 Update decoration.py

- [ ] Add newsletter style selection based on issue type
- [ ] Integrate Newsletter Selects data source (`get_newsletter_selects()`)
- [ ] Use native dict passing (NOT JSON.stringify)
- [ ] Map output fields correctly to Airtable

#### 1.4 Add API Endpoint

- [ ] Create `/api/trigger/decoration` endpoint
- [ ] Add to JOB_FUNCTIONS in trigger.py
- [ ] Add to QUEUE_MAPPING as 'default' priority

#### 1.5 Add UI Card

- [ ] Create Text Decoration card component
- [ ] Add "Run Text Decoration" button
- [ ] Add status indicator
- [ ] Add execution logs display

### Phase 2: Image Generation Worker (Card 2)

**No cron triggers - manual trigger only.**

#### 2.1 Update image_generation.py

- [ ] Verify Gemini Imagen 3 model configuration
- [ ] Verify OpenAI fallback configuration
- [ ] Verify Cloudflare upload logic

#### 2.2 Add API Endpoint

- [ ] Create `/api/trigger/image-generation` endpoint
- [ ] Add to JOB_FUNCTIONS in trigger.py

#### 2.3 Add UI Card

- [ ] Create Image Generation card component
- [ ] Add "Run Image Generation" button
- [ ] Add status indicator

### Phase 3: Dashboard Integration

- [ ] Create two-card layout in Step 3 section
- [ ] Wire up buttons to API endpoints
- [ ] Display job status and logs

---

## EXACT n8n Prompts to Store

### Content Creator Prompt

**Store in PostgreSQL with key: `content_creator`**

See `n8n-prompts-extracted.md` for full prompt. Key elements:

```
MASTER PROMPT — PIVOT 5 AI NEWSLETTER CONTENT CREATION

## YOUR ROLE
You are an expert newsletter editor creating content for Pivot 5's AI-focused newsletter.

## AUDIENCE
- CEOs, founders, general managers, and senior business leaders
- They are busy, strategic thinkers who want actionable insights

## LABEL OPTIONS (choose exactly one):
WORK, EDUCATION, INFRASTRUCTURE, POLICY, TALENT, HEALTH, RETAIL,
ENTERPRISE, COMPETITION, FUNDING, SECURITY, TOOLS, SEARCH,
INVESTORS, CHINA, REGULATION, ETHICS, LAWSUITS

## CRITICAL RULES FOR BULLETS
1. Each bullet MUST be EXACTLY 2 sentences. Not 1. Not 3. Exactly 2.
```

### Bolding Pass Prompt

**Store in PostgreSQL with key: `bolding_pass`**

```
For each bullet field (ai_bullet_1, ai_bullet_2, ai_bullet_3):
1. Identify the SINGLE most important phrase (5-15 words)
2. Wrap that phrase in HTML bold tags: <b>phrase here</b>
3. Only bold ONE phrase per bullet
4. Do NOT change any wording, punctuation, or content
```

---

## Pre-Implementation Checklist

Before coding, verify:

- [ ] **Airtable field names match exactly** (case-sensitive!)
- [ ] **PostgreSQL has n8n prompts loaded**
- [ ] **Model names correct**: `claude-sonnet-4-5-20250929`, `gemini-3-flash-preview`
- [ ] **Newsletter style variants defined**
- [ ] **No cron triggers implemented** (manual only for this phase)

---

## Testing Checklist

After implementation, verify:

- [ ] Bullets have EXACTLY 2 sentences each
- [ ] Bullets contain HTML `<b>` tags (NOT Markdown `**`)
- [ ] Labels are from the 18-category list
- [ ] Field names in Airtable are `ai_bullet_1/2/3` not `b1/b2/b3`
- [ ] Newsletter style matches issue type (pivot_ai/build/invest)
- [ ] Manual trigger from dashboard works
- [ ] Job status displays correctly in UI

---

## Risk Considerations

1. **Prompt changes affect output quality** - Test thoroughly before deploying
2. **Field name changes may break downstream** - Check Step 4 HTML compile
3. **Database prompts must be seeded first** - Or fallbacks will use old prompts
4. **No cron means manual trigger required** - Document for ops team

---

## References

### Migration Documentation
- **Main Migration Doc**: This file
- **Codebase Analysis**: [codebase-analysis.md](./codebase-analysis.md)
- **Worker Architecture**: [worker-architecture.md](./worker-architecture.md)
- **Extracted n8n Prompts**: [n8n-prompts-extracted.md](./n8n-prompts-extracted.md)
- **n8n Workflow JSON**: [step3-n8n-workflow.json](./step3-n8n-workflow.json)

### Project Documentation
- Skill Reference: `/app/.claude/skills/step-3-decoration.md`
- Infrastructure Docs: `/docs/AI-Editor-2.0-Infrastructure-Step-3-12-23-25.md`
- CLAUDE.md: `/app/CLAUDE.md`

### Airtable Tables
| Table | Base | Table ID |
|-------|------|----------|
| Newsletter Issue Stories | AI Editor 2.0 | `tbla16LJCf5Z6cRn3` |
| Selected Slots | AI Editor 2.0 | `tblzt2z7r512Kto3O` |
| Articles All Ingested | AI Editor 2.0 | `tblMfRgSNSyoRIhx1` |
| Newsletter Selects | AI Editor 2.0 | `tblKhICCdWnyuqgry` |
