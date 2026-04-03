# Pipeline Scenario Exploration

**Date:** 2026-04-02
**Seed:** Full podcast pipeline from download to multi-platform posting
**Domain:** Software
**Iterations:** 25

---

## Iteration 1 — [HAPPY_PATH] Standard Episode Processing

**Actors:** Pipeline operator (user)
**Precondition:** Episode audio uploaded to Dropbox, all API credentials valid
**Trigger:** `uv run main.py ep30 --auto-approve`
**Flow:**
1. Dropbox downloads WAV file
2. WhisperX transcribes with speaker diarization
3. GPT-4o analyzes transcript, produces clips/summary/social captions
4. AudioProcessor censors profanity with beep overlay
5. AudioProcessor normalizes LUFS levels
6. AudioProcessor creates 8 clips (20-30s each)
7. SubtitleClipGenerator burns SRT captions into vertical video clips
8. ThumbnailGenerator creates 1280x720 PNG
9. AudioProcessor converts to MP3
10. DropboxHandler uploads MP3 to finished folder
11. RSSFeedGenerator updates podcast_feed.xml
12. YouTubeUploader uploads full episode + clips as Shorts (clips 3-8 private)
13. TwitterUploader posts 4-tweet thread
14. BlueskyUploader posts episode + clips
15. ContentCalendar creates 2-week distribution plan
16. PipelineState checkpoints after each step

**Expected outcome:** All uploads succeed, calendar populated, state file shows all steps complete
**What could go wrong:** Any step could fail — checkpoint/resume should handle gracefully
**Severity:** -

---

## Iteration 2 — [ERROR_PATH] Dropbox Download Fails Mid-Transfer

**Actors:** Pipeline, Dropbox API
**Precondition:** Episode exists in Dropbox, network is unstable
**Trigger:** Network drops during large WAV download (500MB+)
**Flow:**
1. download_episode starts streaming chunks to local file
2. Network interruption at 60% through download
3. requests raises ConnectionError
4. retry_with_backoff retries 3 times with exponential delay
5. All retries fail

**Expected outcome:** Pipeline raises Exception, partial file deleted, user informed
**What could go wrong:** Partial file left on disk, next run uses corrupt truncated WAV. The new size check (Bug #9 fix) would catch this, but the partial file itself isn't cleaned up — it persists at `downloads/episode.wav`
**Severity:** HIGH — Corrupted audio could propagate through entire pipeline silently
**Edge case found:** `dropbox_handler.py` doesn't delete partial downloads on failure

---

## Iteration 3 — [EDGE_CASE] Episode With Zero Profanity

**Actors:** Pipeline, ContentEditor, AudioProcessor
**Precondition:** Episode is clean — no profanity detected by GPT-4o
**Trigger:** Analysis returns `censor_timestamps: []`
**Flow:**
1. ContentEditor returns empty censor_timestamps list
2. AudioProcessor.apply_censorship() called with empty list
3. ??? Does it skip censoring or still process?

**Expected outcome:** Censored file = original file, pipeline continues
**What could go wrong:** apply_censorship might still write the file (wasting time on 500MB WAV) or might return None (breaking downstream)
**Severity:** MEDIUM

---

## Iteration 4 — [INTEGRATION] YouTube Daily Upload Quota Exceeded

**Actors:** Pipeline, YouTube API
**Precondition:** Already uploaded 5+ videos today (YouTube limits unverified channels)
**Trigger:** YouTubeUploader.upload_short() for clip 6 hits quota limit
**Flow:**
1. Clips 1-5 upload successfully
2. Clip 6 returns `uploadLimitExceeded` error
3. YouTubeUploader catches HttpError, returns None
4. Pipeline records clip 6-8 as failed uploads

**Expected outcome:** Pipeline continues with remaining platforms (Twitter, Bluesky), failed clips logged
**What could go wrong:** Content calendar gets populated with clip slots that have no youtube_video_id — scheduled posting later tries to make a non-existent video public. (This is exactly what happened with ep30 clip 8!)
**Severity:** HIGH — Calendar slots reference videos that don't exist

---

## Iteration 5 — [CONCURRENT] Two Pipeline Runs for Same Episode

**Actors:** User (2 terminals), Pipeline, PipelineState
**Precondition:** User accidentally runs `uv run main.py ep30` in two terminals simultaneously
**Trigger:** Both processes start at the same time
**Flow:**
1. Both processes create PipelineState for "ep_30"
2. Both download the same WAV from Dropbox (wasted bandwidth)
3. Both transcribe simultaneously (WhisperX on same GPU = OOM crash or serialized)
4. Both write checkpoint JSON — last writer wins (race condition on state file)
5. Both try to upload to YouTube — second upload gets duplicate rejection

**Expected outcome:** One should succeed, other should detect and abort
**What could go wrong:** PipelineState has no file locking — both writes succeed, checkpoint corruption. GPU OOM from two Whisper processes. Double-upload to YouTube (duplicate content flag)
**Severity:** CRITICAL — No protection against concurrent runs

---

## Iteration 6 — [TEMPORAL] Content Calendar Slot Fires During Platform Outage

**Actors:** GitHub Actions, Twitter API, BlueskyUploader
**Precondition:** Calendar has clip_3 scheduled for today, Twitter is down
**Trigger:** scheduled-content.yml runs at 10 AM ET
**Flow:**
1. post_scheduled_content reads pending slots
2. Attempts to make YouTube Short public → succeeds
3. Attempts Twitter post → ConnectionError after timeout
4. Exception caught, results["twitter"] = {"error": "..."}
5. mark_slot_failed called because results contain error

**Expected outcome:** Slot marked as failed, YouTube Short was already made public but social posts didn't go out
**What could go wrong:** YouTube privacy change succeeded (irreversible) but slot is marked "failed" — the Short is now public without social promotion. Re-running won't retry the YouTube privacy change (it checks slot status, sees "failed", might skip or reattempt everything)
**Severity:** HIGH — Partial execution with no rollback. YouTube action is irreversible but slot status doesn't track per-platform success/failure

---

## Iteration 7 — [EDGE_CASE] Episode Title Contains Special Characters

**Actors:** Pipeline, all uploaders, thumbnail generator
**Precondition:** Episode title is `"It's a 'Test' — Does <HTML> & "Quotes" Work?"`
**Trigger:** Pipeline processes episode with special chars in title
**Flow:**
1. Thumbnail generator renders text with quotes/ampersands → Pillow handles fine
2. RSS feed generator → xml.etree escapes automatically ✓
3. Twitter post → 280 char limit with URL, special chars count as 1 each
4. YouTube title → max 100 chars, special chars allowed
5. Bluesky post → 300 grapheme limit, curly quotes = multi-byte graphemes
6. File paths → episode folder name derived from title?

**Expected outcome:** All platforms handle special chars correctly
**What could go wrong:** If episode folder name is derived from the raw title, characters like `<>:"/\|?*` are invalid in Windows paths. The `&` in RSS could break if not escaped (but xml.etree handles it). Bluesky grapheme counting might truncate differently than Python `len()`.
**Severity:** MEDIUM — Windows path chars could crash pipeline

---

## Iteration 8 — [RECOVERY] Pipeline Crashes at Step 5.5 (Video Conversion)

**Actors:** Pipeline, PipelineState, FFmpeg
**Precondition:** Pipeline ran steps 1-5 successfully, NVENC session limit hit at step 5.5
**Trigger:** FFmpeg OOM or NVENC failure during video conversion
**Flow:**
1. Pipeline state has steps 1-5 checkpointed
2. video_converter.py raises RuntimeError (even with new NVENC fallback, libx264 could also fail on very large files)
3. Pipeline catches exception, logs error
4. User reruns with `--resume`
5. Steps 1-5 skipped (checkpointed), step 5.5 retried

**Expected outcome:** Resume picks up where it left off, video conversion retried
**What could go wrong:** Step 5 outputs (clip WAV files) might be referenced by Path objects stored in PipelineState — if the output directory was cleaned between runs, the paths are stale. Also, if the crash happened mid-write of the state file (before the atomic write fix), state could be corrupted.
**Severity:** MEDIUM — Resume should work now with atomic state writes

---

## Iteration 9 — [DATA_VARIATION] Very Short Episode (Under 2 Minutes)

**Actors:** Pipeline, ContentEditor, AudioProcessor
**Precondition:** Episode audio is only 90 seconds long
**Trigger:** User processes a trailer/teaser episode
**Flow:**
1. Transcription succeeds (short audio = fast)
2. GPT-4o analysis: asked for 8 clips from a 90-second episode
3. best_clips returned are overlapping or cover the entire episode
4. Clip creation: clips may be longer than the source audio
5. "Best clips" of 20-30s each × 8 = 160-240s needed from 90s source

**Expected outcome:** Fewer clips generated, no crashes
**What could go wrong:** Clip start/end timestamps from GPT-4o could exceed audio duration. AudioProcessor.create_clips() would try to slice beyond the end of the audio. Pydub handles this gracefully (returns shorter segment), but the clip might be 2 seconds instead of 20 — useless content uploaded to YouTube.
**Severity:** MEDIUM — No validation that clip timestamps are within audio bounds

---

## Iteration 10 — [INTEGRATION] Bluesky AT Protocol Session Expires Mid-Posting

**Actors:** Pipeline, BlueskyUploader, AT Protocol
**Precondition:** Bluesky session created at pipeline start, posting happens 30+ minutes later
**Trigger:** AT Protocol access token expires (typically 2 hours, but can be shorter)
**Flow:**
1. BlueskyUploader.post() called with expired accessJwt
2. API returns 401 Unauthorized
3. Does the uploader auto-refresh the session?

**Expected outcome:** Session auto-refreshes, post succeeds
**What could go wrong:** If there's no refresh logic, all Bluesky posts after token expiry fail silently
**Severity:** HIGH — Could silently lose all Bluesky distribution

---

## Iteration 11 — [STATE_TRANSITION] Calendar Slot Stuck in "failed" State

**Actors:** GitHub Actions, ContentCalendar
**Precondition:** Slot marked "failed" due to temporary API error
**Trigger:** Next day's scheduled-content run
**Flow:**
1. get_all_pending_slots() only returns slots with status="pending"
2. The "failed" slot is never retried
3. That clip/quote never gets posted

**Expected outcome:** Failed slots should be retried (at least once)
**What could go wrong:** There's no retry mechanism for failed slots — they're permanently stuck. The content is lost from the calendar.
**Severity:** HIGH — No recovery path for failed scheduled posts

---

## Iteration 12 — [SCALE] 3-Hour Episode (Large Audio File)

**Actors:** Pipeline, WhisperX, FFmpeg
**Precondition:** Episode audio is 3 hours, ~1.5GB WAV file
**Trigger:** Pipeline processes the long episode
**Flow:**
1. Dropbox download: 1.5GB download, 5-10 minutes
2. WhisperX transcription: 3 hours of audio on RTX 3070 = ~15-30 minutes
3. GPT-4o analysis: very long transcript, may exceed token limit
4. Censoring: processing 1.5GB in pydub loads entire file into memory (~6GB RAM)
5. Video conversion: 3-hour video with FFmpeg, timeout set to 7200s (2 hours)
6. MP3 conversion: large file

**Expected outcome:** All steps complete, possibly slowly
**What could go wrong:** GPT-4o token limit exceeded for 3-hour transcript (100K+ words). Pydub OOM on 1.5GB WAV. FFmpeg 2-hour timeout might not be enough for 3-hour episode with subtitle burn-in. VideoConverter creates full-episode video = very long encode.
**Severity:** HIGH — Token limits and memory issues could crash silently

---

## Iteration 13 — [ABUSE] Command Injection via Episode Filename

**Actors:** Attacker (Dropbox file uploader), Pipeline
**Precondition:** Malicious filename uploaded to Dropbox: `episode; rm -rf /;.wav`
**Trigger:** Pipeline downloads file, uses filename in subprocess calls
**Flow:**
1. Dropbox returns file with malicious name
2. Pipeline creates local file path from the name
3. FFmpeg subprocess.run called with the path as argument
4. If path is passed as string (not list), shell injection possible

**Expected outcome:** Filename should be sanitized, no injection
**What could go wrong:** subprocess.run with `shell=True` would execute the injection. With `shell=False` (list args), the filename is treated as a literal path — safe. But does the pipeline ever use `shell=True`?
**Severity:** CRITICAL if shell=True used, LOW if all subprocess uses list args

---

## Iteration 14 — [PERMISSION] YouTube OAuth Token Expires and Can't Refresh

**Actors:** Pipeline, YouTube API, Google OAuth
**Precondition:** YouTube refresh token revoked (user changed Google password, or token > 6 months old)
**Trigger:** YouTubeUploader.__init__ tries to authenticate
**Flow:**
1. Load pickle token from credentials/youtube_token.pickle
2. Token is expired, attempt refresh
3. Refresh fails (revoked/expired refresh token)
4. YouTube uploader raises ValueError
5. Pipeline catches in _init_uploaders, excludes YouTube

**Expected outcome:** Pipeline continues without YouTube, other platforms still work
**What could go wrong:** If this is the GitHub Actions run, there's no way to re-authenticate interactively. YouTube uploads silently stop. No notification sent about the auth failure. Could go unnoticed for days.
**Severity:** HIGH — Silent YouTube distribution loss with no alerting

---

## Iteration 15 — [TEMPORAL] Episode Released Right Before Daylight Saving Time Change

**Actors:** User, ContentCalendar, GitHub Actions
**Precondition:** Episode released March 8 (day before spring DST in US)
**Trigger:** Calendar slots span the DST transition
**Flow:**
1. Episode released at 2 PM ET on March 8
2. Calendar slots at D+1 = March 9 at 2 PM ET
3. But on March 9, clocks spring forward — 2 PM ET = 1 PM old-time
4. GitHub Actions cron (set in UTC) fires at the same UTC time
5. datetime.now() behavior changes

**Expected outcome:** Posts go out at the intended local time
**What could go wrong:** With the TZ=America/New_York fix in GitHub Actions, DST should be handled by the OS timezone library. But the stored timestamps in calendar JSON are naive — the 2 PM on March 9 might be ambiguous or off by 1 hour depending on when the timestamp was created.
**Severity:** MEDIUM — DST transitions could cause 1-hour scheduling drift

---

## Iteration 16 — [EDGE_CASE] GPT-4o Returns Malformed Analysis JSON

**Actors:** Pipeline, ContentEditor, OpenAI API
**Precondition:** GPT-4o has a bad day, returns JSON with missing required fields
**Trigger:** analyze_content() parses the GPT response
**Flow:**
1. GPT-4o returns: `{"episode_title": "...", "social_captions": null, "best_clips": []}`
2. best_clips is empty — no clips to create
3. social_captions is null — Twitter/Bluesky posting tries to access None.get()
4. censor_timestamps missing entirely — KeyError in censoring step

**Expected outcome:** Pipeline handles missing/null fields gracefully with defaults
**What could go wrong:** KeyError on missing fields. NoneType.get() on null social_captions. Empty best_clips means no video clips, no YouTube Shorts, empty content calendar.
**Severity:** HIGH — GPT output is trusted without validation

---

## Iteration 17 — [CONCURRENT] Two GitHub Actions Runs Overlap

**Actors:** GitHub Actions, post_scheduled_content.py
**Precondition:** Scheduled run at 10 AM, plus manual workflow_dispatch at 10:01 AM
**Trigger:** Both runs execute simultaneously
**Flow:**
1. Both read content_calendar.json
2. Both find the same pending slots
3. Both post to Twitter/Bluesky (duplicate posts!)
4. Both try mark_slot_uploaded
5. Both read-modify-write the calendar JSON — last writer wins

**Expected outcome:** Only one run should post, other should detect and skip
**What could go wrong:** No locking on content_calendar.json. Duplicate social posts. Calendar corruption from concurrent writes. Git push conflict (both try to commit).
**Severity:** HIGH — Duplicate posts look unprofessional, calendar corruption

---

## Iteration 18 — [DATA_VARIATION] Episode Audio is MP3 Instead of WAV

**Actors:** Pipeline, Transcriber, AudioProcessor
**Precondition:** Someone uploads an MP3 instead of WAV to Dropbox
**Trigger:** Pipeline downloads and processes the MP3
**Flow:**
1. Download succeeds (any file extension works)
2. WhisperX: accepts MP3 natively ✓
3. AudioProcessor: pydub handles MP3 ✓
4. But: normalization with FFmpeg expects WAV pipeline
5. Output naming: `*_censored.wav` but input was MP3

**Expected outcome:** Pipeline should handle MP3 input transparently
**What could go wrong:** If any step hardcodes `.wav` extension for input validation, MP3 gets rejected. File naming inconsistencies (input is .mp3, output says .wav).
**Severity:** LOW — Most libraries handle format transparently

---

## Iteration 19 — [RECOVERY] GitHub Actions Scheduled Run Fails, No Manual Retry

**Actors:** GitHub Actions, scheduled-content.yml
**Precondition:** Daily scheduled run fails (e.g., pip install error)
**Trigger:** Run fails at 10 AM, next run is tomorrow at 10 AM
**Flow:**
1. Today's clips/quotes don't get posted
2. Tomorrow's run picks up today's pending slots (they're past due)
3. Two days' worth of content posted in one burst

**Expected outcome:** Missed slots should be posted on next successful run
**What could go wrong:** Posting 2+ days of accumulated content at once looks spammy (5-6 posts in rapid succession). No rate limiting or batching in the scheduled poster.
**Severity:** MEDIUM — Burst posting after outage could trigger rate limits or look spammy

---

## Iteration 20 — [EDGE_CASE] Clip Duration Exactly 60.0 Seconds

**Actors:** Pipeline, YouTubeUploader
**Precondition:** GPT-4o suggests a clip from 10:00 to 11:00 (exactly 60 seconds)
**Trigger:** Clip created and uploaded as YouTube Short
**Flow:**
1. AudioProcessor creates 60.0s clip
2. VideoConverter creates vertical video at 60.0s
3. YouTubeUploader.upload_short() uploads
4. YouTube Shorts limit is ≤60 seconds

**Expected outcome:** 60.0s should be accepted (≤ not <)
**What could go wrong:** FFmpeg might add a few milliseconds during encoding (muxing overhead), making it 60.05s — YouTube rejects as "too long for Short." Float precision: 60.0000001 seconds.
**Severity:** MEDIUM — Boundary condition on YouTube Shorts duration limit

---

## Iteration 21 — [INTEGRATION] OpenAI API Rate Limit During Analysis

**Actors:** Pipeline, ContentEditor, OpenAI API
**Precondition:** Heavy API usage or shared API key hitting rate limits
**Trigger:** GPT-4o returns 429 Too Many Requests during content analysis
**Flow:**
1. ContentEditor.analyze_content() calls OpenAI
2. OpenAI returns 429 with Retry-After header
3. Does ContentEditor have retry logic?

**Expected outcome:** Retry with backoff, eventually succeed
**What could go wrong:** If no retry logic, analysis fails, no clips/summary/social content generated. Pipeline continues but with empty analysis — all downstream steps produce garbage.
**Severity:** HIGH — Single point of failure with no retry for the most critical step

---

## Iteration 22 — [STATE_TRANSITION] Pipeline State Checkpoint Key Mismatch After Code Change

**Actors:** Developer, Pipeline, PipelineState
**Precondition:** Pipeline code updated — step names changed (e.g., "step_5_clips" renamed to "step_5_create_clips")
**Trigger:** User runs `--resume` on an episode that was partially processed with old code
**Flow:**
1. PipelineState loads old checkpoint file
2. Checks `is_step_completed("step_5_create_clips")` → False (old key was "step_5_clips")
3. Re-runs step 5 even though it already completed
4. Creates duplicate clips or overwrites existing ones

**Expected outcome:** Resume should detect step was already done under old name
**What could go wrong:** Step name changes break resume. No migration for old checkpoint files. Could re-process expensive steps unnecessarily.
**Severity:** LOW — Wastes time but doesn't corrupt data

---

## Iteration 23 — [TEMPORAL] YouTube Token Pickle Created on Windows, Used on Linux (GitHub Actions)

**Actors:** GitHub Actions, YouTubeUploader
**Precondition:** youtube_token.pickle created on Windows Python 3.12, base64-encoded to GitHub secret
**Trigger:** GitHub Actions (Linux Python 3.12) decodes and loads the pickle
**Flow:**
1. Workflow decodes base64 → credentials/youtube_token.pickle
2. YouTubeUploader loads pickle: `pickle.load(open(path, "rb"))`
3. Pickle contains google.oauth2.credentials.Credentials object

**Expected outcome:** Pickle loads successfully cross-platform
**What could go wrong:** Pickle is generally cross-platform for Python objects, but path separators stored in the credentials object could differ. If the credential object cached any Windows-specific paths, they'd fail on Linux.
**Severity:** LOW — google-auth Credentials don't store file paths in the pickle

---

## Iteration 24 — [ABUSE] Extremely Long Episode Title Overflows UI

**Actors:** User, Pipeline, all uploaders
**Precondition:** Episode title is 500+ characters
**Trigger:** Pipeline processes episode with very long title
**Flow:**
1. YouTube: max 100 chars for title — what happens to the excess?
2. Twitter: 280 char limit total, title + URL might not fit
3. Bluesky: 300 grapheme limit
4. Thumbnail: text wrapping at 84pt font, might overflow image bounds
5. File paths: folder name from title could exceed Windows 260-char path limit

**Expected outcome:** Each platform truncates appropriately
**What could go wrong:** YouTube title silently truncated (API might reject or truncate). Thumbnail text could overflow below the overlay zone into the logo area. Windows MAX_PATH exceeded if title is used in directory name.
**Severity:** MEDIUM — No consistent title length validation at pipeline entry

---

## Iteration 25 — [RECOVERY] Content Calendar JSON Corrupted

**Actors:** Pipeline, ContentCalendar, GitHub Actions
**Precondition:** content_calendar.json has a syntax error (e.g., trailing comma from manual edit)
**Trigger:** Any code that calls calendar.load_all()
**Flow:**
1. load_all() calls json.loads(path.read_text())
2. json.JSONDecodeError raised
3. Does load_all() catch this or crash?

**Expected outcome:** Graceful handling — return empty dict or log warning
**What could go wrong:** Unhandled JSONDecodeError crashes the pipeline or the GitHub Actions scheduled poster. All scheduled posting stops until someone manually fixes the JSON.
**Severity:** HIGH — Single corrupted file stops all automated posting
