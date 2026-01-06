# Newsletter Link Extraction Feature

**Date:** January 2, 2026
**Updated:** January 2, 2026 (Separated into standalone job)
**Status:** DEPLOYED

**Files:**
- `workers/jobs/newsletter_extract_sandbox.py` (standalone job)
- `workers/config/newsletter_extraction.py` (config)
- `workers/config/freshrss_client.py` (domain mappings)
- `src/app/(dashboard)/sandbox/page.tsx` (UI - third card)
- `src/app/api/jobs/route.ts` (API routing)
- `workers/trigger.py` (job trigger)

---

## Overview

This feature extracts external news links from AI newsletters and ingests them into the `Articles - All Ingested` table with provenance tracking. Each newsletter has different sections where "real news" links are found.

**Architecture Change (Jan 2, 2026):** Newsletter extraction is now a **separate button** in the dashboard, not integrated into the ingest job. This allows running newsletter extraction independently.

---

## How It Works

```
Dashboard: Click "Newsletter Link Extraction" button (third card)
    |
    v
API: POST /api/jobs with step="newsletter_extract_sandbox"
    |
    v
Trigger Service: Enqueue newsletter_extract_sandbox job
    |
    v
Job: Fetch feed/17 articles from FreshRSS (Kill The Newsletter)
    |
    v
For each newsletter article:
    +-- Identify newsletter domain from HTML content
    +-- Look up extraction config for that newsletter
    +-- Call Claude Haiku to extract news links from HTML
    +-- For each extracted link:
        +-- Resolve URL (decode Google News if needed)
        +-- Extract source from domain
        +-- Generate pivot_id
        +-- Check for duplicates
        +-- Create record with notes="Link derived from [newsletter] on [date]"
```

**Note:** The regular "Ingest Articles" button no longer processes newsletters - use the dedicated Newsletter Extraction button.

---

## Newsletter Configuration

### Active Newsletters (with extraction logic)

| Newsletter | Domain | Section to Extract | Ignore Sections |
|------------|--------|-------------------|-----------------|
| **Deep View** | thedeepview.co | "From around the web" | Original content at top |
| **AI Valley** | theaivalley.com | "Through the Valley" | - |
| **TLDR AI** | tldr.tech | All links | - |
| **The Rundown** | therundown.ai | All external links | - |
| **There's an AI For That** | theresanaiforthat.com | "Breaking News", "The Latest AI Developments" | - |
| **Forward Future** | forwardfuture.ai | All except ignored | "From the Live Show", "Toolbox", "Job Board" |
| **AI Breakfast** | aibreakfast.beehiiv.com | Entire newsletter | - |
| **Future Tools** | futuretools.beehiiv.com | All links | - |
| **Superhuman** | joinsuperhuman.ai / superhuman.ai | "Today in AI" only | Memes, Productivity, In The Know |
| **Mindstream** | mindstream.news | All links | - |
| **Ben's Bites** | bensbites.co | All links | - |
| **The AI Report** | theaireport.ai | All links | - |

### Skipped Newsletters (No Extraction)

| Newsletter | Domain | Reason |
|------------|--------|--------|
| **The Neuron** | theneurondaily.com | Low quality |

---

## Configuration File

**Path:** `workers/config/newsletter_extraction.py`

### Newsletter Config Structure

```python
NEWSLETTER_EXTRACTION_CONFIG = {
    "thedeepview.co": {
        "name": "The Deep View",
        "extract_sections": ["From around the web"],  # Only extract from these
        "ignore_sections": [],                        # Skip these sections
        "extract_all": False                          # If True, extract all links
    },
    "tldr.tech": {
        "name": "TLDR AI",
        "extract_sections": [],
        "ignore_sections": [],
        "extract_all": True  # All links are news
    },
    # ... more newsletters
}
```

### Blocked Domains

Links from these domains are never extracted:

- Newsletter platforms: beehiiv.com, substack.com, mailchimp.com, convertkit.com
- Social media profiles: twitter.com/home, linkedin.com/in/, facebook.com, instagram.com
- Sponsor/ad domains: bit.ly, tinyurl.com, geni.us, amzn.to
- Newsletter's own domains (self-referential links)

### Non-News URL Patterns

URLs matching these patterns are skipped:

- AI model pages: /models/, huggingface.co/
- Product pages: /pricing, /signup, /download
- Documentation: /docs/, /api-reference
- Job postings: /careers, /jobs/, greenhouse.io

---

## LLM Extraction

Uses **Claude 3 Haiku** (claude-3-haiku-20240307) for fast, cheap extraction.

### Cost Estimate

| Metric | Value |
|--------|-------|
| Input tokens per newsletter | ~15K |
| Output tokens per newsletter | ~500 |
| Cost per newsletter | ~$0.004 |
| Daily cost (10 newsletters) | ~$0.04 |
| Monthly cost | ~$1.20 |

### Extraction Prompt

The LLM is instructed to:
1. Extract only links to REAL NEWS STORIES (not blog posts, product pages)
2. Follow section-specific rules for each newsletter
3. Skip newsletter infrastructure links (unsubscribe, social profiles)
4. Return JSON array with: url, headline (if visible), source_hint (if detectable)

---

## Provenance Tracking

Each extracted link gets a `notes` field with:

```
Link derived from [Newsletter Name] on [YYYY-MM-DD]
```

Example:
```
Link derived from The Deep View on 2026-01-02
```

---

## Airtable Schema

**Table:** Articles - All Ingested (AI Editor 2.0 base)

**New Field:** `notes` (Single Line Text)

**Fields written for newsletter-derived articles:**
- `pivot_id` - Deduplication key
- `original_url` - Resolved article URL
- `source_name` - Publication name (extracted from URL)
- `headline` - Article title (if extracted) or "Article from [Source]"
- `date_ingested` - When ingested (EST)
- `needs_ai` - True (for AI scoring)
- `fit_status` - "pending"
- `notes` - Provenance tracking
- `date_og_published` - Newsletter publication date

---

## Adding a New Newsletter

1. **Identify the newsletter's domain** (appears in Kill The Newsletter content)

2. **Add to `newsletter_extraction.py`:**
```python
NEWSLETTER_EXTRACTION_CONFIG = {
    # ... existing ...
    "newnewsletter.com": {
        "name": "New Newsletter",
        "extract_sections": ["News Section"],  # Or [] if extract_all
        "ignore_sections": ["Sponsors", "Jobs"],
        "extract_all": False  # Or True for all links
    },
}
```

3. **Add to `freshrss_client.py`:**
```python
NEWSLETTER_DOMAIN_TO_SOURCE = {
    # ... existing ...
    "newnewsletter.com": "New Newsletter",
}
```

4. **Set up email forwarding in Kill The Newsletter**

---

## Skipping a Newsletter

Add the domain to `SKIP_NEWSLETTERS` in `newsletter_extraction.py`:

```python
SKIP_NEWSLETTERS = [
    "theneurondaily.com",  # REMOVED - low quality
    "badnewsletter.com",   # Whatever reason
]
```

---

## Testing

1. Click the **"Newsletter Link Extraction"** button (third card) in the Sandbox dashboard
2. Check logs for:
   - `[NEWSLETTER EXTRACTION] Processing X newsletter articles`
   - `[Newsletter Extract] Extracted Y links from [Newsletter Name]`
   - `[Newsletter Extract] Created Z records from [Newsletter Name]`
3. Verify articles in Airtable have `notes` field populated
4. Verify no duplicates (pivot_id deduplication working)
5. Spot-check extracted URLs to confirm they're real news stories

**Note:** The regular "Ingest Articles" button does NOT process newsletters anymore.

---

## Expected Log Output

```
============================================================
[NEWSLETTER EXTRACTION] Processing 3 newsletter articles
============================================================
[Newsletter Extract] Processing The Deep View (thedeepview.co)
[Newsletter Extract] Extracted 5 links from The Deep View (filtered from 8 raw)
[Newsletter Extract] Created 5 records from The Deep View
[Newsletter Extract] Processing TLDR AI (tldr.tech)
[Newsletter Extract] Extracted 12 links from TLDR AI (filtered from 15 raw)
[Newsletter Extract] Created 12 records from TLDR AI

[NEWSLETTER EXTRACTION] Summary:
  Newsletter articles processed: 3
  Links extracted and created:   17
============================================================
```

---

## Related Files

| File | Purpose |
|------|---------|
| `workers/jobs/newsletter_extract_sandbox.py` | **Standalone newsletter extraction job** |
| `workers/config/newsletter_extraction.py` | Newsletter configs, blocked domains, patterns |
| `workers/config/freshrss_client.py` | Domain-to-source mappings |
| `workers/trigger.py` | Job routing (maps `newsletter_extract_sandbox` to job function) |
| `src/app/api/jobs/route.ts` | API route (validates `newsletter_extract_sandbox` step) |
| `src/app/(dashboard)/sandbox/page.tsx` | UI with third card for newsletter extraction |
| `docs/ai-ingestion-engine-step-0/Old-Article-Fix-1-2-26.md` | FreshRSS date filtering |
| `docs/ai-ingestion-engine/Google-News-Fix-12-27-25.md` | Google News URL decoding |

---

## Outstanding Items

### Newsletters to Add (Pending Confirmation)

| Newsletter | Email | Status |
|------------|-------|--------|
| Alpha Signal | news@alphasignal.ai | Need to confirm subscription |
| AI for Work | aiforwork@mail.beehiiv.com | Need to confirm subscription |
| Semi-Analysis | TBD | May require paid subscription |

### Manual Steps Required

1. **Kill The Newsletter email forwarding** - Add new newsletter emails to Kill The Newsletter
2. **Unsubscribe from The Neuron** - Remove from email forwarding

---

## References

- [Kill The Newsletter](https://kill-the-newsletter.com/) - Email to RSS conversion
- [Claude 3 Haiku](https://www.anthropic.com/claude) - LLM for extraction
- [FreshRSS API](https://freshrss.github.io/FreshRSS/en/) - RSS aggregation
