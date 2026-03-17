# Testing Patterns

**Analysis Date:** 2026-03-16

## Test Framework

**Runner:**
- pytest (version from `requirements.txt`)
- Config: `pyproject.toml` — `testpaths = ["tests"]`

**Assertion Library:**
- pytest built-in `assert` statements (no separate assertion library)

**Mocking:**
- `unittest.mock` — `patch`, `patch.object`, `patch.dict`, `Mock`, `MagicMock`, `mock_open`

**Run Commands:**
```bash
pytest                 # Run all tests
pytest --cov           # Run with coverage
pytest tests/test_analytics.py  # Run single file
pytest -v              # Verbose output
```

## Test File Organization

**Location:** All tests in `tests/` directory (separate from source)

**Naming:**
- `tests/test_<module>.py` maps directly to source module: `tests/test_analytics.py` tests `analytics.py`
- Uploader tests: `tests/test_youtube_uploader.py` tests `uploaders/youtube_uploader.py`

**Structure:**
```
tests/
├── __init__.py              # Empty (pytest discovery only)
├── test_analytics.py
├── test_audio_processor.py
├── test_audiogram_generator.py
├── test_blog_generator.py
├── test_clip_previewer.py
├── test_content_editor.py
├── test_instagram_uploader.py
├── test_notifications.py
├── test_pipeline_state.py
├── test_process_historical_episodes.py
├── test_retry_utils.py
├── test_scheduler.py
├── test_search_index.py
├── test_spotify_uploader.py
├── test_subtitle_generator.py
├── test_thumbnail_generator.py
├── test_tiktok_uploader.py
├── test_twitter_uploader.py
├── test_video_converter.py
└── test_youtube_uploader.py
```

Total: 20 test files, ~4,910 lines, 279+ tests.

## Test Structure

**Suite Organization:**
```python
"""Module docstring describing what is tested."""

import pytest
from unittest.mock import patch, Mock, MagicMock, mock_open

from module_under_test import ClassUnderTest
from config import Config


# Module-level test fixtures (shared sample data)
SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode",
    ...
}


class TestClassNameAction:
    """Tests for ClassName.<action>."""

    def test_<what>_<condition>(self):
        """Docstring describing what this test verifies."""
        ...
```

**Class grouping:** Tests are grouped into classes named `Test<ClassName><Action>` or `Test<ClassName>` when all tests relate to one class. For example, `analytics.py` has:
- `TestAnalyticsCollectorInit`
- `TestFetchYouTubeAnalytics`
- `TestFetchTwitterAnalytics`
- `TestCollectAnalytics`
- `TestSaveAndLoadAnalytics`
- `TestCalculateEngagementScore`

**Docstrings on test methods:** Every test method has a one-line docstring stating what it verifies.

**Setup/Teardown:**
- Prefer `tmp_path` (pytest built-in fixture) for filesystem isolation
- `monkeypatch.setattr(Config, "ATTR", value)` to override Config attributes cleanly
- No `setUp`/`tearDown` methods — use pytest fixtures or `patch.dict` context managers

**Three-part structure** used in many tests (especially `test_audio_processor.py`):
```python
def test_apply_censorship_with_mp4_file(self, mock_from_file, audio_processor, mock_audio_segment, tmp_path):
    # Setup
    mock_from_file.return_value = mock_audio_segment
    audio_file = tmp_path / "test.mp4"
    audio_file.write_text("fake")

    # Execute
    result = audio_processor.apply_censorship(audio_file, [], output_path)

    # Verify
    assert result == output_path
```

## Mocking

**Framework:** `unittest.mock` — `@patch`, `@patch.object`, `patch.dict`, `Mock`, `MagicMock`

**Patching Config class attributes:**
```python
# Preferred: patch.object patches at class level, affects all instances
@patch.object(Config, "TWITTER_API_KEY", "valid_key")
@patch.object(Config, "DISCORD_WEBHOOK_URL", None)

# Also used: monkeypatch for fixtures
def test_foo(self, monkeypatch):
    monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
```

**Patching env vars:**
```python
# patch.dict with clear=True to isolate from actual environment
@patch.dict("os.environ", {}, clear=True)
@patch.dict("os.environ", {"ANALYTICS_ENABLED": "true"})

# In init tests that re-read env vars via os.getenv:
with patch.dict("os.environ", {"SCHEDULE_YOUTUBE_DELAY_HOURS": "2"}):
    scheduler = UploadScheduler()
```

**Patching module-level functions:**
```python
# Patch by full dotted path to the module where it's imported
@patch("analytics.Path.mkdir")
@patch("notifications.requests.post")
@patch("uploaders.twitter_uploader.tweepy.Client")
@patch("uploaders.youtube_uploader.build")
```

**Patching instance methods:**
```python
# patch.object on an already-created instance
with patch.object(collector, "fetch_youtube_analytics", return_value=youtube_data):
    result = collector.collect_analytics(25)
```

**API mock chain pattern (for chained calls like `api.resource().list().execute()`):**
```python
mock_youtube = MagicMock()
mock_youtube.search().list().execute.return_value = {"items": [...]}
with patch("googleapiclient.discovery.build", return_value=mock_youtube):
    result = collector.fetch_youtube_analytics(25)
```

**What to Mock:**
- All external API calls (YouTube, Twitter, Discord, Dropbox)
- File I/O when testing logic (not when testing actual persistence)
- `Path.mkdir`, `Path.exists` when testing code that creates directories
- `time.sleep` in retry tests to avoid slow tests

**What NOT to Mock:**
- SQLite operations in `search_index.py` tests — use `tmp_path` with real DB
- `Path` operations in tests that verify actual file persistence (round-trip tests use `tmp_path`)
- Pure computation methods (engagement score calculation, string formatting)

## Fixtures and Factories

**pytest fixtures for reusable test objects:**
```python
@pytest.fixture
def audio_processor():
    """Create an AudioProcessor instance."""
    return AudioProcessor()

@pytest.fixture
def mock_audio_segment():
    """Create a mock AudioSegment."""
    audio = Mock(spec=AudioSegment)
    audio.duration_seconds = 100.0
    return audio
```

**Module-level sample data constants** for complex dict structures:
```python
# Defined at module top, reused across multiple test classes
SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode Title",
    "episode_summary": "A great episode about testing.",
    "chapters": [...],
    "social_captions": {"youtube": "YT caption", ...},
}
```

**Helper functions** for setup in test modules without a class:
```python
def _make_index(tmp_path):
    """Helper to create an EpisodeSearchIndex backed by a temp database."""
    db_path = str(tmp_path / "test.db")
    return EpisodeSearchIndex(db_path=db_path)
```

**Location:** Fixtures defined at top of test file or inline. No shared `conftest.py` detected — fixtures are file-local.

## Coverage

**Requirements:** No enforced threshold in `pyproject.toml`

**View Coverage:**
```bash
pytest --cov
pytest --cov --cov-report=html
```

## Test Types

**Unit Tests:**
- Primary test type — all 279+ tests are unit tests
- Test single class methods in isolation
- External dependencies always mocked

**Integration Tests:**
- No separate integration test suite
- Round-trip tests (save + load) use `tmp_path` for real filesystem/SQLite interaction without mocking storage layer

**E2E Tests:**
- Not present

## Common Patterns

**Testing the `enabled` flag pattern:**
```python
def test_init_disabled(self):
    """BLOG_ENABLED=false should set enabled=False."""
    with patch.dict("os.environ", {"BLOG_ENABLED": "false"}):
        gen = BlogPostGenerator()
        assert gen.enabled is False

def test_send_notification_disabled(self, mock_post):
    """When disabled, returns False without making a request."""
    notifier = DiscordNotifier()  # no webhook = disabled
    result = notifier.send_notification("Title", "Description")
    assert result is False
    mock_post.assert_not_called()
```

**Testing failure/exception paths:**
```python
def test_fetch_youtube_failure(self, mock_mkdir):
    """YouTube fetch returns None on exception."""
    collector = AnalyticsCollector()
    with patch("analytics.Path.exists", return_value=True):
        with patch("builtins.open", side_effect=Exception("API error")):
            result = collector.fetch_youtube_analytics(25)
    assert result is None
```

**Testing raises:**
```python
def test_init_without_credentials(self):
    """Test initialization fails without credentials."""
    with pytest.raises(ValueError, match="Twitter API credentials not configured"):
        TwitterUploader()
```

**Async Testing:**
- Not used — all code is synchronous

**Verifying call arguments:**
```python
# Check that mock was called with correct structure
call_kwargs = mock_post.call_args
payload = call_kwargs.kwargs["json"]
embed = payload["embeds"][0]
assert embed["title"] == "Test Title"
assert embed["color"] == 0x00FF00
```

**Real-filesystem round-trip tests:**
```python
def test_save_and_load_analytics(self, mock_mkdir, tmp_path):
    """Round-trip save then load preserves data."""
    collector = AnalyticsCollector()
    collector.analytics_dir = tmp_path  # redirect to tmp

    saved_path = collector.save_analytics(25, analytics_data)
    assert saved_path.exists()

    loaded = collector.load_analytics(25)
    assert loaded == analytics_data
```

**Precision assertions for numeric calculations:**
```python
# pytest.approx for floating point
assert delays[0] == pytest.approx(1.0)

# Exact float comparison when result is known exactly
score = scorer.calculate_engagement_score(analytics_data)
assert score == 7.1
```

## Entry Point

Each test file ends with:
```python
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

This allows running individual test files directly with `python tests/test_analytics.py`.

---

*Testing analysis: 2026-03-16*
