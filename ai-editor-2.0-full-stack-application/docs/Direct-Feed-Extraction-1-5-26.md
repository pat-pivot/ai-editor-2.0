# Direct Feed Extraction - Separate Ingestion Process

**Date:** January 5, 2026
**Status:** Implemented
**Problem:** Direct RSS feed articles were not being ingested

---

## Problem Summary

Investigation of the 6PM ingest run revealed:
- **ALL** Render logs showed `[GNEWS DECODE]` entries
- **ZERO** direct feed articles were being ingested
- Expected ~112 direct feed URLs from FreshRSS, but only 19 made it to Airtable
- The `ingest_sandbox.py` job was ONLY processing Google News URLs

### Root Cause

Google News URL decoding is slow (5+ seconds per URL due to rate limiting), which blocked/skipped direct RSS feeds (Reuters, TechCrunch, etc.) that don't need decoding.

---

## Solution: Separate Extraction Process

Since the system cannot efficiently process both at once, we created a **completely separate** job for direct feeds.

### How It Works

| Job | What It Does | Identifies Records By |
|-----|--------------|----------------------|
| `ingest_sandbox` | Decodes Google News URLs | `gnews_url` field is PRESENT |
| `ingest_direct_feeds` | Ingests non-Google News URLs | `gnews_url` field is ABSENT |

---

## Files Created/Modified

### New File: `workers/jobs/ingest_direct_feeds.py`

New job function that:
1. Fetches articles from FreshRSS
2. **Filters OUT** any URLs containing `news.google.com`
3. Only processes direct feed URLs
4. Creates Airtable records **without** `gnews_url` field

```python
def ingest_direct_feeds(
    limit: int = 500,
    since_hours: int = 36,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Ingest ONLY direct feed articles (non-Google News).
    This runs SEPARATELY from Google News ingestion.
    """
```

### Modified: `workers/trigger.py`

Added endpoint for triggering direct feed ingestion:

```python
# In get_job_function():
elif step_name == 'ingest_direct_feeds':
    from jobs.ingest_direct_feeds import ingest_direct_feeds
    JOB_FUNCTIONS[step_name] = ingest_direct_feeds

# In QUEUE_MAPPING:
'ingest_direct_feeds': 'default',
```

### Modified: `src/components/step/zeroin-ingest-panel.tsx`

Added "Direct Feed Ingest" button to the dashboard:
- Uses teal color scheme (distinct from orange Google News jobs)
- Same state management pattern as other jobs
- Run/Cancel functionality
- Shows elapsed time and results

---

## Dashboard Usage

### Manual Trigger

1. Go to **Step 0: ZeroIn Ingest** panel
2. Click **Direct Feed Ingest** button (teal, 4th card)
3. Job runs in background (~30 seconds typical)
4. Results show count of ingested/skipped articles

### When to Use

- After Google News ingest completes
- To catch direct feeds that weren't processed
- For testing direct feed sources in isolation

---

## Cron Schedule (Configured)

Direct feed extraction runs **1 HOUR AFTER the full pipeline COMPLETES**. This ensures Google News decoding, AI Scoring, and Pre-Filter have all finished before direct feeds are ingested.

### Pipeline Timing

| Step | Duration | Notes |
|------|----------|-------|
| Ingest (Google News) | ~1.5 hours | Slow due to URL decoding rate limits |
| AI Scoring | ~45 min | Scores all pending articles |
| Pre-Filter (5 slots) | ~1.25 hours | Sequential slot processing |
| **TOTAL** | **~3.5 hours** | Pipeline completion time |

### Cron Schedule

| Cycle | Pipeline Start | Pipeline Ends | Direct Feed Start |
|-------|----------------|---------------|-------------------|
| Night | 2:00 AM ET | ~5:30 AM ET | **6:30 AM ET** (11:30 UTC) |
| Morning | 9:30 AM ET | ~1:00 PM ET | **2:00 PM ET** (19:00 UTC) |
| EOD | 5:00 PM ET | ~8:30 PM ET | **9:30 PM ET** (2:30 UTC) |

```
EACH CYCLE:
═══════════════════════════════════════════════════════
0:00      Pipeline starts (Ingest → AI Scoring → Pre-Filter)
+3:30     Pipeline COMPLETES
+4:30     DIRECT FEED INGEST (1 hour buffer after completion)
```

---

## Source Breakdown

The job logs which sources it processes:

```
[DIRECT FEED INGEST] Sources found:
  Reuters: 45
  TechCrunch: 23
  The Verge: 15
  CNBC: 12
  ...
```

### Supported Sources

Direct feeds are identified by domain mapping in `DOMAIN_TO_SOURCE`:
- Reuters, CNBC, The Verge, TechCrunch
- Yahoo Finance (blocked - stock speculation)
- WSJ, Bloomberg, Financial Times
- Wired, Ars Technica, VentureBeat
- And 30+ more sources

### Blocked Domains

```python
BLOCKED_DOMAINS = [
    "yahoo.com",
    "finance.yahoo.com",
    "barrons.com",
]
```

---

## Airtable Record Differences

### Google News Article
```json
{
  "pivot_id": "abc123",
  "original_url": "https://reuters.com/article/...",
  "gnews_url": "https://news.google.com/rss/...",  // PRESENT
  "source_name": "Reuters",
  "headline": "...",
  "needs_ai": true
}
```

### Direct Feed Article
```json
{
  "pivot_id": "xyz789",
  "original_url": "https://techcrunch.com/2026/01/...",
  // NO gnews_url field - this is a direct feed
  "source_name": "TechCrunch",
  "headline": "...",
  "needs_ai": true
}
```

---

## Results Format

```python
{
    "started_at": "2026-01-05T18:00:00-05:00",
    "source": "FreshRSS-DirectFeeds",
    "articles_fetched": 200,           # Total from FreshRSS
    "direct_feeds_found": 112,         # Non-Google News URLs
    "google_news_skipped": 88,         # Filtered out
    "articles_ingested": 95,           # Created in Airtable
    "articles_skipped_duplicate": 15,  # Already existed
    "articles_skipped_invalid": 2,     # Missing URL/title
    "articles_skipped_blocked": 0,     # From blocked domains
    "ingested_sources": {              # Breakdown by source
        "Reuters": 23,
        "TechCrunch": 18,
        ...
    },
    "completed_at": "2026-01-05T18:00:30-05:00"
}
```

---

## Troubleshooting

### No direct feeds found
- Check FreshRSS has non-Google News subscriptions
- Verify `since_hours` parameter covers recent articles

### High duplicate count
- Normal if running frequently
- Duplicates are identified by `pivot_id` hash

### Missing expected source
- Add to `DOMAIN_TO_SOURCE` mapping
- Check if domain is in `BLOCKED_DOMAINS`

---

## Key Insight

The critical insight is that **Google News decoding and direct feed ingestion are fundamentally different operations**:

| Aspect | Google News | Direct Feeds |
|--------|-------------|--------------|
| URL Type | `news.google.com/rss/...` | Direct publisher URLs |
| Processing | Decode to find original URL | Use URL directly |
| Speed | ~5s per URL (rate limited) | Instant |
| Can Run Together | No - blocks other processing | Yes - fast |

By separating them, both run efficiently without blocking each other.
