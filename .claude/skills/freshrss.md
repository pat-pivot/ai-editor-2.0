# FreshRSS Google Reader API Reference

This skill provides documentation for working with the FreshRSS Google Reader compatible API used by the Pivot 5 ingestion pipeline.

## Quick Reference

**Production Instance:** `https://pivot-media-rss-feed.onrender.com`
**API Endpoint:** `https://pivot-media-rss-feed.onrender.com/api/greader.php`
**Context7 Library ID:** `/websites/freshrss_github_io_freshrss_en`

## Authentication

FreshRSS uses a GoogleLogin-style auth token in the format `username/token`.

### Auth Header Format
```
Authorization: GoogleLogin auth=admin/d13c712f15c87f1d9aee574372ed7dffe7e5e880
```

### Login Endpoint
```bash
curl 'https://freshrss.example.net/api/greader.php/accounts/ClientLogin?Email=alice&Passwd=Abcdef123456'
```

**Response:**
```json
{
  "SID": "alice/8e6845e089457af25303abc6f53356eb60bdb5f8",
  "Auth": "alice/8e6845e089457af25303abc6f53356eb60bdb5f8"
}
```

## Key API Endpoints

### List Subscriptions
```bash
curl -s -H "Authorization:GoogleLogin auth=admin/TOKEN" \
  'https://pivot-media-rss-feed.onrender.com/api/greader.php/reader/api/0/subscription/list?output=json'
```

### Unread Count
```bash
curl -s -H "Authorization:GoogleLogin auth=admin/TOKEN" \
  'https://pivot-media-rss-feed.onrender.com/api/greader.php/reader/api/0/unread-count?output=json'
```

### Stream Contents (Articles)
```bash
curl -s -H "Authorization:GoogleLogin auth=admin/TOKEN" \
  'https://pivot-media-rss-feed.onrender.com/api/greader.php/reader/api/0/stream/contents/reading-list?n=100&output=json'
```

### Stream Contents Parameters
| Parameter | Description |
|-----------|-------------|
| `n` | Number of items to return (default varies) |
| `ot` | Oldest timestamp - only return items newer than this Unix timestamp |
| `nt` | Newest timestamp - only return items older than this Unix timestamp |
| `c` | Continuation token for pagination |
| `r` | Ranking/sort order |
| `output` | Response format (`json`) |

### Specific Feed
```bash
curl -s -H "Authorization:GoogleLogin auth=admin/TOKEN" \
  'https://pivot-media-rss-feed.onrender.com/api/greader.php/reader/api/0/stream/contents/feed/3?n=50&output=json'
```

## Article Response Fields

Each article item in the response contains:

```json
{
  "id": "tag:google.com,2005:reader/item/...",
  "title": "Article headline",
  "published": 1735488000,        // Unix timestamp when PUBLISHED (article date)
  "crawlTimeMsec": "1735520400000", // When FreshRSS DISCOVERED it (ms)
  "alternate": [{"href": "https://..."}],
  "origin": {
    "streamId": "feed/3",
    "title": "Bloomberg Technology"
  },
  "summary": {"content": "..."},
  "content": {"content": "..."}
}
```

## CRITICAL: Timestamp Fields

**Two different timestamps - know the difference:**

| Field | Format | Meaning | Use Case |
|-------|--------|---------|----------|
| `published` | Unix seconds | When article was **originally published** | Filter for news recency |
| `crawlTimeMsec` | Unix milliseconds | When FreshRSS **discovered** the article | Filter to avoid reprocessing |

### Common Issue
An article published 7 days ago can be crawled today (e.g., backfill when new feeds are added). Using identical time windows for both filters is too aggressive.

**Best Practice:** Use different windows for each filter:
1. `crawlTimeMsec` - 36h window (prevents reprocessing, allows for FreshRSS crawl delays)
2. `published` - 72h window (allows 2-3 day old articles, blocks week-old stale news)

```python
# Filter by BOTH timestamps with different windows
cutoff = datetime.now(timezone.utc) - timedelta(hours=36)  # crawl filter
published_cutoff = datetime.now(timezone.utc) - timedelta(hours=72)  # published filter

if article.get("crawl_dt"):
    if article["crawl_dt"] < cutoff:
        continue
if article.get("published_dt"):
    if article["published_dt"] < published_cutoff:
        continue
```

**Why 36h for crawl?** FreshRSS requires external triggers to crawl and may not run consistently. 36h gives buffer for crawl delays while still preventing stale reprocessing.

**Why 72h for published?** Articles can be crawled days after publication (Google News delays, editorial processes). 72h allows recently-discovered older articles while blocking stale news that would flood the pipeline.

## Feed Types (Pivot 5 Configuration)

We use **3 types of feeds** in FreshRSS:

### 1. Direct RSS Feeds
Native RSS from publisher websites. URLs point directly to articles.
- Bloomberg, TechCrunch, The Verge, The Atlantic, CNBC, VentureBeat, TechRepublic

### 2. Google News RSS Searches
RSS feeds from Google News search queries. **URLs are `news.google.com` redirects** that must be decoded.
```
https://news.google.com/rss/search?q=site:wsj.com/tech&hl=en-US&gl=US&ceid=US:en
https://news.google.com/rss/search?q=AI+OR+"artificial+intelligence"+when:12h
```
- WSJ (Tech, Business AI), NYT Technology, Reuters AI, Semafor, Google News AI

### 3. Kill The Newsletter
Email newsletters converted to RSS via kill-the-newsletter.com
```
https://kill-the-newsletter.com/feeds/wursamkt3o49gpvmp6la.xml
```
- AI Newsletter forwards (The Neuron, AI Valley, etc.)

## Feed IDs (Pivot 5 Production)

Updated Dec 31, 2025 - Semafor feed changed to tech-only (site:semafor.com/tech).

| Feed ID | Source | Type |
|---------|--------|------|
| `feed/3` | Bloomberg Technology | Direct RSS |
| `feed/8` | The Verge | Direct RSS |
| `feed/10` | CNBC Tech | Direct RSS |
| `feed/11` | The Atlantic | Direct RSS |
| `feed/16` | Google News AI | Google News |
| `feed/17` | AI Newsletters | Kill The Newsletter |
| `feed/23` | Reuters AI | Google News |
| `feed/41` | Semafor Tech | Google News (site:semafor.com technology AI) |
| `feed/28` | VentureBeat | Direct RSS |
| `feed/30` | The Next Web AI | Direct RSS |
| `feed/31` | MIT Tech Review AI | Direct RSS |
| `feed/32` | MIT News AI | Direct RSS |
| `feed/33` | Science Daily AI | Direct RSS |
| `feed/42` | The Guardian AI | Google News (site:theguardian.com/technology AI) |
| `feed/35` | TechCrunch AI | Direct RSS |
| `feed/36` | TechRepublic AI | Direct RSS |
| `feed/37` | New York Times AI | Direct RSS (native) |
| `feed/38` | WSJ Technology | Direct RSS (Dow Jones) |

## CRITICAL: Google News URL Resolution

Google News RSS feeds return **redirect URLs** like:
```
https://news.google.com/rss/articles/CBMiWkFVX3lxTE1...
```

These MUST be decoded to get the actual article URL. We use the `googlenewsdecoder` package:

```python
from googlenewsdecoder import gnewsdecoder

result = gnewsdecoder(google_news_url, interval=0.3)
if result.get("status") and result.get("decoded_url"):
    actual_url = result["decoded_url"]
```

### Rate Limiting
- Process Google News URLs in **batches of 10**
- Add **1 second delay** between batches
- Use thread pool (max 10 workers) for async resolution

### Source Extraction After Resolution
After decoding, extract source name from the resolved URL domain:
```python
DOMAIN_TO_SOURCE = {
    "reuters.com": "Reuters",
    "wsj.com": "WSJ",
    "nytimes.com": "New York Times",
    "bloomberg.com": "Bloomberg",
    "cnbc.com": "CNBC",
    "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge",
    # ... 30+ mappings in ingest_sandbox.py
}
```

## Marking Items as Read (Fever API)

FreshRSS also supports the Fever API for marking items:

```bash
# Mark single item as read
curl 'https://freshrss.example.net/api/fever.php?api&mark=item&as=read&id=ITEM_ID'

# Mark entire feed as read
curl 'https://freshrss.example.net/api/fever.php?api&mark=feed&as=read&feed_id=FEED_ID'
```

**Note:** Pivot 5 uses `pivot_id` hash deduplication instead of marking items read.

## Using Context7 for Documentation

To look up FreshRSS documentation:

```
mcp__context7__query-docs:
  libraryId: /websites/freshrss_github_io_freshrss_en
  query: "your search query here"
```

**Example queries:**
- `"Google Reader API stream contents parameters"`
- `"authentication login endpoint"`
- `"subscription list endpoint"`
- `"mark items read edit-tag"`

## Codebase Integration

### Python Client Location
`workers/config/freshrss_client.py`

### Key Functions
- `FreshRSSClient.get_articles(limit, feed_id, since_hours)` - Fetch articles
- `FreshRSSClient.list_feeds()` - List subscriptions
- `FreshRSSClient.health_check()` - Verify API connectivity

### Environment Variables
```
FRESHRSS_URL=https://pivot-media-rss-feed.onrender.com
FRESHRSS_AUTH=admin/d13c712f15c87f1d9aee574372ed7dffe7e5e880
```

## CRITICAL: FreshRSS Feed Refresh

**FreshRSS requires an external trigger to crawl feeds - it doesn't auto-refresh on its own.**

### Actualize Endpoint (Wake Up FreshRSS)
```bash
curl 'https://pivot-media-rss-feed.onrender.com/i/?c=feed&a=actualize&ajax=1&maxFeeds=50'
```

**Response:** `OK` if successful

### Auto-Refresh in Python Client
The `FreshRSSClient.get_articles()` method automatically calls `trigger_refresh()` before fetching articles. This ensures feeds are freshly crawled.

```python
# Auto-refresh is enabled by default
articles = client.get_articles(limit=100)

# Disable if you just want to read cached articles
articles = client.get_articles(limit=100, auto_refresh=False)
```

### Why This Matters
Without triggering a refresh, articles from some feeds may be 40+ hours old (last crawl time), causing them to be filtered out by the 36h crawl window.

## Troubleshooting

### "Only getting articles from some feeds"
- **Cause:** FreshRSS hasn't crawled some feeds recently (needs external trigger)
- **Fix:** Call the actualize endpoint before fetching, or ensure `auto_refresh=True`

### "Only getting Google News articles"
- **Cause:** Limit too low, Google News feeds fill quota first
- **Fix:** Increase `limit` parameter (e.g., 1000) then filter by recency

### "Articles missing from certain feeds"
- **Cause:** Filtering by `published` only misses recently-crawled older articles
- **Fix:** Filter by both `crawlTimeMsec` AND `published`

### "403 Forbidden"
- **Cause:** Auth token invalid or expired
- **Fix:** Regenerate API token in FreshRSS settings
