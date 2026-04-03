# Content Calendar Edge Cases

**Date:** 2026-04-02
**Focus:** Edge cases in autonomous scheduling/posting
**Iterations:** 15

---

## 1. [EDGE_CASE] Slot scheduled_at is in the future but only by seconds
**Trigger:** GitHub Actions runs at 14:00:00 UTC, slot scheduled at 14:00:01 UTC
**What happens:** `scheduled <= now` is False — slot skipped. Next run is 24 hours later.
**Impact:** MEDIUM — slot posts 24 hours late because of 1-second timing gap
**Fix needed:** Add small grace window (e.g., `scheduled <= now + timedelta(minutes=5)`)

## 2. [EDGE_CASE] Multiple episodes have pending slots at same time
**Trigger:** Ep29 and ep30 both have clips due today (overlapping 2-week calendars)
**What happens:** `get_all_pending_slots()` returns slots from both episodes. `post_scheduled` iterates all. Both episodes' clips post back-to-back.
**Impact:** MEDIUM — Twitter/Bluesky get flooded with 4-6 posts in rapid succession from different episodes. Looks spammy.
**Fix needed:** Rate limiting between posts, or priority ordering (newest episode first)

## 3. [EDGE_CASE] Calendar JSON has episode with no slots key
**Trigger:** Manual calendar edit removes `"slots"` key from an episode entry
**What happens:** `ep_data.get("slots") or {}` returns empty dict — silently skipped. No error.
**Impact:** LOW — gracefully handled, but no warning that an episode has no scheduled content

## 4. [EDGE_CASE] Slot has platforms list but no uploaders available
**Trigger:** GitHub Actions secrets misconfigured — Twitter/Bluesky creds missing
**What happens:** `_init_uploaders()` returns empty dict. `post_scheduled` logs "No uploaders available" and returns empty list. No slots get posted. No slots get marked failed.
**Impact:** HIGH — slots stay "pending" forever, accumulating. When creds are fixed, ALL accumulated slots fire at once.

## 5. [EDGE_CASE] YouTube Short video was deleted between upload and scheduled public date
**Trigger:** User manually deletes a YouTube Short. Calendar still has the video_id.
**What happens:** `set_video_privacy(video_id, "public")` fails with HttpError 404. Error recorded. Slot marked as partial success (Twitter/Bluesky still post with a dead YouTube URL).
**Impact:** HIGH — Social posts promote a dead YouTube link. No validation that video still exists before promoting.

## 6. [EDGE_CASE] Same slot posted twice due to race between mark_uploaded and save
**Trigger:** Extremely unlikely but possible: process crashes between `_post_slot()` succeeding and `calendar.mark_slot_uploaded()` persisting
**What happens:** Slot stays "pending". Next run re-posts to Twitter/Bluesky (duplicate posts). YouTube privacy change is idempotent (already public), so no YouTube issue.
**Impact:** MEDIUM — duplicate social posts. The atomic save (tmp+replace) prevents partial writes, but the gap between posting and marking is real.

## 7. [EDGE_CASE] Quote card slot has no quote_text
**Trigger:** GPT-4o analysis returned `best_quotes: [{"quote": "", "timestamp": "00:05:00"}]`
**What happens:** `content.get("quote_text", "")` returns empty string. `text` in `_post_slot` is empty. Twitter gets `tweet_text = ""` — Twitter API rejects empty tweets (400 error).
**Impact:** MEDIUM — slot fails with unhelpful "empty text" error, gets retried 3 times, then stuck

## 8. [EDGE_CASE] Bluesky rate limit during burst posting
**Trigger:** 6+ posts in rapid succession (accumulated slots after outage)
**What happens:** Bluesky AT Protocol has undocumented rate limits (~30 actions/300s). After 5-6 rapid posts, API returns 429. Posts fail with rate limit error.
**Impact:** MEDIUM — remaining slots fail and enter retry queue. Next day's run tries again and probably succeeds.

## 9. [EDGE_CASE] Calendar file locked by another process during save
**Trigger:** User has content_calendar.json open in an editor, or antivirus is scanning it
**What happens:** `tmp_path.replace(self.calendar_path)` raises `PermissionError` on Windows. The tmp file persists, original file unchanged. Slot status not updated.
**Impact:** MEDIUM — posts succeed but calendar isn't updated. Next run re-posts (duplicates).

## 10. [EDGE_CASE] Workflow git push fails due to concurrent calendar edit
**Trigger:** User pushes a calendar change while GitHub Actions is running
**What happens:** Workflow step `git push` fails with "rejected — non-fast-forward". Calendar changes from the run (slot status updates) are lost.
**Impact:** HIGH — all slot status updates from this run vanish. Next run re-processes everything, causing duplicate posts.

## 11. [EDGE_CASE] Content calendar grows indefinitely
**Trigger:** After 50+ episodes, calendar JSON has 50 episode entries with 11 slots each = 550 slots
**What happens:** `get_all_pending_slots()` iterates all 550 slots every run. `load_all()` reads a large JSON file. Performance degrades slowly.
**Impact:** LOW — no crash, just slow. At 100+ episodes, should archive old entries.

## 12. [EDGE_CASE] Clip slot has youtube_video_id but video is set to "public" already
**Trigger:** User manually made the Short public via YouTube Studio before the scheduler ran
**What happens:** `set_video_privacy(video_id, "public")` succeeds (idempotent — setting public on an already-public video is fine). Twitter/Bluesky posts go out normally.
**Impact:** NONE — this edge case is handled correctly. No action needed.

## 13. [EDGE_CASE] Slot scheduled_at has timezone info but comparison uses naive datetime
**Trigger:** Someone manually adds `"scheduled_at": "2026-04-05T14:00:00-04:00"` (with timezone)
**What happens:** `datetime.fromisoformat()` parses it as timezone-aware. `datetime.now()` returns naive. Comparison `scheduled <= now` raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
**Impact:** CRITICAL — one bad timestamp crashes the entire posting run. All slots for all episodes fail.

## 14. [EDGE_CASE] GitHub Actions workflow runs but repo has no content_calendar.json
**Trigger:** Fresh clone, calendar hasn't been created yet (no episodes processed)
**What happens:** `calendar.load_all()` returns `{}`. `get_all_pending_slots()` returns empty list. `post_scheduled` logs "No pending slots" and exits cleanly.
**Impact:** NONE — handled correctly.

## 15. [EDGE_CASE] Twitter credits exhausted mid-posting session
**Trigger:** Pay-per-use credits run out after 2 tweets in a 5-slot posting session
**What happens:** First 2 slots succeed on Twitter. Slot 3 fails with 402 Payment Required. Remaining slots also fail on Twitter. YouTube/Bluesky continue working.
**Impact:** MEDIUM — partial platform failure per slot. Slots marked as uploaded (YouTube/Bluesky succeeded). Twitter portion lost for remaining slots with no indication to retry just Twitter.
