# Technology Stack

**Project:** Podcast Automation Pipeline Upgrade
**Researched:** 2026-03-16

---

## Existing Stack (Do Not Replace)

The current stack is working. These are NOT candidates for replacement:

| Technology | Version (pinned) | Role |
|------------|-----------------|------|
| Python | 3.12+ | Language |
| openai-whisper | 20231117 | Local transcription |
| whisperx | 3.1.6 | Diarization + word alignment |
| torch / torchaudio | 2.1.0 | ML backend |
| pydub | 0.25.1 | Audio manipulation |
| ffmpeg-python | 0.2.0 | FFmpeg bindings |
| FFmpeg binary | system | Media processing engine |
| Pillow | 10.2.0 | Thumbnail generation |
| tweepy | 4.14.0 | Twitter/X posting |
| google-api-python-client | 2.116.0 | YouTube uploads |
| dropbox | 12.0.2 | Storage |
| Ollama (local) | HTTP | LLM inference (Llama 3.2) |

---

## New Stack Additions

### Audio: LUFS Normalization

**Recommended:** `ffmpeg-normalize` 1.37.3

**Why:** The existing `audio_processor.py` already uses FFmpeg for audio processing. `ffmpeg-normalize` wraps FFmpeg's two-pass `loudnorm` filter — the EBU R128 standard used by Spotify, YouTube, and broadcast radio. Single dependency, no ML stack required, produces the exact same output as professional DAWs. Ships as a CLI tool but is fully usable as a Python library.

**Why not `pyloudnorm`:** pyloudnorm (0.2.0, Jan 2026) measures loudness using ITU-R BS.1770 but does NOT apply normalization itself — you still need to implement gain application. It is primarily a measurement tool. For a pipeline that needs measure-then-normalize in one pass, `ffmpeg-normalize` is the right abstraction.

**Why not raw `ffmpeg-python` with loudnorm filter:** You can call the loudnorm filter directly with the existing `ffmpeg-python` binding. This works but requires two-pass implementation from scratch. `ffmpeg-normalize` already implements this correctly and handles edge cases (clipping, true peak limiting). Use it.

```bash
pip install ffmpeg-normalize==1.37.3
```

**Confidence:** HIGH — Official PyPI page confirmed version and release date (Feb 8, 2026).

---

### Audio: Ducking and Volume Automation

**Recommended:** FFmpeg `sidechaincompress` + `amix` filters via existing `ffmpeg-python`

**Why:** Audio ducking (volume dip when censoring instead of a beep) does not require a new library. FFmpeg has native sidechain compression support. The existing `ffmpeg-python==0.2.0` binding can construct these filter graphs. The `pydub` pattern of "manipulate AudioSegment objects" works fine for simpler segment-level ducking: identify the censor window from the transcript, extract the segment, apply `segment - N_db` for the dip duration with fade-in/out.

**Implementation pattern:** Transcript already has millisecond-accurate word timestamps from WhisperX. The censor step knows exactly when banned words occur. Apply a programmatic volume envelope via pydub's `.fade()` and `.apply_gain()` on that window. No new library needed.

**Why not `autoducking` package:** The `autoducking` project on GitHub is a single-purpose tool for music-under-voiceover scenarios (background music ducking). That is not the use case here. The use case is censorship ducking on a single audio track, which pydub handles directly.

**Confidence:** HIGH — pydub volume automation is well-documented. FFmpeg sidechain compress is available in current FFmpeg builds.

---

### Audio: Feature Analysis for Clip Detection

**Recommended:** `librosa` 0.11.0

**Why:** Smarter clip detection requires understanding audio energy, speech rate changes, laughter patterns, and engagement peaks — not just transcript topic shifts. `librosa` provides onset detection, RMS energy tracking, spectral analysis, and zero-crossing rate, all of which are signals for identifying high-engagement moments in a comedy podcast.

**Specific signals to extract for clip scoring:**
- Energy bursts (RMS spike) → likely reaction or punchline
- Speech rate from WhisperX word timestamps (already available) → rapid fire = energy
- Onset density → overlapping speech = crosstalk = engagement
- Silence gaps → natural clip endpoints

`librosa` is the dominant library for audio ML feature extraction in Python (38k+ GitHub stars, actively maintained, Python 3.8–3.13 supported as of 0.11.0).

**Why not pyAudioAnalysis:** pyAudioAnalysis is older, less maintained, and adds a heavier dependency footprint. `librosa` is the current standard.

**Why not a paid service (Opus Clip, Clipcast):** Out of scope — project constraint is no new paid APIs.

```bash
pip install librosa==0.11.0
```

**Confidence:** HIGH — PyPI page confirmed version 0.11.0, released March 11, 2025.

---

### Social: Bluesky

**Recommended:** `atproto` 0.0.65

**Why:** `atproto` is the official AT Protocol Python SDK. It is auto-generated from the Bluesky lexicons, fully type-hinted, supports both sync and async clients, and handles image blob upload, rich text facets (links, mentions), and post creation. It is the only Python library with official endorsement from the Bluesky/ATProto team. The Bluesky API requires no app approval — just an app password from account settings.

**Usage pattern:** Same two-step as Twitter — authenticate, send_post(). Media is uploaded as a blob first, then referenced in the post record. This mirrors the existing tweepy pattern closely.

```bash
pip install atproto==0.0.65
```

**Confidence:** HIGH — PyPI page confirmed version 0.0.65, released December 8, 2025.

---

### Social: Threads

**Recommended:** `pythreads` 0.2.1 (with caveat — see below)

**Why:** Meta has an official Threads API (part of Meta Graph API). `pythreads` wraps this official API using OAuth 2.0, handles the two-step container-create/publish flow, supports image and carousel posts, and has 93% test coverage. It is the closest Python library to an official, tested wrapper.

**Caveat:** `pythreads` is still in beta (pre-1.0, last release July 2024). The official Meta Threads API itself requires app review for some publishing permissions. Before building the Threads uploader, verify that the Fake Problems Podcast's Meta developer account has publishing permissions approved.

**Alternative:** If `pythreads` proves insufficient, the Threads API is a straightforward REST API (POST to graph.facebook.com/v19.0/) and can be called directly via the existing `requests` library using the same pattern as the existing Instagram uploader. This is the fallback — no library required, just two HTTP calls.

**Why not MetaThreads or threads-api (unofficial):** Both reverse-engineer Instagram's private API. They break when Meta changes internals and carry ban risk. Do not use.

```bash
pip install pythreads==0.2.1
```

**Confidence:** MEDIUM — Package verified on PyPI, but beta status and Meta app review requirements add uncertainty. Official Meta Threads API documentation should be consulted before implementation.

---

### Content Generation: Keyword Extraction for SEO

**Recommended:** `keybert` 0.9.0

**Why:** Blog posts and episode descriptions generated by Ollama will benefit from keyword extraction to improve search discoverability. KeyBERT uses BERT embeddings to extract keywords and keyphrases most relevant to the document — significantly better than TF-IDF or RAKE for conversational podcast transcript text. Integrates with `sentence-transformers` (already used by the ML stack via torch). Minimal overhead: one call per episode.

**Why not spaCy:** spaCy is heavier and requires model downloads. For keyword extraction specifically, KeyBERT is more accurate and simpler.

**Why not a custom Ollama prompt:** LLM keyword extraction is inconsistent in format and requires prompt engineering maintenance. KeyBERT is deterministic and returns ranked keyphrases directly.

```bash
pip install keybert==0.9.0
```

**Confidence:** HIGH — PyPI confirmed version 0.9.0, released February 7, 2025.

---

### CLI Refactoring: main.py God Object

**Recommended:** `click` (already available as transitive dep) or standard `argparse` with explicit subcommand modules

**Why:** The 1700-line `main.py` needs decomposition. The recommended pattern for this codebase (flat module structure, no src/ directory) is to split orchestration by pipeline stage into separate orchestrator modules, with `main.py` as a thin dispatcher. This does NOT require adding a new CLI framework — the existing `argparse`-based CLI in `main.py` can be preserved and the internal logic moved to separate `pipeline_*.py` or `steps/` modules.

**Why not Typer or Click migration:** Migrating the CLI interface is scope creep. The interface (`python main.py ep29 --auto-approve`) must not break. Internal decomposition is a refactor, not a CLI replacement.

**No new package needed** — this is an architecture change, not a library addition.

**Confidence:** HIGH — This is a code organization decision, not a library choice.

---

## Packages to Fix (Not New — But Broken)

| Problem | Current State | Fix |
|---------|--------------|-----|
| `openai` SDK missing from requirements.txt | `blog_generator.py` uses it, requirements.txt omits it | Add `openai>=1.0.0` (or remove usage in favor of Ollama) |
| `torch==2.1.0` is outdated | Released 2023, PyTorch 2.6 is current | Upgrade carefully — WhisperX pins torch, check compatibility before upgrading |
| `tweepy==4.14.0` | Released 2023, current is 4.15+ | Minor upgrade safe, check Twitter API v2 endpoint changes |

---

## Packages Evaluated and Rejected

| Package | Use Case | Decision | Reason |
|---------|----------|----------|--------|
| `pyloudnorm` | LUFS measurement | Rejected (for normalization) | Measurement only, not normalization — use `ffmpeg-normalize` instead |
| `autoducking` | Audio ducking | Rejected | Designed for music-under-voice, not censorship ducking. pydub + ffmpeg sufficient |
| `pyAudioAnalysis` | Audio feature extraction | Rejected | Older, less maintained than librosa |
| `MetaThreads` / `threads-api` (unofficial) | Threads posting | Rejected | Reverse-engineered, fragile, ban risk |
| `spaCy` | Keyword extraction | Rejected | Too heavy for keyword-only use case; KeyBERT is more accurate with less overhead |
| Opus Clip / Clipcast | Clip detection | Rejected (paid) | Project constraint: no new paid APIs |

---

## Full Dependency Delta

Libraries to add to `requirements.txt`:

```
# Audio normalization (LUFS / EBU R128)
ffmpeg-normalize==1.37.3

# Audio feature extraction (smarter clip detection)
librosa==0.11.0

# Bluesky social posting
atproto==0.0.65

# Threads social posting (Meta official API wrapper)
pythreads==0.2.1

# Keyword extraction for SEO
keybert==0.9.0

# Fix: OpenAI SDK (currently used but not pinned)
openai>=1.0.0
```

---

## Sources

- [ffmpeg-normalize PyPI](https://pypi.org/project/ffmpeg-normalize/) — version 1.37.3, released Feb 8, 2026
- [ffmpeg-normalize GitHub (slhck)](https://github.com/slhck/ffmpeg-normalize) — EBU R128, two-pass loudnorm
- [pyloudnorm PyPI](https://pypi.org/project/pyloudnorm/) — version 0.2.0, Jan 4, 2026
- [pyloudnorm GitHub](https://github.com/csteinmetz1/pyloudnorm) — BS.1770 measurement only
- [librosa PyPI](https://pypi.org/project/librosa/) — version 0.11.0, March 11, 2025
- [librosa GitHub](https://github.com/librosa/librosa) — audio/music signal analysis
- [atproto PyPI](https://pypi.org/project/atproto/) — version 0.0.65, December 8, 2025
- [atproto GitHub (MarshalX)](https://github.com/MarshalX/atproto) — official AT Protocol Python SDK
- [Bluesky API docs](https://docs.bsky.app/docs/get-started)
- [pythreads PyPI](https://pypi.org/project/pythreads/) — version 0.2.1, July 15, 2024
- [pythreads GitHub (marclove)](https://github.com/marclove/pythreads) — Meta Threads official API wrapper
- [Threads API documentation](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api)
- [keybert PyPI](https://pypi.org/project/keybert/) — version 0.9.0, February 7, 2025
- [keybert GitHub (MaartenGr)](https://github.com/MaartenGr/KeyBERT)
- [Python Audio Tools 2025 — graphlogic.ai](https://graphlogic.ai/blog/resources-tools/best-python-tools-audio-manipulation/)
- [Building CLI Tools with Python 2025 — dasroot.net](https://dasroot.net/posts/2025/12/building-cli-tools-python-click-typer-argparse/)
