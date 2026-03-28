# Project Research Summary

**Project:** Podcast Automation — v1.4 Real-World Testing & Sales Readiness
**Domain:** Podcast production pipeline — multi-genre client testing and sales demo packaging
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

The v1.4 milestone is fundamentally about proving the existing pipeline works with real clients across multiple genres, then packaging that proof into a compelling sales demo. This is not a feature-build milestone — it is a validation and sales-readiness milestone. The core pipeline is fully built (570 tests, 5 shipped phases), but it is deeply comedy-tuned with hardcoded Fake Problems defaults that will corrupt output for any other genre if not explicitly overridden. The primary engineering risk is config leakage: host names, voice persona examples, and podcast name are all embedded in the codebase in ways that silently fall back to Fake Problems values if a client YAML fails to override them.

The recommended approach is a four-phase build: (1) fix config leakage and set up real client YAMLs before processing a single episode, (2) add RSS episode sourcing to unblock non-Dropbox clients, (3) run real genre episodes and fix integration issues as they surface, and (4) package demo output for sales. The single most important technical change is decoupling `DropboxHandler` instantiation from ingest — the current architecture raises `ValueError` for any client without Dropbox credentials, which is every real client targeted for v1.4. Only one new dependency is required (`feedparser>=6.0.12`); everything else is YAML config authoring and targeted code fixes.

The competitive positioning is strong: the pipeline does more than Swell AI, Castmagic, or Descript in a single command at near-zero ongoing cost (~$1-3 in OpenAI tokens per episode vs. $29-200/episode alternatives). The demo must lead with output quality and cost, not the command-line interface. The before/after audio comparison (raw vs. normalized + censored) is the single most persuasive artifact for a 30-minute sales conversation. Demo quality is entirely dependent on persona quality — authoring genre-appropriate `voice_persona` YAML content before running any episode is the highest-leverage preparation step.

## Key Findings

### Recommended Stack

The v1.4 stack requires only one new package addition. `feedparser>=6.0.12` handles all RSS/Atom feed variants plus iTunes extension tags (`itunes:episode`, `itunes:duration`, enclosure URLs) in a single library. Audio download reuses the existing `requests` streaming pattern already used in `dropbox_handler.py`. Demo packaging uses stdlib `zipfile`/`shutil` plus the existing `jinja2` dependency already in `pyproject.toml`. No PDF libraries — WeasyPrint requires GTK+/MSYS2 on Windows; wkhtmltopdf was archived in January 2023. Self-contained HTML is the correct demo format for media-rich content that embeds actual clips.

**Core technologies:**
- `feedparser>=6.0.12` (new): RSS/Atom feed parsing including iTunes tags — only new dependency needed; confirmed on PyPI September 2025
- `requests>=2.31.0` (existing): streaming audio download with progress bar, reuses `dropbox_handler.py` pattern with `tqdm`
- `jinja2>=3.0.0` (existing): demo HTML summary page generation, same pattern as `episode_webpage_generator.py`
- `zipfile` / `shutil` (stdlib): demo package archive creation — no external dependency
- No new AI/LLM packages: genre tuning is YAML config authoring and prompt engineering, not model switching

### Expected Features

The pipeline already produces every deliverable a prospect expects (clips, show notes, thumbnails, social captions, chapters, RSS). The gap is packaging and narrative — prospects cannot evaluate what they cannot understand. The before/after audio comparison is both a demo table stake and the one feature requiring a pipeline change (the pipeline does not currently snapshot raw audio before Step 4 censor).

**Must have (table stakes for demo):**
- Before/after audio comparison (raw vs. processed 60-sec segment) — fastest trust-builder; requires pre-censor snapshot addition to pipeline
- Organized demo folder per client with all deliverables — processed MP3, 2-3 captioned clips, show notes, thumbnail, social captions, chapter list, compliance report
- Genre-appropriate voice persona in AI output — wrong tone destroys the demo before quality is assessed
- `DEMO.md` per client explaining what was automated, estimated time saved, cost per episode, LUFS metrics — makes artifacts interpretable to a non-technical prospect

**Should have (competitive differentiators to surface):**
- Clip energy scores and selection rationale in demo — shows clips chosen by scoring model, not randomly
- Compliance report in demo package — no SaaS tool offers this; critical differentiator for brand podcasts
- LUFS before/after in demo README — demonstrates professional broadcast-standard audio mastering (Spotify requires -14 LUFS)
- Cost per episode estimate (~$1-3 OpenAI tokens) — primary moat vs. $29-200/episode alternatives

**Defer (post-demo validation or v2+):**
- White-label output for agency resale
- Client Dropbox folder handoff automation (useful at 3+ active clients)
- Demo video walkthrough for async cold outreach (defer until live demo is validated)
- Dynamic ad insertion (requires CDN, IAB DAAST compliance — architecturally incompatible with zero-cost model)
- Filler word removal (kills comedy timing; degrades interview cadence; high false-positive rate — off by default per project feedback)

### Architecture Approach

The v1.4 additions layer cleanly onto the existing pipeline without touching core logic. Three new/modified patterns drive everything: (1) `Config.EPISODE_SOURCE` flag gates whether ingest calls `RSSEpisodeFetcher` or `DropboxHandler`, fixing the critical blocker where `DropboxHandler.__init__()` raises `ValueError` for clients without Dropbox credentials; (2) `Config.PODCAST_GENRE` injects genre context into the GPT-4o prompt as additive soft guidance alongside the existing `VOICE_PERSONA` field — no ContentEditor subclassing needed; (3) `DemoPackager` is a read-only view of existing pipeline output, never re-generating content, isolating demo packaging failure from pipeline risk.

**Major components:**
1. `rss_episode_fetcher.py` (new) — fetches feed metadata and downloads audio enclosure; peer to `dropbox_handler.py` in the `components` dict; conditionally constructed in `runner.py` based on `Config.EPISODE_SOURCE`
2. `demo_packager.py` (new) — reads `output/<client>/ep_N/` artifacts, assembles `demo/<client>/ep_N/` with summary HTML, clips copy, captions.txt, README.md; invoked via `main.py package-demo` command
3. `pipeline/steps/ingest.py` (modified) — branches on `Config.EPISODE_SOURCE`; moves `DropboxHandler` construction inside the `dropbox` branch only, eliminating the unconditional `ValueError` for non-Dropbox clients
4. `pipeline/steps/analysis.py` (modified) — reads `Config.PODCAST_GENRE` and `Config.COMPLIANCE_ENABLED`; injects genre context into `ContentEditor.analyze_content()` call
5. `client_config.py` / `config.py` (modified) — four new Config fields: `EPISODE_SOURCE`, `RSS_FEED_URL`, `PODCAST_GENRE`, `COMPLIANCE_ENABLED`; all additive with env-var defaults

### Critical Pitfalls

1. **`DropboxHandler` unconditionally constructed in `runner.py`** — raises `ValueError` for every real client without Dropbox credentials; blocks the entire pipeline before ingest starts. Fix: gate `DropboxHandler` construction behind `EPISODE_SOURCE == "dropbox"` check in `_init_components()`. This is the highest-priority architectural fix for v1.4.

2. **`Config.NAMES_TO_REMOVE` falls back to Fake Problems host names** — silently censors any client episode featuring a guest named "Evan", "Joey", or mentions of "Gross" as a word. Fix: require `names_to_remove` as an explicit field in every client YAML; treat absence as a `validate-client` error, not a silent fallback to comedy defaults.

3. **Hardcoded Fake Problems voice examples in `_build_analysis_prompt()`** — the BAD/GOOD example block (lobster immortality, etc.) is a string literal that fires for every client regardless of `voice_persona` setting. Corrupts show notes, chapter titles, and social captions for non-comedy genres even when `voice_persona` is correctly configured. Fix: make the example block conditional on client type; omit or replace for non-comedy clients.

4. **Whisper `base` model degrades on real-world audio** — comedy studio WAV files at ~700MB are not representative of client audio quality. Phone recordings, compressed MP3s, and non-native speakers can drop word accuracy from ~95% to 70-80%, cascading into broken censor timestamps and bad clip selection. Fix: add `whisper_model` to client YAML; default to `small` for unknown audio quality; spot-check transcript JSON before proceeding past Step 2.

5. **Episode number parsing assumes `ep25` filename convention** — date-based (`2024-03-15-title.mp3`), slug-based, or `S01E03` filenames resolve `episode_number` to `None`, causing checkpoint key collisions and analytics overwrites. Fix: verify with `--dry-run` before first live run per client; pre-rename files to `ep01_original-name.ext` convention if needed.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Client Configuration & Config Hardening
**Rationale:** Config leakage (host names, voice persona, podcast name) is a prerequisite failure mode that corrupts every downstream step. Must be resolved before processing a single real episode. Real client YAML configs and explicit `validate-client` checks must exist before anything else.
**Delivers:** 2-3 real genre client YAMLs (true crime, business/interview, one more) with correct `voice_persona`, `names_to_remove`, `words_to_censor`, `whisper_model`; enhanced `validate-client` that flags missing content fields and verifies `Config.PODCAST_NAME` matches YAML after activation; `--dry-run` prints active Config values for audit before any live run
**Addresses:** Genre-appropriate tone (demo table stake); DEMO.md persona accuracy
**Avoids:** Pitfalls — NAMES_TO_REMOVE leakage (Pitfall 1), voice persona corruption (Pitfall 2), podcast name leakage (Pitfall 7), episode number parse failure (Pitfall 6)

### Phase 2: RSS Episode Source (Ingest Decoupling)
**Rationale:** Every real client target for v1.4 uses RSS, not Dropbox. The `DropboxHandler` construction blocker must be resolved before any real episode can be processed. This is the single architectural change that unblocks all client testing.
**Delivers:** `rss_episode_fetcher.py` with `feedparser`; `EpisodeMeta` dataclass; conditional component construction in `runner.py`; branched `pipeline/steps/ingest.py`; new Config fields (`EPISODE_SOURCE`, `RSS_FEED_URL`, `PODCAST_GENRE`, `COMPLIANCE_ENABLED`, `CENSOR_ENABLED`); `_YAML_TO_CONFIG` mapping extensions; `tests/test_rss_episode_fetcher.py`
**Uses:** `feedparser>=6.0.12` (new dep, `uv add feedparser`); existing `requests` streaming + `tqdm` progress bar pattern
**Implements:** Episode Source Abstraction via Config Flag (Architecture Pattern 1); Conditional Component Initialization in `runner.py` (Architecture Pattern 4)
**Avoids:** Pitfall — unconditional `DropboxHandler` construction blocking non-Dropbox clients (Pitfall — critical architectural blocker)

### Phase 3: Integration Testing & Genre-Aware Pipeline Fixes
**Rationale:** Processing real episodes will surface genre-specific failures that cannot be predicted without running real audio. Voice examples leaking, energy scoring wrong for interview format, and compliance thresholds miscalibrated are data-driven discoveries. This phase is empirical.
**Delivers:** Fixed `_build_analysis_prompt()` voice examples block (conditional on client type); genre context injection in `analysis.py`; `COMPLIANCE_ENABLED` flag respected in audio step; `CENSOR_ENABLED` flag; `clip_selection_mode` YAML field for energy vs. content-weighted clip selection; processed first real episode per genre with quality validation; manual transcript spot-check gate documented
**Addresses:** Differentiators — energy-scored clip selection calibrated per genre; compliance report; genre-appropriate AI output tone
**Avoids:** Pitfalls — energy scoring wrong for flat-energy interview podcast (Pitfall 3), compliance calibration wrong for genre (Pitfall 4), Whisper model too weak for client audio (Pitfall 5)

### Phase 4: Demo Packaging & Sales Readiness
**Rationale:** Once real episodes produce quality output across genres, package the output as a persuasive sales leave-behind. Phase 4 depends on Phase 3 producing good artifacts — a demo package of bad output is worse than no demo. Before/after audio snapshot requires a pipeline change independent of the demo packaging module.
**Delivers:** `demo_packager.py` with `DemoPackager` class; `package-demo` CLI command in `main.py`; `demo/<client>/ep_N/` structure with self-contained summary HTML (base64 thumbnail), clips copy, thumbnail, captions.txt, blog_post.html, README.md; `DEMO.md` per client with automation narrative, time saved estimate, LUFS metrics, clip scores, cost per episode; before/after audio snapshot (pipeline change to capture raw 60-sec segment before Step 4 censor); `tests/test_demo_packager.py`
**Uses:** `jinja2` (existing) for summary HTML generation; stdlib `zipfile`/`shutil` for archive
**Implements:** Demo Package as Read-Only View of Existing Output (Architecture Pattern 3)
**Avoids:** Pitfall — demo output not reviewed before presenting (UX pitfall — manual review gate before packaging)

### Phase Ordering Rationale

- Phase 1 before everything: No point downloading a real episode if Config output will contain Fake Problems host names in the censorship pass. YAML configs must be correct before any real audio is processed.
- Phase 2 before Phase 3: Cannot process real RSS episodes without the ingest decoupling. The `DropboxHandler` blocker is a hard prerequisite.
- Phase 3 before Phase 4: Demo packaging of poor-quality output is counterproductive. Quality must be validated per genre before assembling a sales artifact.
- Phases 1 and 2 have no code dependency between them and can be developed in parallel. Phase 1 YAML authoring should complete first so Phase 3 test runs have correct configs from the start — the two are sequentially ordered by workflow, not by code.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** Genre-specific clip quality is empirical — can only be validated by running real audio. The `voice_persona` prompt content for true crime and business genres needs iteration based on actual output review. No pre-research can substitute for running a real episode and reading the show notes output.
- **Phase 3:** Compliance calibration per genre requires manual review of first-run output. The right thresholds for true crime vs. business vs. comedy cannot be theorized — they must be observed and adjusted based on what the compliance checker actually produces.

Phases with standard patterns (skip research):
- **Phase 1:** YAML authoring and `validate-client` enhancement follow established patterns; no research needed
- **Phase 2:** `feedparser` is well-documented; conditional component construction extends the existing try/except pattern in `runner.py`; `feedparser.readthedocs.io` has confirmed enclosure and iTunes tag support
- **Phase 4:** `DemoPackager` follows the same read-only-copy pattern as other post-pipeline tools; `jinja2` template generation is established in the codebase (`episode_webpage_generator.py`)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Only one new library (`feedparser>=6.0.12`); version confirmed on PyPI September 2025; all other technologies are existing deps or stdlib |
| Features | MEDIUM | Industry competitor feature comparison from MEDIUM-confidence sources; table stakes list is well-grounded. Demo format and persuasion angle recommendations are reasoned inference, not field-tested |
| Architecture | HIGH | Based on direct code inspection of all relevant modules with line-number citations. The DropboxHandler blocker is confirmed code-level issue. All 4 architectural patterns are grounded in existing codebase patterns |
| Pitfalls | HIGH | All 7 critical pitfalls confirmed via direct codebase analysis with specific line numbers in `content_editor.py`, `config.py`, `client_config.py`. Not hypothetical — these are actual hardcoded values that produce incorrect output for non-comedy clients |

**Overall confidence:** HIGH

### Gaps to Address

- **Before/after audio snapshot implementation:** The exact extraction approach (which timestamp, how to expose a raw segment to `DemoPackager`) needs design during Phase 4 planning. The pipeline currently normalizes in-place and does not expose a pre-censor copy path. Requires targeted change to `pipeline/steps/audio.py`.
- **Genre-tuned clip scoring:** The `clip_selection_mode` YAML field (energy vs. content vs. balanced) is specified in architecture research but the `AudioClipScorer` modification to respect this flag is not detailed. Phase 3 may need to address how to suppress or weight the energy candidates block for flat-energy interview audio.
- **Compliance `compliance_style` field:** PITFALLS.md recommends a `permissive`/`standard`/`strict` flag but this is not mapped to a concrete `ContentComplianceChecker` prompt change. Needs design during Phase 3 once first-run compliance output is reviewed per genre.
- **RSS `episode_index` boundary behavior:** The `episode_index` field (0 = latest, 1 = second-most-recent) behavior when the feed has fewer entries than expected needs explicit error handling in `RSSEpisodeFetcher` to avoid silent `IndexError` failures.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `pipeline/steps/ingest.py`, `pipeline/runner.py`, `client_config.py`, `dropbox_handler.py`, `config.py`, `content_editor.py` (lines 263–285, 287), `audio_clip_scorer.py`, `clients/example-client.yaml`
- [feedparser 6.0.12 on PyPI](https://pypi.org/project/feedparser/) — version confirmed, released September 10, 2025
- [feedparser official docs](https://feedparser.readthedocs.io/en/latest/introduction/) — enclosure and iTunes extension parsing confirmed
- [Python zipfile stdlib](https://docs.python.org/3/library/zipfile.html) — packaging approach confirmed
- [Python shutil stdlib](https://docs.python.org/3/library/shutil.html) — `make_archive()` confirmed

### Secondary (MEDIUM confidence)
- [Professional Podcast Production Services — PropodcastSolutions](https://propodcastsolutions.com/podcast-production-services/) — industry feature expectations
- [Top 17 Podcast Production Companies 2026 — Content Allies](https://contentallies.com/learn/podcast-production-companies-agencies-services-for-b2b-b2c) — competitor feature analysis
- [Viral Podcast Clips Guide 2025 — Fame](https://www.fame.so/post/ultimate-podcast-clip-guide) — clip content standards per genre
- [True Crime Podcast Guide — Jellypod](https://jellypod.ai/blog/perfect-guide-true-crime) — genre-specific content and tone expectations
- [B2B Podcast Production Checklist — Rise25](https://rise25.com/lead-generation/b2b-podcast-production-checklist/) — business podcast deliverable requirements
- [Pilot Project Structure — Ankord Media](https://www.ankordmedia.com/blog/bay-area-startups-structure-podcast-agency-pilot-project) — trial episode and demo package structure
- [Science of Viral Podcast Clips — Listeners to Clients](https://listenerstoclients.com/blog/the-science-of-viral-podcast-clips-a-proven-framework-for-high-impact-content) — clip selection criteria

### Tertiary (LOW confidence)
- [WeasyPrint Windows issues](https://github.com/Kozea/WeasyPrint/issues/1464) — GTK+/MSYS2 complexity on Windows 11; used to reject PDF output approach
- [wkhtmltopdf archived](https://github.com/wkhtmltopdf/wkhtmltopdf) — confirmed abandoned January 2023; used to reject pdfkit approach
- [AI-Powered Podcast Service for Agencies — 51Blocks](https://51blocks.com/ai-podcasts-for-agencies) — marketing page, directional signal only

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
