# Feature Research

**Domain:** Comedy podcast content calendar and clip distribution automation
**Researched:** 2026-03-18
**Milestone:** v1.3 — Content Calendar & CI/CD
**Confidence:** MEDIUM

---

## Context: What Already Exists (Do Not Re-Build)

These are built and fully integrated. New features in v1.3 must work *with* them, not replace them.

| Module | What It Does | Integration Point for v1.3 |
|--------|--------------|----------------------------|
| `scheduler.py` (`UploadScheduler`) | Per-platform hour-offsets from `.env`; writes `upload_schedule.json` with ISO datetimes; `mark_uploaded` / `mark_failed` state tracking | Content calendar extends this — per-clip slots replace per-platform monolithic delay |
| `posting_time_optimizer.py` (`PostingTimeOptimizer`) | Spearman correlation on engagement history; returns optimal weekday per platform; 15-episode confidence gate | Calendar consults optimizer for day-of-week; new platform hour defaults fill the hour slot the optimizer doesn't provide |
| `analytics.py` | Collects YouTube + Twitter engagement; stores per-episode JSON | Calendar reads engagement history to determine which clips performed best for slot prioritization |
| `audio_clip_scorer.py` | Energy-based scoring selects 3 clips per episode | Clip 1 (highest score) is the teaser candidate; calendar assigns it to D-1 slot |
| `pipeline/steps/` | Runs all production steps including Social (step 8) | Calendar generator runs after step 8 (Social), before 8.5 (Blog); clips must already exist |

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a bi-weekly comedy podcast pipeline must have for the calendar to be functional rather than decorative. Missing any of these means the release cycle is still manual.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Content calendar JSON per episode (`content_calendar.json`) defining episode drop datetime and per-clip scheduled datetimes | Any structured release plan requires a durable artifact the pipeline can read and a human can inspect; `upload_schedule.json` already exists for same-day uploads but has no multi-day awareness | LOW | Writes to `output/{epN}/content_calendar.json`; keys: episode, clip_1, clip_2, clip_3 with ISO datetimes and platform targets |
| Minimum spread schedule: clip 1 day of episode, clip 2 at D+2, clip 3 at D+4 | Industry baseline — same-day clip dump is treated as spam by algorithms; spread is the floor for sustained presence | LOW | Extend `UploadScheduler.create_schedule()` or write a new `ContentCalendar` class; derive clip offsets from episode anchor date |
| Platform hour defaults baked into config as fallbacks | `PostingTimeOptimizer` returns a weekday but not an hour; a calendar without hours is incomplete | LOW | Add `SCHEDULE_YOUTUBE_POSTING_HOUR`, `SCHEDULE_TWITTER_POSTING_HOUR`, `SCHEDULE_TIKTOK_POSTING_HOUR` to `config.py`; research-validated defaults: YouTube 14:00, Twitter 10:00, TikTok 19:00 |
| Dry-run calendar display before any upload runs | Operators need to see the full week plan before committing, especially for edgy content that may have compliance flags | LOW | Print table to stdout: item (episode / clip N), platform, scheduled datetime; honors `--dry-run` flag |
| GitHub Actions manual dispatch (`workflow_dispatch`) | Any CI approach must allow "run now" without waiting for a cron; this is the primary operational escape hatch | LOW | Standard `workflow_dispatch` in the workflow YAML; free on GitHub free tier; no infrastructure cost |
| Dropbox polling in CI (cron every 30 minutes) | Episodes land in Dropbox after recording; the pipeline should detect new files without manual intervention | LOW | GitHub Actions `schedule: cron` trigger; compare known episode list to Dropbox folder contents; trigger `python main.py` on new file detection |

### Differentiators (Competitive Advantage)

Features that make this pipeline smarter than a fixed delay configuration.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Teaser clip posted 24–48 hours BEFORE episode drop | Pre-episode teasers build audience anticipation and prime the algorithm; audiences already engaged when the episode drops produce higher initial velocity on Spotify/YouTube; standard practice for podcast promotion teams | MEDIUM | Clip 1 (highest `audio_clip_scorer` score) becomes the teaser; calendar assigns it to D-1 slot across Twitter and TikTok; full episode upload stays blocked until teaser window closes; requires pipeline to support a "pre-drop" execution mode |
| Self-hosted runner on the local GPU machine | Whisper transcription requires the NVIDIA GPU; cloud runners cannot run it at production speed and add cost; self-hosted runner gives CI the GPU without any recurring expense | LOW | Register the Windows 11 machine as a GitHub Actions self-hosted runner; workflow uses `runs-on: self-hosted`; existing `python main.py` command works unchanged |
| Comedy-aware platform hour targeting | Comedy Shorts peak 1–4 PM weekday and 8–10 PM weekend on YouTube; Twitter peaks 9 AM–12 PM EST weekdays; TikTok peaks 7–9 PM Tue–Fri; generic "post at noon" misses these windows by hours — early engagement velocity is the primary algorithm signal in 2025 | MEDIUM | Config defaults are research-validated; `PostingTimeOptimizer` overrides them when 15-episode confidence gate is met; calendar uses the better of the two |
| Bi-weekly gap content: mid-cycle clip repost | With 14 days between episodes, the 4-day clip spread still leaves ~10 days of algorithmic silence; one recycled clip from a prior episode at D+7 sustains presence without new production | LOW | Calendar adds an optional `throwback` slot at D+7; references clip paths from `output/{epN-1}/clips/`; gated on Instagram/TikTok uploaders becoming non-stubs |
| Calendar diff on re-run | When `main.py` is re-run before any clips upload (e.g., after compliance flag review), the calendar should warn if slots conflict with what was previously planned | LOW | Read existing `content_calendar.json`; if timestamps changed by more than 2 hours, print a warning listing the delta; operator confirms before overwrite |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Post all 3 clips same day as episode | "Get everything out at once" — feels efficient | Algorithm treats multiple posts in one session as one signal; no sustained presence between episodes; each clip competes with the episode for attention; most likely to be scroll-ignored | Spread: D-1 teaser, D0 episode + clip 1, D+2 clip 2, D+4 clip 3 |
| Automatic reschedule when a window is missed | "If the cron missed a window, compute a new optimal time and retry" | `mark_uploaded` in `scheduler.py` prevents duplicate uploads, but rescheduling resets that flag; creates ambiguous state if the upload actually completed but status wasn't flushed | Mark missed windows as `skipped` with timestamp; operator reruns with `--force`; no automatic state mutation |
| Cloud GPU runner for Whisper in CI | "Fully automated, no local machine dependency" | GitHub ML runners and AWS GPU instances add metered cost even on free orgs; Whisper on CPU is 3x slower and quality degrades on 70-minute episodes; fundamentally incompatible with zero-cost constraint | Self-hosted runner on the existing Windows 11 NVIDIA machine; CI triggers it; no cloud GPU spend |
| Dropbox push webhook trigger | "Run automatically the moment a file appears" | Dropbox webhooks require a public HTTPS endpoint; this is a Windows home machine behind NAT; adds ngrok/tunnel complexity that conflicts with the zero-infra constraint | Poll Dropbox on a 30-minute cron in GitHub Actions; compare known episode list to folder contents; fire on new detection |
| Full ML-driven calendar (model picks all slots) | "Let the data decide everything" | Only ~30 episodes of history; `PostingTimeOptimizer` already uses Spearman for day-of-week (correct tool for this dataset size per v1.2 architecture decision); adding ML for hours would overfit immediately | Keep `PostingTimeOptimizer` for weekday selection; use research-validated hour defaults as fallback; no new ML |
| Dynamic teaser window based on engagement velocity | "If clip 1 is getting traction after 6 hours, delay episode drop to ride the wave" | Requires continuous polling of YouTube/Twitter API; adds real-time state management to the pipeline; engagement velocity cannot be measured without waiting hours post-teaser; incompatible with the batch pipeline model | Post teaser at fixed D-1; observe engagement naturally; consider manually adjusting episode drop in exceptional cases |

---

## Feature Dependencies

```
Content Calendar Generator
    └──reads──> Episode release date (from output/{epN}/ or explicit config anchor)
    └──reads──> Clip paths (output/{epN}/clips/ — must exist; runs after step 5.1)
    └──reads──> PostingTimeOptimizer (best weekday per platform)
    └──reads──> Platform hour defaults (config.py — new)
    └──writes──> output/{epN}/content_calendar.json

Teaser Pre-Drop Slot (D-1)
    └──requires──> Content Calendar Generator (to know D-1 slot)
    └──requires──> Clip 1 path (highest audio_clip_scorer score)
    └──gate──> Full episode upload must NOT run until teaser window opens (D0)

GitHub Actions CI Workflow
    └──requires──> Self-hosted runner registered on GPU machine
    └──requires──> Dropbox polling script (compare known vs. available episodes)
    └──calls──> python main.py {epN} --auto-approve (unchanged command)
    └──reads──> Content Calendar Generator output (to align cron triggers with calendar slots)

PostingTimeOptimizer (existing)
    └──enhances──> Content Calendar Generator (weekday selection)
    └──falls back to──> Platform hour defaults (new config values)

Platform Hour Defaults (new config.py values)
    └──feeds into──> Content Calendar Generator
    └──overridden by──> PostingTimeOptimizer when 15-episode confidence gate is met

Mid-Cycle Throwback Slot (D+7)
    └──requires──> Content Calendar Generator (anchor + offset)
    └──requires──> Clip paths from prior episode (output/{epN-1}/clips/)
    └──blocked on──> Instagram/TikTok uploaders becoming functional (currently stubs)
```

### Dependency Notes

- **Content Calendar must run after step 5.1 (clip approval):** clip paths do not exist until approval is complete. Calendar slot is step 8.6 (between Social and Blog).
- **Teaser feature is a calendar slot, not a separate pipeline step:** it is activated by the calendar placing clip 1 on D-1; the existing `UploadScheduler.create_schedule()` handles the actual upload; no new uploader code needed.
- **GitHub Actions CI requires self-hosted runner:** cloud runners cannot run Whisper at production speed. The local Windows 11 machine with NVIDIA GPU must register as a self-hosted runner via the GitHub Actions runner application.
- **Dropbox polling must not use push webhooks:** polling is the only viable zero-infra approach; do not implement both.
- **Platform hour defaults are a prerequisite for the calendar:** the calendar cannot produce meaningful ISO datetimes without hours; this config addition must happen in Phase 1 of implementation.

---

## MVP Definition

### Launch With (v1.3 core)

Minimum viable content calendar and CI — what's needed to automate the bi-weekly cycle without manual intervention.

- [ ] Content calendar generator: produces `content_calendar.json` with per-item (episode, clip 1, clip 2, clip 3) scheduled datetimes using spread schedule (D0, D+2, D+4) and platform-aware hours
- [ ] Platform hour defaults in `config.py`: `SCHEDULE_YOUTUBE_POSTING_HOUR=14`, `SCHEDULE_TWITTER_POSTING_HOUR=10`, `SCHEDULE_TIKTOK_POSTING_HOUR=19` (research-validated; overridable by env var)
- [ ] Dry-run calendar display: print full week schedule as a table before any upload; honors `--dry-run` flag
- [ ] GitHub Actions workflow YAML with `workflow_dispatch` and `schedule: cron` (every 30 min) for Dropbox polling
- [ ] Self-hosted runner registration instructions/config for the Windows 11 GPU machine
- [ ] Dropbox polling script: compare known episode numbers to Dropbox folder; trigger pipeline on new detection

### Add After Validation (v1.3.x)

Add once the calendar is running through at least 2 full bi-weekly cycles.

- [ ] Teaser clip at D-1 before episode drop — requires confirming the calendar's D0 gate logic is reliable
- [ ] Calendar diff/conflict warning on re-run — add once the JSON format is stable and operators are familiar with the output
- [ ] Mid-cycle throwback clip slot (D+7) — add once Instagram or TikTok uploaders are functional

### Future Consideration (v2+)

- [ ] Comedy clip role classifier (teaser hook vs. punchline vs. controversy bait) — meaningful only after 10+ episodes of calendar data show which roles drive engagement
- [ ] Dynamic teaser window adjustment — requires real-time engagement polling, incompatible with batch pipeline model today

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Content calendar JSON with spread schedule | HIGH | LOW | P1 |
| Platform hour defaults in config | HIGH | LOW | P1 |
| Dry-run calendar display | HIGH | LOW | P1 |
| GitHub Actions manual dispatch | HIGH | LOW | P1 |
| Self-hosted runner (GPU machine) | HIGH | LOW | P1 |
| Dropbox polling cron | HIGH | LOW | P1 |
| Teaser clip at D-1 | MEDIUM | MEDIUM | P2 |
| PostingTimeOptimizer hour extension | MEDIUM | MEDIUM | P2 |
| Calendar diff on re-run | MEDIUM | LOW | P2 |
| Mid-cycle throwback clip (D+7) | LOW | LOW | P3 — blocked on stubs |
| Comedy clip role classifier | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for v1.3 launch — enables automated bi-weekly cycle
- P2: Should have, add once core calendar is validated
- P3: Nice to have — future milestone material or blocked on other work

---

## Comedy-Specific Pattern Notes

Based on research (MEDIUM confidence — WebSearch verified against multiple sources):

**Clip timing windows:**
- YouTube Shorts comedy: 1–4 PM weekday, 8–10 PM weekend; Wednesday/Thursday are the highest-engagement days
- Twitter/X comedy clips: Monday–Friday 9 AM–12 PM EST; native video upload gets 40% more engagement than shared links — the existing Twitter uploader must post video directly
- TikTok: Tuesday–Friday 7–9 PM; TikTok is the best platform for pre-episode teasers

**Algorithm mechanics:**
- First 2–3 hours after posting drive discovery velocity; post at the START of the peak window, not the middle
- Multiple posts in one session are treated as one signal; one clip per platform per day is the effective maximum
- Spread clips across days, not hours — platforms suppress accounts that post the same content type multiple times in one day

**Teaser evidence:**
- Pre-episode teasers posted 24–48 hours before drop consistently cited as driving higher episode engagement at launch
- Mechanism: audience priming + algorithm pre-warming on the channel
- TikTok is specifically called out as the best teaser platform; YouTube Shorts and Twitter work but are secondary

**Bi-weekly cadence gap:**
- 14 days between episodes means 4-day clip spread still leaves ~10 days of algorithmic silence
- Mid-cycle throwback or bonus content is the only no-production way to maintain presence
- This is a differentiator, not table stakes — cannot be implemented until Instagram/TikTok uploaders are functional

**Short-form builds awareness, not downloads (important calibration):**
- Short-form video builds brand awareness on a long arc, not weekly download KPIs
- Algorithm "waves" can take hours or days to start; don't optimize the calendar around same-day download spikes

---

## Competitor Feature Analysis

| Feature | SaaS tools (Buzzsprout, Castos, Buffer) | Manual indie workflow | Our Approach |
|---------|------------------------------------------|-----------------------|--------------|
| Clip distribution timing | Fixed delay from episode drop; no comedy-aware slots | Ad-hoc; usually same-day dump | Research-validated spread (D-1 teaser, D0, D+2, D+4) with platform-specific hour targeting |
| Calendar persistence | Dashboard with calendar view | Spreadsheet or nothing | JSON artifact per episode in `output/`; dry-run print; no UI |
| CI automation trigger | SaaS-managed; no GPU access | None; manual `python main.py` | GitHub Actions self-hosted on GPU machine; polls Dropbox; manual dispatch escape hatch |
| Bi-weekly gap content | No cadence awareness | Manual reposts | Optional throwback slot in calendar; gated on stubs becoming functional |
| Comedy voice in scheduling | Not applicable | Host judgment | Calendar inherits `VOICE_PERSONA` constraint from existing pipeline; clip role classifier deferred |

---

## Sources

- [The Ultimate Guide For Creating Podcast Clips That Go Viral On Shorts in 2025 | Fame](https://www.fame.so/post/ultimate-podcast-clip-guide) — MEDIUM confidence
- [Best Times to Post on YouTube & Shorts in 2025 | Sprout Social](https://sproutsocial.com/insights/best-times-to-post-on-youtube/) — MEDIUM confidence
- [Best Time to Post YouTube Shorts in 2025 | Screenstory](https://www.screenstory.io/blog/the-best-time-to-post-youtube-shorts-in-2025) — MEDIUM confidence
- [Best Times to Post TikTok, YouTube Shorts, and Instagram Reels in 2025 | ClipGOAT](https://www.clipgoat.com/blog/best-times-to-post-tiktok-youtube-shorts-and-instagram-reels-in-2025-(and-how-to-automate-it)) — MEDIUM confidence
- [Best Time to Post on Twitter (X) 2025 | Hashmeta](https://hashmeta.com/insights/best-time-post-twitter) — MEDIUM confidence
- [TikTok's Impact on Podcasting: How (+ What) to Post in 2025 | Cohost](https://www.cohostpodcasting.com/resources/tiktok-for-podcasters) — MEDIUM confidence
- [Podcast Promotion Strategies 2025 | The Podcast Consultant](https://thepodcastconsultant.com/blog/podcast-promotion-strategies-to-boost-your-audience-in-2025) — MEDIUM confidence
- [Podcast Content Calendar Guide | Galati Media](https://galatimedia.com/podcast-content-calendar-the-ultimate-guide-for-growth-organization/) — MEDIUM confidence
- [State of Video Podcasts 2025 | Sweet Fish Media](https://www.sweetfishmedia.com/blog/the-2025-state-of-video-podcasts) — MEDIUM confidence
- [GitHub Actions Self-Hosted Runner Guide 2025 | DevOps Tooling](https://thedevopstooling.com/github-actions-self-hosted-runner/) — HIGH confidence (official documentation backed)
- [Self-hosted runners | GitHub Docs](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners) — HIGH confidence (official)

---
*Feature research for: comedy podcast content calendar and clip distribution (v1.3 milestone)*
*Researched: 2026-03-18*
