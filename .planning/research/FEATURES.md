# Feature Research

**Domain:** Podcast production service — real-world client testing and sales demo packaging
**Researched:** 2026-03-28
**Milestone:** v1.4 — Real-World Testing & Sales Readiness
**Confidence:** MEDIUM

---

## Context

The pipeline is fully built (570 tests, all features shipped through v1.3 + multi-client YAML).
This research answers: what does a compelling sales demo look like, what genre-specific tuning
is needed for non-comedy podcasts, and how do production services win clients.

The pipeline already produces: cleaned audio, clips with burned-in captions, show notes, thumbnails,
social captions, compliance reports, chapters, RSS, and YouTube upload. The gap is packaging and
positioning that output as a persuasive demo for prospects.

---

## Feature Landscape

### Table Stakes (Prospects Expect These)

Features a prospective client assumes exist when evaluating any production service.
Missing these = demo feels incomplete before quality is even assessed.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Before/after audio clip | Strongest single proof point. Prospects want to hear the transformation in 60 seconds | MEDIUM | Not currently packaged. Need to snapshot raw audio before censor/normalize steps, then extract matching timestamp segment from both raw and processed for side-by-side |
| 2-3 social clips with captions per genre | Every production service delivers this. Swell AI, Castmagic, Descript all lead with clips | LOW | Already built. Demo folder must include 2-3 `.mp4` clip files with burned-in subtitles per client genre |
| Show notes / blog post sample | Every agency includes show notes as a deliverable. Absence signals incomplete service | LOW | Already built: BlogPostGenerator. Demo package must include the generated `.md` or `.html` output |
| Platform-specific social captions | Ready-to-post copy per platform is baseline expectation from any content service | LOW | Already built: analysis dict contains `social_captions` per platform. Must be included in demo folder as a readable `.txt` |
| Episode thumbnail | Visual identity is table stakes for YouTube. First thing a prospect looks at | LOW | Already built: ThumbnailGenerator. Include the `.png` in demo package |
| Chapter list / timestamps | Podcast apps show chapters. Prospects who listen on Overcast/Pocket Casts notice immediately | LOW | Already built: chapter_generator + RSS Podcasting 2.0. Format as a readable list in demo |
| Genre-appropriate tone in AI-generated content | Show notes and captions must sound like the show, not a generic template | MEDIUM | Current per-client YAML `voice_persona` and `blog_voice` fields support this. Requires prompt engineering per genre before demo runs |
| One-page explanation of what was automated | Prospects cannot evaluate what they cannot understand. The demo output means nothing without a narrative | LOW | New deliverable: `DEMO.md` per client explaining each artifact, what was automated, and estimated time saved |

### Differentiators (Competitive Advantage)

Features that separate this pipeline from Swell AI, Castmagic, Descript, and one-person editors.
These are where the demo wins or loses.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| One command → full pipeline output | Prospect sees everything produced from a single run, not 12 tools stitched together. No SaaS subscriptions. | LOW | Demo README must open with: `uv run main.py --client <name> ep1` → all deliverables appear in `output/<client>/<ep>/` |
| Per-client voice persona in AI content | Generated content sounds like the show, not a generic template. True crime narrative vs. business insight vs. comedy edge — each demo artifact should be unmistakably genre-matched | MEDIUM | YAML persona config exists and works. Demo must show genre-distinct show notes side-by-side to make this tangible |
| Compliance-gated upload safety | Catches content that would trigger YouTube/Spotify guideline violations before they happen. Critical for brand podcasts with reputational stakes | LOW | Already built. Include a compliance report `.txt` in demo package. This is a differentiator no SaaS tool offers |
| Audio ducking censorship (not a beep) | Professional duck-fade sounds hand-edited. Prospects have heard beep censorship on bad tools. The before/after comparison makes this immediately audible | LOW | Demo must include explicit before/after audio for this one feature alone. It's the fastest trust builder |
| Energy-scored clip selection | Clips are selected by a scoring model, not random timestamps. Prospect can see why each clip was chosen | MEDIUM | AudioClipScorer already runs and writes scores. Expose the top-3 scores and reasoning in the demo package |
| EBU R128 / LUFS audio mastering | Real broadcast-standard loudness normalization. Podcasts submitted to Spotify require -14 LUFS. Most one-person editors do not do this correctly | LOW | Include the measured LUFS value before/after normalization in the demo README |
| Full pipeline cost: near-zero per episode | OpenAI tokens + local Whisper. No per-seat SaaS. Scales from 1 to 100 clients without per-unit pricing | LOW | Include cost estimate in demo README. This is a competitive moat vs. Swell AI ($29-99/mo) and editor time ($50-200/ep) |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Live upload demo to prospect's platforms | Feels real. Shows the full pipeline | Requires their OAuth credentials. Security risk. Quota concerns. Cannot do in a meeting. Brand risk if something goes wrong | Demo the upload step logs + screenshots of a test account's YouTube/Spotify output. Describe the capability in README |
| Fully automated publishing without human review | "Set it and forget it" appeals to busy hosts | Prospects — especially brand/business podcasts — correctly want editorial control. Removing them from the loop creates liability for content errors | Demo `--auto-approve` mode but lead with interactive clip approval workflow. Frame automation as time-saving, not human-eliminating |
| Real-time processing during a demo meeting | Shows transparency and power | 70-minute episode: 20-40 min Whisper on GPU, another 5-10 min for analysis. No prospect sits through that | Pre-process all demo episodes. Present output artifacts, not progress bars |
| Generic AI persona for all clients | Simpler to configure one template | Destroys the core value proposition. A true crime podcast's show notes written in comedy voice is an anti-demo | Per-client YAML persona is the correct approach. Demo must show genre-distinct outputs explicitly |
| Filler word removal | Commonly asked about. Sounds professional | Kills comedy timing. Degrades interview cadence where verbal pauses signal thinking. High false-positive rate. Per feedback from Fake Problems hosts, this is a known bad default | Demonstrate silence trimming between segments instead. Flag filler removal as configurable but off by default. Include a note in DEMO.md |
| Dynamic ad insertion | Monetization pitch is appealing | Requires CDN hosting, mid-roll insertion logic, IAB DAAST compliance. Fundamentally incompatible with zero-cost constraint | Explain that chapter markers are ad markers that a separate DAI system (Spotify, Acast) can hook into without pipeline changes |

---

## Feature Dependencies

```
Demo Package Output
    └──requires──> Per-client pipeline run (fully processed episode)
                       └──requires──> Client config (YAML: voice_persona, blog_voice, rss_metadata)
                                          └──requires──> Public episode download or local audio file

Genre Persona Tuning (per-client YAML)
    └──enhances──> Show notes tone
    └──enhances──> Social caption voice
    └──enhances──> Clip hook language in subtitle clips
    └──must run before──> pipeline analysis step (Step 3)

Before/After Audio Comparison
    └──requires──> Raw audio snapshot (before Step 4 censor)
    └──requires──> Processed audio (after Step 4.5 normalize)
    └──requires──> Matching timestamp segment extraction via FFmpeg
    └──note──> Pipeline currently does not snapshot raw audio. Must add snapshot logic.

DEMO.md per client
    └──requires──> Processed episode (all artifacts)
    └──reads──> LUFS values from normalization log
    └──reads──> Clip energy scores from analysis JSON
    └──reads──> Compliance report from analysis step
    └──written manually or templated──> One per genre client

Compliance Report in Demo Package
    └──requires──> Analyze step (GPT-4o compliance pass)
    └──already generated──> Surfaces as field in analysis JSON; needs extraction to readable format
```

### Dependency Notes

- **Genre persona tuning must happen before running the pipeline, not after.** YAML voice_persona feeds into the GPT-4o analysis prompt. Running first, then tuning, requires re-running the analysis step.
- **Before/after audio requires a pipeline change.** The pipeline normalizes audio in-place. A raw segment must be captured before Step 4 (censor) to enable comparison. This is medium-complexity: save a 60-second clip at a selected timestamp before the censor step runs.
- **Demo quality multiplies with persona quality.** A generic voice_persona produces generic show notes. The whole demo looks weak. Persona tuning is the highest-leverage P1 task before running any demo episode.
- **Real podcast sourcing unblocks everything.** Without a real public episode to run, genre tuning cannot be validated and demo artifacts cannot be generated. Client sourcing is the first dependency in the chain.

---

## MVP Definition

v1.4 scope. MVP here means: minimum demo that would convince a real podcast host to
pay for production services after a 30-minute conversation or async review.

### Launch With (Demo v1)

- [ ] 2-3 real genre clients configured in YAML (true crime, business/interview, one more) — no demo without this
- [ ] Processed episode per genre with full pipeline run — no artifacts without this
- [ ] Demo folder per client: processed MP3, 2-3 captioned clips, show notes, thumbnail, social captions `.txt`, chapter list, compliance report — the "leave-behind" a prospect reviews after the call
- [ ] Before/after audio segment (same 60-second timestamp: raw vs processed) — fastest trust-builder; requires pipeline snapshot change
- [ ] `DEMO.md` per client: what was automated, estimated time saved per episode, cost per episode, LUFS before/after, clip scores — the narrative that makes the artifacts make sense

### Add After Validation (Post-demo)

- [ ] Genre-tuned clip scoring criteria (true crime: narrative tension; business: insight quotability) — add when real clients surface the need after seeing initial clip selection
- [ ] Compliance report as formatted `.pdf` or standalone `.txt` deliverable — add if brand-podcast prospects specifically ask for it
- [ ] Demo video walkthrough (screen recording + narration, 3-5 min) — useful for async cold outreach; defer until live demo is validated with at least one real prospect

### Future Consideration (v2+)

- [ ] White-label output (remove pipeline branding from generated content headers) — needed if reselling to agencies, not direct clients
- [ ] Client Dropbox folder handoff automation (write all demo deliverables to a named Dropbox folder) — useful at 3+ active clients; today manual folder share is fine
- [ ] Proposal email generator (uses episode metadata + client name to draft a pitch) — clever but premature

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Genre-matched voice persona per client YAML | HIGH | LOW (YAML already supported; needs prompt text) | P1 |
| Real public podcast sourced per genre (2-3) | HIGH | LOW (research + download) | P1 |
| Demo output folder with all deliverables organized | HIGH | LOW (pipeline already produces files; needs folder copy logic) | P1 |
| `DEMO.md` per client explaining artifacts | HIGH | LOW (write once, template it) | P1 |
| True crime voice persona tuning | HIGH | LOW (prompt engineering in YAML) | P1 |
| Business/interview voice persona tuning | HIGH | LOW (prompt engineering in YAML) | P1 |
| Before/after audio segment comparison | HIGH | MEDIUM (requires pipeline snapshot before censor step) | P1 |
| Clip energy scores surfaced in demo | MEDIUM | LOW (already in analysis JSON; just needs extraction) | P2 |
| Compliance report in demo package | MEDIUM | LOW (already generated; needs extraction to readable file) | P2 |
| Chapter list formatted for demo | MEDIUM | LOW (already generated) | P2 |
| Genre-tuned clip scoring profiles | MEDIUM | MEDIUM (new scoring criteria in YAML per genre) | P2 |
| Demo video walkthrough (async outreach) | MEDIUM | MEDIUM (screen recording + narration) | P3 |

**Priority key:**
- P1: Demo is incomplete without it — blocks showing anything to a prospect
- P2: Materially improves demo quality and conversion probability
- P3: Adds polish; defer until live demo is validated

---

## Genre-Specific Tuning Requirements

What needs to change per genre in the existing per-client YAML configuration.
All of these map to existing `voice_persona`, `blog_voice`, and `topic_scoring` fields.

### True Crime

**Tone:** Narrative, investigative, empathetic. Avoids dark comedy. Avoids casual irreverence.
**`voice_persona`:** "You are a true crime podcast producer with a background in investigative journalism. Write in a gripping, narrative voice. Use active voice. Build tension. Treat victims and families with dignity. Never make light of violence or trauma."
**`blog_voice`:** Chronological case summary. Include trigger warnings for violence/trauma content. Avoid speculating on guilt.
**Clip selection:** Favor moments of revelation, tension, interview testimony, case-breaking details. Avoid crosstalk, tangents, host banter.
**Censorship word list:** Minimize. True crime rarely has profanity censorship needs. May need victim/minor name protection depending on case. No comedy-specific words.
**Social captions:** Teaser hooks ("The one detail investigators missed for 10 years"). Avoid humor entirely. Platform: Reddit/Instagram/TikTok over Twitter.
**Compliance:** Extra scrutiny on misinformation about active cases. Real names of minors must be flagged as compliance risk.
**Thumbnail:** Dark palette, true crime aesthetic. May need a different Pillow template than the current comedy layout.

### Business / Interview

**Tone:** Authoritative, professional, insight-driven. Warm but not edgy. Guest expertise is central.
**`voice_persona`:** "You are a business podcast producer. Write in a confident, professional voice. Lead with actionable insights. Highlight guest credentials and specific expertise. Use precise language. Avoid jargon."
**`blog_voice`:** Key insights as numbered bullet points. Guest bio paragraph at top. Timestamp links to key moments. Resource links if mentioned in episode.
**Clip selection:** Favor quotable insights, counterintuitive takes, concrete frameworks or numbers. Avoid long preamble, filler-heavy setup, crosstalk.
**Censorship word list:** Minimal. Company names and competitor mentions require care. Standard light profanity list.
**Social captions:** Insight hook on LinkedIn ("How [guest] built $X with one counterintuitive rule"), shorter for Twitter. LinkedIn is the primary platform for business podcasts.
**Compliance:** Low inherent risk. Watch for investment advice, medical advice, or legal claims that could trigger platform financial/health content policies.
**Thumbnail:** Guest headshot + show logo. Clean, professional layout. Corporate-friendly.

### Comedy (existing Fake Problems config — baseline)

**Tone:** Edgy, irreverent, dark humor. Censorship is for genuine slurs/doxxing, not punchlines.
**Clip selection:** High-energy laugh moments, outrageous premises, unexpected punchlines, escalating bits.
**Compliance:** Comedy-aware — profanity and dark humor are NOT violations. Genuine hate speech and dangerous misinformation are. (This is already implemented correctly.)

---

## Competitor Feature Analysis

Services prospects are already aware of or comparing against:

| Feature | Swell AI / Castmagic | Descript | Manual editor ($50-200/ep) | Our Pipeline |
|---------|----------------------|----------|---------------------------|--------------|
| Auto clip extraction | Yes — AI highlights | Yes — manual + AI suggestions | Manual judgment | Yes — energy-scored AudioClipScorer |
| Burned-in captions on clips | Yes — auto | Yes — manual styling | Varies | Yes — Hormozi-style word-by-word |
| Show notes generation | Yes — voice-matched | No | Sometimes | Yes — persona-matched per client YAML |
| Platform-specific social captions | Yes | No | Sometimes | Yes — per-platform in analysis dict |
| Full audio mastering (EBU R128 -14 LUFS) | No | No | Depends on editor | Yes — ffmpeg-loudnorm |
| Censorship with duck-fade | No | No | Manual edit | Yes — smooth duck-fade, not beep |
| Content compliance check | No | No | No | Yes — GPT-4o compliance gate |
| RSS with Podcasting 2.0 chapters | No | No | No | Yes — chapter markers in RSS + ID3 |
| YouTube upload + Shorts | No | No | No | Yes — full episode + Shorts clips |
| One-command full pipeline | No (multiple tools) | No (manual steps) | No | Yes |
| Per-client genre persona tuning | No | No | Human judgment | Yes — YAML voice_persona |
| Cost per episode (ongoing) | $29-99/mo SaaS | $24/mo + editor time | $50-200/episode | ~$1-3 OpenAI tokens only |

**Positioning summary:** The pipeline wins on depth of integration (one command, real audio mastering,
compliance, full distribution) and near-zero cost at scale. It loses on UX polish — Descript has a
GUI, Swell has a web app. The demo must lead with output quality and cost, not the interface.
The "no SaaS subscription" and "works for any genre with a config change" angles are the strongest
competitive differentiators for a sales conversation.

---

## Sources

- [Professional Podcast Production Services — PropodcastSolutions](https://propodcastsolutions.com/podcast-production-services/) — MEDIUM confidence
- [Top 17 Podcast Production Companies 2026 — Content Allies](https://contentallies.com/learn/podcast-production-companies-agencies-services-for-b2b-b2c) — MEDIUM confidence
- [7 AI Podcast Production Systems — GodOfPrompt](https://www.godofprompt.ai/blog/7-ai-podcast-production-systems-that-automated-the-entire-workflow) — MEDIUM confidence
- [Viral Podcast Clips Guide 2025 — Fame](https://www.fame.so/post/ultimate-podcast-clip-guide) — MEDIUM confidence
- [Shareable Podcast Clips Guide 2026 — Riverside](https://riverside.com/blog/podcast-clips) — MEDIUM confidence
- [Trial Episode Strategy — We Edit Podcasts](https://weeditpodcasts.com/trial/) — MEDIUM confidence
- [True Crime Podcast Guide 2025/2026 — Jellypod](https://jellypod.ai/blog/perfect-guide-true-crime) — MEDIUM confidence
- [True Crime Podcast Business Growth 2026 — Variety](https://variety.com/2026/digital/podcasts/true-crime-podcasts-business-growth-1236679547/) — MEDIUM confidence
- [Most Popular Podcast Genres 2025 — Command Your Brand](https://commandyourbrand.com/the-most-popular-podcast-genres-in-2025-ranked-by-audience-growth/) — MEDIUM confidence
- [B2B Podcast Production Checklist — Rise25](https://rise25.com/lead-generation/b2b-podcast-production-checklist/) — MEDIUM confidence
- [Podcast Demo Reel Guide — Promo.ly](https://promo.ly/podcast-demo-reel/) — MEDIUM confidence
- [Pilot Project Structure for Podcast Agencies — Ankord Media](https://www.ankordmedia.com/blog/bay-area-startups-structure-podcast-agency-pilot-project) — MEDIUM confidence
- [Science of Viral Podcast Clips — Listeners to Clients](https://listenerstoclients.com/blog/the-science-of-viral-podcast-clips-a-proven-framework-for-high-impact-content) — MEDIUM confidence
- [AI-Powered Podcast Service for Agencies — 51Blocks](https://51blocks.com/ai-podcasts-for-agencies) — LOW confidence (marketing page)

---

*Feature research for: podcast production service — real-world client testing and sales demo packaging (v1.4 milestone)*
*Researched: 2026-03-28*
