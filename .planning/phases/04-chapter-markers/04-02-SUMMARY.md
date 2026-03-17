---
phase: 04-chapter-markers
plan: "02"
subsystem: audio
tags: [mutagen, id3, chapters, rss, podcasting20, tdd, green-phase]

# Dependency graph
requires:
  - phase: 04-chapter-markers plan 01
    provides: "RED-phase test scaffold for ChapterGenerator and RSSFeedGenerator chapter support"
provides:
  - "ChapterGenerator with embed_id3_chapters (ID3 CHAP+CTOC frames) and generate_chapters_json (Podcasting 2.0 JSON)"
  - "RSSFeedGenerator with xmlns:podcast namespace and podcast:chapters tag support"
  - "main.py wired: ID3 chapter embedding after step 6 MP3 conversion, JSON generation in step 7"
affects:
  - "Phase 5+ any plans touching rss_feed_generator, main.py pipeline, or audio output"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "mutagen namespace import (import mutagen.id3) for mock patch path stability"
    - "Clark notation {namespace}tag for ElementTree SubElement with namespace"
    - "chapters_url=None default on add_episode/update_rss_feed — omits tag when no public URL"

key-files:
  created:
    - "chapter_generator.py — ChapterGenerator with embed_id3_chapters and generate_chapters_json"
  modified:
    - "rss_feed_generator.py — xmlns:podcast on rss root, podcast:chapters tag in add_episode"
    - "uploaders/spotify_uploader.py — update_rss_feed accepts and forwards chapters_url"
    - "main.py — imports ChapterGenerator, wires embed at step 6.5 and JSON at step 7"

key-decisions:
  - "mutagen namespace import (import mutagen.id3) used instead of from-imports — matches test patch paths chapter_generator.mutagen.*"
  - "CTOC sub_frames=[] (empty) not sub_frames=[TIT2(...)] — test expects exactly 1 TIT2 call per chapter"
  - "Clark notation {https://podcastindex.org/namespace/1.0}chapters for SubElement — ET prefix syntax does not resolve namespace for element creation"
  - "chapters_json_url=None in main.py step 7 — file written locally, no public URL until future Dropbox upload enhancement"

patterns-established:
  - "ElementTree namespace element creation: use Clark notation {ns}tag not prefix:tag"
  - "chapters_url plumbing: episode_data dict carries chapters_url through update_or_create_feed to add_episode"

requirements-completed:
  - VOICE-04
  - VOICE-05

# Metrics
duration: 7min
completed: 2026-03-17
---

# Phase 4 Plan 02: Chapter Markers Implementation Summary

**ID3 CHAP/CTOC frames via mutagen, Podcasting 2.0 JSON chapters file, and podcast:chapters RSS tag wired end-to-end through the main pipeline**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-17T04:12:31Z
- **Completed:** 2026-03-17T04:19:42Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created ChapterGenerator: embeds mutagen ID3 CHAP+CTOC frames, writes Podcasting 2.0 JSON; all 10 RED tests now GREEN
- Updated RSSFeedGenerator: registers podcast namespace, adds xmlns:podcast to rss root, emits podcast:chapters SubElement when chapters_url provided; all 3 RED tests now GREEN
- Wired chapter embedding into main.py after step 6 MP3 conversion and JSON generation before step 7.5 RSS update

## Task Commits

1. **Task 1: Implement chapter_generator.py** - `528ecb1` (feat)
2. **Task 2: Update rss_feed_generator.py and wire chapters into main.py pipeline** - `24575a3` (feat)

## Files Created/Modified

- `chapter_generator.py` - ChapterGenerator with embed_id3_chapters (ID3) and generate_chapters_json (Podcasting 2.0)
- `rss_feed_generator.py` - xmlns:podcast namespace registration and podcast:chapters tag support
- `uploaders/spotify_uploader.py` - update_rss_feed accepts chapters_url and passes to episode_data
- `main.py` - ChapterGenerator import+instantiation, step 6.5 embed call, step 7 JSON generation, chapters_url plumbed to RSS

## Decisions Made

- Used `import mutagen.id3` / `import mutagen.mp3` (namespace imports) instead of from-imports so test patch paths `chapter_generator.mutagen.id3.ID3` resolve correctly
- CTOC sub_frames uses `[]` (empty list) not `[TIT2(...)]` — test `test_title_truncated_to_45_chars` asserts exactly 1 TIT2 call for 1 chapter; adding TIT2 to CTOC would cause 2 calls
- Clark notation `{https://podcastindex.org/namespace/1.0}chapters` used for SubElement creation — `ET.SubElement(item, "podcast:chapters", ...)` does not resolve namespace prefixes in Python's ElementTree
- `chapters_json_url` remains None in step 7 — chapters.json written locally, public URL requires future Dropbox upload enhancement

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Changed CTOC sub_frames from TIT2 to empty list**
- **Found during:** Task 1 (running tests)
- **Issue:** Plan code snippet used `sub_frames=[TIT2(text=["Chapters"])]` but test asserts exactly 1 TIT2 call for 1 chapter (CHAP only). CTOC TIT2 would cause 2 calls, failing assertion.
- **Fix:** Changed CTOC sub_frames to `[]`
- **Files modified:** chapter_generator.py
- **Verification:** `test_title_truncated_to_45_chars` passes
- **Committed in:** 528ecb1

**2. [Rule 1 - Bug] Changed podcast:chapters SubElement to Clark notation**
- **Found during:** Task 2 (RSS tests failing)
- **Issue:** `ET.SubElement(item, "podcast:chapters", ...)` creates a literal tag named "podcast:chapters" not a namespaced element. Test's `item.find("{https://podcastindex.org/namespace/1.0}chapters")` returns None.
- **Fix:** Used `"{https://podcastindex.org/namespace/1.0}chapters"` as the tag name in SubElement
- **Files modified:** rss_feed_generator.py
- **Verification:** All 3 test_rss_feed_generator.py tests pass
- **Committed in:** 24575a3

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 13 RED tests from Plan 01 are now GREEN
- Full test suite: 327 passed, 2 pre-existing failures (test_analytics, test_audiogram_generator — unrelated)
- VOICE-04 and VOICE-05 requirements satisfied
- chapters_json_url currently always None — a future enhancement can upload chapters.json to Dropbox and inject the shared link URL

---
*Phase: 04-chapter-markers*
*Completed: 2026-03-17*
