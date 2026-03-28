---
phase: 17-integration-testing-genre-fixes
plan: 02
subsystem: testing
tags: [multi-client, rss-ingest, genre-aware, integration-test, true-crime, compliance]

# Dependency graph
requires:
  - phase: 17-01
    provides: "Genre-aware clip selection and compliance prompt via CLIP_SELECTION_MODE/COMPLIANCE_STYLE"
  - phase: 16-rss-episode-source
    provides: "RSS episode ingest path and _YAML_TO_CONFIG extension pattern"
provides:
  - "Validated true-crime-client.yaml with RSS source, content clip selection, strict compliance"
  - "Validated business-interview-client.yaml with RSS source, content clip selection, standard compliance"
  - "End-to-end integration proof: two non-comedy genres produce genre-appropriate output"
  - "Six bug fixes discovered during real-episode integration testing"
affects: [clients, pipeline/steps/distribute.py, rss_episode_fetcher.py, audio_processor.py, uploaders]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Non-Dropbox client guard: check component existence before calling Dropbox-specific distribute steps"
    - "RSS downloader User-Agent spoofing for feeds that block default Python requests"
    - "normalize_audio temp-file-then-rename pattern to avoid FFmpeg in-place write crash"

key-files:
  created: []
  modified:
    - clients/true-crime-client.yaml
    - clients/business-interview-client.yaml
    - pipeline/steps/distribute.py
    - rss_episode_fetcher.py
    - audio_processor.py
    - pyproject.toml

key-decisions:
  - "True crime client uses Casefile Acast feed URL (original Simplecast feed returns 403)"
  - "normalize_audio writes to temp file then renames to avoid FFmpeg refusing input=output path"
  - "Non-Dropbox clients must skip ALL uploaders in distribute.py (not just Dropbox step) to prevent FP credential leakage"
  - "PyTorch CUDA 12.4 index pinned in pyproject.toml to prevent CPU-only install on GPU machines"

patterns-established:
  - "Integration testing pattern: run real episodes, inspect analysis JSON for tone/contamination, check compliance counts"
  - "RSS feed verification: test feed URL directly before adding to YAML; Acast/Simplecast feeds may rotate URLs"

requirements-completed: [TEST-01, TEST-02]

# Metrics
duration: ~40min (integration run dominated by Whisper + GPT-4o API time)
completed: 2026-03-28
---

# Phase 17 Plan 02: Genre Client YAML Configuration and Integration Testing Summary

**True crime and business interview episodes processed end-to-end via RSS with genre-appropriate tone, compliance calibration, and zero Fake Problems contamination — six pipeline bugs found and fixed during integration**

## Performance

- **Duration:** ~40 min (dominated by Whisper transcription + OpenAI API calls)
- **Started:** 2026-03-28
- **Completed:** 2026-03-28
- **Tasks:** 2 (Task 1 auto, Task 2 human-verify checkpoint)
- **Files modified:** 6

## Accomplishments

- Configured `true-crime-client.yaml` with Casefile RSS source, `clip_selection_mode: content`, `compliance_style: strict`
- Configured `business-interview-client.yaml` with How I Built This RSS source, `clip_selection_mode: content`, `compliance_style: standard`
- True crime episode (BTK/Casefile ep 399) produced investigative, journalistic tone — no comedy framing, compliance strict mode flagged 12 items (graphic_violence, sexual_content, self_harm), upload correctly blocked
- Business interview episode (How I Built This ep 18) produced professional, educational tone — 0 compliance flags, clips focused on specific insights
- Six bugs discovered and fixed during integration: Dropbox credential leakage, FFmpeg in-place normalize crash, distribute.py KeyError, stale RSS URL, RSS 403, PyTorch CPU-only install

## Task Commits

Each task was committed atomically:

1. **Task 1: Update genre client YAMLs with RSS source and content fields** - `e9acbd1` (feat)
2. **Task 2 bug fixes (discovered during integration):**
   - `6566788` fix: skip all uploaders for non-dropbox clients (FP credential leakage)
   - `f9240ad` fix: User-Agent header for RSS downloader + update Casefile URL to Acast
   - `b19ec1e` fix: PyTorch CUDA 12.4 index in pyproject.toml
   - `3f29136` fix: normalize_audio temp file + rename pattern
   - `921c2ad` fix: skip Dropbox upload when component not configured

## Files Created/Modified

- `clients/true-crime-client.yaml` - RSS source (Casefile Acast), content clip selection, strict compliance
- `clients/business-interview-client.yaml` - RSS source (How I Built This), content clip selection, standard compliance
- `pipeline/steps/distribute.py` - Guard against missing Dropbox component; skip all uploaders for non-Dropbox clients
- `rss_episode_fetcher.py` - User-Agent header for RSS HTTP requests; updated Casefile feed URL
- `audio_processor.py` - normalize_audio writes to temp file then renames (avoids FFmpeg in-place crash)
- `pyproject.toml` - PyTorch CUDA 12.4 index URL for GPU machines

## Decisions Made

- Casefile original Simplecast URL (`feeds.simplecast.com/xl3WWLBP`) returns 403 — updated to Acast URL discovered by testing directly
- `normalize_audio` crash was FFmpeg refusing to read and write the same file path; fix is temp file + atomic rename
- All uploaders (not just Dropbox) must be skipped for non-Dropbox clients — each uploader reads FP-specific env vars at construction time, which could leak credentials or produce wrong-client output
- PyTorch installed CPU-only from default PyPI index; GPU acceleration requires CUDA-specific index pinned in `pyproject.toml`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Uploaders leaked Fake Problems credentials to RSS clients**
- **Found during:** Task 2 (integration test — true crime processing)
- **Issue:** `distribute.py` ran all platform uploaders even for non-Dropbox clients, causing FP API credentials to be used for non-FP content
- **Fix:** Added guard to skip all uploaders when `episode_source != dropbox`
- **Files modified:** `pipeline/steps/distribute.py`
- **Committed in:** `6566788`

**2. [Rule 3 - Blocking] RSS downloader returned 403 Forbidden**
- **Found during:** Task 2 (first run of true crime client)
- **Issue:** Casefile's Acast CDN blocks requests without a browser-like User-Agent; also the Simplecast feed URL was stale
- **Fix:** Added `User-Agent: Mozilla/5.0` header to RSS HTTP requests; updated Casefile feed URL to current Acast URL
- **Files modified:** `rss_episode_fetcher.py`, `clients/true-crime-client.yaml`
- **Committed in:** `f9240ad`

**3. [Rule 3 - Blocking] PyTorch installed as CPU-only — Whisper ran 3x slower**
- **Found during:** Task 2 (Whisper transcription step)
- **Issue:** Default PyPI PyTorch is CPU-only; CUDA variant requires a separate index URL
- **Fix:** Added CUDA 12.4 extra index URL to `pyproject.toml`; ran `uv sync` to reinstall GPU-enabled PyTorch
- **Files modified:** `pyproject.toml`
- **Committed in:** `b19ec1e`

**4. [Rule 1 - Bug] FFmpeg normalize_audio crashed when writing in-place**
- **Found during:** Task 2 (audio normalization step)
- **Issue:** `normalize_audio` passed the same path as both input and output to FFmpeg, which FFmpeg refuses (would corrupt the source)
- **Fix:** Write to a temp file, then `os.replace(temp, original)` for atomic rename
- **Files modified:** `audio_processor.py`
- **Committed in:** `3f29136`

**5. [Rule 1 - Bug] `distribute.py` raised KeyError for missing Dropbox component**
- **Found during:** Task 2 (distribute step for RSS client)
- **Issue:** `distribute.py` accessed `self.components["dropbox"]` unconditionally; RSS clients don't have that component
- **Fix:** Added `if "dropbox" in self.components:` guard before Dropbox-specific steps
- **Files modified:** `pipeline/steps/distribute.py`
- **Committed in:** `921c2ad`

---

**Total deviations:** 5 auto-fixed (2 blocking, 3 bugs)
**Impact on plan:** All auto-fixes were required for pipeline to complete. No scope creep.

## Issues Encountered

- Casefile feed URL in the plan's interface spec was stale (Simplecast → Acast migration). Discovered by testing the URL directly and updating in YAML + rss_episode_fetcher.py.
- PyTorch GPU dependency is not automatically handled by `uv sync` from default PyPI — requires explicit CUDA index. Added to `pyproject.toml` as a permanent fix so future `uv sync` runs on GPU machines get CUDA PyTorch.

## User Setup Required

None - no external service configuration required beyond what was already configured.

## Next Phase Readiness

- Both genre client YAMLs are production-ready: RSS sources configured, genre-appropriate clip selection and compliance active
- Six pipeline bugs fixed — RSS clients now process cleanly end-to-end without FP contamination
- All four phase 17 requirements verified: TEST-01, TEST-02 (this plan), TEST-03, TEST-04 (Plan 01)
- Phase 17 is complete — pipeline is validated for true crime and business interview genres
- Ready for v1.4 demo packaging (Phase 18)

## Self-Check

Commits verified in git log:
- `e9acbd1` feat(17-02): add RSS source and genre content fields to client YAMLs - FOUND
- `6566788` fix(17-02): skip all uploaders for non-dropbox clients - FOUND
- `f9240ad` fix(17-02): add User-Agent header to RSS downloader, update Casefile feed URL - FOUND
- `b19ec1e` fix: configure PyTorch CUDA 12.4 index in pyproject.toml - FOUND
- `3f29136` fix: normalize_audio writes to temp file when in-place - FOUND
- `921c2ad` fix(17-02): skip Dropbox upload when component not configured - FOUND

## Self-Check: PASSED

All commits confirmed in git log. Client YAMLs verified to contain required fields.

---
*Phase: 17-integration-testing-genre-fixes*
*Completed: 2026-03-28*
