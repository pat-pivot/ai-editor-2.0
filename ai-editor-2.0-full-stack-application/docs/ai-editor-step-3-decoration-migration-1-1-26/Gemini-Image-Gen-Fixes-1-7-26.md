# Gemini Image Generation Fixes - January 7, 2026

**Status:** CRITICAL - AttributeError blocking image generation
**Error:** `AttributeError: 'ImageClient' object has no attribute 'cloudinary_url'`
**Location:** `app/workers/jobs/image_generation.py` line 111
**n8n Workflow Reference:** `HCbd2g852rkQgSqr` (STEP 3 AI Editor 2.0 - Decoration_12.19.25)

---

## Summary of Current Errors

### Error 1: cloudinary_url Attribute Not Found (CRITICAL)

**File:** `/app/workers/jobs/image_generation.py`
**Line:** 111

```python
# CURRENT CODE (BROKEN - line 111)
_log(f"    Cloudinary: {'configured' if image_client.cloudinary_url else 'NOT configured'}")
```

**Problem:** The `ImageClient` class was refactored to use HTTP POST for Cloudinary uploads instead of the SDK. The `cloudinary_url` attribute was removed during this refactoring, but the logging statement in `image_generation.py` still references it.

**Fix Required:** Update the logging statement to check for the cloud_name or remove the Cloudinary configuration check since Cloudinary config is now hardcoded in the `optimize_image()` method.

---

## n8n Workflow Reference: Image Generation Pipeline

The n8n workflow `HCbd2g852rkQgSqr` implements image generation in the "Create/Upload Image" section. Here is the exact flow:

### n8n Image Generation Flow

```
1. Gemini Generate Image (primary)
   ├── URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent
   ├── Model: gemini-3-pro-image-preview
   ├── Uses: Google PaLM API credentials (x-goog-api-key header)
   └── On Error: Falls back to OpenAI

2. OpenAI Backup Node (fallback)
   ├── URL: https://api.openai.com/v1/images/generations
   ├── Model: gpt-image-1.5
   └── Size: 1536x1024

3. Convert to Binary (code node)
   └── Extracts base64 from response, creates binary image

4. Cloudinary Upload (HTTP POST)
   ├── URL: https://api.cloudinary.com/v1_1/dzocuy47k/image/upload
   ├── upload_preset: "MakeImage"
   └── Returns: URL with image

5. Optimized URL (Set node)
   ├── Transform: /upload/ → /upload/c_scale,w_636,q_auto:eco,f_webp/
   └── Force HTTPS

6. Get Optimized Image (HTTP GET)
   └── Fetch the optimized image binary

7. Upload to Cloudflare (HTTP POST)
   ├── URL: https://api.cloudflare.com/client/v4/accounts/57031a8d3a5fcec5b7f5f7b4e2fa943b/images/v1
   ├── Authorization: Bearer token
   └── Final URL: https://img.pivotnews.com/cdn-cgi/imagedelivery/{id}/newsletter
```

---

## Python Code Fixes Required

### Fix 1: Remove cloudinary_url Reference (CRITICAL)

**File:** `/app/workers/jobs/image_generation.py`
**Lines:** 110-112

```python
# BEFORE (BROKEN)
_log(f"    Gemini API: {'configured' if image_client.gemini_api_key else 'NOT configured'}")
_log(f"    OpenAI API: {'configured' if image_client.openai_api_key else 'NOT configured'}")
_log(f"    Cloudinary: {'configured' if image_client.cloudinary_url else 'NOT configured'}")  # LINE 111 - ERROR
_log(f"    Cloudflare: {'configured' if image_client.cloudflare_account_id else 'NOT configured'}")
```

```python
# AFTER (FIXED)
_log(f"    Gemini API: {'configured' if image_client.gemini_api_key else 'NOT configured'}")
_log(f"    OpenAI API: {'configured' if image_client.openai_api_key else 'NOT configured'}")
_log(f"    Cloudinary: configured (using HTTP POST with preset 'MakeImage')")  # Cloudinary uses hardcoded config
_log(f"    Cloudflare: {'configured' if image_client.cloudflare_account_id else 'NOT configured'}")
```

**Reason:** The `ImageClient` class now uses hardcoded Cloudinary configuration in the `optimize_image()` method:
- Cloud name: `dzocuy47k`
- Upload preset: `MakeImage`

There is no `cloudinary_url` attribute to check.

---

## Line-by-Line Comparison: n8n vs Python

### Gemini Image Generation

| Aspect | n8n Workflow | Python Code | Status |
|--------|--------------|-------------|--------|
| **API URL** | `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent` | Same URL (line 124 in images.py) | OK |
| **Model** | `gemini-3-pro-image-preview` | Same model | OK |
| **Auth Header** | `x-goog-api-key` via Google PaLM API credentials | `x-goog-api-key` (line 128 in images.py) | OK |
| **Response Modalities** | `["IMAGE"]` | `["image"]` (lowercase) | VERIFY |
| **Aspect Ratio Config** | `"imageConfig": { "aspectRatio": "16:9" }` | `"imageConfig": { "aspectRatio": "16:9" }` (line 143 in images.py) | OK |

### OpenAI Fallback

| Aspect | n8n Workflow | Python Code | Status |
|--------|--------------|-------------|--------|
| **API URL** | `https://api.openai.com/v1/images/generations` | Same URL (line 98 in images.py) | OK |
| **Model** | `gpt-image-1.5` | `gpt-image-1` (line 90 in images.py) | MISMATCH |
| **Size** | `1536x1024` | `1024x1024` (line 93 in images.py) | MISMATCH |

### Cloudinary Upload

| Aspect | n8n Workflow | Python Code | Status |
|--------|--------------|-------------|--------|
| **Upload URL** | `https://api.cloudinary.com/v1_1/dzocuy47k/image/upload` | Same URL (line 209 in images.py) | OK |
| **Upload Preset** | `MakeImage` | `MakeImage` (line 208 in images.py) | OK |
| **Transform** | `/upload/` to `/upload/c_scale,w_636,q_auto:eco,f_webp/` | Same transform (lines 239-241 in images.py) | OK |

### Cloudflare Upload

| Aspect | n8n Workflow | Python Code | Status |
|--------|--------------|-------------|--------|
| **Account ID** | `57031a8d3a5fcec5b7f5f7b4e2fa943b` | Uses env var `CLOUDFLARE_ACCOUNT_ID` | OK |
| **API URL** | `https://api.cloudflare.com/client/v4/accounts/{id}/images/v1` | Same pattern (line 31 in images.py) | OK |
| **Auth** | Bearer token | Bearer token (line 307 in images.py) | OK |

---

## Issues Found and Fixes

### Issue 1: OpenAI Model Mismatch

**n8n uses:** `gpt-image-1.5`
**Python uses:** `gpt-image-1`

**File:** `/app/workers/utils/images.py`
**Line:** 90

```python
# BEFORE
payload = {
    "model": "gpt-image-1",
    ...
}
```

```python
# AFTER
payload = {
    "model": "gpt-image-1.5",
    ...
}
```

### Issue 2: OpenAI Image Size Mismatch

**n8n uses:** `1536x1024` (16:9 aspect ratio)
**Python uses:** `1024x1024` (1:1 aspect ratio)

**File:** `/app/workers/utils/images.py`
**Line:** 93

```python
# BEFORE
payload = {
    ...
    "size": "1024x1024",
    ...
}
```

```python
# AFTER
payload = {
    ...
    "size": "1536x1024",
    ...
}
```

### Issue 3: Response Modalities Case

**n8n uses:** `["IMAGE"]` (uppercase)
**Python uses:** `["image"]` (lowercase)

This may or may not matter depending on API case sensitivity. The n8n workflow explicitly uses uppercase.

**File:** `/app/workers/utils/images.py`
**Line:** 140

```python
# BEFORE
"generationConfig": {
    "responseModalities": ["image"],
    ...
}
```

```python
# AFTER (match n8n exactly)
"generationConfig": {
    "responseModalities": ["IMAGE"],
    ...
}
```

---

## Image Generation Prompt Comparison

### n8n Prompt (from Gemini Generate Image node)

```
Create a clean, minimal, informative landscape infographic based on this AI news story.

DESIGN REQUIREMENTS:
- Aspect ratio: 16:9
- MINIMAL TEXT - prioritize icons and visuals over words
- Orange accent color: #ff6f00 for accents and highlights
- White or light gray background
- Plenty of white space
- Modern, premium aesthetic

Story Context:
Headline: [headline]

Key Points (if available):
- [b1]
- [b2]
- [b3]

Style: Soft watercolor aesthetic with orange (#ff6f00) accents. Clean typography. NO clutter.
```

### Python Prompt (from image_generation.py _build_image_prompt())

```python
prompt = f"""Create a clean, minimal, informative landscape infographic based on this AI news story.

DESIGN REQUIREMENTS:
- Aspect ratio: 16:9
- MINIMAL TEXT - prioritize icons and visuals over words
- Orange accent color: #ff6f00 for accents and highlights
- White or light gray background
- Plenty of white space
- Modern, premium aesthetic

Story Context:
Headline: {headline}{key_points}

Style: Soft watercolor aesthetic with orange (#ff6f00) accents. Clean typography. NO clutter."""
```

**Status:** MATCHES - The Python prompt format matches n8n exactly.

---

## Complete Fix Summary

### File 1: `/app/workers/jobs/image_generation.py`

**Change 1:** Line 111 - Remove cloudinary_url reference

```python
# Line 111 - CHANGE FROM:
_log(f"    Cloudinary: {'configured' if image_client.cloudinary_url else 'NOT configured'}")

# Line 111 - CHANGE TO:
_log(f"    Cloudinary: configured (using HTTP POST with preset 'MakeImage')")
```

### File 2: `/app/workers/utils/images.py`

**Change 1:** Line 90 - Update OpenAI model

```python
# Line 90 - CHANGE FROM:
"model": "gpt-image-1",

# Line 90 - CHANGE TO:
"model": "gpt-image-1.5",
```

**Change 2:** Line 93 - Update OpenAI image size

```python
# Line 93 - CHANGE FROM:
"size": "1024x1024",

# Line 93 - CHANGE TO:
"size": "1536x1024",
```

**Change 3:** Line 140 - Match responseModalities case (optional)

```python
# Line 140 - CHANGE FROM:
"responseModalities": ["image"],

# Line 140 - CHANGE TO:
"responseModalities": ["IMAGE"],
```

---

## Testing Checklist

After applying fixes, verify:

- [ ] **No AttributeError** - Run `generate_images()` and confirm no cloudinary_url error
- [ ] **Gemini API works** - Check logs for "Gemini Imagen API" success messages
- [ ] **OpenAI fallback works** - Temporarily disable Gemini to test fallback
- [ ] **Cloudinary upload works** - Verify "Cloudinary upload success" log message
- [ ] **Cloudinary transform works** - Check optimized URL has `/c_scale,w_636,q_auto:eco,f_webp/`
- [ ] **Cloudflare upload works** - Verify final URL is on `img.pivotnews.com` domain
- [ ] **Image appears in Airtable** - Check `image_url` field is populated
- [ ] **Image status updates** - Check `image_status` changes to `generated`
- [ ] **16:9 aspect ratio** - Verify generated images are landscape format

### Manual Test Commands

```bash
# Test via API trigger
curl -X POST http://localhost:8000/api/trigger/image-generation \
  -H "Content-Type: application/json" \
  -H "X-Trigger-Secret: $TRIGGER_SECRET"

# Or test single image regeneration
curl -X POST http://localhost:8000/api/trigger/image-generation/regenerate \
  -H "Content-Type: application/json" \
  -H "X-Trigger-Secret: $TRIGGER_SECRET" \
  -d '{"record_id": "recXXXXXX"}'
```

---

## Environment Variables Required

| Variable | Required For | Status |
|----------|--------------|--------|
| `GEMINI_API_KEY` | Gemini Imagen 3 (primary) | Check configured |
| `OPENAI_API_KEY` | GPT Image 1.5 (fallback) | Check configured |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Images upload | Check configured |
| `CLOUDFLARE_API_KEY` | Cloudflare Images upload | Check configured |

Note: Cloudinary uses unsigned upload with preset `MakeImage`, so no API key is required.

---

## References

- **n8n Workflow:** `HCbd2g852rkQgSqr`
- **Python ImageClient:** `/app/workers/utils/images.py`
- **Python Image Job:** `/app/workers/jobs/image_generation.py`
- **Migration Doc:** `/docs/ai-editor-step-3-decoration-migration-1-1-26/AI-Editor-2.0-Step-3-Headline-Decoration-Migration-1-1-26.md`
