# Google News URL Resolution Fix

**Date:** December 27, 2025
**File Modified:** `workers/jobs/ingest.py`
**Status:** ✅ CONFIRMED WORKING (12/27/2025)

---

## Problem

Google News RSS feed URLs were not being resolved to their actual source URLs. The logs showed:

```
[Ingest] Resolved Google News URL: https://news.google.com/rss/articles/CBMi... -> https://news.google.com/rss/articles/CBMi... (source: Google)
```

The input and output URLs were **identical** - no actual resolution was happening.

---

## Root Cause Analysis

### Why Base64 Decoding Failed (v1 Fix - BROKEN)

The original approach attempted pure Base64 decoding of the URL:

```python
# BROKEN - This does NOT work
encoded = match.group(1)  # Extract CBMi... part
decoded_bytes = base64.urlsafe_b64decode(encoded)
decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
# Try to find URL in decoded string
```

**This approach fails because:**

1. The decoded bytes are a **protobuf structure**, not a URL
2. Decoded output looks like: `b'\x08\x13"\xa9\x01AU_yqLOQwBV5ieTt2VH-oDEO_Jqah...'`
3. The inner string (`AU_yqL...`) is an **encrypted token**, NOT the actual URL
4. This token can only be resolved by calling Google's API

### How Google News URLs Actually Work

1. **URL format:** `https://news.google.com/rss/articles/CBMi...`
2. The `CBMi...` portion is Base64-encoded protobuf
3. For modern URLs (starting with `AU_yqL` in the protobuf), you MUST:
   - Fetch the Google News page to get `signature` and `timestamp` parameters
   - POST to `https://news.google.com/_/DotsSplashUi/data/batchexecute`
   - Parse the response to extract the actual URL

**Pure Base64 decoding DOES NOT WORK for modern Google News URLs.**

---

## Solution (v2 Fix - Pending Confirmation)

### Using `googlenewsdecoder` Package

The `googlenewsdecoder` package handles all the complexity of:
1. Fetching the Google News page
2. Extracting signature and timestamp
3. Calling the batchexecute API
4. Parsing the response

### Dependencies Added

```txt
# workers/requirements.txt
googlenewsdecoder==0.1.7
beautifulsoup4==4.12.3
lxml==5.3.0
```

### Updated Code

```python
from googlenewsdecoder import gnewsdecoder
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Thread pool for blocking gnewsdecoder calls (it makes HTTP requests)
_google_news_executor = ThreadPoolExecutor(max_workers=10)

async def resolve_google_news_url(
    session: aiohttp.ClientSession,
    url: str
) -> tuple[str, Optional[str]]:
    """
    Resolve a Google News URL to the actual article URL.
    Uses googlenewsdecoder package which calls Google's batchexecute API.
    """
    if not url or "news.google.com" not in url:
        return url, None

    try:
        # Run blocking gnewsdecoder in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _google_news_executor,
            lambda: gnewsdecoder(url, interval=0.3)
        )

        if result.get("status") and result.get("decoded_url"):
            decoded_url = result["decoded_url"]
            source_name = extract_source_from_url(decoded_url)
            print(f"[Ingest] Decoded Google News URL: {url[:50]}... -> {decoded_url[:60]}... (source: {source_name})")
            return decoded_url, source_name
        else:
            print(f"[Ingest] Could not decode Google News URL: {url[:60]}...")
            return url, "Google News"

    except Exception as e:
        print(f"[Ingest] Error decoding Google News URL: {e}")
        return url, "Google News"
```

---

## Expected Behavior After Fix

**Before (BROKEN):**
```
[Ingest] Resolved Google News URL: https://news.google.com/rss/articles/CBMi... -> https://news.google.com/rss/articles/CBMi... (source: Google)
```

**After (EXPECTED - pending confirmation):**
```
[Ingest] Decoded Google News URL: https://news.google.com/rss/articles/CBMi... -> https://www.techcrunch.com/2025/12/27/article... (source: TechCrunch)
```

---

## n8n Workflow Comparison

The n8n Ingestion Engine workflow uses a similar HTTP redirect approach which has the **same limitation**. The Python implementation now uses `googlenewsdecoder` which correctly handles the encoded URL format by calling Google's API.

---

## Testing

To verify the fix is working:

1. Trigger Step 0 Ingest
2. Check the logs for messages like:
   ```
   [Ingest] Decoded Google News URL: ... -> https://actualsite.com/... (source: ActualSite)
   ```
3. Verify articles in Airtable have proper `core_url` values pointing to actual news sites, not `news.google.com`

---

## Related Files

- `workers/jobs/ingest.py` - Main ingest job with URL resolution
- `workers/requirements.txt` - Dependencies (aiohttp, googlenewsdecoder)

---

## Version History

| Date | Version | Status | Notes |
|------|---------|--------|-------|
| 12/27/2025 | v1 | BROKEN | Base64 decode approach - doesn't work for modern URLs |
| 12/27/2025 | v2 | ✅ CONFIRMED | googlenewsdecoder package - verified working |
| 12/27/2025 | v3 | ✅ CONFIRMED | AI Scoring job confirmed working via Airtable API |
| 01/01/2026 | v4 | ✅ CONFIRMED | Rate limiting fix - 2s intervals, sequential processing |

---

## CRITICAL: Duplicate Records Issue (12/27/2025)

### Problem Discovered
Both Python AI Scoring AND n8n AI Scoring workflows are running simultaneously, creating duplicate Newsletter Story records.

### Evidence
For pivotId `p_cvgpzy`, THREE records exist:
1. **19:30 UTC** - Old Python run (missing fields, broken tags format)
2. **19:56 UTC** - Current Python run (✅ correct format)
3. **20:02 UTC** - n8n workflow (has `ai_headline`, `date_ai_processed`)

### How to Identify Source
- **Python-created records**: `id` = `pivotId`, NO `ai_headline`, NO `date_ai_processed`
- **n8n-created records**: `id` = Airtable record ID (rec...), HAS `ai_headline`, HAS `date_ai_processed`

### Resolution Applied (12/27/2025)
**Removed Newsletter Story creation from Python AI Scoring.**

Python AI Scoring now ONLY:
- Scores articles (interest_score, sentiment, topic, tags, fit_score, newsletter)
- Updates the Articles table
- Does NOT create Newsletter Stories

n8n "Pivot Media AI Decoration" workflow handles:
- Creating Newsletter Stories with full decoration (ai_headline, ai_dek, bullets, image_prompt)
- This prevents duplicates since only ONE system creates records

---

## Python AI Scoring: CONFIRMED WORKING (12/27/2025)

### Verified via Airtable API
```bash
# Articles scored today (needs_ai=false with interest_score)
curl "https://api.airtable.com/v0/appwSozYTkrsQWUXB/tblGumae8KDpsrWvh?filterByFormula=..."

# Newsletter Stories created today
curl "https://api.airtable.com/v0/appwSozYTkrsQWUXB/tblY78ziWp5yhiGXp?filterByFormula=..."
```

### Fields Written by Python AI Scoring

**To Articles table:**
- `interest_score`, `sentiment`, `topic`, `tags` (comma-separated)
- `newsletter`, `fit_score`, `date_scored`
- `needs_ai` → false

**To Newsletter Stories table (interest_score >= 15):**
- `id`, `storyID`, `pivotId`
- `core_url`, `date_og_published`
- `interest_score`, `sentiment`, `topic`, `tags`, `fit_score`, `newsletter`
- `image_status` → "pending"

---

## Related Fix: AI Scoring Bug (12/27/2025)

After the Google News fix was confirmed working, a separate issue was discovered with AI Scoring:

**Problem:** AI Scoring job failed to update articles (422 errors)
- Non-existent Airtable fields being written

**Fixes Applied (all verified against n8n workflow Airtable schema):**

| Fix | Wrong Field | Correct Field/Action |
|-----|-------------|---------------------|
| 1 | `primary_newsletter_slug` | Removed (doesn't exist) |
| 2 | `fit_score_*` | Removed (doesn't exist) |
| 3 | `date_ai_scored` | → `date_scored` |
| 4 | `headline` in ingest.py | Removed (doesn't exist in Articles) |
| 5 | `source_id` in Newsletter Stories | Removed (doesn't exist) |
| 6 | `interest_score` in Newsletter Stories | Removed (doesn't exist) |

**Verified Airtable Schemas:**

Articles table (`tblGumae8KDpsrWvh`):
- `pivot_Id`, `original_url`, `source_id`, `date_published`, `date_ingested`
- `needs_ai`, `interest_score`, `sentiment`, `topic`, `tags`, `date_scored`

Newsletter Stories table (`tblY78ziWp5yhiGXp`):
- `pivotId`, `core_url`, `date_og_published`
- `sentiment`, `topic`, `tags`, `fit_score`, `newsletter`

See `workers/jobs/ai_scoring.py` for details.

---

## Rate Limiting Fix (01/01/2026)

### Problem
Google was returning 429 (Too Many Requests) errors when processing Google News URLs in rapid succession. The original 1-second interval was too aggressive.

### Root Cause
- `googlenewsdecoder` calls Google's `batchexecute` API for each URL
- Google rate limits this API aggressively
- Render.com services share outbound IP ranges, increasing rate limit likelihood
- Previous 1-second interval triggered rate limiting after ~10-20 requests

### Solution Applied

**File:** `workers/jobs/ingest_sandbox.py`

```python
async def resolve_google_news_url(url: str, retry_count: int = 0) -> tuple[str, Optional[str]]:
    """
    RATE LIMITING: Uses conservative timing to avoid Google 429 errors:
      - 2.0s interval in gnewsdecoder
      - Up to 3 retries with exponential backoff (10s, 20s, 40s)
    """
    max_retries = 3

    result = await loop.run_in_executor(
        _google_news_executor,
        lambda: gnewsdecoder(url, interval=2.0)  # 2s delay - conservative
    )

    # On rate limit, retry with exponential backoff
    if "status" not in result or not result["status"]:
        if retry_count < max_retries:
            backoff = 10 * (2 ** retry_count)  # 10s, 20s, 40s
            await asyncio.sleep(backoff)
            return await resolve_google_news_url(url, retry_count + 1)
```

**Batch Processing Changes:**
```python
# CONSERVATIVE rate limiting
batch_size = 5  # Reduced from 10

# Process URLs SEQUENTIALLY within batch (not parallel)
for idx, article in batch:
    resolved_url, source_name = await resolve_google_news_url(url)
    await asyncio.sleep(2)  # 2 second delay between individual URLs

# 5 second delay between batches
await asyncio.sleep(5)
```

### Test Results (01/01/2026)

```
[Ingest Sandbox] Resolving 10 Google News URLs using googlenewsdecoder...
[Ingest Sandbox] Using conservative rate limiting (2s interval, 3s between URLs)
[Ingest Sandbox] Decoded: news.google.com -> businessinsider.com (Business Insider)
[Ingest Sandbox] Decoded: news.google.com -> forbes.com (Forbes)
[Ingest Sandbox] Decoded: news.google.com -> samsung.com (Samsung)
... (7 more)
[Ingest Sandbox] Google News URL resolution complete:
  - Resolved: 10
  - Failed/Unresolved: 0
```

**Result: 10/10 URLs resolved successfully with no rate limiting errors.**

### Additional Changes (01/01/2026)

1. **Decoupled AI Scoring from Ingestion**
   - Removed auto-chaining of `run_ai_scoring_sandbox()` after ingest
   - AI scoring now triggered manually via dashboard

2. **Removed AI Scoring Batch Limits**
   - Changed `batch_size` default from `50` to `None`
   - AI scoring now processes ALL records with `needs_ai=true`

---

## References

- [googlenewsdecoder on PyPI](https://pypi.org/project/googlenewsdecoder/)
- [GitHub: google-news-url-decoder](https://github.com/SSujitX/google-news-url-decoder)
- [Decode script gist](https://gist.github.com/huksley/bc3cb046157a99cd9d1517b32f91a99e)
