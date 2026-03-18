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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~3 | 5 | Established TDD + mechanical extraction pattern |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 333 | — | 2 (mutagen, openai) |

### Top Lessons (Verified Across Milestones)

1. Integration testing at milestone boundary catches gaps that phase-level unit tests miss
2. Refactor last — stable code is safer to extract than moving targets
