# Milestones

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

