# Project Research Summary

**Project:** Podcast Automation — v1.5 First Paying Client
**Domain:** Go-to-market for a podcast production automation service
**Researched:** 2026-03-28
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a go-to-market milestone, not a technical one. The pipeline is fully built and battle-tested across multiple clients. The v1.5 work is about finding the right podcast prospects, processing a demo using their actual content (with consent), generating personalized outreach copy, and tracking the conversion to first paying client. The recommended approach is a linear four-step process: discover and qualify prospects via iTunes Search API → process one episode per prospect as a demo → generate a personalized pitch email/DM → execute outreach manually with lightweight contact tracking.

The technical implementation requires zero new packages. Three new modules (`prospect_finder.py`, `pitch_generator.py`, `outreach_tracker.py`) plug into the existing architecture using patterns already in the codebase: `requests` to the iTunes Search API, `feedparser` for RSS contact extraction, the existing `openai` SDK for GPT-4o pitch copy, and `sqlite3` for the contact log. All three follow the project's `self.enabled` convention. `OutreachTracker` mirrors `search_index.py` exactly; `PitchGenerator` mirrors `content_editor.py` exactly.

The highest-leverage risk in this milestone is non-technical: processing a prospect's episode without their explicit consent. Running someone's audio through transcription, AI analysis, and clip generation for a commercial pitch — even from a public RSS feed — creates copyright and GDPR exposure, and risks reputational damage in a tightly connected community. The mitigation is a consent-first workflow: contact the prospect first, ask to run their episode as a free demo, then process only after they agree. This converts a legal risk into a warm lead. Pricing should be anchored to delivered value ($300–600/episode entry), not pipeline cost ($1–3/episode), to avoid commoditizing the service.

---

## Key Findings

### Recommended Stack

All three new capability areas build entirely on existing dependencies. No new packages are needed. The iTunes Search API requires no auth and is covered by a direct `requests.get()` call; the archived `podsearch` library and `python-podcastindex` (requires HMAC auth) are both deferred. The outreach contact tracker uses `sqlite3` following the exact pattern of `search_index.py`. GPT-4o via the existing `openai` SDK is the right choice for pitch copy over local Ollama — the quality gap matters for persuasive writing, and cost is approximately $0.01–0.02 per pitch.

**Core technologies:**
- `requests` (existing): iTunes Search API calls — free, no auth, 200 results per call
- `feedparser` (existing since v1.4): RSS contact extraction from `itunes:email` / `managingEditor` fields
- `openai` SDK (existing): GPT-4o at temperature 0.7 for personalized pitch email and DM copy
- `sqlite3` (stdlib): Outreach contact log — two tables (prospects, contacts), no ORM
- `jinja2` (existing): Structural templates for pitch formatting, wrapping GPT-4o output

### Expected Features

**Must have (table stakes — no client without these):**
- Prospect list (3-5 qualified shows) — research task, not code
- Prospect qualification criteria checklist — ICP definition before any demo investment
- RSS contact extraction — `itunes:email` from feedparser; approximately 15 lines of code
- Demo run per prospect — existing pipeline + `package-demo`; requires consent before processing
- Personalized pitch email per prospect — references specific episode, LUFS delta, clip count, show note excerpt
- Contact tracker — CSV or SQLite, updated after each interaction

**Should have (differentiators that increase conversion):**
- Demo built from prospect's own episode (with consent) — eliminates imagination from prospect's evaluation; most persuasive artifact
- `gen-pitch` CLI command — reads `_analysis.json` + `DEMO.md`, outputs `PITCH.md` to demo folder
- Before/after audio segment — already in `demo_packager.py`; verify working per-client before outreach
- Genre-matched voice persona in YAML before demo run — prevents off-brand output that kills deals
- Estimated time-saved table and cost-per-episode breakdown — already in `DEMO.md` template; verify accuracy

**Defer until after first client signs:**
- Automated prospect scraping — not justified until pitch is validated at scale (20+ prospects)
- Full CRM (HubSpot, Pipedrive, Airtable) — overkill until 3+ active clients
- Automated email sending / sequences — spam risk at a domain with no sending history
- Proposal generation tool — write manually after first interested reply
- Inbound SEO / content marketing — post-v1.5 concern entirely

### Architecture Approach

Three new standalone modules added to the flat module structure. Zero pipeline changes. All surface as new CLI commands in `main.py`'s existing `_handle_client_command()` dispatch table. Prospect identity is canonical in `clients/<slug>.yaml` (a `prospect:` block ignored by `activate_client()`); the SQLite database tracks events, not identity. Demo output from the existing `demo_packager.py` is the direct input to `pitch_generator.py` — no new pipeline steps or modifications to any existing pipeline component.

**Major components:**
1. `prospect_finder.py` (ProspectFinder) — iTunes Search API query + feedparser RSS enrichment + YAML `prospect:` block write; registers prospect in outreach DB via `OutreachTracker`
2. `pitch_generator.py` (PitchGenerator) — reads `demo/<client>/<ep>/DEMO.md` + `*_analysis.json` + client YAML; GPT-4o generates subject, email, and DM; writes `PITCH.md` to demo folder
3. `outreach_tracker.py` (OutreachTracker) — SQLite CRM at `output/outreach.db`; two tables (prospects + contacts); CRUD + status lifecycle (`identified → demo_processed → contacted → replied → call_scheduled → client | declined`)

### Critical Pitfalls

1. **Processing a prospect's episode without consent** — Creates copyright and GDPR exposure even for public RSS content; risks reputational damage in a small, interconnected community. Prevention: contact the prospect first, ask permission, process only after yes. Use Fake Problems as a fallback demo artifact if consent workflow is not yet established.

2. **Wrong voice persona in demo output** — Fake Problems comedy framing applied to a true crime or B2B show produces output the prospect immediately dismisses as a mismatch. Prevention: listen to the show, write a genre-specific `voice_persona` in the client YAML before running the pipeline; manually review all AI-generated output before packaging the demo.

3. **Targeting the wrong prospect size or stage** — Shows too large have production teams; shows too small have no budget. Prevention: filter for 1K–20K estimated monthly downloads, monetization signals (Patreon, sponsors), active release cadence, and visible production pain (no clips, no transcripts, sporadic schedule). Apply the ICP checklist before investing any demo processing time.

4. **Pricing from cost, not value** — Pipeline costs $1–3/episode in API tokens. Pricing at $50–75/episode signals a hobbyist tool and attracts price-sensitive churners. Prevention: anchor price to delivered value ($300–600/episode entry; move to monthly retainers quickly). Market rate for full-service podcast production is $500–2,000/episode or $1,500–5,000/month retainer.

5. **Pitching the technology instead of the outcome** — "I built a Python pipeline with Whisper and GPT-4o" produces no emotional response from a podcast host. Prevention: lead with the prospect's production pain and the specific output produced from their episode. The demo is evidence, not the pitch itself.

---

## Implications for Roadmap

The ARCHITECTURE.md research defines a clear build order based on data dependencies. Each phase is independently testable before the next begins.

### Phase 1: OutreachTracker (Contact Log)

**Rationale:** No external dependencies, no API keys, no file dependencies. Establishes the data store that ProspectFinder writes to, so it must exist first. Verifiable immediately with real SQLite + `tmp_path` tests. Building this first also forces the contact-tracking discipline before any outreach begins.
**Delivers:** `outreach_tracker.py`, `tests/test_outreach_tracker.py`, CLI subcommands `outreach log / list / update` in `main.py`
**Addresses:** Contact tracking feature; prevents duplicate outreach and lost warm leads (Pitfall 9 in PITFALLS.md)
**Avoids:** No-tracking scenario that allows aggressive follow-up damage and missed replies

### Phase 2: ProspectFinder (Discovery + Qualification)

**Rationale:** Depends on Phase 1 for persistence. iTunes API requires no auth — no setup friction, runnable immediately. RSS contact extraction uses existing `feedparser`. This is the entry point to the entire outreach funnel; nothing else can start without a qualified prospect list.
**Delivers:** `prospect_finder.py`, `tests/test_prospect_finder.py`, CLI commands `find-prospects` and `add-prospect` in `main.py`; `prospect:` block written to client YAML for each selected prospect
**Uses:** `requests` (iTunes Search API), `feedparser` (RSS enrichment), `OutreachTracker` (persistence)
**Avoids:** Pitfall 2 (wrong target size) via qualification criteria applied during prospect review before any demo investment

### Phase 3: PitchGenerator (Outreach Copy)

**Rationale:** Depends on Phase 2 for prospect YAMLs and depends on an existing demo run having produced output. GPT-4o integration mirrors `content_editor.py` exactly. `PitchGenerator` reads only local files — no live API calls during pitch generation (RSS data cached in YAML from Phase 2).
**Delivers:** `pitch_generator.py`, `tests/test_pitch_generator.py`, CLI command `gen-pitch <slug> <ep_id>` in `main.py`, `PITCH.md` written to demo folder per prospect
**Uses:** `openai` SDK (GPT-4o at temperature 0.7), existing `demo_packager.py` output, client YAML `prospect:` block
**Avoids:** Pitfall 5 (template-blast generic email), Pitfall 7 (pitching the tech), Pitfall 8 (pitch with no show-specific content)

### Phase 4: Manual End-to-End Validation (Outreach Execution)

**Rationale:** This is the actual sales work. Code is done after Phase 3. Find 3-5 real prospects, get consent, run demos, generate pitches, send manually, log in tracker. Validates messaging quality and ICP definition before any further optimization.
**Delivers:** First client conversation (and ideally, first paying client); validated pitch messaging; contact log with real data
**Avoids:** Pitfall 1 (consent-first workflow enforced before any processing), Pitfall 3 (value-based pricing introduced before any price is named), Pitfall 4 (voice persona review before demo packaging), Pitfall 6 (accurate expectation framing — "you review and approve" not "fully automated")
**Note:** No code deliverables in this phase. It is operational execution.

### Phase Ordering Rationale

- **Data store first:** `OutreachTracker` must exist before `ProspectFinder` can persist discoveries. Starting here also validates the SQLite pattern in isolation before it has dependents.
- **Discovery before generation:** `PitchGenerator` reads prospect YAML written by `ProspectFinder`. That YAML data must exist before pitch generation can run end-to-end.
- **Demo pipeline is untouched:** The existing `package-demo` command produces the input `PitchGenerator` reads. No pipeline changes means no regression risk to the existing 570-test suite.
- **Consent workflow reinforced by ordering:** A natural slug-to-YAML-to-demo flow requires the prospect to be registered in the tracker before demo processing begins, which creates a process-level checkpoint against the "process first, ask later" mistake.

### Research Flags

Phases with well-documented patterns (skip deeper research):
- **Phase 1 (OutreachTracker):** Direct copy of `search_index.py` SQLite pattern. No research needed.
- **Phase 3 (PitchGenerator):** Direct copy of `content_editor.py` GPT-4o integration pattern. No research needed.

Phases that benefit from spot validation:
- **Phase 2 (ProspectFinder):** iTunes genre IDs are documented in community sources but not in official Apple docs. Validate `genreId` values (Comedy=1303, True Crime=1488, Business=1321) with a live test call before committing them to the implementation.
- **Phase 4 (Outreach Execution):** Pitch messaging quality is empirical. Build in a review loop after the first 1-2 pitches are sent — iterate the `gen-pitch` GPT-4o prompt if output is generic or off-tone.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new packages; all technologies already integrated; patterns verified by direct codebase inspection |
| Features | MEDIUM | Feature list is well-grounded; pricing guidance conflicts between FEATURES.md ($75-150/ep) and PITFALLS.md ($300-600/ep) — use PITFALLS.md value-anchored range |
| Architecture | HIGH | All integration points verified via direct inspection of `main.py`, `search_index.py`, `content_editor.py`, `demo_packager.py`, `client_config.py` |
| Pitfalls | MEDIUM-HIGH | Sales/outreach pitfalls from practitioner sources; legal section explicitly not legal advice; consent risk is HIGH confidence and the most critical finding |

**Overall confidence:** HIGH for technical implementation; MEDIUM for go-to-market execution (empirical, will need iteration based on real prospect responses)

### Gaps to Address

- **Genre ID verification:** iTunes `genreId` values (Comedy=1303, True Crime=1488, Business=1321) confirmed from community sources, not official Apple docs. Run a test query per genre before committing these constants to the implementation.
- **Pricing disconnect:** FEATURES.md suggests $75–150/episode entry pricing (below market, to reduce friction). PITFALLS.md recommends $300–600/episode (value-anchored, prevents commoditization). Resolve before outreach execution — recommend PITFALLS.md guidance. Under-pricing signals hobbyist tool and attracts churners.
- **Consent workflow formalization:** PITFALLS.md identifies consent as the highest-risk issue but there is no code-level enforcement mechanism. This is a process gap to address in Phase 4 operational documentation — a pre-processing checklist step before any `uv run main.py --client <prospect>` command is issued.
- **Follow-up cadence reminders:** FEATURES.md defines a 3-touch follow-up cadence (Day 4, Day 10, Day 20). The contact tracker stores dates but nothing reminds the operator of next actions. For 3-5 prospects, calendar reminders are sufficient; flag for a future automation phase if prospect volume grows.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `main.py`, `search_index.py`, `content_editor.py`, `demo_packager.py`, `client_config.py`, `rss_episode_fetcher.py`, `pipeline/context.py` — integration pattern verification
- [iTunes Search API Official Docs](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/index.html) — endpoint, parameters, no-auth requirement confirmed
- [iTunes Search API Examples](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/SearchExamples.html) — parameter structure confirmed
- feedparser project dependency (`rss_episode_fetcher.py`) — `author_detail.email`, `itunes_email`, `feed.entries` fields confirmed

### Secondary (MEDIUM confidence)
- [iTunes genre IDs community reference (publicapis.io)](https://publicapis.io/i-tunes-search-api) — Comedy (1303), True Crime (1488), Business (1321); not in official Apple docs
- [Listen Notes API Documentation](https://www.listennotes.com/api/docs/) — alternative prospect discovery method, free tier confirmed
- [podseeker.co RSS contact extraction](https://www.podseeker.co/blog/fastest-way-to-get-podcast-contact-information) — `itunes:owner/itunes:email` reliability confirmed
- [Podcast Production Pricing 2026 — Rise25](https://rise25.com/lead-generation/podcast-production-pricing/) — market rate ranges ($500-2,000/episode full-service)
- [Podcast Editing Rates — SasPod](https://saspod.com/blog/podcast-editor-costs-and-rates-freelancers) — freelance rates ($50-200/episode)
- [Cold outreach best practices — Cleverly](https://www.cleverly.co/blog/cold-email-outreach-best-practices) — pitch structure and follow-up cadence
- [Google Spam Policy changes — Outbound Republic](https://outboundrepublic.com/blog/what-googles-spam-changes-mean-for-b2b-cold-email-in-2025) — deliverability risk for new domains (enforced November 2025)
- [GDPR voice data rules — IAPP](https://iapp.org/news/a/how-do-the-rules-on-audio-recording-change-under-the-gdpr) — voice recordings as personal data under GDPR

### Tertiary (LOW confidence)
- [WaveApps cold pitch templates](https://www.waveapps.com/freelancing/cold-pitch-templates) — general freelance templates; not podcast-specific; used for structural reference only
- Podcast listener count estimates (Chartable, Rephonic, Podchaser) — download estimates are imprecise; useful directionally

---

*Research completed: 2026-03-28*
*Ready for roadmap: yes*
