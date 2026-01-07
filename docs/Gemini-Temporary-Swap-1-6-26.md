# TEMPORARY: Gemini → Claude Pre-Filter Swap

**Date:** January 6, 2026
**Status:** TEMPORARY - Revert when Gemini quota restored
**Reason:** Gemini API 429 RESOURCE_EXHAUSTED (account-level quota exhausted)

---

## Executive Summary

The pre-filter step has been **temporarily** switched from Gemini to Claude Sonnet 4.5 due to Gemini API quota exhaustion. This is a drop-in replacement with the same interface.

**To revert:** Set `PREFILTER_MODEL=gemini` in environment variables.

---

## What Changed

### Files Modified

| File | Change |
|------|--------|
| `workers/jobs/prefilter.py` | Conditional import based on `PREFILTER_MODEL` env var |
| `workers/utils/claude_prefilter.py` | **NEW** - Claude drop-in replacement for GeminiClient |

### Environment Variable

```bash
# Current (Claude - TEMPORARY)
PREFILTER_MODEL=claude  # or unset (defaults to claude)

# To revert to Gemini
PREFILTER_MODEL=gemini
```

---

## Technical Details

### Claude Configuration

- **Model:** `claude-sonnet-4-5-20250929` (Claude Sonnet 4.5)
- **Max Tokens:** 8,192 (Claude supports up to 64K output)
- **Temperature:** 0.3 (same as Gemini)
- **Context Window:** 200K tokens

### Interface (Unchanged)

Both clients have identical method signatures:

```python
def prefilter_batch_slot_1(articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]
def prefilter_batch_slot_2(articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]
def prefilter_batch_slot_3(articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]
def prefilter_batch_slot_4(articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]
def prefilter_batch_slot_5(articles: List[Dict], yesterday_headlines: List[str]) -> List[Dict]
```

**Returns:** `[{"story_id": "recXXX", "headline": "..."}]`

---

## How to Revert to Gemini

When Gemini quota is restored:

### Option 1: Environment Variable (Recommended)

```bash
# In Render Dashboard → Environment Variables
PREFILTER_MODEL=gemini
```

No code changes needed. The existing code will import `GeminiClient` instead of `ClaudePrefilterClient`.

### Option 2: Full Cleanup (When Permanent)

1. Remove or comment out Claude import in `prefilter.py`
2. Delete `workers/utils/claude_prefilter.py`
3. Remove `PREFILTER_MODEL` env var
4. Search for `TODO(gemini-quota)` and clean up markers

---

## Finding Temporary Code

All temporary code is marked with:

```bash
# Search for temporary markers
grep -r "TODO(gemini-quota)" workers/
grep -r "TEMPORARY" workers/
```

### Markers Used

- `TODO(gemini-quota)` - Searchable TODO tag
- `TEMPORARY:` - In comments and docstrings
- `[TEMPORARY Claude` - In log messages
- Banner in `claude_prefilter.py` init

---

## Monitoring

### Logs to Watch

Claude pre-filter logs include `[TEMPORARY Claude slot_X]` prefix:

```
[TEMPORARY Claude slot_1] Using Claude Sonnet 4.5 (Gemini quota exhausted)
[TEMPORARY Claude slot_1] Calling Claude API (attempt 1/3)...
[TEMPORARY Claude slot_1] Found 15 matches
```

### Startup Banner

When Claude is active, a visible banner appears:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  TEMPORARY: Using Claude Sonnet 4.5 for pre-filter (Gemini quota exhausted)  ║
║  TODO(gemini-quota): Revert to GeminiClient when quota restored              ║
║  See: docs/Gemini-Temporary-Swap-1-6-26.md                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Cost Comparison

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Gemini 1.5 Flash | $0.075 | $0.30 |
| Claude Sonnet 4.5 | $3.00 | $15.00 |

**Note:** Claude is significantly more expensive. Revert to Gemini when quota restored.

---

## Error That Triggered This Change

```
google.api_core.exceptions.ResourceExhausted: 429 RESOURCE_EXHAUSTED
Quota exceeded for quota metric 'Generate Content API requests per minute (base model)'
and limit 'GenerateContent request limit per minute for a region (base model)'
```

This is an **account-level quota** issue, not a key-specific issue. Creating new API keys does not help.

---

## Related Files

- `workers/jobs/prefilter.py` - Main pre-filter job
- `workers/utils/claude_prefilter.py` - TEMPORARY Claude client
- `workers/utils/gemini.py` - Original Gemini client (unchanged)
- `docs/Codebase-Migration-Organization-1-6-26.md` - Codebase structure docs

---

## Checklist for Reverting

- [ ] Gemini quota confirmed restored
- [ ] Set `PREFILTER_MODEL=gemini` in Render env vars
- [ ] Trigger a test pre-filter run
- [ ] Verify Gemini logs appear (not Claude)
- [ ] Monitor for 429 errors
- [ ] If stable for 24h, optionally delete `claude_prefilter.py`
- [ ] Update this doc with revert date
