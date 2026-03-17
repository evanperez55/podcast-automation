# Codebase Concerns

**Analysis Date:** 2026-03-16

## Tech Debt

**OpenAI `openai` Package Missing from requirements.txt:**
- Issue: `content_editor.py` and `blog_generator.py` both `import openai` and call `openai.OpenAI(api_key=...)` but `requirements.txt` only lists `openai-whisper==20231117` (the Whisper CLI tool), not the `openai` Python SDK package.
- Files: `content_editor.py:3`, `blog_generator.py:48`, `requirements.txt`
- Impact: Fresh installs will silently fail at runtime when content analysis or blog generation runs. `pip install -r requirements.txt` does not install the `openai` SDK.
- Fix approach: Add `openai>=1.0.0` to `requirements.txt`. Alternatively commit to fully removing OpenAI and routing all LLM calls through `ollama_client.py`.

**Google Docs Topic Tracker Disabled with TODO:**
- Issue: `self.topic_tracker = None` with comment `# TODO: Re-enable after fixing Google OAuth credentials` at `main.py:106-107`. The tracker has a full implementation in `google_docs_tracker.py` and credentials exist on disk (`google_docs_credentials.json`, `google_docs_token.json`) but OAuth is broken.
- Files: `main.py:105-108`, `google_docs_tracker.py`
- Impact: Topic tracking is silently skipped every run. No test coverage for `google_docs_tracker.py`.
- Fix approach: Debug Google OAuth token refresh. If the flow is permanently broken, remove `google_docs_tracker.py` and the import at `main.py:16`.

**Scheduled Upload Execution is a Stub:**
- Issue: `_run_upload_scheduled()` in `main.py:1559-1606` scans for pending uploads but logs `[TODO] %s upload not yet automated in scheduled mode` instead of performing the upload. The schedule is then marked as "uploaded" with a placeholder.
- Files: `main.py:1593-1600`
- Impact: Running `python main.py upload-scheduled` silently marks all pending uploads as done without actually uploading them. Data is lost.
- Fix approach: Wire the platform uploaders (`YouTubeUploader`, `TwitterUploader`, etc.) into `_run_upload_scheduled()` using the file paths stored in the schedule JSON.

**Instagram Upload Not Implemented in Main Pipeline:**
- Issue: `_upload_instagram()` in `main.py:389-419` only logs that videos are ready and instructs to upload manually. It never calls `InstagramUploader.upload_reel()`.
- Files: `main.py:389-419`
- Impact: Instagram Reels are never automatically posted regardless of credentials.
- Fix approach: Require a Dropbox public link step before the Instagram upload, then call `self.uploaders["instagram"].upload_reel(video_url=public_url, caption=caption)`.

**dBFS Used as LUFS Proxy:**
- Issue: `audio_processor.py:normalize_audio()` applies gain based on `Config.LUFS_TARGET` (default `-16`) but uses pydub's `audio.dBFS` (average RMS power) rather than true integrated LUFS (ITU-R BS.1770). The config variable name implies podcast-standard loudness normalization but the implementation is a simpler approximation.
- Files: `audio_processor.py:47-86`, `config.py:179`
- Impact: Output loudness will be inconsistent across episodes with different dynamic range. Platforms that enforce LUFS targets (Spotify, Apple Podcasts) may apply additional normalization.
- Fix approach: Use `ffmpeg-loudnorm` filter (already available via FFmpeg) for true integrated LUFS normalization.

**`_parse_claude_response` Misnaming:**
- Issue: `content_editor.py` uses OpenAI GPT-4o as the LLM but the internal parsing method is named `_parse_claude_response` (line 61, 263). This is a naming artifact from a prior migration away from Claude/Anthropic.
- Files: `content_editor.py:61`, `content_editor.py:263`
- Impact: Minor confusion only — no functional impact.
- Fix approach: Rename to `_parse_llm_response`.

**Duplicate Config Reads in `scheduler.py`:**
- Issue: `UploadScheduler.__init__()` reads delay values directly from `os.getenv()` instead of using `Config.SCHEDULE_*_DELAY_HOURS` attributes that already exist in `config.py`.
- Files: `scheduler.py:17-20`, `config.py:87-92`
- Impact: Two sources of truth for the same values. Changes to `Config` class won't affect `UploadScheduler`.
- Fix approach: Replace `os.getenv(...)` calls in `scheduler.py` with `Config.SCHEDULE_YOUTUBE_DELAY_HOURS` etc.

**`re` Module Imported Inline and Aliased:**
- Issue: `main.py` imports `re` three times inline at different function scopes (lines 1624, 1631, 1732), two of which use `import re as _re` with an underscore alias to avoid linting warnings.
- Files: `main.py:1624`, `main.py:1631`, `main.py:1732`
- Impact: Minor style inconsistency, signals incomplete refactoring.
- Fix approach: Add `import re` at the top of `main.py` alongside other module imports.

---

## Known Bugs

**`Config.validate()` Requires `OPENAI_API_KEY` But Primary LLM is Ollama:**
- Symptoms: `main.py` calls `Config.validate()` (line 85) which raises `ValueError` if `OPENAI_API_KEY` is not set. However the CLAUDE.md notes "requirements.txt comments out anthropic (replaced by Ollama) but config.py still references OPENAI_API_KEY", and `content_editor.py` calls OpenAI directly.
- Files: `config.py:211-219`, `content_editor.py:14`
- Trigger: Running `python main.py latest` without `OPENAI_API_KEY` set.
- Workaround: Set a dummy `OPENAI_API_KEY` in `.env`. The actual key is required for `content_editor.py` to function.

**Twitter URL Length Calculation Off for `post_clip()`:**
- Symptoms: In `twitter_uploader.py:post_clip()`, suffix length is calculated as `len(suffix) - len(youtube_url) + 23` (line 313) but `suffix` at that point includes the URL already embedded via f-string at line 311. The URL appears in `suffix` and is subtracted then re-added as the t.co length — this arithmetic is correct only if `youtube_url` appears exactly once in `suffix`, which it does. However if `youtube_url` is `None`, `suffix_display_len = len(suffix)` (line 315) counts the literal `youtube_url` variable characters, not the URL — but `youtube_url` is `None` so the suffix won't contain it. Logic is fragile and hard to follow.
- Files: `uploaders/twitter_uploader.py:309-318`
- Trigger: Any `post_clip()` call.
- Workaround: Current behavior may work but is error-prone on edge cases.

---

## Security Considerations

**Google Credentials Files in Project Root:**
- Risk: `google_docs_credentials.json` and `google_docs_token.json` exist at the project root as untracked files (confirmed via `git ls-files`). They are covered by `*.json` in `.gitignore`, but their location adjacent to committed files creates accidental commit risk.
- Files: `google_docs_credentials.json`, `google_docs_token.json`
- Current mitigation: `.gitignore` blocks `*.json` (except `requirements.json`, `package.json`).
- Recommendations: Move to `credentials/` directory alongside `youtube_credentials.json` and `youtube_token.pickle` which are already there and gitignored via `credentials/`.

**YouTube Token Stored as Pickle:**
- Risk: `credentials/youtube_token.pickle` uses Python's `pickle` format. Pickle files are executable code; a tampered pickle file can achieve arbitrary code execution when loaded.
- Files: `analytics.py:44-50`, `credentials/youtube_token.pickle`
- Current mitigation: File is gitignored via `credentials/`. Only local threat.
- Recommendations: Migrate to JSON-based token storage (Google's `google.oauth2.credentials.Credentials.to_json()`) or use the standard `google_auth_oauthlib` token file.

**TikTok Access Token Stored in `.env` Without Expiry Handling:**
- Risk: TikTok access tokens expire (typically 24h or per OAuth flow). `tiktok_uploader.py` uses the token directly from `Config.TIKTOK_ACCESS_TOKEN` with no refresh mechanism. An expired token will cause silent upload failures.
- Files: `uploaders/tiktok_uploader.py:21`, `config.py:78`
- Current mitigation: Fails gracefully with error logging.
- Recommendations: Add OAuth refresh flow or document re-auth requirement.

**`NAMES_TO_REMOVE` Contains Real Full Names Hardcoded:**
- Risk: `config.py:125-138` contains the full legal names of podcast hosts (`Evan Perez`, `Joey Gross`, `Dominique Karolczak`) committed in plain text.
- Files: `config.py:125-138`
- Current mitigation: This is a podcast automation tool so hosts' names are expected to be known. Low risk in context.
- Recommendations: If this repo is ever made public, move names to `.env` to avoid PII in version history.

---

## Performance Bottlenecks

**TikTok Upload Reads Entire Video into RAM:**
- Problem: `tiktok_uploader._upload_video_file()` reads the entire video file into memory with `video_file.read()` (line 211) then sends it in a single `requests.put()`.
- Files: `uploaders/tiktok_uploader.py:207-226`
- Cause: No streaming or chunked upload; large video files (4GB max per TikTok) will exhaust available RAM.
- Improvement path: Use `requests` with a generator or `files` parameter for streaming, or split into the chunk-size segments already calculated in `_initialize_upload()`.

**Whisper Model Loaded Once at Init, All Episodes in Same Process:**
- Problem: `Transcriber.__init__()` loads the Whisper model into GPU/CPU memory at startup. The `WHISPER_MODEL` default is `"base"` (config.py:177), but for production quality the large model requires ~10GB VRAM. No memory cleanup between episodes.
- Files: `transcription.py:15-43`, `config.py:177`
- Cause: Design choice for pipeline efficiency, but `diarize.py` uses `large-v2` via WhisperX separately (not the same model instance).
- Improvement path: Accept as-is for single-episode pipeline. For batch processing, add explicit model unloading between runs.

**Analytics YouTube Search API Called Per Episode Number:**
- Problem: `analytics.py:fetch_youtube_analytics()` uses YouTube Data API `search.list` to find videos by episode number pattern. Search API has a 100-unit daily quota cost vs. 1 unit for `videos.list`. Running analytics for all episodes hits this quickly.
- Files: `analytics.py:58-68`
- Cause: No stored mapping of episode number to YouTube video ID.
- Improvement path: Store `video_id` in the upload result and persist it to `output/ep_N/upload_results.json`. Use the stored ID for analytics instead of search.

---

## Fragile Areas

**`main.py` at 1,802 Lines — High Coupling:**
- Files: `main.py`
- Why fragile: The entire pipeline orchestration, all CLI argument parsing, upload coordination, dry-run logic, and analytics/search commands live in one file. `PodcastAutomation.__init__()` initializes 12+ components. Adding a new platform or pipeline step requires touching this file.
- Safe modification: Changes to `_upload_twitter()`, `_upload_youtube()` etc. are relatively isolated. Avoid changing `process_episode()` (line ~1400+) without tracing all callers.
- Test coverage: No `tests/test_main.py` exists.

**`continue_episode.py` Duplicates Pipeline Logic:**
- Files: `continue_episode.py`
- Why fragile: A 525-line standalone script that re-implements upload, conversion, and RSS steps outside of `main.py`'s `PodcastAutomation` class. It duplicates credential initialization, platform uploader construction, and error handling. Changes to any uploader interface require updating both files.
- Safe modification: Treat as a one-off script; do not rely on it staying in sync with `main.py`.
- Test coverage: No `tests/test_continue_episode.py` exists.

**Topic Engine Modules Have No Test Coverage:**
- Files: `topic_curator.py`, `topic_scraper.py`, `topic_scorer.py`, `track_episode_topics.py`, `notion_integration.py`
- Why fragile: These modules make external API calls to Notion and Reddit (PRAW). No tests verify their behavior under API errors, rate limits, or changed API schemas.
- Safe modification: Wrap all Notion API calls with the existing `retry_utils.py` decorator. Add `--dry-run` checks before writing to Notion.
- Test coverage: None.

**RSS Feed Generated with String Concatenation in `spotify_uploader.py`:**
- Files: `uploaders/spotify_uploader.py:69-81`
- Why fragile: `generate_rss_item()` builds XML via f-string concatenation rather than using `xml.etree.ElementTree` (which `rss_feed_generator.py` uses correctly). Special characters in `title` or `description` will break feed validity.
- Safe modification: Only call `generate_rss_item()` with sanitized/escaped strings.
- Test coverage: `tests/test_spotify_uploader.py` exists but may not test XML escaping edge cases.

**`TikTokUploader` Uses `print()` Instead of `logger`:**
- Files: `uploaders/tiktok_uploader.py` (24 print statements, 0 logger calls)
- Why fragile: All TikTok status/error output bypasses the centralized logger. Messages go to stdout only and are not written to `output/podcast_automation.log`. Debugging TikTok upload failures requires watching the terminal.
- Safe modification: Non-breaking to leave as-is, but replace `print(...)` with `logger.info(...)` / `logger.error(...)` for consistency.
- Test coverage: `tests/test_tiktok_uploader.py` exists.

---

## Scaling Limits

**Scheduler Does Not Execute Uploads:**
- Current capacity: The scheduler stores schedule JSON files and tracks pending uploads. It does not run any background process or cron job.
- Limit: Scheduled delays are purely informational. The `upload-scheduled` command marks them as complete with a placeholder rather than uploading.
- Scaling path: Implement the upload logic in `_run_upload_scheduled()` using the stored platform uploaders, then set up a cron/Task Scheduler job to run `python main.py upload-scheduled` periodically.

---

## Dependencies at Risk

**`whisperx==3.1.6` Pinned with Tight `torch==2.1.0`:**
- Risk: WhisperX 3.1.6 pins to PyTorch 2.1.0. Newer CUDA drivers and GPU architectures may require newer PyTorch. The combination is over 2 years old.
- Impact: GPU acceleration may degrade or fail on newer NVIDIA hardware.
- Files: `requirements.txt:9-11`
- Migration plan: Test with `whisperx>=3.2.0` and latest PyTorch stable when upgrading hardware.

**`openai-whisper==20231117` vs `openai` SDK:**
- Risk: The repo uses `openai-whisper` (Whisper transcription CLI/library) for transcription and separately requires the `openai` Python SDK (GPT-4o) for content analysis, but the SDK is not listed in `requirements.txt`.
- Files: `requirements.txt:8`, `content_editor.py:3`
- Migration plan: Add `openai>=1.0.0` to `requirements.txt` immediately, or migrate `content_editor.py` to use `ollama_client.py`.

**Instagram Graph API Version Pinned to `v18.0`:**
- Risk: `InstagramUploader.API_BASE = "https://graph.facebook.com/v18.0"` (line 16). Meta deprecates Graph API versions ~2 years after release; v18.0 was released September 2023.
- Impact: Instagram uploads will fail when Meta retires v18.0.
- Files: `uploaders/instagram_uploader.py:16`
- Migration plan: Update to latest stable version (currently v21.0+). Make the version configurable via env var.

---

## Missing Critical Features

**No End-to-End Test for the Full Pipeline:**
- Problem: `tests/` contains 20 unit test files covering individual modules, but there is no integration test that runs the full `process_episode()` pipeline with mocked external calls.
- Blocks: Confidence when making cross-cutting changes (e.g., changing the `analysis` dict schema propagates across content_editor, clips, blog, thumbnails, YouTube, Twitter, RSS).
- Files: `main.py:process_episode()` (no corresponding test file)

**No Tests for Core Pipeline Modules:**
- Problem: `main.py`, `dropbox_handler.py`, `transcription.py`, `rss_feed_generator.py`, `ollama_client.py`, `diarize.py`, `content_editor.py` (full analysis flow), and `google_docs_tracker.py` all lack test files.
- Files: all listed above
- Risk: Regressions in download, transcription, or upload steps are not caught automatically.
- Priority: High for `dropbox_handler.py`, `content_editor.py`, `rss_feed_generator.py`

---

## Test Coverage Gaps

**Core Pipeline Has No Tests:**
- What's not tested: `main.py` orchestration, `dropbox_handler.py` download/upload, `transcription.py` Whisper wrapping, `rss_feed_generator.py` feed generation and parsing, `ollama_client.py` HTTP client.
- Files: `main.py`, `dropbox_handler.py`, `transcription.py`, `rss_feed_generator.py`, `ollama_client.py`
- Risk: Silent regressions in the primary episode processing flow.
- Priority: High

**Topic Engine Entirely Untested:**
- What's not tested: `topic_curator.py`, `topic_scraper.py`, `topic_scorer.py`, `notion_integration.py`, `track_episode_topics.py`, `match_topics_keywords.py`, `match_topics_to_episodes.py`
- Files: all listed above
- Risk: Notion API calls can corrupt the topic backlog silently. Topic scoring formula changes have no guard.
- Priority: Medium

**Ad-hoc Scripts with No Tests:**
- What's not tested: `continue_episode.py`, `repost_twitter.py`, `populate_rss_feed.py`, `organize_output.py`, `process_historical_episodes.py` (has test but limited coverage)
- Files: all listed above
- Risk: These scripts run against production data. Bugs could corrupt output or send duplicate uploads.
- Priority: Low (scripts are one-off by design, but `repost_twitter.py` especially could cause duplicate posts)

---

*Concerns audit: 2026-03-16*
