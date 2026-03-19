# Phase 12: ContentCalendar Foundation - Research

**Researched:** 2026-03-19
**Domain:** Python content scheduling, JSON state management, CLI integration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAL-01 | Content calendar generates a 5-slot distribution plan per episode (D-1 teaser, D0 episode + clip 1, D+2 clip 2, D+4 clip 3) | `PostingTimeOptimizer.get_optimal_publish_at()` provides per-platform best hours; `datetime + timedelta(days=N)` for day offsets |
| CAL-02 | Calendar tracks per-slot, per-platform upload status in `topic_data/content_calendar.json` | Existing `scheduler.save_schedule()` pattern (atomic write via .tmp) is the exact model to replicate |
| CAL-03 | `python main.py upload-scheduled` fires due slots from the calendar (extends existing scheduled upload) | `run_upload_scheduled()` already loops `output/*/upload_schedule.json`; extend to also loop `topic_data/content_calendar.json` |
| CAL-04 | Dry run displays the full calendar plan with slot dates and platform assignments | `dry_run()` in `runner.py` is a known extension point; already shows scheduler status at Step 8 |
</phase_requirements>

---

## Summary

Phase 12 adds a `content_calendar.py` module that generates a 5-slot weekly spread for each episode and persists slot state to `topic_data/content_calendar.json`. This replaces the existing flat per-episode upload schedule (which fires all uploads within hours of processing) with a deliberate day-spread pattern: D-1 teaser, D0 full episode + clip 1, D+2 clip 2, D+4 clip 3.

The technical surface is narrow. All primitives are already in the codebase: `UploadScheduler` (slot state model), `PostingTimeOptimizer` (per-platform optimal hours), and `run_upload_scheduled()` (slot dispatch). The new module introduces a calendar abstraction above the existing scheduler rather than replacing it. The key design decision is that `content_calendar.json` is a single global file in `topic_data/` (one record per episode), unlike the per-episode `upload_schedule.json` files under `output/`.

No new dependencies are needed. The entire implementation uses Python stdlib (`datetime`, `timedelta`, `json`, `dataclasses`, `pathlib`) plus existing project modules.

**Primary recommendation:** Build `content_calendar.py` as a thin wrapper around `datetime + timedelta` arithmetic, following the `UploadScheduler.save_schedule()` atomic-write pattern. Wire it into `run_distribute()` and extend `run_upload_scheduled()` to check calendar slots alongside the existing per-episode schedules.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `datetime` / `timedelta` | stdlib | Day-offset slot calculation | Already used throughout scheduler.py |
| `dataclasses` | stdlib | CalendarEntry / ClipSlot typed structs | Project convention (PipelineContext uses dataclass) |
| `json` | stdlib | Persist `content_calendar.json` | Already used for all JSON state files |
| `pathlib.Path` | stdlib | File paths (Config.TOPIC_DATA_DIR) | Project convention — every module uses it |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `PostingTimeOptimizer` | project | Per-platform optimal posting hour | Use inside `ContentCalendar.plan_episode()` to get best time-of-day for each slot |
| `UploadScheduler` | project | Existing slot state patterns | Reference its atomic-write and mark_uploaded patterns exactly |
| `Config` | project | `TOPIC_DATA_DIR`, platform hour defaults | Single source for all config values |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dataclasses` for slots | plain `dict` | Dicts are fine for small structs but dataclasses give type safety and are already the project convention for context objects |
| Single `content_calendar.json` | Per-episode calendar files | Single file is simpler to scan in `upload-scheduled`; per-episode files mirror upload_schedule.json but Phase 13 needs the single file for deduplication |

**Installation:** No new packages. All stdlib.

---

## Architecture Patterns

### Recommended Project Structure

The flat module structure convention (all top-level `.py` files) means:

```
content_calendar.py          # New module — CalendarEntry, ClipSlot, ContentCalendar class
tests/test_content_calendar.py  # New test file (project convention)
topic_data/content_calendar.json  # Generated state — NOT checked in, created at runtime
```

### Pattern 1: Slot Schema

**What:** Each calendar entry is an episode record with named slots. Each slot has a platform, a datetime, content metadata, and an upload status.

**When to use:** Every time `plan_episode()` is called.

**Slot layout (5 slots total):**
```
D-1 (day before release):
  - teaser: Twitter teaser post (hook from best clip)

D0 (release day):
  - episode: YouTube full episode + Twitter announcement
  - clip_1: YouTube Short + Twitter clip post (clip index 0)

D+2:
  - clip_2: YouTube Short + Twitter clip post (clip index 1)

D+4:
  - clip_3: YouTube Short + Twitter clip post (clip index 2)
```

**Note from requirements:** The 5-slot pattern from the additional context is: D-1 teaser, D0 episode + clip 1, D+2 clip 2, D+4 clip 3. Success criterion 4 explicitly requires "episode on D0, clip 1 on D+2, clip 2 on D+4". These slightly conflict. The success criteria are the authoritative source — use D0 episode, D+2 clip 1, D+4 clip 2 for the spread. The D-1 teaser is the 5th slot.

**JSON schema for `content_calendar.json`:**
```python
{
  "ep_29": {
    "episode_number": 29,
    "created_at": "2026-03-19T14:00:00",
    "slots": {
      "teaser": {
        "slot_type": "teaser",
        "day_offset": -1,
        "scheduled_at": "2026-03-18T10:00:00",
        "platforms": ["twitter"],
        "clip_index": 0,
        "content": {"caption": "...", "clip_path": "..."},
        "status": "pending",
        "uploaded_at": null,
        "upload_results": {}
      },
      "episode": {
        "slot_type": "episode",
        "day_offset": 0,
        "scheduled_at": "2026-03-19T14:00:00",
        "platforms": ["youtube", "twitter"],
        "content": {"title": "...", "video_path": "..."},
        "status": "pending",
        ...
      },
      "clip_1": { "day_offset": 2, ... },
      "clip_2": { "day_offset": 4, ... }
    }
  }
}
```

### Pattern 2: Atomic Write (follow UploadScheduler exactly)

**What:** Write to `.tmp` file, then `Path.replace()` to swap atomically.
**Why:** Prevents partial reads during concurrent `upload-scheduled` runs.

```python
# Source: scheduler.py lines 130-131 (project-established pattern)
tmp_path = calendar_path.with_suffix(".json.tmp")
tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
tmp_path.replace(calendar_path)
```

### Pattern 3: Day-Offset Datetime Calculation

**What:** Compute slot datetimes relative to a release_date anchor.

```python
# Source: stdlib datetime, following scheduler.py pattern
from datetime import datetime, timedelta

def _slot_datetime(release_date: datetime, day_offset: int, platform: str) -> datetime:
    """Return the scheduled datetime for a slot."""
    optimizer = PostingTimeOptimizer()
    optimal = optimizer.get_optimal_publish_at(platform)
    hour = optimal.hour if optimal else _default_hour(platform)
    base = release_date + timedelta(days=day_offset)
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)
```

**Key constraint:** If `PostingTimeOptimizer` has insufficient data (< 15 episodes), it returns `None` — fall back to `Config.SCHEDULE_*_POSTING_HOUR` values (14 for YouTube, 10 for Twitter, 12 for Instagram/TikTok).

### Pattern 4: run_upload_scheduled Extension

**What:** Extend existing `run_upload_scheduled()` to also check `content_calendar.json`.

**Current behavior:** Scans `output/*/upload_schedule.json`, dispatches past-due slots.

**Extension:** After existing loop, also scan `topic_data/content_calendar.json` for past-due pending slots. Reuse same dispatch table and `mark_uploaded` / `mark_failed` pattern.

```python
# Conceptual extension in pipeline/runner.py
def run_upload_scheduled():
    # ... existing upload_schedule.json loop ...

    # NEW: content calendar slots
    calendar = ContentCalendar()
    all_episodes = calendar.load_all()
    for ep_key, ep_data in all_episodes.items():
        pending = calendar.get_pending_slots(ep_data)
        for slot in pending:
            _dispatch_calendar_slot(slot, calendar, ep_key)
```

### Pattern 5: dry_run() Calendar Display

**What:** In `dry_run()`, after Step 8 social media block, add a calendar preview block.

**What to print:** All 5 slots with day labels (D-1, D0, D+2, D+4), scheduled datetimes, and platform assignments. Use stub `release_date = datetime.now()` since no real episode data is available in dry_run.

```
[MOCK] Content Calendar for ep_XX (release: 2026-03-19):
  D-1 2026-03-18 10:00  teaser    → Twitter
  D0  2026-03-19 14:00  episode   → YouTube, Twitter
  D0  2026-03-19 14:00  clip_1    → YouTube (Short)
  D+2 2026-03-21 10:00  clip_2    → YouTube (Short), Twitter
  D+4 2026-03-23 10:00  clip_3    → YouTube (Short), Twitter
```

### Pattern 6: ContentCalendar.plan_episode() — Called from distribute.py

**Where:** In `run_distribute()` in `pipeline/steps/distribute.py`, after social media uploads succeed (or in place of them when scheduling is enabled).

**Trigger condition:** Always generate the calendar when `ctx.episode_number` is set and content calendar is enabled.

```python
# In run_distribute(), after existing social media block
calendar = ContentCalendar()
calendar.plan_episode(
    episode_number=ctx.episode_number,
    release_date=datetime.now(),
    analysis=analysis,
    video_clip_paths=video_clip_paths,
    full_episode_video_path=full_episode_video_path,
)
```

### Anti-Patterns to Avoid

- **Generating a new calendar on every pipeline run:** `plan_episode()` must check if an entry already exists for the episode and skip re-generation (idempotent). Use `if ep_key in calendar_data: return` guard.
- **Using `output/ep_XX/` for calendar state:** The calendar is a cross-episode planning document. It belongs in `topic_data/`, not in episode output dirs.
- **Calling `PostingTimeOptimizer` per-slot without a fallback:** The optimizer returns `None` when history is sparse. Always fall back to `Config` posting hours.
- **Blocking the pipeline if calendar write fails:** Calendar generation is non-critical. Wrap in try/except and log a warning — don't raise.
- **Checking Instagram/TikTok slots:** Out of scope per REQUIREMENTS.md: "calendar generates slots but skips non-functional platforms." YouTube and Twitter only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Optimal posting time per platform | Custom hour lookup | `PostingTimeOptimizer.get_optimal_publish_at()` | Already computes best weekday+hour from engagement history |
| Atomic file writes | `open()` + write directly | `.tmp` + `Path.replace()` pattern from `UploadScheduler.save_schedule()` | Prevents partial reads during concurrent scheduled upload scans |
| Platform dispatch in upload-scheduled | New dispatch logic | Extend existing `dispatch` dict in `run_upload_scheduled()` | The YouTube/Twitter dispatch is already tested and working |
| Retry logic for slot uploads | Manual retry loop | `@retry_with_backoff` from `retry_utils.py` | Already used in `run_upload_scheduled()` for the same purpose |

**Key insight:** This phase is almost entirely wiring. Every primitive exists — `PostingTimeOptimizer`, atomic writes, slot dispatch, status tracking. The value is in the calendar abstraction and the 5-slot day-spread logic.

---

## Common Pitfalls

### Pitfall 1: D0 Date Anchoring
**What goes wrong:** If `plan_episode()` uses `datetime.now()` as the release date, the D-1 slot will already be in the past when called during the pipeline run.
**Why it happens:** `plan_episode()` is called at the end of the pipeline (Step 8), which may run hours after the episode is "released."
**How to avoid:** Accept `release_date` as an explicit parameter. Default to `datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)` (midnight today) so D0 slots still land at the configured posting hour on the current day. D-1 will be in the past — that's expected; `upload-scheduled` will skip it.
**Warning signs:** D-1 teaser slot appears in `get_pending_slots()` immediately after generation.

### Pitfall 2: Re-planning on Resume
**What goes wrong:** If the pipeline resumes mid-run and calls `plan_episode()` again, it would reset slot statuses — losing any already-uploaded slot records.
**Why it happens:** `pipeline_state.py` checkpoint logic may cause distribute step to re-run.
**How to avoid:** Make `plan_episode()` idempotent — check for existing entry first: `if episode_key in data: return data[episode_key]`. Only write new entry if absent.
**Warning signs:** Upload results disappear from `content_calendar.json` on re-runs.

### Pitfall 3: Slot Count vs Available Clips
**What goes wrong:** If an episode has only 1 clip, generating 3 clip slots (D0, D+2, D+4) results in 2 empty slots.
**Why it happens:** Calendar plan is generated before knowing how many clips actually exist.
**How to avoid:** Generate only as many clip slots as there are `video_clip_paths`. If 0 clips, generate no clip slots. If 1 clip, generate D+2 only. Cap at 3 clips.
**Warning signs:** Slots with `clip_path: null` being fired by `upload-scheduled`.

### Pitfall 4: Instagram/TikTok Slots
**What goes wrong:** Including Instagram/TikTok in calendar slots generates slots that can never be fulfilled (uploaders are stubs).
**Why it happens:** Easy to include all platforms by default.
**How to avoid:** Hardcode platforms per slot type: teaser/clips → `["youtube", "twitter"]`, episode → `["youtube", "twitter"]`. Per REQUIREMENTS.md: "skips non-functional platforms."
**Warning signs:** Calendar slots with `"instagram"` in platforms list.

### Pitfall 5: Two Clips Same Day
**What goes wrong:** Scheduling clip_1 on D0 and the episode on D0 violates the success criterion "no two clips same day."
**Why it happens:** Confusion between the additional_context 5-slot layout (D0 episode + clip 1) vs success criterion 4 (episode D0, clip 1 D+2).
**How to avoid:** Follow success criteria, not the summary. D0 = episode only. D+2 = clip 1. D+4 = clip 2. D-1 = teaser.
**Warning signs:** Two slots sharing the same `day_offset`.

---

## Code Examples

Verified patterns from existing codebase:

### Atomic JSON Write (from scheduler.py)
```python
# Source: scheduler.py lines 129-133
schedule_path = output_dir / "upload_schedule.json"
tmp_path = output_dir / "upload_schedule.json.tmp"
tmp_path.write_text(json.dumps(schedule, indent=2), encoding="utf-8")
tmp_path.replace(schedule_path)
```

### PostingTimeOptimizer fallback chain (from scheduler.py)
```python
# Source: scheduler.py lines 233-257
try:
    optimizer = PostingTimeOptimizer()
    optimal_dt = optimizer.get_optimal_publish_at(platform)
    if optimal_dt is not None:
        return optimal_dt.isoformat()
except Exception:
    pass  # fall through to fixed delay

# Fallback to config
if delay > 0:
    return (datetime.now() + timedelta(hours=delay)).isoformat()
return None
```

### Slot status model (follows scheduler.py get_pending_uploads pattern)
```python
# Source: scheduler.py lines 155-174
def get_pending_slots(self, episode_data: dict) -> list[dict]:
    now = datetime.now()
    pending = []
    for slot_name, slot in episode_data.get("slots", {}).items():
        if slot.get("status") != "pending":
            continue
        scheduled_at = datetime.fromisoformat(slot["scheduled_at"])
        if scheduled_at <= now:
            pending.append({**slot, "slot_name": slot_name})
    return pending
```

### Dry run calendar display (pattern from dry_run() in runner.py)
```python
# Source: runner.py lines 800-813 (Step 8 scheduling note pattern)
if calendar_generator and calendar_generator.enabled:
    print("[MOCK] Content Calendar:")
    for slot in stub_slots:
        print(f"  {slot['label']:4s} {slot['dt'].strftime('%Y-%m-%d %H:%M')}  "
              f"{slot['type']:8s} → {', '.join(slot['platforms'])}")
```

### run_upload_scheduled extension point (from runner.py)
```python
# Source: runner.py lines 940-1037
# Current: scans output/*/upload_schedule.json
# Extension: after existing loop, also scan topic_data/content_calendar.json
schedule_files = list(output_dir.glob("*/upload_schedule.json"))
# NEW: calendar_path = Config.TOPIC_DATA_DIR / "content_calendar.json"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All uploads fire immediately on pipeline completion | Fixed-delay scheduling via `upload_schedule.json` (Phase 11) | v1.2 | Uploads can be deferred hours |
| Fixed hour delays per platform | Smart scheduling via `PostingTimeOptimizer` (Phase 11) | v1.2 | Uses engagement data to pick best weekday+hour |
| Single schedule per episode in output/ | **New:** Multi-episode calendar in topic_data/ with day-spread | Phase 12 | Spreads clips across a week |

---

## Open Questions

1. **D-1 teaser slot content**
   - What we know: It should be a "teaser" Twitter post. The analysis dict has `social_captions.twitter` (episode announcement) and clips have `hook_caption`.
   - What's unclear: Should the teaser use `hook_caption` from clip 0, or a separate teaser caption from the LLM analysis? Analysis dict does not have a dedicated `teaser_caption` field.
   - Recommendation: Use `best_clips[0]["hook_caption"]` for the teaser text. This is the first interesting soundbite — suitable for a pre-release hook. If no clips, skip the teaser slot.

2. **`CONTENT_CALENDAR_ENABLED` config flag**
   - What we know: Every module uses `self.enabled = Config.SOME_ENABLED`. The calendar should be skippable.
   - What's unclear: Whether the planner wants this gated by a config flag or always-on.
   - Recommendation: Add `CONTENT_CALENDAR_ENABLED = os.getenv("CONTENT_CALENDAR_ENABLED", "true") == "true"` to `config.py`. This follows the established pattern.

3. **`Config.TOPIC_DATA_DIR` path**
   - What we know: `topic_data/` directory already exists and holds `content_calendar.json` per requirements.
   - What's unclear: Whether `Config` has a `TOPIC_DATA_DIR` attribute or if we construct it inline.
   - Recommendation: Search config.py. If absent, define `TOPIC_DATA_DIR = Path("topic_data")` in Config — it's a constant path, not environment-specific.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | none — pytest discovers tests/ automatically |
| Quick run command | `pytest tests/test_content_calendar.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAL-01 | `plan_episode()` generates 5 slots with correct day offsets | unit | `pytest tests/test_content_calendar.py::TestPlanEpisode -x` | ❌ Wave 0 |
| CAL-01 | No two slots share the same day_offset | unit | `pytest tests/test_content_calendar.py::TestPlanEpisode::test_no_duplicate_day_offsets -x` | ❌ Wave 0 |
| CAL-01 | Clip slots capped to available video_clip_paths count | unit | `pytest tests/test_content_calendar.py::TestPlanEpisode::test_clip_slot_count -x` | ❌ Wave 0 |
| CAL-02 | `content_calendar.json` written atomically after plan_episode | unit | `pytest tests/test_content_calendar.py::TestSaveLoad -x` | ❌ Wave 0 |
| CAL-02 | plan_episode is idempotent (second call skips re-planning) | unit | `pytest tests/test_content_calendar.py::TestPlanEpisode::test_idempotent -x` | ❌ Wave 0 |
| CAL-03 | `get_pending_slots()` returns only past-due pending slots | unit | `pytest tests/test_content_calendar.py::TestGetPendingSlots -x` | ❌ Wave 0 |
| CAL-03 | `mark_slot_uploaded()` sets status=uploaded and saves | unit | `pytest tests/test_content_calendar.py::TestMarkSlot -x` | ❌ Wave 0 |
| CAL-03 | `run_upload_scheduled()` fires calendar slots (integration) | unit | `pytest tests/test_scheduler.py::TestRunUploadScheduled -x` | ✅ (extend) |
| CAL-04 | dry_run prints calendar block without errors | unit | `pytest tests/test_content_calendar.py::TestDryRunDisplay -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_content_calendar.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_content_calendar.py` — covers CAL-01, CAL-02, CAL-03, CAL-04
- [ ] `content_calendar.py` — new module (Wave 0 creates skeleton with class + method stubs)

*(No framework install needed — pytest already configured)*

---

## Sources

### Primary (HIGH confidence)
- Direct code read: `scheduler.py` — slot schema, atomic write, mark_uploaded patterns
- Direct code read: `pipeline/runner.py` — `run_upload_scheduled()` extension point, `dry_run()` integration point
- Direct code read: `pipeline/steps/distribute.py` — where `plan_episode()` should be called
- Direct code read: `posting_time_optimizer.py` — `get_optimal_publish_at()` fallback chain
- Direct code read: `config.py` — platform posting hours (YouTube=14, Twitter=10, Instagram/TikTok=12)
- Direct code read: `pipeline/context.py` — `PipelineContext` fields available during distribute step
- Direct code read: `.planning/ROADMAP.md` — exact plan breakdown for 12-01 and 12-02
- Direct code read: `.planning/REQUIREMENTS.md` — authoritative slot layout (CAL-01)

### Secondary (MEDIUM confidence)
- Direct code read: `tests/test_scheduler.py` — test conventions (class grouping, mock patterns)

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, no external dependencies, all patterns already in project
- Architecture: HIGH — slot schema, day-offset math, and dispatch pattern all directly derived from existing code
- Pitfalls: HIGH — derived from reading actual code paths and success criteria conflicts

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable domain — pure Python, no external APIs)
