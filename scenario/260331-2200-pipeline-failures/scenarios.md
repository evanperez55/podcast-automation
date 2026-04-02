# Pipeline Failure Scenarios

**Date:** 2026-03-31
**Seed:** Podcast episode processing pipeline encounters failures at each stage
**Domain:** Software | **Depth:** Standard (25 iterations) | **Focus:** Failures

---

## Stage 1: Download / Ingest

### [ERROR_PATH] S01: Dropbox token expired mid-download

**Actors:** Pipeline, Dropbox API
**Precondition:** OAuth refresh token has expired (>6 months without use)
**Trigger:** `DropboxHandler.download_episode()` called
**Flow:**
1. Pipeline calls Dropbox API with refresh token
2. Dropbox returns 401 Unauthorized
3. `retry_with_backoff` retries 3 times — all fail
4. Exception propagates to `run()` which raises
**Expected outcome:** Pipeline fails with clear error message about expired credentials
**What could go wrong:** Generic "Failed to download" message without mentioning auth — user doesn't know to re-authenticate
**Severity:** HIGH

### [EDGE_CASE] S02: Audio file is 0 bytes (empty file in Dropbox)

**Actors:** Pipeline, Dropbox
**Precondition:** Someone uploaded an empty file to Dropbox
**Trigger:** Download succeeds but file is 0 bytes
**Flow:**
1. Download returns 0-byte file
2. Transcriber gets `audio_file` path
3. Whisper crashes or returns empty segments
**Expected outcome:** Pipeline should detect 0-byte file and fail early with clear message
**What could go wrong:** Whisper may hang or produce garbage output; downstream steps operate on empty data
**Severity:** MEDIUM

### [INTEGRATION] S03: RSS feed returns malformed XML

**Actors:** Pipeline, RSS feed source
**Precondition:** RSS feed endpoint returns invalid XML (CDN cache corruption)
**Trigger:** `RSSEpisodeFetcher.fetch_episode()` called
**Flow:**
1. HTTP GET returns 200 but body is truncated HTML
2. XML parser raises `xml.etree.ElementTree.ParseError`
**Expected outcome:** Pipeline catches parse error, logs it, fails with actionable message
**What could go wrong:** Uncaught exception with unhelpful traceback
**Severity:** MEDIUM

---

## Stage 2: Transcription

### [ERROR_PATH] S04: GPU out of memory during Whisper transcription

**Actors:** Pipeline, CUDA/GPU
**Precondition:** Another process using GPU memory, or episode is 3+ hours long
**Trigger:** `model.transcribe()` called
**Flow:**
1. Whisper begins processing
2. CUDA raises `torch.cuda.OutOfMemoryError` mid-transcription
3. Partial transcript data is lost
**Expected outcome:** Pipeline catches OOM, optionally retries with CPU fallback
**What could go wrong:** `torch.cuda.OutOfMemoryError` is not caught — pipeline crashes with CUDA stack trace; no CPU fallback exists
**Severity:** HIGH

### [EDGE_CASE] S05: Audio file is entirely silence (no speech)

**Actors:** Pipeline, Whisper
**Precondition:** Episode file is valid WAV but contains only silence (e.g., wrong track exported)
**Trigger:** Whisper processes silence
**Flow:**
1. Whisper's VAD filter detects no speech
2. Returns empty segments list and empty words list
3. `transcript_data = {"segments": [], "words": [], "duration": 3600}`
4. Analysis step receives empty transcript
**Expected outcome:** Pipeline should warn "No speech detected" and skip analysis
**What could go wrong:** ContentEditor sends empty text to OpenAI, burns API credits, returns hallucinated analysis; downstream clips have no content
**Severity:** MEDIUM

### [DATA_VARIATION] S06: Audio file is MP4 video (not audio-only)

**Actors:** Pipeline
**Precondition:** User provides an MP4 video file as input
**Trigger:** Whisper processes video file
**Flow:**
1. faster-whisper accepts MP4 (FFmpeg extracts audio internally)
2. Transcription succeeds on audio track
3. Pipeline treats it as audio-only — video track ignored
**Expected outcome:** Transcription works; video source detection should flag `has_video_source=True`
**What could go wrong:** If video source detection fails, clips are created as audio-only with static logo instead of cutting from source video
**Severity:** LOW

---

## Stage 3: Content Analysis

### [INTEGRATION] S07: OpenAI API rate limit during analysis

**Actors:** Pipeline, OpenAI API
**Precondition:** Account hitting rate limits (concurrent requests from other processes)
**Trigger:** `_call_openai_with_retry()` called
**Flow:**
1. First request returns 429 Rate Limit
2. Retry with exponential backoff (2s, 4s, 8s)
3. After 3 retries, still rate-limited
4. Exception raised
**Expected outcome:** Pipeline raises with clear "OpenAI rate limit exceeded after 3 retries" message
**What could go wrong:** Already handled by `_call_openai_with_retry` — but the delay (2+4+8=14s) may not be enough during heavy rate limiting. Max delay capped at 60s but only 3 retries.
**Severity:** MEDIUM

### [DATA_VARIATION] S08: Transcript contains only non-English speech

**Actors:** Pipeline, OpenAI
**Precondition:** Episode is in Spanish but prompts are English-only
**Trigger:** ContentEditor analyzes non-English transcript
**Flow:**
1. Whisper transcribes in detected language (Spanish)
2. English analysis prompt + Spanish transcript sent to GPT-4o
3. GPT-4o may return English analysis of Spanish content, or mixed-language results
**Expected outcome:** Analysis should work (GPT-4o is multilingual) but results may be lower quality
**What could go wrong:** Censor word lists (`NAMES_TO_REMOVE`, `WORDS_TO_REMOVE`) are English-only — names in other scripts won't be caught by direct search
**Severity:** LOW

---

## Stage 3.6: Compliance Check

### [ERROR_PATH] S09: OpenAI returns non-JSON compliance response

**Actors:** Pipeline, OpenAI API
**Precondition:** Model glitch or response truncation
**Trigger:** Compliance checker parses response
**Flow:**
1. GPT-4o returns response with markdown wrapping: ```json\n[...]\n```
2. `_parse_response()` attempts to extract JSON
3. Parse succeeds or fails depending on extraction logic
**Expected outcome:** Parser strips markdown and extracts JSON array
**What could go wrong:** If response is fully malformed, `json.loads` raises — is this caught?
**Severity:** MEDIUM

---

## Stage 4: Censorship

### [EDGE_CASE] S10: Censor timestamp extends past audio end

**Actors:** Pipeline, pydub
**Precondition:** GPT-4o hallucinates a timestamp beyond audio duration (e.g., 02:15:00 in a 1-hour episode)
**Trigger:** `apply_censorship()` processes the timestamp
**Flow:**
1. `start_ms = 8100000` (2h15m), audio length = 3600000 (1h)
2. `end_ms = min(end_ms, len(audio))` → clamps to audio end
3. `start_ms > end_ms` → invalid range
**Expected outcome:** Skip this censor point or handle gracefully
**What could go wrong:** `_apply_duck_segment(audio, 8100000, 3600000)` receives start > end — behavior undefined
**Severity:** MEDIUM

### [EDGE_CASE] S11: Hundreds of censor timestamps (performance)

**Actors:** Pipeline, pydub
**Precondition:** Highly profane episode or GPT-4o over-flags content
**Trigger:** `apply_censorship()` with 200+ timestamps
**Flow:**
1. Loop processes 200 censor points
2. Each iteration creates a new AudioSegment slice
3. Memory usage grows as pydub copies audio segments
**Expected outcome:** Completes, possibly slowly
**What could go wrong:** O(n) pydub operations on a 2-hour WAV file could take 30+ minutes and use excessive memory; no progress indication for user
**Severity:** LOW

---

## Stage 4.5: Normalization

### [ERROR_PATH] S12: FFmpeg normalization pass 1 returns invalid JSON

**Actors:** Pipeline, FFmpeg
**Precondition:** FFmpeg version mismatch or corrupt audio
**Trigger:** `normalize_audio()` pass 1 runs
**Flow:**
1. FFmpeg runs loudnorm measurement
2. stderr output is not valid JSON (FFmpeg warning messages mixed in)
3. `_parse_loudnorm_json()` fails to find JSON block
**Expected outcome:** Raises RuntimeError with clear message
**What could go wrong:** Already handled — `_parse_loudnorm_json` raises RuntimeError. But the error message may not indicate which audio file caused the problem.
**Severity:** LOW

---

## Stage 5: Clip Creation

### [EDGE_CASE] S13: best_clips has clip with start > end (inverted range)

**Actors:** Pipeline, AudioProcessor
**Precondition:** GPT-4o returns clip with start_seconds > end_seconds
**Trigger:** `create_clips()` called
**Flow:**
1. Clip info: `{start_seconds: 500, end_seconds: 300}`
2. `extract_clip()` is called with inverted range
3. pydub slicing with `audio[start_ms:end_ms]` where start > end → empty segment
**Expected outcome:** Should detect and skip invalid clips
**What could go wrong:** Empty AudioSegment is saved as a 0-byte or minimal WAV — downstream video conversion creates blank videos uploaded to YouTube
**Severity:** HIGH

### [EDGE_CASE] S14: All clips are shorter than minimum duration

**Actors:** Pipeline, AudioProcessor
**Precondition:** GPT-4o identifies clips that are all under `CLIP_MIN_DURATION` threshold
**Trigger:** `create_clips()` filters clips
**Flow:**
1. 5 clips identified, all are 3-5 seconds (min is 15s)
2. All filtered out by minimum duration check
3. `clip_paths = []`
4. Downstream: no videos created, no social media uploads
**Expected outcome:** Pipeline completes but with "0 clips" warning
**What could go wrong:** Some platforms may fail if they expect at least one clip; empty list handling may not be tested in all downstream paths
**Severity:** LOW

---

## Stage 5.5: Video Conversion

### [ERROR_PATH] S15: NVENC encoder not available (GPU driver mismatch)

**Actors:** Pipeline, FFmpeg, NVIDIA GPU
**Precondition:** NVIDIA driver updated but NVENC library version mismatch
**Trigger:** FFmpeg with `-c:v h264_nvenc` fails
**Flow:**
1. `get_h264_encoder_args()` returns NVENC args
2. FFmpeg subprocess fails with "Cannot load nvcuda.dll"
3. returncode != 0
**Expected outcome:** Falls back to libx264 software encoding
**What could go wrong:** If no fallback exists, all video creation fails — clips and full episode video are None
**Severity:** HIGH

### [CONCURRENT] S16: Multiple NVENC sessions exceed GPU limit

**Actors:** Pipeline, ThreadPoolExecutor, NVENC
**Precondition:** `MAX_NVENC_SESSIONS` set to 4, but GPU supports only 2
**Trigger:** ThreadPoolExecutor submits 4 FFmpeg encoding tasks
**Flow:**
1. First 2 tasks start encoding successfully
2. Task 3 and 4 fail with "NVENC session limit reached"
3. futures return None for failed tasks
**Expected outcome:** 2/4 clips created, pipeline continues
**What could go wrong:** If `MAX_NVENC_SESSIONS` config doesn't match hardware, some clips are silently lost
**Severity:** MEDIUM

---

## Stage 7: Dropbox Upload

### [INTEGRATION] S17: Dropbox upload fails after censored audio but before clips

**Actors:** Pipeline, Dropbox
**Precondition:** Network drops mid-upload sequence
**Trigger:** `upload_finished_episode()` succeeds, `upload_clips()` fails
**Flow:**
1. MP3 uploaded to finished folder ✓
2. Network drops
3. Clip uploads fail — empty `uploaded_clip_paths`
4. Pipeline continues to RSS feed update with finished path
**Expected outcome:** RSS feed updated with episode, clips missing from Dropbox
**What could go wrong:** RSS feed references episode but clips aren't available; `--resume` can't retry just the clip upload (checkpoint says "dropbox" complete)
**Severity:** MEDIUM

### [RECOVERY] S18: Resume after crash during video conversion

**Actors:** Pipeline, PipelineState
**Precondition:** Pipeline crashed during video conversion (e.g., power failure)
**Trigger:** `--resume` flag used on re-run
**Flow:**
1. State file shows transcribe, analysis, censor, normalize completed
2. create_clips not in state → clips re-created
3. subtitles not in state → re-generated
4. convert_videos not in state → re-encoded
**Expected outcome:** Skips completed steps, resumes from clip creation
**What could go wrong:** Partially written video files from crash may confuse re-run (file exists but is truncated/corrupt); FFmpeg will overwrite with `-y` flag, so this should be OK
**Severity:** LOW

---

## Stage 8: Social Media Upload

### [INTEGRATION] S19: YouTube upload succeeds but returns no video_id

**Actors:** Pipeline, YouTube API
**Precondition:** YouTube API response missing expected fields
**Trigger:** `upload_episode()` returns result without `video_id`
**Flow:**
1. Upload completes
2. Result dict doesn't contain `video_id` key
3. `platform_ids["youtube"] = full_ep.get("video_id")` → None
4. platform_ids.json saved with `{"youtube": null}`
5. Analytics later can't find the video
**Expected outcome:** Should warn that video_id was not returned
**What could go wrong:** Silent None stored — analytics lookups fail silently, engagement history has no YouTube data
**Severity:** MEDIUM

### [TEMPORAL] S20: Scheduled upload time is in the past

**Actors:** Pipeline, UploadScheduler
**Precondition:** Long processing time (3+ hours) makes the calculated `publish_at` in the past by the time upload runs
**Trigger:** `run_upload_scheduled()` checks pending uploads
**Flow:**
1. Schedule created at 2pm with publish_at = 5pm
2. Pipeline takes 4 hours, finishes at 6pm
3. Upload runs with publish_at = 5pm (past)
4. YouTube may reject or immediately publish
**Expected outcome:** YouTube API accepts past publish_at and publishes immediately
**What could go wrong:** YouTube API may return error for past dates; no retry logic for this case
**Severity:** LOW

### [INTEGRATION] S21: Twitter API credentials revoked mid-upload

**Actors:** Pipeline, Twitter/X API
**Precondition:** API key revoked by Twitter (policy change, billing issue)
**Trigger:** `post_episode_announcement()` called
**Flow:**
1. API call returns 401 Forbidden
2. Exception caught in `_upload_twitter`
3. Returns `{"error": "401 Forbidden"}`
4. Pipeline continues without Twitter
**Expected outcome:** Pipeline completes, Twitter upload skipped with warning
**What could go wrong:** Already handled — but error dict stored in results doesn't trigger any alerting or notification
**Severity:** LOW

---

## Stage 8.5: Blog Post

### [ERROR_PATH] S22: OpenAI returns truncated blog post (max_tokens hit)

**Actors:** Pipeline, OpenAI API
**Precondition:** Very long episode with detailed transcript
**Trigger:** `generate_blog_post()` hits max_tokens limit
**Flow:**
1. GPT-4o starts generating markdown
2. Hits token limit mid-sentence
3. Returns truncated markdown
**Expected outcome:** Blog post saved but incomplete
**What could go wrong:** Truncated markdown may have unclosed tags, broken links; no validation of completeness
**Severity:** LOW

---

## Stage 9: Search Index

### [EDGE_CASE] S23: SQLite database locked by another process

**Actors:** Pipeline, SQLite
**Precondition:** Another instance of the pipeline running analytics on the same DB
**Trigger:** `index_episode()` called
**Flow:**
1. SQLite tries to acquire write lock
2. Another process holds the lock
3. Default timeout (5s) exceeded
4. `sqlite3.OperationalError: database is locked`
**Expected outcome:** Error caught, pipeline continues without indexing
**What could go wrong:** Already caught by `try/except Exception` in `run_distribute` — but no retry logic, episode permanently missing from search index
**Severity:** LOW

---

## Cross-Cutting Concerns

### [RECOVERY] S24: Disk full during WAV censorship output

**Actors:** Pipeline, filesystem
**Precondition:** Disk space exhausted (long episode + many clips)
**Trigger:** pydub `export()` writing censored WAV
**Flow:**
1. `audio.export(str(output_path), format="wav")` starts writing
2. Disk fills up mid-write
3. pydub raises `OSError: [Errno 28] No space left on device`
4. Partial WAV file left on disk
**Expected outcome:** Pipeline should catch and report disk space issue clearly
**What could go wrong:** Exception propagates up as generic error; partial file left on disk wastes remaining space; `--resume` finds partial file and treats it as complete
**Severity:** HIGH

### [STATE_TRANSITION] S25: Pipeline state file corrupted between runs

**Actors:** Pipeline, PipelineState
**Precondition:** State JSON manually edited or binary-corrupted
**Trigger:** `--resume` loads corrupt state
**Flow:**
1. `_load()` reads state file
2. `json.load()` raises `JSONDecodeError`
3. Caught by existing handler → starts fresh state
4. All steps re-run from scratch
**Expected outcome:** Fresh start with warning message
**What could go wrong:** Already handled — `_load()` catches `JSONDecodeError` and starts fresh. But the corrupt file is not backed up, so debugging why it corrupted is impossible.
**Severity:** LOW
