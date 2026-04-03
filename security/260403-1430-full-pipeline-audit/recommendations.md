# Security Recommendations — Priority Order

## Priority 1 — Medium (Fix When Convenient)

### 1. Sanitize Blog Generator HTML Output
**Finding:** Blog XSS (#5)
**Effort:** 15 minutes
**File:** `blog_generator.py`
```python
import re

def _sanitize_html(self, markdown: str) -> str:
    """Strip unsafe HTML tags from LLM-generated markdown."""
    safe_tags = r'(?:b|i|em|strong|a|blockquote|code|pre|h[1-6]|ul|ol|li|p|br|hr)'
    return re.sub(rf'<(?!/?{safe_tags}\b)[^>]+>', '', markdown)
```
Call before `save_blog_post()`.

## Priority 2 — Low (Hardening)

### 2. Add Timeouts to All requests Calls
**Finding:** No-timeout requests (#6)
**Effort:** 10 minutes
**Files:** `uploaders/instagram_uploader.py`, `uploaders/tiktok_uploader.py`, `setup_instagram.py`
```python
# Add timeout=30 to every requests.get() and requests.post()
response = requests.get(url, params=params, timeout=30)
```

### 3. Replace os.startfile for Clip Preview (Windows)
**Finding:** shell=True (#2)
**Effort:** 5 minutes
**File:** `clip_previewer.py:126-128`
```python
if os.name == "nt":
    os.startfile(str(clip_path))
```

## Priority 3 — Accepted Risks (No Action Needed)

- Pickle deserialization for YouTube tokens — standard Google OAuth pattern
- Static Twitter/Bluesky credentials — no auto-rotation available
- RSS SSRF — no internal services in current deployment
- GitHub token scope — standard for Pages deployment
- Content calendar tampering — requires local filesystem access
