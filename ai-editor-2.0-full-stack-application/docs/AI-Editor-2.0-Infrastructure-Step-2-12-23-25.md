# AI Editor 2.0 Infrastructure - Step 2: Slot Selection Workflow

**Document:** AI-Editor-2.0-Infrastructure-Step-2-12-23-25.md
**Date:** December 23, 2025
**Purpose:** Complete node-by-node analysis of Step 2: Slot Selection workflow

---

## Workflow Overview

**Workflow Name:** STEP 2 - AI Editor Slot Agent Selects
**Workflow ID:** `SZmPztKNEmisG3Zf`
**Total Nodes:** 30
**Schedule:** `15 2 * * 2-6` (9:15 PM EST, Monday-Friday)

### Purpose
Five sequential Claude AI agents each select the best story for their assigned slot, with cumulative tracking of selected companies, sources, and story IDs to enforce editorial diversity rules.

### AI Model
- **Model:** `claude-sonnet-4-5-20250929`
- **Provider:** Anthropic
- **Temperature:** 0.5 (agents), 0.7 (subject line)
- **Max Tokens:** 2000

---

## Editorial Diversity Rules

| Rule | Description |
|------|-------------|
| Yesterday's Headlines | Don't select stories covering same topics as yesterday's issue |
| No Repeat Companies | Each company appears at most once across all 5 slots |
| Source Diversity | Maximum 2 stories per source per day |
| No Duplicate Stories | Don't select storyIDs already chosen in earlier slots today |
| Slot 1 Two-Day Rule | Slot 1 company can't repeat yesterday's Slot 1 company |

---

## Airtable Tables Referenced

### Input Tables

| Base | Table | Table ID | Purpose |
|------|-------|----------|---------|
| AI Editor 2.0 | Pre-Filter Log | `tbl72YMsm9iRHj3sp` | Slot candidates from Step 1 |
| AI Editor 2.0 | Selected Slots | `tblzt2z7r512Kto3O` | Yesterday's issue for diversity |

### Output Table

| Base | Table | Table ID | Purpose |
|------|-------|----------|---------|
| AI Editor 2.0 | Selected Slots | `tblzt2z7r512Kto3O` | Today's 5 selected stories |

---

## Slot-Specific Focus Criteria

| Slot | Focus | Freshness |
|------|-------|-----------|
| 1 | AI impact on jobs, economy, stock market, broad societal impact | 0-24 hours |
| 2 | Tier 1 AI companies, economic themes, research | 24-48 hours |
| 3 | Industry verticals (Healthcare, Government, Education, etc.) | 0-7 days |
| 4 | Emerging companies, product launches, fundraising | 0-48 hours |
| 5 | Consumer AI, human interest, ethics, entertainment | 0-7 days |

---

## Node-by-Node Analysis

### Node 1: Schedule Trigger
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

**Purpose:** Triggers at 9:15 PM EST (15 minutes after pre-filter completes).

**Output:** → Connects to "Pull Yesterday Issue"

---

### Node 2: Pull Yesterday Issue
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

### Nodes 3-7: Pull Slot Candidates (Slots 1-5)
**Node Type:** `n8n-nodes-base.airtable`
**Version:** 2.1

Each node pulls pre-filtered candidates for its specific slot.

#### Pull Slot 1 Candidates
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

#### Pull Slot 2-5 Candidates
Similar configuration with `{slot}=2`, `{slot}=3`, etc.

**Freshness Filters by Slot:**
- Slot 1: Last 1 day
- Slot 2: Last 2 days
- Slot 3: Last 7 days
- Slot 4: Last 2 days
- Slot 5: Last 7 days

---

### Nodes 8-12: Merge Slot Inputs (Slots 1-5)
**Node Type:** `n8n-nodes-base.merge`
**Version:** 3

Each merge node combines:
1. Slot candidates from Pre-Filter Log
2. Yesterday's issue (for context)
3. Previously selected stories from earlier slots (cumulative tracking)

**Purpose:** Provides complete context for each slot agent.

---

### Nodes 13-17: Prepare Slot Context (Slots 1-5)
**Node Type:** `n8n-nodes-base.code`
**Version:** 2

#### Prepare Slot 1 Context
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

#### Prepare Slot 2-5 Context
Each subsequent slot context includes cumulative tracking from previous slots:
- `selectedToday`: Array of storyIDs already selected
- `selectedCompanies`: Array of companies already featured
- `selectedSources`: Array of sources already used

---

### Nodes 18-22: Slot Agent (Slots 1-5)
**Node Type:** `@n8n/n8n-nodes-langchain.agent`
**Version:** 1.7

**AI Model Configuration:**
- **Model:** `claude-sonnet-4-5-20250929`
- **Temperature:** 0.5
- **Max Tokens:** 2000

#### Slot 1 Agent
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

#### Slot 2 Agent Focus
- Tier 1 AI companies
- Economic themes, research
- 24-48 hour freshness

#### Slot 3 Agent Focus
- Industry verticals
- Healthcare, Government, Education, etc.
- 0-7 day freshness

#### Slot 4 Agent Focus
- Emerging AI companies
- Product launches, fundraising
- 0-48 hour freshness

#### Slot 5 Agent Focus
- Consumer AI, human interest
- Ethics, entertainment, quirky uses
- 0-7 day freshness

---

### Nodes 23-27: Remove Slot Stories (Slots 1-5)
**Node Type:** `n8n-nodes-base.code`
**Version:** 2

Each node processes the agent's selection and updates cumulative tracking.

#### Remove Slot 1 Stories
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

### Node 28: Assembly Code
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

### Node 29: Subject Line Generator
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

### Node 30: Prepare Write Data
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

### Node 31: Write AI Editor - Selected Slots
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

## Step 2 Data Flow Summary

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

## API Credentials for Step 2

### Airtable
| Key | Value |
|-----|-------|
| API Key | `[REDACTED]` |
| Base: AI Editor 2.0 | `appglKSJZxmA9iHpl` |

### Anthropic Claude
| Key | Value |
|-----|-------|
| Model | `claude-sonnet-4-5-20250929` |
| API Key | Environment variable: `ANTHROPIC_API_KEY` |

---

## Selected Slots Table Schema (tblzt2z7r512Kto3O)

| Field | Type | Description |
|-------|------|-------------|
| issue_id | Text | Unique issue identifier (e.g., `pivot5_2024-12-23`) |
| issue_date | Text | Display date (e.g., `Pivot 5 - Dec 23`) |
| subject_line | Text | Email subject line (max 60 chars) |
| status | Select | `pending`, `decorated`, `sent` |
| social_post_status | Select | `pending`, `synced` |
| slot_1_storyId | Text | Selected story ID for slot 1 |
| slot_1_pivotId | Text | Link to Articles table |
| slot_1_headline | Text | Headline for slot 1 |
| slot_2_storyId | Text | Selected story ID for slot 2 |
| slot_2_pivotId | Text | Link to Articles table |
| slot_2_headline | Text | Headline for slot 2 |
| slot_3_storyId | Text | Selected story ID for slot 3 |
| slot_3_pivotId | Text | Link to Articles table |
| slot_3_headline | Text | Headline for slot 3 |
| slot_4_storyId | Text | Selected story ID for slot 4 |
| slot_4_pivotId | Text | Link to Articles table |
| slot_4_headline | Text | Headline for slot 4 |
| slot_5_storyId | Text | Selected story ID for slot 5 |
| slot_5_pivotId | Text | Link to Articles table |
| slot_5_headline | Text | Headline for slot 5 |

---

## Migration Status: n8n to Full-Stack Application

**Last Updated:** December 30, 2025

### Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Python Worker (Step 2) | **IMPLEMENTED** | `/app/workers/jobs/slot_selection.py` |
| Claude Client Utility | **IMPLEMENTED** | `/app/workers/utils/claude.py` |
| Airtable Client Methods | **IMPLEMENTED** | `/app/workers/utils/airtable.py` |
| RQ Scheduler Config | **IMPLEMENTED** | Schedule: 11:55 PM EST (4:55 UTC) |
| Dashboard UI (Step View) | **IMPLEMENTED** | `/app/src/app/(dashboard)/step/[id]/page.tsx` |
| API Endpoints | **IMPLEMENTED** | Job trigger via `/api/jobs` |

### Python Worker Implementation (`slot_selection.py`)

The Step 2 worker at `/app/workers/jobs/slot_selection.py` implements the full slot selection pipeline:

```python
# Key function signature
def select_slots() -> dict:
    """
    Returns: {slots_filled: int, subject_line: str, record_id: str, errors: list}
    """
```

**Features Implemented:**
- Sequential processing of 5 slots with cumulative state tracking
- Diversity rule enforcement (no repeat companies, max 2 sources/day)
- Yesterday's issue lookup for topic avoidance
- Subject line generation from selected headlines
- Error handling with per-slot error tracking

**Claude Model Used:**
- Worker uses `claude-sonnet-4-20250514` (verify against CLAUDE.md for current model)
- Model specified in `/app/workers/utils/claude.py`

### Key Differences: n8n vs Python Worker

| Aspect | n8n Workflow | Python Worker |
|--------|--------------|---------------|
| Schedule | 9:15 PM EST (15 min after Step 1) | 11:55 PM EST |
| Model | `claude-sonnet-4-5-20250929` | `claude-sonnet-4-20250514` |
| Prompt Loading | Hardcoded in nodes | `ClaudeClient.select_slot()` |
| Error Handling | Per-node failure | Try/catch with error array |
| Output | Airtable record creation | Same + return dict |

### Known Issues / Bugs to Fix

1. **max_records Limit Bug** (From Slot-1-2-Cross-Reference doc)
   - Full-stack app uses `max_records=100` in some queries
   - n8n has no limit and fetches all records (e.g., 299 vs 100)
   - This causes fewer candidates to be available for selection
   - **Fix Required:** Remove `max_records` parameter or increase significantly

2. **Model Version Mismatch**
   - CLAUDE.md specifies `claude-sonnet-4-5-20250929`
   - Worker may use older model - verify and update `claude.py`

### Migration Approach (Followed from Step 1 Pattern)

Step 2 followed the same migration pattern as Step 1 (Pre-Filter):

1. **Airtable Operations** via `AirtableClient` class
   - `get_yesterday_issue()` - Pull yesterday's Selected Slots record
   - `get_prefilter_candidates(slot, freshness_days)` - Get slot candidates
   - `write_selected_slots(issue_data)` - Create today's issue record

2. **AI Operations** via `ClaudeClient` class
   - `select_slot(slot, candidates, yesterday_data, cumulative_state)` - Agent selection
   - `generate_subject_line(headlines)` - Subject line generation

3. **Job Configuration** for RQ Scheduler
   ```python
   JOB_CONFIG = {
       "func": select_slots,
       "trigger": "cron",
       "hour": 4,
       "minute": 55,
       "day_of_week": "tue-sat",
       "id": "step2_slot_selection"
   }
   ```

### Frontend Integration

The Step 2 job can be triggered from the dashboard UI:

- **Route:** `/step/2`
- **Component:** `/app/src/app/(dashboard)/step/[id]/page.tsx`
- **Job Mapping:** Step ID `2` maps to job name `slot_selection`

---

*Document generated: December 23, 2025*
*Migration status updated: December 30, 2025*
