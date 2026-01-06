# Google News URL Resolution Fix

**Date:** December 27, 2025
**File Modified:** `workers/jobs/ingest.py`
**Status:** Implemented

---

## Problem

Google News RSS feed URLs were not being resolved to their actual source URLs. The logs showed:

```
[Ingest] Resolved Google News URL: https://news.google.com/rss/articles/CBMi... -> https://news.google.com/rss/articles/CBMi... (source: Google)
```

The input and output URLs were **identical** - no actual resolution was happening.

---

## Root Cause

The original code used HTTP redirects (`allow_redirects=True` with aiohttp) to resolve Google News URLs. However, **Google News URLs are NOT HTTP redirects**.

Google News RSS URLs look like:
```
https://news.google.com/rss/articles/CBMihgFodHRwczovL3d3dy50ZWNoY3J1bmNoLmNv...
```

The `CBMi...` portion after `/articles/` is **Base64-encoded protobuf data** that contains the actual article URL embedded within it.

### Why HTTP Redirects Don't Work

- Making an HTTP GET request to a Google News URL returns a 200 response with an HTML page
- There is no HTTP 301/302 redirect header
- The `allow_redirects=True` parameter has no effect
- The final URL remains the Google News URL

---

## Solution

Added a new `decode_google_news_url()` function that:

1. Extracts the Base64-encoded portion from the URL path
2. Decodes it using URL-safe Base64
3. Searches the decoded bytes for embedded HTTP URLs
4. Returns the actual source URL (e.g., `techcrunch.com`, `wired.com`)

---

## Code Changes

### New Function: `decode_google_news_url()`

```python
def decode_google_news_url(url: str) -> Optional[str]:
    """
    Decode a Google News article URL to get the actual source URL.

    Google News RSS feeds use URLs like:
    https://news.google.com/rss/articles/CBMi...

    The part after 'articles/' is a Base64-encoded protobuf containing the real URL.
    """
    import base64
    import re

    try:
        # Extract the encoded part from the URL
        match = re.search(r'/articles/([^?]+)', url)
        if not match:
            return None

        encoded = match.group(1)

        # Add padding if needed for base64
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += '=' * padding

        # URL-safe base64 decode
        try:
            decoded_bytes = base64.urlsafe_b64decode(encoded)
        except Exception:
            decoded_bytes = base64.b64decode(encoded)

        # Extract URL from decoded bytes
        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')

        # Find URL patterns in the decoded string
        url_match = re.search(r'(https?://[^\s\x00-\x1f"<>]+)', decoded_str)
        if url_match:
            found_url = url_match.group(1)
            # Clean up any trailing garbage characters
            found_url = re.sub(r'[\x00-\x1f].*', '', found_url)
            found_url = found_url.rstrip('"\'>)}]')
            return found_url

        return None

    except Exception as e:
        print(f"[Ingest] Error decoding Google News URL: {e}")
        return None
```

### Updated Function: `resolve_google_news_url()`

```python
async def resolve_google_news_url(
    session: aiohttp.ClientSession,
    url: str
) -> tuple[str, Optional[str]]:
    """
    Resolve a Google News redirect URL to the actual article URL.
    Uses Base64 decoding instead of following HTTP redirects.
    """
    if not url or "news.google.com" not in url:
        return url, None

    try:
        # Decode the Google News URL to get the actual article URL
        decoded_url = decode_google_news_url(url)

        if decoded_url and decoded_url != url:
            source_name = extract_source_from_url(decoded_url)
            print(f"[Ingest] Decoded Google News URL: {url[:50]}... -> {decoded_url[:60]}... (source: {source_name})")
            return decoded_url, source_name
        else:
            # Fallback: try HTTP redirect method (for older URL formats)
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            ) as response:
                final_url = str(response.url)
                if final_url != url and "news.google.com" not in final_url:
                    source_name = extract_source_from_url(final_url)
                    return final_url, source_name

        print(f"[Ingest] Could not resolve Google News URL: {url[:60]}...")
        return url, "Google News"

    except Exception as e:
        print(f"[Ingest] Failed to resolve Google News URL: {e}")
        return url, "Google News"
```

---

## Expected Behavior After Fix

**Before:**
```
[Ingest] Resolved Google News URL: https://news.google.com/rss/articles/CBMi... -> https://news.google.com/rss/articles/CBMi... (source: Google)
```

**After:**
```
[Ingest] Decoded Google News URL: https://news.google.com/rss/articles/CBMi... -> https://www.techcrunch.com/2025/12/27/article... (source: TechCrunch)
```

---

## n8n Workflow Comparison

The n8n Ingestion Engine workflow (ID: `ddobfIOQeOykMUq6`) uses a similar HTTP redirect approach in its "Resolve URLs" node:

```javascript
const res = await ctx.helpers.httpRequest({
    method: 'GET',
    url,
    followRedirect: true,
    resolveWithFullResponse: true,
    simple: false,
});
const finalUrl = res.request?.uri?.href || res.headers?.location || url;
```

This approach has the **same limitation** - it relies on HTTP redirects which Google News doesn't use for modern URLs. The Python implementation now uses Base64 decoding which correctly handles the encoded URL format.

---

## Testing

To verify the fix is working:

1. Trigger Step 0 Ingest
2. Check the logs for messages like:
   ```
   [Ingest] Decoded Google News URL: ... -> https://actualsite.com/... (source: ActualSite)
   ```
3. Verify articles in Airtable have proper `core_url` values pointing to actual news sites, not `news.google.com`

---

## Related Files

- `workers/jobs/ingest.py` - Main ingest job with URL resolution
- `workers/requirements.txt` - Dependencies (aiohttp for async HTTP)
