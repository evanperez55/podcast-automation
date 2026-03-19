# Technology Stack

**Project:** Podcast Automation — v1.3 Content Calendar & CI/CD
**Researched:** 2026-03-18
**Confidence:** HIGH (GitHub Actions), HIGH (Dropbox polling), MEDIUM (bi-weekly scheduling approach)

---

## Existing Stack (Do Not Replace)

Validated, working dependencies. Not candidates for replacement or re-research.

| Technology | Version (pinned) | Role |
|------------|-----------------|------|
| Python | 3.12+ | Language |
| FFmpeg binary | C:\ffmpeg\bin\ffmpeg.exe | Media processing engine |
| openai | >=1.0.0 | GPT-4o for content optimization |
| tweepy | 4.14.0 | Twitter API v2 |
| google-api-python-client | 2.116.0 | YouTube Data API + Analytics v2 |
| praw | 7.7.1 | Reddit topic research |
| dropbox | 12.0.2 | Dropbox upload + file polling (already in use) |
| pandas | >=2.0.0,<3.0.0 | Cross-episode analytics |
| numpy | >=1.26.4,<2.0.0 | Constrained by torch==2.1.0 |
| scipy | >=1.11.0,<2.0.0 | Statistical correlation |

---

## New Stack Additions (v1.3 Only)

### 1. GitHub Actions: Self-Hosted Runner on Windows (LOCAL machine)

**Recommended:** Self-hosted runner installed as a Windows service on the existing dev machine.

**Why self-hosted over GitHub cloud runners:**
- Whisper requires NVIDIA GPU + CUDA. GitHub's free cloud runners have no GPU.
- GitHub's GPU-hosted runners (T4) require GitHub Team/Enterprise plan — paid tier.
- Existing environment already has all dependencies installed (FFmpeg, torch, CUDA drivers, credentials).
- A cloud runner would need to reinstall ~5GB of dependencies on every run (torch, WhisperX, CUDA) — impractical.
- The pipeline accesses local Dropbox sync folder and local credential files. A cloud runner cannot reach these without significant additional infrastructure (Dropbox API download step, secret management for all credential files).

**Self-hosted runner setup:**
```bash
# Run as Administrator in PowerShell
mkdir C:\actions-runner && cd C:\actions-runner
# Download from: Settings → Actions → Runners → New self-hosted runner (Windows/x64)
.\config.cmd --url https://github.com/evanp/podcast-automation --token <TOKEN>
# Install as Windows service so it runs on boot
.\svc.sh install
.\svc.sh start
```

**Labels to assign the runner:** `self-hosted`, `windows`, `gpu`
**Run-as user:** The account that owns the Dropbox sync folder and Python virtualenv.

**Security note:** This is a private repository. Self-hosted runners on private repos are standard practice. The runner only accepts jobs from workflows in this repo. Risk is low because only the repo owner pushes code. Reference: GitHub recommends self-hosted runners only for private repos — this qualifies.

**Confidence:** HIGH — official docs confirm Windows service install path; GPU access works natively when runner runs as the same user account that owns the CUDA installation.

---

### 2. GitHub Actions: Workflow Files (no new Python package)

**Recommended:** Two workflow files under `.github/workflows/`.

**Why two files:**
- `poll.yml` — runs on a cron schedule to detect new Dropbox files (lightweight, no GPU needed)
- `process.yml` — triggered by `workflow_dispatch` to run the full pipeline (heavy, GPU needed)

This separation means the poll job can theoretically run on a lightweight cloud runner (no GPU), while the heavy processing job runs on the self-hosted runner. In practice, both can run on the self-hosted runner for simplicity.

**Workflow triggers needed:**
```yaml
# poll.yml — check for new episode every few hours
on:
  schedule:
    - cron: '0 */4 * * *'   # every 4 hours
  workflow_dispatch:          # manual trigger for testing

# process.yml — run full pipeline
on:
  workflow_dispatch:
    inputs:
      episode:
        description: 'Episode ID (e.g. ep31) or "latest"'
        required: false
        default: 'latest'
```

**No bi-weekly cron for the pipeline itself.** The podcast is released bi-weekly but the upload date varies. A cron trigger cannot know when an episode is ready — only Dropbox polling can detect that. The bi-weekly cadence is encoded in the content calendar output, not in workflow scheduling.

**Confidence:** HIGH — standard GitHub Actions pattern for event-driven automation.

---

### 3. Dropbox Trigger: Polling via Existing `dropbox` SDK (no new package)

**Recommended:** Periodic polling using `files_list_folder` + stored cursor, NOT webhooks.

**Why polling over webhooks:**
- Webhooks require a publicly accessible HTTPS endpoint. Running one from a Windows home machine requires ngrok, Cloudflare Tunnel, or a VPS reverse proxy — unnecessary infrastructure.
- Long-polling (`/files/list_folder/longpoll`) is the interactive client approach; for a server-side background job, simple cron-based polling is cleaner and more reliable.
- The existing `dropbox==12.0.2` SDK supports `files_list_folder` and cursor management. No new package needed.
- The cron-triggered GitHub Action runs every 4 hours — if a new episode appears, the workflow detects it on the next poll and triggers processing. A 4-hour window is acceptable for an automated pipeline.

**Implementation pattern:**
```python
# dropbox_poller.py — minimal new module
import dropbox
import json, os

CURSOR_FILE = "data/dropbox_cursor.json"

def check_for_new_episode(dbx, watch_folder="/Podcast/raw"):
    if os.path.exists(CURSOR_FILE):
        cursor = json.load(open(CURSOR_FILE))["cursor"]
        result = dbx.files_list_folder_continue(cursor)
    else:
        result = dbx.files_list_folder(watch_folder)

    new_files = [e for e in result.entries
                 if isinstance(e, dropbox.files.FileMetadata)
                 and e.name.endswith('.wav')]

    # Always save latest cursor
    json.dump({"cursor": result.cursor}, open(CURSOR_FILE, "w"))
    return new_files
```

The cursor is committed to the repo (or stored in a repo-tracked file) so the next poll resumes from where the last one left off. Only new files since the last check are returned.

**Why not the Dropbox Python watch folder (local sync daemon):** The self-hosted runner runs workflows on demand, not as a persistent process. The cron trigger + API poll is more reliable than a background daemon.

**Confidence:** HIGH — Dropbox docs explicitly recommend this pattern for server-side change detection; SDK version 12.0.2 already in requirements.txt.

---

### 4. Content Calendar: No New Package — Use stdlib `datetime` + `json`

**Recommended:** A new `content_calendar.py` module using only Python stdlib (`datetime`, `json`, `calendar`) plus existing `scheduler.py` patterns.

**Why no new package:**
- Content calendar for a bi-weekly podcast means: "given a release date, compute when to post the episode, then spread 3 clips across the following 5 days."
- This is date arithmetic, not calendar infrastructure. `datetime.timedelta`, `datetime.date.weekday()`, and `calendar.weekday()` handle everything needed.
- Tools like `icalendar`, `arrow`, `pendulum`, or `dateutil` add dependencies for zero benefit here. The pipeline is CLI-driven with no web frontend to display iCal output.

**What the content calendar computes:**
1. Episode release date → post to YouTube + RSS (day 0)
2. Clip 1 → post day 1 or 2 (highest-energy clip, first)
3. Clip 2 → post day 3
4. Clip 3 → post day 5 or 6
5. Blog post → post day 1
6. Each posting time calculated using existing `PostingTimeOptimizer` from `scheduler.py`

**Bi-weekly cadence handling:** The calendar module does not use cron for bi-weekly scheduling. Instead, it generates a `content_calendar.json` file with absolute ISO timestamps for each asset. The pipeline reads this file at distribution time instead of computing delays on the fly.

**Confidence:** HIGH — stdlib only, no versioning risk.

---

### 5. GitHub Actions Secrets: Repository Secrets (no new package)

**Recommended:** GitHub repository secrets for all credentials the workflow needs.

**Secrets to configure in GitHub Settings → Secrets:**
- `OPENAI_API_KEY` — GPT-4o
- `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN` — Dropbox API
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` — YouTube OAuth
- `TWITTER_BEARER_TOKEN`, `TWITTER_API_KEY`, `TWITTER_API_SECRET` — Twitter
- `DISCORD_WEBHOOK_URL` — notifications
- `HF_TOKEN` — HuggingFace for pyannote diarization

**Why NOT .env file committed to repo:** Obvious. All secrets must live in GitHub Secrets, mapped to environment variables in the workflow `env:` block.

**Critical for self-hosted runner:** The secrets are injected as environment variables at workflow execution time, matching what `config.py` already reads via `os.environ.get()`. No code changes needed in config.py — the existing env var pattern is already workflow-compatible.

**Why NOT GitHub Environment secrets:** Repository secrets are sufficient for a single-environment private repo. Environment secrets add approval gates (useful for staging → production promotion) which is unnecessary overhead here.

**Confidence:** HIGH — standard GitHub Actions secrets pattern.

---

## Packages Evaluated and Rejected (v1.3)

| Package | Use Case | Decision | Reason |
|---------|----------|----------|--------|
| `dropbox-webhooks` / webhook framework | Real-time Dropbox file detection | Rejected | Requires public HTTPS endpoint; cron polling via existing SDK is sufficient and simpler |
| `pendulum` / `arrow` / `python-dateutil` | Content calendar date arithmetic | Rejected | stdlib `datetime` is sufficient for day arithmetic; no timezone complexity in a single-timezone local pipeline |
| `APScheduler` | Persistent cron daemon on Windows | Rejected (was rejected in v1.2 also) | GitHub Actions cron replaces this; daemon model conflicts with CLI-run-and-exit pattern |
| `celery` + `redis` | Task queue for scheduled uploads | Rejected | GitHub Actions workflow_dispatch replaces this need with zero infrastructure overhead |
| `icalendar` | Generate .ics calendar files | Rejected | No web frontend to consume iCal; JSON is sufficient for pipeline-internal scheduling |
| `act` (local GitHub Actions runner) | Test workflows locally | Optional dev tool | Useful for development but not a runtime dependency; install separately if needed |
| Cloud GPU runner (GitHub-hosted) | Run Whisper on cloud runner | Rejected | Requires paid GitHub Team/Enterprise tier; existing CUDA machine is free and already configured |
| `ngrok` / Cloudflare Tunnel | Expose webhook endpoint | Rejected | Polling avoids this entirely |

---

## GitHub Actions Workflow Architecture

```
.github/
  workflows/
    poll-dropbox.yml     # Cron every 4h: check for new WAV in Dropbox
    run-pipeline.yml     # workflow_dispatch: run main.py with episode arg
    run-analytics.yml    # Cron weekly: python main.py analytics all
```

**poll-dropbox.yml** runs `python dropbox_poller.py` and, if a new file is detected, calls `gh workflow run run-pipeline.yml --field episode=latest` via the GitHub CLI (pre-installed on self-hosted runner). This chains the workflows without a monolithic single workflow.

**run-pipeline.yml** runs on `runs-on: [self-hosted, windows, gpu]` and executes `python main.py ${{ inputs.episode }} --auto-approve`.

**run-analytics.yml** runs weekly on a standard schedule to collect engagement data.

---

## Bi-Weekly Schedule Approach

GitHub Actions cron has no native "every 2 weeks" support. Two correct approaches:

**Approach A (recommended): Event-driven, not time-driven**
The pipeline does not need a bi-weekly cron trigger. It triggers when a new WAV file appears in Dropbox — which happens on the show's actual release cadence. The content calendar is computed from the episode's Dropbox upload date, not from a fixed cron schedule. This is more robust: if the show skips a week or releases early, the pipeline just works.

**Approach B (fallback): Weekly cron with modulo check**
If polling must be supplemented with a periodic "force check", use `cron: '0 9 * * 1'` (every Monday 9 AM UTC) with a Python script that checks `(current_week_number % 2 == expected_week % 2)` to skip non-release weeks. This is a last resort — the event-driven approach is cleaner.

**Recommendation: Use Approach A.** The Dropbox upload is the canonical event. The cron trigger in `poll-dropbox.yml` is a polling mechanism, not a release gate.

---

## Version Compatibility Matrix (v1.3 additions)

| Component | Version / Config | Compatible With | Notes |
|-----------|-----------------|-----------------|-------|
| GitHub Actions runner app | Latest (auto-updated) | Windows 11, x64 | Install at C:\actions-runner; run as Windows service |
| dropbox SDK | 12.0.2 (already pinned) | Python 3.12 | Use existing; PyPI classifiers show 3.4-3.8 but runs fine on 3.12 |
| GitHub Secrets | N/A | All workflow files | Injected as env vars matching config.py's `os.environ.get()` calls |
| content_calendar.py | stdlib only | Python 3.12 | No new packages |

---

## Integration Points with Existing Code

| New Component | Integrates With | What Changes |
|--------------|----------------|--------------|
| `dropbox_poller.py` (new) | Existing `dropbox` SDK, Dropbox config in `config.py` | Adds `check_for_new_episode()` function; writes cursor to `data/dropbox_cursor.json` |
| `.github/workflows/poll-dropbox.yml` | `dropbox_poller.py`, GitHub CLI | Cron job; calls workflow_dispatch if new file detected |
| `.github/workflows/run-pipeline.yml` | `main.py` — existing CLI entrypoint | No code changes to main.py; workflow runs `python main.py latest --auto-approve` |
| `content_calendar.py` (new) | `scheduler.py` — existing `PostingTimeOptimizer` | Generates `content_calendar.json` with absolute timestamps; pipeline reads it at distribution step |
| `.github/workflows/run-analytics.yml` | `main.py analytics all` — existing CLI | No code changes; analytics already runs as a CLI command |

---

## What NOT to Build

| Anti-pattern | Why | Correct Approach |
|--------------|-----|-----------------|
| Persistent polling daemon on Windows | Fragile across reboots; fights the CLI-run-and-exit model | Use GitHub Actions cron-triggered poll job instead |
| Webhook receiver with public URL | Requires ngrok/tunnel maintenance; adds a persistent service | Use API polling from Actions workflow |
| Monolithic single workflow doing everything | One failure cancels all steps; can't re-trigger middle steps | Separate poll.yml + process.yml; pipeline's existing checkpoint/resume handles partial failures |
| Bi-weekly cron trigger as release gate | Episodes don't release on a fixed cron; skipped weeks break assumptions | Event-driven on Dropbox file detection |
| Cloud runner for Whisper | No GPU on free tier; paid tier required | Self-hosted runner on existing CUDA machine |
| Committing .env to repo for CI | Security | GitHub Secrets injected as env vars at workflow runtime |

---

## Sources

- [GitHub Docs: Adding self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners) — Windows service install confirmed
- [GitHub Docs: Self-hosted runner security](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners) — private repo recommendation verified
- [GitHub Changelog: GPU hosted runners GA](https://github.blog/changelog/2024-07-08-github-actions-gpu-hosted-runners-are-now-generally-available/) — requires paid plan, confirmed
- [Dropbox Detecting Changes Guide](https://developers.dropbox.com/detecting-changes-guide) — server-side polling pattern with cursor confirmed; webhook requires public endpoint
- [Dropbox SDK Python PyPI](https://pypi.org/project/dropbox/) — version 12.0.2 latest (June 2024)
- [GitHub Docs: Secrets](https://docs.github.com/en/actions/concepts/security/secrets) — repository vs environment secrets distinction
- [GitHub Community: Bi-weekly cron workaround](https://github.com/orgs/community/discussions/49483) — confirmed no native bi-weekly cron; modulo approach documented
- [Sysdig: Self-hosted runner security risks](https://www.sysdig.com/blog/how-threat-actors-are-using-self-hosted-github-actions-runners-as-backdoors/) — private repo + sole owner mitigates risk; verified
- [Sprout Social: Best times to post 2025](https://sproutsocial.com/insights/best-times-to-post-on-social-media/) — platform timing defaults for content calendar (MEDIUM confidence — general audience, not niche comedy)

---

*Stack research for: GitHub Actions CI/CD and content calendar additions to podcast-automation pipeline*
*Researched: 2026-03-18*
