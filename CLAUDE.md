# AI Editor 2.0 - Project Notes

## CRITICAL: Directory Structure

The working directory is `/app/` - this IS the Next.js project root.

- `src/` - The actual source code (Next.js App Router)
- `workers/` - Python workers for cron jobs

**ONLY edit files in `src/`**

## CRITICAL: Deployment

**This project deploys on RENDER, NOT Vercel.**

- Render dashboard: https://dashboard.render.com
- Deployment is automatic on push to main

## Airtable Field Names

### Pre-Filter Log Table (tbl72YMsm9iRHj3sp)
- `core_url` (NOT `original_url`)
- `date_og_published`
- `storyID`, `pivotId`, `headline`, `slot`, `source_id`

### Decoration Table (tbla16LJCf5Z6cRn3)
- `story_id`, `slot_order`, `headline`, `label`
- `b1`, `b2`, `b3`, `ai_dek`
- `image_url`, `image_status`, `social_status`
- `pivotnews_url`
