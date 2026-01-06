# Step 3: Decoration Cross-Reference Analysis

**Document:** Step-3-Cross-Reference-12-23-25.md
**Date:** December 23, 2025
**Infrastructure Doc:** AI-Editor-2.0-Infrastructure-Step-3-12-23-25.md
**Implementation File:** `/app/src/lib/airtable.ts`

---

## Summary

| Category | Status |
|----------|--------|
| Dashboard READ Operations | ✅ Implemented |
| Python Worker Job (Text Decoration) | ❌ Not Implemented |
| Python Worker Job (Image Generation) | ❌ Not Implemented |
| Gemini AI Integration (Content Cleaning) | ❌ Not Implemented |
| Claude AI Integration (Content Creation) | ❌ Not Implemented |
| Cloudflare Image Upload | ❌ Not Implemented |
| Airtable WRITE Operations | ❌ Not Implemented |

---

## Critical Architecture: Two-Phase Processing

Step 3 runs in **two phases** at different times:

```
Phase 1: Text Decoration (9:25 PM EST)
├── Pull pending issue from Selected Slots
├── Expand into 5 individual slots
├── For each slot:
│   ├── Lookup article markdown by pivotId
│   ├── Clean content (Gemini)
│   ├── Generate headline/dek/bullets (Claude)
│   ├── Apply bold formatting (Claude)
│   └── Write to Decoration table (image_status='needs_image')

Phase 2: Image Generation (9:30 PM EST)
├── Get stories with image_status='needs_image'
└── For each story:
    ├── Generate image (Gemini primary)
    ├── Fallback to GPT Image 1.5 if needed
    ├── Upload to Cloudflare CDN
    └── Update decoration record (image_status='generated')
```

---

## Node-by-Node Cross-Reference

### Node 1: Schedule Trigger
**Infrastructure:** Two cron expressions
- `25 2 * * 2-6` (9:25 PM EST) - Text decoration
- `30 2 * * 2-6` (9:30 PM EST) - Image generation

**Implementation Status:** ❌ Not Implemented

**Action Required:**
- Python worker with Redis Queue (RQ) scheduled jobs
- File: `workers/jobs/decoration.py` (text)
- File: `workers/jobs/image_generation.py` (images)

---

### Node 2: Pull Latest Issue
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tblzt2z7r512Kto3O` (Selected Slots)
- Filter: `{status}='pending'`
- Sort: `issue_date` DESC
- Max Records: 1

**Implementation:** ⚠️ Partial in `getSelectedSlots()` (lines 390-467)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Base ID | `appglKSJZxmA9iHpl` | `process.env.AI_EDITOR_BASE_ID` | ✅ |
| Table ID | `tblzt2z7r512Kto3O` | `process.env.AI_EDITOR_SELECTED_SLOTS_TABLE` | ✅ |
| Filter | `{status}='pending'` | None | ❌ |
| Sort | `issue_date` DESC | `issue_date` DESC | ✅ |
| Max Records | 1 | 1 | ✅ |

**Gap:** Dashboard returns latest issue regardless of status. Step 3 specifically needs `status='pending'` to find today's issue awaiting decoration.

**Recommendation:** Add filter for Python worker:
```python
filter_by_formula = "{status}='pending'"
```

---

### Node 3: Expand Slots
**Infrastructure:** JavaScript code that expands single issue into 5 slot items
**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def expand_slots(issue: dict) -> List[dict]:
    """Expand issue into 5 individual slot items"""
    slots = []
    for i in range(1, 6):
        slots.append({
            "slot_order": i,
            "pivotId": issue[f"slot_{i}_pivotId"],
            "headline": issue[f"slot_{i}_headline"],
            "issue_id": issue["issue_id"],
            "issue_date": issue["issue_date"],
            "subject_line": issue["subject_line"]
        })
    return slots
```

---

### Node 4: Split In Batches
**Infrastructure:** Batch size 1 for sequential processing
**Implementation Status:** ❌ Not Implemented (Python worker needed)

**Action Required:**
- Python worker: process slots one at a time to avoid API rate limits

---

### Node 5: Lookup Article
**Infrastructure:**
- Base: `appwSozYTkrsQWUXB` (Pivot Media Master)
- Table: `tblGumae8KDpsrWvh` (Articles)
- Filter: `{pivot_Id}='{{ pivotId }}'`
- Fields: `pivot_Id`, `markdown`, `original_url`, `source_id`, `date_published`

**Implementation Status:** ❌ Not Implemented (no direct lookup by pivotId)

The dashboard `getStories()` function fetches articles in bulk and builds a lookup map (lines 281-295), but this is for source_id lookup, not for getting full article markdown.

**Action Required:**
```python
def get_article_by_pivot_id(pivot_id: str) -> dict:
    """Lookup article markdown by pivotId"""
    filter_formula = f"{{pivot_Id}}='{pivot_id}'"
    # Airtable GET with filter
    pass
```

---

### Node 6: Clean Content (Gemini)
**Infrastructure:**
- Model: `gemini-3-flash-preview`
- Temperature: 0.1
- Purpose: Remove navigation, ads, footers from markdown

**Implementation Status:** ❌ Not Implemented

**Critical Gap:** No Gemini AI integration for content cleaning.

**Action Required:**
```python
def clean_content(markdown: str, gemini_client) -> str:
    """Use Gemini to clean article content"""

    system_prompt = """You are a content cleaner. Remove all navigation elements, ads, footers,
headers, social media buttons, and non-article content from this markdown.

Keep ONLY the main article body text. Preserve paragraph structure.

Return the cleaned article text only."""

    response = gemini_client.generate_content(
        model="gemini-3-flash-preview",
        contents=markdown,
        generation_config={
            "temperature": 0.1
        }
    )

    return response.text
```

---

### Node 7: Content Creator (Claude)
**Infrastructure:**
- Model: `claude-sonnet-4-5-20250929`
- Temperature: 0.6
- Max Tokens: 1500
- Output: JSON with `ai_headline`, `ai_dek`, `b1`, `b2`, `b3`, `image_prompt`, `label`

**Implementation Status:** ❌ Not Implemented

**Critical Gap:** This is the core AI functionality for generating newsletter content.

**Action Required:**
```python
def create_content(cleaned_content: str, original_headline: str, anthropic_client) -> dict:
    """Generate headline, dek, bullets, image prompt using Claude"""

    system_prompt = f"""You are a senior editor for Pivot 5, a daily AI newsletter for business professionals.

ARTICLE CONTENT:
{cleaned_content}

ORIGINAL HEADLINE:
{original_headline}

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
{{
  "ai_headline": "...",
  "ai_dek": "...",
  "b1": "...",
  "b2": "...",
  "b3": "...",
  "image_prompt": "...",
  "label": "..."
}}"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        temperature=0.6,
        messages=[{"role": "user", "content": system_prompt}]
    )

    return json.loads(response.content[0].text)
```

---

### Node 8: Bolding Pass (Claude)
**Infrastructure:**
- Model: `claude-sonnet-4-5-20250929`
- Temperature: 0.3
- Purpose: Add **bold** to key phrases in bullets

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def apply_bolding(b1: str, b2: str, b3: str, anthropic_client) -> dict:
    """Add bold formatting to key phrases in bullets"""

    prompt = f"""Add bold formatting to key phrases in these bullet points.

RULES:
- Bold 1-3 key phrases per bullet (2-4 words each)
- Bold company names, numbers, percentages
- Bold action verbs and outcomes
- Use **markdown bold** syntax
- Do NOT change any other text

BULLETS:
b1: {b1}
b2: {b2}
b3: {b3}

Return as JSON:
{{
  "b1": "...",
  "b2": "...",
  "b3": "..."
}}"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text)
```

---

### Node 9: Prepare Decoration Record
**Infrastructure:** JavaScript code that combines all data into decoration record
**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def prepare_decoration_record(
    slot_data: dict,
    content: dict,
    bolded: dict,
    article: dict
) -> dict:
    """Prepare decoration record for Airtable"""
    return {
        "issue_id": slot_data["issue_id"],
        "story_id": f"{slot_data['issue_id']}_slot{slot_data['slot_order']}",
        "slot_order": slot_data["slot_order"],
        "pivotId": slot_data["pivotId"],
        "headline": content["ai_headline"],
        "ai_dek": content["ai_dek"],
        "label": content["label"],
        "b1": bolded["b1"],
        "b2": bolded["b2"],
        "b3": bolded["b3"],
        "image_prompt": content["image_prompt"],
        "image_status": "needs_image",
        "raw": article["markdown"],
        "core_url": article["original_url"],
        "source_id": article["source_id"]
    }
```

---

### Node 10: Write Decoration
**Infrastructure:**
- Base: `appglKSJZxmA9iHpl` (AI Editor 2.0)
- Table: `tbla16LJCf5Z6cRn3` (Newsletter Issue Stories / Decoration)
- Operation: Upsert
- Match Field: `story_id`

**Implementation:** ⚠️ Partial - `getDecorations()` READ only (lines 496-547)

**Comparison:**
| Aspect | Infrastructure | Implementation | Match |
|--------|---------------|----------------|-------|
| Base ID | `appglKSJZxmA9iHpl` | `process.env.AI_EDITOR_BASE_ID` | ✅ |
| Table ID | `tbla16LJCf5Z6cRn3` | `process.env.AI_EDITOR_DECORATION_TABLE` | ✅ |
| Operation | Upsert | READ only | ❌ |
| Fields | 16 fields | 17 fields | ✅ |

**Gap:** Dashboard can READ decorations but not CREATE/UPSERT them.

**Action Required:**
```python
def write_decoration(record: dict) -> str:
    """Upsert decoration record to Airtable"""
    # Airtable UPSERT with match on story_id
    pass
```

---

## Image Generation Pipeline

### Node 11: Get Stories Needing Images
**Infrastructure:**
- Filter: `{image_status}='needs_image'`
- Max Records: 10

**Implementation Status:** ❌ Not Implemented

---

### Node 13: Gemini Generate Image
**Infrastructure:**
- Model: `gemini-3-pro-image-preview`
- URL: `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent`
- Image Size: 636px × 358px

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def generate_image_gemini(image_prompt: str, gemini_api_key: str) -> Optional[bytes]:
    """Generate image using Gemini"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

    payload = {
        "contents": [{
            "parts": [{
                "text": f"Generate a professional, abstract newsletter image for: {image_prompt}. Style: clean, modern, suitable for business newsletter. No text or logos. 636px width, landscape orientation."
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

    response = requests.post(
        f"{url}?key={gemini_api_key}",
        json=payload
    )

    if response.ok:
        data = response.json()
        base64_data = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        return base64.b64decode(base64_data)

    return None
```

---

### Node 15: GPT Image 1.5 Backup
**Infrastructure:**
- Model: `gpt-image-1.5`
- Size: 1024×1024
- Quality: standard

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def generate_image_openai(image_prompt: str, openai_client) -> Optional[str]:
    """Generate image using GPT Image 1.5 as fallback"""

    full_prompt = f"""{image_prompt}

Style: Professional, abstract, suitable for business newsletter.
No text, logos, or words. Clean modern design."""

    response = openai_client.images.generate(
        model="gpt-image-1.5",
        prompt=full_prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )

    return response.data[0].url
```

---

### Nodes 18-19: Cloudflare Upload
**Infrastructure:**
- Endpoint: `https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1`
- CDN URL Pattern: `https://img.pivotnews.com/cdn-cgi/imagedelivery/KXy14RehLGC3ziMxzD_shA/{id}/newsletter`

**Implementation Status:** ❌ Not Implemented

**Action Required:**
```python
def upload_to_cloudflare(image_data: bytes, account_id: str, api_token: str) -> str:
    """Upload image to Cloudflare Images CDN"""

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1"

    headers = {
        "Authorization": f"Bearer {api_token}"
    }

    files = {
        "file": ("newsletter_image.png", image_data, "image/png")
    }

    response = requests.post(url, headers=headers, files=files)
    data = response.json()

    image_id = data["result"]["id"]
    return f"https://img.pivotnews.com/cdn-cgi/imagedelivery/KXy14RehLGC3ziMxzD_shA/{image_id}/newsletter"
```

---

### Node 20: Update Image Status
**Infrastructure:**
- Operation: Update record
- Fields: `image_url`, `image_status='generated'`, `cloudflare_id`

**Implementation Status:** ❌ Not Implemented

---

## Environment Variables Required

### Currently Configured
```bash
AIRTABLE_API_KEY=✅ Configured
AI_EDITOR_BASE_ID=✅ Configured (appglKSJZxmA9iHpl)
AI_EDITOR_DECORATION_TABLE=✅ Configured (tbla16LJCf5Z6cRn3)
AI_EDITOR_SELECTED_SLOTS_TABLE=✅ Configured (tblzt2z7r512Kto3O)
AIRTABLE_BASE_ID=✅ Configured (appwSozYTkrsQWUXB)
AIRTABLE_ARTICLES_TABLE=✅ Configured (tblGumae8KDpsrWvh)
```

### Missing
```bash
GEMINI_API_KEY=❌ Required for content cleaning and image generation
ANTHROPIC_API_KEY=❌ Required for Claude content creation
OPENAI_API_KEY=❌ Required for GPT Image 1.5 fallback
CLOUDFLARE_ACCOUNT_ID=❌ Required for image upload
CLOUDFLARE_API_TOKEN=❌ Required for image upload
```

---

## Python Worker Specification

### File 1: `workers/jobs/decoration.py`
**Queue:** Redis Queue (RQ)
**Schedule:** `25 2 * * 2-6` UTC (9:25 PM EST)

```python
# Main job function
def decorate_stories() -> dict:
    """Step 3 Phase 1: Text Decoration Job"""
    pass

# Data retrieval
def get_pending_issue() -> dict:
    """Get today's pending issue from Selected Slots"""
    pass

def get_article_by_pivot_id(pivot_id: str) -> dict:
    """Lookup article markdown by pivotId"""
    pass

# AI processing
def clean_content(markdown: str) -> str:
    """Use Gemini to clean article content"""
    pass

def create_content(cleaned_content: str, headline: str) -> dict:
    """Use Claude to generate headline/dek/bullets"""
    pass

def apply_bolding(b1: str, b2: str, b3: str) -> dict:
    """Use Claude to add bold formatting"""
    pass

# Output
def prepare_decoration_record(...) -> dict:
    """Prepare record for Airtable"""
    pass

def write_decoration(record: dict) -> str:
    """Upsert to Decoration table"""
    pass
```

### File 2: `workers/jobs/image_generation.py`
**Queue:** Redis Queue (RQ)
**Schedule:** `30 2 * * 2-6` UTC (9:30 PM EST)

```python
# Main job function
def generate_images() -> dict:
    """Step 3 Phase 2: Image Generation Job"""
    pass

# Data retrieval
def get_stories_needing_images() -> List[dict]:
    """Get decorations where image_status='needs_image'"""
    pass

# Image generation
def generate_image_gemini(prompt: str) -> Optional[bytes]:
    """Primary: Gemini image generation"""
    pass

def generate_image_openai(prompt: str) -> Optional[str]:
    """Fallback: GPT Image 1.5"""
    pass

# Upload
def upload_to_cloudflare(image_data: bytes) -> str:
    """Upload to Cloudflare CDN"""
    pass

def download_image(url: str) -> bytes:
    """Download image from URL (for OpenAI fallback)"""
    pass

# Output
def update_image_status(record_id: str, image_url: str, cloudflare_id: str) -> None:
    """Update decoration record with image URL"""
    pass
```

---

## Orchestration Flow

### Phase 1: Text Decoration
```python
def decorate_stories():
    # 1. Get pending issue
    issue = get_pending_issue()
    if not issue:
        return {"status": "no_pending_issue"}

    # 2. Expand into 5 slots
    slots = expand_slots(issue)

    # 3. Process each slot
    for slot in slots:
        # 3a. Lookup article
        article = get_article_by_pivot_id(slot["pivotId"])

        # 3b. Clean content (Gemini)
        cleaned = clean_content(article["markdown"])

        # 3c. Create content (Claude)
        content = create_content(cleaned, slot["headline"])

        # 3d. Apply bolding (Claude)
        bolded = apply_bolding(content["b1"], content["b2"], content["b3"])

        # 3e. Prepare and write record
        record = prepare_decoration_record(slot, content, bolded, article)
        write_decoration(record)

    return {"status": "success", "slots_decorated": 5}
```

### Phase 2: Image Generation
```python
def generate_images():
    # 1. Get stories needing images
    stories = get_stories_needing_images()

    results = []
    for story in stories:
        # 2. Try Gemini first
        image_data = generate_image_gemini(story["image_prompt"])

        # 3. Fallback to GPT Image 1.5
        if not image_data:
            image_url = generate_image_openai(story["image_prompt"])
            if image_url:
                image_data = download_image(image_url)

        # 4. Upload to Cloudflare
        if image_data:
            cdn_url = upload_to_cloudflare(image_data)
            cloudflare_id = cdn_url.split("/")[-2]

            # 5. Update record
            update_image_status(story["id"], cdn_url, cloudflare_id)
            results.append({"id": story["id"], "status": "success"})
        else:
            results.append({"id": story["id"], "status": "failed"})

    return {"processed": len(results), "results": results}
```

---

## Critical Issues Found

### Issue 1: No AI Integration for Content Creation
**Problem:** Dashboard has no mechanism to call Gemini or Claude APIs
**Impact:** Cannot generate headlines, bullets, or cleaned content
**Resolution:** Python workers with Gemini/Claude API clients

### Issue 2: No Image Generation Pipeline
**Problem:** No implementation for image generation or CDN upload
**Impact:** Stories cannot get newsletter images
**Resolution:** Python worker with Gemini/GPT Image 1.5/Cloudflare integration

### Issue 3: Dashboard is Read-Only for Decorations
**Location:** `getDecorations()` lines 496-547
**Problem:** Only READ operation, no CREATE/UPSERT
**Impact:** Dashboard can view decorated stories but not create them
**Resolution:** This is correct for dashboard - Python worker handles creation

### Issue 4: Selected Slots Missing Status Filter
**Location:** `getSelectedSlots()` line 395
**Problem:** No filter for `{status}='pending'`
**Impact:** May fetch completed/sent issue instead of today's pending issue
**Resolution:** Add filter for Python worker

---

## Implementation Priority

1. **High Priority (Worker Core):**
   - [ ] Create `workers/jobs/decoration.py`
   - [ ] Create `workers/jobs/image_generation.py`
   - [ ] Implement Gemini API client (content cleaning + image gen)
   - [ ] Implement Anthropic Claude client (content creation + bolding)
   - [ ] Implement Cloudflare Images upload

2. **Medium Priority (Fallback):**
   - [ ] Implement OpenAI GPT Image 1.5 fallback
   - [ ] Add retry logic for failed image generations
   - [ ] Error handling and logging

3. **Low Priority (Dashboard Updates):**
   - [ ] Add "Run Decoration" manual trigger button
   - [ ] Display decoration status per story
   - [ ] Show image generation progress
   - [ ] Image preview/regeneration controls

---

## AI Model Configuration

### Gemini (Content Cleaning)
```python
config = {
    "model": "gemini-3-flash-preview",
    "temperature": 0.1,
    "api_endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"
}
```

### Claude (Content Creation)
```python
config = {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.6,
    "max_tokens": 1500
}
```

### Claude (Bolding Pass)
```python
config = {
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.3,
    "max_tokens": 500
}
```

### Gemini (Image Generation - Primary)
```python
config = {
    "model": "gemini-3-pro-image-preview",
    "image_dimensions": {"width": 636, "height": 358},
    "api_endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"
}
```

### GPT Image 1.5 (Image Generation - Fallback)
```python
config = {
    "model": "gpt-image-1.5",
    "size": "1024x1024",
    "quality": "standard"
}
```

---

## Decoration Table Schema

| Field | Type | Description |
|-------|------|-------------|
| story_id | Text | Unique ID (`{issue_id}_slot{n}`) - Match key for upsert |
| issue_id | Text | Link to Selected Slots |
| slot_order | Number | 1-5 slot position |
| pivotId | Text | Link to Articles table |
| headline | Text | AI-generated headline (Title Case, <80 chars) |
| ai_dek | Text | Descriptive deck (15-25 words) |
| label | Select | AI, Tech, Business, Policy, Research, Industry |
| b1 | Text | Bullet 1 - Main announcement (<260 chars) |
| b2 | Text | Bullet 2 - Key details (<260 chars) |
| b3 | Text | Bullet 3 - Business impact (<260 chars) |
| image_prompt | Text | Image generation prompt |
| image_status | Select | `needs_image`, `generated`, `failed` |
| image_url | Text | Cloudflare CDN URL |
| cloudflare_id | Text | Cloudflare image ID |
| raw | Long Text | Original article markdown |
| core_url | Text | Original article URL |
| source_id | Text | Publisher name |
| social_status | Select | `pending`, `synced` |

---

*Cross-reference generated: December 23, 2025*
