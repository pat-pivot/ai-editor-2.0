# Old Article Fix

**Date:** January 2, 2026
**File Modified:** `workers/config/freshrss_client.py`
**Status:** DEPLOYED

---

## Problem

Old articles (2-3+ years old) were being ingested into the `Articles - All Ingested` table in Airtable.

The `date_og_published` field showed articles from 2022-2023 being ingested on January 2, 2026.

---

## Root Cause

The FreshRSS client was NOT filtering by publication date. It only filtered by `crawl_dt` (when FreshRSS discovered the article), NOT by `published_dt` (when the article was actually published).

This allowed articles that were:
- Published 3 years ago
- But crawled by FreshRSS today

To slip through into Airtable.

---

## Key Discovery: Google Reader API Limitations

**CRITICAL FINDING (Confirmed via Perplexity + FreshRSS GitHub issues):**

| Parameter | What It Actually Does | Use Case |
|-----------|----------------------|----------|
| `ot` | Filters by **CRAWL date** (when FreshRSS discovered it) | Reduces data transfer |
| `q=pubdate:` | **Web UI search only** - does NOT work in API | N/A for API |
| Publication date filter | **NOT AVAILABLE in API** | Must use Python |

**Source:** [FreshRSS GitHub Issue #2566](https://github.com/FreshRSS/FreshRSS/issues/2566)

> "The `ot` parameter filters by article discovery date (when added to the database), not publication date."

**This means:** There is NO way to filter by publication date at the API level. Python filtering is REQUIRED.

---

## History of Attempted Fixes

| Attempt | Filter | Problem |
|---------|--------|---------|
| v1 | Only `crawl_dt` (Python) | Old articles (years old) slip through |
| v2 | `q=pubdate:` at API level | **WRONG** - This syntax is for web UI, not API |
| v3 | `ot` parameter thinking it filters by pub date | **WRONG** - `ot` filters by CRAWL date |
| **v4** | **API `ot` for crawl + Python for publication** | **CORRECT - see below** |

---

## The Fix: Hybrid Filtering

**File:** `workers/config/freshrss_client.py`
**Location:** `get_articles()` method

### Layer 1: API-Level Filter (Crawl Date)

The `ot` parameter reduces data transfer by only fetching recently crawled articles:

```python
# Only fetch articles CRAWLED in last 7 days
crawl_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
crawl_timestamp = int(crawl_cutoff.timestamp())

data = self._make_request(
    endpoint,
    params={
        "n": limit,
        "output": "json",
        "ot": crawl_timestamp  # Filters by CRAWL date, NOT publication date
    }
)
```

### Layer 2: Python Filter (Publication Date) - THE REAL FILTER

This is the only way to filter by publication date:

```python
# Filter by PUBLICATION date (the only way to do this)
cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)  # 36 hours

if article.get("published_dt"):
    if article["published_dt"] < cutoff:
        skipped_count += 1
        continue
```

### Why Both Layers?

| Layer | Parameter | Filters By | Purpose |
|-------|-----------|------------|---------|
| API | `ot` | **Crawl date** | Reduces bandwidth - don't fetch old crawl batches |
| Python | `published_dt` | **Publication date** | The REAL filter - blocks old news |

**The Python filter is doing the actual work.** The API filter just reduces how much data we fetch.

---

## Why November 19th Articles Appear (And Get Filtered)

When you see logs like:
```
[FreshRSS] Skipping old article (pub 2025-11-19 07:00, cutoff 2026-01-01 05:41): Article Title...
```

This is **expected and correct**:
1. Article was PUBLISHED on Nov 19, 2025
2. FreshRSS CRAWLED it recently (within 7 days)
3. API returned it (because `ot` filters by crawl date)
4. Python filter correctly blocked it (because publication date is old)

**This is not a bug - this is the only way it can work.**

---

## Expected Behavior

| Article Published | Crawled Recently? | Result |
|-------------------|-------------------|--------|
| 3 years ago | Yes | **REJECTED** (by Python) |
| 2 months ago | Yes | **REJECTED** (by Python) |
| 5 days ago | Yes | **REJECTED** (by Python) |
| 30 hours ago | Yes | ACCEPTED |
| 12 hours ago | Yes | ACCEPTED |

---

## Log Output

Summary log after fetching:
```
[FreshRSS] Fetching articles crawled since 2025-12-26 (Python filters by pub date: 2026-01-01 05:41)
[FreshRSS] Fetched 45 articles, skipped 120 old articles
```

If you see `skipped 0 old articles`, either:
- All crawled articles happened to be recently published (rare)
- Or something is wrong with the Python filter

---

## Deduplication

**Q: If I run ingest twice in 24 hours, will there be duplicates?**

**A: No.** Each article gets a `pivot_id` generated from its URL. Before creating a record, the ingest job checks if that `pivot_id` exists in Airtable. Duplicates are prevented.

---

## Trade-off

With a strict 36-hour `published_dt` filter, you may miss articles that:
- Google News surfaces 2-5 days after publication
- Were published on weekends and crawled on Monday

If this becomes an issue, increase the `since_hours` parameter in the ingest job.

---

## Testing

1. Run ingest from the dashboard
2. Check Render logs for `Fetched X articles, skipped Y old articles`
3. Verify `Articles - All Ingested` table only contains recent articles
4. Check `date_og_published` field - all dates should be within last 36 hours

---

## Related Files

- `workers/config/freshrss_client.py` - FreshRSS API client (contains the fix)
- `workers/jobs/ingest_sandbox.py` - Ingest job that calls FreshRSS client

---

## References

- [FreshRSS GitHub Issue #2566](https://github.com/FreshRSS/FreshRSS/issues/2566) - Confirms `ot` is crawl date
- [FreshRSS Filter Docs](https://freshrss.github.io/FreshRSS/en/users/10_filter.html) - `pubdate:` is for web UI only
- [Re-Implementing Google Reader API](https://www.davd.io/posts/2025-02-05-reimplementing-google-reader-api-in-2025/) - API spec details
