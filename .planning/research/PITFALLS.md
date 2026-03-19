# Pitfalls Research

**Domain:** Podcast automation pipeline — content calendar + GitHub Actions CI/CD
**Researched:** 2026-03-18
**Confidence:** HIGH (most pitfalls verified by official docs + multiple independent sources)
**Milestone:** v1.3 Content Calendar & CI/CD

---

## Critical Pitfalls

Mistakes that cause rewritten workflows, security incidents, or content crises.

---

### Pitfall 1: Secrets Baked Into the Self-Hosted Runner Environment

**What goes wrong:**
OAuth tokens, API keys, and credential files that live locally (credentials/ directory, .env) get hardcoded into workflow YAML as env blocks or mounted as file paths. A supply chain attack on a third-party action — like the March 2025 tj-actions/changed-files compromise that exposed secrets in 23,000+ repositories — or a developer mistake printing a secret in a run step exfiltrates all credentials in a single job log.

The Fake Problems pipeline has more credential surface area than a typical project: Dropbox API, YouTube OAuth (google_docs_token.json is a JSON file with multiple fields), Twitter OAuth 1.0a (four keys), OpenAI, Google Docs. JSON credential files are particularly dangerous because GitHub's automatic log redaction does not reliably redact structured data — only scalar string values get masked.

**Why it happens:**
The existing pipeline reads credentials from local files. The instinct when moving to CI is "just make it find the same files on the runner." This treats the runner like a dev machine and puts credential files in repository-accessible paths.

**How to avoid:**
- Store every secret as a GitHub Actions repository secret — Dropbox token, YouTube client_id/client_secret/refresh_token (three separate secrets, not one JSON blob), Twitter four-key set, OpenAI API key.
- For OAuth JSON files (google_docs_token.json), split the JSON into individual secrets or base64-encode the JSON and reconstruct the file in a step that uses `::add-mask::` on the decoded value.
- Pin every third-party action to a full commit SHA: `uses: actions/checkout@a81bbbf8298c0fa03ea29cdc473d45769f953675` not `@v4`.
- Never echo any secret-derived value in a run step. If a debug log is needed, write it only to `$GITHUB_STEP_SUMMARY` (never persisted to external logs).
- Scope secrets to individual steps (not job-level `env:`) so they are in memory for the minimum time.

**Warning signs:**
- Workflow YAML contains file paths like `credentials/google_docs_token.json` in a run step
- `env:` blocks at job level with API keys
- Actions pinned with a version tag (`@v3`, `@main`) instead of a full SHA
- Any `cat`, `echo`, or `print` of a variable containing a credential in CI logs

**Phase to address:**
Phase 1 (CI Foundation). Must be verified before any workflow that can write to external platforms is merged.

---

### Pitfall 2: Concurrent Pipeline Runs Corrupting Episode State

**What goes wrong:**
Two runs start for the same episode simultaneously: a scheduled Dropbox poll fires while a manual dispatch is still running, or a developer re-runs a failed job while the retry is still running. Both write to `output/epN/`, both update the checkpoint JSON, both may reach the upload step. The result is duplicate YouTube uploads, duplicate Twitter threads, or a corrupted checkpoint file that records the episode as complete when it stopped halfway through.

**Why it happens:**
GitHub Actions has no default mutual exclusion. Scheduled triggers fire on the clock regardless of whether a previous run is active. Manual dispatches do not automatically cancel scheduled runs. The existing checkpoint system uses file writes that are not atomic under concurrent access.

**How to avoid:**
Add a `concurrency:` block to every workflow, with `cancel-in-progress: false` (queue, do not cancel — a cancelled upload mid-flight is worse than waiting):

```yaml
concurrency:
  group: podcast-pipeline-${{ github.event.inputs.episode_number || 'scheduled' }}
  cancel-in-progress: false
```

For manual dispatch, include the episode number in the concurrency group so different episodes can run in parallel, but the same episode cannot. For the scheduled Dropbox-polling workflow, use a fixed group name so two polls cannot overlap.

Additionally, verify the existing checkpoint system handles the case where a checkpoint file is written by two processes: use atomic file rename (write to `.tmp`, rename to final name) or check that the runner's single-threaded process model prevents this in practice.

**Warning signs:**
- No `concurrency:` block in any workflow YAML
- Checkpoint file `last_modified` timestamp is from a different run than expected
- Duplicate YouTube uploads or Twitter threads appearing
- `output/epN/` contains files with two different creation timestamps for the same step

**Phase to address:**
Phase 1 (CI Foundation). Must be in the initial workflow design, not retrofitted after a race condition causes a duplicate post.

---

### Pitfall 3: 700MB WAV Files Destroying CI Performance and Disk

**What goes wrong:**
The pipeline downloads a ~700MB WAV from Dropbox as step 1. In CI this causes three distinct failure modes:

1. **Artifact storage blowup:** If the workflow is split into multiple jobs and the WAV is passed between jobs via `actions/upload-artifact`, it immediately consumes GitHub artifact storage quota (2GB free on the Free plan) and will fail uploads silently for large payloads.
2. **Runner disk exhaustion:** GitHub-hosted runners have ~14GB free. A Windows Server 2025 hosted runner recently lost its D: drive and now has ~33GB total. After 2-3 episodes' worth of intermediate files accumulate without cleanup, the runner runs out of disk mid-job.
3. **Repeated downloads on retry:** If step 1 (download) completes but step 2 (transcription) fails and the job retries, the 700MB download runs again from scratch unless the checkpoint is respected.

**Why it happens:**
Developers split workflows into jobs for parallelism without accounting for the audio file size. Artifact passing is the standard pattern for multi-job workflows, but it was designed for kilobytes-to-megabytes assets, not audio files.

**How to avoid:**
- Keep the entire pipeline as a single job (not multi-job). The 2-episode/month cadence does not benefit from job-level parallelism, and the complexity cost is high.
- Never use `actions/upload-artifact` for audio files. The WAV lives on the runner's local disk only for the job's lifetime.
- Add a disk-space check at job start: fail fast with a clear error if `df -h` shows less than 10GB free.
- Add a cleanup step at the END of each run: delete `output/epN/` intermediate files (WAV, uncompressed audio), keeping only final deliverables (MP3, videos, subtitle files). Keep final deliverables for N days for re-upload purposes.
- Respect the existing checkpoint: if the WAV download checkpoint exists and the file is on disk with the expected size, skip re-download.

**Warning signs:**
- Workflow has multiple jobs passing files between them
- `actions/upload-artifact` appears anywhere near audio processing steps
- Runner disk usage climbs episode over episode with no cleanup step
- Job fails with "no space left on device" error mid-transcription

**Phase to address:**
Phase 1 (CI Foundation). The single-job architecture decision must be made before writing any YAML.

---

### Pitfall 4: Auto-Posting Edgy Comedy Content Without Human Review Gate

**What goes wrong:**
The workflow is configured with `--auto-approve` covering all pipeline steps including distribution (step 8 onward). The pipeline processes and posts to YouTube, Twitter, and Shorts overnight without any human seeing the content first. An episode with dark humor that aged badly, a misunderstood joke, or a topic that was fine during recording but became problematic by release day (see: ep29 cancer misinformation strike) gets published while the host is asleep. Recovery window: until someone notices, which could be hours.

The existing compliance checker (GPT-4o at temp=0.1) is a safety gate — but it has documented false-negative rates on comedy content that uses real-world events as comedic setups. It was designed to catch clear violations, not to make editorial judgment calls.

**Why it happens:**
`--auto-approve` was built for speed on local runs where a human just finished reviewing the content. In CI it removes the last human checkpoint, and developers configure it this way because it's the default "fast" mode.

**How to avoid:**
- CI pipeline must stop after step 6 (MP3 + Dropbox upload) and fire a Discord notification requesting human review before upload.
- Distribution steps (7.5 RSS, 8 Social, 8.5 Blog, 8.6 Webpage) must be a separate manual-trigger-only workflow, or require a GitHub Actions `environment: production` gate with required reviewers.
- The `environment: production` gate pauses the workflow in the GitHub UI until a named reviewer approves — this is a first-class GitHub feature, not a workaround.
- Never set `--force` on the compliance safety gate in CI workflow YAML. The `--force` flag bypasses the compliance gate entirely.
- Send the Discord notification with a direct link to the GitHub Actions approval URL so the host can approve from mobile.

**Warning signs:**
- `python main.py ep$N --auto-approve` covers the full pipeline including steps 8+ in CI YAML
- No `environment:` with required reviewers on any distribution job
- Discord notification is sent after upload completes, not before
- `--force` appears anywhere in CI workflow YAML for upload steps

**Phase to address:**
Phase 1 (CI Foundation) for the architecture. Phase 2 (Content Calendar) for the notification and approval UX.

---

### Pitfall 5: OAuth Token Expiry Silently Failing Uploads in CI

**What goes wrong:**
YouTube, Twitter, and Google Docs OAuth tokens expire or get revoked. On a developer's machine this triggers an interactive re-auth browser flow. In CI there is no terminal — the job quietly fails with a `401 Unauthorized` or similar error, the Discord notification may not fire (if the notification step is after the failed upload step), and the episode is stuck in limbo. No one notices for days.

YouTube OAuth apps in "testing" status in Google Cloud Console issue tokens that expire every 7 days. If the app is still in testing status (unverified OAuth consent screen), every refresh token becomes invalid after one week. This is a silent killer for CI.

**Why it happens:**
Developers don't notice because local re-auth happens automatically. The testing vs. published distinction in Google Cloud Console is not obvious. CI has no fallback re-auth path, so the first time a token expires in CI, there is no graceful error message — just a 401.

**How to avoid:**
- Check Google Cloud Console: if the YouTube OAuth app is in "Testing" status, either publish it (requires OAuth verification if using sensitive scopes) or add the podcast's Google account as a "Test user" to get consistent refresh behavior.
- Add a pre-flight credential check step at job start that calls a low-cost read endpoint for each platform before attempting any writes: YouTube `channels.list` (1 quota unit), Twitter `users/me`, Dropbox `check/user`.
- The pre-flight step must exit non-zero on 401 — do not silently continue to the upload step.
- Store the refresh token (not just the access token) in GitHub Secrets. Access tokens expire in minutes; refresh tokens last until revoked.
- Set a calendar reminder for manual token refresh for any platform that does not support headless token refresh from a stored refresh token.

**Warning signs:**
- YouTube OAuth consent screen in Google Cloud Console shows status "Testing"
- Credential JSON files contain `access_token` but no `refresh_token`
- Upload steps complete with exit code 0 but no video appears on YouTube (silent 401 swallowed by the uploader)
- No pre-flight credential check step in the workflow

**Phase to address:**
Phase 1 (CI Foundation). Credential health check must be a first-class workflow step before the first production run.

---

### Pitfall 6: Windows Self-Hosted Runner Becoming Unmaintained Infrastructure

**What goes wrong:**
The self-hosted runner on the dev Windows 11 machine accumulates problems over time: CUDA driver updates break WhisperX, Python venv becomes stale after `pip install -r requirements.txt` silently upgrades a transitive dependency, disk fills with episode intermediates from previous runs, Windows Update reboots the machine mid-job. The machine is also the developer's daily driver — a 60-minute Whisper transcription job competes with everything else.

Starting March 2026, GitHub requires self-hosted runners to be at minimum version v2.329.0 or they are blocked from receiving jobs. This minimum version requirement will increase over time.

**Why it happens:**
Self-hosted runners are treated as set-and-forget after initial setup. The runner is not resilient to reboots unless explicitly configured as a Windows Service. CUDA drivers are updated via Windows Update or manually, with no pin to a known-good version.

**How to avoid:**
- Install the runner as a Windows Service using `./config.cmd --runasservice` so it survives reboots automatically.
- Add a disk cleanup step at the END of every pipeline run: delete intermediate files in `output/epN/` older than the last completed episode, keeping only final deliverables.
- Lock Python dependencies to a hash-pinned lockfile (`pip freeze > requirements-lock.txt`) for the CI environment, separate from the development `requirements.txt`.
- Add a weekly smoke-test workflow that runs `python -c "import whisperx; print('ok')"` and alerts Discord if it fails — catches CUDA/venv breakage before the next episode.
- Subscribe to GitHub's `actions/runner` release notes; update the runner binary before the minimum version enforcement deadline.
- Pin CUDA toolkit version in a runner setup document; do not allow Windows Update to auto-update GPU drivers.

**Warning signs:**
- Runner service is not in `services.msc` (not installed as a service, will not survive reboots)
- `output/` directory accumulating files across multiple episodes with no cleanup
- Runner binary version is more than 3 minor versions behind current
- No health-check workflow running periodically

**Phase to address:**
Phase 1 (CI Foundation) for initial runner setup. Ongoing operational runbook for maintenance.

---

### Pitfall 7: Dropbox Polling Triggering False-Positive Pipeline Runs

**What goes wrong:**
The scheduled workflow polls Dropbox for new episodes. Dropbox's folder also contains sync metadata files (`.dropbox`, `~$` lock files from apps that touch the folder), partially-synced files (Dropbox creates a temp file during upload that is renamed on completion), and potentially renamed or re-uploaded older episodes. Any of these triggers a pipeline run for a non-episode file or a partial upload.

If a partial 700MB upload is detected at 300MB (Dropbox sync in progress), WhisperX will attempt to transcribe a truncated WAV, produce a corrupted transcript, and mark the episode as "analyzed" in the checkpoint — preventing a clean re-run without manual checkpoint deletion.

**Why it happens:**
File-presence detection without content validation is the simplest implementation. Dropbox's sync model means a file "exists" in the API before it is fully uploaded. The existing `python main.py latest` command may use filename or modification-time heuristics that are fooled by partial syncs.

**How to avoid:**
- Filter by explicit filename pattern: only trigger on files matching the episode naming convention (e.g., `ep[0-9]+\.(wav|mp3)` or whatever convention is used). Reject all other files.
- Add a file-size sanity check: a real 70-minute episode WAV is 650-750MB. Reject files below 100MB as incomplete.
- Add a file-age check: only trigger on files whose `server_modified` timestamp (Dropbox's server-side timestamp, set when upload completes) is more than 5 minutes in the past. This guards against triggering on files mid-upload.
- Deduplicate: persist the last-processed episode identifier (number or filename) in a file in the repo or a GitHub Actions variable. Skip any detected file that matches an already-processed episode.

**Warning signs:**
- Pipeline runs triggered by files that are not episodes
- Episode processed twice (same content appears in output twice)
- WAV download step completes in under 30 seconds (too fast for 700MB — file is smaller than expected)
- Checkpoint shows "analyzed" for an episode that does not appear on YouTube

**Phase to address:**
Phase 2 (Content Calendar / CI Trigger Design). Polling logic must include all four guards before the first scheduled run.

---

### Pitfall 8: Content Calendar Posting Schedule Surviving Sensitive Current Events

**What goes wrong:**
The content calendar plans clip releases for the week following an episode drop. A clip that was funny in isolation gets scheduled to post the day after a real-world tragedy that happens to overlap with the joke topic. The comedy podcast with dark humor is particularly exposed: clips about death, cancer, crime, or political topics can age badly within hours of being scheduled.

With GitHub Actions scheduling, the clip posts automatically because no one reviewed the schedule after the tragic event. The post goes live, gets reported, and triggers a platform response.

**Why it happens:**
Content calendar automation assumes the world stays static between planning and posting. For edgy comedy content, this assumption fails more often than for mainstream content.

**How to avoid:**
- No clip should auto-post without a 24-hour human review window between "scheduled" and "live."
- The Discord notification for each scheduled clip must include: the clip title, the topic, the scheduled time, and a one-click link to cancel the post. The host must affirmatively confirm or let it expire.
- Build a "pause all scheduled posts" kill switch: a single GitHub Actions dispatch workflow that sets a flag (a file in the repo, a repository variable) that the posting workflows check before executing.
- Treat the content calendar as a planning tool, not an execution tool. CI generates the calendar and sends it to the host for approval; the host manually approves each post or accepts the schedule.

**Warning signs:**
- Scheduled posts fire automatically with no confirmation step
- No "pause all" mechanism exists in the workflow design
- Discord notifications are informational only (no approve/cancel action)
- Calendar planning and post execution happen in the same workflow step

**Phase to address:**
Phase 2 (Content Calendar). Human-in-the-loop design is required before building the calendar feature at all.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Run full pipeline in one CI job | Simple, no artifact passing | Slow (60-90 min per episode); no partial retry | Always — 2 episodes/month makes complexity unjustified |
| Store episode state in local output/ files | Zero infrastructure | Concurrent run corruption risk | Acceptable with concurrency group lock in place |
| Use personal OAuth apps (not service accounts) | Quick setup | Token expiry, quota tied to personal account | Acceptable for MVP; migrate to service account if account is suspended |
| Pin `--auto-approve` in CI for pre-upload steps only | Faster pipeline | Easy to accidentally extend to uploads | Only for steps 1-6; never for distribution steps 7.5+ |
| Hardcode episode number detection by filename | Works for current naming convention | Breaks if naming changes without updating polling logic | Acceptable with documented naming convention and validation |
| Skip disk cleanup for first CI run | Reduces initial complexity | Disk fills after 3-4 episodes | Never — add cleanup from the first workflow version |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| YouTube OAuth | Leaving app in "Testing" status | Publish OAuth app or add account as test user; testing-status tokens expire every 7 days |
| YouTube Data API | Upload + analytics in same pipeline job | Separate analytics into a distinct weekly scheduled workflow; 10k units/day quota is shared |
| Twitter API v2 | Assuming bearer token works for posting | Bearer is read-only; posting requires OAuth 1.0a user context or OAuth 2.0 with write scope |
| Dropbox API | Triggering on any file change event | Filter by filename pattern + file size + file age before triggering the pipeline |
| GitHub Actions secrets | Passing JSON credential files as a single secret | Split into discrete scalar secrets to ensure log redaction works reliably |
| OpenAI API in CI | No timeout set on API calls | Network latency in CI is higher and less predictable; set `timeout=60` and add retry with backoff |
| WhisperX CUDA | Assuming CUDA driver survives Windows Update | Pin CUDA toolkit version in runner setup documentation; verify with `nvidia-smi` at job start |
| GitHub environment gates | Assuming workflow YAML is sufficient | `environment: production` with required reviewers must be configured in the GitHub repo Settings > Environments UI — YAML alone does nothing |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Re-downloading 700MB WAV on every retry | Job restart from step 1 re-fetches full file from Dropbox | Checkpoint step 1 with file hash; skip download if WAV already on disk with expected size | Every retry after a failed transcription job |
| WhisperX model not cached on runner | First 2-3 minutes of every run spent downloading model weights | Pre-download Whisper model during runner setup; smoke-test verifies cache exists | Every fresh runner setup or after an accidental cache clear |
| OpenAI calls not checkpointed | GPT-4o analyze + compliance re-run from scratch on resume | Verify existing checkpoint keys `analyze` and `censor` are honored; do not re-call if checkpoint file exists | Any re-run after partial failure at or after step 3 |
| No job timeout set | Hung Whisper job (CUDA OOM, corrupt WAV) occupies runner indefinitely | Set `timeout-minutes: 120` at job level | First corrupt WAV or CUDA out-of-memory stall |
| Scheduled analytics collection during pipeline run | Analytics and upload compete for YouTube API quota | Run analytics collection in a separate weekly workflow, never in the episode pipeline | First episode where upload + analytics shares the 10k daily quota |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Echoing secrets in debug steps | Secret appears in job log, stored in GitHub for 90 days | Never `echo $SECRET`; use `::add-mask::` if a derived value must be printed |
| Third-party action pinned by tag not SHA | Supply chain compromise (tj-actions March 2025) changes action behavior silently | Pin all `uses:` to full commit SHA; audit action code before trust |
| `pull_request_target` trigger with secrets access | Untrusted fork PR can read secrets | Use `pull_request` (not `pull_request_target`) for untrusted contributor workflows |
| Credential files in git-tracked paths | Token exposure via git history | Confirm `credentials/` and `*.json` OAuth files are in `.gitignore` and not currently tracked |
| Runner token with org-wide scope | Compromised runner gets access to all org repos | Use fine-grained repository tokens scoped only to the podcast repo |
| `--auto-approve` + `--force` in CI for distribution | Bypasses compliance gate; auto-posts content that may violate YouTube guidelines | Remove `--force` from all CI YAML; require human approval before any distribution step |
| Dropbox app with full account access | Compromised Dropbox token can access all files in the account | Restrict Dropbox app scope to the specific podcast folder only |

---

## Comedy Content Specific Risks

### Auto-Posting Raises the Stakes of Every Compliance False Negative

The v1.1 compliance checker uses GPT-4o at temp=0.1 to classify YouTube guideline violations. It was designed to pass/fail on clear violations while preserving comedy content — dark humor and profanity are explicitly not violations in the prompt. However, the checker has a documented false-negative rate for edge cases: jokes about real medical conditions, extreme political content framed as comedy, content referencing ongoing news events.

In manual mode, a false negative means the host reviews the content and catches it. In CI auto-post mode, a false negative means the video goes live immediately. Given ep29's cancer misinformation strike history, this is not hypothetical.

**Prevention:** The compliance gate in CI must stop the pipeline and request human review, not gate the auto-post decision. The gate answers "should a human review this?" not "is this safe to auto-post?"

### Rigid Posting Schedule Is Tone-Deaf to Current Events

Dark comedy about sensitive topics (death, crime, health crises) can be completely appropriate when the episode releases and become deeply inappropriate 48 hours later due to breaking news. A content calendar that automatically drips clips all week has no mechanism to pause when the world changes.

**Prevention:** Every scheduled post beyond the initial episode upload requires same-day human confirmation. The calendar is a suggestion, not a commitment.

### Bulk Upload Pattern May Trigger YouTube Detection

In 2025, YouTube's detection systems became more aggressive about identifying bulk upload patterns combined with other automation signals. For a comedy podcast, uploading one full episode + three Shorts + thumbnail updates in rapid succession within a single CI job may trigger detection, especially if the uploads are closely spaced in time.

**Prevention:** Add configurable delays between upload steps (30-60 seconds minimum between each upload API call). Avoid uploading all Shorts in the same minute. This also reduces quota spike risk.

---

## "Looks Done But Isn't" Checklist

- [ ] **Secrets split correctly:** YouTube OAuth is split into individual secrets (client_id, client_secret, refresh_token) — not a single JSON blob. Verify log redaction works by checking a dry-run job's log for any credential fragments.
- [ ] **Concurrency guard works:** Test by dispatching two manual runs with the same episode number simultaneously. Confirm the second run queues and waits, not runs in parallel.
- [ ] **Human upload gate is real:** `environment: production` with required reviewers must exist in GitHub repo Settings > Environments UI — the YAML alone does not create the gate.
- [ ] **Token pre-flight actually fails on 401:** Manually revoke a test token, run the pre-flight step, confirm it exits non-zero and fires a Discord alert before reaching any upload step.
- [ ] **Disk cleanup runs:** Run two episodes back-to-back. Check `output/` on the runner after both complete. Intermediate files should not accumulate.
- [ ] **Dropbox dedup works:** Upload a dummy file to the Dropbox watch folder that does not match the filename pattern. Confirm the scheduled workflow does not trigger a pipeline run.
- [ ] **WhisperX model is cached:** Delete `~/.cache/whisper` on the runner and run the smoke-test workflow. Confirm it downloads the model and re-caches it without requiring a full episode run.
- [ ] **`--force` is absent from CI YAML:** Run `grep -r '\-\-force' .github/` before every merge. The compliance safety gate must never be overridden in CI.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Secret exposed in job log | HIGH | Rotate all secrets immediately; check GitHub log retention settings; revoke any tokens that may have been seen; audit for unauthorized API calls |
| Duplicate YouTube upload | MEDIUM | Delete duplicate in YouTube Studio before it gets indexed; check for duplicate Twitter threads and delete; review concurrency group config |
| Concurrent run corrupted checkpoint | MEDIUM | Delete checkpoint file for the affected episode; re-run from scratch with `--no-resume`; verify concurrency group is set correctly |
| OAuth token expired mid-upload | LOW | Re-auth locally to get new refresh token; update the corresponding GitHub Secret; re-run distribution-only steps |
| Runner disk full mid-transcription | LOW | SSH to runner; delete old episode intermediates; verify remaining disk > 10GB; re-run from download checkpoint |
| Dropbox false-positive processed wrong file | HIGH | Identify and delete any content that was incorrectly processed and uploaded; fix polling filter logic before next scheduled run |
| Auto-post of episode that receives YouTube strike | HIGH | Submit YouTube strike appeal immediately; set all future posts to manual-only until appeal resolves; add the violated topic to the compliance prompt's negative examples |
| Content posted during breaking news crisis | HIGH | Manually delete or private the post on all platforms immediately; implement "pause all" kill switch before next calendar cycle; review all remaining scheduled posts for the week |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Secrets exposure | Phase 1 (CI Foundation) | Audit all workflow YAML for file paths and hardcoded values; grep for any credential patterns |
| Concurrent run corruption | Phase 1 (CI Foundation) | Test dual simultaneous dispatch; confirm only one run proceeds |
| 700MB file handling + disk exhaustion | Phase 1 (CI Foundation) | Run two back-to-back episodes; check runner disk usage and absence of accumulated intermediates |
| Auto-post without human review | Phase 1 (CI Foundation) + Phase 2 (Content Calendar) | Confirm `environment: production` is configured in GitHub UI; perform end-to-end approval flow test |
| OAuth token expiry | Phase 1 (CI Foundation) | Revoke a test token; confirm pre-flight step fails and alerts Discord before any upload attempt |
| Runner maintenance / service setup | Phase 1 (CI Foundation) | Verify runner appears in `services.msc`; simulate reboot and confirm runner reconnects |
| Dropbox false-positive trigger | Phase 2 (Content Calendar / Trigger Design) | Upload dummy file to Dropbox folder; confirm no pipeline run fires |
| Current events sensitivity | Phase 2 (Content Calendar) | Verify no clip auto-posts without same-day confirmation; test the "pause all" kill switch |
| Third-party action supply chain | Phase 1 (CI Foundation) | Grep all `uses:` lines for SHA pinning before any workflow is merged |
| Bulk upload YouTube detection | Phase 1 (CI Foundation) | Add inter-upload delays to workflow; verify delay between each upload step |

---

## Sources

- [Top 10 GitHub Actions Security Pitfalls](https://arctiq.com/blog/top-10-github-actions-security-pitfalls-the-ultimate-guide-to-bulletproof-workflows) — MEDIUM confidence (vendor blog corroborated by official docs)
- [GitHub Actions Secure Use Reference](https://docs.github.com/en/actions/reference/security/secure-use) — HIGH confidence (official GitHub docs)
- [tj-actions Supply Chain Compromise March 2025](https://thehackernews.com/2025/03/github-action-compromise-puts-cicd.html) — HIGH confidence (reported incident with public disclosure)
- [GitHub Actions Concurrency Docs](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency) — HIGH confidence (official GitHub docs)
- [GitHub Actions Control Concurrency](https://docs.github.com/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs) — HIGH confidence (official GitHub docs)
- [GitHub Actions GPU Runners Generally Available](https://github.blog/changelog/2024-07-08-github-actions-gpu-hosted-runners-are-now-generally-available/) — HIGH confidence (official GitHub changelog)
- [Windows Server 2025 Runner Disk Space Issue](https://github.com/actions/runner-images/issues/12609) — HIGH confidence (official runner-images issue tracker)
- [Self-Hosted Runner Minimum Version Enforcement](https://github.blog/changelog/2026-02-05-github-actions-self-hosted-runner-minimum-version-enforcement-extended/) — HIGH confidence (official GitHub changelog)
- [Dropbox Webhooks Developer Reference](https://www.dropbox.com/developers/reference/webhooks) — HIGH confidence (official Dropbox docs)
- [Concurrency Control in GitHub Actions — OneUptime](https://oneuptime.com/blog/post/2025-12-20-concurrency-control-github-actions/view) — MEDIUM confidence (practitioner blog, consistent with official docs)
- [YouTube Strike Policy Update Nov 2025](https://medium.com/@info.shaludroid/youtube-strike-policy-update-everything-creators-must-know-effective-17-nov-2025-6376baadf6e2) — MEDIUM confidence (third-party summary; cross-reference YouTube Help Center before acting on specifics)
- [YouTube Bulk Upload Detection Risk 2025](https://x.com/1of10media/status/1995176099303596381) — LOW confidence (social media post; treat as directional signal only)
- [Challenges of Social Media Automation 2025](https://vistasocial.com/insights/challenges-of-social-media-automation/) — MEDIUM confidence (vendor blog, consistent with platform documentation)
- [Managing Secrets in GitHub Actions — Doppler](https://www.doppler.com/blog/managing-secrets-ci-cd-environments-github-actions-advanced-techniques) — MEDIUM confidence (vendor blog, technically accurate)
- Project CLAUDE.md, PROJECT.md, existing pipeline code — HIGH confidence (source of truth for project constraints and known issues)

---
*Pitfalls research for: podcast automation — content calendar + GitHub Actions CI/CD (v1.3)*
*Researched: 2026-03-18*
