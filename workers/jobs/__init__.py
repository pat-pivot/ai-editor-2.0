"""AI Editor 2.0 Background Jobs

Production Pipeline:
  Step 0: ingest_articles - Fetch articles from RSS feeds
  Step 1: prefilter_stories - Pre-filter candidates by slot eligibility
  Step 2: select_slots - Claude agents select 5 stories for newsletter
  Step 3: decorate_stories - Generate headlines, deks, bullets
  Step 3b: generate_images - Gemini Imagen 3 + Cloudinary + Cloudflare
  Step 4: compile_html - Build email HTML template
  Step 4b: send_via_mautic - Send newsletter via Mautic
  Step 5: sync_social_posts - Syndicate to P5 Social Posts

Sandbox Pipeline (FreshRSS-based):
  Step 0a: ingest_sandbox - Fetch from FreshRSS → Articles - All Ingested
  Step 0b: ai_scoring_sandbox - Score & extract → Newsletter Selects

Note: Jobs are imported lazily by trigger.py to avoid circular import issues.
"""

# No auto-imports - trigger.py uses lazy loading
