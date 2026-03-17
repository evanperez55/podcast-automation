# Coding Conventions

**Analysis Date:** 2026-03-16

## Naming Patterns

**Files:**
- `snake_case.py` for all module files: `audio_processor.py`, `blog_generator.py`, `rss_feed_generator.py`
- `test_<module>.py` for test files: `tests/test_audio_processor.py`
- Uploader modules grouped under `uploaders/` subdirectory: `uploaders/twitter_uploader.py`

**Classes:**
- `PascalCase`: `AudioProcessor`, `DiscordNotifier`, `UploadScheduler`, `AnalyticsCollector`
- One primary class per module, named after the module's purpose
- Helper/secondary classes in same file when closely related: `TopicEngagementScorer` in `analytics.py`

**Functions and Methods:**
- `snake_case` for all public methods: `fetch_youtube_analytics`, `send_notification`, `create_schedule`
- `_snake_case` with single underscore prefix for private helpers: `_get_beep_sound`, `_build_prompt`, `_parse_index`, `_generate_fallback`
- Verb-noun pattern for method names: `apply_censorship`, `save_analytics`, `mark_uploaded`

**Variables:**
- `snake_case` for local variables and instance attributes
- `UPPER_SNAKE_CASE` for class-level constants on `Config`: `FFMPEG_PATH`, `PODCAST_NAME`, `CLIP_MIN_DURATION`

**Test Methods:**
- `test_<what>_<condition>` format: `test_fetch_youtube_success`, `test_init_disabled`, `test_send_notification_with_fields`

## Code Style

**Formatting:**
- Tool: `ruff format` (enforced via pre-commit hook)
- Line length: default ruff (88 chars)
- Double quotes for strings

**Linting:**
- Tool: `ruff check`
- `# noqa: F401` used on unused imports that are intentional: `import json  # noqa: F401` in `blog_generator.py`

## Module Structure Pattern

Every feature module follows this consistent structure:

```python
"""Module docstring describing purpose."""

import stdlib_modules
from pathlib import Path
from typing import Optional, Dict, Any  # type hints on public methods

from config import Config   # always imported
from logger import logger   # always imported


class FeatureClass:
    """Class docstring."""

    def __init__(self):
        """Initialize with self.enabled gated by env var."""
        self.enabled = os.getenv("FEATURE_ENABLED", "true").lower() == "true"

    def public_method(self, param: type) -> ReturnType:
        """Docstring with Args/Returns sections for non-trivial methods."""
        if not self.enabled:
            logger.warning("Feature disabled...")
            return False
        ...

    def _private_helper(self):
        """Helper method."""
        ...
```

## Import Organization

**Order:**
1. Standard library (`import os`, `import json`, `from pathlib import Path`, `from typing import ...`)
2. Third-party packages (`import requests`, `import tweepy`)
3. Internal modules (`from config import Config`, `from logger import logger`)

**Path Aliases:**
- None — flat module structure, all top-level imports by module name

**Conditional imports:**
- Heavy/optional dependencies imported inside method body: `import openai` inside `generate_blog_post`, `import pickle` inside `fetch_youtube_analytics`

## The `self.enabled` Pattern

All feature modules gate behavior with an `enabled` flag set from env vars in `__init__`:

```python
# Pattern from notifications.py
self.enabled = bool(self.webhook_url)

# Pattern from analytics.py / blog_generator.py
self.enabled = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"

# When disabled, methods return early with False/None:
if not self.enabled:
    logger.warning("Feature disabled (no webhook URL configured)")
    return False
```

Config class defines the canonical defaults at `config.py` (e.g., `ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"`).

## Error Handling

**Patterns:**
- External API calls wrapped in `try/except`, return `None` on failure (never raise to caller)
  ```python
  # From analytics.py pattern
  try:
      result = api.call()
      return result
  except Exception as e:
      logger.warning("Failed to fetch: %s", e)
      return None
  ```
- Specific exception types where possible: `requests.RequestException`, `FileNotFoundError`
- `raise` used at system boundaries (missing credentials, missing required files)
  ```python
  # From youtube_uploader.py pattern
  if not creds_path.exists():
      raise FileNotFoundError("YouTube credentials file not found")
  ```
- `ValueError` raised for missing configuration: `raise ValueError(f"Missing required configuration: {', '.join(missing)}")`
- No bare `except:` clauses — always catches named exception or `Exception as e`

**Return conventions:**
- Methods returning results: return `None` on failure, data dict on success
- Methods returning status: return `True` on success, `False` on failure
- Always log with `logger.warning` before returning failure

## Logging

**Framework:** Python `logging` module via `logger.py`

**Import pattern:**
```python
from logger import logger  # module-level singleton
```

**Log levels used:**
- `logger.info(...)` — pipeline progress and state changes
- `logger.debug(...)` — detailed diagnostic data (file paths, metrics, calculations)
- `logger.warning(...)` — non-fatal issues, disabled features, API failures
- `logger.error(...)` — fatal errors after all retries exhausted

**Format:**
```python
# Always use %s formatting, never f-strings in log calls
logger.info("Processing episode: %s", episode_number)
logger.debug("Current dBFS: %.1f, Target: %.1f", current_dbfs, target_dbfs)
```

**Output:** Console (INFO+) and `output/podcast_automation.log` (DEBUG+)

## Comments

**When to Comment:**
- Module-level docstring on every file explaining purpose
- Class-level docstring on every class
- Method docstrings with `Args:` and `Returns:` sections for non-trivial public methods
- Inline comments for non-obvious logic: censorship word lists, algorithm notes

**JSDoc/TSDoc:**
- Python docstrings follow Google style with `Args:` and `Returns:` sections:
  ```python
  def send_notification(self, title, description, color=0x00FF00, fields=None):
      """Send a rich embed notification to Discord.

      Args:
          title: Embed title.
          description: Embed description text.
          color: Embed sidebar color (hex int).
          fields: Optional list of field dicts with name, value, inline keys.

      Returns:
          True if sent successfully, False otherwise.
      """
  ```

## Type Hints

**Usage:** Applied to public method signatures in newer modules, not universally enforced:
```python
def fetch_youtube_analytics(self, episode_number: int) -> Optional[dict]:
def generate_blog_post(self, transcript_data: Dict[str, Any], analysis: Dict[str, Any], episode_number: int) -> str:
```

Older modules have no type hints. `from typing import Optional, Dict, Any, List` imported as needed.

## Function Design

**Size:** Methods generally focused on one task; longer methods (50+ lines) are acceptable for complex orchestration logic in `main.py`

**Parameters:** Prefer keyword arguments for optional parameters with defaults; avoid `*args`/`**kwargs` except in decorators

**Return Values:** Consistent within a class — either data-or-None or True/False, not mixed

## Module Design

**Exports:** No `__all__` defined — all public classes and functions are importable

**Barrel Files:** `tests/__init__.py` is empty (only for pytest discovery); no barrel files in source

## Configuration Access

Config is always accessed via class attributes on the `Config` class — never instantiated:
```python
from config import Config
path = Config.FFMPEG_PATH
name = Config.PODCAST_NAME
```

Env var overrides use `os.getenv()` directly in `__init__` methods; class-level `Config` attributes serve as defaults.

---

*Convention analysis: 2026-03-16*
