# Testing Guide

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov

# Run with HTML coverage report
uv run pytest --cov --cov-report=html

# Run a single test file
uv run pytest tests/test_audio_processor.py

# Run with verbose output
uv run pytest -v

# Run a specific test class
uv run pytest tests/test_analytics.py::TestFetchYouTubeAnalytics

# Run a specific test method
uv run pytest tests/test_analytics.py::TestFetchYouTubeAnalytics::test_fetch_youtube_success
```

## Current Stats

- **Test files:** 55 files in `tests/`
- **Total tests:** 1,255+
- **Coverage:** ~94%
- **Lines of test code:** ~25,500

## Pre-Commit Hook

The project uses a pre-commit hook at `.githooks/pre-commit` that runs:

1. `ruff check` -- linting
2. `ruff format --check` -- formatting

Fix lint/format issues before committing:

```bash
uv run ruff check . --fix
uv run ruff format .
```

## Test Conventions

### File Naming

Each test file maps directly to a source module:

| Source Module | Test File |
|--------------|-----------|
| `audio_processor.py` | `tests/test_audio_processor.py` |
| `analytics.py` | `tests/test_analytics.py` |
| `uploaders/youtube_uploader.py` | `tests/test_youtube_uploader.py` |
| `pipeline/steps/video.py` | `tests/test_video_step.py` |
| `pipeline/runner.py` | `tests/test_runner.py` |

### Class Grouping

Tests are grouped into classes named `Test<ClassName><Action>`:

```python
class TestAnalyticsCollectorInit:
    """Tests for AnalyticsCollector initialization."""

class TestFetchYouTubeAnalytics:
    """Tests for AnalyticsCollector.fetch_youtube_analytics."""

class TestCollectAnalytics:
    """Tests for AnalyticsCollector.collect_analytics."""
```

### Test Method Naming

Methods follow `test_<what>_<condition>`:

```python
def test_fetch_youtube_success(self):
    """YouTube fetch returns analytics dict on success."""

def test_init_disabled(self):
    """BLOG_ENABLED=false should set enabled=False."""

def test_send_notification_with_fields(self):
    """Notification with custom fields includes them in embed."""
```

### Docstrings

Every test method has a one-line docstring describing what it verifies.

### Test Structure

Tests follow a three-part arrange/act/assert pattern:

```python
def test_apply_censorship_with_mp4_file(self, mock_from_file, audio_processor, tmp_path):
    # Setup
    mock_from_file.return_value = mock_audio_segment
    audio_file = tmp_path / "test.mp4"
    audio_file.write_text("fake")

    # Execute
    result = audio_processor.apply_censorship(audio_file, [], output_path)

    # Verify
    assert result == output_path
```

### Entry Point

Each test file ends with:

```python
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Mocking Patterns

All external dependencies are mocked. No test calls a real API.

### Patching Config Attributes

```python
# Using @patch.object (preferred for Config class)
@patch.object(Config, "TWITTER_API_KEY", "valid_key")
@patch.object(Config, "DISCORD_WEBHOOK_URL", None)
def test_something(self):
    ...

# Using monkeypatch fixture
def test_something(self, monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
```

### Patching Environment Variables

```python
# Isolate from actual environment
@patch.dict("os.environ", {}, clear=True)
def test_init_defaults(self):
    ...

# Set specific env vars
@patch.dict("os.environ", {"ANALYTICS_ENABLED": "true"})
def test_init_enabled(self):
    ...

# Re-read env vars in init
with patch.dict("os.environ", {"SCHEDULE_YOUTUBE_DELAY_HOURS": "2"}):
    scheduler = UploadScheduler()
```

### Patching Module-Level Functions

Patch by the full dotted path to where the function is imported:

```python
@patch("analytics.Path.mkdir")
@patch("notifications.requests.post")
@patch("uploaders.twitter_uploader.tweepy.Client")
@patch("uploaders.youtube_uploader.build")
```

### Patching Instance Methods

```python
with patch.object(collector, "fetch_youtube_analytics", return_value=youtube_data):
    result = collector.collect_analytics(25)
```

### API Mock Chains

For chained API calls like `api.resource().list().execute()`:

```python
mock_youtube = MagicMock()
mock_youtube.search().list().execute.return_value = {"items": [...]}
with patch("googleapiclient.discovery.build", return_value=mock_youtube):
    result = collector.fetch_youtube_analytics(25)
```

### Subprocess Mocking

```python
@patch("subprocess.run")
def test_ffmpeg_call(self, mock_run):
    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
    result = converter.convert(input_path)
    mock_run.assert_called_once()
```

## Fixture Patterns

### pytest Fixtures

Fixtures are defined at the top of each test file (file-local scope). Shared fixtures live in `tests/conftest.py`.

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

### Module-Level Sample Data

Complex dict structures are defined as module-level constants and reused across test classes:

```python
SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode Title",
    "episode_summary": "A great episode about testing.",
    "chapters": [{"start": 0, "title": "Intro"}],
    "social_captions": {"youtube": "YT caption", "twitter": "Tweet text"},
}
```

### Temporary Filesystem

Use `tmp_path` (pytest built-in) for filesystem isolation:

```python
def test_save_and_load(self, tmp_path):
    collector = AnalyticsCollector()
    collector.analytics_dir = tmp_path

    saved_path = collector.save_analytics(25, data)
    assert saved_path.exists()

    loaded = collector.load_analytics(25)
    assert loaded == data
```

## Common Test Patterns

### Testing the `enabled` Flag

```python
def test_init_disabled(self):
    """BLOG_ENABLED=false should set enabled=False."""
    with patch.dict("os.environ", {"BLOG_ENABLED": "false"}):
        gen = BlogPostGenerator()
        assert gen.enabled is False

def test_method_when_disabled(self, mock_post):
    """When disabled, returns False without making a request."""
    notifier = DiscordNotifier()  # no webhook = disabled
    result = notifier.send_notification("Title", "Desc")
    assert result is False
    mock_post.assert_not_called()
```

### Testing Exception Paths

```python
def test_fetch_failure_returns_none(self):
    """Returns None on API exception."""
    collector = AnalyticsCollector()
    with patch("builtins.open", side_effect=Exception("API error")):
        result = collector.fetch_youtube_analytics(25)
    assert result is None

def test_missing_credentials_raises(self):
    """Raises ValueError without credentials."""
    with pytest.raises(ValueError, match="credentials not configured"):
        TwitterUploader()
```

### Verifying Call Arguments

```python
call_kwargs = mock_post.call_args
payload = call_kwargs.kwargs["json"]
embed = payload["embeds"][0]
assert embed["title"] == "Test Title"
assert embed["color"] == 0x00FF00
```

### Floating Point Assertions

```python
assert delays[0] == pytest.approx(1.0)
```

## What to Mock vs. What to Test Real

**Always mock:**
- External API calls (YouTube, Twitter, Discord, Dropbox, OpenAI, Ollama)
- File I/O when testing pure logic
- `Path.mkdir`, `Path.exists` when testing code that creates directories
- `time.sleep` in retry tests
- `subprocess.run` for FFmpeg calls

**Use real implementations:**
- SQLite operations -- use `tmp_path` with a real database file
- File persistence round-trips -- use `tmp_path` for actual read/write
- Pure computation (engagement scores, string formatting, duration calculations)

## Adding Tests for New Features

1. Create `tests/test_{module}.py` matching the source module name
2. Group tests into classes: `Test<ClassName><Action>`
3. Add a one-line docstring to every test method
4. Mock all external dependencies
5. Test the `enabled` flag pattern if the module uses it
6. Test both success and failure paths
7. End the file with:
   ```python
   if __name__ == "__main__":
       pytest.main([__file__, "-v"])
   ```
