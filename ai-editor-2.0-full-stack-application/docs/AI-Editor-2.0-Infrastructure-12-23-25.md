# AI Editor 2.0 Infrastructure Documentation

**Document:** AI-Editor-2.0-Infrastructure-12-23-25.md
**Date:** December 23, 2025
**Purpose:** Complete node-by-node analysis of all 5 AI Editor workflow pipelines

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Airtable Database Architecture](#airtable-database-architecture)
3. [Step 1: Pre-Filter Workflow](#step-1-pre-filter-workflow)
4. [Step 2: Slot Agent Selection Workflow](#step-2-slot-agent-selection-workflow)
5. [Step 3: Decoration Workflow](#step-3-decoration-workflow)
6. [Step 4: HTML Compile and Send Workflow](#step-4-html-compile-and-send-workflow)
7. [Step 5: Social Post Trigger Workflow](#step-5-social-post-trigger-workflow)
8. [Complete Data Flow Diagram](#complete-data-flow-diagram)
9. [Cron Schedule Summary](#cron-schedule-summary)
10. [API Credentials Reference](#api-credentials-reference)

---

## System Overview

The AI Editor 2.0 pipeline consists of **5 sequential n8n workflows** that orchestrate the daily Pivot 5 newsletter production:

| Step | Workflow Name | Workflow ID | Purpose |
|------|---------------|-------------|---------|
| 1 | AI Editor Pre-Filter Cron | `VoSZu0MIJAw1IuLL` | Filter articles into 5 slot categories |
| 2 | AI Editor Slot Agent Selects | `SZmPztKNEmisG3Zf` | AI agents select one story per slot |
| 3 | AI Editor Decoration | `HCbd2g852rkQgSqr` | Generate headlines, bullets, and images |
| 4 | Compile HTML and Send | `NKjC8hb0EDHIXx3U` | Build email HTML and send via Mautic |
| 5 | Airtable Social Post Trigger | `I8U8LgJVDsO8PeBJ` | Syndicate to social media queue |

### AI Models Used

| Model | Provider | Purpose |
|-------|----------|---------|
| `gemini-3-flash-preview` | Google | Pre-filtering articles into slots, content cleaning |
| `claude-sonnet-4-5-20250929` | Anthropic | Slot agent selection, content decoration |
| `gemini-3-pro-image-preview` | Google | Image generation (primary) |
| `gpt-image-1.5` | OpenAI | Image generation (fallback) |

---

## Airtable Database Architecture

### Base: Pivot 5 AI Editor 2.0
**Base ID:** `appglKSJZxmA9iHpl`

| Table | Table ID | Purpose |
|-------|----------|---------|
| AI Editor - Pre-Filter Log | `tbl72YMsm9iRHj3sp` | Stores pre-filtered candidates per slot |
| AI Editor - Selected Slots | `tblzt2z7r512Kto3O` | Daily issue with 5 selected stories |
| Newsletter Issue Stories (Decoration) | `tbla16LJCf5Z6cRn3` | Decorated stories with AI content |
| Source Credibility | `tbl3Zkdl1No2edDLK` | Source ratings (1-5 scale) |
| AI Editor - Queued Stories | `tblN1RypWAOBMOfQ5` | Manually queued priority stories |

### Base: Pivot Media Master
**Base ID:** `appwSozYTkrsQWUXB`

| Table | Table ID | Purpose |
|-------|----------|---------|
| Articles | `tblGumae8KDpsrWvh` | Raw ingested articles with markdown |
| Newsletter Stories | `tblY78ziWp5yhiGXp` | Stories with basic AI decoration |
| Newsletter Issues | `tbl7mcCCGbjEfli25` | Compiled newsletter HTML |
| Newsletter Issues Archive | `tblHo0xNj8nbzMHNI` | Sent newsletter archive |

### Base: P5 Social Posts
**Base ID:** `appRUgK44hQnXH1PM`

| Table | Table ID | Purpose |
|-------|----------|---------|
| P5 Social Posts | `tbllJMN2QBPJoG3jA` | Social media content queue |

---

## Step 1: Pre-Filter Workflow

**Workflow Name:** STEP 1 AI Editor 2.0 - AI Editor Pre-Filter Cron
**Workflow ID:** `VoSZu0MIJAw1IuLL`
**Total Nodes:** 27
**Schedule:** `0 2 * * 2-6` (9:00 PM ET, Monday-Friday)

### Purpose
Filters candidate articles from the past 7 days into 5 newsletter slots based on content relevance, freshness, and source credibility using Google Gemini AI.

### Slot Eligibility Criteria

| Slot | Focus | Freshness Window |
|------|-------|------------------|
| 1 | AI impact on jobs, economy, stock market, broad societal impact | 0-24 hours |
| 2 | Tier 1 AI companies (OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon) + economic themes + research | 24-48 hours |
| 3 | Industry impact (Healthcare, Government, Education, Legal, Manufacturing, etc.) | 0-7 days |
| 4 | Emerging companies (product launches, fundraising, acquisitions, new AI tools) | 0-48 hours |
| 5 | Consumer AI / human interest (ethics, entertainment, societal impact, fun uses) | 0-7 days |

---

### Node-by-Node Analysis

#### Node 1: Schedule Trigger
**Node ID:** `schedule-trigger`
**Type:** `n8n-nodes-base.scheduleTrigger`
**Version:** 1.2
**Position:** [-1808, 464]

**Configuration:**
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "0 2 * * 2-6"
      }
    ]
  }
}
```

**Purpose:** Triggers the workflow at 9:00 PM ET Monday-Friday.

**Output:** Timestamp trigger event → Connects to "Get Newsletter Stories"

---

#### Node 2: Get Newsletter Stories
**Node ID:** `get-newsletter-stories`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1600, 464]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tblY78ziWp5yhiGXp` (Newsletter Stories)
- **Operation:** List records

**Filter Formula:**
```
AND(
  IS_AFTER({date_og_published}, DATEADD(TODAY(), -7, 'days')),
  {newsletter}='pivot_ai'
)
```

**Fields Retrieved:**
| Field | Type | Description |
|-------|------|-------------|
| storyID | Text | Unique story identifier |
| pivotId | Text | Link to Articles table |
| ai_headline | Text | AI-generated headline |
| date_og_published | DateTime | Original publication date |
| newsletter | Select | Newsletter type (pivot_ai) |

**Output:** Array of candidate stories → Connects to "Prepare Candidates"

---

#### Node 3: Get Queued Stories
**Node ID:** `get-queued-stories`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1600, 240]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblN1RypWAOBMOfQ5` (Queued Stories)
- **Operation:** List records

**Filter Formula:**
```
{status}='pending'
```

**Fields Retrieved:**
| Field | Type | Description |
|-------|------|-------------|
| storyID | Text | Story identifier |
| pivotId | Text | Link to Articles |
| headline | Text | Story headline |
| slot | Number | Target slot (1-5) |
| status | Select | Queue status |

**Purpose:** Retrieves manually queued priority stories that should be considered for specific slots.

**Output:** Queued stories → Connects to "Prepare Candidates"

---

#### Node 4: Get Yesterday's Issue
**Node ID:** `get-yesterday-issue`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1600, 688]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)
- **Operation:** List records

**Filter Formula:**
```
IS_AFTER({issue_date}, DATEADD(TODAY(), -14, 'days'))
```

**Sort:** `issue_date` DESC
**Max Records:** 5

**Fields Retrieved:**
| Field | Type | Description |
|-------|------|-------------|
| issue_id | Text | Issue identifier |
| issue_date | Date | Issue date |
| slot_1_storyId through slot_5_storyId | Text | Previously selected story IDs |
| slot_1_headline through slot_5_headline | Text | Previous headlines |

**Purpose:** Retrieves last 14 days of issues to prevent story repetition.

**Output:** Previous issues → Connects to "Prepare Candidates"

---

#### Node 5: Get Source Scores
**Node ID:** `get-source-scores`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1600, 912]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbl3Zkdl1No2edDLK` (Source Credibility)
- **Operation:** List records

**Fields Retrieved:**
| Field | Type | Description |
|-------|------|-------------|
| source_name | Text | Publisher/source name |
| credibility_score | Number | Rating 1-5 (5 = highest) |

**Purpose:** Retrieves source credibility scores for weighting article selection.

**Output:** Source scores lookup → Connects to "Prepare Candidates"

---

#### Node 6: Get Articles for Source Lookup
**Node ID:** `get-articles-source`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1600, 1136]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tblGumae8KDpsrWvh` (Articles)
- **Operation:** List records

**Filter Formula:**
```
IS_AFTER({date_published}, DATEADD(TODAY(), -7, 'days'))
```

**Fields Retrieved:**
| Field | Type | Description |
|-------|------|-------------|
| pivot_Id | Text | Article identifier |
| source_id | Text | Publisher name |
| original_url | Text | Article URL |
| date_published | DateTime | Publication date |

**Purpose:** Provides source_id and original_url for each candidate article.

**Output:** Article metadata → Connects to "Aggregate Articles"

---

#### Node 7: Aggregate Articles
**Node ID:** `aggregate-articles`
**Type:** `n8n-nodes-base.aggregate`
**Version:** 1
**Position:** [-1376, 1136]

**Configuration:**
```json
{
  "aggregate": "aggregateAllItemData",
  "destinationFieldName": "articles_lookup"
}
```

**Purpose:** Aggregates all article records into a single lookup object for efficient source_id matching.

**Output:** Aggregated articles → Connects to "Prepare Candidates"

---

#### Node 8: Prepare Candidates
**Node ID:** `prepare-candidates`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-1152, 464]

**JavaScript Code:**
```javascript
// Merges stories with source scores and article metadata
// Calculates freshness scores based on publication date
// Filters out previously selected stories
// Enriches each story with:
//   - source_id (from Articles lookup)
//   - original_url (from Articles lookup)
//   - credibility_score (from Source Scores)
//   - hours_old (calculated from date_og_published)

const stories = $('Get Newsletter Stories').all();
const queued = $('Get Queued Stories').all();
const previousIssues = $('Get Yesterday\'s Issue').all();
const sourceScores = $('Get Source Scores').all();
const articlesLookup = $('Aggregate Articles').first().json.articles_lookup;

// Build previously selected story IDs set
const previouslySelected = new Set();
previousIssues.forEach(issue => {
  for (let i = 1; i <= 5; i++) {
    const storyId = issue.json.fields[`slot_${i}_storyId`];
    if (storyId) previouslySelected.add(storyId);
  }
});

// Build source score lookup
const scoreMap = {};
sourceScores.forEach(s => {
  scoreMap[s.json.fields.source_name] = s.json.fields.credibility_score || 3;
});

// Enrich and filter stories
return stories
  .filter(story => !previouslySelected.has(story.json.fields.storyID))
  .map(story => {
    const pivotId = story.json.fields.pivotId;
    const article = articlesLookup.find(a => a.pivot_Id === pivotId);
    const hoursOld = (Date.now() - new Date(story.json.fields.date_og_published)) / 3600000;

    return {
      json: {
        ...story.json,
        source_id: article?.source_id || 'Unknown',
        original_url: article?.original_url || '',
        credibility_score: scoreMap[article?.source_id] || 3,
        hours_old: Math.round(hoursOld)
      }
    };
  });
```

**Output:** Enriched candidates → Connects to 5 parallel slot pre-filter nodes

---

#### Nodes 9-13: Slot Pre-Filter (Slots 1-5)
**Node Type:** `@n8n/n8n-nodes-langchain.chainLlm`
**Version:** 1.4

Each slot has its own pre-filter node that uses Google Gemini to evaluate article eligibility.

##### Slot 1 Pre-Filter
**Node ID:** `slot-1-prefilter`
**Position:** [-928, 0]

**AI Model Configuration:**
- **Model:** `models/gemini-3-flash-preview`
- **Temperature:** 0.3

**System Prompt:**
```
You are an AI news editor for Pivot 5, a daily AI newsletter.

SLOT 1 CRITERIA:
- Focus: AI impact on jobs, economy, stock market, broad societal impact
- Freshness: Must be published within last 24 hours
- Priority: Major announcements affecting general public

Evaluate each article and return JSON:
{
  "eligible": true/false,
  "reason": "Brief explanation",
  "relevance_score": 1-10
}
```

**Input:** Candidate stories with hours_old < 24

**Output:** Eligible stories for Slot 1 → Connects to "Filter Slot 1 Eligible"

##### Slot 2 Pre-Filter
**Node ID:** `slot-2-prefilter`
**Position:** [-928, 224]

**System Prompt Focus:**
- Tier 1 AI companies: OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon
- Economic themes, research papers
- Freshness: 24-48 hours

##### Slot 3 Pre-Filter
**Node ID:** `slot-3-prefilter`
**Position:** [-928, 448]

**System Prompt Focus:**
- Industry verticals: Healthcare, Government, Education, Legal, Accounting, Retail, Security, Transportation, Manufacturing, Real Estate, Agriculture, Energy
- Freshness: 0-7 days

##### Slot 4 Pre-Filter
**Node ID:** `slot-4-prefilter`
**Position:** [-928, 672]

**System Prompt Focus:**
- Emerging AI companies
- Product launches, fundraising, acquisitions
- New AI tools and startups
- Freshness: 0-48 hours

##### Slot 5 Pre-Filter
**Node ID:** `slot-5-prefilter`
**Position:** [-928, 896]

**System Prompt Focus:**
- Consumer AI, human interest
- AI ethics, entertainment, societal impact
- Fun/quirky AI uses
- Freshness: 0-7 days

---

#### Nodes 14-18: Filter Slot Eligible (Slots 1-5)
**Node Type:** `n8n-nodes-base.filter`
**Version:** 2

Each filter node processes the Gemini response and keeps only eligible articles.

**Example Filter Configuration (Slot 1):**
```json
{
  "conditions": {
    "conditions": [
      {
        "leftValue": "={{ $json.eligible }}",
        "rightValue": true,
        "operator": {
          "type": "boolean",
          "operation": "equals"
        }
      }
    ]
  }
}
```

**Output:** Filtered eligible stories → Connects to corresponding "Write Slot X Log" node

---

#### Nodes 19-23: Write Slot Log (Slots 1-5)
**Node Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Operation:** Create records

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbl72YMsm9iRHj3sp` (Pre-Filter Log)

**Column Mapping:**
| Airtable Field | Source Expression | Description |
|----------------|-------------------|-------------|
| storyID | `{{ $json.fields.storyID }}` | Story identifier |
| pivotId | `{{ $json.fields.pivotId }}` | Link to Articles |
| headline | `{{ $json.fields.ai_headline }}` | Story headline |
| original_url | `{{ $json.original_url }}` | Article URL |
| source_id | `{{ $json.source_id }}` | Publisher name |
| date_og_published | `{{ $json.fields.date_og_published }}` | Original pub date |
| date_prefiltered | `{{ $now.toISO() }}` | Pre-filter timestamp |
| slot | `1` / `2` / `3` / `4` / `5` | Slot number (hardcoded per node) |

**Purpose:** Creates one record per eligible story per slot in the Pre-Filter Log table.

---

### Step 1 Data Flow Summary

```
Schedule Trigger (9 PM EST)
       │
       ├── Get Newsletter Stories (7-day window)
       ├── Get Queued Stories (status='pending')
       ├── Get Yesterday's Issue (14-day window)
       ├── Get Source Scores (all sources)
       └── Get Articles (7-day window)
              │
              ▼
       Aggregate Articles
              │
              ▼
       Prepare Candidates (merge, enrich, filter)
              │
       ┌──────┼──────┬──────┬──────┐
       ▼      ▼      ▼      ▼      ▼
    Slot 1  Slot 2  Slot 3  Slot 4  Slot 5
   Pre-Filter (Gemini AI for each slot)
       │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼
   Filter  Filter  Filter  Filter  Filter
   Eligible Eligible Eligible Eligible Eligible
       │      │      │      │      │
       ▼      ▼      ▼      ▼      ▼
    Write   Write   Write   Write   Write
    Slot 1  Slot 2  Slot 3  Slot 4  Slot 5
     Log     Log     Log     Log     Log
       │      │      │      │      │
       └──────┴──────┴──────┴──────┘
                     │
                     ▼
            Pre-Filter Log Table
            (tbl72YMsm9iRHj3sp)
```

---

## Step 2: Slot Agent Selection Workflow

**Workflow Name:** STEP 2 - AI Editor Slot Agent Selects
**Workflow ID:** `SZmPztKNEmisG3Zf`
**Total Nodes:** 30
**Schedule:** `15 2 * * 2-6` (9:15 PM ET, Monday-Friday)

### Purpose
Five sequential Claude AI agents each select the best story for their assigned slot, with cumulative tracking of selected companies, sources, and story IDs to enforce editorial diversity rules.

### Editorial Diversity Rules

1. **Yesterday's Headlines:** Don't select stories covering same topics as yesterday's issue
2. **No Repeat Companies:** Each company appears at most once across all 5 slots
3. **Source Diversity:** Maximum 2 stories per source per day
4. **No Duplicate Stories:** Don't select storyIDs already chosen in earlier slots today
5. **Slot 1 Two-Day Rule:** Slot 1 company can't repeat yesterday's Slot 1 company

---

### Node-by-Node Analysis

#### Node 1: Schedule Trigger
**Node ID:** `schedule-trigger`
**Type:** `n8n-nodes-base.scheduleTrigger`
**Version:** 1.2
**Position:** [-1920, 256]

**Configuration:**
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "15 2 * * 2-6"
      }
    ]
  }
}
```

**Purpose:** Triggers workflow at 9:15 PM ET Monday-Friday (15 minutes after pre-filter completes).

**Output:** → Connects to "Pull Yesterday Issue"

---

#### Node 2: Pull Yesterday Issue
**Node ID:** `pull-yesterday-issue`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1696, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)
- **Operation:** List records
- **Sort:** `issue_date` DESC
- **Max Records:** 1

**Fields Retrieved:**
| Field | Type | Purpose |
|-------|------|---------|
| issue_date | Date | Yesterday's date |
| slot_1_headline | Text | For topic avoidance |
| slot_1_storyId | Text | For company extraction |
| slot_2_headline through slot_5_headline | Text | Topic context |
| slot_2_storyId through slot_5_storyId | Text | Previously used |

**Output:** Yesterday's issue data → Connects to all 5 "Pull Slot X Candidates" nodes

---

#### Nodes 3-7: Pull Slot Candidates (Slots 1-5)
**Node Type:** `n8n-nodes-base.airtable`
**Version:** 2.1

Each node pulls pre-filtered candidates for its specific slot.

##### Pull Slot 1 Candidates
**Node ID:** `pull-slot-1-candidates`
**Position:** [-1472, 0]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbl72YMsm9iRHj3sp` (Pre-Filter Log)

**Filter Formula:**
```
AND(
  {slot}=1,
  IS_AFTER({date_prefiltered}, DATEADD(TODAY(), -1, 'days'))
)
```

**Sort:** `date_og_published` DESC

**Fields Retrieved:**
| Field | Type |
|-------|------|
| storyID | Text |
| pivotId | Text |
| headline | Text |
| original_url | Text |
| source_id | Text |
| date_og_published | DateTime |

##### Pull Slot 2-5 Candidates
Similar configuration with `{slot}=2`, `{slot}=3`, etc.

**Freshness Filters by Slot:**
- Slot 1: Last 1 day
- Slot 2: Last 2 days
- Slot 3: Last 7 days
- Slot 4: Last 2 days
- Slot 5: Last 7 days

---

#### Nodes 8-12: Merge Slot Inputs (Slots 1-5)
**Node Type:** `n8n-nodes-base.merge`
**Version:** 3

Each merge node combines:
1. Slot candidates from Pre-Filter Log
2. Yesterday's issue (for context)
3. Previously selected stories from earlier slots (cumulative tracking)

**Purpose:** Provides complete context for each slot agent.

---

#### Nodes 13-17: Prepare Slot Context (Slots 1-5)
**Node Type:** `n8n-nodes-base.code`
**Version:** 2

##### Prepare Slot 1 Context
**Node ID:** `prepare-slot-1-context`
**Position:** [-1024, 0]

**JavaScript Code:**
```javascript
const candidates = $('Pull Slot 1 Candidates').all();
const yesterday = $('Pull Yesterday Issue').first();

// Extract yesterday's headlines for topic avoidance
const yesterdayHeadlines = [];
for (let i = 1; i <= 5; i++) {
  const headline = yesterday?.json?.fields?.[`slot_${i}_headline`];
  if (headline) yesterdayHeadlines.push(headline);
}

// Extract yesterday's Slot 1 company for 2-day rotation rule
const slot1Company = yesterday?.json?.fields?.slot_1_storyId || '';

return [{
  json: {
    candidates: candidates.map(c => ({
      storyID: c.json.fields.storyID,
      pivotId: c.json.fields.pivotId,
      headline: c.json.fields.headline,
      source_id: c.json.fields.source_id,
      original_url: c.json.fields.original_url,
      date_og_published: c.json.fields.date_og_published
    })),
    yesterdayHeadlines,
    slot1Company,
    selectedToday: [],
    selectedCompanies: [],
    selectedSources: []
  }
}];
```

##### Prepare Slot 2-5 Context
Each subsequent slot context includes cumulative tracking from previous slots:
- `selectedToday`: Array of storyIDs already selected
- `selectedCompanies`: Array of companies already featured
- `selectedSources`: Array of sources already used

---

#### Nodes 18-22: Slot Agent (Slots 1-5)
**Node Type:** `@n8n/n8n-nodes-langchain.agent`
**Version:** 1.7

**AI Model Configuration:**
- **Model:** `claude-sonnet-4-5-20250929`
- **Temperature:** 0.5
- **Max Tokens:** 2000

##### Slot 1 Agent
**Node ID:** `slot-1-agent`
**Position:** [-800, 0]

**System Prompt:**
```
You are the Slot 1 Editor for Pivot 5, a daily AI newsletter.

SLOT 1 FOCUS: AI impact on jobs, economy, stock market, broad societal impact

YOUR TASK:
Select the BEST story from the candidates for Slot 1.

RULES:
1. Story must be published within last 24 hours
2. Story must NOT cover same topic as yesterday's headlines
3. Company featured must NOT be yesterday's Slot 1 company (2-day rotation)
4. Prioritize high credibility sources
5. Choose stories with broad appeal and clear impact

YESTERDAY'S HEADLINES (avoid these topics):
{{ $json.yesterdayHeadlines.join('\n') }}

YESTERDAY'S SLOT 1 COMPANY (cannot repeat):
{{ $json.slot1Company }}

CANDIDATES:
{{ JSON.stringify($json.candidates, null, 2) }}

Return your selection as JSON:
{
  "selected_storyId": "story_id_here",
  "selected_headline": "headline_here",
  "selected_pivotId": "pivot_id_here",
  "reasoning": "Why you selected this story",
  "company": "Primary company mentioned (for tracking)"
}
```

##### Slot 2-5 Agents
Each agent has slot-specific focus criteria and receives cumulative tracking data:

**Slot 2 Agent Focus:**
- Tier 1 AI companies
- Economic themes, research
- 24-48 hour freshness

**Slot 3 Agent Focus:**
- Industry verticals
- Healthcare, Government, Education, etc.
- 0-7 day freshness

**Slot 4 Agent Focus:**
- Emerging AI companies
- Product launches, fundraising
- 0-48 hour freshness

**Slot 5 Agent Focus:**
- Consumer AI, human interest
- Ethics, entertainment, quirky uses
- 0-7 day freshness

---

#### Nodes 23-27: Remove Slot Stories (Slots 1-5)
**Node Type:** `n8n-nodes-base.code`
**Version:** 2

Each node processes the agent's selection and updates cumulative tracking.

##### Remove Slot 1 Stories
**Node ID:** `remove-slot-1-stories`
**Position:** [-576, 0]

**JavaScript Code:**
```javascript
const selection = $('Slot 1 Agent').first().json;
const context = $('Prepare Slot 1 Context').first().json;

// Add selected story to tracking
const selectedToday = [selection.selected_storyId];
const selectedCompanies = [selection.company];
const selectedSources = [selection.source_id];

// Remove selected story from remaining candidates
const remainingCandidates = context.candidates.filter(
  c => c.storyID !== selection.selected_storyId
);

return [{
  json: {
    slot1Selection: selection,
    remainingCandidates,
    selectedToday,
    selectedCompanies,
    selectedSources,
    yesterdayHeadlines: context.yesterdayHeadlines
  }
}];
```

**Output:** Updated tracking → Connects to "Prepare Slot 2 Context"

---

#### Node 28: Assembly Code
**Node ID:** `assembly-code`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [224, 256]

**Purpose:** Assembles all 5 slot selections into final issue record.

**JavaScript Code:**
```javascript
const slot1 = $('Remove Slot 1 Stories').first().json.slot1Selection;
const slot2 = $('Remove Slot 2 Stories').first().json.slot2Selection;
const slot3 = $('Remove Slot 3 Stories').first().json.slot3Selection;
const slot4 = $('Remove Slot 4 Stories').first().json.slot4Selection;
const slot5 = $('Remove Slot 5 Stories').first().json.slot5Selection;

// Generate issue_id and issue_date
const today = new Date();
const issueDate = today.toLocaleDateString('en-US', {
  month: 'short',
  day: 'numeric'
});

return [{
  json: {
    issue_id: `pivot5_${today.toISOString().split('T')[0]}`,
    issue_date: `Pivot 5 - ${issueDate}`,
    slot_1_storyId: slot1.selected_storyId,
    slot_1_pivotId: slot1.selected_pivotId,
    slot_1_headline: slot1.selected_headline,
    slot_2_storyId: slot2.selected_storyId,
    slot_2_pivotId: slot2.selected_pivotId,
    slot_2_headline: slot2.selected_headline,
    slot_3_storyId: slot3.selected_storyId,
    slot_3_pivotId: slot3.selected_pivotId,
    slot_3_headline: slot3.selected_headline,
    slot_4_storyId: slot4.selected_storyId,
    slot_4_pivotId: slot4.selected_pivotId,
    slot_4_headline: slot4.selected_headline,
    slot_5_storyId: slot5.selected_storyId,
    slot_5_pivotId: slot5.selected_pivotId,
    slot_5_headline: slot5.selected_headline,
    status: 'pending'
  }
}];
```

**Output:** Assembled issue → Connects to "Subject Line Generator"

---

#### Node 29: Subject Line Generator
**Node ID:** `subject-line-generator`
**Type:** `@n8n/n8n-nodes-langchain.chainLlm`
**Version:** 1.4
**Position:** [448, 256]

**AI Model Configuration:**
- **Model:** `claude-sonnet-4-5-20250929`
- **Temperature:** 0.7

**System Prompt:**
```
Generate a compelling email subject line for this daily AI newsletter.

TODAY'S HEADLINES:
1. {{ $json.slot_1_headline }}
2. {{ $json.slot_2_headline }}
3. {{ $json.slot_3_headline }}
4. {{ $json.slot_4_headline }}
5. {{ $json.slot_5_headline }}

REQUIREMENTS:
- Maximum 60 characters
- Create urgency and curiosity
- Reference 1-2 key stories
- Avoid clickbait, be substantive
- Match professional newsletter tone

Return ONLY the subject line, no quotes or explanation.
```

**Output:** Subject line text → Connects to "Prepare Write Data"

---

#### Node 30: Prepare Write Data
**Node ID:** `prepare-write-data`
**Type:** `n8n-nodes-base.set`
**Version:** 3.4
**Position:** [672, 256]

**Purpose:** Adds subject line to assembled issue data.

**Configuration:**
```json
{
  "assignments": {
    "assignments": [
      {
        "name": "subject_line",
        "value": "={{ $('Subject Line Generator').first().json.text }}",
        "type": "string"
      }
    ]
  }
}
```

**Output:** Complete issue data → Connects to "Write AI Editor - Selected Slots"

---

#### Node 31: Write AI Editor - Selected Slots
**Node ID:** `write-selected-slots`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [896, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)
- **Operation:** Create record

**Column Mapping:**
| Airtable Field | Source Expression |
|----------------|-------------------|
| issue_id | `{{ $json.issue_id }}` |
| issue_date | `{{ $json.issue_date }}` |
| subject_line | `{{ $json.subject_line }}` |
| status | `pending` |
| social_post_status | `pending` |
| slot_1_storyId | `{{ $json.slot_1_storyId }}` |
| slot_1_pivotId | `{{ $json.slot_1_pivotId }}` |
| slot_1_headline | `{{ $json.slot_1_headline }}` |
| slot_2_storyId | `{{ $json.slot_2_storyId }}` |
| slot_2_pivotId | `{{ $json.slot_2_pivotId }}` |
| slot_2_headline | `{{ $json.slot_2_headline }}` |
| slot_3_storyId | `{{ $json.slot_3_storyId }}` |
| slot_3_pivotId | `{{ $json.slot_3_pivotId }}` |
| slot_3_headline | `{{ $json.slot_3_headline }}` |
| slot_4_storyId | `{{ $json.slot_4_storyId }}` |
| slot_4_pivotId | `{{ $json.slot_4_pivotId }}` |
| slot_4_headline | `{{ $json.slot_4_headline }}` |
| slot_5_storyId | `{{ $json.slot_5_storyId }}` |
| slot_5_pivotId | `{{ $json.slot_5_pivotId }}` |
| slot_5_headline | `{{ $json.slot_5_headline }}` |

---

### Step 2 Data Flow Summary

```
Schedule Trigger (9:15 PM EST)
       │
       ▼
Pull Yesterday Issue
       │
       ├───────────────────────────────────────┐
       ▼                                       │
Pull Slot 1 Candidates ──► Merge ──► Prepare ──► Slot 1 Agent (Claude)
       │                   Context            │
       │                                      ▼
       │                              Remove Slot 1 Stories
       │                                      │
       │                    ┌─────────────────┘
       │                    │ (selectedToday, selectedCompanies, selectedSources)
       ▼                    ▼
Pull Slot 2 Candidates ──► Merge ──► Prepare ──► Slot 2 Agent (Claude)
       │                   Context            │
       │                                      ▼
       │                              Remove Slot 2 Stories
       │                                      │
       ... (continues for Slots 3, 4, 5) ...  │
       │                                      │
       └──────────────────────────────────────┘
                                              │
                                              ▼
                                        Assembly Code
                                              │
                                              ▼
                                   Subject Line Generator (Claude)
                                              │
                                              ▼
                                       Prepare Write Data
                                              │
                                              ▼
                                Write AI Editor - Selected Slots
                                      (tblzt2z7r512Kto3O)
```

---

## Step 3: Decoration Workflow

**Workflow Name:** STEP 3 AI Editor 2.0 - Decoration
**Workflow ID:** `HCbd2g852rkQgSqr`
**Total Nodes:** 41
**Schedules:**
- Headlines/Bullets: `25 2 * * 2-6` (9:25 PM EST)
- Image Generation: `30 2 * * 2-6` (9:30 PM EST)

### Purpose
Generates AI-powered headlines, deks, bullet points, and images for each selected story, then uploads images to Cloudflare CDN.

---

### Node-by-Node Analysis

#### Node 1: Schedule Trigger
**Node ID:** `schedule-trigger`
**Type:** `n8n-nodes-base.scheduleTrigger`
**Version:** 1.2
**Position:** [-2048, 256]

**Configuration:**
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "25 2 * * 2-6"
      },
      {
        "field": "cronExpression",
        "expression": "30 2 * * 2-6"
      }
    ]
  }
}
```

**Purpose:** Two triggers - 9:25 PM for text decoration, 9:30 PM for image generation.

---

#### Node 2: Pull Latest Issue
**Node ID:** `pull-latest-issue`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1824, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)

**Filter Formula:**
```
{status}='pending'
```

**Sort:** `issue_date` DESC
**Max Records:** 1

**Fields Retrieved:**
| Field | Type |
|-------|------|
| issue_id | Text |
| issue_date | Text |
| slot_1_pivotId through slot_5_pivotId | Text |
| slot_1_headline through slot_5_headline | Text |
| subject_line | Text |

**Output:** Latest pending issue → Connects to "Expand Slots"

---

#### Node 3: Expand Slots
**Node ID:** `expand-slots`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-1600, 256]

**JavaScript Code:**
```javascript
const issue = $input.first().json.fields;

const slots = [];
for (let i = 1; i <= 5; i++) {
  slots.push({
    json: {
      slot_order: i,
      pivotId: issue[`slot_${i}_pivotId`],
      headline: issue[`slot_${i}_headline`],
      issue_id: issue.issue_id,
      issue_date: issue.issue_date,
      subject_line: issue.subject_line
    }
  });
}

return slots;
```

**Purpose:** Expands single issue record into 5 individual slot items for parallel processing.

**Output:** 5 slot items → Connects to "Split In Batches"

---

#### Node 4: Split In Batches
**Node ID:** `split-in-batches`
**Type:** `n8n-nodes-base.splitInBatches`
**Version:** 3
**Position:** [-1376, 256]

**Configuration:**
```json
{
  "batchSize": 1,
  "options": {
    "reset": false
  }
}
```

**Purpose:** Processes each slot one at a time to avoid rate limits.

**Output:** Single slot → Connects to "Lookup Article"

---

#### Node 5: Lookup Article
**Node ID:** `lookup-article`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1152, 256]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tblGumae8KDpsrWvh` (Articles)

**Filter Formula:**
```
{pivot_Id}='{{ $json.pivotId }}'
```

**Fields Retrieved:**
| Field | Type | Description |
|-------|------|-------------|
| pivot_Id | Text | Article identifier |
| markdown | Long Text | Full article content |
| original_url | Text | Source URL |
| source_id | Text | Publisher name |
| date_published | DateTime | Publication date |

**Output:** Article content → Connects to "Clean Content"

---

#### Node 6: Clean Content
**Node ID:** `clean-content`
**Type:** `@n8n/n8n-nodes-langchain.chainLlm`
**Version:** 1.4
**Position:** [-928, 256]

**AI Model Configuration:**
- **Model:** `models/gemini-3-flash-preview`
- **Temperature:** 0.1

**System Prompt:**
```
You are a content cleaner. Remove all navigation elements, ads, footers,
headers, social media buttons, and non-article content from this markdown.

Keep ONLY the main article body text. Preserve paragraph structure.

Return the cleaned article text only.
```

**Input:** Raw markdown from Articles table

**Output:** Cleaned article text → Connects to "Content Creator"

---

#### Node 7: Content Creator
**Node ID:** `content-creator`
**Type:** `@n8n/n8n-nodes-langchain.chainLlm`
**Version:** 1.4
**Position:** [-704, 256]

**AI Model Configuration:**
- **Model:** `claude-sonnet-4-5-20250929`
- **Temperature:** 0.6
- **Max Tokens:** 1500

**System Prompt:**
```
You are a senior editor for Pivot 5, a daily AI newsletter for business professionals.

ARTICLE CONTENT:
{{ $json.cleaned_content }}

ORIGINAL HEADLINE:
{{ $('Split In Batches').item.json.headline }}

Generate the following for this article:

1. AI_HEADLINE: A punchy, Title Case headline under 80 characters
   - Should be more compelling than original
   - Focus on business impact
   - No clickbait

2. AI_DEK: A 1-sentence descriptive deck (15-25 words)
   - Provides context not in headline
   - Answers "why should I care?"

3. BULLET_1 (Main Announcement): 2 sentences, under 260 characters
   - What happened / what was announced
   - Key facts and figures

4. BULLET_2 (Key Details): 2 sentences, under 260 characters
   - Additional context
   - Who, what, when specifics

5. BULLET_3 (Business Impact): 2 sentences, under 260 characters
   - Why this matters
   - Market/industry implications

6. IMAGE_PROMPT: A detailed prompt for generating a newsletter image
   - Professional, abstract style
   - Relevant to article topic
   - No text or logos

7. LABEL: Category tag (one of: AI, Tech, Business, Policy, Research, Industry)

Return as JSON:
{
  "ai_headline": "...",
  "ai_dek": "...",
  "b1": "...",
  "b2": "...",
  "b3": "...",
  "image_prompt": "...",
  "label": "..."
}
```

**Output:** Decorated content JSON → Connects to "Bolding Pass"

---

#### Node 8: Bolding Pass
**Node ID:** `bolding-pass`
**Type:** `@n8n/n8n-nodes-langchain.chainLlm`
**Version:** 1.4
**Position:** [-480, 256]

**AI Model Configuration:**
- **Model:** `claude-sonnet-4-5-20250929`
- **Temperature:** 0.3

**System Prompt:**
```
Add bold formatting to key phrases in these bullet points.

RULES:
- Bold 1-3 key phrases per bullet (2-4 words each)
- Bold company names, numbers, percentages
- Bold action verbs and outcomes
- Use **markdown bold** syntax
- Do NOT change any other text

BULLETS:
b1: {{ $json.b1 }}
b2: {{ $json.b2 }}
b3: {{ $json.b3 }}

Return as JSON:
{
  "b1": "...",
  "b2": "...",
  "b3": "..."
}
```

**Output:** Bolded bullets → Connects to "Prepare Decoration Record"

---

#### Node 9: Prepare Decoration Record
**Node ID:** `prepare-decoration-record`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-256, 256]

**JavaScript Code:**
```javascript
const slot = $('Split In Batches').item.json;
const content = $('Content Creator').first().json;
const bolded = $('Bolding Pass').first().json;
const article = $('Lookup Article').first().json.fields;

return [{
  json: {
    issue_id: slot.issue_id,
    story_id: `${slot.issue_id}_slot${slot.slot_order}`,
    slot_order: slot.slot_order,
    pivotId: slot.pivotId,
    headline: content.ai_headline,
    ai_dek: content.ai_dek,
    label: content.label,
    b1: bolded.b1,
    b2: bolded.b2,
    b3: bolded.b3,
    image_prompt: content.image_prompt,
    image_status: 'needs_image',
    raw: article.markdown,
    core_url: article.original_url,
    source_id: article.source_id
  }
}];
```

**Output:** Decoration record → Connects to "Write Decoration"

---

#### Node 10: Write Decoration
**Node ID:** `write-decoration`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-32, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories / Decoration)
- **Operation:** Upsert
- **Match Field:** `story_id`

**Column Mapping:**
| Airtable Field | Source Expression |
|----------------|-------------------|
| story_id | `{{ $json.story_id }}` |
| issue_id | `{{ $json.issue_id }}` |
| slot_order | `{{ $json.slot_order }}` |
| pivotId | `{{ $json.pivotId }}` |
| headline | `{{ $json.headline }}` |
| ai_dek | `{{ $json.ai_dek }}` |
| label | `{{ $json.label }}` |
| b1 | `{{ $json.b1 }}` |
| b2 | `{{ $json.b2 }}` |
| b3 | `{{ $json.b3 }}` |
| image_prompt | `{{ $json.image_prompt }}` |
| image_status | `{{ $json.image_status }}` |
| raw | `{{ $json.raw }}` |
| core_url | `{{ $json.core_url }}` |
| source_id | `{{ $json.source_id }}` |

**Output:** Written record → Connects back to "Split In Batches" (loop)

---

### Image Generation Pipeline

#### Node 11: Get Stories Needing Images
**Node ID:** `get-stories-needing-images`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [224, 512]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories)

**Filter Formula:**
```
{image_status}='needs_image'
```

**Max Records:** 10

**Output:** Stories needing images → Connects to "Image Split Batches"

---

#### Node 12: Image Split Batches
**Node ID:** `image-split-batches`
**Type:** `n8n-nodes-base.splitInBatches`
**Version:** 3
**Position:** [448, 512]

**Configuration:**
```json
{
  "batchSize": 1
}
```

---

#### Node 13: Gemini Generate Image
**Node ID:** `gemini-generate-image`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [672, 512]

**HTTP Configuration:**
- **Method:** POST
- **URL:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent`

**Query Parameters:**
```json
{
  "key": "{{ $env.GEMINI_API_KEY }}"
}
```

**Request Body:**
```json
{
  "contents": [{
    "parts": [{
      "text": "Generate a professional, abstract newsletter image for: {{ $json.fields.image_prompt }}. Style: clean, modern, suitable for business newsletter. No text or logos. 636px width, landscape orientation."
    }]
  }],
  "generationConfig": {
    "responseModalities": ["image"],
    "imageDimensions": {
      "width": 636,
      "height": 358
    }
  }
}
```

**Output:** Generated image (base64) → Connects to "Check Gemini Success"

---

#### Node 14: Check Gemini Success
**Node ID:** `check-gemini-success`
**Type:** `n8n-nodes-base.if`
**Version:** 2
**Position:** [896, 512]

**Condition:**
```json
{
  "conditions": [
    {
      "leftValue": "={{ $json.candidates[0].content.parts[0].inlineData.data }}",
      "rightValue": "",
      "operator": {
        "type": "string",
        "operation": "notEmpty"
      }
    }
  ]
}
```

**True Branch:** → "Convert to Binary"
**False Branch:** → "OpenAI Backup Node"

---

#### Node 15: OpenAI Backup Node
**Node ID:** `openai-backup`
**Type:** `n8n-nodes-base.openAi`
**Version:** 1.5
**Position:** [896, 736]

**Configuration:**
- **Operation:** Generate Image
- **Model:** `gpt-image-1.5`
- **Size:** `1024x1024`
- **Quality:** `standard`

**Prompt:**
```
{{ $('Image Split Batches').item.json.fields.image_prompt }}

Style: Professional, abstract, suitable for business newsletter.
No text, logos, or words. Clean modern design.
```

**Output:** DALL-E image URL → Connects to "Download OpenAI Image"

---

#### Node 16: Download OpenAI Image
**Node ID:** `download-openai-image`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [1120, 736]

**Configuration:**
- **Method:** GET
- **URL:** `{{ $json.data[0].url }}`
- **Response Format:** File

**Output:** Binary image data → Connects to "Convert OpenAI to Binary"

---

#### Node 17: Convert to Binary
**Node ID:** `convert-to-binary`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [1120, 512]

**JavaScript Code:**
```javascript
const base64Data = $json.candidates[0].content.parts[0].inlineData.data;
const mimeType = $json.candidates[0].content.parts[0].inlineData.mimeType || 'image/png';

const binaryData = Buffer.from(base64Data, 'base64');

return [{
  json: $json,
  binary: {
    data: {
      data: base64Data,
      mimeType: mimeType,
      fileName: 'newsletter_image.png'
    }
  }
}];
```

**Output:** Binary image → Connects to "Upload to Cloudflare"

---

#### Node 18: Upload to Cloudflare
**Node ID:** `upload-to-cloudflare`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [1344, 512]

**HTTP Configuration:**
- **Method:** POST
- **URL:** `https://api.cloudflare.com/client/v4/accounts/{{ $env.CLOUDFLARE_ACCOUNT_ID }}/images/v1`

**Headers:**
```json
{
  "Authorization": "Bearer {{ $env.CLOUDFLARE_API_TOKEN }}"
}
```

**Body:** Form-data with binary image

**Output:** Cloudflare image response → Connects to "Extract Image URL"

---

#### Node 19: Extract Image URL
**Node ID:** `extract-image-url`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [1568, 512]

**JavaScript Code:**
```javascript
const cfResponse = $json;
const imageId = cfResponse.result.id;
const storyId = $('Image Split Batches').item.json.id;

// Construct newsletter-optimized URL
const imageUrl = `https://img.pivotnews.com/cdn-cgi/imagedelivery/KXy14RehLGC3ziMxzD_shA/${imageId}/newsletter`;

return [{
  json: {
    recordId: storyId,
    image_url: imageUrl,
    cloudflare_id: imageId
  }
}];
```

**Output:** Image URL → Connects to "Update Image Status"

---

#### Node 20: Update Image Status
**Node ID:** `update-image-status`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [1792, 512]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories)
- **Operation:** Update record
- **Record ID:** `{{ $json.recordId }}`

**Column Mapping:**
| Airtable Field | Source Expression |
|----------------|-------------------|
| image_url | `{{ $json.image_url }}` |
| image_status | `generated` |
| cloudflare_id | `{{ $json.cloudflare_id }}` |

**Output:** → Connects back to "Image Split Batches" (loop)

---

### Step 3 Data Flow Summary

```
Schedule Trigger (9:25 PM / 9:30 PM EST)
       │
       ▼
Pull Latest Issue (status='pending')
       │
       ▼
Expand Slots (1 issue → 5 slots)
       │
       ▼
Split In Batches (process one at a time)
       │
       ├──────────────────────────────────────┐
       ▼                                      │
Lookup Article (get markdown by pivotId)     │
       │                                      │
       ▼                                      │
Clean Content (Gemini - remove nav/ads)      │
       │                                      │
       ▼                                      │
Content Creator (Claude - headlines/bullets) │
       │                                      │
       ▼                                      │
Bolding Pass (Claude - bold key phrases)     │
       │                                      │
       ▼                                      │
Prepare Decoration Record                    │
       │                                      │
       ▼                                      │
Write Decoration (tbla16LJCf5Z6cRn3)         │
       │                                      │
       └──────────────────────────────────────┘
                     │
                     ▼
         (Loop until all 5 slots done)
                     │
                     ▼
       ┌─────────────────────────┐
       │   IMAGE GENERATION      │
       └─────────────────────────┘
                     │
                     ▼
Get Stories Needing Images (image_status='needs_image')
                     │
                     ▼
            Image Split Batches
                     │
       ┌─────────────┴─────────────┐
       ▼                           │
Gemini Generate Image              │
       │                           │
       ▼                           │
Check Gemini Success?              │
   │         │                     │
   ▼         ▼                     │
 YES        NO                     │
   │         │                     │
   │    OpenAI Backup              │
   │         │                     │
   ▼         ▼                     │
Convert to Binary                  │
       │                           │
       ▼                           │
Upload to Cloudflare               │
       │                           │
       ▼                           │
Extract Image URL                  │
       │                           │
       ▼                           │
Update Image Status                │
   (image_status='generated')      │
       │                           │
       └───────────────────────────┘
```

---

## Step 4: HTML Compile and Send Workflow

**Workflow Name:** STEP 4 AI Editor 2.0 - Compile HTML and Send
**Workflow ID:** `NKjC8hb0EDHIXx3U`
**Total Nodes:** 17
**Schedules:**
- HTML Compilation: `0 3 * * 2-6` (10:00 PM EST)
- Email Send: `0 10 * * 1-5` (5:00 AM EST)

### Purpose
Compiles the 5 decorated stories into HTML email format, generates newsletter summaries, archives to Newsletter Issues table, and sends via Mautic email marketing platform.

---

### Node-by-Node Analysis

#### Node 1: Schedule Trigger
**Node ID:** `schedule-trigger`
**Type:** `n8n-nodes-base.scheduleTrigger`
**Version:** 1.2
**Position:** [-1920, 256]

**Configuration:**
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "0 3 * * 2-6"
      },
      {
        "field": "cronExpression",
        "expression": "0 10 * * 1-5"
      }
    ]
  }
}
```

**Purpose:**
- 10:00 PM EST: Compile HTML
- 5:00 AM EST: Send email

---

#### Node 2: Get Decorated Stories
**Node ID:** `get-decorated-stories`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1696, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories)

**Filter Formula:**
```
{image_status}='generated'
```

**Sort:** `slot_order` ASC
**Max Records:** 5

**Fields Retrieved:**
| Field | Type |
|-------|------|
| story_id | Text |
| issue_id | Text |
| slot_order | Number |
| headline | Text |
| ai_dek | Text |
| label | Text |
| b1 | Text |
| b2 | Text |
| b3 | Text |
| image_url | Text |
| core_url | Text |

**Output:** 5 decorated stories → Connects to "Aggregate Stories"

---

#### Node 3: Aggregate Stories
**Node ID:** `aggregate-stories`
**Type:** `n8n-nodes-base.aggregate`
**Version:** 1
**Position:** [-1472, 256]

**Configuration:**
```json
{
  "aggregate": "aggregateAllItemData",
  "destinationFieldName": "stories"
}
```

**Purpose:** Combines 5 stories into single object for HTML template.

**Output:** Aggregated stories → Connects to "Get Subject Line"

---

#### Node 4: Get Subject Line
**Node ID:** `get-subject-line`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-1248, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)

**Filter Formula:**
```
{status}='pending'
```

**Sort:** `issue_date` DESC
**Max Records:** 1

**Fields Retrieved:**
| Field | Type |
|-------|------|
| issue_id | Text |
| issue_date | Text |
| subject_line | Text |

**Output:** Issue metadata → Connects to "Compile HTML"

---

#### Node 5: Compile HTML
**Node ID:** `compile-html`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-1024, 256]

**JavaScript Code (simplified):**
```javascript
const stories = $('Aggregate Stories').first().json.stories;
const issue = $('Get Subject Line').first().json.fields;

// HTML Template structure
const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${issue.subject_line}</title>
  <style>
    /* Responsive email styles */
    body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
    .container { max-width: 640px; margin: 0 auto; }
    .story-block { padding: 24px; border-bottom: 1px solid #eee; }
    .label {
      background: #ff6f00;
      color: white;
      padding: 4px 12px;
      font-size: 12px;
      border-radius: 4px;
    }
    .headline { font-size: 22px; font-weight: bold; margin: 16px 0; }
    .dek { font-size: 16px; color: #666; margin-bottom: 16px; }
    .bullet { margin: 8px 0; line-height: 1.5; }
    .read-more {
      color: #ff6f00;
      text-decoration: none;
      font-weight: bold;
    }
    img { max-width: 100%; height: auto; }
  </style>
</head>
<body>
  <div class="container">
    <!-- Preheader -->
    <span style="display:none;">${issue.subject_line}</span>

    <!-- Header -->
    <div style="text-align:center; padding:24px;">
      <img src="https://img.pivotnews.com/pivot5-logo.png" alt="Pivot 5" width="200">
      <p style="color:#666;">5 headlines • 5 minutes • 5 days a week</p>
    </div>

    <!-- Stories -->
    ${stories.map((story, i) => `
      <div class="story-block">
        <span class="label">${story.fields.label}</span>
        <h2 class="headline">${story.fields.headline}</h2>
        <img src="${story.fields.image_url}" alt="${story.fields.headline}">
        <p class="dek">${story.fields.ai_dek}</p>
        <ul>
          <li class="bullet">${story.fields.b1}</li>
          <li class="bullet">${story.fields.b2}</li>
          <li class="bullet">${story.fields.b3}</li>
        </ul>
        <a href="${story.fields.core_url}" class="read-more">Read More →</a>
      </div>
    `).join('')}

    <!-- Footer -->
    <div style="padding:24px; text-align:center; background:#f5f5f5;">
      <p>© 2025 Pivot Media. All rights reserved.</p>
      <a href="{unsubscribe_url}">Unsubscribe</a> |
      <a href="{preferences_url}">Manage Preferences</a>
    </div>
  </div>
</body>
</html>
`;

return [{
  json: {
    html: html,
    issue_id: issue.issue_id,
    issue_date: issue.issue_date,
    subject_line: issue.subject_line
  }
}];
```

**Output:** Compiled HTML → Connects to "Generate Summary"

---

#### Node 6: Generate Summary
**Node ID:** `generate-summary`
**Type:** `@n8n/n8n-nodes-langchain.chainLlm`
**Version:** 1.4
**Position:** [-800, 256]

**AI Model Configuration:**
- **Model:** `claude-sonnet-4-5-20250929`
- **Temperature:** 0.5

**System Prompt:**
```
Generate two newsletter summaries:

HEADLINES FROM TODAY'S ISSUE:
{{ $('Aggregate Stories').first().json.stories.map(s => s.fields.headline).join('\n') }}

1. SUMMARY (exactly 15 words): A punchy overview of today's newsletter
2. SUMMARY_PLUS (exactly 20 words): Slightly more detailed overview

Return as JSON:
{
  "summary": "...",
  "summary_plus": "..."
}
```

**Output:** Summaries → Connects to "Prepare Issue Record"

---

#### Node 7: Prepare Issue Record
**Node ID:** `prepare-issue-record`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-576, 256]

**JavaScript Code:**
```javascript
const compiled = $('Compile HTML').first().json;
const summaries = $('Generate Summary').first().json;

return [{
  json: {
    issue_id: compiled.issue_id,
    newsletter_id: 'pivot_ai',
    html: compiled.html,
    subject_line: compiled.subject_line,
    summary: summaries.summary,
    summary_plus: summaries.summary_plus,
    status: 'compiled'
  }
}];
```

---

#### Node 8: Write Newsletter Issue
**Node ID:** `write-newsletter-issue`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [-352, 256]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tbl7mcCCGbjEfli25` (Newsletter Issues)
- **Operation:** Upsert
- **Match Field:** `issue_id`

**Column Mapping:**
| Airtable Field | Source Expression |
|----------------|-------------------|
| issue_id | `{{ $json.issue_id }}` |
| newsletter_id | `{{ $json.newsletter_id }}` |
| html | `{{ $json.html }}` |
| subject_line | `{{ $json.subject_line }}` |
| summary | `{{ $json.summary }}` |
| summary_plus | `{{ $json.summary_plus }}` |
| status | `{{ $json.status }}` |

**Output:** Written issue → Connects to "Check Time for Send"

---

#### Node 9: Check Time for Send
**Node ID:** `check-time-for-send`
**Type:** `n8n-nodes-base.if`
**Version:** 2
**Position:** [-128, 256]

**Purpose:** Determines if this is the 5 AM send trigger or 10 PM compile trigger.

**Condition:**
```javascript
// Check if current hour is 5 AM EST (10:00 UTC)
const hour = new Date().getUTCHours();
return hour >= 9 && hour <= 11; // 5 AM - 6 AM EST window
```

**True Branch:** → "Create Mautic Email"
**False Branch:** → End (compile only)

---

#### Node 10: Create Mautic Email
**Node ID:** `create-mautic-email`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [96, 256]

**HTTP Configuration:**
- **Method:** POST
- **URL:** `https://app.pivotnews.com/api/emails/new`

**Authentication:**
- **Type:** OAuth2
- **Credentials:** Mautic OAuth2

**Request Body:**
```json
{
  "name": "{{ $json.issue_id }}",
  "subject": "{{ $json.subject_line }}",
  "customHtml": "{{ $json.html }}",
  "emailType": "list",
  "lists": [1],
  "isPublished": true,
  "template": null,
  "utmTags": {
    "utmSource": "newsletter",
    "utmMedium": "email",
    "utmCampaign": "pivot5_daily"
  }
}
```

**Output:** Mautic email ID → Connects to "Attach Transport"

---

#### Node 11: Attach Transport
**Node ID:** `attach-transport`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [320, 256]

**HTTP Configuration:**
- **Method:** PATCH
- **URL:** `https://app.pivotnews.com/api/emails/{{ $json.email.id }}/transport`

**Request Body:**
```json
{
  "transport_id": "{{ $env.GREENARROW_TRANSPORT_ID }}"
}
```

**Purpose:** Associates email with GreenArrow SMTP transport for deliverability.

---

#### Node 12: Send Email
**Node ID:** `send-email`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [544, 256]

**HTTP Configuration:**
- **Method:** POST
- **URL:** `https://app.pivotnews.com/api/emails/{{ $json.email.id }}/send`

**Request Body:**
```json
{
  "lists": [1]
}
```

**Output:** Send response → Connects to "Archive Sent"

---

#### Node 13: Archive Sent
**Node ID:** `archive-sent`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [768, 256]

**Airtable Configuration:**
- **Base ID:** `appwSozYTkrsQWUXB` (Pivot Media Master)
- **Table ID:** `tblHo0xNj8nbzMHNI` (Newsletter Issues Archive)
- **Operation:** Create record

**Column Mapping:**
| Airtable Field | Source Expression |
|----------------|-------------------|
| issue_id | `{{ $('Prepare Issue Record').first().json.issue_id }}` |
| sent_status | `sent` |
| mautic_email_id | `{{ $json.email.id }}` |
| mautic_response | `{{ JSON.stringify($json) }}` |
| sent_at | `{{ $now.toISO() }}` |

---

#### Node 14: Update Selected Slots Status
**Node ID:** `update-selected-slots-status`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [992, 256]

**Airtable Configuration:**
- **Base ID:** `appglKSJZxmA9iHpl` (AI Editor 2.0)
- **Table ID:** `tblzt2z7r512Kto3O` (Selected Slots)
- **Operation:** Update record

**Column Mapping:**
| Airtable Field | Value |
|----------------|-------|
| status | `sent` |

---

### Step 4 Data Flow Summary

```
Schedule Trigger (10 PM compile / 5 AM send)
       │
       ▼
Get Decorated Stories (image_status='generated')
       │
       ▼
Aggregate Stories (combine 5 stories)
       │
       ▼
Get Subject Line (from Selected Slots)
       │
       ▼
Compile HTML (build email template)
       │
       ▼
Generate Summary (15 + 20 word versions)
       │
       ▼
Prepare Issue Record
       │
       ▼
Write Newsletter Issue (tbl7mcCCGbjEfli25)
       │
       ▼
Check Time for Send?
   │         │
   ▼         ▼
 5 AM      10 PM
(send)    (compile only)
   │
   ▼
Create Mautic Email
   │
   ▼
Attach Transport (GreenArrow)
   │
   ▼
Send Email
   │
   ▼
Archive Sent (tblHo0xNj8nbzMHNI)
   │
   ▼
Update Selected Slots Status (status='sent')
```

---

## Step 5: Social Post Trigger Workflow

**Workflow Name:** STEP 5 AI Editor 2.0 - Airtable Social Post Trigger
**Workflow ID:** `I8U8LgJVDsO8PeBJ`
**Total Nodes:** 10
**Schedules:**
- `30 4 * * 1-5` (4:30 AM EST, Monday-Friday)
- `0 5 * * 1-5` (5:00 AM EST, Monday-Friday)

### Purpose
Syndicates decorated newsletter stories to the P5 Social Posts table for downstream social media workflows, preventing duplicate posts.

---

### Node-by-Node Analysis

#### Node 1: Schedule Trigger
**Node ID:** `schedule-trigger`
**Type:** `n8n-nodes-base.scheduleTrigger`
**Version:** 1.2
**Position:** [-1104, -80]

**Configuration:**
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "30 4 * * 1-5"
      },
      {
        "field": "cronExpression",
        "expression": "0 5 * * 1-5"
      }
    ]
  }
}
```

**Purpose:** Runs at 4:30 AM and 5:00 AM EST to catch newly generated content.

---

#### Node 2: GET Decorated Stories Ready for Social
**Node ID:** `1719734d-da69-48a3-938f-731622d0ae24`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [-768, -16]

**HTTP Configuration:**
- **Method:** GET
- **URL:** `https://api.airtable.com/v0/appglKSJZxmA9iHpl/tbla16LJCf5Z6cRn3`

**Query Parameters:**
| Parameter | Value |
|-----------|-------|
| filterByFormula | `AND({image_status}='generated', OR({social_status}='', {social_status}='pending'))` |
| maxRecords | `10` |

**Headers:**
| Header | Value |
|--------|-------|
| Authorization | `Bearer [REDACTED]` |
| Content-Type | `application/json` |

**Purpose:** Fetches stories that have images generated but haven't been synced to social yet.

**Output:** Airtable records → Connects to "Extract Records"

---

#### Node 3: Extract Records
**Node ID:** `b8371e59-1270-45a1-8deb-46b4650adf11`
**Type:** `n8n-nodes-base.code`
**Version:** 2
**Position:** [-544, -16]

**JavaScript Code:**
```javascript
// Extract records array from Airtable API response
const airtableResponse = $input.first().json;

return airtableResponse.records.map(record => {
  // Clean the raw field if it exists
  if (record.fields?.raw) {
    let raw = record.fields.raw;

    // Remove HTML tags
    raw = raw.replace(/<[^>]*>/g, '');

    // Decode common HTML entities
    raw = raw.replace(/&nbsp;/g, ' ')
             .replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"')
             .replace(/&#39;/g, "'");

    // Normalize whitespace: replace multiple newlines/spaces with single space
    raw = raw.replace(/\s+/g, ' ');

    // Trim
    raw = raw.trim();

    // Update the field
    record.fields.raw = raw;
  }

  return {json: record};
});
```

**Purpose:** Extracts individual records from Airtable response and cleans HTML from raw content.

**Output:** Individual story records → Connects to "Split In Batches"

---

#### Node 4: Split In Batches
**Node ID:** `406eacf1-187d-4b43-900b-de444f6abfab`
**Type:** `n8n-nodes-base.splitInBatches`
**Version:** 3
**Position:** [-320, -176]

**Configuration:**
```json
{
  "options": {
    "reset": false
  }
}
```

**Purpose:** Process stories one at a time to handle deduplication.

**Output:** Single story → Connects to "Find Existing in P5 Social Posts"

---

#### Node 5: Find Existing in P5 Social Posts
**Node ID:** `342fed88-5e06-4a9a-8c32-bbc1e047bfbd`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [-112, 48]

**HTTP Configuration:**
- **Method:** GET
- **URL:** `https://api.airtable.com/v0/appRUgK44hQnXH1PM/tbllJMN2QBPJoG3jA`

**Query Parameters:**
| Parameter | Value |
|-----------|-------|
| filterByFormula | `AND({source_record_id}="{{ $json.id }}",{source_record_id}!="")` |

**Headers:**
| Header | Value |
|--------|-------|
| Authorization | `Bearer [REDACTED]` |

**Purpose:** Checks if a social post already exists for this source record.

**Output:** Existing records (if any) → Connects to "Check If Exists"

---

#### Node 6: Check If Exists
**Node ID:** `ea3b0b03-8d00-496a-b3b1-0d82ca2a49a9`
**Type:** `n8n-nodes-base.function`
**Version:** 1
**Position:** [96, 96]

**JavaScript Code:**
```javascript
const sourceRecord = $input.item.json;
const existingRecordsResponse = $('Find Existing in P5 Social Posts').first().json;

// If record already exists, mark it as 'skip' so we continue the loop
if (existingRecordsResponse.records && existingRecordsResponse.records.length > 0) {
  return {json: {...sourceRecord, action: 'skip'}};
}

// Record doesn't exist, pass it through with action='create'
return {json: {...sourceRecord, action: 'create'}};
```

**Purpose:** Determines whether to create new social post or skip duplicate.

**Output:** Record with action flag → Connects to "Does Newsletter Post Already Exist?"

---

#### Node 7: Does Newsletter Post Already Exist?
**Node ID:** `0361a445-a621-436d-a63a-f651a3d065e5`
**Type:** `n8n-nodes-base.if`
**Version:** 2
**Position:** [320, 96]

**Condition:**
```json
{
  "conditions": {
    "conditions": [
      {
        "id": "condition1",
        "leftValue": "={{ $json.action }}",
        "rightValue": "skip",
        "operator": {
          "type": "string",
          "operation": "equals"
        }
      }
    ],
    "combinator": "and"
  }
}
```

**True Branch (Skip):** → "Split In Batches" (continue loop)
**False Branch (Create):** → "Create a record"

---

#### Node 8: Create a record
**Node ID:** `bfb7c3aa-36f1-4928-91df-597fcd3835c9`
**Type:** `n8n-nodes-base.airtable`
**Version:** 2.1
**Position:** [528, 192]

**Airtable Configuration:**
- **Base ID:** `appRUgK44hQnXH1PM` (P5 Social Posts)
- **Table ID:** `tbllJMN2QBPJoG3jA` (P5 Social Posts)
- **Operation:** Create record

**Credentials:**
- **Name:** Airtable Pivot Studio
- **ID:** `oWcf5peCOkQe8Rem`

**Column Mapping:**
| Airtable Field | Source Expression | Type |
|----------------|-------------------|------|
| source_record_id | `{{ $('Split In Batches').item.json.id }}` | Text |
| label | `{{ $('Split In Batches').item.json.fields.label }}` | Text |
| headline | `{{ $('Split In Batches').item.json.fields.headline }}` | Text |
| image_raw_url | `{{ $('Split In Batches').item.json.fields.image_url }}` | Text |
| Raw | `{{ $('Split In Batches').item.json.fields.raw }}` | Long Text |
| publish_status | `ready` | Select (ready/processing/published) |
| Order | `{{ $('Split In Batches').item.json.fields.slot_order }}` | Number |
| Name | `{{ $('Split In Batches').item.json.fields.headline }}` | Text |
| b1 | `{{ $('Split In Batches').item.json.fields.b1 }}` | Text |
| b2 | `{{ $('Split In Batches').item.json.fields.b2 }}` | Text |
| b3 | `{{ $('Split In Batches').item.json.fields.b3 }}` | Text |

**Output:** Created record → Connects to "Mark Social Synced"

---

#### Node 9: Mark Social Synced
**Node ID:** `mark-social-synced`
**Type:** `n8n-nodes-base.httpRequest`
**Version:** 4.2
**Position:** [752, 192]

**HTTP Configuration:**
- **Method:** PATCH
- **URL:** `https://api.airtable.com/v0/appglKSJZxmA9iHpl/tbla16LJCf5Z6cRn3/{{ $('Split In Batches').item.json.id }}`

**Headers:**
| Header | Value |
|--------|-------|
| Authorization | `Bearer [REDACTED]` |
| Content-Type | `application/json` |

**Request Body:**
```json
{"fields": {"social_status": "synced"}}
```

**Purpose:** Updates the source decoration record to mark it as synced to social.

**Output:** → Connects back to "Split In Batches" (continue loop)

---

### Step 5 Data Flow Summary

```
Schedule Trigger (4:30 AM / 5:00 AM EST)
       │
       ▼
GET Decorated Stories Ready for Social
(filter: image_status='generated' AND social_status empty/pending)
       │
       ▼
Extract Records (clean HTML from raw)
       │
       ▼
Split In Batches
       │
       ├─────────────────────────────────────────────┐
       ▼                                             │
Find Existing in P5 Social Posts                    │
(check if source_record_id already exists)          │
       │                                             │
       ▼                                             │
Check If Exists (add action: skip/create)           │
       │                                             │
       ▼                                             │
Does Newsletter Post Already Exist?                 │
       │              │                              │
       ▼              ▼                              │
     YES            NO                              │
   (skip)        (create)                           │
       │              │                              │
       │              ▼                              │
       │      Create a record                       │
       │    (P5 Social Posts table)                 │
       │              │                              │
       │              ▼                              │
       │      Mark Social Synced                    │
       │    (social_status='synced')                │
       │              │                              │
       └──────────────┴──────────────────────────────┘
                      │
                      ▼
             (Loop until all done)
```

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SOURCES                                   │
│                     (RSS Feeds, scraped via Firecrawl)                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARTICLES TABLE (appwSozYTkrsQWUXB)                        │
│                         tblGumae8KDpsrWvh                                   │
│  Fields: pivot_Id, original_url, source_id, date_published, markdown        │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                              ┌───────┴───────┐
                              ▼               ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│    NEWSLETTER STORIES           │   │    SOURCE CREDIBILITY           │
│    (appwSozYTkrsQWUXB)          │   │    (appglKSJZxmA9iHpl)          │
│    tblY78ziWp5yhiGXp            │   │    tbl3Zkdl1No2edDLK           │
│    ai_headline, ai_dek, etc.    │   │    source_name, credibility     │
└─────────────────────────────────┘   └─────────────────────────────────┘
              │                                    │
              └────────────────┬───────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STEP 1: PRE-FILTER (9:00 PM EST)                     │
│                           Workflow: VoSZu0MIJAw1IuLL                        │
│               Google Gemini filters into 5 slot categories                  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRE-FILTER LOG (appglKSJZxmA9iHpl)                       │
│                         tbl72YMsm9iRHj3sp                                   │
│  Fields: storyID, pivotId, headline, source_id, slot (1-5)                  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 2: SLOT SELECTION (9:15 PM EST)                     │
│                           Workflow: SZmPztKNEmisG3Zf                        │
│          5 sequential Claude agents select one story per slot               │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SELECTED SLOTS (appglKSJZxmA9iHpl)                       │
│                         tblzt2z7r512Kto3O                                   │
│  Fields: issue_id, issue_date, subject_line, slot_1-5_storyId/pivotId       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   STEP 3: DECORATION (9:25 PM / 9:30 PM EST)                │
│                           Workflow: HCbd2g852rkQgSqr                        │
│        Claude generates headlines/bullets, Gemini/DALL-E generates images   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              NEWSLETTER ISSUE STORIES / DECORATION                          │
│                     (appglKSJZxmA9iHpl)                                     │
│                         tbla16LJCf5Z6cRn3                                   │
│  Fields: story_id, headline, ai_dek, b1-b3, image_url, image_status         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                      ┌───────────────┴───────────────┐
                      │                               │
                      ▼                               ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────────┐
│  STEP 4: HTML COMPILE & SEND    │   │  STEP 5: SOCIAL SYNDICATION         │
│  10 PM compile / 5 AM send      │   │  4:30 AM / 5:00 AM EST              │
│  Workflow: NKjC8hb0EDHIXx3U     │   │  Workflow: I8U8LgJVDsO8PeBJ         │
└─────────────────┬───────────────┘   └─────────────────┬───────────────────┘
                  │                                     │
                  ▼                                     ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────────┐
│    NEWSLETTER ISSUES            │   │    P5 SOCIAL POSTS                  │
│    (appwSozYTkrsQWUXB)          │   │    (appRUgK44hQnXH1PM)              │
│    tbl7mcCCGbjEfli25            │   │    tbllJMN2QBPJoG3jA                │
│    html, subject_line, summary  │   │    headline, b1-b3, image_raw_url   │
└─────────────────┬───────────────┘   └─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│    MAUTIC EMAIL PLATFORM        │
│    https://app.pivotnews.com    │
│    OAuth2 + GreenArrow SMTP     │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│    NEWSLETTER ISSUES ARCHIVE    │
│    (appwSozYTkrsQWUXB)          │
│    tblHo0xNj8nbzMHNI            │
│    sent_status, mautic_response │
└─────────────────────────────────┘
```

---

## Cron Schedule Summary

All times are **Eastern Standard Time (EST)**. UTC conversions shown for n8n configuration.

| Workflow | Step | Cron Expression (UTC) | ET Time | Days |
|----------|------|----------------------|---------|------|
| Pre-Filter | 1 | `0 2 * * 2-6` | 9:00 PM | Mon-Fri |
| Slot Selection | 2 | `15 2 * * 2-6` | 9:15 PM | Mon-Fri |
| Decoration (Text) | 3 | `25 2 * * 2-6` | 9:25 PM | Mon-Fri |
| Decoration (Images) | 3 | `30 2 * * 2-6` | 9:30 PM | Mon-Fri |
| HTML Compile | 4 | `0 3 * * 2-6` | 10:00 PM | Mon-Fri |
| Email Send | 4 | `0 10 * * 1-5` | 5:00 AM | Tue-Sat |
| Social Sync 1 | 5 | `30 9 * * 1-5` | 4:30 AM | Tue-Sat |
| Social Sync 2 | 5 | `0 10 * * 1-5` | 5:00 AM | Tue-Sat |

### Daily Timeline (EST)

```
9:00 PM  ──► Step 1: Pre-Filter (Gemini categorizes articles into slots)
9:15 PM  ──► Step 2: Slot Selection (Claude agents select 5 stories)
9:25 PM  ──► Step 3: Text Decoration (Claude generates headlines/bullets)
9:30 PM  ──► Step 3: Image Generation (Gemini/DALL-E creates images)
10:00 PM ──► Step 4: HTML Compilation (builds email template)

─────────── OVERNIGHT ───────────

4:30 AM  ──► Step 5: Social Syndication (syncs to P5 Social Posts)
5:00 AM  ──► Step 4: Email Send (sends via Mautic/GreenArrow)
5:00 AM  ──► Step 5: Social Syndication (second sync pass)
```

---

## API Credentials Reference

### Airtable
| Key | Value |
|-----|-------|
| API Key | `[REDACTED]` |
| Base: AI Editor 2.0 | `appglKSJZxmA9iHpl` |
| Base: Pivot Media Master | `appwSozYTkrsQWUXB` |
| Base: P5 Social Posts | `appRUgK44hQnXH1PM` |

### AI Services
| Service | Model |
|---------|-------|
| Google Gemini (Pre-filter/Content Cleaning) | `gemini-3-flash-preview` |
| Google Gemini (Image Generation) | `gemini-3-pro-image-preview` |
| Claude Sonnet (Selection/Decoration) | `claude-sonnet-4-5-20250929` |
| OpenAI (Backup Image Generation) | `gpt-image-1.5` |

### Email / Image Hosting
| Service | Endpoint |
|---------|----------|
| Mautic | `https://app.pivotnews.com/api` |
| Cloudflare Images | `https://img.pivotnews.com/cdn-cgi/imagedelivery/KXy14RehLGC3ziMxzD_shA/{id}/newsletter` |

---

## Appendix: Airtable Field Reference

### AI Editor - Pre-Filter Log (tbl72YMsm9iRHj3sp)
| Field | Type | Description |
|-------|------|-------------|
| storyID | Text | Story identifier (same as article_id) |
| pivotId | Text | Link to Articles table |
| headline | Text | Story headline |
| original_url | Text | Source URL |
| source_id | Text | Publisher name |
| date_og_published | DateTime | Original publication date |
| date_prefiltered | Date | Pre-filter timestamp |
| slot | Number | Eligible slot (1-5) |

### AI Editor - Selected Slots (tblzt2z7r512Kto3O)
| Field | Type | Description |
|-------|------|-------------|
| issue_id | Text | Unique issue identifier |
| issue_date | Text | Display date ("Pivot 5 - Dec 23") |
| subject_line | Text | Email subject |
| status | Select | pending → sent |
| social_post_status | Select | pending → synced |
| slot_1_storyId | Text | Slot 1 story ID |
| slot_1_pivotId | Text | Slot 1 article link |
| slot_1_headline | Text | Slot 1 headline |
| ... | ... | (slots 2-5 same pattern) |

### Newsletter Issue Stories / Decoration (tbla16LJCf5Z6cRn3)
| Field | Type | Description |
|-------|------|-------------|
| story_id | Text | Unique: `{issue_id}_slot{N}` |
| issue_id | Text | Parent issue |
| slot_order | Number | 1-5 |
| pivotId | Text | Link to Articles |
| headline | Text | AI-generated headline |
| ai_dek | Text | AI-generated deck |
| label | Text | Category (AI, Tech, Business, etc.) |
| b1 | Text | Bullet 1 (bolded) |
| b2 | Text | Bullet 2 (bolded) |
| b3 | Text | Bullet 3 (bolded) |
| image_prompt | Text | Prompt used for image |
| image_status | Select | needs_image → generated |
| image_url | Text | Cloudflare CDN URL |
| cloudflare_id | Text | Image ID |
| raw | Long Text | Cleaned article markdown |
| core_url | Text | Original article URL |
| source_id | Text | Publisher name |
| social_status | Select | pending → synced |

### P5 Social Posts (tbllJMN2QBPJoG3jA)
| Field | Type | Description |
|-------|------|-------------|
| source_record_id | Text | Links to Decoration table |
| Name | Text | Headline (display name) |
| headline | Text | Story headline |
| label | Text | Category label |
| b1 | Text | Bullet 1 |
| b2 | Text | Bullet 2 |
| b3 | Text | Bullet 3 |
| image_raw_url | Text | Image URL |
| Raw | Long Text | Cleaned content |
| publish_status | Select | ready → processing → published |
| Order | Number | Slot order (1-5) |

---

*Document generated: December 23, 2025*
*Last updated: December 23, 2025*
