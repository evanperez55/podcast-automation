---
phase: 06-subtitle-clip-generator
plan: 02
subsystem: video
tags: [ffmpeg, pysubs2, subtitle-clips, pipeline, libass, anton-font]

# Dependency graph
requires:
  - phase: 06-01
    provides: SubtitleClipGenerator class with create_subtitle_clips() batch method
provides:
  - SubtitleClipGenerator wired into pipeline Step 5.5 as default first-priority path
  - Anton-Regular.ttf font asset in assets/fonts/ for bold libass caption rendering
  - Subtitle clip branch before audiogram check in pipeline/steps/video.py
  - SubtitleClipGenerator registered in both dry_run and normal _init_components()
affects:
  - phase 07 (site publish): video_clip_paths populated by subtitle clips for social upload
  - phase 08 (compliance): upload step now feeds subtitle MP4s not audiograms

# Tech tracking
tech-stack:
  added: [Anton-Regular.ttf (Google Fonts, 170KB TTF)]
  patterns:
    - subtitle_clip_generator checked first in Step 5.5 (before audiogram, before plain converter)
    - USE_SUBTITLE_CLIPS env var gates feature; default true
    - checkpoint save (convert_videos) mirrored across all three Step 5.5 branches

key-files:
  created:
    - assets/fonts/Anton-Regular.ttf
  modified:
    - pipeline/runner.py
    - pipeline/steps/video.py

key-decisions:
  - "Subtitle clip branch inserted as first elif in Step 5.5; audiogram preserved as second elif (fallback when USE_SUBTITLE_CLIPS=false)"
  - "dry_run() updated to surface subtitle clip mode in Step 5.5 mock output and module validation list"

patterns-established:
  - "New video generation modes go BEFORE existing modes in Step 5.5 elif chain (highest-priority first)"
  - "Each Step 5.5 branch must include full episode video creation AND checkpoint save"

requirements-completed: [CLIP-04]

# Metrics
duration: 5min
completed: 2026-03-18
---

# Phase 06 Plan 02: Pipeline Wiring Summary

**SubtitleClipGenerator wired into pipeline Step 5.5 as first-priority path with Anton font, audiogram preserved as fallback**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-18T22:53Z
- **Completed:** 2026-03-18T22:58Z
- **Tasks:** 1 of 2 (Task 2 is checkpoint:human-verify)
- **Files modified:** 3

## Accomplishments
- `SubtitleClipGenerator` imported and instantiated in both dry_run and normal `_init_components()` paths
- New subtitle clip elif branch added as first-priority in Step 5.5 before audiogram check
- Audiogram fallback preserved unchanged (active when `USE_SUBTITLE_CLIPS=false`)
- Anton-Regular.ttf (170KB) committed to `assets/fonts/` for bold libass rendering
- dry_run() updated to show subtitle clip mode in mock output and module validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Download Anton font and wire SubtitleClipGenerator into pipeline** - `0891f87` (feat)

**Deviation fix:** `8ef126b` (fix: update dry_run() to display subtitle clip mode correctly)

## Files Created/Modified
- `assets/fonts/Anton-Regular.ttf` - Anton bold font (170KB, Google Fonts OFL) for libass subtitle rendering
- `pipeline/runner.py` - Import + instantiate SubtitleClipGenerator in both dry_run and normal init; update dry_run mock output
- `pipeline/steps/video.py` - Add subtitle_clip_generator branch as first elif in Step 5.5

## Decisions Made
- Subtitle clip branch is the default (USE_SUBTITLE_CLIPS=true); audiogram only activates when subtitle clips are disabled
- dry_run validation updated immediately (Rule 1 deviation) to avoid silent incorrect mock output

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed dry_run() Step 5.5 display not reflecting new subtitle clip mode**
- **Found during:** Task 1 (pipeline wiring)
- **Issue:** dry_run() still showed only audiogram vs plain video mode for Step 5.5, missing subtitle clip mode — incorrect output when USE_SUBTITLE_CLIPS=true (the default)
- **Fix:** Added subtitle_clip_generator extraction, new first-priority if-branch in dry run Step 5.5 mock output, and added SubtitleClipGenerator to module validation list
- **Files modified:** pipeline/runner.py
- **Verification:** ruff clean, all 36 tests pass
- **Committed in:** 8ef126b

---

**Total deviations:** 1 auto-fixed (Rule 1 - incorrect dry run display)
**Impact on plan:** Necessary for correctness of dry run output. No scope creep.

## Issues Encountered
None — pipeline wiring was straightforward.

## Checkpoint Status

**Task 2 (human-verify):** Awaiting visual confirmation that subtitle clips render with Anton font, correct word highlighting, and synced captions. See checkpoint details below.

## Next Phase Readiness
- Pipeline wiring complete — `USE_SUBTITLE_CLIPS=true` will produce subtitle clips as default
- Audiogram fallback verified in code
- Pending: human visual verification of rendered clip quality (Task 2 checkpoint)

---
*Phase: 06-subtitle-clip-generator*
*Completed: 2026-03-18*
