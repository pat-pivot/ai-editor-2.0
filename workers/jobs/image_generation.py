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
    _log(f"    Cloudinary: {'configured' if image_client.cloudinary_url else 'NOT configured'}")
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
                # Get image prompt
                image_prompt = fields.get('image_prompt', '')
                _log(f"  image_prompt from Airtable: {image_prompt[:100] if image_prompt else '(empty)'}...")

                if not image_prompt:
                    # Generate fallback prompt from headline
                    headline = fields.get('headline', '')
                    image_prompt = f"Abstract editorial illustration representing: {headline}"
                    _log(f"  ⚠️ No image_prompt, using headline fallback")
                    _log(f"  Fallback prompt: {image_prompt[:100]}...")

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
                    _log(f"  Updating Airtable record...")
                    update_data = {
                        "image_url": image_url,
                        "image_status": "generated",
                        "image_source": source,
                        "date_image_generated": datetime.utcnow().strftime('%Y-%m-%d')
                    }
                    _log(f"  Update data:", update_data)
                    airtable.update_decoration(record_id, update_data)
                    _log(f"  ✓ Airtable updated")

                    results["generated"] += 1

                else:
                    _log(f"  ❌ Image generation returned no URL")
                    _log(f"    Source returned: {source}")
                    # Mark as failed
                    airtable.update_decoration(record_id, {
                        "image_status": "failed",
                        "image_error": "Generation failed - no URL returned"
                    })

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

                # Mark as failed in Airtable
                try:
                    airtable.update_decoration(record_id, {
                        "image_status": "failed",
                        "image_error": str(e)[:500]
                    })
                    _log(f"  Marked as failed in Airtable")
                except Exception as update_err:
                    _log(f"  ⚠️ Failed to update Airtable: {update_err}")

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
            'story_id', 'headline', 'image_prompt',
            'image_status', 'slot_order'
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
        image_prompt = fields.get('image_prompt', '')

        _log(f"  ✓ Record found:")
        _log(f"    story_id: {story_id}")
        _log(f"    image_prompt: {image_prompt[:100] if image_prompt else '(empty)'}...")

        if not image_prompt:
            headline = fields.get('headline', '')
            image_prompt = f"Abstract editorial illustration representing: {headline}"
            _log(f"  ⚠️ Using headline fallback prompt")
            _log(f"    Fallback: {image_prompt[:100]}...")

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
                "image_status": "generated",
                "image_source": source,
                "date_image_generated": datetime.utcnow().strftime('%Y-%m-%d')
            })
            _log("  ✓ Airtable updated")

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
