# Worker and Render Deployment Architecture

**Date:** January 1, 2026
**Source:** Agent analysis of AI Editor 2.0 infrastructure

---

## ARCHITECTURE OVERVIEW

The AI Editor 2.0 uses a **distributed microservices architecture** on Render with the following components:

### Core Services

| Service | Type | Runtime | Purpose |
|---------|------|---------|---------|
| ai-editor-dashboard | Web | Node | Next.js frontend |
| ai-editor-worker | Worker | Python | RQ job processing |
| ai-editor-scheduler | Worker | Python | Cron job scheduling |
| ai-editor-trigger | Web | Python | HTTP trigger endpoints |
| ai-editor-db | Database | PostgreSQL | System prompts, audit logs |
| ai-editor-redis | Cache | Redis | Job queue |

---

## WORKER ENTRY POINT: worker.py

**File:** `/app/workers/worker.py`

### Modes of Operation

```bash
# Mode 1: Worker only (processes jobs from Redis queue)
python worker.py

# Mode 2: Scheduler only (enqueues cron jobs)
python worker.py --with-scheduler
```

### Queue Priority System

The worker listens to 3 queues in priority order:
1. **high** - Slot Selection, Mautic Send (time-sensitive)
2. **default** - Pre-filter, Decoration, Images, HTML Compile
3. **low** - Social Sync (background tasks)

```python
queues = [
    Queue('high', connection=conn),
    Queue('default', connection=conn),
    Queue('low', connection=conn),
]
worker = Worker(queues, connection=conn)
worker.work()
```

---

## SCHEDULER CONFIGURATION

**Cron Schedule:** Tuesday-Saturday (2-6 UTC) for Mon-Fri newsletter delivery

| Step | Time (UTC) | Time (ET) | Queue |
|------|------------|-----------|-------|
| Step 1: Pre-filter | 2:00 AM | 9:00 PM | default |
| Step 2: Slot Selection | 2:15 AM | 9:15 PM | high |
| Step 3: Decoration | 2:25 AM | 9:25 PM | default |
| Step 3b: Images | 2:30 AM | 9:30 PM | default |
| Step 4: HTML Compile | 3:00 AM | 10:00 PM | default |
| Step 4b: Mautic Send | 10:00 AM | 5:00 AM | high |
| Step 5: Social Sync | 9:30 AM | 4:30 AM | low |

---

## JOB ARCHITECTURE PATTERNS

### 1. Standard Job Structure

```python
def step_name_job() -> dict:
    """
    Step X: Description

    Returns:
        dict with: {success, records_processed, errors}
    """
    results = {"processed": 0, "errors": []}

    try:
        print(f"[Step X] Starting job at {datetime.utcnow().isoformat()}")

        # Main logic here

        print(f"[Step X] Job complete: {results}")
        return results

    except Exception as e:
        print(f"[Step X] Fatal error: {e}")
        results["errors"].append({"fatal": str(e)})
        raise
```

### 2. Job Configuration Block

Every job file ends with:

```python
JOB_CONFIG = {
    "func": job_function_name,
    "trigger": "cron",
    "hour": 2,
    "minute": 0,
    "day_of_week": "tue-sat",
    "id": "step_id_name",
    "replace_existing": True
}
```

### 3. Multi-Client Initialization

```python
def step_name() -> dict:
    airtable = AirtableClient()
    claude = ClaudeClient()
    gemini = GeminiClient()

    results = {"processed": 0, "written": 0, "errors": []}

    try:
        # Main job logic
        pass
    except Exception as e:
        results["errors"].append({"fatal": str(e)})
        raise
```

---

## API TRIGGER SYSTEM

**Flask Service:** `/app/workers/trigger.py`

### HTTP Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/jobs/<step_name>` | POST | Trigger a specific job |
| `/jobs/status/<job_id>` | GET | Get job status |
| `/jobs/queue` | GET | Get queue status |
| `/jobs/<job_id>/cancel` | POST | Cancel a specific job |
| `/jobs/cancel-all` | POST | Cancel all jobs |

### Job Function Mapping

```python
JOB_FUNCTIONS = {
    'ingest': ingest_articles,
    'ai_scoring': run_ai_scoring,
    'prefilter': prefilter_stories,
    'slot_selection': select_slots,
    'decoration': decorate_stories,
    'images': generate_images,
    'html_compile': compile_html,
    'mautic_send': send_via_mautic,
    'social_sync': sync_social_posts,
}

QUEUE_MAPPING = {
    'slot_selection': 'high',
    'mautic_send': 'high',
    'prefilter': 'default',
    'decoration': 'default',
    'images': 'default',
    'html_compile': 'default',
    'social_sync': 'low',
}
```

### Job Enqueuing Pattern

```python
queue = Queue(queue_name, connection=conn)
job = queue.enqueue(
    job_func,
    job_timeout='30m',
    **params
)
```

---

## NEXT.JS API ROUTES

**File:** `/app/src/app/api/jobs/route.ts`

### TypeScript Trigger Pattern

```typescript
const TRIGGER_SERVICE_URL = process.env.TRIGGER_SERVICE_URL;

export async function POST(request: NextRequest) {
  const { step, params = {} } = await request.json();

  const response = await fetch(`${TRIGGER_SERVICE_URL}/jobs/${step}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TRIGGER_SECRET}`,
    },
    body: JSON.stringify(params),
  });

  return NextResponse.json(await response.json());
}
```

---

## SHARED UTILITIES

### AirtableClient (`utils/airtable.py`)

```python
class AirtableClient:
    def __init__(self):
        self.pivot_media_base_id = 'appwSozYTkrsQWUXB'
        self.ai_editor_base_id = 'appglKSJZxmA9iHpl'

        # Table IDs
        self.articles_table_id = 'tblGumae8KDpsrWvh'
        self.prefilter_log_table_id = 'tbl72YMsm9iRHj3sp'
        self.decoration_table_id = 'tbla16LJCf5Z6cRn3'
        self.newsletter_selects_table_id = 'tblKhICCdWnyuqgry'
```

### ClaudeClient (`utils/claude.py`)

```python
class ClaudeClient:
    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        self.default_model = "claude-sonnet-4-5-20250929"  # NOT 3.x
```

### GeminiClient (`utils/gemini.py`)

```python
class GeminiClient:
    def __init__(self):
        genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
        self.flash_model = genai.GenerativeModel('gemini-3-flash-preview')  # NOT 2.0
```

---

## STEP 3 DECORATION FLOW PATTERN

```python
def decorate_stories() -> dict:
    airtable = AirtableClient()
    gemini = GeminiClient()
    claude = ClaudeClient()

    for slot in range(1, 6):
        # 1. Fetch article markdown
        article = airtable.get_article_by_pivot_id(pivot_id)

        # 2. Clean using Gemini
        cleaned = gemini.clean_content(markdown)

        # 3. Decorate using Claude
        decoration = claude.decorate_story(story_data, cleaned_content)

        # 4. Apply bolding
        bolded = claude.apply_bolding(bullets)

        # 5. Write result
        record_id = airtable.write_decoration(decoration_data)

    # 6. Update issue status
    airtable.update_issue_status(issue_id, "decorated")
```

---

## ERROR HANDLING PATTERNS

### Graceful Degradation

```python
# Gemini cleaning is optional
try:
    cleaned_content = gemini.clean_content(markdown)
except Exception as e:
    print(f"[Step 3] Gemini cleaning failed, using raw: {e}")
    cleaned_content = markdown[:8000]

# Bolding is optional
try:
    bolded_bullets = claude.apply_bolding(bullets)
except Exception as e:
    print(f"[Step 3] Bolding failed, using original: {e}")
    # Use unbolded bullets
```

### Per-Slot Error Isolation

```python
for slot in range(1, 6):
    try:
        # Process slot
        pass
    except Exception as e:
        results["errors"].append({"slot": slot, "error": str(e)})
        continue  # Skip this slot, continue with others
```

---

## RATE LIMITING & TIMEOUTS

### Job Timeout
All jobs have **30-minute timeout**:
```python
job = queue.enqueue(job_func, job_timeout='30m')
```

### Airtable Batch Limits
- 10 records per batch write
- Chunk large operations:
```python
for i in range(0, len(records), 10):
    batch = records[i:i+10]
    # Write batch
```

### Content Truncation
```python
cleaned_content = markdown[:8000]  # 8KB limit for API calls
```

---

## ENVIRONMENT VARIABLES

### Required
```bash
REDIS_URL=redis://...
DATABASE_URL=postgresql://...
AIRTABLE_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
AIRTABLE_BASE_ID=appwSozYTkrsQWUXB
AI_EDITOR_BASE_ID=appglKSJZxmA9iHpl
TRIGGER_SECRET=...
```

### Optional
```bash
OPENAI_API_KEY=sk-...
CLOUDINARY_URL=cloudinary://...
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_KEY=...
```

---

## RENDER DEPLOYMENT NOTES

### Service Configuration (`render.yaml`)

```yaml
services:
  - type: worker
    name: ai-editor-worker
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python worker.py

  - type: worker
    name: ai-editor-scheduler
    runtime: python
    startCommand: python worker.py --with-scheduler

  - type: web
    name: ai-editor-trigger
    runtime: python
    startCommand: gunicorn --bind 0.0.0.0:$PORT trigger:app
```

### Auto-Deployment
- Push to main triggers deployment
- Services restart in dependency order

### Scaling
- **Worker**: Can have multiple instances (same Redis queue)
- **Scheduler**: Only ONE instance (prevents duplicate jobs)

---

## LOGGING PATTERN

```python
print(f"[Step 3] Starting job at {datetime.utcnow().isoformat()}")
print(f"[Step 3] Processing {count} items...")
print(f"[Step 3] Slot 1: Success")
print(f"[Step 3] ERROR: {error_message}")
print(f"[Step 3] Job complete: {results}")
```

View logs in Render Dashboard → Service → Logs
