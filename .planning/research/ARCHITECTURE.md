# Architecture Research

**Domain:** Engagement optimization and smart scheduling — v1.2 integration into existing pipeline
**Researched:** 2026-03-18
**Confidence:** HIGH — based on direct code inspection of all relevant existing modules

---

## Current Architecture (as-built, v1.1)

```
main.py (134-line CLI shim)
    |
pipeline/runner.py (orchestrator, component factory, checkpoint logic)
    |
    +---> pipeline/context.py (PipelineContext dataclass)
    |
    +---> pipeline/steps/ingest.py     (Step 1: download)
    +---> pipeline/steps/analysis.py   (Steps 3-3.5: AI analysis + topic tracker)
    +---> pipeline/steps/audio.py      (stub — Steps 4-6 still inline in runner.py)
    +---> pipeline/steps/video.py      (Steps 5.1-5.6: clips, subs, video, thumb)
    +---> pipeline/steps/distribute.py (Steps 7-9: Dropbox, RSS, social, blog, search)
```

Key facts about existing engagement/scheduling modules:

- `analytics.py` — `AnalyticsCollector` fetches YouTube (views/likes/comments) and Twitter (impressions/engagements) per episode. Saves to `topic_data/analytics/ep_N_analytics.json`. Run via `python main.py analytics epN`.
- `scheduler.py` — `UploadScheduler` creates `upload_schedule.json` with platform entries at `now + SCHEDULE_X_DELAY_HOURS`. Fixed offset only — no awareness of audience activity patterns.
- `topic_scorer.py` — `TopicScorer` via Ollama; already reads `get_engagement_bonus()` from analytics as a weak signal.
- `audio_clip_scorer.py` — `AudioClipScorer` scores segments by RMS energy; feeds into GPT-4o clip selection in `content_editor.py`.
- `pipeline/steps/analysis.py` — already injects `topic_context` (scored topics from `topic_data/`) into AI analysis prompt. This is the pattern for feeding external data into clip selection.

---

## System Overview: v1.2 Additions

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EXISTING PIPELINE (v1.1)                         │
│  main.py → pipeline/runner.py → pipeline/steps/                     │
│                                                                      │
│  Step 3: analysis.py                  Step 8: distribute.py          │
│    reads topic_context (existing)       calls scheduler.create_      │
│    ← [NEW] engagement_profile          schedule() (existing)         │
│                                         ← [NEW] optimizer param      │
├─────────────────────────────────────────────────────────────────────┤
│                    NEW v1.2 MODULES                                  │
│  ┌──────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  engagement_scorer.py│  │  posting_time_optimizer.py          │  │
│  │  - get_engagement_   │  │  - suggest_time(platform) → dt|None │  │
│  │    profile() → dict  │  │  - reads engagement_history.json    │  │
│  │  - record_outcome()  │  │  - fallback: None if < min_episodes │  │
│  └──────────┬───────────┘  └───────────────┬─────────────────────┘  │
│             │                              │                         │
│             ↓   writes                     ↓   reads                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │   topic_data/engagement_history.json                         │   │
│  │   { "episodes": [ { platform: { posted_at, hour_utc,        │   │
│  │     day_of_week, engagement_score }, ... } ] }               │   │
│  └──────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│               MODIFIED EXISTING MODULES                              │
│  analytics.py    — add posted_at capture; record_outcome() hook     │
│  scheduler.py    — add get_optimal_publish_at(platform, optimizer)  │
│  pipeline/context.py — add engagement_profile: Optional[dict] field │
│  pipeline/steps/analysis.py  — load and attach engagement_profile  │
│  pipeline/steps/distribute.py — pass optimizer to create_schedule() │
│  pipeline/runner.py — init new components in _init_components()     │
│  config.py       — SMART_SCHEDULING_ENABLED, MIN_EPISODES env vars  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Project Structure

```
podcast-automation/
├── analytics.py                       # MODIFIED: add posted_at capture
├── scheduler.py                       # MODIFIED: add get_optimal_publish_at()
├── posting_time_optimizer.py          # NEW: optimal posting window logic
├── engagement_scorer.py               # NEW: clip/episode engagement prediction
├── config.py                          # MODIFIED: two new env vars
├── pipeline/
│   ├── context.py                     # MODIFIED: add engagement_profile field
│   └── steps/
│       ├── analysis.py                # MODIFIED: inject engagement_profile
│       └── distribute.py             # MODIFIED: pass optimizer to scheduler
├── topic_data/
│   ├── analytics/
│   │   └── ep_N_analytics.json        # EXISTING: per-episode metrics files
│   └── engagement_history.json        # NEW: cross-episode posting time outcomes
└── tests/
    ├── test_posting_time_optimizer.py  # NEW
    └── test_engagement_scorer.py       # NEW
```

### Structure Rationale

- **Flat module structure** — matches existing project convention; every top-level `.py` module is a peer.
- **`topic_data/engagement_history.json`** — co-located with existing analytics data (`topic_data/analytics/`). Consistent discovery pattern with `scored_topics_*.json` and the analytics dir.
- **Two new modules, not one** — `posting_time_optimizer.py` owns the "when to post" problem; `engagement_scorer.py` owns the "what content scores well" prediction. Separate concerns, separately testable.
- **No new pipeline step** — both new modules are injected into existing steps (analysis and distribute) via the established component pattern, not added as numbered pipeline steps.

---

## Architectural Patterns

### Pattern 1: Engagement History as Rolling JSON File

**What:** A single `topic_data/engagement_history.json` accumulates one entry per episode per platform. `EngagementScorer.record_outcome()` appends to it after `run_analytics()`. Both new modules read it.

**When to use:** Every time `python main.py analytics epN` runs, ~48h after a new episode goes live.

**Trade-offs:** Zero new dependencies, trivial to inspect/debug. Scales to ~100 episodes without performance concern. Does not block if missing — both consumers return `None` gracefully.

```python
# engagement_history.json schema
{
  "episodes": [
    {
      "episode_number": 29,
      "recorded_at": "2026-03-10T14:00:00",
      "youtube": {
        "posted_at": "2026-03-05T10:00:00",
        "posted_hour_utc": 10,
        "posted_day_of_week": 2,          # 0=Mon, 6=Sun
        "engagement_score": 6.4,
        "views": 312,
        "likes": 28
      },
      "twitter": {
        "posted_at": "2026-03-05T11:00:00",
        "posted_hour_utc": 11,
        "posted_day_of_week": 2,
        "engagement_score": 3.1,
        "impressions": 820,
        "engagements": 34
      }
    }
  ]
}
```

Write pattern: atomic `.tmp` then rename — matches existing `scheduler.py` approach to avoid partial-read corruption.

### Pattern 2: Engagement Profile Injected into AI Clip Selection

**What:** `EngagementScorer.get_engagement_profile()` summarizes which topic categories and keywords historically outperform. This dict is attached to `ctx.engagement_profile` by `pipeline/steps/analysis.py` and then passed into `ContentEditor.analyze()` alongside `topic_context` — the same injection point that already exists for scored topics.

**When to use:** Step 3, before GPT-4o clip selection. Falls back to empty dict (no behavioral change) if `engagement_history.json` does not exist yet.

```python
# engagement_scorer.py — what get_engagement_profile() returns
{
  "high_performing_categories": ["shocking_news", "absurd_hypothetical"],
  "high_performing_keywords": ["cheese", "airplane", "diarrhea"],
  "avg_score_by_category": {"shocking_news": 7.2, "dating_social": 4.1},
  "episodes_analyzed": 8,
  "confidence": "medium"   # "low" if < 3 episodes; "none" if no data
}
```

**Trade-offs:** Augments existing `audio_energy_score` + AI scoring without replacing either. No new API calls.

### Pattern 3: Smart Schedule as an Optional Extension to `UploadScheduler`

**What:** Add `get_optimal_publish_at(platform, optimizer)` method to `UploadScheduler`. `create_schedule()` gains an optional `optimizer=None` parameter. When optimizer is present and has enough data, it returns an optimal datetime; otherwise the existing fixed-offset logic runs unchanged.

**When to use:** Called from `_upload_to_social_media()` in `distribute.py`.

**Trade-offs:** Fully backward compatible — `create_schedule()` without optimizer arg behaves exactly as v1.1. `run_upload_scheduled()` and `run_distribute_only()` need no changes.

```python
# scheduler.py addition
def get_optimal_publish_at(self, platform: str, optimizer) -> Optional[str]:
    """Return optimal datetime ISO string if optimizer has sufficient data."""
    if optimizer is None:
        return None
    optimal_dt = optimizer.suggest_time(platform)
    if optimal_dt:
        return optimal_dt.isoformat()
    # Fall back to existing fixed-delay logic
    if platform == "youtube" and self.youtube_delay > 0:
        return (datetime.now() + timedelta(hours=self.youtube_delay)).isoformat()
    return None
```

### Pattern 4: Confidence-Gated Optimization

**What:** `PostingTimeOptimizer.suggest_time(platform)` returns `None` unless at least `ENGAGEMENT_HISTORY_MIN_EPISODES` (default: 5) valid data points exist for that platform. Below the threshold, the optimizer steps aside and fixed offsets apply.

**Why:** With fewer than 5 episodes, the "best hour" computed from 2 data points is noise, not signal. Reporting false confidence leads to suboptimal schedules.

**Threshold exposed in `config.py`:**
```python
ENGAGEMENT_HISTORY_MIN_EPISODES = int(os.getenv("ENGAGEMENT_HISTORY_MIN_EPISODES", "5"))
```

---

## Data Flow

### Engagement Feedback Loop (Cross-Episode, Asynchronous)

```
Episode N uploaded
    |
    | (~48h later)
    v
python main.py analytics epN
    |
    +-- AnalyticsCollector.collect_analytics(N)
    |       reads: YouTube API, Twitter API
    |       saves: topic_data/analytics/ep_N_analytics.json (existing)
    |
    +-- EngagementScorer.record_outcome(N)
            reads: upload_schedule.json → posted_at timestamps
            reads: ep_N_analytics.json → engagement scores
            writes: topic_data/engagement_history.json (append)
```

### Episode Processing Data Flow (v1.2 additions in brackets)

```
run_ingest()
    |
_run_transcribe()
    |
run_analysis()
    |-- _load_scored_topics()                       [existing]
    |-- [EngagementScorer.get_engagement_profile()] [NEW]
    |       reads: engagement_history.json
    |       returns: dict or None
    |--> ctx.engagement_profile = profile           [NEW field]
    |--> ContentEditor.analyze(transcript, topic_context, engagement_profile)
    |--> ctx.analysis (best_clips, topics, etc.)
    |
run_video()
    |
run_distribute()
    |-- [PostingTimeOptimizer.suggest_time(platform)] [NEW]
    |       reads: engagement_history.json
    |       returns: datetime or None
    |--> scheduler.get_optimal_publish_at(platform, optimizer)
    |--> scheduler.create_schedule(...) with smart timestamps
    |--> upload_schedule.json (with optimal or fallback times)
    |--> platform uploads
```

### Key Data Flows

1. **Clip selection bias:** `engagement_history.json` → `EngagementScorer.get_engagement_profile()` → `ctx.engagement_profile` → injected into `content_editor.py` GPT-4o prompt → influences `best_clips` ranking toward historically high-performing categories.

2. **Smart posting time:** `engagement_history.json` → `PostingTimeOptimizer.suggest_time(platform)` → `scheduler.get_optimal_publish_at()` → replaces `now + delay_hours` in platform schedule entries → `upload_schedule.json`.

3. **Analytics feedback collection:** `run_analytics()` call → `AnalyticsCollector` fetches metrics → `EngagementScorer.record_outcome()` reads `upload_schedule.json` for `posted_at` → appends to `engagement_history.json`.

---

## Integration Points

### New Modules

| Module | Integrates With | Direction |
|--------|-----------------|-----------|
| `posting_time_optimizer.py` | `scheduler.py` via `get_optimal_publish_at()` | optimizer → scheduler |
| `posting_time_optimizer.py` | `topic_data/engagement_history.json` | optimizer reads file |
| `engagement_scorer.py` | `topic_data/analytics/ep_N_analytics.json` | scorer reads files |
| `engagement_scorer.py` | `topic_data/engagement_history.json` | scorer writes file |
| `engagement_scorer.py` | `pipeline/steps/analysis.py` | scorer returns profile dict |

### Modified Existing Modules

| Module | Change | Risk |
|--------|--------|------|
| `analytics.py` | `run_analytics()` calls `EngagementScorer.record_outcome()` after collecting; no change to `AnalyticsCollector` class interface | LOW — additive only |
| `scheduler.py` | Add `get_optimal_publish_at(platform, optimizer)` method; `create_schedule()` gains optional `optimizer=None` param | LOW — backward compatible; existing callers unaffected |
| `pipeline/context.py` | Add `engagement_profile: Optional[dict] = None` field | MINIMAL — dataclass field with default, no callers break |
| `pipeline/steps/analysis.py` | Initialize `EngagementScorer`, call `get_engagement_profile()`, assign to `ctx.engagement_profile`; pass to `ContentEditor.analyze()` | LOW — mirrors existing `topic_context` injection |
| `pipeline/steps/distribute.py` | In `_upload_to_social_media()`, pass optimizer from components to `scheduler.create_schedule()` | LOW — optional param, existing behavior preserved when optimizer absent |
| `pipeline/runner.py` | Initialize `EngagementScorer` and `PostingTimeOptimizer` in `_init_components()` (both full and dry-run branches); add to components dict | LOW — standard pattern, matches every other component |
| `config.py` | Add `SMART_SCHEDULING_ENABLED` and `ENGAGEMENT_HISTORY_MIN_EPISODES` env vars | MINIMAL |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `EngagementScorer` ↔ `analysis step` | `get_engagement_profile()` returns dict or None | None = no history yet; callers treat None as "no signal" |
| `PostingTimeOptimizer` ↔ `scheduler` | `suggest_time(platform)` returns datetime or None | None = insufficient data; scheduler uses fixed offset |
| Both new modules ↔ `engagement_history.json` | JSON file read/write; atomic `.tmp` rename on write | Matches scheduler.py's existing safe-write pattern |
| `EngagementScorer.record_outcome()` ↔ `upload_schedule.json` | Reads episode's schedule file to extract `posted_at` timestamps | File may not exist (episode had no schedule); graceful skip |
| New components ↔ `pipeline/runner.py` | Components dict key: `"engagement_scorer"`, `"posting_time_optimizer"` | Same pattern as all 15+ existing components |

---

## Build Order (Dependency-Driven)

```
Phase A (foundation — no dependencies on other new code):
  1. engagement_history.json schema definition (documented, no code yet)
  2. engagement_scorer.py
     - get_engagement_profile() reads history, returns dict or None
     - record_outcome() reads analytics files + schedule, appends to history
     - Standalone, fully testable without pipeline integration
  3. tests/test_engagement_scorer.py

Phase B (optimizer — depends on history schema from Phase A):
  4. posting_time_optimizer.py
     - suggest_time(platform) reads history, returns datetime or None
     - Confidence gate: returns None if < MIN_EPISODES data points
     - Standalone, testable with mock history files
  5. tests/test_posting_time_optimizer.py

Phase C (scheduler extension — depends on optimizer from Phase B):
  6. scheduler.py — add get_optimal_publish_at(platform, optimizer)
     - Tested via existing test_scheduler.py + new optimizer-passing test cases

Phase D (pipeline wiring — depends on Phases A, B, C):
  7. pipeline/context.py — add engagement_profile field
  8. pipeline/steps/analysis.py — inject engagement_profile from scorer
  9. pipeline/steps/distribute.py — pass optimizer to scheduler
  10. pipeline/runner.py — initialize both new components in _init_components()
  11. config.py — add env vars
  12. analytics.py — call record_outcome() from run_analytics()
```

Phases A and B are independent of each other's code (both depend only on the schema). They can be developed in parallel.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 10-50 episodes | JSON file adequate; simple moving average for time optimization |
| 50-200 episodes | Cap history at last 104 episodes (2 years) — trivial JSON trim in `record_outcome()` |
| 200+ episodes | Migrate `engagement_history.json` to SQLite; `search_index.py` already uses SQLite (FTS5), same dependency |

### Scaling Priorities

1. **First bottleneck:** `engagement_history.json` grows unbounded. Fix: `record_outcome()` trims to last N=104 entries on every write. One-line list slice.
2. **Second bottleneck:** YouTube Data API quota for analytics. Fix: cache raw API responses in `ep_N_analytics.json` (already done). Only re-fetch if `collected_at` is >24h old.

---

## Anti-Patterns

### Anti-Pattern 1: Blocking the Pipeline on Analytics Availability

**What people do:** Make clip selection or schedule creation raise an error if `engagement_history.json` is missing.
**Why it's wrong:** New installs have zero history. `python main.py ep30` must work from day one.
**Do this instead:** Every new function returns `None` or `{}` when data is absent. Callers treat `None` as "no signal, use defaults." This is already the pattern in `TopicEngagementScorer.get_engagement_bonus()` — returns `None` if no analytics file exists.

### Anti-Pattern 2: Writing Engagement History During the Main Pipeline Run

**What people do:** Call `EngagementScorer.record_outcome()` at the end of `run_distribute()` (Step 9).
**Why it's wrong:** At upload time, engagement metrics do not exist — the episode was just published. The outcome (views, likes, engagement score) is only knowable 24-48h later.
**Do this instead:** `record_outcome()` runs only from `run_analytics()`, which is a separate CLI command invoked manually after the episode has been live for a day.

### Anti-Pattern 3: Replacing `scheduler.py` Rather Than Extending It

**What people do:** Rewrite `create_schedule()` to require an optimizer, changing its mandatory signature.
**Why it's wrong:** `run_upload_scheduled()` and `run_distribute_only()` call `create_schedule()` without any optimizer context. Breaking the signature breaks resume-only distribution runs.
**Do this instead:** `create_schedule()` gains `optimizer=None` as an optional parameter. When `None`, existing behavior is byte-for-byte identical. The new `get_optimal_publish_at()` is a separate method that callers opt into.

### Anti-Pattern 4: False Confidence from Small Samples

**What people do:** Compute "best posting hour" from 2 episodes and report it as an actionable recommendation.
**Why it's wrong:** With N<5, the computed optimum is indistinguishable from chance. The optimizer will confidently schedule at a suboptimal time.
**Do this instead:** `suggest_time()` returns `None` unless `ENGAGEMENT_HISTORY_MIN_EPISODES` (default 5) valid data points exist for that platform. Log a clear message: "Insufficient history for platform X (N episodes) — using fixed offset."

### Anti-Pattern 5: One Monolithic "EngagementOptimizer" Class

**What people do:** Merge posting time and content prediction into one class.
**Why it's wrong:** The two concerns have different call sites (distribute step vs analysis step), different data consumers (scheduler vs content_editor), and different test surfaces.
**Do this instead:** Keep them as `posting_time_optimizer.py` and `engagement_scorer.py`. Both read the same `engagement_history.json` but are independently testable and replaceable.

---

## Sources

- Direct code inspection: `analytics.py`, `scheduler.py`, `pipeline/runner.py`, `pipeline/steps/distribute.py`, `pipeline/steps/analysis.py`, `pipeline/context.py`, `audio_clip_scorer.py`, `topic_scorer.py`
- Existing data storage patterns: `topic_data/analytics/ep_N_analytics.json`, `output/ep_N/upload_schedule.json`
- Existing atomic write pattern: `scheduler.py:UploadScheduler.save_schedule()` (`.tmp` rename)
- Existing component injection pattern: `pipeline/runner.py:_init_components()` returning components dict
- Existing graceful degradation pattern: `TopicEngagementScorer.get_engagement_bonus()` returning `None` when no analytics exist
- Existing optional-param pattern: `UploadScheduler.create_schedule()` optional `video_clip_paths`, `full_episode_video_path` params

---

*Architecture research for: v1.2 Engagement & Smart Scheduling — Fake Problems Podcast Automation*
*Researched: 2026-03-18*
