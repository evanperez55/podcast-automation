# Edge Cases & Failure Modes — Prioritized by Actionability

## Immediately Actionable (code changes needed)

### HIGH: S04 — GPU OOM has no CPU fallback
- **Location:** `transcription.py:85-90`
- **Issue:** `torch.cuda.OutOfMemoryError` is not caught; no fallback to CPU
- **Fix:** Wrap `model.transcribe()` in try/except for OOM, retry with CPU device
- **Test:** Mock OOM error, verify CPU fallback is attempted

### HIGH: S13 — Inverted clip ranges produce empty clips
- **Location:** `audio_processor.py:266-268`
- **Issue:** `start_seconds > end_seconds` produces empty AudioSegment, saved as valid file
- **Fix:** Add `if start_seconds >= end_seconds: logger.warning(...); continue`
- **Test:** Pass clip with start > end, verify it's skipped

### HIGH: S15 — No NVENC fallback to libx264
- **Location:** `config.py` `get_h264_encoder_args()`
- **Issue:** If NVENC is unavailable, all video creation fails
- **Fix:** Catch NVENC failure in first video conversion, switch to libx264 for remaining
- **Test:** Mock FFmpeg NVENC failure, verify libx264 fallback

### HIGH: S24 — Disk full leaves partial files, breaks resume
- **Location:** `audio_processor.py:300-310`
- **Issue:** Partial WAV on disk after `OSError: No space left`; `--resume` may find it and skip re-processing
- **Fix:** Write to temp file then rename (same atomic pattern as pipeline_state.py fix)
- **Test:** Mock disk full during export, verify no partial file remains

### MEDIUM: S10 — Censor timestamp past audio end
- **Location:** `audio_processor.py:280-287`
- **Issue:** `start_ms` could exceed `len(audio)` after `end_ms` clamp, making `start > end`
- **Fix:** Add `if start_ms >= end_ms: continue` check after clamping
- **Test:** Pass timestamp 2x audio length, verify it's skipped gracefully

### MEDIUM: S16 — NVENC session limit mismatch
- **Location:** `config.py` `MAX_NVENC_SESSIONS`, `pipeline/steps/video.py:191`
- **Issue:** Config default may exceed GPU hardware limit
- **Fix:** Auto-detect available NVENC sessions or catch session limit error per-clip
- **Test:** Set MAX_NVENC_SESSIONS > hardware, verify graceful degradation

## Worth Monitoring (existing handling may be sufficient)

### MEDIUM: S02 — 0-byte audio file
- **Current:** Whisper will likely fail with decode error
- **Improvement:** Add file size check in `run_ingest` before proceeding

### MEDIUM: S07 — OpenAI rate limit retry window too short
- **Current:** 3 retries with 2+4+8=14s max
- **Improvement:** Increase to 5 retries or implement adaptive backoff

### MEDIUM: S09 — Compliance response parsing
- **Current:** `_parse_response` may not handle all malformed responses
- **Improvement:** Add explicit JSON extraction with fallback

### MEDIUM: S17 — Partial upload can't resume clips only
- **Current:** Checkpoint marks "dropbox" as complete after any upload
- **Improvement:** Split checkpoint into "dropbox_mp3" and "dropbox_clips"

### MEDIUM: S19 — YouTube upload returns no video_id
- **Current:** Stores None silently
- **Improvement:** Log warning when video_id is missing from upload result

## Low Priority / Already Handled

- S01: Dropbox auth — handled by retry_with_backoff, clear error
- S03: RSS XML parse — caught by ElementTree exception
- S05: Silent audio — Whisper returns empty, pipeline continues
- S06: MP4 input — faster-whisper handles via FFmpeg
- S08: Non-English — GPT-4o handles multilingual
- S11: Many censor points — O(n) on pydub, acceptable for 200 items
- S12: FFmpeg JSON parse — handled by _parse_loudnorm_json
- S14: No clips — downstream handles empty lists
- S18: Resume after crash — PipelineState handles, -y overwrites
- S20: Past publish_at — YouTube publishes immediately
- S21: Twitter API revoked — caught, pipeline continues
- S22: Truncated blog — saved as-is, non-critical
- S23: SQLite locked — caught by broad except
- S25: Corrupt state — caught, starts fresh
