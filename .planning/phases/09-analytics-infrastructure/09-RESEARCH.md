# Phase 9: Analytics Infrastructure - Research

**Researched:** 2026-03-18
**Domain:** Python data persistence, YouTube Data API v3, Twitter API v2 (tweepy), uploader stub detection, hashtag injection
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Engagement history format:** Per-episode granularity, one entry per episode per analytics run
- **Metrics stored:** ALL available metrics (views, likes, comments, impressions, engagements, retweets) plus post_timestamp and episode topics
- **Retention policy:** Keep everything forever — no rolling window
- **Collection timing:** `python main.py analytics` command only, NOT during pipeline run
- **File location:** `topic_data/engagement_history.json`
- **Hashtag strategy:** AI-generated from `clip_hashtags` (existing GPT-4o output), top 2 per Twitter post, appended as separate line at tweet bottom, Twitter only
- **Stub detection behavior:** Log warning + skip: `[SKIP] Instagram: uploader not functional`. Detection at init time via `.functional` flag. Dry run shows: `[MOCK] Instagram: STUB (not functional)`
- **Video ID persistence:** Store in episode output JSON (`output/epN/`). Store ALL platform IDs: YouTube `video_id` + Twitter `tweet_id`. One-time backfill command `python main.py backfill-ids` for ep1-29 using YouTube search API. After backfill, analytics uses direct video ID lookups only.

### Claude's Discretion

- Exact `engagement_history.json` schema structure
- How to detect stub vs functional uploader (method signature check, config flag, or try/catch)
- Backfill command implementation details (batch size, rate limiting)
- Twitter free-tier `impression_count` null handling approach (null vs exclude from score)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLYT-01 | Video IDs stored at upload time for each platform (no search API calls needed for analytics) | YouTube uploader already returns `video_id` in upload result dict; Twitter uploader returns `tweet_id`; episode output JSON already written at end of pipeline; capture IDs there |
| ANLYT-02 | Twitter analytics handles missing impressions gracefully on free tier | Tweepy `public_metrics` returns `impression_count` as integer or absent on free tier; existing `fetch_twitter_analytics` uses `metrics.get("impression_count", 0)` which silently zeros it; need explicit null sentinel instead of 0 to distinguish "not reported" from "zero impressions" |
| ANLYT-03 | Engagement history accumulated in rolling JSON per episode (post time, platform, engagement metrics) | `topic_data/engagement_history.json` doesn't exist yet; `AnalyticsCollector` currently writes per-episode files to `topic_data/analytics/`; need a new accumulate-and-append flow that writes/updates the cross-episode history file |
| ANLYT-04 | Stub uploaders detected and flagged so scheduling/analytics skip non-functional platforms | Both `InstagramUploader.__init__` and `TikTokUploader.__init__` raise `ValueError` if credentials missing; currently these exceptions are caught in `_init_uploaders()` and the uploader is simply absent from the dict; need explicit `.functional = False` flag + warning logging |
| CONTENT-01 | Relevant hashtags auto-injected into Twitter posts (1-2 tags from curated list) | `clip_hashtags` already generated per clip in `content_editor.py`; `post_episode_announcement()` in `twitter_uploader.py` doesn't use them yet; need to thread `clip_hashtags` from analysis through `distribute.py` → `post_episode_announcement()` |
</phase_requirements>

## Summary

Phase 9 hardens the analytics data pipeline across five tightly scoped changes: (1) storing platform video/tweet IDs in the episode output JSON at upload time so analytics never needs a search API call, (2) accumulating per-episode metrics into a cross-episode `engagement_history.json` file, (3) making Twitter's free-tier impression_count absence visible as null rather than silently zero, (4) marking Instagram and TikTok uploaders as non-functional stubs with explicit flags so scheduler and analytics skip them cleanly, and (5) injecting the top 2 `clip_hashtags` from GPT-4o analysis into Twitter episode announcement posts.

The codebase is well-structured for all five changes. Every integration point is already identified and most require surgical edits to existing methods rather than new modules. The biggest new artifact is `engagement_history.json` — a simple append-to-list JSON file that accumulates across runs. No new libraries are needed. The backfill command (`python main.py backfill-ids`) is the only genuinely new CLI surface.

**Primary recommendation:** Work in a deliberate order — video ID capture first (ANLYT-01), then engagement history accumulation (ANLYT-03), then stub detection (ANLYT-04), then Twitter null guard (ANLYT-02), then hashtag injection (CONTENT-01). Each change is independent but ANLYT-01 unblocks the "no search API after backfill" goal.

## Standard Stack

### Core (already in use — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` (stdlib) | 3.12 | engagement_history.json read/write | No dependency, sufficient for the file sizes involved (~30 episodes/year) |
| `tweepy` | already in requirements.txt | Twitter API v2 tweet posting + analytics | Already used in `analytics.py` and `twitter_uploader.py` |
| `google-api-python-client` | already in requirements.txt | YouTube Data API v3 video stats lookup | Already used in `analytics.py` |
| `pathlib.Path` (stdlib) | 3.12 | File I/O patterns | Already the project convention throughout |

### No New Libraries Required

All five requirements are implementable with the existing stack. `pandas` (noted as potential transitive dep in STATE.md) is NOT needed — the engagement history is a plain JSON list, and Phase 10 is where correlation scoring happens.

**Installation:** None required.

## Architecture Patterns

### Recommended Project Structure (no new files needed except engagement_history.json)

```
analytics.py                     # extend: add append_to_engagement_history()
uploaders/twitter_uploader.py    # extend: post_episode_announcement() hashtag param
pipeline/steps/distribute.py     # extend: capture video_id/tweet_id, pass hashtags
pipeline/runner.py               # extend: run_analytics() + add backfill-ids command
main.py                          # extend: add backfill-ids CLI branch
topic_data/engagement_history.json  # NEW: created on first analytics run
```

### Pattern 1: Video ID Capture at Upload Time (ANLYT-01)

**What:** After `_upload_youtube()` and `_upload_twitter()` succeed in `distribute.py`, write the returned IDs into the episode output JSON.

**When to use:** At the end of `run_distribute()`, after social media uploads complete, before returning ctx.

**How the output JSON works:**

```python
# Source: output/ep_1/ contains "Episode #1 - CTE Can't Hurt Me_results.json"
# Keys already present: episode_number, original_audio, transcript, analysis,
# censored_audio_wav, censored_audio_mp3, clips, dropbox_transcription_path,
# dropbox_finished_path, dropbox_clip_paths, episode_summary, best_clips_info, censor_count
#
# PHASE 9 ADDS: platform_ids
{
  "platform_ids": {
    "youtube": "dQw4w9WgXcQ",     # from full episode upload result
    "twitter": "1234567890123456789"  # from post_episode_announcement result (first tweet)
  }
}
```

**Finding the output JSON in distribute.py:**
`distribute.py` doesn't currently write to the results JSON. The results JSON is written earlier in the pipeline. The correct approach is to write a separate `platform_ids.json` alongside the results JSON in `episode_output_dir`, or append to the existing results JSON. Given the CONTEXT.md decision to "store in episode output JSON", appending/merging into the existing `*_results.json` or writing a new `platform_ids.json` in `output/epN/` both satisfy the requirement. A dedicated `platform_ids.json` is simpler — no risk of corrupting existing results files.

**Twitter tweet_id extraction from thread result:**
`post_episode_announcement()` returns a list of dicts (one per tweet in thread). The tweet_id for the episode announcement is `result[0]["tweet_id"]` when `result` is not None.

### Pattern 2: Engagement History Accumulation (ANLYT-03)

**What:** After each analytics collection run, append/update a record in `topic_data/engagement_history.json`.

**Schema design (Claude's discretion):** A flat list of records — one per episode per collection run. Simple to query, simple to append. Phase 10 will read this file for correlation scoring.

```json
[
  {
    "episode_number": 29,
    "collected_at": "2026-03-18T14:30:00",
    "post_timestamp": "2026-03-16T18:19:32",
    "topics": ["CTE prevention", "workout safety"],
    "youtube": {
      "video_id": "dQw4w9WgXcQ",
      "views": 1500,
      "likes": 120,
      "comments": 30
    },
    "twitter": {
      "tweet_id": "1234567890123456789",
      "impressions": null,
      "engagements": 45,
      "retweets": 8,
      "likes": 37
    }
  }
]
```

**Key decisions embedded in schema:**
- `post_timestamp` comes from episode output JSON `collected_at` field (or file mtime as fallback)
- `topics` comes from `best_clips[*].suggested_title` in the analysis JSON (same as `correlate_topics()` already does)
- `youtube.video_id` and `twitter.tweet_id` come from `platform_ids.json` written during upload (ANLYT-01)
- `twitter.impressions` is `null` (Python `None`) when not returned by API, not `0`
- When re-running analytics for the same episode, UPDATE the existing record (match on `episode_number`) rather than appending a duplicate

**Implementation in analytics.py:**

```python
def append_to_engagement_history(self, episode_number: int, analytics_data: dict,
                                  platform_ids: dict, topics: list,
                                  post_timestamp: str) -> Path:
    """Append or update episode record in engagement_history.json."""
    history_path = Config.BASE_DIR / "topic_data" / "engagement_history.json"

    # Load existing or start fresh
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    # Build record
    yt = analytics_data.get("youtube") or {}
    tw = analytics_data.get("twitter") or {}
    record = {
        "episode_number": episode_number,
        "collected_at": datetime.now().isoformat(),
        "post_timestamp": post_timestamp,
        "topics": topics,
        "youtube": {
            "video_id": platform_ids.get("youtube"),
            "views": yt.get("views", 0),
            "likes": yt.get("likes", 0),
            "comments": yt.get("comments", 0),
        } if yt else None,
        "twitter": {
            "tweet_id": platform_ids.get("twitter"),
            "impressions": tw.get("impressions"),  # None if absent, not 0
            "engagements": tw.get("engagements", 0),
            "retweets": tw.get("retweets", 0),
            "likes": tw.get("likes", 0),
        } if tw else None,
    }

    # Update existing or append
    idx = next((i for i, r in enumerate(history)
                if r["episode_number"] == episode_number), None)
    if idx is not None:
        history[idx] = record
    else:
        history.append(record)

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    return history_path
```

### Pattern 3: Stub Uploader Detection (ANLYT-04)

**What:** Add a `.functional` boolean flag to Instagram and TikTok uploaders. Set it based on whether credentials are configured, without raising in `__init__`. The runner's `_init_uploaders()` logs a `[SKIP]` warning when functional is False.

**Current behavior:** `InstagramUploader.__init__` raises `ValueError` if `INSTAGRAM_ACCESS_TOKEN` is missing/placeholder. `TikTokUploader.__init__` raises `ValueError` if `TIKTOK_CLIENT_KEY` is missing/placeholder. Both exceptions are caught in `_init_uploaders()` and the uploader is simply absent from the dict.

**Revised approach:** The simplest change that satisfies ANLYT-04 without breaking existing behavior is to add a `functional` class-level attribute check at init time. There are two reasonable approaches:

Option A — Add `.functional` flag to uploader classes (recommended, cleanest):
```python
class InstagramUploader:
    def __init__(self):
        token = Config.INSTAGRAM_ACCESS_TOKEN
        account_id = Config.INSTAGRAM_ACCOUNT_ID
        self.functional = bool(
            token and token != "your_instagram_access_token_here"
            and account_id and account_id != "your_instagram_account_id_here"
        )
        if not self.functional:
            return  # Don't raise — let caller check .functional
        self.access_token = token
        self.account_id = account_id
```

Option B — Detect stub in `_init_uploaders()` via try/catch + explicit flag (no change to uploader classes):
```python
try:
    uploaders["instagram"] = InstagramUploader()
    uploaders["instagram"].functional = True
except ValueError as e:
    stub = object.__new__(InstagramUploader)
    stub.functional = False
    uploaders["instagram"] = stub
    logger.warning("[SKIP] Instagram: uploader not functional")
```

**Recommendation:** Option A — modify the uploader classes to not raise on missing credentials, instead setting `self.functional = False`. This is more testable and consistent with the `self.enabled` pattern used throughout the codebase. All methods should guard with `if not self.functional: return None`.

**Dry run output pattern** (matching CONTEXT.md spec):
```python
# In dry_run() in runner.py, replace:
#   platform_status.append(f"{name.capitalize()}: ready")
# With:
uploader = uploaders.get(name)
if uploader and not getattr(uploader, "functional", True):
    platform_status.append(f"{name.capitalize()}: STUB (not functional)")
else:
    platform_status.append(f"{name.capitalize()}: ready")
```

### Pattern 4: Twitter Impression Null Guard (ANLYT-02)

**What:** In `fetch_twitter_analytics()`, treat absent/zero `impression_count` as `None` rather than `0`.

**Current code (analytics.py line ~151):**
```python
total_impressions += metrics.get("impression_count", 0)
```

**Problem:** Twitter free-tier API returns `impression_count` as `0` or omits it entirely. Both cases produce `0`, which is indistinguishable from genuinely zero impressions. Phase 10's scoring formula must not divide by zero or treat null as a low score.

**Fix:** Track whether any tweet returned a non-zero impression_count. If all are zero/absent, return `None` for `impressions` field:
```python
# Replace the accumulation loop logic:
impression_data_available = False
for tweet in response.data:
    metrics = tweet.public_metrics or {}
    imp = metrics.get("impression_count")
    if imp is not None and imp > 0:
        impression_data_available = True
        total_impressions += imp
    # ... rest of metrics

return {
    "impressions": total_impressions if impression_data_available else None,
    "engagements": total_engagements,
    "retweets": total_retweets,
    "likes": total_likes,
}
```

**Impact on `calculate_engagement_score()`:** The existing scorer uses `tw.get("impressions", 0) * 0.0001`. When `impressions` is `None`, `None * 0.0001` raises `TypeError`. Must add null guard:
```python
tw_impressions = tw.get("impressions") or 0  # None becomes 0 for scoring
twitter_score = (
    tw_impressions * 0.0001
    + tw.get("engagements", 0) * 0.05
    + ...
)
```

### Pattern 5: Twitter Hashtag Injection (CONTENT-01)

**What:** Extract top 2 hashtags from `clip_hashtags` in the analysis dict and append them as a separate line at the bottom of the main episode announcement tweet.

**Data flow:**
1. `content_editor.py` generates `best_clips[*].clip_hashtags` (list of strings, no `#` prefix)
2. `distribute.py`'s `_upload_twitter()` calls `post_episode_announcement()`
3. `post_episode_announcement()` builds the main tweet text

**Extraction logic (in `_upload_twitter()`):**
```python
# Collect all clip_hashtags, deduplicate, take top 2
all_hashtags = []
for clip in best_clips:
    all_hashtags.extend(clip.get("clip_hashtags", []))
# Deduplicate preserving order
seen = set()
unique_hashtags = []
for tag in all_hashtags:
    if tag not in seen:
        seen.add(tag)
        unique_hashtags.append(tag)
top_hashtags = unique_hashtags[:2]
```

**Tweet format** (CONTEXT.md: "appended as separate line at bottom"):
```
[tweet body]

#hashtag1 #hashtag2
```

**Character budget:** Each hashtag is displayed via t.co (23 chars wrapped). The raw hashtag text is what counts for the 280-char limit. Two hashtags + `\n\n` + `#` prefixes = roughly `2 + len(tag1) + 1 + len(tag2)` chars beyond the newlines. Hashtags generated by GPT-4o are typically 6-15 chars. Budget is safe.

**Modified `post_episode_announcement()` signature:**
```python
def post_episode_announcement(
    self,
    episode_number: int,
    episode_summary: str,
    youtube_url: Optional[str] = None,
    spotify_url: Optional[str] = None,
    clip_youtube_urls: Optional[List[Dict[str, str]]] = None,
    twitter_caption: Optional[str] = None,
    hashtags: Optional[List[str]] = None,  # NEW parameter
) -> Optional[List[Dict[str, Any]]]:
```

Hashtag injection happens in the tweet-building block:
```python
if hashtags:
    hashtag_line = " ".join(f"#{tag}" for tag in hashtags[:2])
    # Append to main_tweet before 280-char trim
    main_tweet = f"{main_tweet}\n\n{hashtag_line}"
```

### Pattern 6: Backfill Command (ANLYT-01 support)

**What:** `python main.py backfill-ids` uses YouTube search API (one search per episode) to look up video IDs for ep1-29 and writes them to `platform_ids.json` in each episode output dir.

**YouTube search API quota cost:** Each `search.list` call costs 100 units. Daily quota is 10,000 units. 29 episodes = 2,900 units — safe in one run. No batching needed.

**Rate limiting:** Add 1-2 second sleep between requests to avoid hitting per-second limits.

```python
def run_backfill_ids():
    """One-time backfill: look up YouTube video IDs for existing episodes."""
    import time
    youtube = _build_youtube_client()  # existing pickle-based auth in analytics.py
    output_dir = Config.OUTPUT_DIR
    ep_dirs = sorted(output_dir.glob("ep_*"))

    for ep_dir in ep_dirs:
        match = re.search(r"ep_(\d+)", ep_dir.name)
        if not match:
            continue
        ep_num = int(match.group(1))

        platform_ids_path = ep_dir / "platform_ids.json"
        if platform_ids_path.exists():
            print(f"[SKIP] ep_{ep_num}: platform_ids.json already exists")
            continue

        # Search YouTube
        try:
            results = youtube.search().list(
                q=f"Episode #{ep_num}",
                channelId=os.getenv("YOUTUBE_CHANNEL_ID", ""),
                type="video", part="id", maxResults=1
            ).execute()
            items = results.get("items", [])
            video_id = items[0]["id"]["videoId"] if items else None
        except Exception as e:
            logger.warning("YouTube search failed for ep_%s: %s", ep_num, e)
            video_id = None

        platform_ids = {"youtube": video_id, "twitter": None}
        with open(platform_ids_path, "w", encoding="utf-8") as f:
            json.dump(platform_ids, f, indent=2)
        print(f"[OK] ep_{ep_num}: youtube={video_id}")
        time.sleep(1.5)  # Rate limiting
```

### Anti-Patterns to Avoid

- **Treating `impression_count=0` as real data:** Silently converts a free-tier limitation into an incorrect "zero impressions" signal that Phase 10's scoring would penalize. Use `None` as the sentinel.
- **Appending duplicate history records:** Running `python main.py analytics all` twice should update records, not duplicate them. Always upsert by `episode_number`.
- **Using YouTube search API in `fetch_youtube_analytics()` after backfill:** The whole point of ANLYT-01 is to eliminate search API calls post-backfill. The analytics path should read `platform_ids.json` first; fall back to search only if the file is absent.
- **Raising in stub uploader `__init__`:** The current raise-on-missing-credentials pattern prevents the scheduler from even instantiating the uploader to check its status. Adding `.functional = False` without raising is cleaner.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON persistence for engagement history | Custom database, SQLite, pandas DataFrame | Plain `json.load` / `json.dump` on a list | 30 episodes/year keeps file under 50KB; stdlib is sufficient; Phase 10 reads it as a list |
| YouTube auth management | Token refresh code | Existing pickle-based auth already in `analytics.py` (`fetch_youtube_analytics`) | Already handles expired token refresh via `google.auth.transport.requests.Request` |
| Twitter rate limiting | Custom backoff | `retry_with_backoff` decorator already in `retry_utils.py` | Already used in `twitter_uploader.py` |
| Hashtag deduplication | Custom trie | `dict.fromkeys()` or seen-set pattern | Simple, no library needed |

**Key insight:** Every infrastructure piece is already in the codebase. This phase is wiring and hardening, not building new systems.

## Common Pitfalls

### Pitfall 1: YouTube Search API Cost on Every Analytics Run

**What goes wrong:** The current `fetch_youtube_analytics()` calls `search().list()` every time analytics runs. With 29+ episodes and `python main.py analytics all`, that's 29 × 100 = 2,900 quota units per run. Daily limit is 10,000 units — safe for now, but will eventually exhaust quota once episode count grows or if analytics is run multiple times per day.

**Why it happens:** The original analytics.py was written before video IDs were persisted at upload time.

**How to avoid:** After ANLYT-01 lands, modify `fetch_youtube_analytics()` to accept an optional `video_id` parameter. If provided, skip `search()` and go directly to `videos().list(id=video_id)` (cost: 1 unit, not 100). Load video_id from `platform_ids.json` in the analytics runner.

**Warning signs:** Running `python main.py analytics all` multiple times in one day and seeing YouTube API quota errors.

### Pitfall 2: Existing Tests Break on impression_count=None

**What goes wrong:** `test_analytics.py::TestCalculateEngagementScore` tests pass `"impressions": 5000` directly. After adding null guard to `calculate_engagement_score()`, tests still pass. But the `TestFetchTwitterAnalytics::test_fetch_twitter_success` test asserts `result["impressions"] == 5000` — this passes because the mock tweet has a nonzero `impression_count`. The test for null handling needs to be added.

**How to avoid:** Add a test case with `impression_count=0` and `impression_count=None` returning `None` for impressions. Add a test for `calculate_engagement_score()` where `tw["impressions"] = None` doesn't raise `TypeError`.

### Pitfall 3: Old Episode Output JSON Format Varies

**What goes wrong:** Episodes 1-28 were processed before the current pipeline refactor. Their output dirs contain `*_results.json` files with different key structures. Some have `*_analysis.json` separately. The backfill command iterates `output/ep_*` — it must not assume any particular analysis JSON filename pattern.

**How to avoid:** The backfill command writes a NEW `platform_ids.json` file rather than modifying existing result files. Similarly, `_upload_twitter()` and `_upload_youtube()` should write `platform_ids.json` as a new file in `episode_output_dir`, not modify the existing results JSON (which was written much earlier in the pipeline and isn't easily accessible from `run_distribute()`).

### Pitfall 4: Twitter Thread Returns List, Not Single Dict

**What goes wrong:** `post_episode_announcement()` returns `Optional[List[Dict]]` (a list of tweet dicts, one per thread post). Capturing the `tweet_id` requires `result[0]["tweet_id"]` — but `result` can be None if posting fails, or can be an empty list.

**How to avoid:** Guard carefully:
```python
twitter_result = uploaders["twitter"].post_episode_announcement(...)
tweet_id = None
if twitter_result and len(twitter_result) > 0:
    tweet_id = twitter_result[0].get("tweet_id")
```

### Pitfall 5: YouTube OAuth Scope May Not Cover yt-analytics.readonly

**What goes wrong:** STATE.md documents this concern: "YouTube Analytics API v2 OAuth scope (`yt-analytics.readonly`) may not be in existing credentials". However, Phase 9 uses the YouTube DATA API v3 (not the Analytics API v2) for video statistics. `videos().list(part="statistics")` only needs `youtube.readonly` scope, which is almost certainly already in the existing pickle token.

**How to avoid:** Verify with `python -c "import pickle; c=pickle.load(open('credentials/youtube_token.pickle','rb')); print(c.scopes)"` before planning any OAuth re-auth. If only DATA API v3 stats are needed (views, likes, comments), existing credentials should work.

### Pitfall 6: engagement_history.json Race Condition on Concurrent Writes

**What goes wrong:** `python main.py analytics all` iterates episodes sequentially — no concurrency. Not a real risk in this codebase. But if the file grows and two processes run simultaneously (e.g., scheduled job + manual run), they could corrupt the file.

**How to avoid:** Not worth handling now. The CLI is run-and-exit, sequential. Document as known limitation; revisit if scheduled daemon is ever added.

## Code Examples

Verified patterns from existing codebase:

### Loading platform_ids.json for analytics lookup

```python
# Source: pattern derived from output dir structure (output/ep_N/ directory scan)
def _load_platform_ids(episode_number: int) -> dict:
    """Load stored platform IDs for an episode, or return empty dict."""
    platform_ids_path = Config.OUTPUT_DIR / f"ep_{episode_number}" / "platform_ids.json"
    if platform_ids_path.exists():
        with open(platform_ids_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
```

### Writing platform_ids.json after upload

```python
# Source: distribute.py run_distribute() — after social media results
platform_ids = {}
if youtube_results:
    full_ep = youtube_results.get("full_episode") or {}
    if full_ep.get("video_id"):
        platform_ids["youtube"] = full_ep["video_id"]
if twitter_results and isinstance(twitter_results, list) and twitter_results:
    if twitter_results[0].get("tweet_id"):
        platform_ids["twitter"] = twitter_results[0]["tweet_id"]
if platform_ids:
    platform_ids_path = episode_output_dir / "platform_ids.json"
    with open(platform_ids_path, "w", encoding="utf-8") as f:
        json.dump(platform_ids, f, indent=2)
```

### Uploader stub detection (.functional flag)

```python
# Source: pattern matches self.enabled convention from config.py-gated modules
class InstagramUploader:
    def __init__(self):
        token = Config.INSTAGRAM_ACCESS_TOKEN
        account_id = Config.INSTAGRAM_ACCOUNT_ID
        self.functional = (
            bool(token) and token != "your_instagram_access_token_here"
            and bool(account_id) and account_id != "your_instagram_account_id_here"
        )
        if not self.functional:
            return  # Skip credential assignment — uploader won't be called
        self.access_token = token
        self.account_id = account_id
```

### Hashtag injection into tweet

```python
# Source: twitter_uploader.py post_episode_announcement(), new parameter
if hashtags:
    hashtag_line = " ".join(f"#{tag}" for tag in hashtags[:2])
    # Compute space needed: \n\n + hashtag_line length
    hashtag_addition = f"\n\n{hashtag_line}"
    if len(main_tweet) + len(hashtag_addition) <= 280:
        main_tweet = main_tweet + hashtag_addition
    else:
        # Trim main_tweet to fit hashtags
        max_len = 280 - len(hashtag_addition)
        main_tweet = main_tweet[:max_len] + hashtag_addition
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| YouTube search on every analytics run | Direct video ID lookup (after backfill) | Phase 9 | 100x quota reduction per analytics run |
| No engagement history file | `topic_data/engagement_history.json` | Phase 9 | Enables Phase 10 correlation scoring |
| Impression silently zero on free tier | `null` sentinel | Phase 9 | Prevents Phase 10 from scoring null data as "zero engagement" |
| Instagram/TikTok raise on missing creds | `.functional = False` flag | Phase 9 | Cleaner stub detection, no try/catch in caller |

**Deprecated/outdated patterns to replace in this phase:**
- `fetch_youtube_analytics()` doing `search().list()` always — replace with ID-first lookup
- `metrics.get("impression_count", 0)` — replace with null-aware logic
- Implicit stub detection via absent dict key — replace with explicit `.functional` flag

## Open Questions

1. **YouTube credentials scope verification**
   - What we know: STATE.md flags that `yt-analytics.readonly` scope may be missing. But Phase 9 only needs `youtube.readonly` (Data API v3 statistics), not the Analytics API v2.
   - What's unclear: Whether existing `youtube_token.pickle` has the right scopes without re-auth.
   - Recommendation: Wave 0 task should verify scope by running `python -c "import pickle; c=pickle.load(open('credentials/youtube_token.pickle','rb')); print(c.scopes)"`. If `youtube.readonly` or `https://www.googleapis.com/auth/youtube` is present, no re-auth needed.

2. **TikTok app audit status**
   - What we know: STATE.md notes "TikTok Content Posting API requires app audit approval — confirm status; exclude TikTok from scheduling if unaudited."
   - What's unclear: Current audit status.
   - Recommendation: For Phase 9, TikTok is treated as a stub (ANLYT-04). Audit status affects future phases, not this one.

3. **How to extract post_timestamp for engagement_history.json**
   - What we know: `platform_ids.json` won't contain upload time. The episode results JSON has a `collected_at`-like structure but the file naming uses timestamps (e.g., `ep_29_raw_20260316_181932_analysis.json`).
   - What's unclear: Whether a reliable upload timestamp is persisted anywhere.
   - Recommendation: Use file mtime of `platform_ids.json` as the post_timestamp (written at upload time). This is accurate to within seconds and requires no new data.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, all 364+ tests passing) |
| Config file | none — pytest auto-discovers |
| Quick run command | `pytest tests/test_analytics.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLYT-01 | platform_ids.json written after upload | unit | `pytest tests/test_distribute.py -k "platform_ids" -x` | ❌ Wave 0 — need test additions to test_distribute.py or new test file |
| ANLYT-01 | fetch_youtube_analytics uses video_id param if provided, skips search | unit | `pytest tests/test_analytics.py -k "video_id" -x` | ❌ Wave 0 |
| ANLYT-02 | fetch_twitter_analytics returns None for impressions when impression_count=0/absent | unit | `pytest tests/test_analytics.py -k "impression" -x` | ❌ Wave 0 |
| ANLYT-02 | calculate_engagement_score handles None impressions without TypeError | unit | `pytest tests/test_analytics.py -k "null_impression" -x` | ❌ Wave 0 |
| ANLYT-03 | append_to_engagement_history writes correct schema | unit | `pytest tests/test_analytics.py -k "engagement_history" -x` | ❌ Wave 0 |
| ANLYT-03 | append_to_engagement_history upserts on same episode_number | unit | `pytest tests/test_analytics.py -k "upsert" -x` | ❌ Wave 0 |
| ANLYT-04 | InstagramUploader.functional = False when credentials absent | unit | `pytest tests/test_instagram_uploader.py -k "functional" -x` | ❌ Wave 0 |
| ANLYT-04 | TikTokUploader.functional = False when credentials absent | unit | `pytest tests/test_tiktok_uploader.py -k "functional" -x` | ❌ Wave 0 |
| CONTENT-01 | post_episode_announcement injects top-2 hashtags as final line | unit | `pytest tests/test_twitter_uploader.py -k "hashtag" -x` | ❌ Wave 0 |
| CONTENT-01 | hashtags trimmed to 2 from clip_hashtags list | unit | `pytest tests/test_twitter_uploader.py -k "hashtag" -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_analytics.py tests/test_twitter_uploader.py tests/test_instagram_uploader.py tests/test_tiktok_uploader.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] New test methods in `tests/test_analytics.py` — ANLYT-01 video_id param, ANLYT-02 null impressions, ANLYT-03 engagement_history upsert
- [ ] New test methods in `tests/test_twitter_uploader.py` — CONTENT-01 hashtag injection
- [ ] New test methods in `tests/test_instagram_uploader.py` — ANLYT-04 `.functional` flag
- [ ] New test methods in `tests/test_tiktok_uploader.py` — ANLYT-04 `.functional` flag
- [ ] Tests for `distribute.py` platform_ids capture — either extend `tests/test_pipeline_refactor.py` or add `tests/test_distribute.py`

No new test framework or fixture infrastructure needed — existing `tmp_path`, `patch`, and `MagicMock` patterns cover all new behaviors.

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `analytics.py` — full source read; `AnalyticsCollector`, `TopicEngagementScorer` methods, auth patterns
- Direct code inspection: `uploaders/twitter_uploader.py` — `post_episode_announcement()`, `post_tweet()`, return types
- Direct code inspection: `uploaders/instagram_uploader.py` — credential check, `__init__` raise behavior
- Direct code inspection: `uploaders/tiktok_uploader.py` — credential check, `__init__` raise behavior
- Direct code inspection: `pipeline/steps/distribute.py` — `_upload_youtube()`, `_upload_twitter()`, return shapes
- Direct code inspection: `pipeline/runner.py` — `_init_uploaders()`, `run_analytics()`, `dry_run()`
- Direct code inspection: `tests/test_analytics.py` — existing test coverage baseline
- Direct code inspection: `output/ep_1/` and `output/ep_29/` — actual output file structure on disk
- Direct code inspection: `topic_data/` — existing JSON files, directory structure

### Secondary (MEDIUM confidence)

- `.planning/phases/09-analytics-infrastructure/09-CONTEXT.md` — locked decisions from user discussion
- `.planning/STATE.md` — documented concerns: YouTube OAuth scope, TikTok audit status, pandas transitive dep
- `.planning/REQUIREMENTS.md` — requirement definitions for ANLYT-01 through ANLYT-04, CONTENT-01

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, verified in source
- Architecture: HIGH — all integration points located in source code
- Pitfalls: HIGH — derived from actual code inspection of raise behavior, API patterns, and test coverage
- Schema design: MEDIUM — engagement_history.json schema is Claude's discretion per CONTEXT.md; schema proposed is reasonable but planner may adjust

**Research date:** 2026-03-18
**Valid until:** 2026-04-17 (stable domain; YouTube/Twitter APIs change infrequently)
