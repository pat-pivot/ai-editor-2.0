# AI Editor 2.0 Infrastructure - Step 3: Decoration Workflow

**Document:** AI-Editor-2.0-Infrastructure-Step-3-12-23-25.md
**Date:** December 23, 2025
**Purpose:** Complete node-by-node analysis of Step 3: Decoration workflow

---

## Workflow Overview

**Workflow Name:** STEP 3 AI Editor 2.0 - Decoration
**Workflow ID:** `HCbd2g852rkQgSqr`
**Total Nodes:** 41
**Schedules:**
- Headlines/Bullets: `25 2 * * 2-6` (9:25 PM EST)
- Image Generation: `30 2 * * 2-6` (9:30 PM EST)

### Purpose
Generates AI-powered headlines, deks, bullet points, and images for each selected story, then uploads images to Cloudflare CDN.

### AI Models
| Model | Provider | Purpose |
|-------|----------|---------|
| `gemini-3-flash-preview` | Google | Content cleaning |
| `claude-sonnet-4-5-20250929` | Anthropic | Headlines, bullets, bolding |
| `gemini-3-pro-image-preview` | Google | Primary image generation |
| `gpt-image-1.5` | OpenAI | Fallback image generation |

---

## Airtable Tables Referenced

### Input Tables

| Base | Table | Table ID | Purpose |
|------|-------|----------|---------|
| AI Editor 2.0 | Selected Slots | `tblzt2z7r512Kto3O` | Today's pending issue |
| Pivot Media Master | Articles | `tblGumae8KDpsrWvh` | Raw article markdown |

### Output Table

| Base | Table | Table ID | Purpose |
|------|-------|----------|---------|
| AI Editor 2.0 | Newsletter Issue Stories / Decoration | `tbla16LJCf5Z6cRn3` | Decorated stories with images |

---

## Node-by-Node Analysis

### Node 1: Schedule Trigger
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

### Node 2: Pull Latest Issue
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

### Node 3: Expand Slots
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

### Node 4: Split In Batches
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

### Node 5: Lookup Article
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

### Node 6: Clean Content
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

### Node 7: Content Creator
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

### Node 8: Bolding Pass
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

### Node 9: Prepare Decoration Record
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

### Node 10: Write Decoration
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

## Image Generation Pipeline

### Node 11: Get Stories Needing Images
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

### Node 12: Image Split Batches
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

### Node 13: Gemini Generate Image
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

### Node 14: Check Gemini Success
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

### Node 15: OpenAI Backup Node
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

**Output:** GPT Image 1.5 image URL → Connects to "Download OpenAI Image"

---

### Node 16: Download OpenAI Image
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

### Node 17: Convert to Binary
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

### Node 18: Upload to Cloudflare
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

### Node 19: Extract Image URL
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

### Node 20: Update Image Status
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

## Step 3 Data Flow Summary

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
   │    (GPT Image 1.5)            │
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

## API Credentials for Step 3

### Airtable
| Key | Value |
|-----|-------|
| API Key | `[REDACTED - use environment variable]` |
| Base: AI Editor 2.0 | `appglKSJZxmA9iHpl` |
| Base: Pivot Media Master | `appwSozYTkrsQWUXB` |

### Google Gemini
| Key | Value |
|-----|-------|
| Text Model | `gemini-3-flash-preview` |
| Image Model | `gemini-3-pro-image-preview` |
| API Key | Environment variable: `GEMINI_API_KEY` |

### Anthropic Claude
| Key | Value |
|-----|-------|
| Model | `claude-sonnet-4-5-20250929` |
| API Key | Environment variable: `ANTHROPIC_API_KEY` |

### OpenAI (Fallback)
| Key | Value |
|-----|-------|
| Model | `gpt-image-1.5` |
| API Key | Environment variable: `OPENAI_API_KEY` |

### Cloudflare Images
| Key | Value |
|-----|-------|
| Account ID | Environment variable: `CLOUDFLARE_ACCOUNT_ID` |
| API Token | Environment variable: `CLOUDFLARE_API_TOKEN` |
| CDN URL Pattern | `https://img.pivotnews.com/cdn-cgi/imagedelivery/KXy14RehLGC3ziMxzD_shA/{id}/newsletter` |

---

## Decoration Table Schema (tbla16LJCf5Z6cRn3)

| Field | Type | Description |
|-------|------|-------------|
| story_id | Text | Unique ID (`{issue_id}_slot{n}`) |
| issue_id | Text | Link to Selected Slots |
| slot_order | Number | 1-5 slot position |
| pivotId | Text | Link to Articles table |
| headline | Text | AI-generated headline (Title Case, <80 chars) |
| ai_dek | Text | Descriptive deck (15-25 words) |
| label | Select | Category tag (AI, Tech, Business, Policy, Research, Industry) |
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

*Document generated: December 23, 2025*
