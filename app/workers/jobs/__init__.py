"""AI Editor 2.0 Background Jobs

Step 1: prefilter_stories - Pre-filter candidates by slot eligibility
Step 2: select_slots - Claude agents select 5 stories for newsletter
Step 3: decorate_stories - Generate headlines, deks, bullets
Step 3b: generate_images - Gemini Imagen 3 + Cloudinary + Cloudflare
Step 4: compile_html - Build email HTML template
Step 4b: send_via_mautic - Send newsletter via Mautic
Step 5: sync_social_posts - Syndicate to P5 Social Posts
"""

from .prefilter import prefilter_stories
from .slot_selection import select_slots
from .decoration import decorate_stories
from .image_generation import generate_images, regenerate_image
from .html_compile import compile_html, preview_html
from .mautic_send import send_via_mautic, test_send, get_send_stats
from .social_sync import sync_social_posts, resync_story, get_social_stats

__all__ = [
    # Step 1
    'prefilter_stories',
    # Step 2
    'select_slots',
    # Step 3
    'decorate_stories',
    # Step 3b
    'generate_images',
    'regenerate_image',
    # Step 4
    'compile_html',
    'preview_html',
    # Step 4b
    'send_via_mautic',
    'test_send',
    'get_send_stats',
    # Step 5
    'sync_social_posts',
    'resync_story',
    'get_social_stats',
]
