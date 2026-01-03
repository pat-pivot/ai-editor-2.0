# Newsletter Link Extraction

**Date:** January 2, 2026
**Status:** IMPLEMENTED

---

## Overview

Extracts external news links from AI newsletters and ingests them into the Articles table with provenance tracking. Each newsletter has specific extraction rules based on where "real news" links are found.

---

## Architecture

```
Email Newsletter
    ↓
Kill The Newsletter (converts email → Atom RSS feed)
    ↓
FreshRSS (polls feed, stores as feed/17)
    ↓
Newsletter Extract Job (triggered via dashboard)
    ├── Fetches feed/17 articles from FreshRSS
    ├── Detects newsletter domain from HTML content
    ├── Looks up extraction config (NEWSLETTER_EXTRACTION_CONFIG)
    ├── Calls Claude Haiku to extract <a href> links from HTML
    ├── Filters out blocked domains, non-news URLs
    ├── Resolves Google News URLs if present
    └── Creates records in "Articles - All Ingested" table
        with notes="Link derived from [newsletter] on [date]"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `workers/jobs/newsletter_extract_sandbox.py` | Main extraction job |
| `workers/config/newsletter_extraction.py` | Newsletter configs, blocked domains, patterns |
| `workers/config/freshrss_client.py` | FreshRSS API client (fetches feed/17) |

---

## Newsletter Configuration

### Active Newsletters (with extraction)

| Newsletter | Domain | Section to Extract | Ignore Sections |
|------------|--------|-------------------|-----------------|
| **The Deep View** | thedeepview.co | "From around the web" | Original content at top |
| **AI Valley** | theaivalley.com | "Through the Valley" | - |
| **TLDR AI** | tldr.tech | All external links | - |
| **The Rundown** | therundown.ai | All external links | - |
| **There's an AI For That** | theresanaiforthat.com | "Breaking News", "The Latest AI Developments" | - |
| **Forward Future** | forwardfuture.ai | All except ignored | "From the Live Show", "Toolbox", "Job Board" |
| **AI Breakfast** | aibreakfast.beehiiv.com | All links | - |
| **Future Tools** | futuretools.beehiiv.com | All links | - |
| **Superhuman** | joinsuperhuman.ai | "Today in AI" only | Memes, Productivity, In The Know |
| **Mindstream** | mindstream.news | All links | - |
| **Ben's Bites** | bensbites.co | All links | - |
| **The AI Report** | theaireport.ai | All links | - |
| **ReadWrite AI** | readwrite.com | All links | - |

### Skipped Newsletters

| Newsletter | Domain | Reason |
|------------|--------|--------|
| The Neuron | theneurondaily.com | Low quality, removed |

### Outstanding (Not Yet Configured)

| Newsletter | Status |
|------------|--------|
| **Alpha Signal** | news@alphasignal.ai (pending confirmation) |
| **AI for Work** | aiforwork@mail.beehiiv.com (pending confirmation) |
| **Semi-Analysis** | TBD - may require paid subscription |

---

## Adding a New Newsletter

### 1. Add to Kill The Newsletter

Forward the newsletter's email to your Kill The Newsletter inbox. This creates an Atom feed that FreshRSS will poll.

### 2. Add Config Entry

Edit `workers/config/newsletter_extraction.py`:

```python
NEWSLETTER_EXTRACTION_CONFIG = {
    # ... existing ...

    "newdomain.com": {
        "name": "Newsletter Name",
        "extract_sections": [],           # Specific sections, or empty for all
        "ignore_sections": ["Sponsors"],  # Sections to skip
        "extract_all": True               # True = extract all external links
    },
}
```

### 3. Add to Blocked Domains (if needed)

If the newsletter links to its own domain (most do), add to `BLOCKED_LINK_DOMAINS`:

```python
BLOCKED_LINK_DOMAINS = [
    # ... existing ...
    "newdomain.com",  # Newsletter's own site
]
```

---

## Blocked Domains

Links from these domains are never extracted:

**Newsletter Platforms:**
- beehiiv.com, substack.com, mailchimp.com, convertkit.com, buttondown.email, revue.co

**Social Media:**
- twitter.com/home, x.com/home, linkedin.com/in/, facebook.com, instagram.com, tiktok.com

**Tracking/Ads:**
- bit.ly, tinyurl.com, ow.ly, geni.us, amzn.to

**Newsletter Own Sites:**
- All newsletters in NEWSLETTER_EXTRACTION_CONFIG have their own domains blocked

---

## Non-News URL Patterns

URLs matching these patterns are skipped:

- `/models/`, `huggingface.co/`, `github.com/` (AI model/code pages)
- `/pricing`, `/signup`, `/login`, `/download` (product pages)
- `/docs/`, `/api-reference` (documentation)
- `/careers`, `/jobs/`, `greenhouse.io`, `lever.co` (job postings)

---

## LLM Extraction

Uses **Claude Haiku** (claude-3-haiku-20240307) with:
- `temperature=0.1` (deterministic)
- `max_tokens=4000`
- Explicit anti-hallucination prompt

### Prompt Template

```
You are parsing HTML to find URLs that link to external news articles.

Newsletter: {newsletter_name}

CRITICAL RULE - DO NOT HALLUCINATE:
You must ONLY return URLs that LITERALLY APPEAR in the HTML content below as href attributes.
DO NOT make up URLs. DO NOT generate plausible-looking URLs.
ONLY extract actual URLs from <a href="..."> tags in the HTML.

TASK:
{section_instructions}
{ignore_instructions}

...

IMPORTANT: Every URL you return MUST be copy-pasted from an href attribute in the HTML below.
If you cannot find any valid news URLs in the HTML, return: []
```

---

## Airtable Schema

**Table:** Articles - All Ingested (AI Editor 2.0 base)

**Fields populated by newsletter extraction:**

| Field | Value |
|-------|-------|
| `pivot_id` | Generated hash of URL + headline |
| `original_url` | Extracted article URL |
| `source_name` | Publication name (from domain mapping) |
| `headline` | Anchor text or "Article from {source}" |
| `date_ingested` | Current timestamp (EST) |
| `date_og_published` | Newsletter publish date |
| `needs_ai` | `true` |
| `fit_status` | `"pending"` |
| `notes` | Provenance with friendly date + clickable email link |

**Notes field format:**
```
Link derived from TLDR AI on January 2, 2026 at 7:50am ET
Original email: https://kill-the-newsletter.com/alternates/abc123.html
```

---

## Running the Job

### Via Dashboard

1. Go to AI Editor Dashboard → Sandbox tab
2. Click "Newsletter Link Extraction" card
3. Click "Run Newsletter Extract"

### Via API

```bash
POST /api/jobs
{
  "step": "newsletter_extract_sandbox"
}
```

---

## Cost Estimate

**Claude Haiku:** ~$0.25/1M input, ~$1.25/1M output tokens

**Per Newsletter Issue:**
- Input: ~15K tokens (newsletter HTML, truncated)
- Output: ~500 tokens (JSON array)
- Cost: ~$0.004 per newsletter

**Daily Cost (10-15 newsletters):** ~$0.04-0.06/day = ~$1.50/month

---

## Debugging

### Check Logs

```bash
# Render dashboard → ai-editor-worker → Logs
# Search for: [Newsletter Extract] or [GNEWS DECODE]
```

### Common Issues

**No links extracted:**
- Check if newsletter HTML has full content (not truncated)
- Verify newsletter domain is in NEWSLETTER_EXTRACTION_CONFIG
- Check if all extracted URLs are being blocked

**Hallucinated URLs:**
- If URLs look fake (wrong dates, made-up paths), the HTML content is likely too short
- The 500-char truncation bug in freshrss_client.py was fixed 2026-01-02

**Duplicates:**
- pivot_id deduplication should prevent duplicates
- Check if the same newsletter issue is being processed multiple times

---

## Changelog

**2026-01-02 (update 2):**
- Added backup reasoning to Claude prompt - uses general news detection if section headers differ
- Improved date formatting: "January 2, 2026 at 7:50am ET" instead of ISO format
- Added clickable email link to notes field (links to Kill The Newsletter archive)
- Set Superhuman to extract_all: True (matching other newsletters)

**2026-01-02:**
- Initial implementation
- Separated from ingest_sandbox.py into standalone job
- Fixed 500-char truncation bug in freshrss_client.py (was cutting off all links)
- Added anti-hallucination prompt for Claude Haiku
