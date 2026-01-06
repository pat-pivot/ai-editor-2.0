# STEP 3 DECORATION IMPLEMENTATION ANALYSIS

**Date:** January 1, 2026
**Source:** Agent analysis of codebase vs n8n workflow `HCbd2g852rkQgSqr`
**Updated:** January 1, 2026 - Added specific code line references for gaps

---

## EXECUTIVE SUMMARY

The STEP 3 Decoration implementation in the Python codebase has significant **prompt/output format mismatches** with n8n:

- **Status**: ~85% implemented structurally, but **prompts are OUTDATED**
- **Critical Issue**: Python uses wrong bolding format (Markdown vs HTML)
- **Critical Issue**: Python uses wrong field names (`b1/b2/b3` vs `ai_bullet_1/2/3`)
- **Critical Issue**: Python missing 18 label categories
- **Critical Issue**: Python missing newsletter style variants

---

## 1. SPECIFIC CODE GAPS WITH LINE NUMBERS

### Gap 1: Wrong Bolding Format

**File:** `workers/utils/claude.py`
**Line:** 486

```python
# WRONG (line 486)
prompt = f"""Apply markdown bold (**text**) to 1-2 key phrases in each bullet point.
```

**Should be:**
```python
prompt = f"""Apply HTML bold (<b>text</b>) to one key phrase in each bullet point.
```

### Gap 2: Wrong Bullet Field Names

**File:** `workers/utils/claude.py`
**Lines:** 345, 412-413, 493-495

```python
# WRONG (line 345)
Returns:
    {ai_headline, ai_dek, b1, b2, b3, image_prompt, label}

# WRONG (line 412-413)
Generate all of the above in JSON format with keys: ai_headline, ai_dek, b1, b2, b3, label, image_prompt

# WRONG (line 493-495)
"Bullet with **key phrase** bolded...",
"Another bullet with **important stat** highlighted...",
"Third bullet with **company name** emphasized..."
```

**Should be:**
```python
# Return format
{ai_headline, ai_dek, ai_bullet_1, ai_bullet_2, ai_bullet_3, image_prompt, label}

# JSON keys
Generate all of the above in JSON format with keys: ai_headline, ai_dek, ai_bullet_1, ai_bullet_2, ai_bullet_3, label, image_prompt
```

### Gap 3: Missing 18 Label Categories

**File:** `workers/utils/claude.py`
**Line:** 439, 543

```python
# WRONG (line 439)
6. label: Topic label in ALL CAPS (e.g., "JOBS & ECONOMY", "BIG TECH", "HEALTHCARE AI", "EMERGING TECH", "CONSUMER AI")

# WRONG (line 543)
"label": "AI NEWS",
```

**Should be (18 categories from n8n):**
```
WORK, EDUCATION, INFRASTRUCTURE, POLICY, TALENT, HEALTH, RETAIL,
ENTERPRISE, COMPETITION, FUNDING, SECURITY, TOOLS, SEARCH,
INVESTORS, CHINA, REGULATION, ETHICS, LAWSUITS
```

### Gap 4: Missing "Exactly 2 Sentences" Rule

**File:** `workers/utils/claude.py`
**Line:** 431-437

```python
# MISSING - line 431-437 only says "2 sentences" but not enforced
3. b1: First bullet - Main announcement (2 sentences, max 260 characters). Start with action verb.
4. b2: Second bullet - Key details/context (2 sentences, max 260 characters).
5. b3: Third bullet - Business impact or "why it matters" (2 sentences, max 260 characters).
```

**Should explicitly state (from n8n):**
```
## CRITICAL RULES FOR BULLETS
1. Each bullet MUST be EXACTLY 2 sentences. Not 1. Not 3. Exactly 2.
2. Bullet 1: Lead with the news — what happened, who did it, what changed
3. Bullet 2: Context — why this matters, what it means, relevant background
4. Bullet 3: Forward-looking — implications, what to watch, competitive dynamics
```

### Gap 5: Missing CEO Audience Context

**File:** `workers/utils/claude.py`
**Line:** 418-443 (fallback prompt)

The Python fallback prompt at lines 418-443 is missing the CEO audience context that n8n has:

**Missing (add to prompt):**
```
## AUDIENCE
- CEOs, founders, general managers, and senior business leaders
- They are busy, strategic thinkers who want actionable insights
- They care about business impact, competitive dynamics, and what matters for decision-making

## VOICE & STYLE
- Confident, clear, informed — like a trusted advisor briefing an executive
- Present tense, active voice
- No jargon, no hedging (avoid "could/might/possibly")
- Avoid vague terms like "impact" or "transformation" — stick to concrete business consequences
```

### Gap 6: Missing Newsletter Style Variants

**File:** `workers/jobs/decoration.py`

Python has NO implementation of newsletter style variants. n8n has three:

```javascript
// n8n has this - Python does NOT
const styleByNewsletter = {
  pivot_build: "Audience: builders, product managers...",
  pivot_invest: "Audience: investors and markets-focused...",
  pivot_ai: "Audience: professionals following the AI field..."
}
```

---

## 2. CURRENT FILE STRUCTURE

```
workers/jobs/decoration.py          (Main decoration job)
workers/jobs/image_generation.py    (Image generation job - separate from n8n)
workers/utils/claude.py              (Claude API client with decoration methods)
workers/utils/gemini.py              (Gemini for content cleaning)
workers/utils/images.py              (Image generation and processing)
workers/utils/airtable.py            (Airtable operations)
workers/utils/prompts.py             (Database prompt loading)
```

---

## 3. KEY IMPLEMENTATION DETAILS

### A. Headline Generation
- **Location**: `claude.py` → `decorate_story()` method (lines 334-461)
- **Status**: IMPLEMENTED but with OUTDATED prompts
- **Prompt Loading**: Attempts to load `headline_generator` from database, falls back to hardcoded
- **Model**: `claude-sonnet-4-5-20250929` (correct per CLAUDE.md)
- **Temperature**: 0.5

### B. Bullet Generation (3 bullets)
- **Location**: `claude.py` → `decorate_story()` method
- **Status**: IMPLEMENTED but with WRONG field names (`b1/b2/b3`)
- **Prompt Key**: `bullet_generator`
- **Implementation**: Combined with headline generation in single Claude call
- **Output Format**: `b1`, `b2`, `b3` fields (SHOULD BE `ai_bullet_1/2/3`)

### C. Bold Formatting
- **Location**: `claude.py` → `apply_bolding()` method (lines 462-525)
- **Status**: IMPLEMENTED but with WRONG format (Markdown `**` instead of HTML `<b>`)
- **Prompt Key**: `bold_formatter`
- **Model**: `claude-sonnet-4-5-20250929`
- **Temperature**: 0.3

### D. Image Generation
- **Location**: `workers/jobs/image_generation.py` + `utils/images.py`
- **Status**: IMPLEMENTED
- **Pipeline**:
  1. Generate: Gemini Imagen 3 (primary) → GPT Image 1.5 (fallback)
  2. Optimize: Cloudinary (636px width)
  3. Upload: Cloudflare Images

---

## 4. N8N NODES VS PYTHON IMPLEMENTATION

| n8n Node | Purpose | Python Implementation | Status |
|----------|---------|----------------------|--------|
| Pull Latest Issue | Get pending issue | `airtable.get_pending_issue()` | ✓ MATCH |
| Prepare Story Lookups | Extract slot data | Inline in decoration.py | ✓ MATCH |
| Loop Stories | Process each slot | For loop (1-5) | ✓ MATCH |
| Pull Story Details | Get article markdown | `airtable.get_article_by_pivot_id()` | ✓ MATCH |
| Pull NIS Data | Get Newsletter Selects | `airtable.get_newsletter_selects()` | ⚠️ NOT USED |
| Merge Story Context | Combine data | Inline (lines 113-118) | ✓ MATCH |
| Build Decoration Prompt | Construct prompt with style | Inline (lines 130-160) | ⚠️ MISSING STYLES |
| Content Creator | Claude generation | `claude.decorate_story()` | ⚠️ OUTDATED PROMPT |
| Parse Content Creator | Extract JSON | Inline + `_parse_decoration_response()` | ⚠️ WRONG FIELDS |
| Bolding Pass | Add bold tags | `claude.apply_bolding()` | ⚠️ WRONG FORMAT |
| Normalize Decorated | Prepare for write | Inline (lines 147-164) | ⚠️ WRONG FIELDS |
| Write Decoration | Save to Airtable | `airtable.write_decoration()` | ⚠️ WRONG FIELDS |
| Mark Issue Decorated | Update status | Inline (lines 179-197) | ✓ MATCH |

---

## 5. CRITICAL FIXES REQUIRED

### Priority 1 (Must Fix)

| Fix | File | Lines | Change |
|-----|------|-------|--------|
| Bolding format | claude.py | 486 | `**text**` → `<b>text</b>` |
| Bullet field names | claude.py | 345, 412-413 | `b1/b2/b3` → `ai_bullet_1/2/3` |
| Label categories | claude.py | 439 | Add all 18 n8n categories |
| 2-sentence rule | claude.py | 431-437 | Add "EXACTLY 2 sentences" |
| CEO audience | claude.py | 418 | Add audience context |

### Priority 2 (High)

| Fix | File | Lines | Change |
|-----|------|-------|--------|
| Newsletter styles | decoration.py | N/A | Add pivot_ai/build/invest variants |
| Newsletter Selects | decoration.py | N/A | Call `get_newsletter_selects()` |
| Field mapping | decoration.py | Airtable write | Map to `ai_bullet_1/2/3` |

---

## 6. PROMPT CONFIGURATION

| Prompt Key | Purpose | Model | Temp | Issues |
|------------|---------|-------|------|--------|
| headline_generator | Main decoration | Claude Sonnet 4.5 | 0.5 | OUTDATED - missing CEO context |
| bullet_generator | 3 bullets | Claude Sonnet 4.5 | 0.5 | OUTDATED - wrong field names |
| bold_formatter | Bold formatting | Claude Sonnet 4.5 | 0.3 | WRONG - uses Markdown not HTML |
| image_prompt | Image description | Claude Sonnet 4.5 | 0.5 | OK |
| content_cleaner | Remove nav/ads | Gemini 3 Flash | 0.1 | OK |

---

## 7. AIRTABLE FIELD MAPPING

### Current (WRONG)
```python
decoration_data = {
    "storyID": story_id,
    "pivotId": pivot_id,
    "ai_headline": decoration.get("ai_headline"),
    "ai_dek": decoration.get("ai_dek"),
    "ai_bullet_1": decoration.get("b1"),  # WRONG KEY
    "ai_bullet_2": decoration.get("b2"),  # WRONG KEY
    "ai_bullet_3": decoration.get("b3"),  # WRONG KEY
    "label": decoration.get("label"),
    "image_status": "pending",
}
```

### Should Be (CORRECT)
```python
decoration_data = {
    "storyID": story_id,
    "pivotId": pivot_id,
    "ai_headline": decoration.get("ai_headline"),
    "ai_dek": decoration.get("ai_dek"),
    "ai_bullet_1": decoration.get("ai_bullet_1"),  # CORRECT
    "ai_bullet_2": decoration.get("ai_bullet_2"),  # CORRECT
    "ai_bullet_3": decoration.get("ai_bullet_3"),  # CORRECT
    "label": decoration.get("label"),
    "image_status": "needs_image",  # n8n uses this value
}
```

---

## 8. MODEL VERSIONS (Verified Correct)

| Model | Location | Status |
|-------|----------|--------|
| `claude-sonnet-4-5-20250929` | claude.py line 30 | ✓ Correct |
| `gemini-3-flash-preview` | gemini.py line 71 | ✓ Correct |

---

## 9. EXECUTION FLOW COMPARISON

### N8N Workflow
```
1. Pull Latest Issue (filter: status='pending')
2. Prepare Story Lookups
3. Loop Stories (1-5)
4. Pull Story Details (Articles)
5. Pull NIS Data (Newsletter Selects) ← MISSING IN PYTHON
6. Merge Story Context
7. Build Decoration Prompt (with newsletter styles) ← MISSING STYLES IN PYTHON
8. Content Creator (Claude) ← OUTDATED PROMPT IN PYTHON
9. Parse Content Creator ← WRONG FIELD NAMES IN PYTHON
10. Bolding Pass (Claude) ← WRONG FORMAT IN PYTHON
11. Normalize Decorated ← WRONG FIELD NAMES IN PYTHON
12. Merge Results
13. Write Decoration ← WRONG FIELD NAMES IN PYTHON
14. Mark Issue Decorated
```

### Python Implementation (Current State)
```
1. Get pending issue ✓
2. For each slot 1-5 ✓
3. Extract slot data ✓
4. Get article by pivotId ✓
5. [MISSING] Pull NIS Data
6. Clean content via Gemini ✓
7. Generate decoration via Claude ⚠️ (OUTDATED PROMPT)
8. Apply bolding ⚠️ (WRONG FORMAT - Markdown)
9. Write decoration record ⚠️ (WRONG FIELD NAMES)
10. Update issue status ✓
```

---

## 10. SUMMARY TABLE

| Component | N8N Has | Python Has | Match | Fix Required |
|-----------|---------|-----------|-------|--------------|
| Headline Generation | ✓ | ✓ | PARTIAL | Add CEO context |
| 3 Bullet Points | ✓ | ✓ | NO | Fix field names |
| Bold Formatting | HTML `<b>` | Markdown `**` | NO | Change to HTML |
| 18 Label Categories | ✓ | ✗ | NO | Add all 18 |
| 2-Sentence Rule | ✓ | ✗ | NO | Add explicit rule |
| Newsletter Styles | ✓ | ✗ | NO | Implement 3 styles |
| Newsletter Selects Data | ✓ | ✗ | NO | Integrate data source |
| Image Generation | ✓ | ✓ | YES | None |
| Image Optimization | ✓ | ✓ | YES | None |
| Image Upload | ✓ | ✓ | YES | None |
| Airtable Operations | ✓ | ✓ | PARTIAL | Fix field names |
| Error Handling | PARTIAL | PARTIAL | YES | None |
| Database Prompts | ✓ | ✓ | YES | Update prompts |
| Status Tracking | ✓ | ✓ | YES | None |
