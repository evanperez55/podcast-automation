# Domain Pitfalls

**Domain:** Podcast automation pipeline upgrade (audio processing, social distribution, Python refactoring)
**Researched:** 2026-03-16
**Project:** Fake Problems Podcast — Pipeline Upgrade

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or irreversible production failures.

---

### Pitfall 1: Whisper Timestamp Drift Causes Mis-Censored Audio

**What goes wrong:** Word-level timestamps from Whisper/WhisperX are produced by an inference-time trick, not explicit training. Timestamps can be off by hundreds of milliseconds — sometimes seconds — especially around music, jingles, cross-talk, or long pauses. When audio ducking or bleep replacement uses these timestamps to mute a region, the mute lands on the wrong syllable or the following word.

**Why it happens:** Whisper predicts utterance-level timestamps; per-word alignment is derived by wav2vec2 forced alignment in WhisperX. The two-model pipeline adds a second failure surface: transcription errors in Whisper cause the aligner to find the "closest match," which can be phonetically similar but temporally wrong.

**Consequences:**
- Profanity passes through unmuted (compliance failure for platform distribution)
- Adjacent clean words get muted (noticeable artifact, sounds broken)
- Errors are inconsistent episode-to-episode, making them hard to test systematically

**Prevention:**
- Add a configurable `PAD_MS` buffer (e.g., 150ms before, 75ms after) to every censorship window derived from Whisper timestamps
- After applying ducking, verify by listening to 5-second windows around each mute point — automate this check in `--test` mode by saving these clips as QA artifacts
- Never use single-pass Whisper timestamps for censorship; always route through WhisperX alignment first

**Detection:** Write a post-censor validator that checks no censor window is shorter than 200ms (too short = probably missed the word) or longer than 1500ms (too wide = probably a drift error).

**Phase relevance:** Audio ducking implementation phase. Must be addressed before any ducking code ships.

---

### Pitfall 2: ffmpeg-loudnorm Falls Back to Dynamic Mode Silently

**What goes wrong:** The ffmpeg `loudnorm` filter switches from linear (constant-gain) mode to dynamic (AGC) mode automatically when the input's Loudness Range (LRA) exceeds the target LRA. This fallback happens silently — no error is raised. Dynamic mode produces "pumping" artifacts and inconsistent results across episodes that have different dynamic range characteristics.

**Why it happens:** Two-pass loudnorm requires the second pass to receive the measured stats (`measured_I`, `measured_LRA`, `measured_TP`, `measured_thresh`) from the first pass via stderr JSON parsing. If the parsed values trigger dynamic mode, there's no user-visible warning unless you explicitly check `normalization_type` in the JSON output.

**Consequences:**
- Episode-to-episode loudness is inconsistent despite "normalization"
- Comedy timing gets compressed by AGC (pauses and silence get boosted)
- Spotify/Apple Podcasts apply a second normalization on top, making output unpredictable

**Prevention:**
- After the first pass, read `normalization_type` from the JSON. If it equals `"dynamic"`, log a warning and optionally abort with instructions to adjust source material or target LRA
- Target `-16 LUFS` with `-2 dBTP` true peak limit for podcast platforms — do not use `-23` (broadcast) or `-14` (YouTube streaming); they serve different platform contexts
- Use `ffmpeg-normalize` PyPI package (`pip install ffmpeg-normalize`) instead of raw subprocess calls — it handles two-pass correctly and exposes the normalization type

**Detection:** Parse `normalization_type` from ffmpeg stderr JSON after every normalization run. Log it. Alert if `"dynamic"`.

**Phase relevance:** LUFS normalization phase. The existing dBFS-proxy approach masks this risk; switching to true loudnorm exposes it.

---

### Pitfall 3: main.py Refactor Breaks the Resume Checkpoint System

**What goes wrong:** `main.py` owns the checkpoint/resume logic that lets a failed pipeline restart mid-episode. When breaking main.py into modules, the checkpoint read/write calls get distributed across new files. If the checkpoint schema or step names change during refactoring — even by renaming a method — partially-completed episodes will not resume correctly. They'll either restart from the beginning (wasting GPU/time) or skip steps that didn't complete (producing corrupt output).

**Why it happens:** Checkpoint state is keyed by step names (string literals). Python refactoring tools rename methods but don't rename the string keys that reference those methods. Tests that mock the pipeline don't exercise the checkpoint paths because `main.py` has no test file.

**Consequences:**
- Pipeline re-runs a 70-minute Whisper transcription that already completed
- Pipeline skips normalization because it sees a stale "normalize: complete" flag
- Inconsistent episode output that's hard to diagnose without reading checkpoint JSON manually

**Prevention:**
- Before any refactor, write a test that asserts the checkpoint key names used in `process_episode()` match a known-good list — this test will fail immediately if a refactor renames a key
- Keep checkpoint serialization in a single dedicated module (not scattered across helpers)
- Version the checkpoint schema: add a `schema_version` field to checkpoint JSON so mismatches are detectable at load time

**Detection:** After a refactor, run `python main.py ep29 --dry-run` and inspect the checkpoint JSON to confirm all expected step keys are present with the correct names.

**Phase relevance:** Tech debt / main.py refactor phase.

---

### Pitfall 4: Scheduled Upload Stub Marks Items Done Without Uploading

**What goes wrong:** `_run_upload_scheduled()` already logs `[TODO] upload not yet automated` and marks uploads as `"uploaded"` with a placeholder. If any phase adds scheduling integration without also implementing the upload execution, real uploads will be permanently skipped and the schedule JSON will show them as complete. There is no retry, no error, and no visible failure.

**Why it happens:** The stub was added to make the scheduler framework work without blocking on platform uploader wiring. The implicit contract — "we'll wire this later" — is invisible to anyone running `python main.py upload-scheduled` in production.

**Consequences:** Episodes are silently never uploaded to YouTube, Twitter, or TikTok in scheduled mode. The only symptom is missing content on the platforms — noticed by humans, not the system.

**Prevention:**
- The scheduler must be treated as blocked until real upload execution is wired in
- Add a guard at the top of `_run_upload_scheduled()` that raises `NotImplementedError` if any upload would be marked done without actually executing — remove the guard only when real uploaders are wired
- Do not ship any phase that adds new scheduled platforms until the stub is resolved

**Detection:** Add a test that calls `_run_upload_scheduled()` with a pending item and asserts the platform uploader was actually called (not just that the schedule was marked complete).

**Phase relevance:** Scheduler fix phase (a prerequisite for any distribution expansion).

---

## Moderate Pitfalls

---

### Pitfall 5: Audio Ducking Attack/Release Timing Sounds Unnatural

**What goes wrong:** When implementing volume-dip censorship, the fade-in and fade-out (attack and release) durations are critical. Too fast (< 20ms) produces a click artifact. Too slow (> 100ms) dips into surrounding words on either side of the censored word. The "right" values depend on the surrounding speech cadence and cannot be constants — a word said quickly needs shorter attack/release than one with natural pauses around it.

**Why it happens:** Developers implement a single global attack/release constant and test with one example. Edge cases (rapid-fire speech, back-to-back censored words, censored word at end of sentence) are missed until someone listens to a real episode.

**Consequences:** Ducked audio sounds robotic or choppy rather than the smooth "radio dip" effect that motivated the feature.

**Prevention:**
- Use 30ms attack, 50ms release as starting values — these are the broadcast radio standard for ducking
- Special-case consecutive censored words: merge their windows rather than applying separate dips
- Build a QA mode that exports 3-second clips around every censor point so they can be listened to before final output
- pydub's `fade()` method handles this correctly if given the right duration; do not implement raw sample-level manipulation

**Detection:** After implementation, listen to the QA clips for at least 3 episodes before removing manual review from the workflow.

**Phase relevance:** Audio ducking implementation phase.

---

### Pitfall 6: Instagram Graph API Version Rot Breaks Silently

**What goes wrong:** `instagram_uploader.py` is hardcoded to `graph.facebook.com/v18.0`. Meta releases new Graph API versions quarterly and deprecates old ones on a ~24-month cycle. v18.0 launched September 2023, making it subject to deprecation in 2025. After deprecation, API calls return 400 errors with deprecation messages that are easy to overlook in logs if Instagram upload is already treated as "best effort."

**Why it happens:** The API version is a string constant in the uploader class. There's no automated check against Meta's published deprecation schedule, and Instagram upload is currently manual-only (not wired into the main pipeline), so the error wouldn't surface during normal pipeline runs.

**Consequences:** When the pipeline is finally wired for Instagram, it will immediately fail on v18.0 calls. Debugging will look like an auth issue until someone reads the error body carefully.

**Prevention:**
- Move the API version to `Config.INSTAGRAM_API_VERSION` with a default of `"v22.0"` (current as of March 2026)
- Make it configurable via env var so version bumps require no code change
- Add a startup check that logs the configured API version — makes version rot visible

**Detection:** Any 400 response from Meta Graph API with "deprecated" in the error message.

**Phase relevance:** Instagram wiring phase and any social platform expansion phase.

---

### Pitfall 7: Twitter URL Length Arithmetic Breaks on Edge Cases

**What goes wrong:** The existing Twitter URL length calculation in `post_clip()` is fragile — it embeds the URL in a suffix f-string before calculating display length, then subtracts and re-adds the Twitter t.co length (23 chars). This works only when `youtube_url` is a non-None string. If YouTube upload was skipped (no video ID), `youtube_url` is `None`, the f-string includes the literal string `"None"`, and the clip caption gets truncated incorrectly.

**Why it happens:** The arithmetic was written for the happy path. The `None` case was handled with a conditional but the length calculation path diverges in a way that produces wrong character counts.

**Consequences:** Tweet text gets truncated mid-sentence, or the tweet is rejected by the API for exceeding 280 characters.

**Prevention:**
- Refactor to: build the final text string first (with or without URL), then check `len(text) <= 280` before posting
- Twitter counts any URL as exactly 23 characters regardless of actual length — calculate display length as `len(text_without_url) + 23` if a URL is present, `len(text)` if not
- Test with `youtube_url=None`, `youtube_url=""`, and `youtube_url="https://youtu.be/abc123"`

**Detection:** The existing test for `post_clip()` likely only covers the happy path. Add parameterized tests for all three URL states.

**Phase relevance:** Any phase that touches Twitter uploader or adds new platforms with character limits.

---

### Pitfall 8: LLM Voice Consistency Degrades Across Episodes Without Example Anchoring

**What goes wrong:** Prompting GPT-4o or Llama 3.1 to "write in an edgy comedy voice" produces different interpretations across runs. Without concrete examples of good output anchored in the prompt (few-shot examples from the actual show), the model defaults to generic "irreverent" humor that doesn't match the show's specific comedic register. This is most acute for social captions and blog intros, which are the most visible output.

**Why it happens:** LLMs are non-deterministic, and broad style instructions ("edgy," "dark humor") are underspecified. The model's interpretation of "edgy comedy" varies with temperature, context length, and prompt order.

**Consequences:** AI-generated content needs manual rewriting after every episode — defeating the automation goal.

**Prevention:**
- Store 3-5 gold-standard examples of titles, descriptions, and captions in `config.py` or a dedicated `voice_examples.py` — include them as few-shot examples in every content generation prompt
- Lower temperature to 0.7 for social copy (reduces variance), keep it at 1.0 for blog posts (more creative)
- Add a `--regenerate` flag that re-runs content generation without re-running transcription/analysis — lets hosts reject and regenerate without reprocessing the whole episode

**Detection:** After each episode, hosts should rate the AI content on a 1-3 scale. If average rating stays below 2 for 3 consecutive episodes, the prompts need revision.

**Phase relevance:** AI voice/content generation phase.

---

### Pitfall 9: continue_episode.py Diverges from main.py During Refactor

**What goes wrong:** `continue_episode.py` is a 525-line standalone script that duplicates pipeline logic from `main.py`. When `main.py` is refactored — new module structure, renamed uploaders, changed credential paths — `continue_episode.py` is not updated in parallel. It silently continues to work until a production emergency (failed upload mid-episode) forces someone to use it, at which point it calls the old interface and crashes.

**Why it happens:** The script has no tests and no callers in the test suite. It's only invoked in emergencies. Refactoring PRs don't include it because it's "not the main pipeline."

**Consequences:** The emergency recovery tool fails exactly when it's needed most.

**Prevention:**
- Before the main.py refactor begins, either delete `continue_episode.py` and replace it with `python main.py ep29 --resume-from=step_N`, or add integration smoke tests that call it with mocked uploaders
- If kept, make it a thin wrapper around the same uploader classes used in `main.py` — not a reimplementation

**Detection:** Add `continue_episode.py` to the pre-commit hook's lint scope so at minimum it stays syntactically valid.

**Phase relevance:** Tech debt / main.py refactor phase.

---

## Minor Pitfalls

---

### Pitfall 10: RSS Feed XML Injection via f-String Concatenation

**What goes wrong:** `spotify_uploader.py:generate_rss_item()` builds XML via f-string concatenation. Episode titles or descriptions with `&`, `<`, `>`, or `"` characters will produce malformed XML. Spotify's RSS parser will reject the feed item entirely.

**Prevention:** Use `xml.etree.ElementTree` (already used in `rss_feed_generator.py`) for all RSS generation. The fix is a one-file change with clear test coverage path.

**Phase relevance:** Any phase that touches RSS or Spotify distribution.

---

### Pitfall 11: OpenAI SDK Missing from requirements.txt Causes Silent Runtime Failure

**What goes wrong:** `content_editor.py` and `blog_generator.py` import the `openai` SDK at module load time. If the SDK is not installed (fresh environment, new developer, CI), the import fails with `ModuleNotFoundError` at the start of the pipeline — before any audio is processed. The error message mentions `openai` which is confusingly similar to `openai-whisper`, which is listed in `requirements.txt`.

**Prevention:** Add `openai>=1.0.0` to `requirements.txt` immediately. Long-term, consider routing all LLM calls through `ollama_client.py` to eliminate the dependency.

**Phase relevance:** Should be resolved in tech debt phase before any other phase deploys.

---

### Pitfall 12: TikTok Token Expiry Causes Silent Upload Skip

**What goes wrong:** TikTok access tokens expire (typically every 24 hours). The uploader reads the token from `Config.TIKTOK_ACCESS_TOKEN` with no expiry check. An expired token produces a 401 from TikTok's API, which is logged but not raised. The pipeline continues and marks TikTok upload as "done."

**Prevention:** Add an explicit token expiry timestamp to the TikTok config (or fetch it programmatically from TikTok's token endpoint). Check it before attempting upload and skip with a clear `WARNING: TikTok token expired — re-auth required` message rather than a silent failure.

**Phase relevance:** Any phase that makes TikTok upload production-ready.

---

### Pitfall 13: WhisperX/PyTorch Version Lock Breaks on New Hardware

**What goes wrong:** `whisperx==3.1.6` pins `torch==2.1.0`. NVIDIA GPU drivers for Ada Lovelace (RTX 40xx) and newer architectures require PyTorch 2.2+. Running on a new GPU will produce either CUDA initialization errors or degraded performance, and the error message does not suggest the version conflict as the cause.

**Prevention:** Test `whisperx>=3.2.0` with the latest stable PyTorch before upgrading hardware. Pin the combination that works and document it in `requirements.txt` comments.

**Phase relevance:** Infrastructure/dependency update phase.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Audio ducking implementation | Timestamp drift causes wrong mute windows (Pitfall 1) | Add PAD_MS buffer + QA clip exports |
| LUFS normalization | Silent dynamic mode fallback (Pitfall 2) | Parse `normalization_type` from first-pass JSON |
| main.py refactor | Checkpoint key names break resume (Pitfall 3) | Freeze key names before refactor; add regression test |
| Scheduler wiring | Stub marks uploads done without uploading (Pitfall 4) | Replace stub before enabling scheduled mode |
| Instagram pipeline wiring | API version v18.0 is deprecated (Pitfall 6) | Move to v22.0 via env var before wiring |
| Twitter/social copy generation | Voice inconsistency across episodes (Pitfall 8) | Add few-shot examples to all LLM prompts |
| main.py refactor | continue_episode.py becomes broken recovery tool (Pitfall 9) | Deprecate or cover with smoke tests before refactor |
| Any new platform expansion | Token expiry silently marks uploads done (Pitfall 12) | Validate tokens at pipeline start, not at upload time |

---

## Sources

- [ffmpeg loudnorm filter documentation](http://k.ylo.ph/2016/04/04/loudnorm.html) — MEDIUM confidence (official author's blog, not Meta/FFmpeg docs)
- [ffmpeg-normalize PyPI package](https://pypi.org/project/ffmpeg-normalize/1.31.2/) — HIGH confidence (official PyPI)
- [WhisperX word-level timestamp accuracy issue #1247](https://github.com/m-bain/whisperX/issues/1247) — HIGH confidence (project maintainer GitHub)
- [Twitter API v2 Free Plan media upload rate limits](https://devcommunity.x.com/t/what-are-the-rate-limits-for-media-upload-when-used-with-twitter-api-v2-free-tier/245725) — MEDIUM confidence (official dev community, but rate limits change)
- [Instagram Graph API changelog](https://developers.facebook.com/docs/instagram-platform/changelog/) — HIGH confidence (Meta official docs)
- [Meta Graph API v22.0 (April 2025)](https://help.pressboardmedia.com/meta-graph-api-v22.0) — MEDIUM confidence (third-party summary of Meta release notes)
- [CrisperWhisper: Accurate Timestamps on Verbatim Speech Transcriptions](https://arxiv.org/html/2408.16589v1) — HIGH confidence (academic paper on Whisper timestamp limitations)
- [God Object anti-pattern in Python](https://softwarepatternslexicon.com/patterns-python/11/2/4/) — MEDIUM confidence (community resource)
- [Data pipeline state management pitfalls](https://www.fivetran.com/blog/data-pipeline-state-management-an-underappreciated-challenge) — MEDIUM confidence (industry blog)
- [OpenAI prompt engineering guide](https://platform.openai.com/docs/guides/prompt-engineering) — HIGH confidence (official OpenAI docs)
- Project-specific analysis derived from `.planning/codebase/CONCERNS.md` — HIGH confidence (direct codebase audit)
