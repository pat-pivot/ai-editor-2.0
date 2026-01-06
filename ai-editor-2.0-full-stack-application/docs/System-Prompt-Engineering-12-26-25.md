# System Prompt Engineering - AI Editor 2.0

**Date:** December 26, 2025
**Status:** ✅ FIXED - Database prompts now wired to workers

---

## Executive Summary

The AI Editor 2.0 dashboard allows editing system prompts that are stored in PostgreSQL. As of December 26, 2025, **all 5 Pre-Filter batch methods in `gemini.py` now load prompts from the database** with a fallback to hardcoded prompts if the database prompt is missing.

**Editing a prompt in the dashboard WILL affect the next pipeline run.**

---

## n8n Workflow Reference

**Workflow ID:** `VoSZu0MIJAw1IuLL`
**Name:** STEP 1 AI Editor 2.0 - AI Editor Pre-Filter Cron

### Slot 1 Company Filter (Code-Based, Not AI)

The n8n workflow has a **code-based company filter** that runs IN PARALLEL with the Gemini Slot 1 Pre-Filter. This is NOT an LLM call - it's a simple keyword match:

```javascript
// n8n node: "Slot 1 Company Filter"
const slot1Companies = ['openai', 'google', 'meta', 'nvidia'];

const companyMatches = candidates.filter(story => {
  if (!story.eligible_slots?.includes(1)) return false;
  const headline = (story.headline || '').toLowerCase();
  return slot1Companies.some(company => headline.includes(company));
});

return companyMatches.map(s => ({
  json: {
    article_id: s.article_id,
    story_id: s.story_id,
    // ... fields
    reason: `Tier 1 company in headline: ${slot1Companies.find(c => (s.headline || '').toLowerCase().includes(c))}`
  }
}));
```

**Key Points:**
- Runs in PARALLEL with Gemini Slot 1 Pre-Filter
- Results are MERGED before writing to Airtable
- Only checks for 4 companies: `openai`, `google`, `meta`, `nvidia`
- This guarantees Tier 1 company stories get into Slot 1 even if Gemini misses them

### Python Implementation (Matches n8n)

Our Python worker (`workers/jobs/prefilter.py`) implements this identically:

```python
# Line 22-24
SLOT_1_COMPANIES = ['openai', 'google', 'meta', 'nvidia']

# Line 435-451
def _slot1_company_filter_batch(articles: List[Dict]) -> List[str]:
    """
    Slot 1 Company Filter - runs in PARALLEL with Gemini.
    Returns story_ids for articles with Tier 1 company names in headline.
    """
    matches = []
    for article in articles:
        headline = (article.get('headline') or '').lower()
        for company in SLOT_1_COMPANIES:
            if company in headline:
                matches.append(article['story_id'])
                break
    return matches
```

Results are merged at lines 212-218:
```python
# Slot 1 Company Filter (runs in parallel, merged with Gemini results)
slot1_company_matches = _slot1_company_filter_batch(slot_batches[1])

# Merge and dedupe
slot1_all = list(set(slot1_gemini_matches + slot1_company_matches))
```

---

## Gemini Pre-Filter Prompts (n8n Reference)

### Slot 1: Jobs/Economy
```
You are a pre-filter for an AI newsletter's lead story slot.

Review these candidates and identify ONLY stories about:
1. AI impact on JOBS (layoffs, hiring, workforce changes, labor market)
2. AI impact on ECONOMY (GDP, productivity, economic shifts, industry-wide effects)
3. AI STOCK MARKET / VALUATIONS (market moves, IPOs, funding rounds, earnings)
4. BROAD AI IMPACT (societal, regulatory, not company-specific product launches)

Please review all CANDIDATES here (each has an 'index' field - USE THIS INDEX IN YOUR RESPONSE):
{{ JSON.stringify($json.articles) }}

Return the story_id value for each matching article.
and then Return ONLY valid JSON:
{
  "matches": [
    {"story_id": "rec123ABC", "headline": "headline text"},
    {"story_id": "rec456DEF", "headline": "other headline"}
  ]
}
```

### Slot 2: Tier 1 / Insight
```
You are a pre-filter for Slot 2 (Tier 1 / Insight) of an AI newsletter.

Review these candidates and identify stories that fit ANY of these criteria:

1. TIER 1 AI COMPANIES: OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon
   - But NOT just a passing mention - the story should be PRIMARILY about the company
   - The list above is not exhaustive - use judgment for other major AI players

2. BROAD ECONOMIC THEMES related to AI, including but not limited to:
   - Industry-wide AI adoption
   - AI's impact on productivity, business operations
   - Economic shifts driven by AI

3. AI RESEARCH / INSIGHT PIECES, including but not limited to:
   - Studies, reports, analysis about AI trends
   - Not breaking news - thoughtful analysis
   - Adoption patterns, usage statistics, benchmarks
```

### Slot 3: Industry Impact
```
You are a pre-filter for Slot 3 (Industry Impact) of an AI newsletter.

Slot 3 focuses on how AI is impacting NON-TECH industries. Review these candidates and identify stories that fit:

**ELIGIBLE INDUSTRIES:** Healthcare, Government, Education, Legal, Accounting, Retail, Security, Transportation, Manufacturing, Real Estate, Agriculture, Energy

**WHAT TO LOOK FOR:**
- AI adoption in these industries
- AI impact on industry operations
- Regulatory changes affecting AI in these sectors
- Case studies of AI implementation

**Do NOT include:**
- Stories primarily about tech companies (those go to Slots 1-2)
- Stories about small/emerging AI startups (those go to Slot 4)
- Human interest / consumer AI stories (those go to Slot 5)
- Leadership shuffles
```

### Slot 4: Emerging Companies
```
You are a pre-filter for Slot 4 (Emerging Companies) of an AI newsletter.

Slot 4 focuses on smaller/emerging AI companies (NOT Tier 1 giants like OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon).

**WHAT TO LOOK FOR:**
- Product launches from emerging AI companies
- Big fundraising rounds (Series A, B, C, etc.)
- Acquisition news involving smaller players
- New AI tool/service launches
- Startup milestones and achievements

**Do NOT include:**
- Stories primarily about Tier 1 companies
- Industry-specific AI impact (those go to Slot 3)
- Human interest / consumer AI stories (those go to Slot 5)
- Leadership shuffles
```

### Slot 5: Consumer AI / Human Interest
```
You are a pre-filter for Slot 5 (Consumer AI / Human Interest) of an AI newsletter.

Slot 5 focuses on consumer-friendly AI stories - the "nice to know" pieces about AI's impact on everyday life.

**WHAT TO LOOK FOR:**
- AI's impact on humanity and society
- Consumer AI products and experiences
- AI in arts, entertainment, creativity
- AI ethics and philosophical questions
- Heartwarming or thought-provoking AI stories
- Fun, quirky, or surprising AI use cases

**Do NOT include:**
- Business/enterprise AI news (those go to Slots 1-4)
- Technical/developer focused stories
- Fundraising, acquisitions, corporate news
- Industry-specific B2B applications
- Leadership changes

**TONE:** "Nice to know" not "need to know"
```

---

## Architecture: How Prompts Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DASHBOARD (Frontend)                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │ Edit Prompt │───▶│ Save to API │───▶│ PostgreSQL  │          │
│  │     UI      │    │             │    │  Database   │          │
│  └─────────────┘    └─────────────┘    └──────┬──────┘          │
└────────────────────────────────────────────────┼────────────────┘
                                                 │
                                                 ▼
                         ┌─────────────────────────────────────────┐
                         │           gemini.py                      │
                         │  prefilter_batch_slot_X() methods        │
                         │                                          │
                         │  1. get_prompt('slot_X_prefilter')       │
                         │  2. If found: Use database prompt        │
                         │  3. If not: Use hardcoded fallback       │
                         │  4. Substitute {yesterday_headlines}     │
                         │     and {candidates} variables           │
                         └─────────────────────────────────────────┘
```

---

## Database Prompt Format

Prompts in the database use Python's `.format()` syntax. Required placeholders:

| Placeholder | Description |
|-------------|-------------|
| `{yesterday_headlines}` | Bulleted list of yesterday's 5 headlines |
| `{candidates}` | JSON array of candidate articles |

**Example:**
```
You are a pre-filter for Slot 1 (Jobs/Economy).

YESTERDAY'S HEADLINES (avoid similar topics):
{yesterday_headlines}

CANDIDATES:
{candidates}

Return ONLY valid JSON:
{{"matches": [{{"story_id": "recXXX", "headline": "..."}}]}}
```

**Note:** Double braces `{{` and `}}` are used for literal braces in the JSON response format.

---

## Prompt Keys

| Slot | Database Key | Step |
|------|--------------|------|
| 1 | `slot_1_prefilter` | 1 |
| 2 | `slot_2_prefilter` | 1 |
| 3 | `slot_3_prefilter` | 1 |
| 4 | `slot_4_prefilter` | 1 |
| 5 | `slot_5_prefilter` | 1 |

---

## Comparison: n8n vs Python Implementation

| Feature | n8n Workflow | Python Implementation |
|---------|--------------|----------------------|
| Architecture | 5 batch Gemini calls per slot | ✅ Matches |
| JSON article format | `JSON.stringify($json.articles)` | ✅ `json.dumps(articles, indent=2)` |
| Dynamic prompts | Edit in workflow nodes | ✅ **FIXED** - loads from database |
| Slot 1 Company Filter | 4 companies in parallel | ✅ Matches exactly |
| Freshness rules | Pre-calculated eligibility | ✅ Matches |
| Model | gemini-3-flash-preview | ✅ gemini-2.0-flash |

---

## Files Reference

| File | Purpose |
|------|---------|
| `workers/utils/gemini.py` | Gemini API client with batch prefilter methods |
| `workers/utils/prompts.py` | Database prompt loader |
| `workers/jobs/prefilter.py` | Step 1 job orchestration |
| `db/init.sql` | Database schema with system_prompts table |

---

## Changelog

- **Dec 26, 2025 (PM):** All 5 prefilter batch methods now load prompts from database with fallback
- **Dec 26, 2025 (AM):** Identified gap - prompts were hardcoded
- **Dec 24, 2025:** Initial prompt UI and API completed
