# FreshRSS → Airtable Ingestion Cross-Reference SOP

**Created:** January 1, 2026
**Purpose:** Standard Operating Procedure for verifying FreshRSS feeds are properly ingested into Airtable
**Status:** Initial verification complete - further testing recommended

---

## Table of Contents

1. [Overview](#overview)
2. [Configured FreshRSS Feeds](#configured-freshrss-feeds)
3. [API Configuration](#api-configuration)
4. [Verification Methodology](#verification-methodology)
5. [Cross-Reference Checklist (SOP)](#cross-reference-checklist-sop)
6. [Jan 1, 2026 Test Results](#jan-1-2026-test-results)
7. [Known Issues](#known-issues)
8. [Next Steps](#next-steps)

---

## Overview

The AI Editor ingestion pipeline pulls articles from FreshRSS and writes them to Airtable's "Articles All Ingested" table. This document provides a standard procedure for verifying all publications are being captured correctly.

### Pipeline Flow

```
FreshRSS (18 feeds)
    ↓
ingest_sandbox.py (workers/jobs/)
    ↓
Airtable "Articles All Ingested" (AI Editor 2.0 base)
```

### Key Files

| File | Purpose |
|------|---------|
| `workers/config/freshrss_client.py` | FreshRSS API client, feed mappings |
| `workers/jobs/ingest_sandbox.py` | Ingestion job that writes to Airtable |
| `workers/repair_google_news.py` | Google News URL decoder |

---

## Configured FreshRSS Feeds

**Total: 18 Active Feeds** (as of Dec 30, 2025)

### Stream ID to Source Mapping

From `workers/config/freshrss_client.py` lines 51-72:

| Stream ID | Source Name | Feed Type |
|-----------|-------------|-----------|
| `feed/3` | Bloomberg | Direct RSS |
| `feed/8` | The Verge | Direct RSS |
| `feed/10` | CNBC | Direct RSS |
| `feed/11` | The Atlantic | Direct RSS |
| `feed/16` | Google News AI | Google News RSS |
| `feed/17` | AI Newsletters | Kill The Newsletter |
| `feed/23` | Reuters | Google News RSS |
| `feed/28` | VentureBeat | Direct RSS |
| `feed/30` | The Next Web | Direct RSS |
| `feed/31` | MIT Tech Review | Direct RSS |
| `feed/32` | MIT News | Direct RSS |
| `feed/33` | Science Daily | Direct RSS |
| `feed/35` | TechCrunch | AI-specific feed |
| `feed/36` | TechRepublic | AI-specific feed |
| `feed/37` | New York Times | Native RSS |
| `feed/38` | WSJ | Dow Jones direct |
| `feed/41` | Semafor | Google News (site:semafor.com) |
| `feed/42` | The Guardian | Google News (site:theguardian.com) |

### Newsletter Sources (via Kill The Newsletter - feed/17)

From `NEWSLETTER_DOMAIN_TO_SOURCE` mapping:

| Domain | Source Name |
|--------|-------------|
| theaivalley.com | AI Valley |
| theaireport.ai | The AI Report |
| joinsuperhuman.ai | Superhuman |
| theneurondaily.com | The Neuron |
| bensbites.co | Ben's Bites |
| readwrite.com | ReadWrite AI |
| aibreakfast.beehiiv.com | AI Breakfast |
| tldr.tech | TLDR AI |

---

## API Configuration

### Airtable

```
Base ID:     appglKSJZxmA9iHpl (AI Editor 2.0)
Table ID:    tblMfRgSNSyoRIhx1 (Articles All Ingested)
API Key:     Set in AIRTABLE_API_KEY environment variable
```

### FreshRSS

```
URL:         https://pivot-media-rss-feed.onrender.com
API:         https://pivot-media-rss-feed.onrender.com/api/greader.php
Auth Token:  admin/d13c712f15c87f1d9aee574372ed7dffe7e5e880
```

---

## Verification Methodology

### 1. Query Airtable for Ingested Records

**Python Example:**

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv('.env.local')

AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
AI_EDITOR_BASE_ID = 'appglKSJZxmA9iHpl'
ARTICLES_TABLE_ID = 'tblMfRgSNSyoRIhx1'

headers = {
    'Authorization': f'Bearer {AIRTABLE_API_KEY}',
    'Content-Type': 'application/json'
}

# Query by date (uses UTC - see timezone note below)
params = {
    'filterByFormula': "SEARCH('2026-01-01', {date_ingested}) > 0",
    'pageSize': 100
}

url = f'https://api.airtable.com/v0/{AI_EDITOR_BASE_ID}/{ARTICLES_TABLE_ID}'
response = requests.get(url, headers=headers, params=params)
data = response.json()

# Count by source
source_counts = {}
for record in data.get('records', []):
    source = record['fields'].get('source_name', 'Unknown')
    source_counts[source] = source_counts.get(source, 0) + 1

print(source_counts)
```

### 2. Query FreshRSS for Crawl Status

**Python Example:**

```python
import requests
from datetime import datetime, timezone, timedelta

FRESHRSS_URL = "https://pivot-media-rss-feed.onrender.com"
FRESHRSS_AUTH = "admin/d13c712f15c87f1d9aee574372ed7dffe7e5e880"

headers = {
    "Authorization": f"GoogleLogin auth={FRESHRSS_AUTH}",
    "User-Agent": "Pivot5-Verification/1.0"
}

# Get recent articles from all feeds
response = requests.get(
    f"{FRESHRSS_URL}/api/greader.php/reader/api/0/stream/contents",
    headers=headers,
    params={"n": 500, "output": "json"}
)

data = response.json()
cutoff = datetime.now(timezone.utc) - timedelta(hours=6)

# Count by feed (origin)
feed_counts = {}
for item in data.get('items', []):
    crawl_ms = item.get('crawlTimeMsec')
    if crawl_ms:
        crawl_dt = datetime.fromtimestamp(int(crawl_ms) / 1000, tz=timezone.utc)
        if crawl_dt >= cutoff:
            origin = item.get('origin', {})
            feed_title = origin.get('title', 'Unknown')
            feed_counts[feed_title] = feed_counts.get(feed_title, 0) + 1

print(feed_counts)
```

### 3. Timezone Handling (CRITICAL)

**Airtable stores timestamps in UTC but displays in EST in the UI.**

| UTC Timestamp | EST Display | Notes |
|--------------|-------------|-------|
| 2026-01-01T01:00:00Z | Dec 31, 2025 8:00 PM EST | **Previous day in EST!** |
| 2026-01-01T18:00:00Z | Jan 1, 2026 1:00 PM EST | Same day in EST |

**When filtering by date:**
- Airtable UI filter "January 1st" → Shows EST dates only
- API query `SEARCH('2026-01-01', {date_ingested})` → Matches UTC timestamps

**Solution:** Always note which timezone you're querying in. For accurate EST filtering:

```python
# Filter for EST "January 1st" using UTC range
params = {
    'filterByFormula': "AND({date_ingested} >= '2026-01-01T05:00:00.000Z', {date_ingested} < '2026-01-02T05:00:00.000Z')"
}
```

---

## Cross-Reference Checklist (SOP)

### Pre-Flight

- [ ] Confirm FreshRSS is accessible at https://pivot-media-rss-feed.onrender.com
- [ ] Confirm Airtable API key is valid (test with a simple query)
- [ ] Note the current date/time in both EST and UTC

### Step 1: Check FreshRSS Crawl Status

1. Query FreshRSS for articles crawled in last 6-12 hours
2. Count articles by feed/origin
3. Note any feeds with 0 articles (may indicate dormant feed or publishing pause)

### Step 2: Check Airtable Ingestion

1. Query Airtable for records ingested in the same time window
2. Count by `source_name` field
3. Note the actual record count (not just API estimate)

### Step 3: Cross-Reference

For each configured feed:
- [ ] Verify feed appears in FreshRSS with recent articles (or note publishing pause)
- [ ] Verify corresponding source appears in Airtable
- [ ] Check source name consistency (e.g., "The Guardian" vs "Theguardian")

### Step 4: Document Findings

Record:
- Date/time of verification
- Total articles in FreshRSS (time window)
- Total records in Airtable (time window)
- Any discrepancies or anomalies
- Any feeds with 0 articles and reason (dormant, holiday, etc.)

---

## Jan 1, 2026 Test Results

### Summary

| Metric | Value |
|--------|-------|
| Date Verified | January 1, 2026 ~2:00 PM EST |
| Airtable Records (Jan 1 EST) | **158** |
| FreshRSS Articles (Last 6 hrs) | ~120 |
| Pipeline Status | **Working** |

### Airtable Records by Source (Jan 1 EST Afternoon)

| Source | Count | Feed Type |
|--------|-------|-----------|
| Mashable | 8 | Google News |
| Fool | 7 | Google News |
| Msn | 6 | Google News |
| The Atlantic | 5 | Direct |
| WSJ | 4 | Direct |
| Forbes | 3 | Google News |
| Bloomberg | 3 | Direct |
| The Verge | 3 | Direct |
| Barrons | 3 | Google News |
| New York Times | 2 | Direct |
| TechCrunch | 2 | Direct |
| CNBC | 2 | Direct |
| TLDR AI | 2 | Newsletter |
| Theguardian | 2 | Google News (⚠️ casing issue) |

### FreshRSS Crawl Status (Last 6 Hours)

| Feed | Articles | Status |
|------|----------|--------|
| Google News AI | 98 | Working |
| The Guardian | 8 | Working |
| The Atlantic | 5 | Working |
| WSJ | 4 | Working |
| The Verge | 3 | Working |
| Bloomberg | 3 | Working |
| TechCrunch | 2 | Working |
| Reuters | 1 | Working |
| MIT News | 0 | Holiday pause |
| MIT Tech Review | 0 | Holiday pause |
| The Next Web | 0 | Feed dormant |
| TechRepublic | 0 | Holiday pause |

---

## Known Issues

### 1. Source Name Inconsistency (Minor)

**Problem:** Some articles get inconsistent source names.

```
Morning run:   "The Guardian": 31 records
Afternoon run: "Theguardian": 2 records
```

**Cause:** When stream_id mapping fails, the code falls back to URL-based extraction which capitalizes the domain differently.

**Location:** `workers/config/freshrss_client.py` lines 394-433 (`_extract_source_from_url`)

**Fix:** Add more domain mappings or normalize source names post-extraction.

### 2. Dormant Feeds (Not a Bug)

Some feeds show 0 articles due to holiday publishing schedules:

| Feed | Last Article | Notes |
|------|--------------|-------|
| MIT News | Dec 22, 2025 | University holiday |
| The Next Web | Dec 11, 2025 | Feed appears dormant |
| MIT Tech Review | Dec 30, 2025 | Limited holiday publishing |

**Action:** Monitor these feeds when normal publishing resumes (Jan 6, 2026+).

### 3. Google News URL Decoding

Google News URLs need to be decoded to get the actual article URL. The repair script handles this:

**File:** `workers/repair_google_news.py`

**Trigger:** Via HTTP endpoint `/jobs/repair_google_news`

---

## Next Steps

### Immediate (This Week)

- [ ] Monitor dormant feeds after Jan 6, 2026 when publishers resume
- [ ] Consider fixing source name normalization for consistency

### Short-Term (This Month)

- [ ] Run this SOP verification weekly to confirm all feeds are working
- [ ] Add automated alerts if any feed goes 48+ hours without articles
- [ ] Create a dashboard view for feed health monitoring

### Long-Term

- [ ] Consider adding more direct RSS feeds to reduce Google News dependency
- [ ] Evaluate feed performance and remove consistently dormant feeds
- [ ] Add automated cross-reference verification to CI/CD pipeline

---

## Appendix: Full API Examples

### A. Complete Airtable Query Script

```python
#!/usr/bin/env python3
"""
Airtable Ingestion Verification Script
Run from: /workers directory
"""

import os
import sys
import requests
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv('.env.local')

AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
AI_EDITOR_BASE_ID = 'appglKSJZxmA9iHpl'
ARTICLES_TABLE_ID = 'tblMfRgSNSyoRIhx1'

def query_by_date(date_str: str) -> dict:
    """Query Airtable for records ingested on a specific date (UTC)."""
    headers = {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }

    all_records = []
    offset = None

    while True:
        params = {
            'filterByFormula': f"SEARCH('{date_str}', {{date_ingested}}) > 0",
            'pageSize': 100
        }
        if offset:
            params['offset'] = offset

        url = f'https://api.airtable.com/v0/{AI_EDITOR_BASE_ID}/{ARTICLES_TABLE_ID}'
        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        all_records.extend(data.get('records', []))
        offset = data.get('offset')
        if not offset:
            break

    # Group by source and hour
    by_source = defaultdict(int)
    by_hour = defaultdict(int)

    for record in all_records:
        fields = record.get('fields', {})
        source = fields.get('source_name', 'Unknown')
        by_source[source] += 1

        date_ingested = fields.get('date_ingested', '')
        if 'T' in date_ingested:
            hour = date_ingested.split('T')[1][:2]
            by_hour[f"{hour}:00 UTC"] += 1

    return {
        'total': len(all_records),
        'by_source': dict(sorted(by_source.items(), key=lambda x: -x[1])),
        'by_hour': dict(sorted(by_hour.items()))
    }

if __name__ == '__main__':
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    print(f"Querying Airtable for date: {date}")
    result = query_by_date(date)
    print(f"\nTotal records: {result['total']}")
    print(f"\nBy source:")
    for source, count in result['by_source'].items():
        print(f"  {source}: {count}")
    print(f"\nBy hour (UTC):")
    for hour, count in result['by_hour'].items():
        print(f"  {hour}: {count}")
```

### B. Complete FreshRSS Query Script

```python
#!/usr/bin/env python3
"""
FreshRSS Crawl Verification Script
Run from: /workers directory
"""

import requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict

FRESHRSS_URL = "https://pivot-media-rss-feed.onrender.com"
FRESHRSS_AUTH = "admin/d13c712f15c87f1d9aee574372ed7dffe7e5e880"

def check_crawl_status(hours: int = 6) -> dict:
    """Check FreshRSS crawl status for the last N hours."""
    headers = {
        "Authorization": f"GoogleLogin auth={FRESHRSS_AUTH}",
        "User-Agent": "Pivot5-Verification/1.0"
    }

    response = requests.get(
        f"{FRESHRSS_URL}/api/greader.php/reader/api/0/stream/contents",
        headers=headers,
        params={"n": 500, "output": "json"}
    )

    data = response.json()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    by_feed = defaultdict(int)
    total_recent = 0

    for item in data.get('items', []):
        crawl_ms = item.get('crawlTimeMsec')
        if crawl_ms:
            crawl_dt = datetime.fromtimestamp(int(crawl_ms) / 1000, tz=timezone.utc)
            if crawl_dt >= cutoff:
                origin = item.get('origin', {})
                feed_title = origin.get('title', 'Unknown')
                by_feed[feed_title] += 1
                total_recent += 1

    return {
        'total_recent': total_recent,
        'hours': hours,
        'by_feed': dict(sorted(by_feed.items(), key=lambda x: -x[1]))
    }

if __name__ == '__main__':
    result = check_crawl_status(hours=6)
    print(f"FreshRSS articles crawled in last {result['hours']} hours: {result['total_recent']}")
    print(f"\nBy feed:")
    for feed, count in result['by_feed'].items():
        print(f"  {feed}: {count}")
```

---

**Document Version:** 1.0
**Last Updated:** January 1, 2026
**Author:** Claude Code (AI Assistant)
