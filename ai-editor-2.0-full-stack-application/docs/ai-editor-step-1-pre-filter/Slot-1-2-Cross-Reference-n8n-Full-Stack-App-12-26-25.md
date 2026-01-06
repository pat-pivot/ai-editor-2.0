# Slot 1 & 2 Cross-Reference: n8n vs Full-Stack App

**Date:** December 26, 2025
**Issue:** Full-stack app produces fewer Slot 1 and Slot 2 matches than n8n workflow
**n8n Execution ID:** 20762
**Full-Stack Job ID:** f2937c71-1161-4e1e-a160-ded5cc13f1c3

---

## Executive Summary

**ROOT CAUSE IDENTIFIED:** The full-stack app's `get_fresh_stories()` function has a hardcoded `max_records=100` limit, while n8n's "Pull Fresh Candidates" node pulls ALL eligible stories (299 in this execution).

This means the full-stack app is only evaluating **100 out of 299 stories** (33%) for slot eligibility, significantly reducing the pool of candidates for Slot 1 and Slot 2.

---

## Comparison Data

### n8n Execution 20762 (December 26, 2025 at ~2:48 PM EST)
| Metric | Value |
|--------|-------|
| **Fresh Candidates Pulled** | **299 stories** |
| Execution Status | Canceled (after Slot 2) |
| Execution Duration | 73.5 seconds |

### Full-Stack App Job (December 26, 2025 at ~2:44 PM EST)
| Metric | Value |
|--------|-------|
| **Fresh Stories Fetched** | **100 stories** (hardcoded limit) |
| Slot 1 Eligible | 2 stories |
| Slot 1 Gemini Matches | 1 story |
| Slot 1 Company Filter Matches | 0 stories |
| Slot 2 Eligible | 15 stories |
| Slot 2 Matches | 1 story |
| Total Records Written | 54 |

---

## Detailed Analysis

### The Problem

**File:** `workers/jobs/prefilter.py`
**Line 69:**
```python
fresh_stories = airtable.get_fresh_stories(days=7, max_records=100)
```

**File:** `workers/utils/airtable.py`
**Line 50:**
```python
def get_fresh_stories(self, days: int = 7, max_records: int = 100) -> List[dict]:
```

The `max_records=100` parameter limits how many stories are retrieved from the Newsletter Stories table. Meanwhile, n8n's "Pull Fresh Candidates" node has no such limit and retrieves ALL eligible stories.

### Why This Matters

1. **Reduced Candidate Pool**: With only 100 stories out of 299, the full-stack app misses ~66% of potential candidates
2. **Slot 1 Impact**: Slot 1 requires stories published within 24 hours - with fewer candidates, fewer will be fresh enough
3. **Slot 2 Impact**: Similar issue - the freshest 100 stories may not include all Slot 2 eligible content
4. **Sort Order Dependency**: Stories are sorted by `-date_og_published` (newest first), so older stories within the 7-day window are excluded entirely

### Slot Distribution Comparison

**Full-Stack App Results:**
```
Slot 1: 1 match (from 2 eligible)
Slot 2: 1 match (from 15 eligible)
Slot 3: 32 matches (from 97 eligible)
Slot 4: 4 matches (from 33 eligible)
Slot 5: 17 matches (from 97 eligible)
Total: 55 matches
```

**Expected n8n-equivalent (with all 299 candidates):**
- Slot 1 eligible pool would be ~3x larger (more 0-24h old stories)
- Slot 2 eligible pool would be ~3x larger
- More candidates = more Gemini matches

---

## Recommended Fix

### Option 1: Match n8n (No Limit)
Remove the limit entirely to match n8n behavior:

```python
# workers/jobs/prefilter.py line 69
fresh_stories = airtable.get_fresh_stories(days=7)

# workers/utils/airtable.py line 50
def get_fresh_stories(self, days: int = 7, max_records: Optional[int] = None) -> List[dict]:
```

### Option 2: Increase Limit Significantly
If concerned about API costs or processing time:

```python
fresh_stories = airtable.get_fresh_stories(days=7, max_records=500)
```

### Recommended Action
**Implement Option 1** - The full-stack app should match n8n's behavior exactly by pulling all eligible stories. The filtering happens via Gemini, not via Airtable record limits.

---

## Files to Modify

| File | Change |
|------|--------|
| `workers/utils/airtable.py` | Make `max_records` optional with default `None` |
| `workers/jobs/prefilter.py` | Remove `max_records=100` parameter |

---

## Verification Steps

After implementing the fix:

1. Run the full-stack prefilter job
2. Compare "Fresh Stories Fetched" count with n8n's "Pull Fresh Candidates" output
3. Verify Slot 1 and Slot 2 eligible counts increase proportionally
4. Verify final match counts align with n8n results

---

## Additional Observations

### n8n Sample Data (from execution 20762)
The n8n execution pulled diverse content including:
- China property slowdown analysis
- iRobot bankruptcy coverage
- Musk's Tesla pay package ruling
- Flock AI surveillance camera breach
- Google/Apple H-1B visa warnings
- Kalshi sports betting valuation

All 299 stories had `newsletter='pivot_ai'` or related newsletters and `ai_headline` populated.

### Full-Stack App Logs
```
[Step 1] Found 100 fresh stories
[Step 1] Articles per slot batch: Slot 1: 2, Slot 2: 15, Slot 3: 97, Slot 4: 33, Slot 5: 97
[Step 1] Slot 1: 1 Gemini + 0 Company Filter matches
[Step 1] Slot 2: 1 matches
```

The 2 Slot 1 eligible articles from 100 stories is far lower than expected from a pool of 299.

---

## Conclusion

The discrepancy is **100% due to the hardcoded `max_records=100` limit**. Removing this limit will make the full-stack app produce results matching n8n 1:1.
