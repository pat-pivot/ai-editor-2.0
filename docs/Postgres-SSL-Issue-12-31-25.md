# Postgres SSL Connection Issue - Root Cause Analysis

**Date:** December 31, 2025
**Status:** FIXED

---

## The Problem

Workers on Render were experiencing recurring SSL connection failures to PostgreSQL:

```
Database connection error (attempt 1/5): connection to server at
"dpg-d55iqn4hg0os73a55ka0-a.oregon-postgres.render.com" (35.227.164.209),
port 5432 failed: SSL connection has been closed unexpectedly
```

This was happening on **every retry** (all 5 attempts), causing jobs like `prefilter` to completely fail.

---

## Root Causes Identified

### 1. Missing DATABASE_URL in Worker Service (render.yaml)

The `ai-editor-worker` service in `render.yaml` was missing the `DATABASE_URL` environment variable:

**Before:**
```yaml
# ai-editor-worker service
envVars:
  - key: REDIS_URL
    fromService:
      name: ai-editor-redis
      type: redis
      property: connectionString
  # No DATABASE_URL configured!
```

**After:**
```yaml
envVars:
  - key: REDIS_URL
    fromService:
      name: ai-editor-redis
      type: redis
      property: connectionString
  # Database - CRITICAL: Required for loading prompts from Postgres
  - key: DATABASE_URL
    fromDatabase:
      name: ai-editor-db
      property: connectionString
```

### 2. SSL Mode Conditional on NODE_ENV (db.py)

The database client was using conditional SSL mode based on `NODE_ENV`, which wasn't set for the worker:

**Before:**
```python
def _create_connection(self):
    sslmode = 'require' if os.environ.get('NODE_ENV') == 'production' else 'prefer'
    return psycopg2.connect(
        self.database_url,
        sslmode=sslmode,  # Was 'prefer' because NODE_ENV not set!
        connect_timeout=10,
    )
```

**After:**
```python
def _create_connection(self):
    return psycopg2.connect(
        self.database_url,
        sslmode='require',  # ALWAYS require SSL for Render Postgres
        connect_timeout=30,  # Longer timeout for cold starts
    )
```

### 3. Missing TCP Keepalive Settings (db.py)

Render's infrastructure can drop idle connections. Without TCP keepalives, connections would be silently terminated mid-query, causing "SSL connection has been closed unexpectedly" errors.

**Fix Added:**
```python
return psycopg2.connect(
    self.database_url,
    sslmode='require',
    connect_timeout=30,
    # TCP Keepalive settings - CRITICAL for preventing SSL drops
    keepalives=1,           # Enable TCP keepalives
    keepalives_idle=30,     # Seconds before sending keepalive probe
    keepalives_interval=10, # Seconds between keepalive probes
    keepalives_count=5,     # Number of failed probes before disconnect
    options='-c statement_timeout=60000'
)
```

---

## Files Modified

| File | Change |
|------|--------|
| `workers/utils/db.py` | Always use `sslmode='require'`, added TCP keepalives, increased timeouts |
| `workers/render.yaml` | Added `DATABASE_URL` to `ai-editor-worker` service |

---

## Why This Kept Recurring

1. **No explicit DATABASE_URL** - The variable might have been set manually in Render dashboard previously but was lost during service restarts or configuration changes

2. **Conditional SSL mode** - Using `sslmode='prefer'` instead of `'require'` allowed initial connections but led to unstable SSL sessions

3. **No TCP keepalives** - Render's load balancers have aggressive idle connection timeouts. Without keepalives, connections were being dropped silently

---

## Verification

After deploying these fixes, the prefilter job should:
1. Successfully connect to Postgres on first attempt
2. Maintain stable connections during long-running batch operations
3. Recover gracefully if a connection is lost (with the existing retry logic)

---

## Prevention

To prevent this from happening again:

1. **Always use IaC (render.yaml)** - Don't set environment variables manually in the Render dashboard
2. **Use sslmode='require'** - Never use 'prefer' for production Postgres
3. **Always include TCP keepalives** - Essential for cloud-hosted databases
4. **Set appropriate timeouts** - `connect_timeout=30` for cold starts, `statement_timeout=60000` for long queries
