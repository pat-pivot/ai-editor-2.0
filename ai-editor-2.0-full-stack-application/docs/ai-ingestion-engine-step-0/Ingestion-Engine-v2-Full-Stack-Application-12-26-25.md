# Ingestion Engine v2 - Full-Stack Application

**Version:** 2.0
**Date:** December 26, 2025
**Status:** Implementation Specification

---

## Overview

This document specifies how to recreate the n8n Ingestion Engine as part of the AI Editor 2.0 Full-Stack Application. The ingestion engine fetches articles from RSS feeds and appends them to Airtable.

### Key Design Decisions

1. **RSS-Only Ingestion** - No Firecrawl. Articles are ingested from RSS feeds only.
2. **One-Button-Click Operation** - Single button in frontend triggers ingestion of all feeds
3. **Deduplication via PivotID** - Hash-based unique identifier prevents duplicate articles
4. **Background Processing** - Python worker handles ingestion asynchronously via Redis Queue

---

## Target Airtable Table

### Newsletter Issue Stories

- **Base ID:** `appwSozYTkrsQWUXB`
- **Table ID:** `tblaHcFFG6Iw3w7lL`
- **Table Name:** Newsletter Issue Stories
- **View:** Grid view (`viwMY55gZ1AnmbdV4`)

### Complete Schema

| Field Name | Type | Description | Populated During Ingestion? |
|------------|------|-------------|----------------------------|
| `issue_id` | Text | Newsletter issue identifier | No - set later |
| `newsletter_id` | Text | Newsletter identifier | No - set later |
| `ai_headline` | Multiline Text | Article headline (initially from RSS title) | **YES** |
| `date_og_published` | DateTime | Original publication date from RSS | **YES** |
| `send_date` | DateTime | Newsletter send date | No - set later |
| `send_slot` | Single Select | AM or PM send slot | No - set later |
| `StoryID` | Multiline Text | Story identifier | **YES** (generated) |
| `Order` | Number | Display order in newsletter | No - set later |
| `decorated_url` | URL | Decorated/processed URL | No - set later |
| `tags` | Multiline Text | Article tags | **YES** (from RSS categories) |
| `pivotId` | Text | Unique hash-based identifier | **YES** (generated) |
| `bullet_1` | Multiline Text | Summary bullet 1 | No - decoration step |
| `bullet_2` | Multiline Text | Summary bullet 2 | No - decoration step |
| `bullet_3` | Multiline Text | Summary bullet 3 | No - decoration step |
| `ai_dek` | Multiline Text | Article subtitle/deck | No - decoration step |
| `topic` | Text | Primary topic classification | **YES** (from RSS or inferred) |
| `slot` | Single Select | Newsletter position (header/body/footer/card1/card2/hero) | No - set later |
| `image_url` | URL | Article image URL | **YES** (from RSS if available) |
| `story_link` | Record Link | Link to Articles table record | Optional |
| `markdown (from story_link)` | Lookup | Article markdown content | Lookup field |
| `pivotnews_url` | Formula | Auto-generated URL (`https://pivotnews.com/{StoryID}`) | Auto |
| `blog_post_raw` | Rich Text | Raw blog post content | No - decoration step |
| `clicks_total` | Number | Click tracking | No - analytics |
| `id` | Text | Record identifier | No - auto |
| `ai_image_complete` | Checkbox | Image generation status | No - set later |
| `image_prompt` | Multiline Text | Prompt for AI image generation | No - decoration step |
| `markdown_2` | Multiline Text | Secondary markdown field | No - set later |
| `pivot_Id` | Formula | Formula field (mirrors `pivotId`) | Auto |

### Slot Options

The `slot` field accepts these values:
- `header` - Top story position
- `body` - Main body content
- `footer` - Footer position
- `card1` - Card layout position 1
- `card2` - Card layout position 2
- `hero` - Hero/featured position

### Send Slot Options

The `send_slot` field accepts:
- `AM` - Morning send
- `PM` - Afternoon/evening send

---

## Fields to Populate During Ingestion

When an article is ingested from RSS, populate these fields:

```python
record = {
    "pivotId": generated_pivot_id,      # Hash of URL or title
    "StoryID": generated_story_id,       # Unique story identifier
    "ai_headline": rss_item.title,       # RSS title
    "date_og_published": rss_item.pubDate,  # ISO format
    "tags": rss_item.categories,         # Comma-separated if multiple
    "topic": inferred_topic,             # From RSS category or source
    "image_url": rss_item.enclosure_url  # If available in RSS
}
```

---

## RSS Feeds Configuration

### Complete Feed List (19 Feeds)

| Source | Feed URL |
|--------|----------|
| Reuters AI | `https://rss.app/feeds/MXiuPVkXDT8HqezK.xml` |
| Reuters Business | `https://rss.app/feeds/C3YLADfGxE5e57eT.xml` |
| The Neuron | `https://rss.app/feeds/1iWmVmkwOR9FvPtW.xml` |
| AI Valley | `https://rss.app/feeds/el3M8L2iqw3VrU3A.xml` |
| There's an AI For That | `https://rss.app/feeds/9SVrxNsg7y419Fke.xml` |
| The Deep View | `https://rss.app/feeds/NY8oNua0ZxWUYR3Z.xml` |
| The AI Report | `https://rss.app/feeds/kRbnlccEQPpl1f6M.xml` |
| CNBC Finance | `https://rss.app/feeds/yD81szEq5uTWg5I5.xml` |
| The Verge | `https://rss.app/feeds/08AqYC4pZsuLfMKv.xml` |
| Yahoo Finance | `https://news.yahoo.com/rss/finance` |
| TechCrunch | `https://rss.app/feeds/YaCBpvEvBDczG9zT.xml` |
| Tech Republic | `https://rss.app/feeds/mC6cK6lSVgJjRTgO.xml` |
| SuperHuman | `https://rss.app/feeds/QymucjzuFkzvxvkg.xml` |
| Semafor Business | `https://rss.app/feeds/ZbdBsJTYo3gDOWmI.xml` |
| Semafor Technology | `https://rss.app/feeds/6GwMn0gNjbWxUjPN.xml` |
| Semafor CEO | `https://rss.app/feeds/jSkbNDntFNSdShkz.xml` |
| Google News AI | `https://news.google.com/rss/search?q=AI+OR+%22artificial+intelligence%22+when:12h&hl=en-US&gl=US&ceid=US:en` |
| Google News Finance | `https://news.google.com/rss/search?q=markets+OR+%22S%26P+500%22+OR+stocks+OR+earnings+when:12h&hl=en-US&gl=US&ceid=US:en` |
| The Atlantic Technology | `https://rss.app/feeds/L83urFREcjBOcQ5z.xml` |

### Python Feed Configuration

```python
# workers/config/rss_feeds.py

RSS_FEEDS = [
    {"name": "Reuters AI", "url": "https://rss.app/feeds/MXiuPVkXDT8HqezK.xml", "source_id": "Reuters"},
    {"name": "Reuters Business", "url": "https://rss.app/feeds/C3YLADfGxE5e57eT.xml", "source_id": "Reuters"},
    {"name": "The Neuron", "url": "https://rss.app/feeds/1iWmVmkwOR9FvPtW.xml", "source_id": "The Neuron"},
    {"name": "AI Valley", "url": "https://rss.app/feeds/el3M8L2iqw3VrU3A.xml", "source_id": "AI Valley"},
    {"name": "There's an AI For That", "url": "https://rss.app/feeds/9SVrxNsg7y419Fke.xml", "source_id": "There's an AI For That"},
    {"name": "The Deep View", "url": "https://rss.app/feeds/NY8oNua0ZxWUYR3Z.xml", "source_id": "The Deep View"},
    {"name": "The AI Report", "url": "https://rss.app/feeds/kRbnlccEQPpl1f6M.xml", "source_id": "The AI Report"},
    {"name": "CNBC Finance", "url": "https://rss.app/feeds/yD81szEq5uTWg5I5.xml", "source_id": "CNBC"},
    {"name": "The Verge", "url": "https://rss.app/feeds/08AqYC4pZsuLfMKv.xml", "source_id": "The Verge"},
    {"name": "Yahoo Finance", "url": "https://news.yahoo.com/rss/finance", "source_id": "Yahoo Finance"},
    {"name": "TechCrunch", "url": "https://rss.app/feeds/YaCBpvEvBDczG9zT.xml", "source_id": "TechCrunch"},
    {"name": "Tech Republic", "url": "https://rss.app/feeds/mC6cK6lSVgJjRTgO.xml", "source_id": "Tech Republic"},
    {"name": "SuperHuman", "url": "https://rss.app/feeds/QymucjzuFkzvxvkg.xml", "source_id": "SuperHuman"},
    {"name": "Semafor Business", "url": "https://rss.app/feeds/ZbdBsJTYo3gDOWmI.xml", "source_id": "Semafor"},
    {"name": "Semafor Technology", "url": "https://rss.app/feeds/6GwMn0gNjbWxUjPN.xml", "source_id": "Semafor"},
    {"name": "Semafor CEO", "url": "https://rss.app/feeds/jSkbNDntFNSdShkz.xml", "source_id": "Semafor"},
    {"name": "Google News AI", "url": "https://news.google.com/rss/search?q=AI+OR+%22artificial+intelligence%22+when:12h&hl=en-US&gl=US&ceid=US:en", "source_id": "Google News"},
    {"name": "Google News Finance", "url": "https://news.google.com/rss/search?q=markets+OR+%22S%26P+500%22+OR+stocks+OR+earnings+when:12h&hl=en-US&gl=US&ceid=US:en", "source_id": "Google News"},
    {"name": "The Atlantic Technology", "url": "https://rss.app/feeds/L83urFREcjBOcQ5z.xml", "source_id": "The Atlantic"},
]
```

---

## PivotID Generation Algorithm

The `pivotId` is a unique identifier used for deduplication. It's generated from a hash of the normalized URL or title.

### Python Implementation

```python
# workers/utils/pivot_id.py

def hash_string(s: str) -> str:
    """DJB2 hash algorithm - matches JavaScript implementation."""
    if not isinstance(s, str):
        s = str(s) if s else ''

    hash_value = 5381
    for char in s:
        hash_value = ((hash_value << 5) + hash_value) + ord(char)
        hash_value = hash_value & 0xFFFFFFFF  # Keep as 32-bit unsigned

    return base36_encode(hash_value)


def base36_encode(num: int) -> str:
    """Convert number to base36 string."""
    chars = '0123456789abcdefghijklmnopqrstuvwxyz'
    if num == 0:
        return '0'
    result = ''
    while num:
        result = chars[num % 36] + result
        num //= 36
    return result


def normalize_url(url: str) -> str | None:
    """Normalize URL for consistent hashing."""
    if not url:
        return None

    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

    try:
        parsed = urlparse(url.lower())

        # Remove tracking parameters
        tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'}
        query_params = parse_qs(parsed.query)
        filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}

        # Rebuild URL
        cleaned = parsed._replace(
            query=urlencode(filtered_params, doseq=True),
            path=parsed.path.rstrip('/')
        )
        return urlunparse(cleaned)
    except Exception:
        return url.lower().rstrip('/')


def generate_pivot_id(url: str = None, title: str = None) -> str | None:
    """Generate pivotId from URL or title."""
    normalized_url = normalize_url(url)
    pivot_base = normalized_url or title

    if not pivot_base:
        return None

    return f"p_{hash_string(pivot_base)}"
```

---

## Implementation Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  "Ingest Articles" Button                                    │    │
│  │  - Triggers POST /api/ingest                                 │    │
│  │  - Shows loading state                                       │    │
│  │  - Displays results (new articles, duplicates skipped)       │    │
│  └─────────────────────────────────────────────────────────────┘    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NEXT.JS API ROUTE                               │
│  POST /api/ingest                                                    │
│  - Validates request                                                 │
│  - Enqueues job to Redis Queue                                       │
│  - Returns job ID for status polling                                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PYTHON WORKER                                   │
│  Job: ingest_articles()                                              │
│                                                                      │
│  1. Fetch all RSS feeds in parallel                                  │
│  2. Parse RSS items                                                  │
│  3. Generate pivotId for each article                                │
│  4. Check Airtable for existing pivotId (deduplication)              │
│  5. Create new records in Newsletter Issue Stories table             │
│  6. Return summary (ingested count, skipped count)                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AIRTABLE                                        │
│  Base: appwSozYTkrsQWUXB                                             │
│  Table: tblaHcFFG6Iw3w7lL (Newsletter Issue Stories)                 │
│                                                                      │
│  Records created with:                                               │
│  - pivotId (unique identifier for deduplication)                     │
│  - StoryID                                                           │
│  - ai_headline (from RSS title)                                      │
│  - date_og_published                                                 │
│  - tags (from RSS categories)                                        │
│  - topic                                                             │
│  - image_url (if available)                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Worker Implementation

### Job: ingest_articles

```python
# workers/jobs/ingest.py

import asyncio
import aiohttp
import feedparser
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from pyairtable import Api

from workers.config.rss_feeds import RSS_FEEDS
from workers.utils.pivot_id import generate_pivot_id


async def fetch_feed(session: aiohttp.ClientSession, feed: Dict) -> List[Dict]:
    """Fetch and parse a single RSS feed."""
    try:
        async with session.get(feed["url"], timeout=30) as response:
            content = await response.text()
            parsed = feedparser.parse(content)

            return [
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "pubDate": entry.get("published", ""),
                    "categories": ", ".join([cat.term for cat in entry.get("tags", [])]),
                    "image_url": entry.get("media_content", [{}])[0].get("url", "")
                                 or entry.get("enclosures", [{}])[0].get("href", ""),
                    "source_id": feed["source_id"],
                    "feed_name": feed["name"]
                }
                for entry in parsed.entries
            ]
    except Exception as e:
        print(f"Error fetching {feed['name']}: {e}")
        return []


async def fetch_all_feeds() -> List[Dict]:
    """Fetch all RSS feeds in parallel."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, feed) for feed in RSS_FEEDS]
        results = await asyncio.gather(*tasks)

        # Flatten results
        all_articles = []
        for articles in results:
            all_articles.extend(articles)

        return all_articles


def ingest_articles():
    """Main ingestion job."""

    # Initialize Airtable
    api = Api(os.environ["AIRTABLE_API_KEY"])
    table = api.table("appwSozYTkrsQWUXB", "tblaHcFFG6Iw3w7lL")

    # Fetch all articles from RSS feeds
    articles = asyncio.run(fetch_all_feeds())

    # Get existing pivotIds from Airtable for deduplication
    existing_records = table.all(fields=["pivotId"])
    existing_pivot_ids = {r["fields"].get("pivotId") for r in existing_records if r["fields"].get("pivotId")}

    # Process and create new records
    ingested = 0
    skipped = 0

    for article in articles:
        pivot_id = generate_pivot_id(article["link"], article["title"])

        if not pivot_id:
            skipped += 1
            continue

        if pivot_id in existing_pivot_ids:
            skipped += 1
            continue

        # Generate StoryID (could be same as pivotId or different format)
        story_id = pivot_id.replace("p_", "s_")

        # Prepare Airtable record
        record = {
            "pivotId": pivot_id,
            "StoryID": story_id,
            "ai_headline": article["title"][:500],  # Airtable field limit
            "date_og_published": article["pubDate"] if article["pubDate"] else None,
            "tags": article["categories"][:1000] if article["categories"] else None,
            "topic": article["source_id"],  # Use source as initial topic
            "image_url": article["image_url"] if article["image_url"] else None
        }

        # Remove None values
        record = {k: v for k, v in record.items() if v is not None}

        try:
            table.create(record)
            existing_pivot_ids.add(pivot_id)  # Prevent duplicates within batch
            ingested += 1
        except Exception as e:
            print(f"Error creating record: {e}")
            skipped += 1

    return {
        "articles_found": len(articles),
        "articles_ingested": ingested,
        "articles_skipped": skipped
    }
```

---

## Environment Variables

```bash
# Airtable
AIRTABLE_API_KEY=patQVZtZjQS8GU78r.xxx
AIRTABLE_BASE_ID=appwSozYTkrsQWUXB
AIRTABLE_NEWSLETTER_ISSUE_STORIES_TABLE=tblaHcFFG6Iw3w7lL

# Redis (for job queue)
REDIS_URL=redis://localhost:6379/0
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `workers/config/rss_feeds.py` | RSS feed configuration |
| `workers/utils/pivot_id.py` | PivotID generation utilities |
| `workers/jobs/ingest.py` | Ingestion job implementation |
| `app/src/app/api/ingest/route.ts` | API endpoint for triggering ingestion |
| `app/src/components/IngestButton.tsx` | Frontend button component |

---

## Implementation Checklist

- [ ] Create `workers/config/rss_feeds.py` with feed configuration
- [ ] Create `workers/utils/pivot_id.py` with hash functions
- [ ] Create `workers/jobs/ingest.py` with ingestion logic
- [ ] Create `app/src/app/api/ingest/route.ts` API endpoint
- [ ] Create frontend button component
- [ ] Add job status polling endpoint
- [ ] Test with single feed first
- [ ] Test full ingestion run
- [ ] Monitor Airtable for successful record creation
