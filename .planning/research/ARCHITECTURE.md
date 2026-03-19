# Architecture Research

**Domain:** Content calendar and GitHub Actions CI/CD — v1.3 integration into existing pipeline
**Researched:** 2026-03-19
**Confidence:** HIGH — based on direct code inspection of all relevant existing modules + official GitHub Actions docs

---

## Current Architecture (as-built, v1.2)

```
main.py (134-line CLI shim)
    |
pipeline/runner.py (orchestrator, component factory, checkpoint logic)
    |
    +---> pipeline/context.py (PipelineContext dataclass)
    |
    +---> pipeline/steps/ingest.py     (Step 1: download)
    +---> pipeline/steps/analysis.py   (Steps 3-3.5: AI analysis + topic tracker)
    +---> pipeline/steps/video.py      (Steps 5.1-5.6: clips, subs, video, thumb)
    +---> pipeline/steps/distribute.py (Steps 7-9: Dropbox, RSS, social, blog, search)

State files (per-episode):
    output/ep_N/upload_schedule.json    — platform upload schedule + status
    output/.pipeline_state/ep_N.json    — step checkpoint state

Cross-episode data:
    topic_data/engagement_history.json  — posting time outcomes (v1.2)
    topic_data/analytics/               — per-episode platform metrics
```

Key facts about scheduling in the existing system:

- `scheduler.py` — `UploadScheduler.create_schedule()` writes `upload_schedule.json` per episode at pipeline creation time. `run_upload_scheduled()` in `pipeline/runner.py` polls existing schedule files and fires any pending platform uploads whose `publish_at` has passed.
- `posting_time_optimizer.py` — `PostingTimeOptimizer` computes the next optimal weekday+hour for a platform. Returns `None` if fewer than 15 episodes of history exist.
- No content calendar exists yet. Clip distribution timing is the same as episode publishing — all clips and episode are produced together, published with fixed platform delays.
- No CI/CD exists. All runs are manual via `python main.py latest` or `python main.py epN` on the local Windows machine.

---

## System Overview: v1.3 Additions

```
┌──────────────────────────────────────────────────────────────────────┐
│                  TRIGGER LAYER (NEW)                                  │
│                                                                       │
│  GitHub Actions (.github/workflows/)                                  │
│  ┌──────────────────────┐  ┌───────────────────────────────────────┐ │
│  │  poll.yml            │  │  manual.yml                           │ │
│  │  schedule: cron      │  │  on: workflow_dispatch                │ │
│  │  → python ci/poll.py │  │  inputs: episode_number, flags        │ │
│  │  if new file found:  │  │  → python main.py epN --auto-approve  │ │
│  │    dispatch process  │  └───────────────────────────────────────┘ │
│  └──────────────────────┘                                             │
│                                                                       │
│  runs-on: self-hosted (Windows 11, NVIDIA GPU, CUDA)                  │
├──────────────────────────────────────────────────────────────────────┤
│                  CALENDAR LAYER (NEW)                                 │
│                                                                       │
│  content_calendar.py                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  ContentCalendar                                                  │ │
│  │  - plan_episode(episode_number, release_date) → CalendarEntry    │ │
│  │  - plan_clips(episode_number, clips) → List[ClipSlot]            │ │
│  │  - get_pending_slots(now) → List[ClipSlot]                       │ │
│  │  reads/writes: topic_data/content_calendar.json                  │ │
│  └────────────────────────────┬────────────────────────────────────┘ │
│                               │                                       │
│  ci/poll.py                   │                                       │
│  ┌────────────────────────────▼────────────────────────────────────┐ │
│  │  - list Dropbox new_raw_files                                     │ │
│  │  - compare against content_calendar.json processed episodes      │ │
│  │  - if unprocessed WAV found → write ci/pending_episode.txt       │ │
│  │  - exit 0 (new file) or exit 1 (nothing new)                     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│                  EXISTING PIPELINE (v1.2, unchanged)                  │
│                                                                       │
│  main.py → pipeline/runner.py → pipeline/steps/                      │
│  upload_schedule.json + .pipeline_state/ep_N.json                    │
│                                                                       │
│  MODIFIED: pipeline/steps/distribute.py                              │
│  - After clips produced: ContentCalendar.plan_clips()                │
│  - Assigns clip publish slots spread across the week                 │
│  - Clip uploads read slot datetimes from content_calendar.json       │
├──────────────────────────────────────────────────────────────────────┤
│                  STATE & SECRETS                                      │
│                                                                       │
│  topic_data/content_calendar.json  — calendar entries (local file)   │
│  .env (local, never committed)     — all API keys                    │
│  GitHub Actions Secrets            — mirrors of .env vars            │
│  (runner reads .env from disk; Actions secrets used in cloud fallback)│
└──────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Project Structure

```
podcast-automation/
├── main.py                              # UNCHANGED
├── config.py                           # MODIFIED: CALENDAR_CLIP_SPREAD_DAYS, DROPBOX_POLL_INTERVAL
├── content_calendar.py                 # NEW: ContentCalendar class
├── pipeline/
│   └── steps/
│       └── distribute.py              # MODIFIED: call calendar.plan_clips() after clip creation
├── ci/
│   ├── poll.py                        # NEW: Dropbox polling script for GitHub Actions
│   └── trigger_episode.py             # NEW: invoke pipeline for discovered episode
├── .github/
│   └── workflows/
│       ├── poll.yml                   # NEW: scheduled cron, calls ci/poll.py
│       └── manual.yml                 # NEW: workflow_dispatch for manual episode trigger
├── topic_data/
│   ├── content_calendar.json          # NEW: persistent calendar state
│   ├── engagement_history.json        # EXISTING (v1.2)
│   └── analytics/                     # EXISTING
└── tests/
    └── test_content_calendar.py       # NEW
```

### Structure Rationale

- **`ci/` directory** — separates CI-specific scripts (poll, trigger) from the main pipeline. These scripts are thin: they read Dropbox state and invoke `main.py`. No business logic here.
- **`content_calendar.py` at root** — follows project convention of flat module structure. Peer to `scheduler.py` and `posting_time_optimizer.py`.
- **`topic_data/content_calendar.json`** — co-located with existing cross-episode data files (`engagement_history.json`, `scored_topics_*.json`). Consistent discovery pattern.
- **`.github/workflows/`** — standard location; two workflows (poll + manual) to keep concerns separate.

---

## Architectural Patterns

### Pattern 1: Content Calendar as a JSON State File (Not Config)

**What:** `content_calendar.json` is a generated, mutable state file — not a hand-edited config. `ContentCalendar` generates it when `plan_episode()` or `plan_clips()` is called, and updates it as slots are consumed.

**When to use:** After the distribute step creates clips; before `run_upload_scheduled()` fires.

**Trade-offs:** Zero new database dependency. Trivially inspectable (`cat topic_data/content_calendar.json`). Atomic write pattern (`.tmp` rename) prevents corrupt state on crash. Scales adequately to a bi-weekly show (~50 entries/year). No web UI or external calendar service needed.

**Schema:**
```json
{
  "episodes": {
    "ep_30": {
      "episode_number": 30,
      "release_date": "2026-03-25T14:00:00",
      "status": "scheduled",
      "dropbox_path": "/Fake Problems Podcast/new_raw_files/ep30.wav",
      "clips": [
        {
          "clip_index": 0,
          "clip_path": "output/ep_30/clip_0_subtitled.mp4",
          "platforms": {
            "twitter":  { "publish_at": "2026-03-26T10:00:00", "status": "pending" },
            "tiktok":   { "publish_at": "2026-03-27T12:00:00", "status": "pending" },
            "youtube":  { "publish_at": "2026-03-25T14:00:00", "status": "uploaded", "video_id": "abc123" }
          }
        },
        {
          "clip_index": 1,
          "clip_path": "output/ep_30/clip_1_subtitled.mp4",
          "platforms": {
            "twitter":  { "publish_at": "2026-03-28T10:00:00", "status": "pending" },
            "tiktok":   { "publish_at": "2026-03-29T12:00:00", "status": "pending" }
          }
        }
      ]
    }
  },
  "last_updated": "2026-03-19T12:00:00"
}
```

Clip spread strategy: episode day = Clip 0 (YouTube Short); day+1 = Clip 0 Twitter/TikTok; day+3 = Clip 1 Twitter/TikTok; day+5 = Clip 2 if exists. This gives 5 social touchpoints across the week from a single episode.

### Pattern 2: GitHub Actions Self-Hosted Runner on the Existing Windows Machine

**What:** Install the GitHub Actions runner as a Windows service on the existing local machine. The runner listens for job triggers from GitHub. Workflows run `python main.py` exactly as the host already does — same GPU, same FFmpeg, same `.env` file.

**When to use:** This is the only option that keeps GPU access (Whisper requires CUDA), avoids uploading 700MB WAV files to cloud runners, and costs nothing extra.

**Setup:**
```
# Install runner as Windows service (run once, as Administrator)
# Download from: github.com/{repo}/settings/actions/runners/new
# Config registers the runner with labels: self-hosted, windows, gpu

# Workflow targets it:
runs-on: [self-hosted, windows, gpu]
```

**Trade-offs:** Runner requires the host machine to be on and the service running. Acceptable for a bi-weekly show — no SLA requirement. If the machine is off when the cron fires, GitHub Actions re-runs the scheduled workflow at the next opportunity (within ~1h window). Alternative (cloud GPU runner at $0.07/min) costs ~$5/episode for Whisper — not worth it at current scale.

**Secrets vs .env:** The self-hosted runner executes on the machine that already has `.env`. The workflow can simply invoke `python main.py` — `load_dotenv()` in `config.py` reads `.env` at runtime. No GitHub Secrets needed for the self-hosted path. GitHub Secrets are the fallback if a cloud runner is ever used.

### Pattern 3: Dropbox Polling via Lightweight CI Script

**What:** `ci/poll.py` is a small script (not part of the main pipeline) that:
1. Connects to Dropbox (reads credentials from `.env`)
2. Lists files in `DROPBOX_FOLDER_PATH`
3. Compares against episodes already in `content_calendar.json`
4. If an unprocessed WAV is found, writes its filename to `ci/pending_episode.txt` and exits 0
5. If nothing new, exits 1 (which allows the GitHub Actions workflow to skip the expensive pipeline run)

**When to use:** Called from `poll.yml` on a cron schedule (e.g., every 6 hours). The workflow checks the exit code and only runs the episode pipeline step if exit 0.

```yaml
# .github/workflows/poll.yml
on:
  schedule:
    - cron: '0 */6 * * *'   # every 6 hours
  workflow_dispatch:          # always include for manual testing

jobs:
  poll:
    runs-on: [self-hosted, windows, gpu]
    steps:
      - uses: actions/checkout@v4
      - name: Poll Dropbox for new episodes
        id: poll
        run: python ci/poll.py
        continue-on-error: true
      - name: Process new episode
        if: steps.poll.outcome == 'success'
        run: python main.py latest --auto-approve
```

**Trade-offs:** Simple and transparent. The poll script is ~30 lines, fully unit-testable with mock Dropbox. No webhooks or event subscriptions needed. Polling interval of 6h is fine for a bi-weekly show.

### Pattern 4: Clip Distribution Spread vs. Same-Day

**What:** Rather than uploading all clips on episode release day, spread short-form clips across the week. The `ContentCalendar.plan_clips()` method assigns each clip to a specific platform+day slot.

**Recommended spread for 3 clips, bi-weekly schedule:**
```
Day 0 (release): Episode full video → YouTube
Day 1:           Clip 0 → YouTube Short, Twitter, TikTok
Day 3:           Clip 1 → Twitter, TikTok
Day 5:           Clip 2 → Twitter, TikTok
```

**Rationale:** Social algorithms reward consistent posting (not spikes). Spreading clips extends the promotion window from 1 day to 5 days. Each clip post can reference the full episode, driving late listeners to the back catalog. Evidence from content calendar research: weekly drip sustains engagement for longer than same-day dump.

**Trade-offs:** Clip uploads can no longer happen in a single `run_upload_scheduled()` call. The `upload-scheduled` command must be run periodically (daily via cron) to fire due slots. `main.py upload-scheduled` already exists and iterates pending schedules — it just needs to also read `content_calendar.json` clip slots.

### Pattern 5: Clip Upload via Existing `run_upload_scheduled()` Path

**What:** The clip calendar slots are consumed by extending `run_upload_scheduled()` to also check `content_calendar.json` for due clip slots. No new CLI command needed.

**When to use:** Daily cron in `poll.yml` (or a separate `upload.yml` that runs `python main.py upload-scheduled` daily at 9am).

**Integration point:**
```
pipeline/runner.py:run_upload_scheduled()
    EXISTING: reads output/ep_N/upload_schedule.json for episode-level platform uploads
    NEW: also calls ContentCalendar.get_pending_slots(now)
         for each due clip slot: calls clip-appropriate uploader
         marks slot as uploaded in content_calendar.json
```

This reuses all existing platform uploader code. The calendar is a scheduling layer on top of the existing upload machinery.

---

## Data Flow

### Full Episode Processing + Calendar Planning

```
GitHub Actions poll.yml cron trigger
    |
ci/poll.py
    +-- DropboxHandler.list_episodes()
    +-- ContentCalendar.is_processed(filename)
    |   if processed: exit 1 (no-op)
    |
    v (new episode found)
python main.py latest --auto-approve
    |
pipeline/steps/ingest.py      → download WAV
pipeline/steps/analysis.py    → transcribe, analyze, select clips
pipeline/steps/video.py       → render clip videos (subtitled)
pipeline/steps/distribute.py  → upload episode (YouTube, Spotify, RSS)
                               → ContentCalendar.plan_episode(episode_num, release_dt)
                               → ContentCalendar.plan_clips(episode_num, clip_paths)
                               → saves topic_data/content_calendar.json
```

### Daily Clip Distribution

```
GitHub Actions upload.yml daily cron (or same poll.yml with upload step)
    |
python main.py upload-scheduled
    |
pipeline/runner.py:run_upload_scheduled()
    |
    +-- [EXISTING] iterate output/ep_N/upload_schedule.json files
    |                check publish_at <= now, fire pending platform uploads
    |
    +-- [NEW] ContentCalendar.get_pending_slots(now)
              for each due ClipSlot:
                  call platform uploader (twitter, tiktok, youtube)
                  ContentCalendar.mark_slot_uploaded(episode, clip_index, platform, result)
                  saves content_calendar.json (atomic write)
```

### CI/CD Secrets Flow

```
.env (local file, never committed)
    |
    +-- config.py:load_dotenv()    (production: local Windows machine)
    |
    +-- GitHub Actions Secrets     (future: if cloud runner needed)
           OPENAI_API_KEY
           DROPBOX_APP_KEY / DROPBOX_APP_SECRET / DROPBOX_REFRESH_TOKEN
           YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET
           TWITTER_* / INSTAGRAM_* / TIKTOK_*
           DISCORD_WEBHOOK_URL
```

For self-hosted runner: `.env` is present on disk, `load_dotenv()` works as-is. No GitHub Secrets configuration required for initial setup. Add secrets only if/when switching to cloud runner.

---

## Integration Points

### New Modules

| Module | Integrates With | Direction |
|--------|-----------------|-----------|
| `content_calendar.py` | `pipeline/steps/distribute.py` | distribute calls `plan_episode()`, `plan_clips()` after uploads |
| `content_calendar.py` | `pipeline/runner.py:run_upload_scheduled()` | scheduler reads `get_pending_slots()` to fire clip uploads |
| `content_calendar.py` | `topic_data/content_calendar.json` | reads/writes file (atomic) |
| `ci/poll.py` | `dropbox_handler.py` (indirectly, via Dropbox SDK) | poll reads Dropbox listing |
| `ci/poll.py` | `content_calendar.py` | poll reads processed episode set |
| `.github/workflows/poll.yml` | `ci/poll.py`, `main.py` | workflow invokes scripts |

### Modified Existing Modules

| Module | Change | Risk |
|--------|--------|------|
| `pipeline/steps/distribute.py` | Call `ContentCalendar.plan_clips()` after clips are uploaded. Pass `release_date` from analysis to `plan_episode()`. | LOW — additive; no existing call sites change |
| `pipeline/runner.py:run_upload_scheduled()` | Add ContentCalendar `get_pending_slots()` check alongside existing `upload_schedule.json` loop. | LOW — additive block; existing episode schedule loop untouched |
| `config.py` | Add `CALENDAR_CLIP_SPREAD_DAYS` (default: 5), `DROPBOX_POLL_INTERVAL_HOURS` (default: 6). | MINIMAL |
| `main.py` | No change required — `upload-scheduled` already routes to `run_upload_scheduled()`. | NONE |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `ContentCalendar` ↔ `distribute.py` | `plan_episode()` + `plan_clips()` return void, write file | Called after real uploads complete; safe to skip on dry-run |
| `ContentCalendar` ↔ `run_upload_scheduled()` | `get_pending_slots(now)` returns list of due ClipSlot objects | Returns empty list if calendar missing — no-op behavior |
| `ci/poll.py` ↔ `content_calendar.json` | Read-only: checks processed episode set | Graceful: if calendar missing, assume no episodes processed |
| `ContentCalendar` write path | Atomic `.tmp` rename (matches `scheduler.py` pattern) | Prevents corrupt state if process killed mid-write |
| GitHub Actions ↔ self-hosted runner | HTTPS long-poll from runner to GitHub API | Runner initiates connection; no inbound firewall rule needed |

---

## Anti-Patterns

### Anti-Pattern 1: Storing Calendar in a Hand-Edited Config File

**What people do:** Define the release schedule as static config (e.g., `RELEASE_DAYS = ["Tuesday", "Thursday"]` in config.py).
**Why it's wrong:** The calendar needs per-episode state (was ep30 processed? which clips have been uploaded?). A config value can't track mutable state. Stateless config + mutable state = no safe way to avoid double-uploads.
**Do this instead:** `content_calendar.json` is generated state, not config. Release cadence preferences (spread days, posting hours) live in config.py as constants; the episode-specific schedule lives in the JSON file.

### Anti-Pattern 2: Using GitHub-Hosted Cloud Runners for Whisper

**What people do:** Run the full pipeline on GitHub-hosted runners (ubuntu-latest or windows-latest).
**Why it's wrong:** (a) No GPU — Whisper CPU mode is 3x slower, ~35 minutes for a 70-minute episode. (b) No CUDA — WhisperX/pyannote diarization won't run. (c) 700MB WAV uploads needed. (d) Cost: $0.007/min for Windows hosted runner = ~$25/episode at full duration.
**Do this instead:** Self-hosted runner on the existing Windows machine. GPU is present, CUDA is configured, WAV files don't move. Cost: $0.

### Anti-Pattern 3: Committing `.env` or Credentials to the Repo

**What people do:** Add API keys to `.github/workflows/*.yml` as inline values, or commit a `.env.ci` file for convenience.
**Why it's wrong:** Leaks credentials. GitHub Actions workflow files are public in public repos. Even in private repos, this is a security risk if the repo is ever made public or shared.
**Do this instead:** Self-hosted runner reads `.env` from disk via `load_dotenv()` — nothing in the workflow files. If cloud runners are used in future, secrets go in GitHub Actions Secrets (`${{ secrets.OPENAI_API_KEY }}`), injected as environment variables in the workflow step.

### Anti-Pattern 4: Firing All Clip Uploads in the Main Pipeline Run

**What people do:** Upload all clips to all platforms in the same `run_distribute()` call that uploads the full episode.
**Why it's wrong:** (a) Destroys the spread strategy — all clips land on day 0. (b) Makes the pipeline run ~30-60 minutes longer if Twitter/TikTok rate-limit. (c) If one clip upload fails, it can't be retried without re-running the whole pipeline.
**Do this instead:** Main pipeline uploads only the full episode (YouTube, Spotify, RSS). Clips are planned into `content_calendar.json` with future dates. Daily `upload-scheduled` fires due clip slots. This mirrors the existing `upload_schedule.json` pattern already in use for delayed episode uploads.

### Anti-Pattern 5: Separate CLI Command for Calendar Management

**What people do:** Add `python main.py calendar show`, `python main.py calendar plan ep30`, etc.
**Why it's wrong:** Adds surface area that must be maintained, tested, and documented. The calendar should be invisible plumbing — it updates automatically during the pipeline run.
**Do this instead:** Calendar operations are internal to `content_calendar.py` and triggered by existing pipeline hooks. The only user-visible interaction is: things get uploaded at the right times without manual intervention. If inspection is needed, `cat topic_data/content_calendar.json` is sufficient.

---

## Build Order (Dependency-Driven)

```
Phase A — ContentCalendar foundation (no pipeline dependencies):
  1. content_calendar.py
     - CalendarEntry and ClipSlot dataclasses
     - plan_episode(), plan_clips() — compute spread schedule
     - get_pending_slots(now) — returns due slots
     - mark_slot_uploaded() — updates status + atomic write
     - Standalone, testable with mock data
  2. tests/test_content_calendar.py

Phase B — CI/polling scripts (depends on ContentCalendar for episode check):
  3. ci/poll.py
     - Dropbox list → compare against content_calendar.json
     - exit 0/1 for workflow conditional
  4. .github/workflows/poll.yml
     - cron trigger + workflow_dispatch
     - calls poll.py then main.py if new episode
  5. .github/workflows/manual.yml (or add episode input to poll.yml)
     - workflow_dispatch with episode_number input

Phase C — Pipeline integration (depends on ContentCalendar):
  6. pipeline/steps/distribute.py
     - call plan_episode() + plan_clips() after upload
  7. pipeline/runner.py:run_upload_scheduled()
     - add ContentCalendar.get_pending_slots() check
  8. config.py
     - CALENDAR_CLIP_SPREAD_DAYS, DROPBOX_POLL_INTERVAL_HOURS

Phase D — Self-hosted runner setup (ops, not code):
  9. Install GitHub Actions runner as Windows service on local machine
     - Register at github.com/{repo}/settings/actions/runners
     - Labels: [self-hosted, windows, gpu]
     - Install as service so it survives reboots
```

Phases A and B are independent. Phase C requires Phase A. Phase D is ops-only (no code changes).

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (bi-weekly, ~50 eps/year) | JSON calendar file, local runner, adequate |
| Daily show (~365 eps/year) | Calendar JSON grows to ~5MB — add rolling trim (keep last 60 episodes) |
| Multiple shows | Parameterize calendar with show_id; separate `content_calendar_{show}.json` files |
| Cloud runner needed | Add GitHub Secrets for all API keys; `config.py` already reads from env vars, zero code change |

---

## Sources

- Direct code inspection: `scheduler.py`, `posting_time_optimizer.py`, `pipeline/runner.py`, `pipeline/steps/distribute.py`, `main.py`, `config.py`, `pipeline_state.py`, `dropbox_handler.py`
- [GitHub Actions: Configuring self-hosted runner as a service (Windows)](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/configuring-the-self-hosted-runner-application-as-a-service) — MEDIUM confidence (Windows-specific permission docs sparse)
- [GitHub Actions: Events that trigger workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows) — HIGH confidence (official docs)
- [GitHub Actions: Using secrets](https://docs.github.com/actions/security-guides/using-secrets-in-github-actions) — HIGH confidence (official docs)
- [GitHub Actions: Self-hosted runners reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners) — HIGH confidence (official docs)
- Existing patterns in codebase: `scheduler.py:save_schedule()` atomic write, `pipeline/runner.py:run_upload_scheduled()` polling pattern, `PipelineState` checkpoint JSON
- Podcast clip distribution research: WebSearch (MEDIUM confidence) — drip > dump for sustained week-long engagement; evidence from [Simplecast: Leveraging Podcast Clips for Cross-Promotion](https://blog.simplecast.com/how-to-leverage-podcast-clips-for-cross-promotion)

---

*Architecture research for: v1.3 Content Calendar & CI/CD — Fake Problems Podcast Automation*
*Researched: 2026-03-19*
