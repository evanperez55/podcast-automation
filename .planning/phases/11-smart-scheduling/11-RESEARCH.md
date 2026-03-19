# Phase 11: Smart Scheduling - Research

**Researched:** 2026-03-19
**Domain:** Scheduling optimization, datetime arithmetic, engagement data analysis
**Confidence:** HIGH

## Summary

Phase 11 adds a `posting_time_optimizer.py` module that computes optimal posting datetimes per platform by blending the show's own engagement history with research-based defaults. The existing `EngagementScorer._analyze_day_of_week()` already computes per-platform weekday averages from `engagement_history.json` — the new module wraps that output and converts it into a concrete `datetime` object for the next occurrence of the best weekday at a configured hour-of-day. When fewer than 15 episodes exist (ENGAGE-04 gate), or when confidence is below threshold, it returns `None` and `scheduler.py` falls back to the existing fixed-delay logic unchanged.

The integration point is `_upload_to_social_media()` in `pipeline/steps/distribute.py`. Currently it calls `scheduler.get_youtube_publish_at()` (fixed delay) and passes the result as `publish_at` to `_upload_youtube()`. A new `UploadScheduler.get_optimal_publish_at(platform)` method wraps the optimizer: if the optimizer returns a datetime, use it; otherwise delegate to the existing delay-based logic. No callers in distribute.py change signature — they only switch from `get_youtube_publish_at()` to `get_optimal_publish_at("youtube")`.

**Primary recommendation:** New module `posting_time_optimizer.py` with `PostingTimeOptimizer` class; add `get_optimal_publish_at(platform)` to `UploadScheduler`; add research-based defaults and configurable hour windows to `config.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCHED-01 | Optimal posting time computed from own historical data + research defaults | EngagementScorer._analyze_day_of_week() already produces per-platform weekday averages; optimizer converts best weekday + configured hour into next datetime |
| SCHED-02 | Platform-specific scheduling windows (YouTube, Twitter differ) | Config.py gains per-platform hour windows and research-based day defaults; optimizer selects platform-appropriate window |
| SCHED-03 | scheduler.py accepts computed optimal times via get_optimal_publish_at() — fixed delays remain fallback | UploadScheduler.get_optimal_publish_at(platform) wraps optimizer, falls back to existing fixed-delay logic; distribute.py callers use new method |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| datetime (stdlib) | 3.12+ | Date/time arithmetic for computing next-occurrence windows | Already used throughout codebase |
| scipy.stats | already in requirements | Spearman correlation (already done in EngagementScorer) | No new dependency needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib (stdlib) | 3.12+ | History file path resolution | Already pattern throughout project |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom weekday-to-datetime logic | Arrow / pendulum | No new dependencies needed; stdlib datetime handles next-occurrence arithmetic simply |
| In-process hour config | Cron-style expressions | Cron requires a parser; hour integers in config.py are simpler and already consistent with SCHEDULE_*_DELAY_HOURS pattern |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Project Structure
```
posting_time_optimizer.py    # New module — PostingTimeOptimizer class
scheduler.py                 # Add get_optimal_publish_at(platform) method
config.py                    # Add per-platform hour defaults + research windows
tests/test_posting_time_optimizer.py  # New test file
```

### Pattern 1: Optimizer as Thin Wrapper Over EngagementScorer

**What:** `PostingTimeOptimizer` delegates day-of-week analysis to `EngagementScorer` rather than re-reading history itself. It picks the best-scoring weekday for the requested platform, then computes the next calendar datetime for that weekday at the configured posting hour.

**When to use:** Always — keeps all history-loading logic in one place (EngagementScorer).

```python
# posting_time_optimizer.py
from datetime import datetime, timedelta
from typing import Optional
from engagement_scorer import EngagementScorer
from config import Config

class PostingTimeOptimizer:
    def __init__(self, history_path=None):
        self._scorer = EngagementScorer(history_path=history_path)

    def get_optimal_publish_at(self, platform: str) -> Optional[datetime]:
        """Return optimal posting datetime or None when confidence is insufficient."""
        result = self._scorer.get_category_rankings()
        if result["status"] != "ok":
            return None  # insufficient data — let scheduler fall back to fixed delay

        day_of_week = result.get("day_of_week") or {}
        platform_days = day_of_week.get(platform)  # {"Monday": 2.3, "Tuesday": None, ...}
        if not platform_days:
            return None

        best_day = _best_weekday(platform_days)
        if best_day is None:
            return None

        posting_hour = _posting_hour_for(platform)
        return _next_occurrence(best_day, posting_hour)
```

### Pattern 2: Next-Occurrence Datetime Computation

**What:** Given a weekday name and an hour, compute the nearest future `datetime` that lands on that weekday at that hour. Must handle same-day (if current time is before posting_hour) and advance to next week if today already passed posting_hour.

**When to use:** Core utility for SCHED-01.

```python
WEEKDAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def _next_occurrence(weekday_name: str, hour: int) -> datetime:
    """Return next datetime that is weekday_name at hour (local time, today or later)."""
    today = datetime.now()
    target_dow = WEEKDAY_NAMES.index(weekday_name)
    days_ahead = (target_dow - today.weekday()) % 7
    candidate = today.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    if candidate <= today:
        candidate += timedelta(weeks=1)
    return candidate
```

### Pattern 3: Config-Driven Research Defaults

**What:** Config.py gains per-platform posting hour (time-of-day) and a fallback best-day constant. These are used when historical data is sufficient for day selection but no custom hour is configured, and as pure fallbacks when history is absent.

**When to use:** Always — values must be overridable via env vars so the user can tune without code changes.

```python
# config.py additions
# Research-based posting hour defaults (24h, local time)
SCHEDULE_YOUTUBE_POSTING_HOUR = int(os.getenv("SCHEDULE_YOUTUBE_POSTING_HOUR", "14"))   # 2 PM
SCHEDULE_TWITTER_POSTING_HOUR = int(os.getenv("SCHEDULE_TWITTER_POSTING_HOUR", "10"))   # 10 AM

# Research-based fallback day (used when history < 15 episodes but smart scheduling requested)
# Not needed by SCHED-01 through SCHED-03 — fallback is the existing fixed-delay path.
```

### Pattern 4: UploadScheduler.get_optimal_publish_at()

**What:** New method on existing class. Tries optimizer first; if it returns None, falls back to fixed-delay logic already in `get_youtube_publish_at()`. This is the single change callers in distribute.py need.

**When to use:** Replace the direct `scheduler.get_youtube_publish_at()` call in `_upload_to_social_media()`.

```python
# scheduler.py addition
def get_optimal_publish_at(self, platform: str) -> Optional[str]:
    """Return ISO datetime for optimal publish time, or fixed-delay, or None.

    Tries PostingTimeOptimizer first.  Falls back to delay-based logic when
    optimizer returns None (insufficient data or platform unsupported).
    Returns None when both optimizer and fixed delay are disabled.
    """
    from posting_time_optimizer import PostingTimeOptimizer
    optimizer = PostingTimeOptimizer()
    optimal_dt = optimizer.get_optimal_publish_at(platform)
    if optimal_dt is not None:
        logger.info("Smart scheduling: %s → %s", platform, optimal_dt.isoformat())
        return optimal_dt.isoformat()

    # Fallback: fixed delay (existing behaviour)
    delay_map = {
        "youtube": self.youtube_delay,
        "twitter": self.twitter_delay,
        "instagram": self.instagram_delay,
        "tiktok": self.tiktok_delay,
    }
    delay = delay_map.get(platform, 0)
    if delay > 0:
        return (datetime.now() + timedelta(hours=delay)).isoformat()
    return None
```

### Pattern 5: Confidence-Aware Best-Day Selection

**What:** `_best_weekday()` selects the weekday with the highest average engagement score, ignoring weekdays where the value is None (no data). Returns None if all days have no data.

```python
def _best_weekday(day_scores: dict) -> Optional[str]:
    """Return the weekday name with the highest non-None average score."""
    candidates = {k: v for k, v in day_scores.items() if v is not None}
    if not candidates:
        return None
    return max(candidates, key=lambda k: candidates[k])
```

### Anti-Patterns to Avoid

- **Daemon/cron scheduler:** Out of scope (see REQUIREMENTS.md). Compute at pipeline time only.
- **Re-reading engagement_history.json in PostingTimeOptimizer:** Delegate to EngagementScorer — it owns history loading and the 15-episode confidence gate.
- **Raising exceptions on insufficient data:** Return None — callers must fall back gracefully.
- **Mutating existing `create_schedule()` signature:** Do not change `create_schedule()`. The optimizer feeds into `get_optimal_publish_at()` only.
- **Hardcoding "YouTube" or "Twitter" strings in optimizer:** Use platform string param, look up config by name; makes future platform additions trivial.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Day-of-week engagement averages | Custom history parser | EngagementScorer._analyze_day_of_week() | Already implemented and tested in Phase 10 |
| Data confidence gate | Custom episode counter | EngagementScorer.get_category_rankings() status field | Returns "insufficient_data" when < 15 episodes |
| ISO datetime formatting | Custom string builder | datetime.isoformat() | Already used throughout scheduler.py |

**Key insight:** The entire analytical backend (history loading, weekday bucketing, confidence gating) is already built in EngagementScorer. PostingTimeOptimizer is pure coordination logic (~60 lines).

## Common Pitfalls

### Pitfall 1: Same-Day Scheduling Logic
**What goes wrong:** Computing `today + 0 days` at the target hour gives a past time if the pipeline runs after that hour today.
**Why it happens:** `(target_dow - today.weekday()) % 7 == 0` when today is the best day.
**How to avoid:** After computing candidate datetime, check `if candidate <= datetime.now(): candidate += timedelta(weeks=1)`.
**Warning signs:** Tests pass in the morning but fail in the afternoon.

### Pitfall 2: None Values in day_of_week Dict
**What goes wrong:** `max()` on a dict with None values raises TypeError.
**Why it happens:** EngagementScorer sets weekday avg to None when no episodes posted that day.
**How to avoid:** Filter out None values before calling max(). `_best_weekday()` helper handles this.

### Pitfall 3: PostingTimeOptimizer Circular Import
**What goes wrong:** If scheduler.py imports PostingTimeOptimizer at module level, and PostingTimeOptimizer imports from config.py which imports scheduler.py (if ever added), you get circular import.
**Why it happens:** Python resolves imports at module load time.
**How to avoid:** Import PostingTimeOptimizer inside `get_optimal_publish_at()` method body (local import). This is already the pattern used by `run_distribute_only()` in runner.py for several imports.

### Pitfall 4: Breaking --dry-run / --test modes
**What goes wrong:** Optimizer tries to read engagement_history.json and fails in environments without data.
**Why it happens:** Optimizer is called unconditionally during pipeline.
**How to avoid:** EngagementScorer._load_history() already returns [] when file is absent — optimizer gets "insufficient_data" and returns None. No special dry-run guard needed in optimizer itself.

### Pitfall 5: Twitter vs YouTube Hour Mismatch
**What goes wrong:** Both platforms use the same posting hour even though research shows they differ.
**Why it happens:** Single SCHEDULE_POSTING_HOUR config instead of per-platform.
**How to avoid:** Separate config vars `SCHEDULE_YOUTUBE_POSTING_HOUR` and `SCHEDULE_TWITTER_POSTING_HOUR` (SCHED-02 requirement).

## Code Examples

### Engagement History Record Structure (from test fixtures)
```python
# Source: tests/test_engagement_scorer.py _make_record()
{
    "episode_number": 1,
    "collected_at": "2026-03-19T00:00:00Z",
    "post_timestamp": "2026-03-16T12:00:00+00:00",  # ISO with tz
    "topics": ["shocking_news story"],
    "youtube": {
        "video_id": "vid1",
        "views": 1000,
        "likes": 50,
        "comments": 10,
    },
    "twitter": {
        "tweet_id": "tw1",
        "impressions": 5000,
        "engagements": 100,
        "retweets": 20,
        "likes": 80,
    },
}
```

### EngagementScorer day_of_week Output (consumed by optimizer)
```python
# Source: engagement_scorer.py _analyze_day_of_week()
{
    "youtube": {
        "Monday": 2.35,
        "Tuesday": None,   # no episodes posted Tuesday
        "Wednesday": 1.80,
        "Thursday": None,
        "Friday": 3.10,    # best day
        "Saturday": None,
        "Sunday": None,
    },
    "twitter": {
        "Monday": 0.82,
        "Tuesday": None,
        "Wednesday": 1.10,
        "Thursday": None,
        "Friday": 0.65,
        "Saturday": None,
        "Sunday": None,
    },
}
```

### Existing get_youtube_publish_at() (to be superseded by get_optimal_publish_at)
```python
# Source: scheduler.py lines 212-224
def get_youtube_publish_at(self) -> Optional[str]:
    if self.youtube_delay > 0:
        publish_at = (datetime.now() + timedelta(hours=self.youtube_delay)).isoformat()
        return publish_at
    return None
```

### How distribute.py currently calls scheduler (integration point)
```python
# Source: pipeline/steps/distribute.py lines 295-303
publish_at = scheduler.get_youtube_publish_at() if scheduler else None
youtube_results = _upload_youtube(
    ...,
    publish_at=publish_at,
)
```

The change for SCHED-03: replace `scheduler.get_youtube_publish_at()` with `scheduler.get_optimal_publish_at("youtube")`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed-delay hours (SCHEDULE_YOUTUBE_DELAY_HOURS) | Optimal weekday + hour from own engagement data | Phase 11 | Fixed delays are preserved as fallback |
| No posting time intelligence | Day-of-week averaged engagement informs next-occurrence datetime | Phase 11 | Gradual improvement as data accumulates past 15 episodes |

**Research-based defaults (for config.py):**
- YouTube: Tuesday and Thursday afternoons (2-4 PM) perform well for informational/entertainment content — source: Sprout Social 2024 data (MEDIUM confidence, not verified against official docs).
- Twitter: Tuesday and Wednesday mornings (9-11 AM) for media accounts — source: Sprout Social 2024 (MEDIUM confidence).
- These are used only as the initial `SCHEDULE_*_POSTING_HOUR` defaults; the actual day selection comes from historical data once threshold is met.

## Open Questions

1. **Timezone: local vs UTC**
   - What we know: `post_timestamp` in engagement_history uses ISO with timezone (e.g., `+00:00`). `datetime.now()` in scheduler.py is naive local time.
   - What's unclear: Should optimal publish_at be UTC or local? YouTube's `publishAt` API requires RFC 3339 (UTC preferred). Current `get_youtube_publish_at()` uses naive local ISO.
   - Recommendation: Match current behavior — use naive local datetime (consistent with rest of codebase). If YouTube requires UTC, that's a separate bug in existing code, not introduced by this phase.

2. **Instagram and TikTok platform support**
   - What we know: SCHED-02 mentions "YouTube, Twitter differ" but Instagram/TikTok uploaders are stubs.
   - What's unclear: Should `get_optimal_publish_at("instagram")` be implemented even though uploads are stubs?
   - Recommendation: Implement for all four platforms in optimizer (config defaults + fallback to fixed delay) — zero extra cost, forward-compatible.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no config file — uses defaults) |
| Config file | none — pytest auto-discovers tests/ |
| Quick run command | `pytest tests/test_posting_time_optimizer.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHED-01 | Optimizer returns best-weekday datetime from historical data | unit | `pytest tests/test_posting_time_optimizer.py::TestGetOptimalPublishAt::test_returns_best_weekday -x` | Wave 0 |
| SCHED-01 | Optimizer returns None when EngagementScorer reports insufficient_data | unit | `pytest tests/test_posting_time_optimizer.py::TestGetOptimalPublishAt::test_returns_none_insufficient_data -x` | Wave 0 |
| SCHED-01 | Optimizer returns None when all weekday scores are None | unit | `pytest tests/test_posting_time_optimizer.py::TestGetOptimalPublishAt::test_returns_none_no_weekday_data -x` | Wave 0 |
| SCHED-01 | Next-occurrence is in the future (same-day past-hour guard) | unit | `pytest tests/test_posting_time_optimizer.py::TestNextOccurrence::test_past_hour_advances_one_week -x` | Wave 0 |
| SCHED-02 | YouTube and Twitter use different configured posting hours | unit | `pytest tests/test_posting_time_optimizer.py::TestPlatformHours::test_youtube_twitter_different_hours -x` | Wave 0 |
| SCHED-03 | get_optimal_publish_at uses optimizer when data sufficient | unit | `pytest tests/test_scheduler.py::TestGetOptimalPublishAt::test_uses_optimizer_result -x` | Wave 0 |
| SCHED-03 | get_optimal_publish_at falls back to fixed delay when optimizer returns None | unit | `pytest tests/test_scheduler.py::TestGetOptimalPublishAt::test_fallback_to_fixed_delay -x` | Wave 0 |
| SCHED-03 | get_optimal_publish_at returns None when both optimizer and delay disabled | unit | `pytest tests/test_scheduler.py::TestGetOptimalPublishAt::test_returns_none_when_both_disabled -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_posting_time_optimizer.py tests/test_scheduler.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_posting_time_optimizer.py` — covers SCHED-01 and SCHED-02
- [ ] New test classes in `tests/test_scheduler.py` — covers SCHED-03 (existing file, add class `TestGetOptimalPublishAt`)

## Sources

### Primary (HIGH confidence)
- `engagement_scorer.py` (direct code reading) — _analyze_day_of_week() return structure, confidence gate, WEEKDAY_NAMES
- `scheduler.py` (direct code reading) — existing method signatures, get_youtube_publish_at(), delay pattern
- `pipeline/steps/distribute.py` (direct code reading) — exact integration point at line 295
- `config.py` (direct code reading) — SCHEDULE_*_DELAY_HOURS pattern, env var loading idiom
- `tests/test_scheduler.py` (direct code reading) — existing test patterns to extend

### Secondary (MEDIUM confidence)
- Sprout Social 2024 best posting time research (platform posting hour defaults) — not directly verified against official platform data

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new dependencies
- Architecture: HIGH — integration points verified by direct code reading
- Pitfalls: HIGH — same-day logic and None-filtering are deterministic edge cases identifiable from code
- Research-based hour defaults: MEDIUM — external source, not official platform documentation

**Research date:** 2026-03-19
**Valid until:** 2026-09-19 (stable domain — datetime arithmetic and project architecture don't change)
