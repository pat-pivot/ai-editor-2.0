"""
Step 3b: Image Generation Job
Workflow ID: HCbd2g852rkQgSqr (same as decoration)
Schedule: 9:30 PM EST (0 2 30 * * 2-6 UTC)

Generates images for decorated stories using Gemini Imagen 3 (primary)
with GPT Image 1.5 fallback. Optimizes via Cloudinary and uploads to Cloudflare.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Any

from utils.airtable import AirtableClient
from utils.images import ImageClient


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
    print(f"[Step 3b] Starting image generation at {datetime.utcnow().isoformat()}")

    # Initialize clients
    airtable = AirtableClient()
    image_client = ImageClient()

    # Track results
    results = {
        "generated": 0,
        "failed": 0,
        "errors": []
    }

    try:
        # 1. Get decorated stories needing images
        print("[Step 3b] Fetching stories needing images...")
        pending_decorations = _get_pending_decorations(airtable)

        if not pending_decorations:
            print("[Step 3b] No stories need images")
            return results

        print(f"[Step 3b] Found {len(pending_decorations)} stories needing images")

        # 2. Process each story
        for decoration in pending_decorations:
            record_id = decoration.get('id', '')
            fields = decoration.get('fields', {})
            story_id = fields.get('storyID', 'unknown')

            print(f"[Step 3b] Processing story: {story_id}")

            try:
                # Get image prompt
                image_prompt = fields.get('image_prompt', '')

                if not image_prompt:
                    # Generate fallback prompt from headline
                    headline = fields.get('ai_headline', '')
                    image_prompt = f"Abstract editorial illustration representing: {headline}"

                # 2a-c. Generate, optimize, and upload image
                print(f"[Step 3b] Generating image for {story_id}...")
                image_url, source = image_client.process_image(image_prompt, story_id)

                if image_url:
                    # 2d. Update decoration record
                    print(f"[Step 3b] Updating record with image URL ({source})...")
                    airtable.update_decoration(record_id, {
                        "image_url": image_url,
                        "image_status": "generated",
                        "image_source": source,
                        "date_image_generated": datetime.utcnow().strftime('%Y-%m-%d')
                    })

                    results["generated"] += 1
                    print(f"[Step 3b] Image generated for {story_id}")

                else:
                    # Mark as failed
                    airtable.update_decoration(record_id, {
                        "image_status": "failed",
                        "image_error": "Generation failed"
                    })

                    results["failed"] += 1
                    results["errors"].append({
                        "storyId": story_id,
                        "error": "Image generation failed"
                    })

            except Exception as e:
                print(f"[Step 3b] Error processing {story_id}: {e}")
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
                except Exception:
                    pass

        print(f"[Step 3b] Image generation complete: {results}")
        return results

    except Exception as e:
        print(f"[Step 3b] Fatal error: {e}")
        results["errors"].append({"fatal": str(e)})
        raise


def _get_pending_decorations(airtable: AirtableClient) -> List[dict]:
    """
    Get decorated stories that need images generated.

    Filter: image_status='pending' OR image_status='needs_image'
    """
    table = airtable._get_table(
        airtable.ai_editor_base_id,
        airtable.decoration_table_id
    )

    filter_formula = "OR({image_status}='pending', {image_status}='needs_image')"

    records = table.all(
        formula=filter_formula,
        fields=[
            'storyID', 'pivotId', 'ai_headline', 'image_prompt',
            'image_status', 'slot_order'
        ]
    )

    return records


def regenerate_image(record_id: str) -> dict:
    """
    Manual image regeneration for a specific decoration record.

    Args:
        record_id: Airtable record ID

    Returns:
        {success: bool, image_url: str, source: str, error: str}
    """
    print(f"[Step 3b] Manual regeneration for record: {record_id}")

    airtable = AirtableClient()
    image_client = ImageClient()

    try:
        # Get the decoration record
        table = airtable._get_table(
            airtable.ai_editor_base_id,
            airtable.decoration_table_id
        )
        record = table.get(record_id)

        if not record:
            return {"success": False, "error": "Record not found"}

        fields = record.get('fields', {})
        story_id = fields.get('storyID', 'unknown')
        image_prompt = fields.get('image_prompt', '')

        if not image_prompt:
            headline = fields.get('ai_headline', '')
            image_prompt = f"Abstract editorial illustration representing: {headline}"

        # Generate image
        image_url, source = image_client.process_image(image_prompt, story_id)

        if image_url:
            airtable.update_decoration(record_id, {
                "image_url": image_url,
                "image_status": "generated",
                "image_source": source,
                "date_image_generated": datetime.utcnow().strftime('%Y-%m-%d')
            })

            return {
                "success": True,
                "image_url": image_url,
                "source": source
            }
        else:
            return {
                "success": False,
                "error": "Image generation failed"
            }

    except Exception as e:
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
