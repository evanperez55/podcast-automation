# Phase 1: Foundations - Research

**Researched:** 2026-03-16
**Domain:** Python dependency hygiene, scheduler stub replacement, credential file migration, naming cleanup
**Confidence:** HIGH

## Summary

Phase 1 is a pure stabilization phase — no new features, no architecture changes. Every task has a specific, locatable target in the existing codebase. The work divides into four independent threads: (1) add `openai` to `requirements.txt`, (2) replace the no-op scheduler stub with real uploader calls, (3) move Google credential files to `credentials/` and update the two referencing modules, and (4) rename `_parse_claude_response` to `_parse_llm_response`, consolidate duplicate env reads in `scheduler.py`, and move inline `re` imports to module top.

All required utilities already exist. `retry_utils.py` has a production-ready `retry_with_backoff` decorator with exponential backoff. `notifications.py` has `DiscordNotifier` with a pre-built `notify_failure` method. All four platform uploaders (`YouTubeUploader`, `TwitterUploader`, `InstagramUploader`, `TikTokUploader`) are already imported at the top of `main.py`. The scheduler fix is therefore a wiring task, not a design task.

The only genuine risk is the credential migration: the actual `google_docs_credentials.json` and `google_docs_token.json` files live in the project root today (confirmed via filesystem check). They must be physically moved and all code references updated before the pipeline can run post-merge. No external library research was needed for this phase — all answers are in the existing code.

**Primary recommendation:** Work these four changes in parallel plans since they touch different files with no cross-dependencies. Wire the scheduler first (highest production risk), then credentials migration (file system state change), then the two mechanical cleanups.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Wire real platform uploaders (YouTubeUploader, TwitterUploader, etc.) into `_run_upload_scheduled()` so it actually executes uploads
- On failure: retry 3 times, then mark as failed and send Discord notification via existing `notifications.py`
- Never silently mark uploads as complete — either succeed or fail loudly
- Use existing `retry_utils.py` patterns for retry logic
- Move `google_docs_credentials.json` and `google_docs_token.json` from project root to `credentials/` directory
- Update all code references to use new paths
- Fix the 3 known items: rename `_parse_claude_response` → `_parse_llm_response`, fix duplicate config reads in `scheduler.py`, move inline `re` imports to module top in `main.py`
- Also fix any other obviously wrong naming encountered during the work, but don't do an exhaustive hunt
- Run ruff check/format on touched files to ensure consistency

### Claude's Discretion
- Whether to also migrate `youtube_token.pickle` to JSON-based storage (assess risk vs. scope)
- Whether to move `NAMES_TO_REMOVE` from `config.py` to `.env` (assess based on repo visibility risk)
- Exact retry count and backoff strategy for scheduler (3 retries is the guideline, Claude picks the implementation)
- Any additional obvious cleanup wins encountered during the work

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEBT-02 | openai SDK added to requirements.txt | `openai` is already imported in `content_editor.py` (line 2) — it's a runtime dep, just missing from requirements.txt. Add `openai` (unpinned or pinned to latest 1.x). |
| DEBT-03 | Naming artifacts cleaned up (_parse_claude_response renamed, duplicate config reads fixed, inline re imports moved to top) | Three precise locations identified: `content_editor.py:263` (rename), `scheduler.py:17-20` (use `Config.SCHEDULE_*_DELAY_HOURS`), `main.py:1624,1631,1732` (move `import re` to top). |
| DEBT-04 | Google credential files moved to credentials/ directory | Files confirmed at project root today. Two code files reference old paths: `google_docs_tracker.py:40-41` and `setup_google_docs.py:20,82`. |
| DIST-01 | Scheduled upload execution actually uploads to platforms (fix stub) | Stub is `_run_upload_scheduled()` in `main.py:1559-1606`. All four uploaders already imported. `retry_with_backoff` decorator available in `retry_utils.py`. `DiscordNotifier.notify_failure()` available for failed-upload alerts. |
</phase_requirements>

---

## Standard Stack

### Core (already in project)
| Library | Purpose | Notes |
|---------|---------|-------|
| `openai` | OpenAI API client — used by `content_editor.py` | Missing from `requirements.txt`; add `openai>=1.0.0` |
| `retry_utils.py` | Exponential backoff decorator | In-project module; `retry_with_backoff(max_retries=3, base_delay=1.0, backoff_factor=2.0)` |
| `notifications.py` | Discord webhook alerts | `DiscordNotifier.notify_failure(ep_info, exception, step=...)` |
| `config.py` | Central env var reads | `Config.SCHEDULE_*_DELAY_HOURS` already defined — scheduler.py should use these instead of raw `os.getenv()` |

### No new dependencies needed
All tooling for this phase is already present. Zero new packages required.

## Architecture Patterns

### Scheduler Fix Pattern
The `_run_upload_scheduled()` function in `main.py` currently loops over pending uploads and calls `scheduler.mark_uploaded()` with a placeholder dict. The fix replaces the placeholder with:

1. Instantiate the platform-specific uploader
2. Call upload with data from the schedule entry
3. On success: call `scheduler.mark_uploaded(schedule, platform, result)`
4. On failure after retries: call `scheduler.mark_failed(schedule, platform, error)` (add this method) and send Discord notification
5. Save schedule after each platform attempt (not only after all platforms)

The `retry_with_backoff` decorator pattern already used in `YouTubeUploader` and `TwitterUploader`:

```python
# Source: uploaders/youtube_uploader.py, uploaders/twitter_uploader.py — both already use this pattern
from retry_utils import retry_with_backoff

@retry_with_backoff(max_retries=3, base_delay=1.0, backoff_factor=2.0)
def _upload_to_platform(uploader, ...):
    ...
```

Since the retry decorator is a function wrapper, the scheduler loop should either wrap the upload call with the decorator or call retry logic inline. Inline retry is simpler given the per-platform dispatch pattern:

```python
for item in pending:
    platform = item["platform"]
    try:
        result = _execute_platform_upload(platform, item)
        schedule = scheduler.mark_uploaded(schedule, platform, result)
    except Exception as e:
        logger.error("Upload failed for %s after retries: %s", platform, e)
        schedule = scheduler.mark_failed(schedule, platform, str(e))
        notifier.notify_failure(episode_folder, e, step=f"scheduled_{platform}_upload")
    scheduler.save_schedule(episode_folder, schedule)
```

### Credential Path Pattern
Current pattern in `google_docs_tracker.py` uses bare `Path('google_docs_credentials.json')` (relative, resolves to cwd). The fix uses `Config.BASE_DIR`:

```python
# Before (google_docs_tracker.py lines 40-41)
token_path = Path('google_docs_token.json')
creds_path = Path('google_docs_credentials.json')

# After
token_path = Config.BASE_DIR / 'credentials' / 'google_docs_token.json'
creds_path = Config.BASE_DIR / 'credentials' / 'google_docs_credentials.json'
```

`Config.BASE_DIR` is already used in `youtube_uploader.py` for the YouTube credential paths — this is the established pattern.

### Duplicate Config Read Fix (scheduler.py)
```python
# Before (scheduler.py lines 17-20)
self.youtube_delay = int(os.getenv("SCHEDULE_YOUTUBE_DELAY_HOURS", "0"))
self.twitter_delay = int(os.getenv("SCHEDULE_TWITTER_DELAY_HOURS", "0"))
self.instagram_delay = int(os.getenv("SCHEDULE_INSTAGRAM_DELAY_HOURS", "0"))
self.tiktok_delay = int(os.getenv("SCHEDULE_TIKTOK_DELAY_HOURS", "0"))

# After
self.youtube_delay = Config.SCHEDULE_YOUTUBE_DELAY_HOURS
self.twitter_delay = Config.SCHEDULE_TWITTER_DELAY_HOURS
self.instagram_delay = Config.SCHEDULE_INSTAGRAM_DELAY_HOURS
self.tiktok_delay = Config.SCHEDULE_TIKTOK_DELAY_HOURS
```

Note: The existing `TestUploadSchedulerInit` tests use `@patch.dict("os.environ", ...)` which patches env vars before `Config` class-level reads. These tests will continue to pass only if `Config` attributes are read at instance time or the tests are updated to patch `Config` attributes directly. Verify test behavior after the fix — may need to switch to `@patch.object(Config, 'SCHEDULE_YOUTUBE_DELAY_HOURS', 2)` style.

### Inline Import Fix (main.py)
`main.py` already imports `sys`, `json`, `Path`, `datetime` at the top (lines 3-6). Add `re` to this block. Remove the three inline `import re as _re` / `import re` occurrences at lines 1624, 1631, 1732.

### Anti-Patterns to Avoid
- **Silent success on upload failure:** The entire point of DIST-01 is that the old code called `mark_uploaded` even when no upload happened. Never call `mark_uploaded` unless the upload actually succeeded.
- **Relative paths for credentials:** `Path('filename.json')` resolves to cwd, which is fragile. Always anchor to `Config.BASE_DIR`.
- **Raw `os.getenv()` duplicating Config:** Config centralizes env reads to avoid inconsistency. Don't call `os.getenv()` for values already in Config.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom retry loop with `time.sleep` | `retry_with_backoff` decorator in `retry_utils.py` | Already handles logging, configurable backoff, last-exception re-raise |
| Discord failure alert | Direct `requests.post` to webhook | `DiscordNotifier.notify_failure()` | Handles formatting, error suppression, disabled state |
| Platform upload dispatch | New uploader abstraction | Call existing `YouTubeUploader`, `TwitterUploader`, etc. directly | They already handle auth, retry at upload level, error types |

**Key insight:** Every utility needed for this phase already exists in the codebase. The only construction work is wiring them together in `_run_upload_scheduled()`.

## Common Pitfalls

### Pitfall 1: Scheduler tests break after Config consolidation
**What goes wrong:** `TestUploadSchedulerInit` patches `os.environ` to test different delay values. After changing `scheduler.py` to read `Config.SCHEDULE_*_DELAY_HOURS`, the patches no longer affect the values because `Config` class attributes are evaluated at import time.
**Why it happens:** Python class-level attribute assignment (`SCHEDULE_YOUTUBE_DELAY_HOURS = int(os.getenv(...))`) runs once when the module loads. Patching `os.environ` after that has no effect.
**How to avoid:** Update the existing scheduler tests to use `@patch.object(Config, 'SCHEDULE_YOUTUBE_DELAY_HOURS', 2)` instead of `@patch.dict("os.environ", ...)`. Alternatively, use `monkeypatch.setattr(Config, ...)` which is already used in save/load tests.
**Warning signs:** Tests pass in isolation but fail together, or test values don't match what was patched.

### Pitfall 2: Credential files referenced before physical move
**What goes wrong:** Code is updated to use `credentials/` paths but the actual JSON files are still in the project root. Pipeline crashes at runtime with `FileNotFoundError`.
**Why it happens:** Code change and file move are separate operations — easy to do one without the other.
**How to avoid:** The plan task for credential migration must both move the files AND update the code references. Verify with `ls credentials/` after the task.

### Pitfall 3: Mark failed uploads as uploaded
**What goes wrong:** Exception handling in the scheduler loop catches errors but still calls `mark_uploaded`, defeating the purpose of the fix.
**Why it happens:** Copy-paste from the existing stub which always calls `mark_uploaded`.
**How to avoid:** `mark_uploaded` is only called in the success path. Failures go to a new `mark_failed` method (add it to `UploadScheduler`) that sets `status: "failed"` and stores the error message.

### Pitfall 4: openai version conflict with whisperx
**What goes wrong:** `whisperx==3.1.6` pins `torch==2.1.0`. The `openai` package itself has no torch dependency, so there is no actual conflict. However, a broad `pip install openai` in a fresh environment may update transitive deps.
**Why it happens:** Concern about pinned torch being bumped.
**How to avoid:** Add `openai>=1.0.0` without an upper bound. The openai package is pure Python (no native deps). Confirm with `pip install openai --dry-run` that torch is not affected.

### Pitfall 5: setup_google_docs.py hardcodes error message with old path
**What goes wrong:** `setup_google_docs.py:23` prints `"google_docs_credentials.json not found!"` using the old filename without path context. After migration, users following this error message will look in the wrong place.
**Why it happens:** The error message was written for the old layout.
**How to avoid:** Update the error message in `setup_google_docs.py` to reference the new path (`credentials/google_docs_credentials.json`).

## Code Examples

### retry_with_backoff usage (verified from retry_utils.py)
```python
# Source: retry_utils.py
from retry_utils import retry_with_backoff

@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0, backoff_factor=2.0)
def upload_something():
    # If this raises, it will be retried up to 3 times
    # After 3 failures, the last exception is re-raised
    ...
```

### mark_failed pattern to add to UploadScheduler
```python
def mark_failed(self, schedule: dict, platform: str, error: str) -> dict:
    """Mark a platform upload as failed in the schedule."""
    if platform in schedule.get("platforms", {}):
        schedule["platforms"][platform]["status"] = "failed"
        schedule["platforms"][platform]["error"] = error
        schedule["platforms"][platform]["failed_at"] = datetime.now().isoformat()
        logger.error("Marked %s as failed: %s", platform, error)
    return schedule
```

### Config.BASE_DIR credential path pattern (verified from youtube_uploader.py)
```python
# Source: uploaders/youtube_uploader.py lines 27-28
TOKEN_PATH = Config.BASE_DIR / "credentials" / "youtube_token.pickle"
CREDENTIALS_PATH = Config.BASE_DIR / "credentials" / "youtube_credentials.json"
```

Apply same pattern for Google Docs credentials:
```python
# google_docs_tracker.py — after fix
token_path = Config.BASE_DIR / "credentials" / "google_docs_token.json"
creds_path = Config.BASE_DIR / "credentials" / "google_docs_credentials.json"
```

## Claude's Discretion Recommendations

### youtube_token.pickle migration
**Recommendation: Out of scope for Phase 1.** The pickle format is a minor smell but it works and migration would require OAuth re-authentication. `youtube_uploader.py` already stores the token in `credentials/` (correct location). No production risk here.

### NAMES_TO_REMOVE in config.py
**Recommendation: Leave in config.py.** These are first names of podcast hosts — personal info that should NOT be in a public `.env` example. The `config.py` file would be in `.gitignore` or understood to be private. Moving to `.env` provides no meaningful security benefit and adds friction. Out of scope.

### Retry strategy for scheduler
**Recommendation:** Use `retry_with_backoff(max_retries=3, base_delay=2.0, max_delay=30.0, backoff_factor=2.0)` — 3 retries with 2s/4s/8s delays, capped at 30s. This gives the platform APIs brief recovery time without blocking the scan loop for too long.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`) |
| Quick run command | `pytest tests/test_scheduler.py tests/test_content_editor.py -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-02 | `import openai` succeeds in fresh env | smoke | `pip install openai --dry-run` (manual verify) | N/A |
| DEBT-03 | `_parse_llm_response` callable, no `_parse_claude_response` | unit | `pytest tests/test_content_editor.py -x` | Yes |
| DEBT-03 | scheduler uses Config attrs not os.getenv | unit | `pytest tests/test_scheduler.py -x` | Yes (needs update) |
| DEBT-04 | Google credential files found at new path | unit | New test in `tests/test_google_docs_tracker.py` | No — Wave 0 gap |
| DIST-01 | Upload failure raises exception / marks failed | unit | New test in `tests/test_scheduler.py` TestRunUploadScheduled class | No — Wave 0 gap |
| DIST-01 | Successful upload marks platform uploaded | unit | New test in `tests/test_scheduler.py` | No — Wave 0 gap |

### Sampling Rate
- **Per task commit:** `pytest tests/test_scheduler.py tests/test_content_editor.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scheduler.py` — add `TestRunUploadScheduled` class covering: upload success marks uploaded, upload failure marks failed + Discord notification sent, no silent success
- [ ] `tests/test_google_docs_tracker.py` — add test verifying credential paths resolve to `credentials/` directory (mock filesystem, confirm `Config.BASE_DIR / "credentials" / ...` is used)
- [ ] `scheduler.py` — add `mark_failed` method (needed by DIST-01 implementation)

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `main.py`, `scheduler.py`, `content_editor.py`, `retry_utils.py`, `notifications.py`, `google_docs_tracker.py`, `setup_google_docs.py`, `config.py`, `uploaders/youtube_uploader.py`, `uploaders/twitter_uploader.py`
- Filesystem inspection confirming `google_docs_credentials.json` and `google_docs_token.json` are at project root
- `requirements.txt` confirming `openai` package is absent
- `tests/test_scheduler.py` confirming existing test patterns and what needs updating

### Secondary (MEDIUM confidence)
- None needed — all findings are from direct code inspection

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — confirmed by direct code inspection
- Architecture: HIGH — all patterns found in existing working modules
- Pitfalls: HIGH — identified from concrete code paths, not speculation

**Research date:** 2026-03-16
**Valid until:** Stable — changes only if someone touches the affected files
