---
phase: 06-subtitle-clip-generator
plan: 01
subsystem: content
tags: [pysubs2, ass-subtitles, ffmpeg, word-timestamps, whisperx, captions, vertical-video]

# Dependency graph
requires:
  - phase: existing
    provides: subtitle_generator.py with extract_words_for_clip(), config.py with FFMPEG_PATH and ASSETS_DIR

provides:
  - SubtitleClipGenerator class with pysubs2 ASS generation and FFmpeg burn-in
  - normalize_word_timestamps() for gap/overlap/interpolation correction
  - _generate_ass_file() with per-word Hormozi-style accent color highlights
  - _build_ffmpeg_command() for 720x1280 vertical video with -c:a copy
  - _escape_ffmpeg_filter_path() for Windows drive-letter colon handling
  - 31 unit tests covering all public methods and critical helpers

affects:
  - 06-02 (pipeline wiring — subtitle_clip_generator is the rendering engine)

# Tech tracking
tech-stack:
  added:
    - pysubs2==1.8.0 (ASS subtitle file generation)
  patterns:
    - TDD red/green with real pysubs2 ASS file inspection in TestGenerateAssFile
    - Per-word SSAEvent with inline {\c&H...&} color override for active word
    - Windows FFmpeg filter path escaping via dedicated _escape_ffmpeg_filter_path()

key-files:
  created:
    - subtitle_clip_generator.py
    - tests/test_subtitle_clip_generator.py
  modified:
    - requirements.txt (added pysubs2==1.8.0)

key-decisions:
  - "pysubs2.Alignment.BOTTOM_CENTER used instead of plain int 2 to avoid DeprecationWarning in pysubs2 1.8.0"
  - "srt_path parameter accepted for interface compatibility but word timing sourced exclusively from transcript_data['words']"
  - "SUBTITLE_ACCENT_COLOR defaults to 0x00e0ff (bright cyan) for high contrast on dark 0x1a1a2e background"

patterns-established:
  - "Pattern: normalize_word_timestamps() called before every ASS generation — prerequisite, not optional"
  - "Pattern: all word text .upper() and { } escaped as \\{ \\} before pysubs2 insertion"
  - "Pattern: _to_bgr_hex() converts 0xRRGGBB to BBGGRR for ASS inline \\c&H...& tags"

requirements-completed: [CLIP-01, CLIP-02, CLIP-03]

# Metrics
duration: 4min
completed: 2026-03-18
---

# Phase 6 Plan 01: Subtitle Clip Generator Summary

**pysubs2 ASS subtitle engine with per-word Hormozi-style accent color highlights, WhisperX timestamp normalization, and Windows FFmpeg path escaping for 720x1280 vertical clip generation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-18T03:46:08Z
- **Completed:** 2026-03-18T03:50:21Z
- **Tasks:** 1
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- Built SubtitleClipGenerator rendering engine with all methods required by CLIP-01/02/03
- normalize_word_timestamps() handles three common WhisperX failure modes: gaps <150ms, overlapping segments, and words with zero timestamps
- _generate_ass_file() groups words into 3-word cards; each word becomes one SSAEvent with accent color on the active word and white on surrounding words
- 31 unit tests verify all public methods, helpers, and critical edge cases

## Task Commits

1. **Task 1: Build SubtitleClipGenerator module with tests** - `9aba732` (feat)

**Plan metadata:** (following this summary commit)

## Files Created/Modified
- `subtitle_clip_generator.py` - SubtitleClipGenerator class with all rendering logic
- `tests/test_subtitle_clip_generator.py` - 31 unit tests across 9 test classes
- `requirements.txt` - Added pysubs2==1.8.0

## Decisions Made
- Used `pysubs2.Alignment.BOTTOM_CENTER` enum instead of plain `int 2` to avoid DeprecationWarning in pysubs2 1.8.0
- `srt_path` parameter accepted for interface compatibility with AudiogramGenerator pattern but word timing sourced exclusively from `transcript_data["words"]` via `SubtitleGenerator.extract_words_for_clip()`
- Default accent color set to `0x00e0ff` (bright cyan) rather than show's `0xe94560` red-pink — cyan has higher contrast on the dark navy `0x1a1a2e` background; user can override via `SUBTITLE_ACCENT_COLOR`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- pysubs2 1.8.0 emits DeprecationWarning when `alignment` is set as a plain integer. Fixed by using `pysubs2.Alignment.BOTTOM_CENTER` enum (Rule 1 — minor bug, inline fix, no separate commit needed).

## User Setup Required
None - no external service configuration required. Font file (Anton-Regular.ttf) noted in blockers for end-to-end testing.

## Next Phase Readiness
- SubtitleClipGenerator rendering engine is complete and tested
- Plan 02 wires it into pipeline/steps/video.py as the first-checked branch under USE_SUBTITLE_CLIPS=true
- Blocker noted: Anton-Regular.ttf must be committed to assets/fonts/ before end-to-end clip testing (libass will silently substitute DejaVu Sans otherwise)

---
*Phase: 06-subtitle-clip-generator*
*Completed: 2026-03-18*
