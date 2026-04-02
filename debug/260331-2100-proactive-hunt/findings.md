# Bug Hunt Findings

**Date:** 2026-03-31
**Scope:** Entire podcast-automation codebase
**Iterations:** 20

## Confirmed Bugs

### [MEDIUM] Non-atomic pipeline state write risks checkpoint data loss

- **Location:** `pipeline_state.py:55-56`
- **Hypothesis:** `open("w")` truncates the state file before `json.dump` writes — a crash mid-write leaves a corrupted/empty state file
- **Evidence:** `_save()` does `with open(self.state_file, "w") as f: json.dump(...)` — this truncates first, then writes. Process kill between truncate and write completion = empty file
- **Impact:** `--resume` loses all checkpoint progress, requiring full re-processing (transcription, analysis, video conversion — potentially hours of GPU time)
- **Root cause:** Missing atomic write pattern
- **Suggested fix:** Write to `{state_file}.tmp`, then `os.replace(tmp, state_file)` for atomic swap

### [MEDIUM] Naive datetime in scheduler publish_at — timezone missing

- **Location:** `scheduler.py:253`
- **Hypothesis:** `datetime.now().isoformat()` produces timezone-unaware ISO string
- **Evidence:** Output is `2026-03-31T21:00:00` (no `Z` or `+00:00`). YouTube API's `publishAt` expects RFC 3339 with timezone
- **Impact:** Scheduled uploads could be off by the user's UTC offset (4-5 hours for EST)
- **Root cause:** Using `datetime.now()` instead of timezone-aware datetime
- **Suggested fix:** Use `datetime.now(timezone.utc).isoformat()` or `datetime.now().astimezone().isoformat()`

### [MEDIUM] Missing timeout on FFmpeg subprocess calls

- **Location:** `audio_processor.py:143, 185`, `pipeline/steps/audio.py:80`, `demo_packager.py:534`
- **Hypothesis:** FFmpeg subprocess calls without timeout could hang indefinitely
- **Evidence:** Other FFmpeg calls in the codebase use `timeout=300` or `timeout=600`, but these 4 calls have no timeout
- **Impact:** Pipeline freezes permanently if FFmpeg encounters a corrupt file or infinite loop
- **Root cause:** Inconsistent timeout application across subprocess calls
- **Suggested fix:** Add `timeout=600` (10 minutes) to all FFmpeg subprocess calls

### [LOW] Redundant transcript file re-read shadows ctx variable

- **Location:** `pipeline/steps/distribute.py:483-484`
- **Hypothesis:** Re-reads `transcript_data` from disk instead of using `ctx.transcript_data`
- **Evidence:** `with open(transcript_path, "r") as f: transcript_data = json.load(f)` — ctx already has this data
- **Impact:** Unnecessary disk I/O, variable shadowing (confusing code)
- **Suggested fix:** Replace with `episode_duration = int((ctx.transcript_data or {}).get("duration", 3600))`

### [LOW] video_converter doesn't verify output file exists after FFmpeg success

- **Location:** `video_converter.py:123-125`
- **Hypothesis:** Returns path when `returncode == 0` without checking file existence
- **Evidence:** `cut_video_clip` in `video_utils.py:297-299` checks `Path(output_path).exists()` but `video_converter.py` does not
- **Impact:** Phantom paths if FFmpeg exits 0 without creating file (disk full scenario)
- **Suggested fix:** Add `if not Path(output_path).exists(): return None` after returncode check

## Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| CRITICAL | 0 | - |
| HIGH | 0 | - |
| MEDIUM | 3 | Non-atomic state write, naive datetime, missing timeouts |
| LOW | 2 | Redundant file read, missing file check |
| **Total** | **5** | |

## Disproven Hypotheses

See `eliminated.md` for the 15 hypotheses that were investigated and found to be non-issues.
