# AI Editor 2.0 Full-Stack Application Implementation Plan

**Date:** December 23, 2025 (Updated December 26, 2025)
**Project:** AI Editor Dashboard (replaces n8n workflows)
**Document:** AI-Editor-2.0-Full-Stack-Application-Implementation-Plan-12-23-25

---

## IMPLEMENTATION STATUS

| Step | Name | Status | Notes |
|------|------|--------|-------|
| 0 | Ingest | **IMPLEMENTED** | RSS-only ingestion to Articles table. Pending testing by Pat. |
| 1 | Pre-Filter | **IMPLEMENTED** | AI scoring with Gemini. Reads from Articles. |
| 2 | Slot Selection | PLANNED | Claude agents select best stories |
| 3 | Decoration | PLANNED | Headlines, bullets, images |
| 4 | HTML Compile | PLANNED | Email assembly + Mautic send |
| 5 | Send & Social | PLANNED | Social syndication |

**Last Update:** December 26, 2025 - Fixed Step 0 to write to correct table (Articles)

---

## CRITICAL: Pipeline Architecture

**This is the correct data flow. Future coding agents MUST follow this architecture:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 0: INGESTION (RSS Only)                                               │
│  Worker: workers/jobs/ingest.py                                             │
│  Trigger: Manual or scheduled                                               │
│                                                                              │
│  19 RSS Feeds → Fetch → Deduplicate (pivot_Id) → CREATE records            │
│                                                                              │
│  OUTPUT: Articles table (tblGumae8KDpsrWvh)                                 │
│  Fields: pivot_Id, original_url, source_id, date_published, date_ingested  │
│                                                                              │
│  NOTE: NO Firecrawl, NO markdown scraping. RSS-only for speed/cost.        │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: PRE-FILTER (AI Scoring)                                            │
│  Worker: workers/jobs/prefilter.py                                          │
│  Trigger: 9 PM EST                                                          │
│                                                                              │
│  READ: Articles table (fresh articles)                                      │
│  PROCESS: Gemini AI scores for slot eligibility                             │
│  OUTPUT: Pre-Filter Log table (tbl72YMsm9iRHj3sp)                          │
│                                                                              │
│  AI Scoring Fields:                                                         │
│  - fit_score (number): Editorial relevance                                  │
│  - interest_score (number): Reader interest prediction                      │
│  - sentiment (number): Article sentiment                                    │
│  - topic (string): Primary topic classification                             │
│  - reason_for_fit_score (string): AI explanation                            │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: SLOT SELECTION (Claude Agents)                                     │
│  Worker: workers/jobs/slot_selection.py                                     │
│  Trigger: 11:55 PM EST                                                      │
│                                                                              │
│  READ: Pre-Filter Log (high-scoring candidates)                             │
│  PROCESS: 5 sequential Claude agents select 1 story each                    │
│  OUTPUT: Selected Slots table (tblzt2z7r512Kto3O)                          │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: DECORATION (Content + Images)                                      │
│  Worker: workers/jobs/decoration.py                                         │
│  Trigger: 9:25 PM, 9:30 PM EST                                              │
│                                                                              │
│  READ: Selected Slots                                                       │
│  PROCESS: Claude generates headlines, bullets; Gemini generates images      │
│  OUTPUT: Newsletter Issue Stories table (tblaHcFFG6Iw3w7lL)                │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: HTML COMPILE & SEND                                                │
│  Worker: workers/jobs/html_compile.py                                       │
│  Trigger: 10 PM, 5 AM EST                                                   │
│                                                                              │
│  READ: Newsletter Issue Stories (decorated, with images)                    │
│  PROCESS: Compile HTML email, send via Mautic                               │
│  OUTPUT: Newsletter Issues table + Mautic campaign                          │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: SOCIAL SYNDICATION                                                 │
│  Worker: workers/jobs/social_sync.py                                        │
│  Trigger: 4:30 AM, 5:00 AM EST                                              │
│                                                                              │
│  READ: Newsletter Issue Stories (decorated, synced)                         │
│  OUTPUT: P5 Social Posts table                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## CRITICAL: Airtable Table Reference

| Table | Base | Table ID | Purpose |
|-------|------|----------|---------|
| **Articles** | Pivot Media Master | `tblGumae8KDpsrWvh` | Step 0 OUTPUT - Raw RSS ingestion |
| **Pre-Filter Log** | AI Editor 2.0 | `tbl72YMsm9iRHj3sp` | Step 1 OUTPUT - AI scoring results |
| **Selected Slots** | AI Editor 2.0 | `tblzt2z7r512Kto3O` | Step 2 OUTPUT - Agent selections |
| **Newsletter Issue Stories** | Pivot Media Master | `tblaHcFFG6Iw3w7lL` | Step 3 OUTPUT - Decorated stories |
| **Newsletter Issues** | Pivot Media Master | `tbl7mcCCGbjEfli25` | Step 4 OUTPUT - Compiled HTML |
| **Source Scores** | AI Editor 2.0 | `tbl3Zkdl1No2edDLK` | Source credibility ratings |

**Base IDs:**
- Pivot Media Master: `appwSozYTkrsQWUXB`
- AI Editor 2.0: `appglKSJZxmA9iHpl`

---

## Step 0: Ingestion (IMPLEMENTED)

### What Was Built

**File:** `workers/jobs/ingest.py`

The ingestion job fetches articles from 19 RSS feeds and creates records in the **Articles table**.

### Key Implementation Details

1. **Target Table:** Articles (`tblGumae8KDpsrWvh`) in Pivot Media Master base
2. **Deduplication:** Uses `pivot_Id` field (with underscore) as unique key
3. **No Firecrawl:** RSS-only ingestion for speed and cost efficiency
4. **Parallel Fetching:** Uses `aiohttp` to fetch all feeds concurrently

### Fields Written to Articles Table

```python
record = {
    "pivot_Id": pivot_id,           # Unique hash-based identifier (deduplication key)
    "original_url": article["link"], # Source article URL
    "source_id": article["source_id"], # Publication name (e.g., "Reuters")
    "date_ingested": datetime.now(timezone.utc).isoformat(),
}

# Optional field (if present in RSS)
if article["pubDate"]:
    record["date_published"] = article["pubDate"]
```

### PivotID Generation Algorithm

```python
def generate_pivot_id(url: str, title: str) -> str:
    """
    Generate a unique pivot_Id for deduplication.
    Uses URL if available, falls back to title.
    """
    def hash_string(s: str) -> str:
        hash_val = 5381
        for char in s:
            hash_val = ((hash_val << 5) + hash_val) + ord(char)
        return format(hash_val & 0xFFFFFFFF, 'x')[:8]

    # Normalize URL or use title as fallback
    if url:
        normalized = url.lower().strip()
        # Remove tracking parameters, etc.
    else:
        normalized = title.lower().strip()

    return f"p_{hash_string(normalized)}"
```

### RSS Feeds (19 Total)

| Source | URL | Notes |
|--------|-----|-------|
| Reuters AI | `https://rss.app/feeds/MXiuPVkXDT8HqezK.xml` | |
| Reuters Business | `https://rss.app/feeds/C3YLADfGxE5e57eT.xml` | |
| The Neuron | `https://rss.app/feeds/1iWmVmkwOR9FvPtW.xml` | |
| AI Valley | `https://rss.app/feeds/el3M8L2iqw3VrU3A.xml` | |
| There's an AI For That | `https://rss.app/feeds/9SVrxNsg7y419Fke.xml` | |
| The Deep View | `https://rss.app/feeds/NY8oNua0ZxWUYR3Z.xml` | |
| The AI Report | `https://rss.app/feeds/kRbnlccEQPpl1f6M.xml` | |
| CNBC Finance | `https://rss.app/feeds/yD81szEq5uTWg5I5.xml` | |
| The Verge | `https://rss.app/feeds/08AqYC4pZsuLfMKv.xml` | |
| Yahoo Finance | `https://news.yahoo.com/rss/finance` | Native RSS |
| Tech Crunch | `https://rss.app/feeds/YaCBpvEvBDczG9zT.xml` | |
| Tech Republic | `https://rss.app/feeds/mC6cK6lSVgJjRTgO.xml` | |
| SuperHuman | `https://rss.app/feeds/QymucjzuFkzvxvkg.xml` | |
| Semafor Business | `https://rss.app/feeds/ZbdBsJTYo3gDOWmI.xml` | |
| Semafor Technology | `https://rss.app/feeds/6GwMn0gNjbWxUjPN.xml` | |
| Semafor CEO | `https://rss.app/feeds/jSkbNDntFNSdShkz.xml` | |
| Google News AI | `https://news.google.com/rss/search?q=AI+...` | 12h window |
| Google News Finance | `https://news.google.com/rss/search?q=markets+...` | 12h window |
| The Atlantic Technology | `https://rss.app/feeds/L83urFREcjBOcQ5z.xml` | |

**Feed Configuration:** `workers/config/rss_feeds.py`

### How to Run Step 0

**From Dashboard UI:**
1. Navigate to Step 0 (Ingest) page
2. Click "Run Now" button
3. Monitor progress in the running status banner
4. View results in the "Data" tab

**Via API:**
```bash
curl -X POST http://localhost:3000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"step": "ingest"}'
```

---

## Step 1: Pre-Filter (IMPLEMENTED)

### What Was Built

**File:** `workers/jobs/prefilter.py`

Reads fresh articles from the Articles table, uses Gemini AI to score each article for slot eligibility, and writes results to Pre-Filter Log.

### Slot Eligibility Criteria

| Slot | Focus | Freshness |
|------|-------|-----------|
| 1 | AI impact on jobs/economy/stock market/broad impact | 0-24 hours |
| 2 | Tier 1 AI companies (OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon) | 24-48 hours |
| 3 | Industry verticals (Healthcare, Government, Education, Legal, etc.) | 0-7 days |
| 4 | Emerging companies (product launches, fundraising, acquisitions) | 0-48 hours |
| 5 | Consumer AI / human interest (ethics, entertainment, societal impact) | 0-7 days |

### AI Scoring Process

1. Fetch articles from Articles table where `date_ingested` is recent
2. For each article, call Gemini API with slot eligibility prompt
3. Gemini returns: `fit_score`, `interest_score`, `sentiment`, `topic`, `reason_for_fit_score`
4. Write scored articles to Pre-Filter Log with eligible slot number

---

## Overview

This full-stack application is an **admin/ops monitoring dashboard** at `app.pivotmedia.ai` for the fully automated AI Editor newsletter pipeline. This is NOT an editorial tool - the AI runs automatically on schedule. The dashboard exists to:

1. **Monitor** - See that automation is running correctly
2. **Debug** - View detailed logs when something fails
3. **Intervene** - Retry failed jobs, override selections when needed
4. **Configure** - Edit system prompts for the AI models directly from UI
5. **Audit** - Review historical executions and data

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Render)                        │
│  Next.js 16 + React 19 + Tailwind                          │
│  - Dashboard UI (story management, analytics, monitoring)   │
│  - Magic link authentication                                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 API LAYER (Render Web Service)              │
│  Next.js API Routes                                         │
│  - REST endpoints                                           │
│  - Job enqueueing (creates jobs in Redis)                   │
│  - Webhook handlers                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
       ┌──────▼──────┐    ┌────────▼─────────────┐
       │   Redis     │    │   Python Workers     │
       │   Queue     │    │   (Render Jobs)      │
       │   (RQ)      │    │   - Claude API       │
       │             │◄───│   - Airtable sync    │
       └─────────────┘    │   - Mautic API       │
                          │   - Image generation │
                          └──────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
       ┌──────▼──────┐    ┌────────▼────────┐   ┌───────▼───────┐
       │  PostgreSQL │    │    Airtable     │   │    Mautic     │
       │  (Render)   │    │  (keep as-is)   │   │  (analytics)  │
       │  - Jobs     │    │  - Stories      │   │  - Campaigns  │
       │  - Logs     │    │  - Decoration   │   │  - Contacts   │
       │  - Prompts  │    │                 │   │               │
       └─────────────┘    └─────────────────┘   └───────────────┘
```

---

## Tech Stack

| Component | Technology | Deployment |
|-----------|------------|------------|
| Frontend | Next.js 16 + React 19 + Tailwind | Render Web Service |
| API | Next.js API Routes | Render Web Service |
| Background Jobs | Redis Queue (RQ) | Render Redis |
| Workers | Python 3.11 | Render Worker Services |
| Database | PostgreSQL | Render Postgres |
| Content DB | Airtable | Existing |
| Email | Mautic API | Existing |
| AI | Claude API, Gemini API | API calls from workers |

---

## File Structure

```
app/
├── src/                          # Next.js App Router
│   ├── app/
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx          # Overview - pipeline status
│   │   │   ├── step/
│   │   │   │   └── [id]/page.tsx # Dynamic step page (0-5)
│   │   │   ├── data/
│   │   │   │   ├── stories/      # Stories table view
│   │   │   │   ├── sources/      # Source credibility
│   │   │   │   └── issues/       # Newsletter issues
│   │   │   └── analytics/        # Mautic analytics
│   │   └── api/
│   │       ├── jobs/             # Job management
│   │       ├── prompts/          # System prompts CRUD
│   │       └── airtable/         # Airtable proxy
│   ├── components/
│   │   ├── dashboard/
│   │   │   └── sidebar.tsx       # Left navigation
│   │   └── step/
│   │       ├── execution-logs.tsx
│   │       ├── system-prompts.tsx
│   │       └── step-data.tsx
│   └── lib/
│       ├── db.ts                 # PostgreSQL client
│       ├── airtable.ts           # Airtable client
│       └── step-config.ts        # Step metadata
├── workers/                      # Python workers
│   ├── worker.py                 # RQ worker entrypoint
│   ├── scheduler.py              # Cron job scheduler
│   ├── http_trigger.py           # Flask HTTP trigger
│   ├── jobs/
│   │   ├── ingest.py             # Step 0: RSS ingestion
│   │   ├── prefilter.py          # Step 1: AI scoring
│   │   ├── slot_selection.py     # Step 2: Claude agents
│   │   ├── decoration.py         # Step 3: Content + images
│   │   ├── html_compile.py       # Step 4: Email assembly
│   │   └── social_sync.py        # Step 5: Social posts
│   ├── config/
│   │   └── rss_feeds.py          # RSS feed configuration
│   └── utils/
│       ├── pivot_id.py           # PivotID generation
│       ├── airtable.py           # Airtable helpers
│       ├── claude.py             # Claude API
│       ├── gemini.py             # Gemini API
│       └── prompts.py            # Load prompts from DB
├── db/
│   └── init.sql                  # PostgreSQL schema
└── docs/                         # Documentation
```

---

## Dashboard Navigation

The sidebar shows all pipeline steps:

| Route | Page | Description |
|-------|------|-------------|
| `/` | Overview | Pipeline status, today's issue |
| `/step/0` | Ingest | RSS ingestion logs, Articles data |
| `/step/1` | Pre-Filter | AI scoring logs, Pre-Filter Log data |
| `/step/2` | Slot Selection | Agent selection logs, Selected Slots data |
| `/step/3` | Decoration | Content generation logs |
| `/step/4` | HTML Compile | Email compilation logs |
| `/step/5` | Send & Social | Email send + social sync logs |
| `/data/stories` | Stories | Newsletter Stories table |
| `/data/sources` | Sources | Source credibility scores |
| `/data/issues` | Issues | Newsletter Issues archive |
| `/analytics` | Mautic | Email performance metrics |

---

## Environment Variables

### Required for Workers

```bash
# Airtable
AIRTABLE_API_KEY=pat...
AIRTABLE_BASE_ID=appwSozYTkrsQWUXB          # Pivot Media Master
AIRTABLE_ARTICLES_TABLE=tblGumae8KDpsrWvh   # Articles (Step 0 output)

# AI Editor 2.0 Base
AI_EDITOR_BASE_ID=appglKSJZxmA9iHpl
AI_EDITOR_PREFILTER_LOG_TABLE=tbl72YMsm9iRHj3sp

# AI APIs
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...

# Infrastructure
REDIS_URL=redis://...
DATABASE_URL=postgresql://...
```

---

## Deployment

**Platform:** Render (NOT Vercel)

**Services:**
- `ai-editor-dashboard` - Next.js frontend
- `ai-editor-worker` - Python RQ worker
- `ai-editor-scheduler` - Python RQ scheduler
- `ai-editor-trigger` - Flask HTTP trigger
- `ai-editor-db` - PostgreSQL
- `ai-editor-redis` - Redis

**Deployment Configuration:** `workers/render.yaml`

---

## n8n Workflow Reference

These are the original n8n workflows being replaced:

| Step | n8n Workflow ID | Name |
|------|-----------------|------|
| 0 | `ddobfIOQeOykMUq6` | Ingestion Engine |
| 0.5 | `mgIuocpwH9kXvPjM` | AI Decoration (scoring) |
| 1 | `VoSZu0MIJAw1IuLL` | Pre-Filter |
| 2 | `SZmPztKNEmisG3Zf` | Slot Selection |
| 3 | `HCbd2g852rkQgSqr` | Decoration |
| 4 | `NKjC8hb0EDHIXx3U` | HTML Compile & Send |
| 5 | `I8U8LgJVDsO8PeBJ` | Social Syndication |

---

## Key Differences from n8n Implementation

| Aspect | n8n Workflow | Python Worker |
|--------|--------------|---------------|
| Ingestion | Firecrawl + RSS | **RSS-only** (faster, cheaper) |
| Markdown | Full article scraping | No markdown (minimal data) |
| Scheduling | n8n cron triggers | RQ Scheduler cron |
| Prompts | Hardcoded in workflow | **Stored in PostgreSQL, editable from UI** |
| Monitoring | n8n execution logs | Custom dashboard with detailed logs |

---

## Testing Notes

**Step 0 (Ingest):**
- First test run ingested 431 articles to the **WRONG** table (Newsletter Issue Stories)
- Fixed on December 26, 2025 (commit `388c19b`)
- Now correctly writes to Articles table
- **Pending testing by Pat to confirm fix is working**

---

*Last updated: December 26, 2025*
