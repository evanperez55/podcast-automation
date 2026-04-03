# Swarm Prediction Findings

**Commit:** 4f37d8b
**Personas:** Reliability Engineer, Performance Engineer, Devil's Advocate
**Depth:** Shallow (3 personas, 1 round)
**Goal:** Find reliability and performance issues

---

## Reliability Engineer Findings

### RE-1: Pydub loads entire audio file into memory
- **Location:** `audio_processor.py:420-430` (create_clips), `compilation_generator.py:201`
- **Severity:** HIGH
- **Confidence:** HIGH
- **Evidence:** `AudioSegment.from_file()` loads the entire WAV into memory. A 1-hour episode at 44.1kHz stereo 16-bit = ~635MB. A 3-hour episode = ~1.9GB. With pydub's internal representation overhead, this can easily hit 4-6GB RAM.
- **Recommendation:** For clip extraction, use FFmpeg subprocess directly (already used elsewhere) instead of pydub to avoid loading the full file. FFmpeg can seek to clip start without reading the entire file.

### RE-2: ContentEditor._call_openai_with_retry catches broad Exception
- **Location:** `content_editor.py:238-290`
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Evidence:** The retry loop catches `Exception` broadly, including `KeyboardInterrupt` and `SystemExit` which should propagate. It also retries on non-transient errors (e.g., `InvalidRequestError` for too-long prompts) wasting 3 retry attempts.
- **Recommendation:** Catch `openai.APIError` specifically for retries, let other exceptions propagate.

### RE-3: No timeout on OpenAI API calls
- **Location:** `content_editor.py:260-270`
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Evidence:** `client.chat.completions.create()` is called without a `timeout` parameter. If OpenAI is slow/hanging, the pipeline blocks indefinitely. FFmpeg calls all have timeouts, but the OpenAI call doesn't.
- **Recommendation:** Add `timeout=300` to the OpenAI API call.

### RE-4: Dropbox download doesn't clean up partial files on failure
- **Location:** `dropbox_handler.py:112-127`
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Evidence:** If the download fails mid-stream (network error), the partial file at `local_path` remains on disk. A subsequent `--resume` run might find this file and skip re-download, processing a truncated audio file. The new size check warns but doesn't delete.
- **Recommendation:** Add `try/except` around download loop with `Path(local_path).unlink(missing_ok=True)` in the except block.

### RE-5: Pipeline lock doesn't handle Windows PID reuse
- **Location:** `pipeline/runner.py` (_acquire_pipeline_lock)
- **Severity:** LOW
- **Confidence:** MEDIUM
- **Evidence:** On Windows, PIDs are aggressively reused. `os.kill(old_pid, 0)` succeeds if any process has that PID — not necessarily the pipeline. Could incorrectly block a legitimate new run.
- **Recommendation:** Store PID + timestamp in lock file, treat locks >2 hours old as stale regardless of PID.

---

## Performance Engineer Findings

### PE-1: Full-episode video creation blocks for hours with no progress indication
- **Location:** `video_converter.py:116-121`
- **Severity:** MEDIUM
- **Confidence:** HIGH
- **Evidence:** `subprocess.run()` with `timeout=7200` (2 hours) blocks the main thread. No progress output, no way to tell if it's working or hung. User sees nothing for potentially hours.
- **Recommendation:** Use `subprocess.Popen` with periodic stderr reading to show FFmpeg progress (frame count, time encoded).

### PE-2: RSS feed generator re-parses and rewrites entire XML on every episode
- **Location:** `rss_feed_generator.py:100-150`
- **Severity:** LOW
- **Confidence:** HIGH
- **Evidence:** `add_episode_to_feed()` reads the entire XML, parses it, appends one item, serializes the whole tree back to disk. For 100+ episodes, this grows linearly. Not a problem yet at 30 episodes, but architecturally inefficient.
- **Recommendation:** No action needed at current scale. Monitor as episode count grows past 100.

### PE-3: Thumbnail generator loads logo from disk on every call
- **Location:** `thumbnail_generator.py:66-70`
- **Severity:** LOW
- **Confidence:** HIGH
- **Evidence:** `_create_background()` calls `Image.open(logo_path)` and `resize()` for every thumbnail. During batch operations (8 clips per episode), the same logo is loaded and resized 8+ times.
- **Recommendation:** Cache the resized logo as an instance attribute after first load.

### PE-4: SubtitleClipGenerator creates FFmpeg commands serially then parallelizes
- **Location:** `subtitle_clip_generator.py:443-470`
- **Severity:** LOW
- **Confidence:** MEDIUM
- **Evidence:** The ThreadPoolExecutor parallelizes FFmpeg execution, but command building (which includes SRT file I/O and path computation) is done inside the thread function. This is fine — the actual bottleneck is FFmpeg encoding, not command building.
- **Recommendation:** No action needed — current approach is correct.

---

## Devil's Advocate Findings

### DA-1: Challenge to RE-1 (pydub memory) — Is this actually a problem?
- **Position:** Partially agree
- **Counter-evidence:** The pipeline runs on a machine with an RTX 3070, which implies at least 16GB RAM. A 1.9GB audio file in memory is fine. However, WhisperX also loads a GPU model (~4GB VRAM + 2GB RAM), and FFmpeg processes run concurrently. Combined memory pressure could be an issue.
- **Revised position:** MEDIUM severity, not HIGH. Only a problem for 3+ hour episodes.

### DA-2: Challenge to RE-3 (no OpenAI timeout) — Non-code hypothesis
- **Position:** Agree with finding, but propose additional cause
- **Counter-evidence:** The `openai` Python SDK has a default timeout of 600 seconds (10 minutes). So there IS a timeout — it's just implicit and very long. The real issue isn't no timeout — it's that a 10-minute hang gives no user feedback.
- **Revised position:** The timeout exists at SDK level. The UX issue (no feedback during long waits) is more impactful than the reliability issue.

### DA-3: The real reliability risk isn't in the code — it's in the credentials
- **Position:** New finding
- **Severity:** HIGH
- **Confidence:** HIGH
- **Evidence:** YouTube token at `credentials/youtube_token.pickle` expires and requires interactive re-auth. Twitter pay-per-use credits can run out silently. Bluesky app passwords can be revoked. None of these have health checks or alerting. The pipeline operator (user) has no automated way to know when a credential stops working until posts fail.
- **Recommendation:** Add a `--health-check` CLI command that validates all configured credentials and reports their status.

### DA-4: Challenge to PE-3 (logo caching) — Premature optimization
- **Position:** Disagree
- **Counter-evidence:** Loading a 1MB PNG and resizing it takes <50ms. For 8 thumbnails, that's 400ms total — unnoticeable in a pipeline that runs for 30+ minutes. This is textbook premature optimization.
- **Revised position:** PE-3 should be LOW/SKIP — not worth the code complexity of caching.
