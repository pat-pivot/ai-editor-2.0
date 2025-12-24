# AI Editor 2.0 - Complete Implementation Guide

**Date:** December 24, 2025
**Status:** AUTHORITATIVE REFERENCE

---

## CRITICAL: This Document's Purpose

This document explains **exactly how the AI Editor 2.0 Python workers replicate n8n workflow logic without using n8n at all**.

The n8n workflows are **REFERENCE ONLY** - used to understand the logic, prompts, and data flow. The actual implementation is:
- **Next.js Dashboard** - Edit prompts, view pipeline status
- **PostgreSQL Database** - Store prompts with versioning
- **Python Workers (RQ)** - Execute pipeline logic (replaces n8n)
- **AI APIs** - Gemini and Claude for LLM calls
- **Airtable** - Article storage and pipeline state

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI Editor 2.0 Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐   │
│   │  Next.js Dashboard│────▶│   PostgreSQL     │◀────│  Python Workers  │   │
│   │   (Edit Prompts)  │     │   (Prompts DB)   │     │    (RQ Jobs)     │   │
│   └──────────────────┘     └──────────────────┘     └────────┬─────────┘   │
│                                                               │             │
│                                                               ▼             │
│                            ┌──────────────────┐     ┌──────────────────┐   │
│                            │     Airtable     │◀───▶│    AI APIs       │   │
│                            │ (Articles Data)  │     │ (Gemini/Claude)  │   │
│                            └──────────────────┘     └──────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Dashboard User** edits a system prompt
2. **Next.js API** saves prompt to PostgreSQL with version history
3. **Python Worker** loads prompt from database when job runs
4. **Worker** substitutes variables using Python f-strings
5. **Worker** calls AI API (Gemini or Claude) with the prompt
6. **Worker** writes results to Airtable

---

## Prompt Variable Substitution

### THE CRITICAL DIFFERENCE

| System | Syntax | Example |
|--------|--------|---------|
| n8n (REFERENCE ONLY) | `{{ $json.variable }}` | `{{ $json.headline }}` |
| Python Workers (ACTUAL) | `{variable}` | `{headline}` |

### How It Works in Python

```python
# 1. Load prompt from database
prompt_template = get_prompt('slot_1_prefilter')
# Returns: "Analyze this article:\nHeadline: {headline}\nContent: {content}..."

# 2. Substitute variables using Python string formatting
prompt = prompt_template.format(
    headline=article['headline'],
    content=article['content'],
    source=article['source'],
    date_published=article['date_published']
)

# 3. Send to AI API
response = gemini_client.generate(prompt)
```

### Worker Database Integration

```python
# workers/utils/prompts.py
import os
import psycopg2
from functools import lru_cache

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(DATABASE_URL)

def get_prompt(prompt_key: str) -> str:
    """
    Load current version of a prompt from the database.

    This is called by workers at runtime, so dashboard edits
    take effect on the next pipeline run.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pv.content
                FROM system_prompts sp
                JOIN system_prompt_versions pv ON sp.id = pv.prompt_id
                WHERE sp.prompt_key = %s AND pv.is_current = true
            """, (prompt_key,))
            row = cur.fetchone()
            if row:
                return row[0]
            raise ValueError(f"Prompt not found: {prompt_key}")
    finally:
        conn.close()

def get_slot_prompt(step: int, slot: int) -> str:
    """Get prompt for a specific step and slot."""
    prompt_key = f"slot_{slot}_{'prefilter' if step == 1 else 'agent'}"
    return get_prompt(prompt_key)
```

---

## Step 1: Pre-Filter

### n8n Reference
- Workflow: `VoSZu0MIJAw1IuLL`
- Node 13: Gemini Pre-Filter
- Processes articles in batches of 30

### Python Implementation

**File:** `workers/jobs/prefilter.py`

```python
from utils.prompts import get_prompt
from utils.gemini import gemini_generate
from utils.airtable import get_pending_articles, update_prefilter_result

def run_prefilter():
    """
    Step 1: Pre-filter articles using Gemini.

    For each article:
    1. Load prompt template from database
    2. Substitute article variables
    3. Call Gemini API
    4. Parse slot eligibility from response
    5. Update Airtable Pre-Filter Log
    """
    # Get articles from Airtable (Core URLs or RSS feed)
    articles = get_pending_articles(limit=30)

    # Load prompt template from database
    prompt_template = get_prompt('slot_1_prefilter')

    for article in articles:
        # Substitute variables using Python f-string formatting
        prompt = prompt_template.format(
            headline=article['headline'],
            content=article['content'],
            source=article['source'],
            credibility=article['credibility_score'],
            date_published=article['date_published'],
            hours_ago=calculate_hours_ago(article['date_published'])
        )

        # Call Gemini API
        response = gemini_generate(
            prompt=prompt,
            model='gemini-2.0-flash-exp',
            temperature=0.3
        )

        # Parse JSON response for slot eligibility
        result = parse_prefilter_response(response)

        # Update Airtable Pre-Filter Log
        update_prefilter_result(
            story_id=article['story_id'],
            eligible_slots=result['eligible_slots'],
            primary_slot=result['primary_slot'],
            reasoning=result['reasoning']
        )
```

### Database Prompt Format (slot_1_prefilter)

```
Analyze this news article and determine which newsletter slots it's eligible for.

ARTICLE:
Headline: {headline}
Summary: {content}
Published: {date_published}
Hours Old: {hours_ago}
Source: {source}
Source Credibility: {credibility}/5

SLOT CRITERIA:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market. Must be <24 hours old.
2. TIER 1 AI: OpenAI, Google, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon. Can be 24-48 hours old.
3. INDUSTRY IMPACT: Healthcare, Government, Education, Legal, etc. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, fun uses. Can be up to 7 days old.

Return JSON only:
{{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation"
}}
```

**Note:** Double braces `{{` and `}}` are used in the template for literal JSON braces, since single braces are for variable substitution.

---

## Step 2: Slot Selection

### n8n Reference
- Workflow: `SZmPztKNEmisG3Zf`
- 5 sequential Claude agents
- Cumulative tracking of selected stories

### Python Implementation

**File:** `workers/jobs/slot_selection.py`

```python
from utils.prompts import get_prompt
from utils.claude import claude_generate
from utils.airtable import get_slot_candidates, save_selected_story

def run_slot_selection():
    """
    Step 2: Sequential slot selection using Claude.

    Each slot agent:
    1. Loads its specific prompt from database
    2. Receives list of eligible candidates
    3. Knows which stories were already selected
    4. Selects the best story for its slot
    """
    selected_story_ids = []
    selected_companies = []
    selected_sources = []

    for slot in range(1, 6):
        # Get candidates for this slot from Pre-Filter Log
        candidates = get_slot_candidates(slot, exclude_ids=selected_story_ids)

        if not candidates:
            continue

        # Load slot-specific prompt from database
        prompt_template = get_prompt(f'slot_{slot}_agent')

        # Build candidates JSON for prompt
        candidates_json = format_candidates(candidates)

        # Substitute variables
        prompt = prompt_template.format(
            candidates=candidates_json,
            selected_stories=json.dumps(selected_story_ids),
            selected_companies=json.dumps(selected_companies),
            selected_sources=json.dumps(selected_sources),
            yesterday_slot=get_yesterday_slot(slot)
        )

        # Call Claude API
        response = claude_generate(
            prompt=prompt,
            model='claude-sonnet-4-20250514',
            temperature=0.7
        )

        # Parse selection
        result = parse_selection_response(response)

        # Track for subsequent slots
        selected_story_ids.append(result['selected_story_id'])
        selected_companies.append(result.get('company', ''))
        selected_sources.append(result.get('source', ''))

        # Save to Airtable Selected Slots
        save_selected_story(
            slot=slot,
            story_id=result['selected_story_id'],
            reasoning=result['reasoning']
        )

    # Generate subject line after all slots selected
    generate_subject_line(selected_story_ids)
```

### Database Prompt Format (slot_1_agent)

```
You are selecting the lead story for Slot 1 of the Pivot 5 AI newsletter.

SLOT 1 FOCUS: AI impact on JOBS, ECONOMY, and MARKETS
- Employment disruption or creation
- Stock market movements related to AI
- Economic policy and AI
- Workforce transformation

CANDIDATES:
{candidates}

ALREADY SELECTED STORIES: {selected_stories}
ALREADY SELECTED COMPANIES: {selected_companies}
ALREADY SELECTED SOURCES: {selected_sources}

YESTERDAY'S SLOT 1: {yesterday_slot}
(Avoid similar topics or sources)

SELECTION RULES:
- Cannot select a story already chosen for another slot
- Avoid repeating the same company twice in one issue
- Maximum 2 stories from the same source per issue
- Prioritize freshness (<24 hours for Slot 1)

Return JSON:
{{
  "selected_story_id": "...",
  "company": "Company name if applicable",
  "reasoning": "Brief explanation"
}}
```

---

## Step 3: Decoration

### n8n Reference
- Workflow: `HCbd2g852rkQgSqr`
- 4 sub-tasks: Clean → Decorate → Bold → Image

### Python Implementation

**File:** `workers/jobs/decoration.py`

```python
from utils.prompts import get_prompt
from utils.gemini import gemini_generate
from utils.claude import claude_generate
from utils.cloudflare import upload_image
from utils.airtable import get_selected_stories, update_decoration

def run_decoration():
    """
    Step 3: Decorate each selected story.

    For each of the 5 selected stories:
    1. Clean content (remove ads, etc.) - Gemini
    2. Generate headline + 3 bullets - Claude
    3. Apply bold formatting - Claude
    4. Generate image prompt - Claude
    5. Generate image - Gemini Imagen
    6. Upload to Cloudflare CDN
    7. Update Airtable Decoration table
    """
    stories = get_selected_stories()

    for story in stories:
        # Step 3a: Clean content using Gemini
        clean_prompt = get_prompt('content_cleaner').format(
            raw_content=story['raw_content']
        )
        cleaned_content = gemini_generate(clean_prompt, temperature=0.2)

        # Step 3b: Generate headline and bullets using Claude
        decorate_prompt = get_prompt('headline_generator').format(
            original_headline=story['headline'],
            content=cleaned_content,
            slot=story['slot']
        )
        decoration = claude_generate(decorate_prompt)
        decoration_data = json.loads(decoration)

        # Step 3c: Generate bullets
        bullet_prompt = get_prompt('bullet_generator').format(
            headline=decoration_data['headline'],
            content=cleaned_content
        )
        bullets = json.loads(claude_generate(bullet_prompt))

        # Step 3d: Apply bold formatting
        bold_prompt = get_prompt('bold_formatter').format(
            bullets=json.dumps(bullets['bullets'])
        )
        formatted_bullets = json.loads(claude_generate(bold_prompt))

        # Step 3e: Generate image prompt
        image_prompt_template = get_prompt('image_prompt').format(
            headline=decoration_data['headline'],
            summary=cleaned_content[:500],
            slot=story['slot']
        )
        image_prompt_data = json.loads(claude_generate(image_prompt_template))

        # Step 3f: Generate image using Gemini Imagen
        image_url = generate_and_upload_image(
            prompt=image_prompt_data['image_prompt'],
            story_id=story['story_id']
        )

        # Step 3g: Update Airtable Decoration table
        update_decoration(
            story_id=story['story_id'],
            headline=decoration_data['headline'],
            b1=formatted_bullets['formatted_bullets'][0],
            b2=formatted_bullets['formatted_bullets'][1],
            b3=formatted_bullets['formatted_bullets'][2],
            image_url=image_url,
            image_status='complete'
        )
```

---

## Step 4: HTML Compile

### n8n Reference
- Workflow: `NKjC8hb0EDHIXx3U`
- Compiles 5 decorated stories into HTML email

### Python Implementation

**File:** `workers/jobs/html_compile.py`

```python
from utils.prompts import get_prompt
from utils.claude import claude_generate
from utils.airtable import get_decorated_stories, create_newsletter_issue
from utils.mautic import create_email_campaign

def run_html_compile():
    """
    Step 4: Compile newsletter HTML and create Mautic campaign.

    1. Fetch all 5 decorated stories
    2. Generate 15-word summary
    3. Build HTML from template
    4. Create Mautic email campaign
    """
    stories = get_decorated_stories()

    # Generate summary using Claude
    summary_prompt = get_prompt('summary_generator').format(
        slot1_headline=stories[0]['headline'],
        slot2_headline=stories[1]['headline'],
        slot3_headline=stories[2]['headline'],
        slot4_headline=stories[3]['headline'],
        slot5_headline=stories[4]['headline']
    )
    summary_data = json.loads(claude_generate(summary_prompt))

    # Build HTML from template
    html_content = build_newsletter_html(
        stories=stories,
        summary=summary_data['summary'],
        subject_line=get_today_subject_line()
    )

    # Create Mautic campaign
    campaign_id = create_email_campaign(
        subject=get_today_subject_line(),
        preview_text=summary_data['summary'],
        html_content=html_content
    )

    # Record in Airtable
    create_newsletter_issue(
        date=today(),
        subject=get_today_subject_line(),
        summary=summary_data['summary'],
        mautic_campaign_id=campaign_id,
        status='ready_to_send'
    )
```

---

## Step 5: Send & Archive

### n8n Reference
- Workflow: `I8U8LgJVDsO8PeBJ`
- Triggers Mautic send
- Archives to social posts table

### Python Implementation

**File:** `workers/jobs/mautic_send.py`

```python
from utils.mautic import send_campaign, get_campaign_stats
from utils.airtable import update_issue_status, create_social_posts

def run_send_and_archive():
    """
    Step 5: Send newsletter via Mautic and archive for social.

    1. Trigger Mautic campaign send
    2. Wait for send completion
    3. Archive stories to P5 Social Posts table
    """
    issue = get_ready_issue()

    # Send via Mautic
    send_result = send_campaign(issue['mautic_campaign_id'])

    # Update status
    update_issue_status(
        issue_id=issue['issue_id'],
        status='sent',
        sent_at=datetime.now()
    )

    # Archive to social posts table for downstream automation
    stories = get_issue_stories(issue['issue_id'])
    for story in stories:
        create_social_posts(
            story_id=story['story_id'],
            headline=story['headline'],
            bullets=[story['b1'], story['b2'], story['b3']],
            image_url=story['image_url'],
            issue_date=issue['date']
        )
```

---

## Prompt Database Schema

### Tables

```sql
-- Main prompts table
CREATE TABLE system_prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_key VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'slot_1_prefilter'
    step_id INTEGER NOT NULL,                  -- 1-5
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model VARCHAR(100) NOT NULL,               -- 'gemini-2.0-flash-exp' or 'claude-sonnet-4'
    temperature DECIMAL(3,2) DEFAULT 0.7,
    slot_number INTEGER,                       -- 1-5 for slot-specific prompts
    is_active BOOLEAN DEFAULT true,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Version history (enables rollback)
CREATE TABLE system_prompt_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID REFERENCES system_prompts(id),
    version INTEGER NOT NULL,
    content TEXT NOT NULL,                     -- The actual prompt text
    change_summary TEXT,
    created_by_email VARCHAR(255),
    is_current BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Dashboard → Database → Worker Flow

```
┌─────────────────┐
│ Dashboard User  │
│ edits prompt    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ POST /api/prompts│
│ updates database │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ New version     │
│ created in      │
│ prompt_versions │
│ is_current=true │
└────────┬────────┘
         │
         │  (Next scheduled run)
         ▼
┌─────────────────┐
│ Python Worker   │
│ calls get_prompt│
│ loads current   │
│ version         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Worker uses     │
│ updated prompt  │
│ in pipeline     │
└─────────────────┘
```

---

## All 17 Prompts

| Step | Prompt Key | Model | Purpose | Variables |
|------|------------|-------|---------|-----------|
| 1 | `slot_1_prefilter` | Gemini | Jobs/Economy eligibility | `{headline}`, `{content}`, `{source}`, `{credibility}`, `{hours_ago}` |
| 1 | `slot_2_prefilter` | Gemini | Tier 1 AI eligibility | Same as above |
| 1 | `slot_3_prefilter` | Gemini | Industry eligibility | Same as above |
| 1 | `slot_4_prefilter` | Gemini | Emerging Tech eligibility | Same as above |
| 1 | `slot_5_prefilter` | Gemini | Consumer AI eligibility | Same as above |
| 2 | `slot_1_agent` | Claude | Select Slot 1 story | `{candidates}`, `{selected_stories}`, `{yesterday_slot}` |
| 2 | `slot_2_agent` | Claude | Select Slot 2 story | Same as above |
| 2 | `slot_3_agent` | Claude | Select Slot 3 story | Same as above |
| 2 | `slot_4_agent` | Claude | Select Slot 4 story | Same as above |
| 2 | `slot_5_agent` | Claude | Select Slot 5 story | Same as above |
| 2 | `subject_line` | Claude | Generate email subject | `{slot1_headline}`, `{slot2_headline}`, etc. |
| 3 | `content_cleaner` | Gemini | Clean article content | `{raw_content}` |
| 3 | `headline_generator` | Claude | Generate newsletter headline | `{original_headline}`, `{content}`, `{slot}` |
| 3 | `bullet_generator` | Claude | Generate 3 bullet points | `{headline}`, `{content}` |
| 3 | `bold_formatter` | Claude | Apply bold formatting | `{bullets}` |
| 3 | `image_prompt` | Claude | Generate image prompt | `{headline}`, `{summary}`, `{slot}` |
| 4 | `summary_generator` | Claude | 15-word email preview | `{slot1_headline}` through `{slot5_headline}` |

---

## Airtable Tables

| Table | Table ID | Purpose |
|-------|----------|---------|
| Pre-Filter Log | `tbl72YMsm9iRHj3sp` | Raw articles with slot eligibility |
| Selected Slots | `tblzt2z7r512Kto3O` | Final 5 selected stories per issue |
| Decoration | `tbla16LJCf5Z6cRn3` | Decorated stories with headlines, bullets, images |
| Articles | `tblGumae8KDpsrWvh` | Source articles |
| P5 Social Posts | TBD | Archived for social automation |

### Key Field Names

**Pre-Filter Log:**
- `storyID`, `pivotId`, `headline`, `core_url`, `source_id`
- `date_og_published`, `date_prefiltered`, `slot`

**Decoration:**
- `story_id`, `slot_order`, `headline`, `label`
- `b1`, `b2`, `b3`, `ai_dek`
- `image_url`, `image_status`, `social_status`, `pivotnews_url`

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# AI APIs
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=...

# Airtable
AIRTABLE_API_KEY=pat...
AIRTABLE_BASE_ID=app...

# Cloudflare (for images)
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...

# Mautic
MAUTIC_BASE_URL=https://...
MAUTIC_USERNAME=...
MAUTIC_PASSWORD=...

# Redis (for job queue)
REDIS_URL=redis://...
```

---

## Summary

**The AI Editor 2.0 Python workers completely replace n8n** by:

1. **Storing prompts in PostgreSQL** - Editable from the dashboard
2. **Loading prompts at runtime** - Workers call `get_prompt()` from database
3. **Using Python f-string substitution** - `{variable}` syntax, not n8n syntax
4. **Calling AI APIs directly** - Gemini and Claude via Python SDKs
5. **Managing state in Airtable** - Same tables as n8n used

When a user edits a prompt in the dashboard, the change is saved to the database. The next time a worker runs, it loads the updated prompt and uses it in the pipeline.

**n8n is never used in production.** It was only used as a reference to understand the pipeline logic.
