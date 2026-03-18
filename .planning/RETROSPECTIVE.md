# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Pipeline Upgrade

**Shipped:** 2026-03-18
**Phases:** 5 | **Plans:** 14 | **Sessions:** ~3

### What Was Built
- Professional audio mastering (ducking censorship + LUFS normalization)
- Comedy voice persona injected into all AI-generated content
- AudioClipScorer for energy-based clip selection
- Chapter markers in MP3 ID3 tags and RSS feed
- Modular pipeline/ architecture (main.py 1870 → 134 lines)
- Silent production bug fixes (scheduler, credentials, dependencies)

### What Worked
- TDD approach (RED/GREEN across phases) caught regressions early and made extraction in Phase 5 safe
- Phase ordering (bugs → features → refactor) meant each phase built on a stable base
- Mechanical extraction in Phase 5 preserved all 9 checkpoint keys without renaming
- Integration checker at audit caught the VOICE-02 wiring gap that all phase-level tests missed

### What Was Inefficient
- VOICE-02 audio_path wiring gap existed since Phase 3 but wasn't caught until milestone audit — phase verification only checked unit tests, not production call sites
- Nyquist VALIDATION.md files were created but never fully signed off (all 5 phases remain `nyquist_compliant: false`)
- Some SUMMARY.md files lacked `one_liner` frontmatter, making automated accomplishment extraction fail

### Patterns Established
- `@patch.object(Config, attr)` for testing config-backed attributes instead of `@patch.dict(os.environ)`
- Pipeline step functions accept `(ctx: PipelineContext, components: dict, state=None)`
- Checkpoint keys are string constants preserved exactly across extraction — regression test enforces this

### Key Lessons
1. Phase-level verification passes unit tests but misses integration wiring — the milestone audit's integration checker is essential, not optional
2. Mechanical extraction (copy code faithfully, don't refactor) is the safest approach for large refactors with an existing test suite
3. TDD scaffolds in Wave 0/1 pay off massively — by Phase 5, the 6 structural tests guided the entire refactor

### Cost Observations
- Model mix: ~30% opus (orchestration), ~70% sonnet (research, planning, execution, verification)
- Sessions: ~3 (initial setup + phases 1-4, phase 5 + audit, completion)
- Notable: Sequential wave execution (not parallel) was correct for Phase 5 since each plan depended on the previous

---

## Milestone: v1.1 — Discoverability & Short-Form

**Shipped:** 2026-03-18
**Phases:** 3 | **Plans:** 6 | **Sessions:** ~1

### What Was Built
- Hormozi-style word-by-word subtitle clips (pysubs2 ASS + FFmpeg 9:16 vertical video)
- SEO-optimized episode webpages with PodcastEpisode JSON-LD, deployed to GitHub Pages via PyGithub
- GPT-4o content compliance checker flagging YouTube guideline violations
- Auto-muting of flagged segments by merging into existing censor_timestamps
- Upload safety gate with `--force` override for critical violations

### What Worked
- Reusing existing censor_timestamps for compliance muting — zero new FFmpeg code, elegant architectural fit
- Each phase was truly independent (no shared code between 6/7/8) so sequential execution was clean
- Comedy-aware compliance prompt prevented over-flagging dark humor
- TDD continued to pay off — 83 new tests caught issues immediately

### What Was Inefficient
- SUMMARY frontmatter `requirements_completed` and `one_liner` fields were inconsistently populated across agents
- Nyquist VALIDATION.md frontmatter still not flipped post-execution (same issue as v1.0)
- run_distribute_only compliance bypass wasn't caught until integration checker at audit — confirms v1.0 lesson about integration testing

### Patterns Established
- `self.enabled` env-var pattern works cleanly for new modules (compliance, webpage generator)
- PyGithub upsert (get_contents for SHA, then update/create) is the GitHub Pages deploy pattern
- Merging domain-specific flags into existing pipeline data structures (censor_timestamps) avoids new plumbing

### Key Lessons
1. Nyquist frontmatter needs automated flipping during execution — manual updates are consistently forgotten
2. SUMMARY frontmatter extraction is unreliable for automated reporting — the tool should write these fields
3. Integration testing at milestone boundary continues to catch real gaps (run_distribute_only bypass)

### Cost Observations
- Model mix: ~20% opus (orchestration), ~80% sonnet (research, planning, execution, verification)
- Sessions: ~1 (entire milestone in a single conversation)
- Notable: 3 phases in 2 days — faster than v1.0 thanks to established patterns and clean architecture

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~3 | 5 | Established TDD + mechanical extraction pattern |
| v1.1 | ~1 | 3 | Independent phases, censor_timestamps reuse pattern |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 333 | — | 2 (mutagen, openai) |
| v1.1 | 422 | — | 2 (PyGithub, yake) |

### Top Lessons (Verified Across Milestones)

1. Integration testing at milestone boundary catches gaps that phase-level unit tests miss (v1.0: VOICE-02 wiring, v1.1: run_distribute_only bypass)
2. Refactor last — stable code is safer to extract than moving targets
3. Nyquist frontmatter updates are consistently forgotten — needs automation
