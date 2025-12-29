# AI Ingestion Engine Configuration

**Last Updated:** December 27, 2025
**Status:** Production Ready

---

## Overview

The AI Ingestion Engine is a two-step Python pipeline that replaces n8n workflows:

| Step | Job | Purpose |
|------|-----|---------|
| **Step 0a** | `ingest` | Fetch articles from RSS feeds → Articles table |
| **Step 0b** | `ai_scoring` | Score articles with Claude → Create Newsletter Stories |

---

## Architecture

```
Dashboard UI (Next.js)
    ↓ POST /api/jobs
Flask Trigger Service (port 5001)
    ↓ enqueue to Redis
RQ Worker (Python)
    ↓
Airtable (Articles + Newsletter Stories)
```

---

## Step 0a: Ingest (`workers/jobs/ingest.py`)

### What It Does
1. Fetches RSS feeds from configured sources
2. Resolves Google News URLs using `googlenewsdecoder` package
3. Deduplicates against existing `pivot_Id` values
4. Creates records in Articles table

### Configuration
- **Batch size:** Unlimited (processes all new articles)
- **Deduplication:** By `pivot_Id` (hash of URL)
- **Google News:** Resolved via `googlenewsdecoder` API calls

### Fields Written to Articles Table

| Field | Value |
|-------|-------|
| `pivot_Id` | Unique hash of article URL |
| `original_url` | Resolved source URL (not Google News URL) |
| `source_id` | Publication name extracted from URL |
| `date_ingested` | UTC timestamp |
| `date_published` | From RSS feed (if available) |
| `needs_ai` | `true` |
| `decoration_status` | `"pending"` |

---

## Step 0b: AI Scoring (`workers/jobs/ai_scoring.py`)

### What It Does
1. Queries Articles with `needs_ai = true`
2. Scores each article with Claude Sonnet 4
3. Updates Articles table with scores
4. For high-interest articles (score >= 15): generates decoration and creates Newsletter Story
5. Auto-requeues if more articles remain

### Configuration

| Setting | Value |
|---------|-------|
| **Batch size** | 150 articles per run |
| **Model** | `claude-sonnet-4-5-20250929` |
| **Scoring temperature** | 0.3 |
| **Decoration temperature** | 0.5 |
| **Interest threshold** | 15 (for Newsletter Story creation) |
| **Auto-requeue** | Yes (continues until all processed) |

### Scoring Output (Claude)

| Field | Type | Description |
|-------|------|-------------|
| `interest_score` | 0-25 | Article importance/interest level |
| `sentiment` | -10 to 10 | Tone (-10 negative, +10 positive) |
| `topic` | enum | One of 18 categories (WORK, FINANCE, etc.) |
| `tags` | string | 5 comma-separated descriptive tags |
| `newsletter` | string | Best fit: pivot_ai, pivot_build, pivot_invest |
| `fit_score` | 0-25 | Best newsletter fit score |

### Decoration Output (for interest_score >= 15)

| Field | Description |
|-------|-------------|
| `ai_headline` | Rewritten compelling headline (8-15 words) |
| `ai_dek` | 1-2 sentence summary (25-40 words) |
| `ai_bullet_1` | Key insight with **bold** phrase |
| `ai_bullet_2` | Key insight with **bold** phrase |
| `ai_bullet_3` | Key insight with **bold** phrase |
| `image_prompt` | Prompt for image generation |

### Fields Written to Articles Table

| Field | Value |
|-------|-------|
| `needs_ai` | `false` |
| `interest_score` | 0-25 |
| `sentiment` | -10 to 10 |
| `topic` | Category string |
| `tags` | Comma-separated tags |
| `newsletter` | Best fit newsletter |
| `fit_score` | 0-25 |
| `date_scored` | UTC timestamp |
| `decoration_status` | `"completed"` or `"skipped_low_score"` |

### Fields Written to Newsletter Stories Table (interest_score >= 15)

| Field | Value |
|-------|-------|
| `id` | Airtable record ID from Articles |
| `pivotId` | Same as Articles.pivot_Id |
| `storyID` | Link to Articles record |
| `core_url` | Article URL |
| `date_og_published` | Original publish date |
| `interest_score` | Score from Claude |
| `sentiment` | Sentiment score |
| `topic` | Category |
| `tags` | Comma-separated tags |
| `fit_score` | Newsletter fit score |
| `newsletter` | Best fit newsletter |
| `ai_headline` | Generated headline |
| `ai_dek` | Generated summary |
| `ai_bullet_1/2/3` | Generated bullets |
| `image_prompt` | For image generation |
| `ai_complete` | `true` |
| `image_status` | `"pending"` |
| `date_ai_processed` | UTC timestamp |

---

## Dashboard UI

### Step 0 Page (`/step/0`)

Two manual trigger buttons:

| Button | Action |
|--------|--------|
| **Ingest Articles** | Triggers `ingest` job |
| **Run AI Scoring** | Triggers `ai_scoring` job |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/jobs` | POST | Trigger a job (`step: "ingest"` or `step: "ai_scoring"`) |
| `/api/jobs` | GET | Get queue status |

---

## Airtable Tables

### Articles Table
- **Base:** Pivot Media Master (`appwSozYTkrsQWUXB`)
- **Table ID:** `tblGumae8KDpsrWvh`

### Newsletter Stories Table
- **Base:** Pivot Media Master (`appwSozYTkrsQWUXB`)
- **Table ID:** `tblY78ziWp5yhiGXp`

---

## Deployment

- **Platform:** Render
- **Auto-deploy:** On push to `main` branch
- **Services:**
  - `ai-editor-dashboard` - Next.js frontend
  - `ai-editor-worker` - Python RQ worker
  - `ai-editor-trigger` - Flask trigger service

---

## Dependencies

### Python (`workers/requirements.txt`)
```
pyairtable>=2.0.0
anthropic>=0.18.0
rq>=1.15.0
redis>=4.5.0
aiohttp>=3.9.0
googlenewsdecoder>=0.1.7
beautifulsoup4>=4.12.3
lxml>=5.3.0
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `AIRTABLE_API_KEY` | Airtable authentication |
| `AIRTABLE_BASE_ID` | Pivot Media Master base |
| `ANTHROPIC_API_KEY` | Claude API authentication |
| `REDIS_URL` | Redis connection for RQ |
| `TRIGGER_SERVICE_URL` | Flask trigger service URL |

---

## Changelog

| Date | Change |
|------|--------|
| 12/27/2025 | Added `decoration_status` field (pending/completed/skipped_low_score) |
| 12/27/2025 | Increased batch_size from 50 to 150 |
| 12/27/2025 | Added auto-requeue when more articles remain |
| 12/27/2025 | Added two manual trigger buttons for Step 0 |
| 12/27/2025 | Fixed Google News URL resolution with `googlenewsdecoder` |
| 12/27/2025 | Confirmed AI Scoring creates decorated Newsletter Stories |
