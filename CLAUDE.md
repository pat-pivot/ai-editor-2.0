# AI Editor 2.0 - Project Notes

## ⚠️ CRITICAL: Gemini Model Requirements

**DO NOT USE OUTDATED GEMINI MODELS.** If you find any reference to `gemini-2.0-flash`, `gemini-2.0-flash-exp`, or any Gemini 2.x model, it is OUTDATED and must be updated immediately.

| Use Case | Required Model | NEVER Use |
|----------|----------------|-----------|
| LLM / Pre-Filter work | `gemini-3-flash-preview` | ~~gemini-2.0-flash~~ |
| Text Generation | `gemini-3-pro` | ~~gemini-2.0-pro~~ |
| Image Generation | `gemini-3` | ~~gemini-2.0~~ |

**Files that use Gemini (verify these):**
- `workers/utils/gemini.py` - Main Gemini client (MUST use `gemini-3-flash-preview`)
- `db/seed-prompts-python-syntax.sql` - Database seeds
- `src/app/api/setup/route.ts` - API setup
- `src/app/api/prompts/seed/route.ts` - Prompt seeding

---

## ⚠️ CRITICAL: Anthropic Claude Model Requirements

**DO NOT USE OUTDATED CLAUDE MODELS.** Claude 4.5 models use a different naming convention than Claude 3.x models.

| Use Case | Required Model | NEVER Use |
|----------|----------------|-----------|
| Fast AI Scoring | `claude-haiku-4-5-20251001` | ~~claude-3-5-haiku-20241022~~ |
| Standard Tasks | `claude-sonnet-4-5-20250929` | ~~claude-sonnet-4-20250514~~ |
| Complex Tasks | `claude-opus-4-5-20251101` | ~~claude-3-opus~~ |

**Claude 4.5 Model ID Format:** `claude-{tier}-{major}-{minor}-{YYYYMMDD}`
- Haiku 4.5: `claude-haiku-4-5-20251001` (October 1, 2025)
- Sonnet 4.5: `claude-sonnet-4-5-20250929` (September 29, 2025)
- Opus 4.5: `claude-opus-4-5-20251101` (November 1, 2025)

**Files that use Claude (verify these):**
- `workers/jobs/ai_scoring.py` - AI Scoring job (MUST use `claude-haiku-4-5-20251001`)
- `workers/utils/claude.py` - Claude API client

---

## ⚠️ CRITICAL: Git Repository Structure

**This `app/` folder is its OWN git repository, separate from the parent folder.**

```
pivot-5-website_11.19.25/              ← Parent repo (DO NOT use for this project)
└── ai-editor-2.0-full-stack-application/
    └── app/                           ← THIS is the git repo for AI Editor 2.0
        └── .git/                      ← Git repo root is HERE
```

**Git commands MUST be run from within `/app/`:**
```bash
cd /Users/patsimmons/client-coding/pivot-5-website_11.19.25/ai-editor-2.0-full-stack-application/app
git status
git add .
git commit -m "message"
git push
```

**Remote:** `https://github.com/pat-pivot/ai-editor-2.0.git`

---

## CRITICAL: This App REPLACES n8n Workflows

This full-stack application is designed to **completely replace** the n8n workflows for the Pivot 5 newsletter pipeline. The Python workers with Redis Queue run the actual newsletter generation pipeline. Prompts are stored in PostgreSQL and editable from the dashboard UI.

**When a user edits a prompt in the dashboard, it affects the real automated pipeline.**

## Documentation References

For detailed implementation guidance, refer to these docs in `/docs/`:

| Document | Purpose |
|----------|---------|
| `AI-Editor-2.0-Full-Stack-Application-Implementation-Plan-12-23-25.md` | Full architecture overview |
| `AI-Editor-2.0-Infrastructure-12-23-25.md` | Complete infrastructure reference |
| `AI-Editor-2.0-Infrastructure-Step-1-12-23-25.md` | Step 1: Pre-Filter implementation |
| `AI-Editor-2.0-Infrastructure-Step-2-12-23-25.md` | Step 2: Slot Selection implementation |
| `AI-Editor-2.0-Infrastructure-Step-3-12-23-25.md` | Step 3: Decoration implementation |
| `AI-Editor-2.0-Infrastructure-Step-4-12-23-25.md` | Step 4: HTML Compile implementation |
| `AI-Editor-2.0-Infrastructure-Step-5-12-23-25.md` | Step 5: Send/Archive implementation |

**For step-specific work, always read the individual step docs** - they contain detailed breakdowns of each pipeline phase.

## CRITICAL: Directory Structure

The working directory is `/app/` - this IS the Next.js project root.

```
/app/
├── src/                      # Next.js App Router (frontend)
│   ├── app/                  # Pages and API routes
│   │   └── api/              # API endpoints
│   │       ├── prompts/      # CRUD for system prompts
│   │       ├── sources/      # Source credibility scores
│   │       └── health/       # Health check
│   ├── components/           # React components
│   └── lib/                  # Utilities (db.ts, airtable.ts)
├── workers/                  # Python workers (background jobs)
│   ├── jobs/                 # Job handlers by step
│   ├── utils/                # Shared utilities
│   │   ├── db.py            # PostgreSQL connection
│   │   ├── prompts.py       # Load prompts from database
│   │   ├── airtable.py      # Airtable client
│   │   ├── claude.py        # Claude API client
│   │   └── gemini.py        # Gemini API client
│   └── worker.py            # RQ worker entry point
├── db/                       # Database schema
│   └── init.sql             # PostgreSQL schema with system_prompts table
└── docs/                     # Implementation documentation
```

## CRITICAL: Deployment

**This project deploys on RENDER, NOT Vercel.**

- Render dashboard: https://dashboard.render.com
- Deployment is automatic on push to main
- See `workers/render.yaml` for full deployment config

### Services
- `ai-editor-dashboard` - Next.js frontend
- `ai-editor-worker` - Python RQ worker
- `ai-editor-scheduler` - Python RQ scheduler (cron jobs)
- `ai-editor-db` - PostgreSQL database
- `ai-editor-redis` - Redis for job queue

## Architecture

```
Frontend (Next.js)
    ↓
API Routes (/api/prompts, /api/jobs)
    ↓
Redis Queue (RQ)
    ↓
Python Workers (jobs/)
    ↓
PostgreSQL (prompts) + Airtable (articles)
```

## System Prompts (17 Total)

Prompts are stored in PostgreSQL `system_prompts` table with versioning. The utility `workers/utils/prompts.py` provides functions to load prompts.

**⚠️ IMPORTANT:** Step 1 Pre-Filter prompts are currently HARDCODED in `workers/utils/gemini.py` and do NOT load from the database. See `docs/System-Prompt-Engineering-12-26-25.md` for details and fix plan.

| Step | Prompt Key | Model | Purpose |
|------|------------|-------|---------|
| 1 | slot_1_prefilter | Gemini 3 Flash | Jobs/Economy pre-filter |
| 1 | slot_2_prefilter | Gemini 3 Flash | Big Tech pre-filter |
| 1 | slot_3_prefilter | Gemini 3 Flash | Industry Verticals pre-filter |
| 1 | slot_4_prefilter | Gemini 3 Flash | Emerging Tech pre-filter |
| 1 | slot_5_prefilter | Gemini 3 Flash | Consumer AI pre-filter |
| 2 | slot_1_agent | Claude Sonnet | Slot 1 selection agent |
| 2 | slot_2_agent | Claude Sonnet | Slot 2 selection agent |
| 2 | slot_3_agent | Claude Sonnet | Slot 3 selection agent |
| 2 | slot_4_agent | Claude Sonnet | Slot 4 selection agent |
| 2 | slot_5_agent | Claude Sonnet | Slot 5 selection agent |
| 2 | subject_line | Claude Sonnet | Email subject generator |
| 3 | headline_generator | Claude Sonnet | Story headline |
| 3 | bullet_generator | Claude Sonnet | 3 bullet points |
| 3 | bold_formatter | Claude Sonnet | Apply bold formatting |
| 3 | image_prompt | Claude Sonnet | Generate image prompt |
| 3 | image_generator | Gemini | Generate actual image |
| 4 | summary_generator | Claude Sonnet | 15-word newsletter summary |

## Loading Prompts in Workers

```python
from utils.prompts import get_prompt, get_slot_prompt

# Get any prompt by key
prompt = get_prompt('headline_generator')

# Get slot-specific prompt
prompt = get_slot_prompt(step=1, slot=1)  # Returns slot_1_prefilter content
```

## CRITICAL: Airtable API Access

**When the user asks to "look at Airtable" or verify data in Airtable tables, use the Airtable API directly via curl.**

Credentials are in `.env.local`:
```bash
AIRTABLE_API_KEY=<stored in .env.local>
AIRTABLE_BASE_ID=appwSozYTkrsQWUXB  # Pivot Media Master
AI_EDITOR_BASE_ID=appglKSJZxmA9iHpl  # AI Editor 2.0
```

### Quick Query Examples

**List records from Newsletter Stories:**
```bash
curl "https://api.airtable.com/v0/appwSozYTkrsQWUXB/tblY78ziWp5yhiGXp?maxRecords=10" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY"
```

**Filter by date (URL-encoded formula):**
```bash
# filterByFormula: IS_SAME({date_og_published}, '2025-12-27', 'day')
curl "https://api.airtable.com/v0/appwSozYTkrsQWUXB/tblY78ziWp5yhiGXp?filterByFormula=IS_SAME(%7Bdate_og_published%7D%2C%20%272025-12-27%27%2C%20%27day%27)" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY"
```

### Key Table IDs

| Table | Base | Table ID |
|-------|------|----------|
| Newsletter Stories | Pivot Media Master | `tblY78ziWp5yhiGXp` |
| Articles | Pivot Media Master | `tblGumae8KDpsrWvh` |
| Pre-Filter Log | AI Editor 2.0 | `tbl72YMsm9iRHj3sp` |
| Selected Slots | AI Editor 2.0 | `tblzt2z7r512Kto3O` |
| Decoration | AI Editor 2.0 | `tbla16LJCf5Z6cRn3` |

---

## Airtable Field Names (Verified via API 12/24/25)

### Newsletter Stories Table (tblY78ziWp5yhiGXp) - Pivot Media Master
- `id`, `pivotId`, `storyID`
- `ai_headline`, `ai_dek`, `ai_bullet_1`, `ai_bullet_2`, `ai_bullet_3`
- `core_url`, `topic`, `sentiment`, `fit_score`, `tags`
- `newsletter`, `date_og_published`, `image_url`, `pivotnews_url`

### Pre-Filter Log Table (tbl72YMsm9iRHj3sp) - AI Editor 2.0
- `core_url` (NOT `original_url`)
- `date_og_published`, `date_prefiltered`
- `storyID`, `pivotId`, `headline`, `slot`, `source_id`

### Decoration Table (tbla16LJCf5Z6cRn3) - AI Editor 2.0
- `issue_id`, `slot_order`, `story_id`, `headline`, `label`
- `b1`, `b2`, `b3`, `ai_dek`
- `image_url`, `raw`, `image_status`, `social_status`
- `blog_post_raw`, `pivotnews_url`

### AI Editor Queue Table (tblkVBP5mKq3sBpkv) - AI Editor 2.0
- `original slot`, `status`
- Note: This table has minimal fields; used for manual story queuing

### Selected Slots Table (tblzt2z7r512Kto3O) - AI Editor 2.0
- `issue_id`, `slot`, `story_id`, `pivotId`
- `headline`, `source_id`

## API Endpoints

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/prompts` | GET, PATCH | Get/update system prompts |
| `/api/prompts/versions` | GET, POST | Version history & rollback |
| `/api/sources` | GET, POST, PATCH, DELETE | Source credibility scores |
| `/api/health` | GET | Health check |

## Database Schema (Key Tables)

```sql
-- System prompts with versioning
system_prompts (
  prompt_key VARCHAR UNIQUE,  -- e.g., 'slot_1_prefilter'
  step_id INT,
  name VARCHAR,
  model VARCHAR,
  temperature DECIMAL,
  slot_number INT
)

system_prompt_versions (
  prompt_id UUID REFERENCES system_prompts,
  version INT,
  content TEXT,
  is_current BOOLEAN,
  created_by_email VARCHAR
)

-- Stored procedures
update_prompt_content(key, content, user_id, email, summary)
rollback_prompt(key, version, user_id, email)
```
