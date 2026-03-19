# Milestones

## v1.2 Engagement & Smart Scheduling (Shipped: 2026-03-19)

**Phases:** 3 | **Plans:** 7 | **Files changed:** 46 (+5721/-167)
**New code:** 1,278 LOC Python (2 new modules + 4 new test files + extensions)
**Requirements:** 13/13 satisfied (ANLYT-01–04, ENGAGE-01–04, SCHED-01–03, CONTENT-01–02)
**Timeline:** 2026-03-18 → 2026-03-19 (1 day)
**Git range:** test(09-01) → feat(11-02)

**Key accomplishments:**
1. Platform IDs captured at upload — analytics saves 100 quota units/episode by skipping YouTube search API
2. Engagement history accumulator builds cross-episode corpus automatically with upsert logic
3. Spearman category ranking with comedy voice as hard constraint — edgy content never scored down
4. GPT-4o content generation receives top-3 historically high-performing categories as prompt context
5. Smart scheduling computes optimal posting windows per platform, research-based fallback when sparse
6. Stub uploader detection (.functional flags) + hashtag auto-injection into Twitter posts
7. topic_scorer episode number bug fixed (loop index → actual episode number)

**Tech debt accepted:**
- VALIDATION.md nyquist_compliant not flipped post-execution (all 3 phases)
- SUMMARY frontmatter missing some requirements_completed entries
- Instagram/TikTok day-of-week data not in EngagementScorer (uploaders are stubs — by design)

---

## v1.1 Discoverability & Short-Form (Shipped: 2026-03-18)

**Phases:** 3 | **Plans:** 6 | **Files changed:** 35 (+5931/-68)
**New code:** 2,577 LOC Python (3 modules + 3 test files + 1 template)
**Requirements:** 14/14 satisfied (CLIP-01–04, WEB-01–06, SAFE-01–04)
**Timeline:** 2026-03-17 → 2026-03-18 (2 days)
**Git range:** feat(06-01) → feat(08-02)

**Key accomplishments:**
1. Hormozi-style word-by-word subtitle clips with pysubs2 ASS rendering and FFmpeg 9:16 vertical video
2. SEO-optimized episode webpages with PodcastEpisode JSON-LD, auto-deployed to GitHub Pages via PyGithub
3. GPT-4o content compliance checker that flags YouTube guideline violations before upload
4. Auto-muting of flagged segments by merging into existing censor machinery (zero new FFmpeg code)
5. Upload safety gate blocking distribution on critical violations with `--force` override
6. 83 new tests across 3 modules (31 + 31 + 21), 422 total suite passing

**Tech debt accepted:**
- VALIDATION.md nyquist_compliant frontmatter not flipped post-execution (all 3 phases)
- SUMMARY frontmatter missing some requirements_completed entries
- run_distribute_only bypasses compliance gate (low severity — manual re-run path only)
- Instagram Reels and TikTok uploaders remain stubs (pre-existing, scoped to v2 DIST-02)

---

## v1.0 Pipeline Upgrade (Shipped: 2026-03-18)

**Phases:** 5 | **Plans:** 14 | **Commits:** 42 | **Files changed:** 34 (+4654/-2574)
**Codebase:** 23,810 LOC Python | **Requirements:** 14/14 satisfied
**Timeline:** 2026-03-16 → 2026-03-18 (3 days)
**Git range:** feat(01-foundations) → feat(05-03)

**Key accomplishments:**
1. Replaced beep censorship with smooth audio ducking; normalized to -16 LUFS broadcast standard
2. Injected edgy comedy voice persona into all AI-generated content via few-shot prompts
3. Added AudioClipScorer — clips selected by audio energy and comedy timing
4. Auto-generated chapter markers in MP3 ID3 tags and RSS feed for podcast app navigation
5. Refactored main.py from 1870-line God Object to 134-line CLI shim with pipeline/ package
6. Fixed silent production bugs: scheduler stub, credential paths, dependency hygiene

**Tech debt accepted:**
- beep_sound backward compat (intentional)
- chapters_json_url always None (needs hosting)
- run_audio dead export, _load_scored_topics duplication
- topic_tracker disabled (pre-existing Google OAuth issue)

---

