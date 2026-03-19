# Project Research Summary

**Project:** Podcast Automation — v1.3 Content Calendar & CI/CD
**Domain:** Bi-weekly comedy podcast pipeline automation (content scheduling + CI/CD)
**Researched:** 2026-03-19
**Confidence:** HIGH

## Executive Summary

v1.3 adds two capabilities to an already-working pipeline: a content calendar that spreads clip distribution across a week instead of dumping everything on release day, and GitHub Actions CI/CD that triggers automatically when a new episode appears in Dropbox. The research is unusually clean because the existing codebase (scheduler.py, posting_time_optimizer.py, pipeline/runner.py) already provides the scaffolding — v1.3 extends it, not replaces it. The recommended approach is additive: one new module (content_calendar.py), one new CI script (ci/poll.py), two workflow YAML files, and targeted modifications to distribute.py and runner.py. No new Python packages are needed.

The key architectural decision is self-hosted GitHub Actions runner on the existing Windows 11 GPU machine. Cloud runners cannot run Whisper (no GPU on free tier; paid GPU runners cost ~$5/episode), and they cannot access local Dropbox sync folders or credential files without significant additional infrastructure. The self-hosted runner solves all three problems at zero cost. Dropbox monitoring uses polling (every 4-6 hours via GitHub Actions cron) rather than webhooks, which require a public HTTPS endpoint — polling is the correct pattern for a home machine behind NAT.

The dominant risk is the comedy content dimension: automated posting without human review creates real exposure, as demonstrated by ep29's YouTube cancer misinformation strike. Research is emphatic that CI must stop before distribution steps and require explicit human approval. Concurrency control (preventing duplicate pipeline runs on the same episode) and credential security (secrets split into individual scalar values, not JSON blobs) are the two technical pitfalls that, if missed, cause the most costly recovery scenarios.

## Key Findings

### Recommended Stack

The v1.3 stack adds no new Python packages. GitHub Actions with a self-hosted runner on the existing Windows 11 NVIDIA machine handles CI/CD. Dropbox polling uses the existing dropbox SDK (v12.0.2) already in requirements.txt with cursor-based change detection. The content calendar is pure stdlib (datetime, json). GitHub repository secrets handle credentials for any future cloud runner path.

**Core technologies:**
- GitHub Actions self-hosted runner: CI/CD — only option with GPU access at zero cost; installs as a Windows service for reboot resilience
- dropbox SDK 12.0.2 (existing): Dropbox polling — cursor-based `files_list_folder_continue` detects new episodes without webhooks
- Python stdlib datetime/json: Content calendar — no new packages; date arithmetic is sufficient for bi-weekly spread scheduling
- GitHub Actions secrets: Credential management — maps to existing `os.environ.get()` calls in config.py without code changes

### Expected Features

**Must have (table stakes — v1.3 launch):**
- Content calendar JSON per episode with spread schedule (D0 episode, D+1 clip 0, D+3 clip 1, D+5 clip 2) — pipeline's current same-day dump is treated as spam by algorithms
- Platform hour defaults in config.py (YouTube 14:00, Twitter 10:00, TikTok 19:00) — calendar cannot produce meaningful ISO datetimes without hours
- Dry-run calendar display before any upload commits — operators must see the full week plan first
- GitHub Actions poll workflow (cron every 4-6 hours) to detect new Dropbox episodes — eliminates manual trigger requirement
- GitHub Actions manual dispatch workflow — escape hatch for immediate episode processing
- Self-hosted runner on GPU machine — prerequisite for all CI workflows to function

**Should have (add after 2-cycle validation):**
- Teaser clip at D-1 before episode drop — pre-episode teasers drive higher launch-day engagement velocity; requires D0 gate logic to be proven reliable first
- Calendar diff/conflict warning on re-run — warns when timestamps changed significantly; add once JSON format is stable
- Mid-cycle throwback clip at D+7 — sustains presence in 14-day gap; blocked on Instagram/TikTok uploaders becoming functional

**Defer to v2+:**
- Comedy clip role classifier (teaser hook vs. punchline vs. controversy bait) — requires 10+ episodes of calendar data
- Dynamic teaser window adjustment based on engagement velocity — incompatible with batch pipeline model

### Architecture Approach

The architecture adds a Trigger Layer (GitHub Actions workflows + ci/poll.py) and a Calendar Layer (content_calendar.py) on top of the unchanged existing pipeline. The calendar is a generated, mutable JSON state file at topic_data/content_calendar.json — not hand-edited config. Clip upload slots are consumed by extending the existing run_upload_scheduled() in pipeline/runner.py to also check ContentCalendar.get_pending_slots(now), reusing all existing platform uploader code. The pipeline splits cleanly: main run (episode + step 1-6 production) and daily upload-scheduled run (fires due clip slots from the calendar).

**Major components:**
1. content_calendar.py — ContentCalendar class with plan_episode(), plan_clips(), get_pending_slots(), mark_slot_uploaded(); atomic writes via .tmp rename matching scheduler.py pattern
2. ci/poll.py — lightweight Dropbox polling script (~30 lines); compares Dropbox listing to calendar's processed episodes; exits 0 (new episode found) or 1 (nothing new) for workflow conditional
3. .github/workflows/poll.yml + manual.yml — cron trigger (every 4-6h) for polling; workflow_dispatch for manual episode processing; both target `runs-on: [self-hosted, windows, gpu]`
4. Modified pipeline/steps/distribute.py — calls ContentCalendar.plan_episode() + plan_clips() after episode upload completes
5. Modified pipeline/runner.py:run_upload_scheduled() — adds ContentCalendar.get_pending_slots() check alongside existing upload_schedule.json loop

### Critical Pitfalls

1. **Auto-posting edgy comedy content without human review** — CI must stop after step 6 (MP3 production) and fire a Discord notification with a GitHub Actions `environment: production` gate requiring named reviewer approval before any distribution step runs. Never use `--auto-approve` or `--force` for steps 7.5+. The ep29 YouTube strike is not hypothetical.

2. **Concurrent pipeline runs corrupting episode state** — Add `concurrency: group: podcast-pipeline-${{ inputs.episode_number || 'scheduled' }}` with `cancel-in-progress: false` to every workflow. Two simultaneous dispatches for the same episode create duplicate uploads and corrupted checkpoint files.

3. **Secrets exposure via CI logs or JSON credential blobs** — Split all OAuth credentials into individual scalar secrets (not single JSON blobs); GitHub's log redaction does not reliably mask structured data. Pin all `uses:` to full commit SHA (not @v4 tags) to guard against supply chain compromise (tj-actions March 2025 incident affected 23,000+ repositories).

4. **OAuth token expiry silently failing uploads** — Add a pre-flight credential check step at job start that calls a low-cost read endpoint for each platform. YouTube OAuth apps in "Testing" status issue tokens that expire every 7 days. Exit non-zero on 401 before any upload step runs.

5. **Dropbox polling triggering on partial uploads or non-episode files** — Filter by explicit filename pattern (ep[0-9]+\.wav), file size sanity check (>100MB), and file-age check (server_modified > 5 minutes ago). Deduplication via content_calendar.json's processed episode set prevents re-processing.

## Implications for Roadmap

Based on combined research, the build order is driven by one dependency chain: ContentCalendar must exist before the CI workflows can use it to deduplicate episodes, and the self-hosted runner must be registered before any workflow can run. Within that, ContentCalendar is standalone and fully testable in isolation before any pipeline changes are required.

### Phase A: ContentCalendar Foundation

**Rationale:** No dependencies on existing pipeline code; fully testable in isolation with mock data. Everything else depends on this module existing.
**Delivers:** content_calendar.py with CalendarEntry + ClipSlot dataclasses, plan_episode(), plan_clips(), get_pending_slots(), mark_slot_uploaded(), atomic write pattern; tests/test_content_calendar.py; config.py additions (CALENDAR_CLIP_SPREAD_DAYS, platform hour defaults).
**Addresses:** Content calendar JSON per episode (P1), spread schedule (D0, D+1, D+3, D+5), platform hour defaults, dry-run display.
**Avoids:** Anti-pattern of storing calendar state in hand-edited config; mutable state must live in the JSON file, not config constants.

### Phase B: CI Trigger Layer

**Rationale:** Depends on ContentCalendar for episode deduplication (is_processed check). Can be built in parallel with Phase C once Phase A is complete. Self-hosted runner setup is an ops step that unblocks all workflow testing.
**Delivers:** ci/poll.py with filename/size/age/dedup guards; .github/workflows/poll.yml (cron every 4-6h); .github/workflows/manual.yml (workflow_dispatch); self-hosted runner installed as Windows service with labels [self-hosted, windows, gpu].
**Addresses:** Dropbox polling cron (P1), manual dispatch (P1), self-hosted runner (P1).
**Avoids:** Dropbox false-positive triggers (filename pattern + size + age guards); webhook complexity (polling is the correct approach); WAV file artifact passing between jobs (single-job architecture).

### Phase C: Pipeline Integration

**Rationale:** Depends on Phase A (ContentCalendar class). Modifies existing production code, so must come after the standalone module is tested. Changes are additive with no existing call site modifications.
**Delivers:** Modified distribute.py calling plan_episode() + plan_clips() after upload; modified runner.py:run_upload_scheduled() checking get_pending_slots(); daily upload-scheduled cron workflow or cron step in poll.yml.
**Addresses:** Clip spread schedule execution; daily upload-scheduled cron integration.
**Avoids:** Firing all clip uploads in the main pipeline run (destroys spread strategy; introduces rate-limit risk during a 60-90 min job).

### Phase D: Human Review Gate & Security Hardening

**Rationale:** Must be in place before any end-to-end CI run that includes distribution steps. Can be designed concurrently with A/B/C but must be verified before first production run.
**Delivers:** GitHub Actions `environment: production` with required reviewers (configured in GitHub UI, not just YAML); Discord notification with approve/cancel link and clip preview; "pause all scheduled posts" kill switch (repository variable); pre-flight credential check step; concurrency group in all workflows; third-party action SHA pinning; disk cleanup step.
**Addresses:** Human review requirement for comedy content (critical), concurrent run corruption prevention, OAuth token expiry detection, secrets security, runner disk exhaustion.
**Avoids:** Auto-posting content during breaking news events; duplicate YouTube uploads; silent 401 failures; secrets in workflow logs; tj-actions-style supply chain compromise.

### Phase Ordering Rationale

- Phase A first because ContentCalendar is a standalone, testable unit with no pipeline dependencies — fastest to validate and lowest risk.
- Phase B in parallel with Phase C once Phase A completes. ci/poll.py needs ContentCalendar only for the read-only is_processed() check; the pipeline integration (Phase C) is a more invasive production code change.
- Phase D can be developed concurrently with B and C but must be verified before any distribution workflow is merged. The GitHub `environment: production` gate must be configured in the GitHub UI — YAML alone does nothing.
- Self-hosted runner setup (Phase B ops step) is a prerequisite for testing any workflow YAML — do it early in Phase B even though it requires no code.

### Research Flags

Phases needing deeper research during planning:
- **Phase D (Human Review Gate):** The GitHub Actions `environment: production` required-reviewers feature availability on the Free plan (vs. Team plan) needs verification for personal-account private repositories. Fallback is a manual Discord approve link triggering a separate `workflow_dispatch`. Confirm before designing the approval UX.

Phases with standard patterns (skip research-phase):
- **Phase A (ContentCalendar):** Pure Python stdlib, well-understood JSON state pattern, mirrors existing scheduler.py atomic write pattern already in the codebase.
- **Phase B (CI Trigger Layer):** GitHub Actions cron + workflow_dispatch are official, heavily documented patterns. Dropbox cursor-based polling is documented in official Dropbox SDK guides.
- **Phase C (Pipeline Integration):** Extends existing run_upload_scheduled() and distribute.py with additive, low-risk changes. No new external dependencies.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new packages; all technology choices backed by official docs or existing codebase. Self-hosted runner is the only viable GPU path — no ambiguity. |
| Features | MEDIUM | Comedy-specific posting time windows (YouTube 1-4PM, Twitter 9AM-12PM, TikTok 7-9PM) are from MEDIUM-confidence sources (Sprout Social, ClipGOAT). Platform algorithms shift; these are research-validated defaults, not guarantees. PostingTimeOptimizer will eventually override them with show-specific data. |
| Architecture | HIGH | Based on direct code inspection of all relevant existing modules. ContentCalendar JSON state pattern mirrors scheduler.py (already proven). Integration points are additive with low modification risk. |
| Pitfalls | HIGH | Most pitfalls verified against official GitHub docs. tj-actions supply chain incident is documented public record. ep29 YouTube strike is confirmed project history. OAuth testing-status 7-day expiry is confirmed Google behavior. |

**Overall confidence:** HIGH

### Gaps to Address

- **GitHub Actions `environment:` feature on Free plan:** Required-reviewers on environments may require GitHub Team for organization repos. Verify for a personal-account private repo before committing to this design; fallback is a Discord-triggered `workflow_dispatch` approval flow.
- **Comedy-specific posting hour defaults:** Platform timing research is MEDIUM confidence and based on general audiences, not niche comedy. The PostingTimeOptimizer (already in codebase from v1.2) will override these with show-specific data once the 15-episode confidence gate is met. Accept this uncertainty and let engagement data correct it over 2-3 cycles.
- **Instagram/TikTok uploader status:** Mid-cycle throwback slot (D+7) is explicitly blocked on these uploaders becoming functional. Research does not resolve when this will happen — flag for v1.3.x planning.
- **WhisperX model cache behavior after Windows Update / CUDA driver change:** Pitfalls research recommends a weekly smoke-test workflow. Confirm the Whisper model cache path and version before first production run to prevent cache miss on first episode.
- **YouTube Data API quota during daily upload-scheduled runs:** If upload-scheduled fires clip uploads daily, verify those API calls do not compete with the main episode upload for the 10,000 daily quota. Analytics collection (run-analytics.yml) should run on a separate schedule to avoid quota conflicts.

## Sources

### Primary (HIGH confidence)
- GitHub Docs: Adding self-hosted runners — Windows service install, GPU access, private repo security guidance
- GitHub Docs: Events that trigger workflows — cron schedule, workflow_dispatch inputs
- GitHub Docs: Using secrets in GitHub Actions — repository vs. environment secrets
- GitHub Actions Concurrency Docs — concurrency group patterns and cancel-in-progress behavior
- Dropbox Detecting Changes Guide — server-side cursor polling; webhook requires public endpoint (confirmed)
- Direct code inspection: scheduler.py, posting_time_optimizer.py, pipeline/runner.py, pipeline/steps/distribute.py, main.py, config.py, dropbox_handler.py
- tj-actions supply chain compromise (March 2025) — documented incident with public disclosure; 23,000+ repositories affected
- GitHub Actions self-hosted runner minimum version enforcement (v2.329.0, February 2026) — official changelog
- GitHub Actions GPU Runners GA — requires paid GitHub Team/Enterprise plan; confirmed for free tier unavailability
- Windows Server 2025 runner disk space — official runner-images issue tracker

### Secondary (MEDIUM confidence)
- Sprout Social: Best times to post on social media 2025 — platform hour defaults (general audience, not comedy-specific)
- ClipGOAT: Best times to post TikTok, YouTube Shorts, Instagram Reels 2025 — comedy timing windows
- Simplecast: Leveraging Podcast Clips for Cross-Promotion — drip > dump engagement evidence
- Galati Media: Podcast Content Calendar Guide — bi-weekly gap content patterns
- GitHub Community: Bi-weekly cron workaround — no native bi-weekly cron confirmed; modulo approach documented
- Sysdig: Self-hosted runner security risks — private repo + sole owner mitigates risk

### Tertiary (LOW confidence)
- YouTube Bulk Upload Detection Risk 2025 (social media post) — directional signal only; add inter-upload delays as a precaution but do not treat as confirmed platform behavior

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
