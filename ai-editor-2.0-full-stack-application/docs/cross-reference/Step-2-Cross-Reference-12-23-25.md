# Step 2: Slot Selection Cross-Reference Analysis

**Document:** Step-2-Cross-Reference-12-23-25.md
**Date:** December 23, 2025
**Infrastructure Doc:** AI-Editor-2.0-Infrastructure-Step-2-12-23-25.md
**Implementation File:** `/app/src/lib/airtable.ts`

---

## Summary

| Category | Status |
|----------|--------|
| Dashboard READ Operations | ✅ Partially Implemented |
| Python Worker Job | ❌ Not Implemented |
| Claude AI Integration | ❌ Not Implemented |
| Airtable WRITE Operations | ❌ Not Implemented |
| Sequential Agent Orchestration | ❌ Not Implemented |

---

## Critical Architecture: Sequential Agent Pattern

Step 2 uses a **sequential agent pattern** where each slot agent:
1. Receives context from all previous agents
2. Knows which stories/companies/sources were already selected
3. Enforces cumulative diversity rules

This is fundamentally different from parallel processing and requires careful state management in the Python worker.

```
Slot 1 Agent → Slot 2 Agent → Slot 3 Agent → Slot 4 Agent → Slot 5 Agent
     ↓              ↓              ↓              ↓              ↓
 selectedToday: [] → [A] ───────→ [A,B] ─────→ [A,B,C] ───→ [A,B,C,D]
 selectedCompanies: same cumulative pattern
 selectedSources: same cumulative pattern
```

---

## Node-by-Node Cross-Reference

### Node 1: Schedule Trigger
**Infrastructure:** `15 2 * * 2-6` (9:15 PM EST, Mon-Fri)
**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker with Redis Queue (RQ) scheduled job
- Cron expression: `15 2 * * 2-6` UTC (9:15 PM EST)
- Must run 15 minutes AFTER Step 1 completes
- File: `workers/jobs/slot_selection.py`

---

### Node 2: Pull Yesterday Issue
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tblzt2z7r512Kto3O` (Selected Slots)
- Sort: `issue_date` DESC
- Max Records: 1
- Fields: `issue_date`, `slot_X_headline`, `slot_X_storyId` (X=1-5)

**Implementation:** ⚠️ Partial in `getSelectedSlots()` (lines 390-467)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Base ID | `appglKSJZxmA9iHpl` | `process.env.AI_EDITOR_BASE_ID` | ✅ |
| Table ID | `tblzt2z7r512Kto3O` | `process.env.AI_EDITOR_SELECTED_SLOTS_TABLE` | ✅ |
| Filter | None (gets latest) | None | ✅ |
| Sort | `issue_date` DESC | `issue_date` DESC | ✅ |
| Max Records | 1 | 1 | ✅ |
| Fields | 11 (date + 10 slot fields) | 17 (more fields) | ✅ |

**Gap:** Implementation returns latest issue but Step 2 needs this as "yesterday's issue" for diversity rules. If Step 1/2 run same night, latest may be today's pending issue.

**Recommendation:** Add date filter to get specifically yesterday's SENT issue:
```python
filter_by_formula = f"AND({{status}}='sent', {{issue_date}}='{yesterday_date}')"
```

---

### Nodes 3-7: Pull Slot Candidates
**Infrastructure:** Pull Pre-Filter Log entries for each slot (1-5)

- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tbl72YMsm9iRHj3sp` (Pre-Filter Log)
- Filter: `AND({slot}=X, IS_AFTER({date_prefiltered}, DATEADD(TODAY(), -N, 'days')))`

**Implementation:** ⚠️ Partial in `getPreFilterLog()` (lines 347-369)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Base ID | `appglKSJZxmA9iHpl` | `process.env.AI_EDITOR_BASE_ID` | ✅ |
| Table ID | `tbl72YMsm9iRHj3sp` | `process.env.AI_EDITOR_PREFILTER_LOG_TABLE` | ✅ |
| Filter | Per-slot + freshness | None (gets all) | ❌ |
| Fields | 6 fields | 8 fields | ✅ |

**Gaps:**
1. No per-slot filtering - returns all slots
2. No freshness filtering - returns all dates
3. Dashboard use case vs. Worker use case differ

**Action Required for Python Worker:**
```python
def get_slot_candidates(slot: int, freshness_days: int) -> List[dict]:
    """Get pre-filter candidates for a specific slot"""
    filter_formula = f"AND({{slot}}={slot}, IS_AFTER({{date_prefiltered}}, DATEADD(TODAY(), -{freshness_days}, 'days')))"
    # ...
```

---

### Nodes 8-12: Merge Slot Inputs
**Infrastructure:** Combine candidates with yesterday's issue and cumulative tracking
**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker: merge logic for each slot context
- Cumulative tracking state management

---

### Nodes 13-17: Prepare Slot Context
**Infrastructure:** JavaScript code that prepares agent prompt context
**Implementation Status:** ❌ Not Implemented

**Critical Context Elements:**
| Element | Purpose |
|---------|---------|
| `candidates` | Array of story objects for this slot |
| `yesterdayHeadlines` | 5 headlines to avoid similar topics |
| `slot1Company` | Slot 1 specific: yesterday's company for 2-day rule |
| `selectedToday` | Cumulative: storyIDs already selected today |
| `selectedCompanies` | Cumulative: companies already featured today |
| `selectedSources` | Cumulative: sources already used today |

**Action Required:**
```python
def prepare_slot_context(
    slot: int,
    candidates: List[dict],
    yesterday_data: dict,
    cumulative_state: dict
) -> dict:
    """Prepare context for slot agent"""
    pass
```

---

### Nodes 18-22: Slot Agent (Claude)
**Infrastructure:**
- Model: `claude-sonnet-4-5-20250929`
- Temperature: 0.5
- Max Tokens: 2000
- 5 sequential agent calls

**Implementation Status:** ❌ Not Implemented

**Critical Missing Component:** This is the core AI functionality. Each agent:
1. Receives slot-specific system prompt with focus criteria
2. Receives candidates + context
3. Returns JSON with selection + reasoning

**Action Required:**
```python
def call_slot_agent(
    slot: int,
    context: dict,
    anthropic_client: Anthropic
) -> dict:
    """Call Claude agent for slot selection"""

    system_prompt = get_slot_system_prompt(slot, context)

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        temperature=0.5,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Select the best story for Slot {slot}."
        }]
    )

    return json.loads(response.content[0].text)
```

**Slot Focus Criteria (from Infrastructure):**
| Slot | Focus | Freshness |
|------|-------|-----------|
| 1 | Jobs, economy, stock market, broad impact | 0-24 hours |
| 2 | Tier 1 AI companies, research | 24-48 hours |
| 3 | Industry verticals | 0-7 days |
| 4 | Emerging companies, fundraising | 0-48 hours |
| 5 | Consumer AI, human interest, ethics | 0-7 days |

---

### Nodes 23-27: Remove Slot Stories
**Infrastructure:** Update cumulative tracking after each selection
**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def update_cumulative_state(
    selection: dict,
    cumulative_state: dict
) -> dict:
    """Update tracking after slot selection"""
    cumulative_state['selectedToday'].append(selection['selected_storyId'])
    cumulative_state['selectedCompanies'].append(selection['company'])
    cumulative_state['selectedSources'].append(selection['source_id'])
    return cumulative_state
```

---

### Node 28: Assembly Code
**Infrastructure:** Combine all 5 slot selections into issue record
**Implementation Status:** ❌ Not Implemented

**Output Fields:**
```python
issue_record = {
    "issue_id": f"pivot5_{today.isoformat()}",
    "issue_date": f"Pivot 5 - {today.strftime('%b %d')}",
    "status": "pending",
    "slot_1_storyId": slot1_selection['selected_storyId'],
    "slot_1_pivotId": slot1_selection['selected_pivotId'],
    "slot_1_headline": slot1_selection['selected_headline'],
    # ... slots 2-5
}
```

---

### Node 29: Subject Line Generator
**Infrastructure:**
- Model: `claude-sonnet-4-5-20250929`
- Temperature: 0.7 (higher for creativity)
- Requirements: Max 60 chars, reference 1-2 key stories

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def generate_subject_line(headlines: List[str], anthropic_client: Anthropic) -> str:
    """Generate email subject line from 5 headlines"""

    prompt = f"""Generate a compelling email subject line for this daily AI newsletter.

TODAY'S HEADLINES:
1. {headlines[0]}
2. {headlines[1]}
3. {headlines[2]}
4. {headlines[3]}
5. {headlines[4]}

REQUIREMENTS:
- Maximum 60 characters
- Create urgency and curiosity
- Reference 1-2 key stories
- Avoid clickbait, be substantive
- Match professional newsletter tone

Return ONLY the subject line, no quotes or explanation."""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=100,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()
```

---

### Nodes 30-31: Write Selected Slots
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tblzt2z7r512Kto3O` (Selected Slots)
- Operation: Create record
- 19 fields mapped

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def write_selected_slots(issue_record: dict) -> str:
    """Write new issue to Selected Slots table"""
    # Airtable CREATE operation
    pass
```

---

## Environment Variables Required

### Currently Configured
```bash
AIRTABLE_API_KEY=✅ Configured
AI_EDITOR_BASE_ID=✅ Configured (appglKSJZxmA9iHpl)
AI_EDITOR_SELECTED_SLOTS_TABLE=✅ Configured (tblzt2z7r512Kto3O)
AI_EDITOR_PREFILTER_LOG_TABLE=✅ Configured (tbl72YMsm9iRHj3sp)
```

### Missing
```bash
ANTHROPIC_API_KEY=❌ Required for Claude agents
```

---

## Python Worker Specification

**File:** `workers/jobs/slot_selection.py`
**Queue:** Redis Queue (RQ)
**Schedule:** `15 2 * * 2-6` UTC (9:15 PM EST)
**Dependency:** Must run AFTER Step 1 Pre-Filter completes

### Required Functions

```python
# 1. Main job function
def select_slots() -> dict:
    """Step 2: Slot Selection Job - 5 sequential Claude agents"""
    pass

# 2. Data retrieval
def get_yesterday_issue() -> dict:
    """Get yesterday's sent issue for diversity rules"""
    pass

def get_slot_candidates(slot: int, freshness_days: int) -> List[dict]:
    """Get pre-filter candidates for specific slot"""
    pass

# 3. Context preparation
def extract_yesterday_data(issue: dict) -> dict:
    """Extract headlines, storyIds for diversity checking"""
    pass

def prepare_slot_context(slot: int, candidates: List[dict],
                         yesterday_data: dict, cumulative_state: dict) -> dict:
    """Prepare agent prompt context"""
    pass

# 4. Claude AI agents
def get_slot_system_prompt(slot: int, context: dict) -> str:
    """Get slot-specific system prompt"""
    pass

def call_slot_agent(slot: int, context: dict) -> dict:
    """Call Claude agent for slot selection"""
    pass

def generate_subject_line(headlines: List[str]) -> str:
    """Generate subject line from 5 headlines"""
    pass

# 5. State management
def update_cumulative_state(selection: dict, cumulative_state: dict) -> dict:
    """Update tracking after each slot selection"""
    pass

# 6. Output
def assemble_issue_record(selections: List[dict], subject_line: str) -> dict:
    """Combine 5 selections into issue record"""
    pass

def write_selected_slots(issue_record: dict) -> str:
    """Write to Airtable Selected Slots table"""
    pass
```

### Orchestration Flow

```python
def select_slots():
    # 1. Get yesterday's issue
    yesterday_issue = get_yesterday_issue()
    yesterday_data = extract_yesterday_data(yesterday_issue)

    # 2. Initialize cumulative state
    cumulative_state = {
        "selectedToday": [],
        "selectedCompanies": [],
        "selectedSources": []
    }

    # 3. Sequential slot selection
    selections = []
    freshness_map = {1: 1, 2: 2, 3: 7, 4: 2, 5: 7}

    for slot in range(1, 6):
        # Get candidates for this slot
        candidates = get_slot_candidates(slot, freshness_map[slot])

        # Prepare context with cumulative tracking
        context = prepare_slot_context(slot, candidates, yesterday_data, cumulative_state)

        # Call Claude agent
        selection = call_slot_agent(slot, context)
        selections.append(selection)

        # Update cumulative state
        cumulative_state = update_cumulative_state(selection, cumulative_state)

    # 4. Generate subject line
    headlines = [s['selected_headline'] for s in selections]
    subject_line = generate_subject_line(headlines)

    # 5. Assemble and write
    issue_record = assemble_issue_record(selections, subject_line)
    record_id = write_selected_slots(issue_record)

    return {"record_id": record_id, "selections": selections}
```

---

## Critical Issues Found

### Issue 1: No Sequential Agent Orchestration
**Problem:** The current implementation has no mechanism for sequential agent calls with cumulative state
**Impact:** Cannot replicate the diversity rule enforcement from n8n
**Resolution:** Python worker must maintain state between agent calls

### Issue 2: Dashboard Shows Read-Only View
**Location:** `getSelectedSlots()` in `lib/airtable.ts`
**Problem:** Dashboard can only VIEW selected slots, not CREATE them
**Impact:** Dashboard is read-only for Step 2 output
**Resolution:** This is correct for dashboard - Python worker handles creation

### Issue 3: No Pre-Filter Log Slot Filtering
**Location:** `getPreFilterLog()` lines 347-369
**Problem:** Returns all pre-filter entries, not filtered by slot
**Impact:** Dashboard shows all candidates; worker needs per-slot filtering
**Resolution:** Worker implements slot-specific queries

---

## Implementation Priority

1. **High Priority (Worker Core):**
   - [ ] Create `workers/jobs/slot_selection.py`
   - [ ] Implement Anthropic Claude client
   - [ ] Implement 5 sequential agent calls
   - [ ] Implement cumulative state tracking
   - [ ] Implement subject line generation

2. **Medium Priority (Dashboard Updates):**
   - [ ] Add "Run Step 2" manual trigger button
   - [ ] Display agent reasoning for each slot
   - [ ] Show cumulative diversity tracking

3. **Low Priority (Enhancements):**
   - [ ] Add slot-specific filtering to Pre-Filter Log view
   - [ ] Display yesterday's issue for context

---

## Anthropic API Configuration

**Model:** `claude-sonnet-4-5-20250929`
**Endpoint:** `https://api.anthropic.com/v1/messages`
**Headers:**
```python
headers = {
    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}
```

**Agent Temperature:** 0.5 (focused selection)
**Subject Line Temperature:** 0.7 (creative)
**Max Tokens:** 2000 (agents), 100 (subject line)

---

*Cross-reference generated: December 23, 2025*
