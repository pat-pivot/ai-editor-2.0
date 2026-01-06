# AI Editor 2.0

## What This Is

A full-stack application that **replaces n8n workflows** for the Pivot 5 AI newsletter pipeline. Python workers with Redis Queue handle the automated pipeline; prompts are stored in PostgreSQL and editable via a Next.js dashboard.

**When prompts are edited in the dashboard, they affect the live production pipeline.**

## Current Status (January 1, 2026)

| Step | Name | Status |
|------|------|--------|
| 0 | Sandbox/Ingest | Created (will replace Zero Ingest tab) |
| 1 | Pre-Filter | **DONE** |
| 2 | Slot Selection | **DONE** |
| 3 | Decoration | IN PROGRESS |
| 4 | HTML Compile | Not started |
| 5 | Social Sync | Not started |

---

## Claude Skills

Detailed documentation lives in `.claude/skills/`. **Read the relevant skill before working on any area.**

Skills are automatically available to Claude. To reference them:
- Read the skill file directly: `.claude/skills/step-1-prefilter.md`
- Skills contain exact Airtable field names, API schemas, and implementation details

### Available Skills

| Skill | What It Covers |
|-------|----------------|
| `pipeline-overview.md` | Full 5-step pipeline flow diagram |
| `step-0-ingest.md` | FreshRSS → Newsletter Selects |
| `step-1-prefilter.md` | Gemini pre-filtering (DONE) |
| `step-2-slot-selection.md` | Claude agent selection (DONE) |
| `step-3-decoration.md` | Headlines, bullets, images (IN PROGRESS) |
| `step-4-compile-send.md` | HTML compile & Mautic (NOT STARTED) |
| `step-5-social-sync.md` | Social media posts (NOT STARTED) |
| `airtable-api.md` | Queries, filtering, **exact field names** |
| `render-deployment.md` | Render MCP tools, logs, metrics |
| `system-prompts.md` | Prompt versioning & management |
| `freshrss.md` | FreshRSS Google Reader API |

---

## Tech Stack

- **Frontend:** Next.js 14 (App Router) + React + Tailwind
- **Backend:** Python workers with Redis Queue (RQ)
- **Database:** PostgreSQL (prompts, jobs) + Airtable (articles)
- **Deployment:** Render (NOT Vercel)
- **AI Models:** Gemini 3 Flash, Claude Sonnet 4.5

## Directory Structure

```
app/
├── src/                    # Next.js frontend
│   ├── app/                # Pages: dashboard, sandbox, step/[id]
│   │   └── api/            # API routes: prompts, jobs, health
│   ├── components/         # React components
│   └── lib/                # Utilities (db.ts, airtable.ts)
├── workers/                # Python background workers
│   ├── jobs/               # Step handlers (prefilter.py, slot_selection.py, etc.)
│   ├── utils/              # Shared utilities (airtable.py, claude.py, gemini.py)
│   └── config/             # FreshRSS client, RSS feeds
├── db/                     # PostgreSQL schema (init.sql)
└── .claude/skills/         # Documentation for Claude
```

## Key Commands

```bash
# Development
npm run dev              # Start Next.js frontend
python workers/worker.py # Run Python worker

# Git (run from /app/ directory!)
git status && git add . && git commit -m "message" && git push
```

---

## Model Requirements

### Gemini (for Pre-Filter, Image Generation)
| Use | Model |
|-----|-------|
| Pre-Filter | `gemini-3-flash-preview` |
| Image Gen | `gemini-3` |

### Claude (for Slot Selection, Decoration)
| Use | Model |
|-----|-------|
| AI Scoring | `claude-haiku-4-5-20251001` |
| Standard | `claude-sonnet-4-5-20250929` |

**Never use** deprecated models: `gemini-2.0-*`, `claude-3-*`, `claude-sonnet-4-*`

---

## Git Repository

**This `app/` folder is its own git repo** (separate from parent).

```
pivot-5-website_11.19.25/
└── ai-editor-2.0-full-stack-application/
    └── app/           ← Git repo root (.git/ is here)
```

Remote: `https://github.com/pat-pivot/ai-editor-2.0.git`

---

## Database Schema

PostgreSQL stores prompts and job tracking:

```sql
system_prompts          -- Prompt configuration (key, step_id, model, temperature)
system_prompt_versions  -- Version history with rollback
jobs                    -- Worker job tracking (status, payload, result)
audit_log               -- Action logging
```

Stored procedures: `update_prompt_content()`, `rollback_prompt()`

---

## Airtable Quick Reference

```
Pivot Media Master: appwSozYTkrsQWUXB
AI Editor 2.0:      appglKSJZxmA9iHpl
P5 Social Posts:    appRUgK44hQnXH1PM
```

**Each step skill documents the exact field names for Airtable writes.** Common gotchas:
- `storyID` / `pivotId` (camelCase)
- `core_url` vs `original_url` (varies by table)
- `Order` with capital O (P5 Social Posts)
