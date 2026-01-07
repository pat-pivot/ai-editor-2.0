"""
Step 3b: Image Generation Job
Workflow ID: HCbd2g852rkQgSqr (same as decoration)
Schedule: 9:30 PM EST (0 2 30 * * 2-6 UTC)

Generates images for decorated stories using Gemini Imagen 3 (primary)
with GPT Image 1.5 fallback. Optimizes via Cloudinary and uploads to Cloudflare.
"""

import os
import json
import traceback
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.images import ImageClient


def _log(msg: str, data: Any = None):
    """Enhanced logging with timestamp and optional data dump"""
    timestamp = datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
    print(f"[Step 3b][{timestamp}] {msg}")
    if data is not None:
        if isinstance(data, (dict, list)):
            print(f"[Step 3b][{timestamp}]   └─ {json.dumps(data, indent=2, default=str)[:2000]}")
        else:
            print(f"[Step 3b][{timestamp}]   └─ {str(data)[:500]}")


def _build_image_prompt(headline: str, b1: str, b2: str, b3: str) -> str:
    """
    Build image generation prompt from story content.
    Matches n8n workflow format exactly.

    Args:
        headline: Story headline
        b1, b2, b3: Bullet points (may contain HTML <b> tags)

    Returns:
        Formatted image prompt for Gemini Imagen 3
    """
    # Strip HTML tags from bullets for cleaner prompt
    import re
    def strip_html(text: str) -> str:
        return re.sub(r'<[^>]+>', '', text) if text else ''

    clean_b1 = strip_html(b1)
    clean_b2 = strip_html(b2)
    clean_b3 = strip_html(b3)

    # Build key points section only if bullets exist
    key_points = ""
    if clean_b1 or clean_b2 or clean_b3:
        key_points = "\nKey Points (if available):"
        if clean_b1:
            key_points += f"\n- {clean_b1}"
        if clean_b2:
            key_points += f"\n- {clean_b2}"
        if clean_b3:
            key_points += f"\n- {clean_b3}"

    # Match n8n workflow prompt format exactly
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

    return prompt


def generate_images() -> dict:
    """
    Step 3b: Image Generation Cron Job - Main entry point

    Flow:
    1. Get decorated stories with image_status='pending'
    2. For each story:
       a. Generate image from image_prompt using Gemini Imagen 3
       b. Optimize via Cloudinary (636px width)
       c. Upload to Cloudflare
       d. Update decoration record with image_url
    3. Mark stories with image_status='generated'

    Returns:
        {generated: int, failed: int, errors: list}
    """
    _log("=" * 60)
    _log("IMAGE GENERATION JOB STARTED")
    _log(f"Timestamp: {datetime.utcnow().isoformat()}")
    _log("=" * 60)

    # Initialize clients
    _log("Initializing clients...")
    airtable = AirtableClient()
    _log(f"  ✓ AirtableClient initialized (base: {airtable.ai_editor_base_id})")
    image_client = ImageClient()
    _log(f"  ✓ ImageClient initialized")
    _log(f"    Gemini API: {'configured' if image_client.gemini_api_key else 'NOT configured'}")
    _log(f"    OpenAI API: {'configured' if image_client.openai_api_key else 'NOT configured'}")
    _log(f"    Cloudinary: configured (using HTTP POST with preset 'MakeImage')")
    _log(f"    Cloudflare: {'configured' if image_client.cloudflare_account_id else 'NOT configured'}")

    # Track results
    results = {
        "generated": 0,
        "failed": 0,
        "errors": []
    }

    try:
        # 1. Get decorated stories needing images
        _log("-" * 40)
        _log("STEP 1: Fetching stories needing images...")
        _log(f"  Table: {airtable.decoration_table_id}")
        _log(f"  Filter: image_status='pending' OR image_status='needs_image'")
        pending_decorations = _get_pending_decorations(airtable)

        if not pending_decorations:
            _log("  ⚠️ No stories need images - exiting")
            return results

        _log(f"  ✓ Found {len(pending_decorations)} stories needing images")

        # 2. Process each story
        for idx, decoration in enumerate(pending_decorations, 1):
            record_id = decoration.get('id', '')
            fields = decoration.get('fields', {})
            story_id = fields.get('story_id', 'unknown')

            _log("-" * 40)
            _log(f"STORY {idx}/{len(pending_decorations)}: {story_id}")
            _log(f"  Record ID: {record_id}")
            _log(f"  Fields:", list(fields.keys()))

            try:
                # Build image prompt from headline + bullets (matching n8n workflow)
                headline = fields.get('headline', '')
                b1 = fields.get('b1', '')
                b2 = fields.get('b2', '')
                b3 = fields.get('b3', '')
                label = fields.get('label', 'AI NEWS')

                _log(f"  Building image prompt from story data:")
                _log(f"    headline: {headline[:80] if headline else '(empty)'}...")
                _log(f"    label: {label}")
                _log(f"    b1: {b1[:60] if b1 else '(empty)'}...")

                # Build prompt exactly like n8n workflow
                image_prompt = _build_image_prompt(headline, b1, b2, b3)
                _log(f"  Generated image prompt: {image_prompt[:150]}...")

                # 2a-c. Generate, optimize, and upload image
                _log(f"  Calling image_client.process_image()...")
                _log(f"    Prompt: {image_prompt[:150]}...")
                _log(f"    Story ID: {story_id}")
                image_url, source = image_client.process_image(image_prompt, story_id)

                if image_url:
                    _log(f"  ✓ Image generated successfully")
                    _log(f"    Source: {source}")
                    _log(f"    URL: {image_url}")

                    # 2d. Update decoration record
                    # Only update fields that exist in Newsletter Issue Stories table
                    _log(f"  Updating Airtable record...")
                    update_data = {
                        "image_url": image_url,
                        "image_status": "generated"
                    }
                    _log(f"  Update data:", update_data)
                    _log(f"  (Image source was: {source})")  # Log source for debugging
                    airtable.update_decoration(record_id, update_data)
                    _log(f"  ✓ Airtable updated")

                    results["generated"] += 1

                else:
                    _log(f"  ❌ Image generation returned no URL")
                    _log(f"    Source returned: {source}")
                    # NOTE: "failed" is NOT a valid image_status option
                    # Valid options: needs_image, generated
                    # Leave status as needs_image so it can be retried
                    _log(f"  Leaving image_status as 'needs_image' for retry")

                    results["failed"] += 1
                    results["errors"].append({
                        "storyId": story_id,
                        "error": "Image generation failed"
                    })

            except Exception as e:
                _log(f"  ❌ EXCEPTION: {e}")
                _log(f"  Traceback: {traceback.format_exc()}")
                results["failed"] += 1
                results["errors"].append({
                    "storyId": story_id,
                    "error": str(e)
                })
                # NOTE: "failed" is NOT a valid image_status option
                # Valid options: needs_image, generated
                # Leave status as needs_image so it can be retried
                _log(f"  Leaving image_status as 'needs_image' for retry")

        _log("=" * 60)
        _log("IMAGE GENERATION JOB COMPLETE")
        _log(f"  Generated: {results['generated']}")
        _log(f"  Failed: {results['failed']}")
        _log(f"  Errors: {len(results['errors'])}")
        if results['errors']:
            _log(f"  Error details:", results['errors'])
        _log("=" * 60)
        return results

    except Exception as e:
        _log("=" * 60)
        _log(f"❌ FATAL ERROR: {e}")
        _log(f"Traceback: {traceback.format_exc()}")
        _log("=" * 60)
        results["errors"].append({"fatal": str(e)})
        raise


def _get_pending_decorations(airtable: AirtableClient) -> List[dict]:
    """
    Get decorated stories that need images generated.

    Filter: image_status='pending' OR image_status='needs_image'
    """
    _log("  Querying Airtable for pending decorations...")
    table = airtable._get_table(
        airtable.ai_editor_base_id,
        airtable.decoration_table_id
    )

    filter_formula = "OR({image_status}='pending', {image_status}='needs_image')"
    _log(f"    Formula: {filter_formula}")

    records = table.all(
        formula=filter_formula,
        fields=[
            'story_id', 'headline', 'b1', 'b2', 'b3',
            'image_status', 'slot_order', 'label'
        ]
    )

    _log(f"  Query returned {len(records)} records")
    for i, rec in enumerate(records[:5]):  # Log first 5
        fields = rec.get('fields', {})
        _log(f"    [{i+1}] {fields.get('story_id', 'unknown')} - status: {fields.get('image_status', 'unknown')}")
    if len(records) > 5:
        _log(f"    ... and {len(records) - 5} more")

    return records


def regenerate_image(record_id: str) -> dict:
    """
    Manual image regeneration for a specific decoration record.

    Args:
        record_id: Airtable record ID

    Returns:
        {success: bool, image_url: str, source: str, error: str}
    """
    _log("=" * 60)
    _log(f"MANUAL IMAGE REGENERATION")
    _log(f"  Record ID: {record_id}")
    _log("=" * 60)

    airtable = AirtableClient()
    image_client = ImageClient()
    _log("  ✓ Clients initialized")

    try:
        # Get the decoration record
        _log("  Fetching decoration record from Airtable...")
        table = airtable._get_table(
            airtable.ai_editor_base_id,
            airtable.decoration_table_id
        )
        record = table.get(record_id)

        if not record:
            _log("  ❌ Record not found")
            return {"success": False, "error": "Record not found"}

        fields = record.get('fields', {})
        story_id = fields.get('story_id', 'unknown')

        # Build image prompt from headline + bullets (matching n8n workflow)
        headline = fields.get('headline', '')
        b1 = fields.get('b1', '')
        b2 = fields.get('b2', '')
        b3 = fields.get('b3', '')

        _log(f"  ✓ Record found:")
        _log(f"    story_id: {story_id}")
        _log(f"    headline: {headline[:80] if headline else '(empty)'}...")
        _log(f"    b1: {b1[:60] if b1 else '(empty)'}...")

        # Build prompt exactly like n8n workflow
        image_prompt = _build_image_prompt(headline, b1, b2, b3)
        _log(f"  Generated image prompt: {image_prompt[:150]}...")

        # Generate image
        _log("  Generating image...")
        image_url, source = image_client.process_image(image_prompt, story_id)

        if image_url:
            _log(f"  ✓ Image generated:")
            _log(f"    Source: {source}")
            _log(f"    URL: {image_url}")

            _log("  Updating Airtable...")
            airtable.update_decoration(record_id, {
                "image_url": image_url,
                "image_status": "generated"
            })
            _log(f"  ✓ Airtable updated (source was: {source})")

            return {
                "success": True,
                "image_url": image_url,
                "source": source
            }
        else:
            _log(f"  ❌ Image generation failed (source: {source})")
            return {
                "success": False,
                "error": "Image generation failed"
            }

    except Exception as e:
        _log(f"  ❌ EXCEPTION: {e}")
        _log(f"  Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }


# Job configuration for RQ scheduler
JOB_CONFIG = {
    "func": generate_images,
    "trigger": "cron",
    "hour": 2,   # 2 AM UTC = ~9 PM EST
    "minute": 30,
    "day_of_week": "tue-sat",
    "id": "step3b_image_generation",
    "replace_existing": True
}
